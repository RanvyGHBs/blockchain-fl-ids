"""
Stage 2E Baseline Algorithms & Model Benchmarks.
Implements non-federated baselines and alternative Byzantine aggregators:
1. Centralized-IDS: Global upper bound trained on unified client-training pool.
2. Local-Silo IDS: Uncooperative lower bound trained independently per client.
3. Multi-Krum: Byzantine-tolerant distance-based aggregator (Blanchard et al., NeurIPS 2017).
4. FoolsGold: Sybil-tolerant historical cosine similarity aggregator (Fung et al., IEEE TIFS 2020).
"""

import time
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

from src.models.ids_net import IDSNet


# ---------------------------------------------------------------------------
# Multi-Krum Aggregator (Blanchard et al., NeurIPS 2017)
# ---------------------------------------------------------------------------

def aggregate_multikrum(client_weights: List[np.ndarray], f: int = 1, m: int = 1) -> Tuple[np.ndarray, List[int]]:
    """
    Multi-Krum Byzantine-robust aggregation (Blanchard et al., NeurIPS 2017).
    
    Theoretical Constraint:
        n >= 2f + 3
    where n is total clients and f is assumed number of Byzantine workers.
    
    Args:
        client_weights: List of flattened 1D parameter vectors from participating clients.
        f: Number of assumed Byzantine/malicious clients.
        m: Number of winning updates to average (1 <= m <= n - f - 2). If m=1, standard Krum.
        
    Returns:
        Tuple of (aggregated_weights_vector, selected_client_indices)
    """
    n = len(client_weights)
    if n == 0:
        raise ValueError("Cannot aggregate empty client weights list.")
        
    required_n = 2 * f + 3
    if n < required_n:
        raise ValueError(
            f"Multi-Krum theoretical constraint violated: n={n} clients must be >= 2f + 3 = {required_n} "
            f"for f={f} Byzantine clients. (Valid configurations: n=5 with f=1, or n>=7 for f=2)."
        )
        
    k_closest = n - f - 2
    if k_closest < 1:
        raise ValueError(f"Invalid neighborhood size n - f - 2 = {k_closest} < 1.")
        
    m = max(1, min(m, k_closest))
    
    # Compute pairwise squared Euclidean distances
    stacked = np.stack(client_weights, axis=0)  # Shape: (n, d)
    distances = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        for j in range(i + 1, n):
            d2 = float(np.sum((stacked[i] - stacked[j]) ** 2))
            distances[i, j] = d2
            distances[j, i] = d2
            
    # Calculate Krum scores: sum of squared distances to the k_closest neighbors
    scores = np.zeros(n, dtype=np.float64)
    for i in range(n):
        # Exclude self distance (which is 0.0)
        peer_distances = [distances[i, j] for j in range(n) if j != i]
        peer_distances.sort()
        scores[i] = sum(peer_distances[:k_closest])
        
    # Select m clients with smallest Krum scores
    selected_indices = np.argsort(scores)[:m].tolist()
    selected_weights = [stacked[idx] for idx in selected_indices]
    
    # Average selected updates
    aggregated = np.mean(selected_weights, axis=0).astype(np.float32)
    return aggregated, selected_indices


# ---------------------------------------------------------------------------
# FoolsGold Aggregator (Fung et al., IEEE TIFS 2020)
# ---------------------------------------------------------------------------

class FoolsGoldAggregator:
    """
    FoolsGold Sybil-tolerant aggregation (Fung et al., IEEE TIFS 2020).
    Evaluates pairwise cosine similarities between cumulative historical update trajectories
    to identify and attenuate coordinated/cloned Sybil coalitions.
    """

    def __init__(self, num_clients: int, epsilon: float = 1e-5):
        self.num_clients = num_clients
        self.epsilon = epsilon
        # Cumulative historical update vectors: client_id -> 1D array
        self.historical_trajectories: Dict[int, np.ndarray] = {}

    def aggregate(
        self,
        client_updates: Dict[int, np.ndarray],
        client_weights_map: Optional[Dict[int, np.ndarray]] = None,
        global_weights: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, Dict[int, float]]:
        """
        Aggregates client updates with FoolsGold Sybil penalization.
        
        Args:
            client_updates: Dict mapping client_id -> delta_w or local_weights.
            client_weights_map: Dict mapping client_id -> absolute local weights (if updates are deltas).
            global_weights: Previous global weights vector (if updates are absolute weights).
            
        Returns:
            Tuple of (aggregated_weights, client_alpha_weights_dict)
        """
        cids = sorted(list(client_updates.keys()))
        n = len(cids)
        if n == 0:
            raise ValueError("Cannot aggregate empty client updates dict.")
        if n == 1:
            cid = cids[0]
            w = client_weights_map[cid] if client_weights_map else client_updates[cid]
            return w.astype(np.float32), {cid: 1.0}

        # Calculate delta updates if absolute weights were passed
        deltas: Dict[int, np.ndarray] = {}
        for cid in cids:
            if global_weights is not None:
                deltas[cid] = client_updates[cid] - global_weights
            else:
                deltas[cid] = client_updates[cid]

        # Update historical cumulative trajectories
        for cid in cids:
            # Normalize update delta to avoid magnitude bias
            delta_norm = float(np.linalg.norm(deltas[cid]))
            normalized_delta = deltas[cid] / max(self.epsilon, delta_norm)
            if cid not in self.historical_trajectories:
                self.historical_trajectories[cid] = normalized_delta.copy()
            else:
                self.historical_trajectories[cid] += normalized_delta

        # Compute pairwise cosine similarity matrix between historical trajectories
        sim_matrix = np.zeros((n, n), dtype=np.float64)
        for i, cid_i in enumerate(cids):
            h_i = self.historical_trajectories[cid_i]
            norm_i = float(np.linalg.norm(h_i))
            for j, cid_j in enumerate(cids):
                if i == j:
                    sim_matrix[i, j] = 1.0
                elif j > i:
                    h_j = self.historical_trajectories[cid_j]
                    norm_j = float(np.linalg.norm(h_j))
                    cos_sim = float(np.dot(h_i, h_j) / max(self.epsilon, norm_i * norm_j))
                    sim_matrix[i, j] = cos_sim
                    sim_matrix[j, i] = cos_sim

        # Identify maximum pairwise similarity to any other peer
        max_sims = np.zeros(n, dtype=np.float64)
        for i in range(n):
            peer_sims = [sim_matrix[i, j] for j in range(n) if i != j]
            max_sims[i] = max(0.0, max(peer_sims) if peer_sims else 0.0)

        # Pardoning and attenuation: score alpha_i
        # If client i has similarity higher than others, attenuate its weight
        alphas = np.ones(n, dtype=np.float64)
        v_max = float(np.max(max_sims))
        if v_max > self.epsilon:
            for i in range(n):
                for j in range(n):
                    if i != j and max_sims[i] > max_sims[j]:
                        sim_matrix[i, j] *= (1.0 - max_sims[i]) / (1.0 - max_sims[j] + self.epsilon)
                # Client alpha is 1 - max adjusted similarity
                adj_peer_sims = [sim_matrix[i, j] for j in range(n) if i != j]
                alphas[i] = max(0.0, 1.0 - max(adj_peer_sims))
        else:
            alphas = np.ones(n, dtype=np.float64)

        # Normalize alphas
        alpha_sum = float(np.sum(alphas))
        if alpha_sum < self.epsilon:
            normalized_alphas = np.ones(n, dtype=np.float64) / n
        else:
            normalized_alphas = alphas / alpha_sum

        # Target weights to aggregate
        if client_weights_map:
            target_weights = [client_weights_map[cid] for cid in cids]
        else:
            target_weights = [client_updates[cid] for cid in cids]

        stacked_weights = np.stack(target_weights, axis=0)  # Shape: (n, d)
        aggregated = np.zeros_like(stacked_weights[0])
        alpha_dict: Dict[int, float] = {}
        for idx, cid in enumerate(cids):
            aggregated += normalized_alphas[idx] * stacked_weights[idx]
            alpha_dict[cid] = float(normalized_alphas[idx])

        return aggregated.astype(np.float32), alpha_dict


# ---------------------------------------------------------------------------
# Centralized IDS Model Trainer (Global Upper Bound)
# ---------------------------------------------------------------------------

class CentralizedBaseline:
    """
    Trains a centralized IDS model on the unified client-training pool.
    Represents the empirical performance ceiling (zero data distribution fragmentation).
    Evaluates strictly on the isolated held-out test set.
    """

    def __init__(
        self,
        input_dim: int = 122,
        num_classes: int = 2,
        epochs: int = 5,
        batch_size: int = 64,
        lr: float = 0.002,
        device: str = "cpu",
        seed: int = 42
    ):
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.epochs = epochs
        self.batch_size = batch_size
        self.lr = lr
        self.device = device
        self.seed = seed

    def train_and_evaluate(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict[str, Any]:
        """Trains centralized model and evaluates on held-out test data."""
        # Deterministic seeding
        torch.manual_seed(self.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(self.seed)
        np.random.seed(self.seed)

        model = IDSNet(input_dim=self.input_dim, num_classes=self.num_classes).to(self.device)
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=self.lr)

        train_ds = TensorDataset(torch.from_numpy(X_train).float(), torch.from_numpy(y_train).long())
        train_loader = DataLoader(train_ds, batch_size=self.batch_size, shuffle=True)

        t0_train = time.perf_counter()
        model.train()
        for epoch in range(self.epochs):
            for Xb, yb in train_loader:
                Xb, yb = Xb.to(self.device), yb.to(self.device)
                optimizer.zero_grad()
                out = model(Xb)
                loss = criterion(out, yb)
                loss.backward()
                optimizer.step()
        train_time = time.perf_counter() - t0_train

        # Evaluation on held-out test data
        t0_eval = time.perf_counter()
        model.eval()
        test_ds = TensorDataset(torch.from_numpy(X_test).float(), torch.from_numpy(y_test).long())
        test_loader = DataLoader(test_ds, batch_size=256, shuffle=False)

        all_preds = []
        all_targets = []
        with torch.no_grad():
            for Xb, yb in test_loader:
                Xb = Xb.to(self.device)
                preds = torch.argmax(model(Xb), dim=1).cpu().numpy()
                all_preds.extend(preds)
                all_targets.extend(yb.numpy())
        eval_time = time.perf_counter() - t0_eval

        y_true = np.array(all_targets)
        y_pred = np.array(all_preds)

        acc = float(accuracy_score(y_true, y_pred))
        prec_macro = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
        rec_macro = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
        f1_macro = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
        prec_weighted = float(precision_score(y_true, y_pred, average="weighted", zero_division=0))
        rec_weighted = float(recall_score(y_true, y_pred, average="weighted", zero_division=0))
        f1_weighted = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))
        cm = confusion_matrix(y_true, y_pred).tolist()

        return {
            "model_type": "centralized_ids",
            "seed": self.seed,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "accuracy": acc,
            "precision_macro": prec_macro,
            "recall_macro": rec_macro,
            "f1_macro": f1_macro,
            "precision_weighted": prec_weighted,
            "recall_weighted": rec_weighted,
            "f1_weighted": f1_weighted,
            "confusion_matrix": cm,
            "train_time_sec": train_time,
            "eval_time_sec": eval_time
        }


# ---------------------------------------------------------------------------
# Local Silo IDS Model Trainer (Uncooperative Lower Bound)
# ---------------------------------------------------------------------------

class LocalSiloBaseline:
    """
    Trains independent local IDS models per client partition without federation.
    Represents the uncooperative lower bound (each organization defends in isolation).
    Evaluates each local model against the common held-out test set.
    """

    def __init__(
        self,
        input_dim: int = 122,
        num_classes: int = 2,
        epochs: int = 5,
        batch_size: int = 64,
        lr: float = 0.002,
        device: str = "cpu",
        seed: int = 42
    ):
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.epochs = epochs
        self.batch_size = batch_size
        self.lr = lr
        self.device = device
        self.seed = seed

    def train_and_evaluate_silos(
        self,
        client_partitions: Dict[int, Tuple[np.ndarray, np.ndarray]],
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict[str, Any]:
        """Trains independent models on each client's partition and evaluates on test set."""
        client_results: Dict[int, Dict[str, Any]] = {}
        criterion = nn.CrossEntropyLoss()

        test_ds = TensorDataset(torch.from_numpy(X_test).float(), torch.from_numpy(y_test).long())
        test_loader = DataLoader(test_ds, batch_size=256, shuffle=False)

        total_train_time = 0.0

        for cid, (Xc, yc) in client_partitions.items():
            client_seed = (self.seed * 10007 + cid * 997) % (2**31 - 1)
            torch.manual_seed(client_seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(client_seed)
            np.random.seed(client_seed)

            model = IDSNet(input_dim=self.input_dim, num_classes=self.num_classes).to(self.device)
            optimizer = torch.optim.Adam(model.parameters(), lr=self.lr)

            train_ds = TensorDataset(torch.from_numpy(Xc).float(), torch.from_numpy(yc).long())
            train_loader = DataLoader(train_ds, batch_size=min(self.batch_size, max(2, len(yc))), shuffle=True)

            t0 = time.perf_counter()
            model.train()
            for epoch in range(self.epochs):
                for Xb, yb in train_loader:
                    Xb, yb = Xb.to(self.device), yb.to(self.device)
                    optimizer.zero_grad()
                    loss = criterion(model(Xb), yb)
                    loss.backward()
                    optimizer.step()
            c_train_time = time.perf_counter() - t0
            total_train_time += c_train_time

            # Evaluate on held-out test set
            model.eval()
            all_preds, all_targets = [], []
            with torch.no_grad():
                for Xb, yb in test_loader:
                    Xb = Xb.to(self.device)
                    preds = torch.argmax(model(Xb), dim=1).cpu().numpy()
                    all_preds.extend(preds)
                    all_targets.extend(yb.numpy())

            y_true = np.array(all_targets)
            y_pred = np.array(all_preds)

            client_results[cid] = {
                "client_id": cid,
                "train_samples": len(Xc),
                "accuracy": float(accuracy_score(y_true, y_pred)),
                "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
                "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
                "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
                "train_time_sec": c_train_time
            }

        # Aggregate summary statistics across silos
        accs = [res["accuracy"] for res in client_results.values()]
        f1s = [res["f1_macro"] for res in client_results.values()]

        return {
            "model_type": "local_silos",
            "seed": self.seed,
            "num_silos": len(client_partitions),
            "client_results": client_results,
            "mean_accuracy": float(np.mean(accs)),
            "std_accuracy": float(np.std(accs)),
            "min_accuracy": float(np.min(accs)),
            "max_accuracy": float(np.max(accs)),
            "mean_f1_macro": float(np.mean(f1s)),
            "std_f1_macro": float(np.std(f1s)),
            "total_train_time_sec": total_train_time
        }
