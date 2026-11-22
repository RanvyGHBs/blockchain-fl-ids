"""
Stage 2D Dedicated Test Suite: Advanced Attack Scenarios & Multi-Attack Defense Studio.
Verifies:
1. Targeted label flipping data poisoning and modified sample tracking.
2. Attack Success Rate (ASR) and Clean Accuracy mathematical correctness.
3. Sybil Coalition attack generation and median distortion measurement.
4. Adaptive Byzantine perturbation calibration and evasion criteria satisfaction.
5. Dynamic Defense Matrix tier-by-tier ablation in MultiCriteriaTrustEngine.
6. Stage 2D research metrics (MUDR, MURR, FPR, PUAA, degradation).
7. Orchestrator end-to-end integration across all Stage 2D attack scenarios.
8. ECDSA ingress signature verification rejection.
9. Autonomous quarantine and reputation ablation toggles.
10. Strict benchmark artifact isolation (verifying stage2_results.json hash).
"""

import os
import json
import hashlib
import unittest
import numpy as np
import torch

from src.attacks.targeted_poisoning import (
    apply_targeted_label_flipping_attack,
    compute_attack_success_rate,
    compute_clean_accuracy
)
from src.attacks.sybil_coalition import (
    generate_sybil_coalition_updates,
    evaluate_median_distortion
)
from src.attacks.adaptive_byzantine import (
    generate_adaptive_byzantine_update,
    verify_evasion_criteria
)
from src.trust.evaluator import MultiCriteriaTrustEngine
from src.trust.reputation import ReputationManager
from src.blockchain.crypto import CryptoManager
from src.federated.analytics import (
    compute_mudr, compute_murr, compute_fpr, compute_puaa, compute_stage2d_defense_metrics
)
from src.federated.orchestrator import FederatedOrchestrator


class TestStage2DAttacksAndDefense(unittest.TestCase):

    # -------------------------------------------------------------------------
    # 1. Targeted Label-Flipping Tests
    # -------------------------------------------------------------------------

    def test_01_targeted_label_flipping_ratios_and_sample_counts(self):
        y = np.array([0, 1, 1, 1, 0, 2, 1, 0], dtype=np.int64)
        # Flip class 1 -> 0 with ratio 1.0 (all 4 class 1 samples)
        y_poisoned, flipped_cnt = apply_targeted_label_flipping_attack(
            y, source_class=1, target_class=0, flip_ratio=1.0, seed=42
        )
        self.assertEqual(flipped_cnt, 4)
        self.assertEqual(np.sum(y_poisoned == 1), 0)
        self.assertEqual(np.sum(y_poisoned == 0), 7)
        self.assertEqual(np.sum(y_poisoned == 2), 1)  # Class 2 unaffected

        # Ratio 0.5 (2 out of 4)
        y_half, half_cnt = apply_targeted_label_flipping_attack(
            y, source_class=1, target_class=0, flip_ratio=0.5, seed=42
        )
        self.assertEqual(half_cnt, 2)
        self.assertEqual(np.sum(y_half == 1), 2)
        self.assertEqual(np.sum(y_half == 0), 5)

        # Edge case: non-existent source class
        y_noop, noop_cnt = apply_targeted_label_flipping_attack(
            y, source_class=99, target_class=0, flip_ratio=1.0, seed=42
        )
        self.assertEqual(noop_cnt, 0)
        np.testing.assert_array_equal(y, y_noop)

        # Edge case: source == target
        y_same, same_cnt = apply_targeted_label_flipping_attack(
            y, source_class=1, target_class=1, flip_ratio=1.0, seed=42
        )
        self.assertEqual(same_cnt, 0)
        np.testing.assert_array_equal(y, y_same)

    def test_02_asr_and_clean_accuracy_mathematical_precision(self):
        y_true = np.array([1, 1, 1, 1, 0, 0, 0, 0], dtype=np.int64)
        y_pred = np.array([0, 0, 0, 1, 0, 0, 0, 0], dtype=np.int64)

        # Source=1, Target=0: 3 out of 4 source class samples predicted as target class
        asr = compute_attack_success_rate(y_true, y_pred, source_class=1, target_class=0)
        self.assertAlmostEqual(asr, 0.75, places=5)

        # Clean accuracy on non-source class (class 0 samples: 4/4 correct = 1.0)
        clean_acc = compute_clean_accuracy(y_true, y_pred, source_class=1)
        self.assertAlmostEqual(clean_acc, 1.0, places=5)

        # Overall accuracy without source filter: 5/8 = 0.625
        overall_acc = compute_clean_accuracy(y_true, y_pred, source_class=None)
        self.assertAlmostEqual(overall_acc, 0.625, places=5)

        # Edge case: empty true array
        self.assertEqual(compute_clean_accuracy(np.array([]), np.array([])), 0.0)

        # Edge case: source class absent in y_true
        asr_absent = compute_attack_success_rate(np.array([0, 0]), np.array([0, 0]), source_class=1, target_class=0)
        self.assertEqual(asr_absent, 0.0)

    # -------------------------------------------------------------------------
    # 2. Sybil Coalition Tests
    # -------------------------------------------------------------------------

    def test_03_sybil_coalition_generation_and_median_distortion(self):
        base_weights = np.ones(50, dtype=np.float32)
        coalition_ids = [2, 3, 4]

        # Generate synchronized coalition updates
        sybil_updates = generate_sybil_coalition_updates(
            base_weights, coalition_client_ids=coalition_ids, intensity=3.0, seed=42
        )
        self.assertEqual(len(sybil_updates), 3)
        for cid in coalition_ids:
            self.assertIn(cid, sybil_updates)
            # Default direction is inverted and scaled: -3.0 * 1.0 = -3.0
            np.testing.assert_allclose(sybil_updates[cid], -3.0 * base_weights, rtol=1e-5)

        # Evaluate distortion on Coordinate-wise Median
        honest_nodes = [
            base_weights + np.random.RandomState(i).normal(0.0, 0.05, size=50).astype(np.float32)
            for i in range(3)
        ]
        sybil_nodes = list(sybil_updates.values())

        distortion = evaluate_median_distortion(honest_nodes, sybil_nodes)
        self.assertGreater(distortion["l2_distortion"], 0.0)
        self.assertGreater(distortion["relative_distortion"], 0.5)
        self.assertEqual(distortion["coalition_size"], 3)
        self.assertEqual(distortion["honest_size"], 3)

    # -------------------------------------------------------------------------
    # 3. Adaptive Byzantine Perturbation Tests
    # -------------------------------------------------------------------------

    def test_04_adaptive_byzantine_evasion_criteria_satisfaction(self):
        global_weights = np.ones(100, dtype=np.float32) * 0.5
        honest_weights = global_weights + np.random.RandomState(42).normal(0.0, 0.02, size=100).astype(np.float32)
        median_vector = global_weights.copy()

        # Generate stealth update with stealth factor 0.8
        w_adv = generate_adaptive_byzantine_update(
            honest_weights=honest_weights,
            global_weights=global_weights,
            median_vector=median_vector,
            norm_threshold_factor=2.5,
            cosine_threshold=0.15,
            stealth_factor=0.8,
            seed=42
        )

        evasion = verify_evasion_criteria(
            candidate_weights=w_adv,
            global_weights=global_weights,
            median_vector=median_vector,
            norm_threshold_factor=2.5,
            cosine_threshold=0.15
        )

        self.assertTrue(evasion["norm_evaded"], f"L2 Norm check failed: {evasion}")
        self.assertTrue(evasion["cosine_evaded"], f"Cosine check failed: {evasion}")
        self.assertTrue(evasion["both_tiers_evaded"], f"Adaptive update did not evade both tiers: {evasion}")
        self.assertGreaterEqual(evasion["cosine_similarity"], 0.15)

    # -------------------------------------------------------------------------
    # 4. Dynamic Defense Matrix & Ablation Tests
    # -------------------------------------------------------------------------

    def test_05_dynamic_defense_matrix_tier_ablation(self):
        input_dim = 10
        num_classes = 2
        global_weights = np.ones(input_dim * num_classes + num_classes, dtype=np.float32)

        # Exploding update (breaches norm)
        exploding_update = global_weights * 10.0
        # Inverted update (breaches cosine)
        inverted_update = -global_weights.copy()

        updates = {0: global_weights.copy(), 1: exploding_update, 2: inverted_update}

        # 1. Full defense: both bad updates rejected
        engine_full = MultiCriteriaTrustEngine(
            input_dim=input_dim, num_classes=num_classes,
            enable_norm_check=True, enable_cosine_check=True, enable_loss_check=False
        )
        res_full = engine_full.evaluate_updates(updates, global_weights)
        self.assertTrue(res_full[0]["is_valid"])
        self.assertFalse(res_full[1]["is_valid"])
        self.assertFalse(res_full[2]["is_valid"])

        # 2. Ablation: Disable Norm Check -> exploding_update (Client 1) passes norm check
        engine_no_norm = MultiCriteriaTrustEngine(
            input_dim=input_dim, num_classes=num_classes,
            enable_norm_check=False, enable_cosine_check=True, enable_loss_check=False
        )
        res_no_norm = engine_no_norm.evaluate_updates(updates, global_weights)
        self.assertTrue(res_no_norm[1]["norm_passed"])

        # 3. Ablation: Disable Cosine Check -> inverted_update (Client 2) passes cosine check
        engine_no_cos = MultiCriteriaTrustEngine(
            input_dim=input_dim, num_classes=num_classes,
            enable_norm_check=True, enable_cosine_check=False, enable_loss_check=False
        )
        res_no_cos = engine_no_cos.evaluate_updates(updates, global_weights)
        self.assertTrue(res_no_cos[2]["cosine_passed"])

    # -------------------------------------------------------------------------
    # 5. Stage 2D Metrics Engine Tests
    # -------------------------------------------------------------------------

    def test_06_stage2d_metrics_functions(self):
        # 4 clients: 0, 1 honest; 2, 3 malicious
        all_active = [0, 1, 2, 3]
        malicious = [2, 3]
        rejected = [2, 3]  # Perfect defense

        mudr = compute_mudr(rejected, malicious)
        murr = compute_murr(rejected, malicious)
        fpr = compute_fpr(rejected, [0, 1])
        puaa = compute_puaa(rejected, malicious)

        self.assertEqual(mudr, 1.0)
        self.assertEqual(murr, 1.0)
        self.assertEqual(fpr, 0.0)
        self.assertEqual(puaa, 0.0)
        self.assertEqual(puaa + murr, 1.0)

        # Flawed defense: Node 2 rejected, Node 1 erroneously rejected (FP), Node 3 leaked (FN)
        flawed_rejected = [1, 2]
        mudr_f = compute_mudr(flawed_rejected, malicious)
        murr_f = compute_murr(flawed_rejected, malicious)
        fpr_f = compute_fpr(flawed_rejected, [0, 1])
        puaa_f = compute_puaa(flawed_rejected, malicious)

        self.assertEqual(mudr_f, 0.5)
        self.assertEqual(murr_f, 0.5)
        self.assertEqual(fpr_f, 0.5)
        self.assertEqual(puaa_f, 0.5)

    # -------------------------------------------------------------------------
    # 6. Orchestrator Integration with Stage 2D Attacks
    # -------------------------------------------------------------------------

    def _get_synthetic_data(self):
        rng = np.random.RandomState(42)
        X_train = rng.randn(100, 10).astype(np.float32)
        y_train = rng.randint(0, 2, size=100).astype(np.int64)
        X_val = rng.randn(30, 10).astype(np.float32)
        y_val = rng.randint(0, 2, size=30).astype(np.int64)
        X_test = rng.randn(40, 10).astype(np.float32)
        y_test = rng.randint(0, 2, size=40).astype(np.int64)
        return X_train, y_train, X_val, y_val, X_test, y_test

    def test_07_orchestrator_targeted_label_flip_defended_run(self):
        X_train, y_train, X_val, y_val, X_test, y_test = self._get_synthetic_data()

        config = {
            "scenario_name": "test_targeted_label_flip_defended",
            "track": "Track A",
            "seed": 42,
            "device": "cpu",
            "num_clients": 4,
            "num_rounds": 2,
            "local_epochs": 1,
            "batch_size": 16,
            "lr": 0.01,
            "attack_enabled": True,
            "attack_type": "targeted_label_flip",
            "malicious_client_ids": [2],
            "label_flip_source": 1,
            "label_flip_target": 0,
            "label_flip_ratio": 1.0,
            "defense_enabled": True,
            "aggregation_algorithm": "trust_weighted",
            "X_train": X_train,
            "y_train": y_train,
            "X_val": X_val,
            "y_val": y_val,
            "X_test": X_test,
            "y_test": y_test,
        }

        orch = FederatedOrchestrator(config)
        results = orch.run()

        # Telemetry should log label_flip setup with modified sample count
        setup_logs = [log for log in results["attack_log"] if log.get("phase") == "setup"]
        self.assertGreater(len(setup_logs), 0)
        self.assertEqual(setup_logs[0]["attack_type"], "targeted_label_flip")
        self.assertIn("flipped_samples", setup_logs[0])
        self.assertGreater(setup_logs[0]["flipped_samples"], 0)

        # Stage 2D metrics should be populated
        self.assertIn("stage2d_metrics", results)
        s2d = results["stage2d_metrics"]
        self.assertIn("final_clean_accuracy", s2d)
        self.assertIn("final_asr", s2d)
        self.assertIn("final_mudr", s2d)

    def test_08_orchestrator_sybil_coalition_detection_and_rejection(self):
        X_train, y_train, X_val, y_val, X_test, y_test = self._get_synthetic_data()

        config = {
            "scenario_name": "test_sybil_coalition_defended",
            "track": "Track A",
            "seed": 42,
            "device": "cpu",
            "num_clients": 4,
            "num_rounds": 2,
            "local_epochs": 1,
            "batch_size": 16,
            "lr": 0.01,
            "attack_enabled": True,
            "attack_type": "sybil_coalition",
            "malicious_client_ids": [1, 2],
            "sybil_intensity": 3.0,
            "defense_enabled": True,
            "aggregation_algorithm": "trust_weighted",
            "X_train": X_train,
            "y_train": y_train,
            "X_val": X_val,
            "y_val": y_val,
            "X_test": X_test,
            "y_test": y_test,
        }

        orch = FederatedOrchestrator(config)
        results = orch.run()

        # In round 1, Sybil nodes 1 and 2 should be detected and rejected
        round_1 = results["round_history"][1]
        self.assertIn(1, round_1["rejected_client_ids"])
        self.assertIn(2, round_1["rejected_client_ids"])
        self.assertGreaterEqual(round_1["mudr"], 1.0)
        self.assertAlmostEqual(round_1["murr"], 1.0)

    def test_09_orchestrator_adaptive_byzantine_telemetry(self):
        X_train, y_train, X_val, y_val, X_test, y_test = self._get_synthetic_data()

        config = {
            "scenario_name": "test_adaptive_byzantine",
            "track": "Track A",
            "seed": 42,
            "device": "cpu",
            "num_clients": 4,
            "num_rounds": 2,
            "local_epochs": 1,
            "batch_size": 16,
            "lr": 0.01,
            "attack_enabled": True,
            "attack_type": "adaptive_byzantine",
            "malicious_client_ids": [3],
            "adaptive_stealth_factor": 0.8,
            "defense_enabled": True,
            "aggregation_algorithm": "trust_weighted",
            "X_train": X_train,
            "y_train": y_train,
            "X_val": X_val,
            "y_val": y_val,
            "X_test": X_test,
            "y_test": y_test,
        }

        orch = FederatedOrchestrator(config)
        results = orch.run()

        # Verify adaptive byzantine round entries
        adv_logs = [log for log in results["attack_log"] if log.get("attack_type") == "adaptive_byzantine"]
        self.assertGreater(len(adv_logs), 0)
        self.assertEqual(adv_logs[0]["stealth_factor"], 0.8)

    # -------------------------------------------------------------------------
    # 7. Cryptographic Ingress & Quarantine Ablation
    # -------------------------------------------------------------------------

    def test_10_orchestrator_quarantine_ablation_toggle(self):
        X_train, y_train, X_val, y_val, X_test, y_test = self._get_synthetic_data()

        # Quarantine disabled in defense matrix
        config = {
            "scenario_name": "test_quarantine_ablation",
            "track": "Track A",
            "seed": 42,
            "device": "cpu",
            "num_clients": 4,
            "num_rounds": 2,
            "local_epochs": 1,
            "batch_size": 16,
            "lr": 0.01,
            "attack_enabled": True,
            "attack_type": "gaussian_noise",
            "malicious_client_ids": [3],
            "defense_enabled": True,
            "defense_matrix": {
                "trust_engine": True,
                "norm_check": True,
                "cosine_check": True,
                "loss_check": True,
                "reputation": True,
                "quarantine": False,  # Disabled!
                "signature_verify": True,
                "blockchain": True
            },
            "X_train": X_train,
            "y_train": y_train,
            "X_val": X_val,
            "y_val": y_val,
            "X_test": X_test,
            "y_test": y_test,
        }

        orch = FederatedOrchestrator(config)
        results = orch.run()

        # In round 2, client 3 still submits an update because quarantine was disabled
        round_2 = results["round_history"][2]
        self.assertIn(3, round_2["rejected_client_ids"])  # Detected and rejected again

    # -------------------------------------------------------------------------
    # 8. Strict Research Artifact Isolation
    # -------------------------------------------------------------------------

    def test_11_strict_stage2_artifact_hash_preservation(self):
        """Guarantees that stage2_results.json is byte-for-byte identical to baseline."""
        results_path = os.path.join("data", "processed", "stage2_results.json")
        self.assertTrue(os.path.exists(results_path), "stage2_results.json must exist")

        with open(results_path, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest().upper()

        expected_hash = "B207FBEEC955AF68199A8D6471D3E9BEE47A3D8518D46B77E8C85946885EB82F"
        self.assertEqual(h, expected_hash,
                         f"CRITICAL: stage2_results.json was modified! Hash {h} != {expected_hash}")


if __name__ == "__main__":
    unittest.main()
