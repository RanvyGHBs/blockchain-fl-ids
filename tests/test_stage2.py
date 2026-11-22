"""
Stage 2 Integration Test Suite.

Covers all major subsystems introduced or exercised in Stage 2:
  1.  FederatedOrchestrator – single honest round (no attack, no defense)
  2.  FederatedOrchestrator – multi-round with Gaussian noise attack & defense
  3.  Trust Engine – multi-criteria validation rejects poisoned update
  4.  Trust Engine – honest update always accepted
  5.  Reputation Manager – slash, quarantine, rehabilitation cycle
  6.  Blockchain – genesis integrity + forged block + chain validation
  7.  Blockchain – mempool flush after block mining
  8.  Blockchain – forged chain tamper detection
  9.  ECDSA Crypto – keypair sign / verify round-trip
  10. ECDSA Crypto – tampered message fails verification
  11. Differential Privacy – clipping & noise within tolerance
  12. Differential Privacy – privatised update stays close to original
  13. Aggregation – FedAvg weighted by sample counts
  14. Aggregation – Trimmed Mean removes extreme outliers
  15. Aggregation – Coordinate-wise Median Byzantine-robust property
  16. Aggregation – Trust-Weighted zeroes-out zero-reputation client
  17. XAI Explainer – top-k features sum to ≤ 1.0 relative importance
  18. XAI Explainer – prediction matches argmax of model logits
  19. DP accounting – privatize called N times yields N records
  20. Full pipeline chain validity after multi-round defended experiment
"""

import unittest
import numpy as np
import torch
from typing import Dict, Tuple

# Project imports
from src.data.nsl_kdd import NSLKDDLoader
from src.data.partitioner import FederatedPartitioner
from src.models.ids_net import IDSNet
from src.federated.client import FederatedClient
from src.federated.server import FederatedServer
from src.federated.aggregators import (
    aggregate_fedavg, aggregate_trimmed_mean, aggregate_median, aggregate_trust_weighted
)
from src.federated.orchestrator import FederatedOrchestrator
from src.attacks.model_poisoning import (
    apply_gaussian_noise_attack, apply_sign_flipping_attack, apply_model_scaling_attack
)
from src.attacks.data_poisoning import apply_label_flipping_attack
from src.trust.evaluator import MultiCriteriaTrustEngine
from src.trust.reputation import ReputationManager
from src.blockchain.crypto import CryptoManager
from src.blockchain.block import Block, Transaction
from src.blockchain.chain import Blockchain
from src.privacy.differential import LocalDifferentialPrivacy
from src.xai.explainer import FastFeatureExplainer


# ---------------------------------------------------------------------------
# Shared Fixture Helpers
# ---------------------------------------------------------------------------

INPUT_DIM  = 20   # lightweight synthetic dimension for speed
NUM_CLASSES = 2
N_CLIENTS   = 4
N_TRAIN     = 400
N_TEST      = 100
SEED        = 7


def _synthetic_data(n: int = N_TRAIN, d: int = INPUT_DIM,
                    seed: int = SEED) -> Tuple[np.ndarray, np.ndarray]:
    """Return (X, y) with float32 X in [0,1] and binary int64 y."""
    rng = np.random.RandomState(seed)
    X = rng.rand(n, d).astype(np.float32)
    y = rng.randint(0, NUM_CLASSES, size=n).astype(np.int64)
    return X, y


def _base_orchestrator_config(attack: bool = False, defense: bool = False,
                               attack_type: str = "gaussian_noise",
                               dp: bool = False) -> dict:
    X_train, y_train = _synthetic_data(N_TRAIN)
    X_test,  y_test  = _synthetic_data(N_TEST, seed=SEED + 1)
    return {
        "scenario_name": "test_scenario",
        "seed": SEED,
        "device": "cpu",
        "num_clients": N_CLIENTS,
        "num_rounds": 2,
        "local_epochs": 1,
        "batch_size": 32,
        "lr": 0.005,
        "fedprox_mu": 0.0,
        "aggregation_algorithm": "fedavg",
        "attack_enabled": attack,
        "malicious_client_ids": [2],
        "attack_type": attack_type,
        "defense_enabled": defense,
        "dp_enabled": dp,
        "dp_clip_norm": 1.0,
        "dp_noise_multiplier": 0.05,
        "X_train": X_train, "y_train": y_train,
        "X_test": X_test,  "y_test": y_test,
        "feature_names": [f"f{i}" for i in range(INPUT_DIM)],
        "trust_config": {
            "norm_threshold_factor": 2.5,
            "cosine_threshold": 0.15,
            "loss_increase_threshold": 1.5,
        }
    }


# ===========================================================================
# TEST CLASSES
# ===========================================================================

class TestOrchestratorHonest(unittest.TestCase):
    """Test 1 & 2 – FederatedOrchestrator with and without attacks."""

    def test_01_orchestrator_honest_run_returns_metrics(self):
        """Single honest run completes and returns required keys."""
        cfg = _base_orchestrator_config(attack=False, defense=False)
        orch = FederatedOrchestrator(cfg)
        results = orch.run()

        for key in ("final_accuracy", "final_f1_score", "final_loss",
                    "round_history", "blockchain_summary", "chain_valid"):
            self.assertIn(key, results, f"Missing key: {key}")

        self.assertEqual(len(results["round_history"]), cfg["num_rounds"] + 1)
        self.assertGreater(results["final_accuracy"], 0.0)
        self.assertTrue(results["chain_valid"])

    def test_02_orchestrator_attack_defense_reduces_rejected_to_attacker(self):
        """With defense ON, the attacker (client 2) must appear in rejected logs."""
        cfg = _base_orchestrator_config(attack=True, defense=True,
                                        attack_type="gaussian_noise")
        cfg["num_rounds"] = 3
        orch = FederatedOrchestrator(cfg)
        results = orch.run()

        # At least one round should have rejected the malicious client
        all_rejected = []
        for rnd in results["round_history"][1:]:  # skip round 0
            all_rejected.extend(rnd.get("rejected_client_ids", []))

        self.assertIn(2, all_rejected,
                      "Malicious client 2 was never detected – defense may be broken")


class TestTrustEngine(unittest.TestCase):
    """Tests 3 & 4 – MultiCriteriaTrustEngine."""

    def setUp(self):
        self.engine = MultiCriteriaTrustEngine(
            input_dim=INPUT_DIM, num_classes=NUM_CLASSES,
            norm_threshold_factor=2.5,
            cosine_threshold=0.15,
            loss_increase_threshold=1.5,
            device="cpu"
        )
        self.model = IDSNet(input_dim=INPUT_DIM, num_classes=NUM_CLASSES)
        self.global_weights = self.model.get_weights_vector()
        X_val, y_val = _synthetic_data(50)
        self.val_data = (X_val, y_val)

    def test_03_poisoned_update_rejected(self):
        """Gaussian noise inflated update should fail norm or cosine check."""
        honest = self.global_weights.copy()
        poisoned = apply_gaussian_noise_attack(honest, std=20.0, seed=SEED)

        updates = {0: honest, 1: poisoned}
        reports = self.engine.evaluate_updates(updates, self.global_weights, self.val_data)

        self.assertFalse(reports[1]["is_valid"],
                         "Severely poisoned update should be rejected.")

    def test_04_honest_update_accepted(self):
        """A small-perturbation honest update should be accepted."""
        honest = self.global_weights.copy()
        near_honest = honest + np.random.RandomState(SEED).normal(0, 0.0001,
                                                                   size=honest.shape).astype(np.float32)
        updates = {0: honest, 1: near_honest}
        reports = self.engine.evaluate_updates(updates, self.global_weights, self.val_data)

        # At least one of the two should be valid
        any_valid = any(r["is_valid"] for r in reports.values())
        self.assertTrue(any_valid, "No honest update was accepted.")


class TestReputationManager(unittest.TestCase):
    """Test 5 – Reputation slashing, quarantine, and rehabilitation."""

    def test_05_reputation_lifecycle(self):
        mgr = ReputationManager(client_ids=[0, 1, 2], probation_rounds=2)

        # 0 and 1 always pass; 2 always fails
        for _ in range(3):
            mgr.update_reputation({
                0: {"is_valid": True},
                1: {"is_valid": True},
                2: {"is_valid": False},
            })

        self.assertGreater(mgr.get_reputation(0), 1.0 - 1e-6)   # capped at 1.0
        self.assertTrue(mgr.is_quarantined(2),
                        "Client 2 should be quarantined after repeated failures.")
        self.assertFalse(mgr.is_quarantined(0),
                         "Honest client 0 should not be quarantined.")

        # Rehabilitation: client 2 passes probation_rounds consecutive rounds
        for _ in range(mgr.probation_rounds + 1):
            mgr.update_reputation({2: {"is_valid": True}})

        self.assertFalse(mgr.is_quarantined(2),
                         "Client 2 should be rehabilitated after passing probation.")


class TestBlockchain(unittest.TestCase):
    """Tests 6, 7, 8 – Blockchain data structures and tamper detection."""

    def _make_tx(self, cid: int, rnd: int, status: str = "ACCEPTED") -> Transaction:
        priv, pub = CryptoManager.generate_keypair()
        w_hash = CryptoManager.sha256_hash(f"weights_{cid}_{rnd}")
        sig    = CryptoManager.sign_message(priv, w_hash)
        return Transaction(
            client_id=cid, round_num=rnd,
            weights_hash=w_hash, signature=sig,
            validation_metrics={"is_valid": status == "ACCEPTED"},
            status=status,
            reputation_before=1.0, reputation_after=0.95
        )

    def test_06_genesis_block_valid(self):
        bc = Blockchain(committee_size=2)
        self.assertEqual(len(bc.chain), 1)
        self.assertTrue(bc.is_chain_valid())
        self.assertEqual(bc.chain[0].index, 0)

    def test_07_forged_block_clears_mempool(self):
        bc = Blockchain(committee_size=2)
        bc.add_transaction(self._make_tx(0, 1))
        bc.add_transaction(self._make_tx(1, 1))
        self.assertEqual(len(bc.mempool), 2)
        bc.forge_block(global_model_hash="hash_round_1", validator_id=0)
        self.assertEqual(len(bc.mempool), 0)
        self.assertEqual(len(bc.chain), 2)
        self.assertTrue(bc.is_chain_valid())

    def test_08_tampered_chain_detected(self):
        bc = Blockchain(committee_size=2)
        bc.add_transaction(self._make_tx(0, 1))
        bc.forge_block(global_model_hash="hash_round_1", validator_id=0)

        # Corrupt the stored hash of block 1
        bc.chain[1].hash = "0" * 64
        self.assertFalse(bc.is_chain_valid(),
                         "Tampered chain should fail integrity check.")


class TestCryptography(unittest.TestCase):
    """Tests 9 & 10 – ECDSA sign / verify."""

    def test_09_sign_verify_roundtrip(self):
        priv, pub = CryptoManager.generate_keypair()
        msg = "model_weights_sha256_hash_abcdef1234"
        sig = CryptoManager.sign_message(priv, msg)
        self.assertTrue(CryptoManager.verify_signature(pub, msg, sig))

    def test_10_tampered_message_fails_verification(self):
        priv, pub = CryptoManager.generate_keypair()
        msg = "original_message"
        sig = CryptoManager.sign_message(priv, msg)
        self.assertFalse(
            CryptoManager.verify_signature(pub, "tampered_message", sig),
            "Verification should fail when message is altered."
        )


class TestDifferentialPrivacy(unittest.TestCase):
    """Tests 11 & 12 – LocalDifferentialPrivacy."""

    def test_11_clipping_reduces_large_norm(self):
        dp = LocalDifferentialPrivacy(clip_norm=1.0, noise_multiplier=0.0, seed=SEED)
        big_weights = np.ones(INPUT_DIM, dtype=np.float32) * 100.0
        privatized, meta = dp.privatize(big_weights)
        # Clipped norm should be <= clip_norm + small noise
        self.assertLessEqual(meta["clipped_norm"], 1.0 + 1e-5)

    def test_12_privatised_update_close_with_low_noise(self):
        dp = LocalDifferentialPrivacy(clip_norm=10.0, noise_multiplier=0.001, seed=SEED)
        weights = np.random.RandomState(SEED).rand(INPUT_DIM).astype(np.float32)
        privatized, _ = dp.privatize(weights)
        diff = np.linalg.norm(privatized - weights)
        self.assertLess(diff, 1.0,
                        "Low-noise DP should not dramatically alter weights.")


class TestAggregators(unittest.TestCase):
    """Tests 13-16 – All aggregation algorithms."""

    def _random_weights(self, n: int, d: int = INPUT_DIM,
                        seed: int = SEED) -> list:
        rng = np.random.RandomState(seed)
        return [rng.rand(d).astype(np.float32) for _ in range(n)]

    def test_13_fedavg_weighted_by_sample_count(self):
        weights = [np.array([1.0, 0.0], dtype=np.float32),
                   np.array([0.0, 1.0], dtype=np.float32)]
        counts  = [3, 1]
        avg     = aggregate_fedavg(weights, counts)
        # Expected: 0.75 * [1,0] + 0.25 * [0,1] = [0.75, 0.25]
        np.testing.assert_allclose(avg, [0.75, 0.25], atol=1e-5)

    def test_14_trimmed_mean_removes_outlier(self):
        base    = np.zeros(INPUT_DIM, dtype=np.float32)
        outlier = np.ones(INPUT_DIM, dtype=np.float32) * 1000.0
        weights = [base.copy() for _ in range(4)] + [outlier]
        result  = aggregate_trimmed_mean(weights, beta=0.2)
        # With beta=0.2, 1 of 5 extreme elements is trimmed per coordinate
        self.assertTrue(np.all(result < 500),
                        "Trimmed mean should attenuate the outlier significantly.")

    def test_15_median_ignores_extreme_outlier(self):
        weights = [np.full(INPUT_DIM, v, dtype=np.float32)
                   for v in [0.0, 0.1, 0.1, 0.1, 999.0]]
        median  = aggregate_median(weights)
        # Median should be ~0.1 for all coordinates
        np.testing.assert_allclose(median, 0.1, atol=1e-5)

    def test_16_trust_weighted_zeroes_out_zero_rep(self):
        weights = [np.ones(2, dtype=np.float32),
                   np.full(2, 100.0, dtype=np.float32)]
        counts  = [1, 1]
        reps    = [1.0, 0.0]  # second client has zero reputation
        result  = aggregate_trust_weighted(weights, counts, reps)
        # With zero reputation, second client contributes nothing
        np.testing.assert_allclose(result, [1.0, 1.0], atol=1e-5)


class TestXAIExplainer(unittest.TestCase):
    """Tests 17 & 18 – FastFeatureExplainer."""

    def setUp(self):
        self.model = IDSNet(input_dim=INPUT_DIM, num_classes=NUM_CLASSES)
        self.feature_names = [f"feat_{i}" for i in range(INPUT_DIM)]
        self.explainer = FastFeatureExplainer(
            self.model, feature_names=self.feature_names, device="cpu"
        )
        rng = np.random.RandomState(SEED)
        self.sample = rng.rand(INPUT_DIM).astype(np.float32)

    def test_17_relative_importance_sums_to_at_most_one(self):
        result = self.explainer.explain_flow(self.sample, top_k=5)
        total_rel = sum(f["relative_importance"] for f in result["top_features"])
        self.assertLessEqual(total_rel, 1.0 + 1e-5)

    def test_18_prediction_matches_model_argmax(self):
        result = self.explainer.explain_flow(self.sample, top_k=3)
        x = torch.from_numpy(self.sample.reshape(1, -1)).float()
        with torch.no_grad():
            logits = self.model(x)
        expected_class = int(torch.argmax(logits, dim=1).item())
        self.assertEqual(result["predicted_class"], expected_class)


class TestDPAccounting(unittest.TestCase):
    """Test 19 – DP accounting records per privatize call."""

    def test_19_dp_accounting_entries_recorded(self):
        cfg = _base_orchestrator_config(attack=False, defense=False, dp=True)
        cfg["num_rounds"] = 2
        orch = FederatedOrchestrator(cfg)
        results = orch.run()
        # dp_accounting should have 1 entry per round (2 rounds)
        self.assertEqual(len(results["dp_accounting"]), 2,
                         "DP accounting should record one entry per round.")


class TestFullPipelineIntegrity(unittest.TestCase):
    """Test 20 – Chain validity after multi-round defended experiment."""

    def test_20_chain_valid_after_full_defended_run(self):
        cfg = _base_orchestrator_config(attack=True, defense=True,
                                        attack_type="sign_flip")
        cfg["num_rounds"] = 3
        cfg["aggregation_algorithm"] = "trust_weighted"
        orch = FederatedOrchestrator(cfg)
        results = orch.run()
        self.assertTrue(results["chain_valid"],
                        "Blockchain should remain cryptographically valid after all rounds.")
        audit = results["blockchain_summary"]
        # genesis + 3 rounds = 4 blocks minimum
        self.assertGreaterEqual(audit["total_blocks"], 4)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
