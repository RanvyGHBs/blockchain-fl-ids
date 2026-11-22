"""
Multi-Criteria Trust Validation Engine.
Evaluates candidate model updates using a three-tier inspection defense:
1. L2-Norm Bounding (detects model scaling / noise explosion).
2. Cosine Similarity to Peer Consensus (detects sign-flipping and directional inversion).
3. Validation Loss Verification (Non-IID safe: checks whether applying weights improves or maintains performance on a balanced benchmark slice).
"""

from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader

from src.models.ids_net import IDSNet


class MultiCriteriaTrustEngine:
    """
    Evaluates client updates to distinguish between benign Non-IID variance
    and intentional adversarial poisoning.
    Supports modular enabling/disabling of individual tiers for Dynamic Defense Matrix ablation studies.
    """

    def __init__(self, input_dim: int = 122, num_classes: int = 2,
                 norm_threshold_factor: float = 2.5, cosine_threshold: float = 0.15,
                 loss_increase_threshold: float = 1.5, device: str = "cpu",
                 enable_norm_check: bool = True,
                 enable_cosine_check: bool = True,
                 enable_loss_check: bool = True):
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.norm_threshold_factor = norm_threshold_factor
        self.cosine_threshold = cosine_threshold
        self.loss_increase_threshold = loss_increase_threshold
        self.device = device
        self.enable_norm_check = enable_norm_check
        self.enable_cosine_check = enable_cosine_check
        self.enable_loss_check = enable_loss_check

        # Validator reference model
        self.validator_model = IDSNet(input_dim=input_dim, num_classes=num_classes).to(self.device)

    def evaluate_updates(self, client_updates: Dict[int, np.ndarray],
                         global_weights: np.ndarray,
                         val_data: Optional[Tuple[np.ndarray, np.ndarray]] = None) -> Dict[int, Dict[str, Any]]:
        """
        Executes multi-criteria evaluation across all submitted client weight vectors.
        Returns a dictionary mapping client_id -> validation report.
        """
        results: Dict[int, Dict[str, Any]] = {}
        cids = list(client_updates.keys())
        if len(cids) == 0:
            return results

        # Compute median weight vector across peer submissions as the peer consensus direction
        all_weights = np.stack([client_updates[cid] for cid in cids], axis=0)
        median_vector = np.median(all_weights, axis=0)
        global_norm = float(np.linalg.norm(global_weights))

        # Dynamic L2 norm threshold based on global model norm
        max_allowed_norm = max(1.0, global_norm * self.norm_threshold_factor)

        # Baseline loss on validation set (if available)
        baseline_loss = None
        val_loader = None
        criterion = nn.CrossEntropyLoss()

        if self.enable_loss_check and val_data is not None:
            X_val, y_val = val_data
            val_dataset = TensorDataset(torch.from_numpy(X_val), torch.from_numpy(y_val))
            val_loader = DataLoader(val_dataset, batch_size=128, shuffle=False)

            self.validator_model.set_weights_vector(global_weights)
            self.validator_model.eval()
            total_b_loss = 0.0
            with torch.no_grad():
                for Xb, yb in val_loader:
                    Xb, yb = Xb.to(self.device), yb.to(self.device)
                    total_b_loss += criterion(self.validator_model(Xb), yb).item() * len(yb)
            baseline_loss = total_b_loss / len(val_dataset)

        for cid in cids:
            weights = client_updates[cid]
            weight_norm = float(np.linalg.norm(weights))

            # 1. Norm Check
            if self.enable_norm_check:
                norm_passed = weight_norm <= max_allowed_norm
                norm_reason = "Normal L2 norm" if norm_passed else f"L2 norm {weight_norm:.2f} exceeds threshold {max_allowed_norm:.2f}"
            else:
                norm_passed = True
                norm_reason = "Norm check disabled"

            # 2. Cosine Similarity to Peer Median Check
            norm_prod = np.linalg.norm(weights) * np.linalg.norm(median_vector)
            if norm_prod > 1e-9:
                cos_sim = float(np.dot(weights, median_vector) / norm_prod)
            else:
                cos_sim = 1.0

            if self.enable_cosine_check:
                cosine_passed = cos_sim >= self.cosine_threshold
                cosine_reason = f"Cosine similarity {cos_sim:.3f} within consensus bounds" if cosine_passed else f"Cosine similarity {cos_sim:.3f} below threshold {self.cosine_threshold:.3f}"
            else:
                cosine_passed = True
                cosine_reason = "Cosine similarity check disabled"

            # 3. Validation Loss Check (Non-IID Safe)
            loss_passed = True
            cand_loss = None
            loss_reason = "Validation check not invoked" if not self.enable_loss_check else "Validation loss check active"

            if self.enable_loss_check:
                if val_loader is not None and baseline_loss is not None:
                    self.validator_model.set_weights_vector(weights)
                    self.validator_model.eval()
                    total_c_loss = 0.0
                    with torch.no_grad():
                        for Xb, yb in val_loader:
                            Xb, yb = Xb.to(self.device), yb.to(self.device)
                            total_c_loss += criterion(self.validator_model(Xb), yb).item() * len(yb)
                    cand_loss = total_c_loss / len(val_loader.dataset)
                    loss_delta = cand_loss - baseline_loss

                    loss_passed = loss_delta <= self.loss_increase_threshold
                    loss_reason = f"Loss delta {loss_delta:+.3f} acceptable" if loss_passed else f"Loss delta {loss_delta:+.3f} indicates severe model degradation"
                else:
                    loss_passed = True
                    loss_reason = "Validation data unavailable"

            # Overall Decision: Update is valid ONLY if all enabled checks pass
            is_valid = norm_passed and cosine_passed and loss_passed
            rejection_reasons = []
            if not norm_passed: rejection_reasons.append(norm_reason)
            if not cosine_passed: rejection_reasons.append(cosine_reason)
            if not loss_passed: rejection_reasons.append(loss_reason)

            verdict_reason = "Update verified as honest and consistent" if is_valid else " | ".join(rejection_reasons)

            results[cid] = {
                "client_id": cid,
                "is_valid": is_valid,
                "reason": verdict_reason,
                "l2_norm": float(weight_norm),
                "cosine_similarity": float(cos_sim),
                "cand_loss": float(cand_loss) if cand_loss is not None else None,
                "baseline_loss": float(baseline_loss) if baseline_loss is not None else None,
                "norm_passed": norm_passed,
                "cosine_passed": cosine_passed,
                "loss_passed": loss_passed
            }

        return results
