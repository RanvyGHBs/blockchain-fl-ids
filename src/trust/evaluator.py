"""
Multi-Criteria Trust Validation Engine with Privacy-Aware Calibration (WP3).
Evaluates candidate model updates using a three-tier inspection defense:
1. L2-Norm Bounding (detects model scaling / noise explosion).
2. Cosine Similarity to Peer Consensus & Reference (detects sign-flipping and directional inversion).
3. Validation Loss Verification (Non-IID safe: checks whether applying weights improves or maintains performance on a balanced benchmark slice).

Supports:
- Uncalibrated Mode: Original Stage 2D heuristic thresholds (preserved as comparison baseline).
- Privacy-Aware Calibrated Mode (WP3): Dynamically derived noise-aware thresholds accounting for
  client-level Gaussian perturbation n ~ N(0, (2*sigma*C)^2 * I_d) in high dimensions (d).
"""

from typing import Dict, List, Tuple, Any, Optional, Union
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader

from src.models.ids_net import IDSNet


class MultiCriteriaTrustEngine:
    """
    Evaluates client updates to distinguish between benign Non-IID variance,
    differential privacy perturbation, and intentional adversarial poisoning.
    Supports modular enabling/disabling of individual tiers for Dynamic Defense Matrix ablation studies.
    """

    def __init__(
        self,
        input_dim: int = 122,
        num_classes: int = 2,
        norm_threshold_factor: float = 2.5,
        cosine_threshold: float = 0.15,
        loss_increase_threshold: float = 1.5,
        device: str = "cpu",
        enable_norm_check: bool = True,
        enable_cosine_check: bool = True,
        enable_loss_check: bool = True,
        # WP3 Privacy Calibration Parameters
        calibration_mode: str = "uncalibrated",
        dp_enabled: bool = False,
        dp_clip_norm: float = 1.0,
        dp_noise_multiplier: float = 0.0,
        norm_margin_factor: float = 1.25,
        norm_min_factor: float = 0.75,
        calibrated_cosine_threshold: float = 0.10,
        calibrated_loss_factor: float = 5.0
    ):
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.norm_threshold_factor = norm_threshold_factor
        self.cosine_threshold = cosine_threshold
        self.loss_increase_threshold = loss_increase_threshold
        self.device = device
        self.enable_norm_check = enable_norm_check
        self.enable_cosine_check = enable_cosine_check
        self.enable_loss_check = enable_loss_check

        # Calibration parameters
        cal_mode_clean = str(calibration_mode).lower().strip()
        if cal_mode_clean in ("calibrated", "privacy_aware", "dp_aware"):
            self.calibration_mode = "privacy_aware"
        else:
            self.calibration_mode = "uncalibrated"

        self.dp_enabled = bool(dp_enabled)
        self.dp_clip_norm = float(dp_clip_norm)
        self.dp_noise_multiplier = float(dp_noise_multiplier)
        self.norm_margin_factor = float(norm_margin_factor)
        self.norm_min_factor = float(norm_min_factor)
        self.calibrated_cosine_threshold = float(calibrated_cosine_threshold)
        self.calibrated_loss_factor = float(calibrated_loss_factor)

        # Validator reference model
        self.validator_model = IDSNet(input_dim=input_dim, num_classes=num_classes).to(self.device)

    def is_calibrated(self) -> bool:
        """Returns True if the engine is operating in privacy-aware calibrated mode."""
        return self.calibration_mode == "privacy_aware"

    def evaluate_updates(
        self,
        client_updates: Dict[int, np.ndarray],
        global_weights: np.ndarray,
        val_data: Optional[Tuple[np.ndarray, np.ndarray]] = None
    ) -> Dict[int, Dict[str, Any]]:
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
        d = len(global_weights)

        # ------------------------------------------------------------------
        # 1. Norm Threshold Formulation
        # ------------------------------------------------------------------
        if self.is_calibrated() and (self.dp_enabled or self.dp_noise_multiplier > 0):
            # Root-Mean-Square (RMS) norm of privatized weights under Gaussian perturbation n ~ N(0, (2*sigma*C)^2 * I_d)
            # Mathematical note: mu_norm = sqrt(E[||w||_2^2]) is the RMS norm, which by Jensen's inequality
            # serves as an upper bound on E[||w||_2]. In d=26594 dimensions, RMS approximates E[||w||_2] to within < 0.001%.
            # The interval [min_allowed_norm, max_allowed_norm] = [0.75 * mu, 1.25 * mu] is an engineering heuristic
            # threshold designed to accommodate Non-IID client drift while rejecting model scaling / explosion.
            sigma_eff = self.dp_noise_multiplier
            c_eff = self.dp_clip_norm
            mu_norm = float(np.sqrt(global_norm**2 + 4.0 * d * (sigma_eff**2) * (c_eff**2)))
            max_allowed_norm = mu_norm * self.norm_margin_factor
            min_allowed_norm = mu_norm * self.norm_min_factor
        else:
            mu_norm = global_norm
            max_allowed_norm = max(1.0, global_norm * self.norm_threshold_factor)
            min_allowed_norm = 0.0

        # ------------------------------------------------------------------
        # 2. Validation Loss Setup
        # ------------------------------------------------------------------
        baseline_loss = None
        val_loader = None
        criterion = nn.CrossEntropyLoss()
        cand_losses: Dict[int, float] = {}

        if self.enable_loss_check and val_data is not None:
            X_val, y_val = val_data
            val_dataset = TensorDataset(torch.from_numpy(X_val), torch.from_numpy(y_val))
            val_loader = DataLoader(val_dataset, batch_size=256, shuffle=False)

            self.validator_model.set_weights_vector(global_weights)
            self.validator_model.eval()
            total_b_loss = 0.0
            with torch.no_grad():
                for Xb, yb in val_loader:
                    Xb, yb = Xb.to(self.device), yb.to(self.device)
                    total_b_loss += criterion(self.validator_model(Xb), yb).item() * len(yb)
            baseline_loss = total_b_loss / len(val_dataset)

            # Precompute candidate loss for all submitted weights
            for cid in cids:
                self.validator_model.set_weights_vector(client_updates[cid])
                self.validator_model.eval()
                total_c_loss = 0.0
                with torch.no_grad():
                    for Xb, yb in val_loader:
                        Xb, yb = Xb.to(self.device), yb.to(self.device)
                        total_c_loss += criterion(self.validator_model(Xb), yb).item() * len(yb)
                cand_losses[cid] = total_c_loss / len(val_dataset)

        # ------------------------------------------------------------------
        # 3. Validation Loss Threshold Formulation
        # ------------------------------------------------------------------
        if self.is_calibrated() and (self.dp_enabled or self.dp_noise_multiplier > 0) and len(cand_losses) > 0:
            med_cand_loss = float(np.median(list(cand_losses.values())))
            # Calibrated loss threshold allows DP noise variance across peers up to calibrated_loss_factor
            base_ref = baseline_loss if baseline_loss is not None else 0.0
            max_allowed_loss = max(base_ref + self.loss_increase_threshold, med_cand_loss * self.calibrated_loss_factor)
        elif baseline_loss is not None:
            max_allowed_loss = baseline_loss + self.loss_increase_threshold
        else:
            max_allowed_loss = None

        # ------------------------------------------------------------------
        # 4. Cosine Threshold Formulation
        # ------------------------------------------------------------------
        if self.is_calibrated() and (self.dp_enabled or self.dp_noise_multiplier > 0):
            effective_cos_threshold = self.calibrated_cosine_threshold
        else:
            effective_cos_threshold = self.cosine_threshold

        # ------------------------------------------------------------------
        # 5. Per-Client Multi-Criteria Evaluation
        # ------------------------------------------------------------------
        for cid in cids:
            weights = client_updates[cid]
            weight_norm = float(np.linalg.norm(weights))

            # Tier 1: Norm Check
            if self.enable_norm_check:
                if self.is_calibrated() and (self.dp_enabled or self.dp_noise_multiplier > 0):
                    norm_passed = (weight_norm >= min_allowed_norm) and (weight_norm <= max_allowed_norm)
                    if norm_passed:
                        norm_reason = (
                            f"L2 norm {weight_norm:.2f} within calibrated bounds "
                            f"[{min_allowed_norm:.2f}, {max_allowed_norm:.2f}] (expected mu={mu_norm:.2f})"
                        )
                    else:
                        norm_reason = (
                            f"L2 norm {weight_norm:.2f} exceeds calibrated bounds "
                            f"[{min_allowed_norm:.2f}, {max_allowed_norm:.2f}] (expected mu={mu_norm:.2f})"
                        )
                else:
                    norm_passed = weight_norm <= max_allowed_norm
                    norm_reason = (
                        "Normal L2 norm" if norm_passed
                        else f"L2 norm {weight_norm:.2f} exceeds threshold {max_allowed_norm:.2f}"
                    )
            else:
                norm_passed = True
                norm_reason = "Norm check disabled"

            # Tier 2: Cosine Similarity to Peer Median & Global Alignment
            norm_prod = np.linalg.norm(weights) * np.linalg.norm(median_vector)
            cos_sim = float(np.dot(weights, median_vector) / norm_prod) if norm_prod > 1e-9 else 1.0

            global_prod = np.linalg.norm(weights) * global_norm
            cos_global = float(np.dot(weights, global_weights) / global_prod) if global_prod > 1e-9 else 1.0

            if self.enable_cosine_check:
                if self.is_calibrated() and (self.dp_enabled or self.dp_noise_multiplier > 0):
                    # Directional trust condition:
                    # 1. cos(w_i, m) >= effective_cos_threshold (0.10): alignment with pooled peer consensus median m.
                    # 2. cos(w_i, w_global) >= -0.01: non-inverted alignment with global model, with a -0.01 numerical
                    #    buffer (~1.6 standard deviations of noise in d=26,594 dimensions) to prevent false rejection
                    #    of orthogonal updates undergoing negative random fluctuations.
                    cosine_passed = (cos_sim >= effective_cos_threshold) and (cos_global >= -0.01)
                    if cosine_passed:
                        cosine_reason = (
                            f"Cosine similarity {cos_sim:.3f} >= {effective_cos_threshold:.3f} "
                            f"within consensus bounds (global alignment {cos_global:+.3f})"
                        )
                    else:
                        cosine_reason = (
                            f"Cosine similarity {cos_sim:.3f} below threshold {effective_cos_threshold:.3f} "
                            f"or inverted direction (global alignment {cos_global:+.3f})"
                        )
                else:
                    cosine_passed = cos_sim >= self.cosine_threshold
                    cosine_reason = (
                        f"Cosine similarity {cos_sim:.3f} within consensus bounds" if cosine_passed
                        else f"Cosine similarity {cos_sim:.3f} below threshold {self.cosine_threshold:.3f}"
                    )
            else:
                cosine_passed = True
                cosine_reason = "Cosine similarity check disabled"

            # Tier 3: Validation Loss Check
            cand_loss = cand_losses.get(cid, None)
            if self.enable_loss_check:
                if val_loader is not None and baseline_loss is not None and cand_loss is not None:
                    loss_delta = cand_loss - baseline_loss
                    if self.is_calibrated() and (self.dp_enabled or self.dp_noise_multiplier > 0):
                        loss_passed = cand_loss <= max_allowed_loss
                        loss_reason = (
                            f"Candidate loss {cand_loss:.2f} acceptable (threshold {max_allowed_loss:.2f})" if loss_passed
                            else f"Candidate loss {cand_loss:.2f} exceeds calibrated threshold {max_allowed_loss:.2f}"
                        )
                    else:
                        loss_passed = loss_delta <= self.loss_increase_threshold
                        loss_reason = (
                            f"Loss delta {loss_delta:+.3f} acceptable" if loss_passed
                            else f"Loss delta {loss_delta:+.3f} indicates severe model degradation"
                        )
                else:
                    loss_passed = True
                    loss_reason = "Validation data unavailable"
            else:
                loss_passed = True
                loss_reason = "Validation check disabled"

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
                "calibration_mode": self.calibration_mode,
                "reason": verdict_reason,
                "l2_norm": float(weight_norm),
                "expected_norm": float(mu_norm),
                "max_allowed_norm": float(max_allowed_norm),
                "min_allowed_norm": float(min_allowed_norm),
                "cosine_similarity": float(cos_sim),
                "cos_global": float(cos_global),
                "effective_cosine_threshold": float(effective_cos_threshold),
                "cand_loss": float(cand_loss) if cand_loss is not None else None,
                "baseline_loss": float(baseline_loss) if baseline_loss is not None else None,
                "max_allowed_loss": float(max_allowed_loss) if max_allowed_loss is not None else None,
                "norm_passed": norm_passed,
                "cosine_passed": cosine_passed,
                "loss_passed": loss_passed
            }

        return results


class PrivacyAwareTrustEngine(MultiCriteriaTrustEngine):
    """
    Convenience subclass configuring MultiCriteriaTrustEngine in privacy-aware calibrated mode.
    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("calibration_mode", "privacy_aware")
        super().__init__(*args, **kwargs)
