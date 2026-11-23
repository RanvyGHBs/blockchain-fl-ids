"""
Cryptographic Audit Ledger Verifier & Finite Tampering Benchmark Suite.
Implements:
1. AuditVerifier: Validates block hash chaining, Merkle roots, sequence continuity, and signatures.
2. SyntheticTamperSuite: Evaluates detection rates and false-alarm rates over finite tamper categories.
"""

import copy
import time
import json
import hashlib
from typing import Dict, List, Tuple, Any, Optional
import numpy as np

from src.blockchain.chain import Blockchain
from src.blockchain.block import Block, Transaction
from src.blockchain.crypto import CryptoManager


class AuditVerifier:
    """
    Cryptographic Audit Verifier for the Blockchain Trust Ledger.
    Performs exhaustive verification of chain integrity, Merkle trees, and transaction signatures.
    Accurately identifies the exact block index and failure category when integrity is breached.
    """

    def __init__(self, public_keys: Optional[Dict[int, str]] = None):
        """
        Args:
            public_keys: Optional mapping of client_id -> PEM-encoded public key for signature audit.
        """
        self.public_keys = public_keys or {}

    def verify_chain(
        self,
        blockchain: Blockchain,
        verify_signatures: bool = False,
        expected_height: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Exhaustively audits an entire blockchain ledger instance.
        
        Verification Steps:
        1. Genesis block validity (index 0, previous_hash == '0'*64).
        2. Strict sequential block indexing (index_t == index_{t-1} + 1).
        3. Previous-hash cryptographic pointer chaining (block_t.prev_hash == block_{t-1}.hash).
        4. Header SHA-256 hash recalculation.
        5. Transaction Merkle root recalculation.
        6. Optional ECDSA signature verification for each transaction record.
        
        Returns:
            Dict containing validation status, list of violations, corrupted block index, and latency.
        """
        t0 = time.perf_counter_ns()
        violations: List[str] = []
        corrupted_block_idx: Optional[int] = None
        failure_category: Optional[str] = None

        chain = blockchain.chain
        if len(chain) == 0:
            latency_ms = (time.perf_counter_ns() - t0) / 1e6
            return {
                "is_valid": False,
                "total_blocks": 0,
                "total_transactions": 0,
                "violations": ["Empty blockchain: missing genesis block."],
                "corrupted_block_index": None,
                "failure_category": "EMPTY_CHAIN",
                "audit_latency_ms": latency_ms
            }

        # Check expected height if supplied
        if expected_height is not None and len(chain) != expected_height:
            violations.append(f"Blockchain height mismatch: expected {expected_height}, found {len(chain)}.")
            corrupted_block_idx = len(chain)
            failure_category = "BLOCK_HEIGHT_MISMATCH"

        # 1. Audit Genesis Block
        genesis = chain[0]
        if genesis.index != 0:
            violations.append(f"Genesis block index is {genesis.index}, expected 0.")
            corrupted_block_idx = 0
            failure_category = "GENESIS_INDEX_CORRUPTED"
        if genesis.previous_hash != "0" * 64:
            violations.append(f"Genesis block previous_hash is not 64 zeros: {genesis.previous_hash}")
            corrupted_block_idx = 0
            failure_category = "GENESIS_PREV_HASH_CORRUPTED"
        if genesis.hash != genesis.calculate_hash():
            violations.append(f"Genesis block hash mismatch: recorded={genesis.hash}, computed={genesis.calculate_hash()}")
            corrupted_block_idx = 0
            failure_category = "GENESIS_HASH_MISMATCH"

        total_txs = len(genesis.transactions)

        # 2. Audit Sequential Blocks
        for i in range(1, len(chain)):
            curr = chain[i]
            prev = chain[i - 1]
            total_txs += len(curr.transactions)

            # Sequence check
            if curr.index != prev.index + 1:
                violations.append(f"Block sequence gap at block {i}: current={curr.index}, previous={prev.index}")
                if corrupted_block_idx is None:
                    corrupted_block_idx = i
                    failure_category = "SEQUENCE_DISCONTINUITY"

            # Pointer check
            if curr.previous_hash != prev.hash:
                violations.append(
                    f"Hash-chain broken at block {i}: recorded prev_hash={curr.previous_hash[:16]}..., "
                    f"parent hash={prev.hash[:16]}..."
                )
                if corrupted_block_idx is None:
                    corrupted_block_idx = i
                    failure_category = "PREV_HASH_MISMATCH"

            # Header checksum check
            computed_hash = curr.calculate_hash()
            if curr.hash != computed_hash:
                violations.append(
                    f"Header hash mismatch at block {i}: recorded={curr.hash[:16]}..., "
                    f"computed={computed_hash[:16]}..."
                )
                if corrupted_block_idx is None:
                    corrupted_block_idx = i
                    failure_category = "HEADER_HASH_MISMATCH"

            # Merkle root check
            computed_merkle = curr.calculate_merkle_root()
            if curr.merkle_root != computed_merkle:
                violations.append(
                    f"Merkle root mismatch at block {i}: recorded={curr.merkle_root[:16]}..., "
                    f"computed={computed_merkle[:16]}..."
                )
                if corrupted_block_idx is None:
                    corrupted_block_idx = i
                    failure_category = "MERKLE_ROOT_MISMATCH"

            # Optional signature verification
            if verify_signatures and self.public_keys:
                for tx in curr.transactions:
                    cid = tx.client_id
                    if cid in self.public_keys:
                        pub_k = self.public_keys[cid]
                        # Verify signature on weights_hash
                        is_valid_sig = CryptoManager.verify_signature(pub_k, tx.weights_hash, tx.signature)
                        if not is_valid_sig:
                            violations.append(
                                f"Invalid ECDSA signature in block {i} for client {cid}, tx {tx.tx_id[:8]}"
                            )
                            if corrupted_block_idx is None:
                                corrupted_block_idx = i
                                failure_category = "SIGNATURE_VERIFICATION_FAILED"

        latency_ms = (time.perf_counter_ns() - t0) / 1e6
        is_valid = len(violations) == 0

        return {
            "is_valid": is_valid,
            "total_blocks": len(chain),
            "total_transactions": total_txs,
            "violations": violations,
            "corrupted_block_index": corrupted_block_idx,
            "failure_category": failure_category,
            "audit_latency_ms": latency_ms
        }


# ---------------------------------------------------------------------------
# Synthetic Tampering Benchmark Suite (Finite Test Categories)
# ---------------------------------------------------------------------------

class SyntheticTamperSuite:
    """
    Evaluates audit detection performance across an explicit finite suite of 5 synthetic tampering categories.
    Reports observed detection rate and observed false-alarm rate without overclaiming universal guarantees.
    """

    TAMPER_CATEGORIES = [
        "payload_modification",
        "block_deletion",
        "block_reordering",
        "hash_chain_modification",
        "merkle_root_inconsistency"
    ]

    def __init__(self, verifier: Optional[AuditVerifier] = None):
        self.verifier = verifier or AuditVerifier()

    def generate_tampered_ledger(self, pristine_chain: Blockchain, category: str, seed: int = 42) -> Blockchain:
        """
        Creates a synthetic deep copy of a valid blockchain and injects a single targeted tampering fault.
        """
        cloned_chain = copy.deepcopy(pristine_chain)
        chain = cloned_chain.chain
        num_blocks = len(chain)

        if num_blocks < 3:
            raise ValueError(f"Blockchain must contain at least 3 blocks to test tampering, found {num_blocks}.")

        rng = np.random.RandomState(seed)
        # Select an intermediate block (not genesis, not necessarily the last)
        target_idx = rng.randint(1, num_blocks)

        if category == "payload_modification":
            target_block = chain[target_idx]
            if target_block.transactions:
                # Corrupt the weights_hash of a transaction without updating header
                tx = target_block.transactions[0]
                tx.weights_hash = hashlib.sha256(b"maliciously_altered_model_weights").hexdigest()
                tx.tx_id = tx.calculate_hash()  # Corrupts tx_id, which invalidates block Merkle root
            else:
                # Corrupt global model hash
                target_block.global_model_hash = "forged_model_hash_payload"

        elif category == "block_deletion":
            # Excise an intermediate block from sequence (1 <= target_idx < num_blocks - 1)
            # This ensures sequence discontinuity and broken hash pointer without genesis corruption.
            del_idx = rng.randint(1, num_blocks - 1)
            del chain[del_idx]

        elif category == "block_reordering":
            # Transpose target block with previous or next
            swap_idx = target_idx - 1 if target_idx > 1 else target_idx + 1
            chain[target_idx], chain[swap_idx] = chain[swap_idx], chain[target_idx]

        elif category == "hash_chain_modification":
            # Corrupt previous_hash pointer
            chain[target_idx].previous_hash = hashlib.sha256(b"corrupted_pointer_data").hexdigest()

        elif category == "merkle_root_inconsistency":
            # Overwrite header merkle root directly
            chain[target_idx].merkle_root = hashlib.sha256(b"arbitrary_forged_merkle_root").hexdigest()

        else:
            raise ValueError(f"Unknown tampering category '{category}'. Valid: {self.TAMPER_CATEGORIES}")

        return cloned_chain

    def run_finite_tamper_benchmark(
        self,
        pristine_chain: Blockchain,
        trials_per_category: int = 100,
        negative_trials: int = 100,
        base_seed: int = 42
    ) -> Dict[str, Any]:
        """
        Executes finite tampering benchmark across all 5 positive categories and pristine negative controls.
        
        Returns:
            Dict containing observed detection rates, observed false alarm rate, and per-category diagnostics.
        """
        expected_height = len(pristine_chain.chain)
        # First verify baseline chain is genuinely valid
        initial_check = self.verifier.verify_chain(pristine_chain, expected_height=expected_height)
        if not initial_check["is_valid"]:
            raise ValueError(f"Pristine chain provided to benchmark is already invalid: {initial_check['violations']}")

        results_by_category: Dict[str, Dict[str, Any]] = {}
        total_positive_tested = 0
        total_positive_detected = 0

        # Positive Tests: 5 Categories
        for cat in self.TAMPER_CATEGORIES:
            cat_detected = 0
            cat_latencies = []
            detected_indices = []

            for trial in range(trials_per_category):
                trial_seed = base_seed * 10007 + trial * 997
                tampered = self.generate_tampered_ledger(pristine_chain, cat, seed=trial_seed)
                audit = self.verifier.verify_chain(tampered, expected_height=expected_height)

                if not audit["is_valid"]:
                    cat_detected += 1
                    detected_indices.append(audit["corrupted_block_index"])
                cat_latencies.append(audit["audit_latency_ms"])

            total_positive_tested += trials_per_category
            total_positive_detected += cat_detected

            results_by_category[cat] = {
                "tested": trials_per_category,
                "detected": cat_detected,
                "detection_rate": float(cat_detected / trials_per_category),
                "mean_audit_latency_ms": float(np.mean(cat_latencies)),
                "std_audit_latency_ms": float(np.std(cat_latencies))
            }

        # Negative Tests: Pristine Chains (False Alarm Evaluation)
        false_alarms = 0
        negative_latencies = []
        for trial in range(negative_trials):
            cloned_pristine = copy.deepcopy(pristine_chain)
            audit = self.verifier.verify_chain(cloned_pristine, expected_height=expected_height)
            if not audit["is_valid"]:
                false_alarms += 1
            negative_latencies.append(audit["audit_latency_ms"])

        observed_detection_rate = float(total_positive_detected / total_positive_tested)
        observed_fpr = float(false_alarms / negative_trials)

        return {
            "total_positive_tested": total_positive_tested,
            "total_positive_detected": total_positive_detected,
            "observed_detection_rate": observed_detection_rate,
            "observed_detection_rate_pct": f"{observed_detection_rate * 100:.2f}%",
            "detection_statement": (
                f"{total_positive_detected}/{total_positive_tested} detected — "
                f"{observed_detection_rate * 100:.1f}% observed detection on this finite test suite."
            ),
            "total_negative_tested": negative_trials,
            "total_false_alarms": false_alarms,
            "observed_false_alarm_rate": observed_fpr,
            "observed_false_alarm_rate_pct": f"{observed_fpr * 100:.2f}%",
            "false_alarm_statement": (
                f"{false_alarms}/{negative_trials} false alarms — "
                f"{observed_fpr * 100:.1f}% observed FPR across unperturbed pristine audit ledgers."
            ),
            "mean_pristine_audit_latency_ms": float(np.mean(negative_latencies)),
            "per_category_results": results_by_category
        }
