"""
Unit Tests for Stage 2E WP4: Computational Overhead & Blockchain Audit Evaluation.
Verifies:
1. OverheadProfiler timing instrumentation and statistical summaries.
2. Communication payload byte measurements.
3. AuditVerifier validation on pristine chains.
4. Deterministic detection across all 5 synthetic tampering categories.
5. Zero false alarms on pristine negative controls (observed FPR = 0).
6. Non-repudiation and signature verification.
"""

import copy
import hashlib
import numpy as np
import pytest

from src.blockchain.block import Block, Transaction
from src.blockchain.chain import Blockchain
from src.blockchain.crypto import CryptoManager
from src.blockchain.audit_verifier import AuditVerifier, SyntheticTamperSuite
from src.evaluation.overhead_profiler import OverheadProfiler


class TestWP4OverheadAndAudit:

    @pytest.fixture
    def sample_pristine_blockchain(self):
        """Creates a valid 4-block blockchain with transactions for audit testing."""
        priv_k, pub_k = CryptoManager.generate_keypair()
        bc = Blockchain(committee_size=3)

        for round_num in range(1, 4):
            sample_hash = hashlib.sha256(f"weights_round_{round_num}".encode("utf-8")).hexdigest()
            sig = CryptoManager.sign_message(priv_k, sample_hash)
            tx = Transaction(
                client_id=0,
                round_num=round_num,
                weights_hash=sample_hash,
                signature=sig,
                validation_metrics={"norm_passed": True, "cos_sim": 0.95},
                status="ACCEPTED",
                reputation_before=1.0,
                reputation_after=1.05
            )
            bc.add_transaction(tx)
            bc.forge_block(global_model_hash=sample_hash, validator_id=0)

        return bc, {0: pub_k}

    def test_audit_verifier_pristine_chain_passes(self, sample_pristine_blockchain):
        """Verifies that an uncorrupted blockchain passes all audit checks with zero violations."""
        bc, pub_keys = sample_pristine_blockchain
        verifier = AuditVerifier(public_keys=pub_keys)

        result = verifier.verify_chain(bc, verify_signatures=True)
        assert result["is_valid"] is True
        assert len(result["violations"]) == 0
        assert result["corrupted_block_index"] is None
        assert result["failure_category"] is None
        assert result["total_blocks"] == 4
        assert result["total_transactions"] == 3
        assert result["audit_latency_ms"] > 0.0

    def test_tamper_category_1_payload_modification(self, sample_pristine_blockchain):
        """Verifies detection when transaction payload / weights_hash is modified."""
        bc, _ = sample_pristine_blockchain
        suite = SyntheticTamperSuite()
        tampered = suite.generate_tampered_ledger(bc, category="payload_modification", seed=42)

        verifier = AuditVerifier()
        audit = verifier.verify_chain(tampered)
        assert audit["is_valid"] is False
        assert len(audit["violations"]) > 0
        assert audit["failure_category"] in ("MERKLE_ROOT_MISMATCH", "HEADER_HASH_MISMATCH")

    def test_tamper_category_2_block_deletion(self, sample_pristine_blockchain):
        """Verifies detection when an intermediate block is deleted from the sequence."""
        bc, _ = sample_pristine_blockchain
        suite = SyntheticTamperSuite()
        tampered = suite.generate_tampered_ledger(bc, category="block_deletion", seed=42)

        verifier = AuditVerifier()
        audit = verifier.verify_chain(tampered)
        assert audit["is_valid"] is False
        assert audit["failure_category"] in ("SEQUENCE_DISCONTINUITY", "PREV_HASH_MISMATCH")

    def test_tamper_category_3_block_reordering(self, sample_pristine_blockchain):
        """Verifies detection when consecutive blocks are transposed."""
        bc, _ = sample_pristine_blockchain
        suite = SyntheticTamperSuite()
        tampered = suite.generate_tampered_ledger(bc, category="block_reordering", seed=42)

        verifier = AuditVerifier()
        audit = verifier.verify_chain(tampered)
        assert audit["is_valid"] is False
        assert audit["failure_category"] in ("PREV_HASH_MISMATCH", "SEQUENCE_DISCONTINUITY")

    def test_tamper_category_4_hash_chain_modification(self, sample_pristine_blockchain):
        """Verifies detection when a block's prev_hash pointer is corrupted."""
        bc, _ = sample_pristine_blockchain
        suite = SyntheticTamperSuite()
        tampered = suite.generate_tampered_ledger(bc, category="hash_chain_modification", seed=42)

        verifier = AuditVerifier()
        audit = verifier.verify_chain(tampered)
        assert audit["is_valid"] is False
        assert audit["failure_category"] in ("PREV_HASH_MISMATCH", "HEADER_HASH_MISMATCH")

    def test_tamper_category_5_merkle_root_inconsistency(self, sample_pristine_blockchain):
        """Verifies detection when header merkle_root is altered."""
        bc, _ = sample_pristine_blockchain
        suite = SyntheticTamperSuite()
        tampered = suite.generate_tampered_ledger(bc, category="merkle_root_inconsistency", seed=42)

        verifier = AuditVerifier()
        audit = verifier.verify_chain(tampered)
        assert audit["is_valid"] is False
        assert audit["failure_category"] in ("MERKLE_ROOT_MISMATCH", "HEADER_HASH_MISMATCH")

    def test_synthetic_tamper_benchmark_execution(self, sample_pristine_blockchain):
        """Verifies the complete finite tamper benchmark runner across positive and negative trials."""
        bc, _ = sample_pristine_blockchain
        suite = SyntheticTamperSuite()

        report = suite.run_finite_tamper_benchmark(
            pristine_chain=bc,
            trials_per_category=10,
            negative_trials=10,
            base_seed=42
        )

        assert report["total_positive_tested"] == 50  # 5 categories * 10
        assert report["total_positive_detected"] == 50
        assert report["observed_detection_rate"] == 1.0
        assert report["total_false_alarms"] == 0
        assert report["observed_false_alarm_rate"] == 0.0
        assert len(report["per_category_results"]) == 5

    def test_overhead_profiler_crypto_benchmarks(self):
        """Verifies cryptographic microbenchmarks timing execution."""
        profiler = OverheadProfiler()
        res = profiler.benchmark_crypto_operations(num_trials=10, warm_up=2)

        assert "ecdsa_p256_sign" in res
        assert "ecdsa_p256_verify" in res
        assert "sha256_hash" in res
        assert res["ecdsa_p256_sign"]["mean_ms"] > 0.0
        assert res["ecdsa_p256_verify"]["mean_ms"] > 0.0
        assert res["sha256_hash"]["mean_ms"] > 0.0

    def test_overhead_profiler_communication_payloads(self):
        """Verifies serialized communication byte measurements."""
        profiler = OverheadProfiler()
        sample_weights = np.ones(5000, dtype=np.float32)

        payloads = profiler.measure_communication_payloads(sample_weights, num_clients=5)
        assert payloads["parameter_elements"] == 5000
        assert payloads["raw_tensor_nbytes"] == 5000 * 4  # 20,000 bytes
        assert payloads["client_upstream_bytes_per_round"] > 20000
        assert payloads["server_downstream_bytes_per_round"] > 20000
        assert payloads["total_round_network_kb"] > 0.0

    def test_overhead_profiler_aggregators(self):
        """Verifies aggregation microbenchmark timings."""
        profiler = OverheadProfiler()
        agg_timings = profiler.benchmark_aggregators(weights_dim=500, num_clients=5, num_trials=5, warm_up=1)

        assert "fedavg" in agg_timings
        assert "median" in agg_timings
        assert "trimmed_mean" in agg_timings
        assert "trust_weighted" in agg_timings
        assert "multikrum_f1" in agg_timings
        assert "foolsgold" in agg_timings
        for k, v in agg_timings.items():
            assert v["mean_ms"] > 0.0
            assert v["trials"] == 5
