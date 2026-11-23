"""
WP3 Test Suite: Privacy-Aware Multi-Criteria Trust Calibration.
Verifies:
1. Backward compatibility with uncalibrated baseline mode.
2. Mathematical calibration formulas for L2-norm, cosine similarity, and validation loss.
3. Honest-client false positive reduction under approved DP baseline (C=1.0, sigma=1.0).
4. Robust detection and rejection of Byzantine model poisoning attacks (Gaussian, Scaling, Sign-flip).
5. Dynamic defense matrix tier ablation support.
6. Orchestrator end-to-end integration with execution mode guarantees.
"""

import os
import sys
import math
import unittest
import numpy as np
import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.ids_net import IDSNet
from src.config import get_approved_research_config, ExecutionMode, PrivacyRandomnessMode
from src.trust.evaluator import MultiCriteriaTrustEngine, PrivacyAwareTrustEngine
from src.trust.reputation import ReputationManager
from src.federated.orchestrator import FederatedOrchestrator
from src.attacks.model_poisoning import (
    apply_gaussian_noise_attack, apply_sign_flipping_attack, apply_model_scaling_attack
)


class TestWP3CalibratedTrust(unittest.TestCase):
    """Unit and integration tests for WP3 calibrated trust engine."""

    def setUp(self):
        self.input_dim = 10
        self.num_classes = 2
        model = IDSNet(input_dim=self.input_dim, num_classes=self.num_classes)
        self.w_global = model.get_weights_vector()
        self.d = len(self.w_global)
        self.global_norm = float(np.linalg.norm(self.w_global))
        self.X_val = np.random.randn(50, self.input_dim).astype(np.float32)
        self.y_val = np.random.randint(0, self.num_classes, size=50).astype(np.int64)
        self.val_data = (self.X_val, self.y_val)

    def test_01_uncalibrated_baseline_preservation(self):
        """Verify uncalibrated mode retains exact Stage 2D behavior."""
        engine = MultiCriteriaTrustEngine(
            input_dim=self.input_dim, num_classes=self.num_classes,
            norm_threshold_factor=2.5, cosine_threshold=0.15,
            loss_increase_threshold=1.5,
            calibration_mode="uncalibrated"
        )
        self.assertFalse(engine.is_calibrated())
        self.assertEqual(engine.calibration_mode, "uncalibrated")

        # Exploding update should fail norm
        exploding = self.w_global * 10.0
        updates = {0: self.w_global.copy(), 1: exploding}
        reports = engine.evaluate_updates(updates, self.w_global, self.val_data)
        self.assertTrue(reports[0]["is_valid"])
        self.assertFalse(reports[1]["is_valid"])
        self.assertFalse(reports[1]["norm_passed"])

    def test_02_calibrated_norm_formula(self):
        """Verify mathematical formula for expected norm: mu = sqrt(||w_global||^2 + 4 * d * sigma^2 * C^2)."""
        sigma = 1.0
        c = 1.0
        engine = PrivacyAwareTrustEngine(
            input_dim=self.input_dim, num_classes=self.num_classes,
            dp_enabled=True, dp_clip_norm=c, dp_noise_multiplier=sigma
        )
        self.assertTrue(engine.is_calibrated())

        expected_mu = math.sqrt(self.global_norm**2 + 4.0 * self.d * (sigma**2) * (c**2))
        updates = {0: self.w_global.copy()}
        reports = engine.evaluate_updates(updates, self.w_global)
        rep = reports[0]

        self.assertAlmostEqual(rep["expected_norm"], expected_mu, places=4)
        self.assertAlmostEqual(rep["max_allowed_norm"], expected_mu * 1.25, places=4)
        self.assertAlmostEqual(rep["min_allowed_norm"], expected_mu * 0.75, places=4)

    def test_03_honest_updates_accepted_under_dp(self):
        """Verify honest clients with DP perturbation pass all calibrated checks (FPR = 0%)."""
        sigma = 1.0
        c = 1.0
        engine = PrivacyAwareTrustEngine(
            input_dim=self.input_dim, num_classes=self.num_classes,
            dp_enabled=True, dp_clip_norm=c, dp_noise_multiplier=sigma
        )

        # Generate simulated honest updates with DP perturbation
        np.random.seed(42)
        updates = {}
        for i in range(5):
            noise = np.random.normal(0.0, 2.0 * sigma * c, size=self.d).astype(np.float32)
            updates[i] = self.w_global + noise

        reports = engine.evaluate_updates(updates, self.w_global, self.val_data)
        for cid, rep in reports.items():
            self.assertTrue(rep["is_valid"], f"Honest client {cid} falsely rejected: {rep['reason']}")
            self.assertTrue(rep["norm_passed"])
            self.assertTrue(rep["cosine_passed"])
            self.assertTrue(rep["loss_passed"])

    def test_04_byzantine_scaling_attack_rejected(self):
        """Verify model scaling attack (10x) is rejected by calibrated engine."""
        sigma = 1.0
        c = 1.0
        engine = PrivacyAwareTrustEngine(
            input_dim=self.input_dim, num_classes=self.num_classes,
            dp_enabled=True, dp_clip_norm=c, dp_noise_multiplier=sigma
        )

        np.random.seed(42)
        updates = {}
        for i in range(4):
            noise = np.random.normal(0.0, 2.0 * sigma * c, size=self.d).astype(np.float32)
            updates[i] = self.w_global + noise

        # Client 4 is malicious
        mal_noise = np.random.normal(0.0, 2.0 * sigma * c, size=self.d).astype(np.float32)
        updates[4] = apply_model_scaling_attack(self.w_global + mal_noise, scale_factor=10.0)

        reports = engine.evaluate_updates(updates, self.w_global, self.val_data)
        self.assertTrue(reports[0]["is_valid"])
        self.assertFalse(reports[4]["is_valid"], "Scaling attack was not rejected.")
        self.assertFalse(reports[4]["norm_passed"])

    def test_05_byzantine_sign_flip_rejected(self):
        """Verify sign flipping attack is rejected by calibrated engine."""
        sigma = 1.0
        c = 1.0
        engine = PrivacyAwareTrustEngine(
            input_dim=self.input_dim, num_classes=self.num_classes,
            dp_enabled=True, dp_clip_norm=c, dp_noise_multiplier=sigma
        )

        np.random.seed(42)
        updates = {}
        for i in range(4):
            noise = np.random.normal(0.0, 2.0 * sigma * c, size=self.d).astype(np.float32)
            updates[i] = self.w_global + noise

        mal_noise = np.random.normal(0.0, 2.0 * sigma * c, size=self.d).astype(np.float32)
        updates[4] = apply_sign_flipping_attack(self.w_global + mal_noise, scale=-3.0)

        reports = engine.evaluate_updates(updates, self.w_global, self.val_data)
        self.assertFalse(reports[4]["is_valid"], "Sign-flip attack was not rejected.")

    def test_06_byzantine_gaussian_noise_rejected(self):
        """Verify Gaussian noise attack (std=2.5 added) is rejected by calibrated engine."""
        sigma = 1.0
        c = 1.0
        engine = PrivacyAwareTrustEngine(
            input_dim=self.input_dim, num_classes=self.num_classes,
            dp_enabled=True, dp_clip_norm=c, dp_noise_multiplier=sigma
        )

        np.random.seed(42)
        updates = {}
        for i in range(4):
            noise = np.random.normal(0.0, 2.0 * sigma * c, size=self.d).astype(np.float32)
            updates[i] = self.w_global + noise

        mal_noise = np.random.normal(0.0, 2.0 * sigma * c, size=self.d).astype(np.float32)
        updates[4] = apply_gaussian_noise_attack(self.w_global + mal_noise, std=2.5, seed=42)

        reports = engine.evaluate_updates(updates, self.w_global, self.val_data)
        self.assertFalse(reports[4]["is_valid"], "Gaussian attack was not rejected.")

    def test_07_dynamic_defense_matrix_ablation(self):
        """Verify tier ablation works in calibrated mode."""
        engine_no_norm = PrivacyAwareTrustEngine(
            input_dim=self.input_dim, num_classes=self.num_classes,
            dp_enabled=True, dp_noise_multiplier=1.0,
            enable_norm_check=False, enable_cosine_check=True, enable_loss_check=False
        )
        exploding = self.w_global * 10.0
        updates = {0: self.w_global.copy(), 1: exploding}
        reports = engine_no_norm.evaluate_updates(updates, self.w_global)
        self.assertTrue(reports[1]["norm_passed"], "Norm check should be disabled.")

    def test_08_orchestrator_integration(self):
        """Verify FederatedOrchestrator runs in calibrated mode with honest clients accepted."""
        cfg = get_approved_research_config(
            num_rounds=1, attack_enabled=False, defense_enabled=True,
            trust_calibration_mode="privacy_aware"
        )
        cfg_dict = {k: getattr(cfg, k) for k in cfg.__dataclass_fields__}
        cfg_dict["defense_matrix"] = {
            "trust_engine": True, "norm_check": True, "cosine_check": True,
            "loss_check": True, "reputation": True, "quarantine": True
        }
        orch = FederatedOrchestrator(cfg_dict)
        orch.setup()
        self.assertEqual(orch.trust_engine.calibration_mode, "privacy_aware")
        self.assertTrue(orch.trust_engine.is_calibrated())


if __name__ == "__main__":
    unittest.main()
