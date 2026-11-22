"""
Federated Learning Server / Coordinator.
Manages global rounds, weight distribution, client training dispatch,
model aggregation, and round-by-round global evaluation.
"""

from typing import List, Dict, Any, Optional
import time
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

from src.models.ids_net import IDSNet
from src.federated.client import FederatedClient
from src.federated.aggregators import (
    aggregate_fedavg, aggregate_trimmed_mean, aggregate_median, aggregate_trust_weighted
)


class FederatedServer:
    """
    Coordinates federated learning rounds among independent clients.
    """

    def __init__(self, input_dim: int = 122, num_classes: int = 2, aggregation_algorithm: str = "fedavg",
                 device: str = "cpu", seed: int = 42):
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.aggregation_algorithm = aggregation_algorithm.lower()
        self.device = device
        self.seed = seed

        # Global Model
        torch.manual_seed(self.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(self.seed)
        self.global_model = IDSNet(input_dim=input_dim, num_classes=num_classes).to(self.device)

        # Round tracking
        self.current_round = 0
        self.round_history: List[Dict[str, Any]] = []

    def get_global_weights(self) -> np.ndarray:
        return self.global_model.get_weights_vector()

    def set_global_weights(self, weights: np.ndarray):
        self.global_model.set_weights_vector(weights)

    def get_global_weights_hash(self) -> str:
        return self.global_model.get_weights_hash()

    def execute_round(self, clients: List[FederatedClient], local_epochs: int = 2,
                      batch_size: int = 64, lr: float = 0.001, fedprox_mu: float = 0.0,
                      client_weights_override: Optional[Dict[int, np.ndarray]] = None) -> Dict[str, Any]:
        """
        Executes one complete federated training round:
        1. Broadcasts global weights to active clients.
        2. Clients perform local training (or inject adversarial perturbations).
        3. Collects local weights.
        4. Aggregates updates into new global model.
        """
        self.current_round += 1
        current_global_weights = self.get_global_weights()

        client_updates = []
        client_sample_counts = []
        client_reputations = []
        client_metrics = []

        round_start_time = time.time()

        # Step 1 & 2: Local training on clients
        for client in clients:
            if client.is_quarantined:
                # Quarantined clients are skipped from standard aggregation
                continue

            # Synchronize client model with current global weights
            client.set_global_weights(current_global_weights)

            # Check if an adversarial override is provided (e.g., from Attack Engine)
            if client_weights_override and client.client_id in client_weights_override:
                local_weights = client_weights_override[client.client_id]
                train_meta = {"client_id": client.client_id, "train_loss": 0.0, "num_samples": client.num_samples,
                              "weights_hash": "adversarial"}
            else:
                train_meta = client.local_train(
                    epochs=local_epochs, batch_size=batch_size, lr=lr,
                    fedprox_mu=fedprox_mu, global_weights=current_global_weights,
                    round_num=self.current_round
                )
                local_weights = client.get_local_weights()

            client_updates.append(local_weights)
            client_sample_counts.append(client.num_samples)
            client_reputations.append(client.reputation)
            client_metrics.append(train_meta)

        # Step 3: Aggregation
        agg_start = time.time()
        if self.aggregation_algorithm == "fedavg":
            new_global_weights = aggregate_fedavg(client_updates, client_sample_counts)
        elif self.aggregation_algorithm == "trimmed_mean":
            new_global_weights = aggregate_trimmed_mean(client_updates, beta=0.2)
        elif self.aggregation_algorithm == "median":
            new_global_weights = aggregate_median(client_updates)
        elif self.aggregation_algorithm == "trust_weighted":
            new_global_weights = aggregate_trust_weighted(client_updates, client_sample_counts, client_reputations)
        else:
            raise ValueError(f"Unknown aggregation algorithm: {self.aggregation_algorithm}")

        aggregation_time = time.time() - agg_start

        # Step 4: Update global model
        self.set_global_weights(new_global_weights)
        round_duration = time.time() - round_start_time

        round_summary = {
            "round": self.current_round,
            "participating_clients": [c.client_id for c in clients if not c.is_quarantined],
            "client_sample_counts": client_sample_counts,
            "aggregation_time": float(aggregation_time),
            "round_duration": float(round_duration),
            "global_weights_hash": self.get_global_weights_hash()
        }

        return round_summary

    def evaluate(self, X_eval: np.ndarray, y_eval: np.ndarray, batch_size: int = 128,
                 average: str = "weighted") -> Dict[str, Any]:
        """
        Evaluates global model against an evaluation dataset.
        Supports both weighted and macro multi-class classification metrics.
        """
        self.global_model.eval()
        criterion = nn.CrossEntropyLoss()
        dataset = TensorDataset(torch.from_numpy(X_eval), torch.from_numpy(y_eval))
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

        total_loss = 0.0
        all_preds = []
        all_targets = []

        with torch.no_grad():
            for X_batch, y_batch in dataloader:
                X_batch, y_batch = X_batch.to(self.device), y_batch.to(self.device)
                outputs = self.global_model(X_batch)
                loss = criterion(outputs, y_batch)
                total_loss += loss.item() * len(y_batch)
                preds = torch.argmax(outputs, dim=1).cpu().numpy()
                all_preds.extend(preds)
                all_targets.extend(y_batch.cpu().numpy())

        avg_loss = total_loss / len(dataset)
        acc = accuracy_score(all_targets, all_preds)
        prec = precision_score(all_targets, all_preds, average=average, zero_division=0)
        rec = recall_score(all_targets, all_preds, average=average, zero_division=0)
        f1 = f1_score(all_targets, all_preds, average=average, zero_division=0)
        prec_macro = precision_score(all_targets, all_preds, average="macro", zero_division=0)
        rec_macro = recall_score(all_targets, all_preds, average="macro", zero_division=0)
        f1_macro = f1_score(all_targets, all_preds, average="macro", zero_division=0)
        cm = confusion_matrix(all_targets, all_preds, labels=list(range(self.num_classes))).tolist()

        eval_result = {
            "round": self.current_round,
            "loss": float(avg_loss),
            "accuracy": float(acc),
            "precision": float(prec),
            "recall": float(rec),
            "f1_score": float(f1),
            "precision_macro": float(prec_macro),
            "recall_macro": float(rec_macro),
            "f1_score_macro": float(f1_macro),
            "confusion_matrix": cm,
            "predictions": all_preds
        }
        self.round_history.append(eval_result)
        return eval_result

    def predict(self, X: np.ndarray, batch_size: int = 128) -> np.ndarray:
        """
        Generates class predictions for an input array using the current global model.
        """
        self.global_model.eval()
        dataset = TensorDataset(torch.from_numpy(X.astype(np.float32)))
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
        all_preds = []
        with torch.no_grad():
            for (X_batch,) in dataloader:
                X_batch = X_batch.to(self.device)
                outputs = self.global_model(X_batch)
                preds = torch.argmax(outputs, dim=1).cpu().numpy()
                all_preds.extend(preds)
        return np.array(all_preds, dtype=np.int64)
