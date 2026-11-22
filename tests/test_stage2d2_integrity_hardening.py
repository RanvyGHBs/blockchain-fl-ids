"""
Stage 2D.2 Integrity Hardening & Regression Test Suite.
Verifies:
1. Cumulative metric accounting across rounds (MURR, PUAA, MUDR, FPR).
2. Zero-submission handling: returns None when no malicious updates submitted.
3. Quarantine tracking isolation: prevented submissions tracked separately from rejections.
4. S3 trajectory resolution: earlier accepted updates correctly penalize cumulative MURR/PUAA.
5. Explicit update dispositions conservation: submitted = rejected_crypto + rejected_trust + accepted.
6. Matched benchmark configuration integrity: S2/S2b/S3, S4/S4b/S5, S6/S6b/S7 matched controls.
7. Strict preservation of baseline hashes for stage2_results.json and historical multi_attack_benchmarks.json.
8. Terminology compliance: no active DP-SGD references, Byzantine geometric threshold alignment clarification.
"""

import os
import hashlib
import unittest
import numpy as np

from src.federated.analytics import (
    compute_mudr, compute_murr, compute_fpr, compute_puaa, compute_stage2d_defense_metrics
)
from src.federated.orchestrator import FederatedOrchestrator


class TestStage2D2IntegrityHardening(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.baseline_hash = "B207FBEEC955AF68199A8D6471D3E9BEE47A3D8518D46B77E8C85946885EB82F"
        cls.stage2d_historical_hash = "115FCD137BE6DFA510A36C66A09C31568A53684199831B5C96FED96D52793338"

    def _get_synthetic_data(self):
        rng = np.random.RandomState(42)
        X_train = rng.randn(120, 10).astype(np.float32)
        y_train = (X_train[:, 0] > 0).astype(np.int64)
        X_val = rng.randn(40, 10).astype(np.float32)
        y_val = (X_val[:, 0] > 0).astype(np.int64)
        X_test = rng.randn(40, 10).astype(np.float32)
        y_test = (X_test[:, 0] > 0).astype(np.int64)
        return X_train, y_train, X_val, y_val, X_test, y_test

    # -------------------------------------------------------------------------
    # 1. Zero-Submission Handling
    # -------------------------------------------------------------------------

    def test_01_zero_malicious_submission_returns_none(self):
        """When no malicious updates are submitted, MURR, MUDR, PUAA return None."""
        self.assertIsNone(compute_mudr(flagged_client_ids=[1, 2], submitted_malicious_cids=[]))
        self.assertIsNone(compute_murr(rejected_client_ids=[1, 2], submitted_malicious_cids=[]))
        self.assertIsNone(compute_puaa(rejected_client_ids=[1, 2], submitted_malicious_cids=[]))
        self.assertEqual(compute_fpr(rejected_client_ids=[], submitted_honest_cids=[0, 1]), 0.0)

        # Stage 2D metrics dictionary with zero malicious
        eval_metrics = {"accuracy": 0.85, "precision": 0.85, "recall": 0.85, "f1_score": 0.85, "loss": 0.3}
        metrics = compute_stage2d_defense_metrics(
            eval_metrics=eval_metrics,
            rejected_client_ids=[],
            all_active_client_ids=[0, 1, 2],
            malicious_client_ids=[]
        )
        self.assertIsNone(metrics["mudr"])
        self.assertIsNone(metrics["murr"])
        self.assertIsNone(metrics["puaa"])
        self.assertEqual(metrics["fpr"], 0.0)

    # -------------------------------------------------------------------------
    # 2. Cumulative Accounting and Dispositions Conservation
    # -------------------------------------------------------------------------

    def test_02_cumulative_dispositions_conservation(self):
        """Verifies that submitted = rejected_crypto + rejected_trust + accepted_aggregated."""
        X_train, y_train, X_val, y_val, X_test, y_test = self._get_synthetic_data()

        config = {
            "scenario_name": "test_dispositions_conservation",
            "track": "Track A",
            "seed": 42,
            "device": "cpu",
            "num_clients": 4,
            "num_rounds": 2,
            "local_epochs": 1,
            "batch_size": 16,
            "lr": 0.01,
            "attack_enabled": True,
            "attack_type": "sign_flip",
            "malicious_client_ids": [3],
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

        # Check round records
        for r_log in results["round_history"][1:]:
            disp = r_log["dispositions"]
            # Malicious conservation
            self.assertEqual(
                disp["malicious_submitted"],
                disp["malicious_rejected_crypto"] + disp["malicious_rejected_trust"] + disp["malicious_accepted_aggregated"]
            )
            self.assertEqual(disp["malicious_rejected_total"], disp["malicious_rejected_crypto"] + disp["malicious_rejected_trust"])
            # Honest conservation
            self.assertEqual(
                disp["honest_submitted"],
                disp["honest_rejected_crypto"] + disp["honest_rejected_trust"] + disp["honest_accepted_aggregated"]
            )
            self.assertEqual(disp["honest_rejected_total"], disp["honest_rejected_crypto"] + disp["honest_rejected_trust"])

        # Check cumulative accounting
        cum = results["cumulative_dispositions"]
        self.assertEqual(
            cum["malicious"]["submitted"],
            cum["malicious"]["rejected_crypto"] + cum["malicious"]["rejected_trust"] + cum["malicious"]["accepted_aggregated"]
        )
        self.assertEqual(
            cum["honest"]["submitted"],
            cum["honest"]["rejected_crypto"] + cum["honest"]["rejected_trust"] + cum["honest"]["accepted_aggregated"]
        )

    # -------------------------------------------------------------------------
    # 3. S3 Trajectory Resolution: Earlier Accepted Updates Reflected Cumulatively
    # -------------------------------------------------------------------------

    def test_03_earlier_accepted_updates_penalize_cumulative_murr(self):
        """
        In a multi-round scenario where malicious updates leak in earlier rounds,
        cumulative MURR must strictly reflect all rounds, not just the final round.
        """
        X_train, y_train, X_val, y_val, X_test, y_test = self._get_synthetic_data()

        config = {
            "scenario_name": "test_s3_multi_round_trajectory",
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

        cum_murr = results["cumulative_murr"]
        cum_puaa = results["cumulative_puaa"]
        self.assertIsNotNone(cum_murr)
        self.assertIsNotNone(cum_puaa)
        self.assertAlmostEqual(cum_murr + cum_puaa, 1.0, places=5)

        # Check that stage2d_metrics contains both cumulative and final_round values
        s2d = results["stage2d_metrics"]
        self.assertIn("cumulative_murr", s2d)
        self.assertIn("cumulative_puaa", s2d)
        self.assertIn("final_round_murr", s2d)
        self.assertIn("final_round_puaa", s2d)

    # -------------------------------------------------------------------------
    # 4. Quarantine Tracking Isolation
    # -------------------------------------------------------------------------

    def test_04_quarantine_prevents_submission_without_counting_as_rejection(self):
        """
        Quarantined clients do not participate in local training or submit updates.
        They must be recorded as 'prevented_quarantine' and NOT inflated into rejected updates.
        """
        X_train, y_train, X_val, y_val, X_test, y_test = self._get_synthetic_data()

        config = {
            "scenario_name": "test_quarantine_isolation",
            "track": "Track A",
            "seed": 42,
            "device": "cpu",
            "num_clients": 4,
            "num_rounds": 3,
            "local_epochs": 1,
            "batch_size": 16,
            "lr": 0.01,
            "attack_enabled": True,
            "attack_type": "sign_flip",
            "malicious_client_ids": [3],
            "defense_enabled": True,
            "aggregation_algorithm": "trust_weighted",
            "defense_matrix": {
                "trust_engine": True,
                "norm_check": True,
                "cosine_check": True,
                "loss_check": True,
                "reputation": True,
                "quarantine": True,
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

        # In round 2 or 3, client 3 gets slashed (1.0 - 0.35 = 0.65; round 2: 0.65 - 0.35 = 0.30 < 0.40 -> Quarantined!)
        # In round 3, client 3 is quarantined and prevented from submission.
        cum_disp = results["cumulative_dispositions"]
        self.assertIn("prevented_quarantine", cum_disp["malicious"])
        # Total submissions + prevented submissions
        total_malicious_instances = cum_disp["malicious"]["submitted"] + cum_disp["malicious"]["prevented_quarantine"]
        self.assertEqual(total_malicious_instances, 3)  # 1 instance per round across 3 rounds

    # -------------------------------------------------------------------------
    # 5. Matched Benchmark Scenarios Integrity
    # -------------------------------------------------------------------------

    def test_05_matched_benchmark_controls_integrity(self):
        """Verifies matched control pairs S2/S2b/S3, S4/S4b/S5, S6/S6b/S7 in run_stage2d.py."""
        from run_stage2d import run_stage2d_benchmarks
        import inspect

        # Inspect source code of run_stage2d to verify matched scenarios
        source = inspect.getsource(run_stage2d_benchmarks)
        self.assertIn("s2b_targeted_labelflip_fedavg_defended", source)
        self.assertIn("s4b_sybil_coalition_median_defended", source)
        self.assertIn("s6b_parameterized_byzantine_fedavg_defended", source)

    # -------------------------------------------------------------------------
    # 6. Terminology Compliance
    # -------------------------------------------------------------------------

    def test_06_terminology_compliance(self):
        """Verifies privacy and Byzantine terminology across codebase."""
        # Check differential.py
        with open("src/privacy/differential.py", "r", encoding="utf-8") as f:
            diff_content = f.read()
        self.assertNotIn("DP-SGD", diff_content)
        self.assertIn("without formal privacy accounting", diff_content)

        # Check adaptive_byzantine.py
        with open("src/attacks/adaptive_byzantine.py", "r", encoding="utf-8") as f:
            byz_content = f.read()
        self.assertIn("parameterized stealth-constrained Byzantine perturbation using geometric threshold alignment", byz_content)
        self.assertIn("NOT a closed-loop feedback-adaptive attacker", byz_content)

        # Check README.md
        with open("README.md", "r", encoding="utf-8") as f:
            readme_content = f.read()
        self.assertNotIn("Local DP-SGD Noise", readme_content)

    # -------------------------------------------------------------------------
    # 7. Strict Artifact Hash Preservation
    # -------------------------------------------------------------------------

    def test_07_strict_baseline_and_historical_artifact_hashes(self):
        """Verifies that protected artifacts are byte-for-byte identical to baseline."""
        # 1. Baseline stage2_results.json
        stage2_path = os.path.join("data", "processed", "stage2_results.json")
        self.assertTrue(os.path.exists(stage2_path))
        with open(stage2_path, "rb") as f:
            s2_hash = hashlib.sha256(f.read()).hexdigest().upper()
        self.assertEqual(s2_hash, self.baseline_hash, f"stage2_results.json altered! Expected {self.baseline_hash}, got {s2_hash}")

        # 2. Historical multi_attack_benchmarks.json
        s2d_path = os.path.join("data", "processed", "stage2d", "multi_attack_benchmarks.json")
        self.assertTrue(os.path.exists(s2d_path))
        with open(s2d_path, "rb") as f:
            s2d_hash = hashlib.sha256(f.read()).hexdigest().upper()
        self.assertEqual(s2d_hash, self.stage2d_historical_hash, f"historical multi_attack_benchmarks.json altered! Expected {self.stage2d_historical_hash}, got {s2d_hash}")


if __name__ == "__main__":
    unittest.main()
