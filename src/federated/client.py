"""
Federated Client Representation.
Each client acts as an autonomous network entity (enterprise campus, regional hospital, cloud VPC)
with private local network traffic logs. Supports standard local training and FedProx proximal regularization.
"""

import copy
from typing import Dict, Any, Tuple, Optional, List
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from src.models.ids_net import IDSNet


class FederatedClient:
    """
    Simulates an independent federated participant.
    """

    def __init__(self, client_id: int, client_name: str, X_local: np.ndarray, y_local: np.ndarray,
                 input_dim: int = 122, num_classes: int = 2, device: str = "cpu", seed: int = 42):
        self.client_id = client_id
        self.client_name = client_name
        self.device = device
        self.seed = seed
        self.num_classes = num_classes

        # Local dataset
        self.num_samples = len(y_local)
        self.X_local = X_local
        self.y_local = y_local

        # Internal PyTorch model
        self.model = IDSNet(input_dim=input_dim, num_classes=num_classes).to(self.device)

        # Reputation and status tracked locally / on-chain
        self.reputation = 1.0
        self.is_quarantined = False
        self.is_malicious = False

    def set_global_weights(self, global_weights: np.ndarray):
        """Synchronizes local model parameters with the latest global model."""
        self.model.set_weights_vector(global_weights)

    def get_local_weights(self) -> np.ndarray:
        """Returns flattened 1D local model weights vector."""
        return self.model.get_weights_vector()

    def get_weights_hash(self) -> str:
        """Returns SHA-256 hash of current local model parameters."""
        return self.model.get_weights_hash()

    @staticmethod
    def _build_batch_indices(num_samples: int, batch_size: int, shuffle: bool = True) -> List[List[int]]:
        """
        Partitions sample indices into batches such that no batch has size 1 when num_samples > 1.
        Preserves 100% of samples (every sample index is included exactly once per epoch).
        """
        indices = np.random.permutation(num_samples).tolist() if shuffle else list(range(num_samples))
        if num_samples <= 1:
            return [indices]

        effective_bs = max(2, batch_size)
        if num_samples <= effective_bs:
            return [indices]

        batches = []
        start = 0
        while start < num_samples:
            remaining = num_samples - start
            if remaining == effective_bs + 1:
                # Split remaining B+1 samples into two balanced batches (e.g. 33 -> 17 and 16)
                if remaining >= 4:
                    mid = start + remaining // 2
                    batches.append(indices[start:mid])
                    batches.append(indices[mid:])
                else:
                    # remaining == 3: keep as single batch of 3
                    batches.append(indices[start:])
                break
            elif remaining <= effective_bs:
                batches.append(indices[start:])
                break
            else:
                batches.append(indices[start:start + effective_bs])
                start += effective_bs

        return batches

    def local_train(self, epochs: int = 2, batch_size: int = 64, lr: float = 0.001,
                    fedprox_mu: float = 0.0, global_weights: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Executes local model training on private data.
        Supports both standard Empirical Risk Minimization and FedProx proximal regularization:
            L_total = L_CE + (mu / 2) * ||w - w_global||^2

        Guarantees that 100% of available client-training samples are processed:
        - Avoids singleton batches (len == 1) via dynamic batch construction whenever N > 1.
        - Provides a BatchNorm-compatible mode guard fallback for N == 1 singleton clients.
        - Silently discarding training samples is strictly prevented.
        """
        self.model.train()
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)

        N = len(self.X_local)
        if N == 0:
            return {
                "client_id": self.client_id,
                "train_loss": 0.0,
                "num_samples": 0,
                "samples_processed_per_epoch": 0,
                "total_samples_trained": 0,
                "weights_hash": self.get_weights_hash()
            }

        global_weight_tensor = None
        if fedprox_mu > 0.0 and global_weights is not None:
            global_weight_tensor = torch.from_numpy(global_weights).to(self.device)

        total_loss = 0.0
        total_samples_trained = 0

        for epoch in range(epochs):
            # Dynamic batch partitioning ensuring NO singleton batch when N > 1
            batch_slices = self._build_batch_indices(N, batch_size, shuffle=True)

            for b_idx in batch_slices:
                X_batch = torch.from_numpy(self.X_local[b_idx]).to(self.device)
                y_batch = torch.from_numpy(self.y_local[b_idx]).to(self.device)
                batch_len = len(b_idx)

                optimizer.zero_grad()

                # BatchNorm Mode Guard:
                # BatchNorm requires batch_len > 1 to compute sample variance during training.
                # If N == 1 (client has exactly one sample), temporarily set BatchNorm modules
                # to eval() mode so they use running statistics, computing forward and backward passes
                # without raising division-by-zero ValueError.
                is_singleton = (batch_len == 1)
                if is_singleton:
                    for m in self.model.modules():
                        if isinstance(m, nn.BatchNorm1d):
                            m.eval()

                outputs = self.model(X_batch)
                loss = criterion(outputs, y_batch)

                # FedProx Proximal Regularization Term
                if fedprox_mu > 0.0 and global_weight_tensor is not None:
                    current_flat = torch.cat([p.flatten() for p in self.model.parameters()])
                    prox_term = (fedprox_mu / 2.0) * torch.norm(current_flat - global_weight_tensor) ** 2
                    loss += prox_term

                loss.backward()
                optimizer.step()

                if is_singleton:
                    for m in self.model.modules():
                        if isinstance(m, nn.BatchNorm1d):
                            m.train()

                total_loss += loss.item() * batch_len
                total_samples_trained += batch_len

        avg_loss = total_loss / (epochs * N) if (epochs * N) > 0 else 0.0
        return {
            "client_id": self.client_id,
            "train_loss": float(avg_loss),
            "num_samples": self.num_samples,
            "samples_processed_per_epoch": total_samples_trained // epochs if epochs > 0 else 0,
            "total_samples_trained": total_samples_trained,
            "weights_hash": self.get_weights_hash()
        }

    def evaluate(self, X_eval: np.ndarray, y_eval: np.ndarray, batch_size: int = 128,
                 average: str = "weighted") -> Dict[str, float]:
        """
        Evaluates local model against an evaluation dataset.
        Supports both weighted and macro multi-class classification metrics.
        """
        self.model.eval()
        criterion = nn.CrossEntropyLoss()
        dataset = TensorDataset(torch.from_numpy(X_eval), torch.from_numpy(y_eval))
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

        total_loss = 0.0
        all_preds = []
        all_targets = []

        with torch.no_grad():
            for X_batch, y_batch in dataloader:
                X_batch, y_batch = X_batch.to(self.device), y_batch.to(self.device)
                outputs = self.model(X_batch)
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

        return {
            "loss": float(avg_loss),
            "accuracy": float(acc),
            "precision": float(prec),
            "recall": float(rec),
            "f1_score": float(f1),
            "precision_macro": float(prec_macro),
            "recall_macro": float(rec_macro),
            "f1_score_macro": float(f1_macro)
        }
