"""
Computational Overhead & Communication Payload Profiler.
Measures wall-clock execution latency (milliseconds) and serialized transmission sizes (bytes)
for cryptographic operations, federated aggregation, trust verification, and blockchain ledger mining.
"""

import os
import sys
import time
import json
import copy
import pickle
import hashlib
import platform
from contextlib import contextmanager
from typing import Dict, List, Any, Optional
import numpy as np
import torch

from src.blockchain.crypto import CryptoManager
from src.blockchain.block import Block, Transaction
from src.blockchain.chain import Blockchain
from src.trust.evaluator import MultiCriteriaTrustEngine
from src.federated.aggregators import (
    aggregate_fedavg, aggregate_median, aggregate_trimmed_mean, aggregate_trust_weighted
)
from src.evaluation.baselines import aggregate_multikrum, FoolsGoldAggregator


class OverheadProfiler:
    """
    High-resolution profiler measuring execution time and payload byte footprints
    for cryptographic, federated learning, and blockchain operations.
    """

    def __init__(self):
        self.latency_records: Dict[str, List[float]] = {}
        self.byte_records: Dict[str, int] = {}

    @contextmanager
    def measure(self, category: str, operation: str):
        """Context manager to measure wall-clock elapsed time in milliseconds."""
        key = f"{category}::{operation}"
        t0 = time.perf_counter_ns()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter_ns() - t0) / 1e6
            if key not in self.latency_records:
                self.latency_records[key] = []
            self.latency_records[key].append(elapsed_ms)

    def record_bytes(self, payload_name: str, num_bytes: int):
        """Records payload or network transmission size in bytes."""
        self.byte_records[payload_name] = int(num_bytes)

    # -----------------------------------------------------------------------
    # Standalone Cryptographic Microbenchmarks
    # -----------------------------------------------------------------------

    def benchmark_crypto_operations(
        self,
        num_trials: int = 100,
        warm_up: int = 10
    ) -> Dict[str, Dict[str, float]]:
        """
        Benchmarks ECDSA P-256 signing, signature verification, and SHA-256 hashing.
        """
        priv_pem, pub_pem = CryptoManager.generate_keypair()
        sample_hash = hashlib.sha256(b"benchmark_candidate_model_vector_hash").hexdigest()

        # Warm-up
        for _ in range(warm_up):
            sig = CryptoManager.sign_message(priv_pem, sample_hash)
            _ = CryptoManager.verify_signature(pub_pem, sample_hash, sig)
            _ = hashlib.sha256(sample_hash.encode("utf-8")).hexdigest()

        # Timed trials
        signing_times = []
        verify_times = []
        hashing_times = []

        for _ in range(num_trials):
            # Sign
            t0 = time.perf_counter_ns()
            sig = CryptoManager.sign_message(priv_pem, sample_hash)
            signing_times.append((time.perf_counter_ns() - t0) / 1e6)

            # Verify
            t0 = time.perf_counter_ns()
            valid = CryptoManager.verify_signature(pub_pem, sample_hash, sig)
            verify_times.append((time.perf_counter_ns() - t0) / 1e6)
            assert valid, "Signature verification failed during benchmark."

            # SHA-256
            t0 = time.perf_counter_ns()
            _ = hashlib.sha256(sample_hash.encode("utf-8")).hexdigest()
            hashing_times.append((time.perf_counter_ns() - t0) / 1e6)

        def _stats(arr: List[float]) -> Dict[str, float]:
            return {
                "mean_ms": float(np.mean(arr)),
                "median_ms": float(np.median(arr)),
                "std_ms": float(np.std(arr)),
                "p50_ms": float(np.percentile(arr, 50)),
                "p95_ms": float(np.percentile(arr, 95)),
                "min_ms": float(np.min(arr)),
                "max_ms": float(np.max(arr)),
                "trials": len(arr)
            }

        return {
            "ecdsa_p256_sign": _stats(signing_times),
            "ecdsa_p256_verify": _stats(verify_times),
            "sha256_hash": _stats(hashing_times)
        }

    # -----------------------------------------------------------------------
    # Standalone Aggregator Microbenchmarks
    # -----------------------------------------------------------------------

    def benchmark_aggregators(
        self,
        weights_dim: int = 10000,
        num_clients: int = 5,
        num_trials: int = 50,
        warm_up: int = 5
    ) -> Dict[str, Dict[str, float]]:
        """
        Benchmarks computational latency of all supported aggregation algorithms:
        FedAvg, Coordinate Median, Trimmed Mean, Trust-Weighted FedAvg, Multi-Krum, FoolsGold.
        """
        rng = np.random.RandomState(42)
        sample_weights = [rng.randn(weights_dim).astype(np.float32) for _ in range(num_clients)]
        sample_counts = [1000 for _ in range(num_clients)]
        reputations = [1.0 for _ in range(num_clients)]

        # Warm-up
        for _ in range(warm_up):
            _ = aggregate_fedavg(sample_weights, sample_counts)
            _ = aggregate_median(sample_weights)
            _ = aggregate_trimmed_mean(sample_weights, beta=0.2)
            _ = aggregate_trust_weighted(sample_weights, sample_counts, reputations)
            _ = aggregate_multikrum(sample_weights, f=1, m=1)
            fg = FoolsGoldAggregator(num_clients=num_clients)
            updates_dict = {i: sample_weights[i] for i in range(num_clients)}
            _ = fg.aggregate(updates_dict)

        results: Dict[str, List[float]] = {
            "fedavg": [],
            "median": [],
            "trimmed_mean": [],
            "trust_weighted": [],
            "multikrum_f1": [],
            "foolsgold": []
        }

        for _ in range(num_trials):
            # FedAvg
            t0 = time.perf_counter_ns()
            _ = aggregate_fedavg(sample_weights, sample_counts)
            results["fedavg"].append((time.perf_counter_ns() - t0) / 1e6)

            # Median
            t0 = time.perf_counter_ns()
            _ = aggregate_median(sample_weights)
            results["median"].append((time.perf_counter_ns() - t0) / 1e6)

            # Trimmed Mean
            t0 = time.perf_counter_ns()
            _ = aggregate_trimmed_mean(sample_weights, beta=0.2)
            results["trimmed_mean"].append((time.perf_counter_ns() - t0) / 1e6)

            # Trust Weighted
            t0 = time.perf_counter_ns()
            _ = aggregate_trust_weighted(sample_weights, sample_counts, reputations)
            results["trust_weighted"].append((time.perf_counter_ns() - t0) / 1e6)

            # Multi-Krum (f=1, m=1)
            t0 = time.perf_counter_ns()
            _ = aggregate_multikrum(sample_weights, f=1, m=1)
            results["multikrum_f1"].append((time.perf_counter_ns() - t0) / 1e6)

            # FoolsGold
            fg = FoolsGoldAggregator(num_clients=num_clients)
            updates_dict = {i: sample_weights[i] for i in range(num_clients)}
            t0 = time.perf_counter_ns()
            _ = fg.aggregate(updates_dict)
            results["foolsgold"].append((time.perf_counter_ns() - t0) / 1e6)

        def _stats(arr: List[float]) -> Dict[str, float]:
            return {
                "mean_ms": float(np.mean(arr)),
                "median_ms": float(np.median(arr)),
                "std_ms": float(np.std(arr)),
                "p50_ms": float(np.percentile(arr, 50)),
                "p95_ms": float(np.percentile(arr, 95)),
                "min_ms": float(np.min(arr)),
                "max_ms": float(np.max(arr)),
                "trials": len(arr)
            }

        return {k: _stats(v) for k, v in results.items()}

    # -----------------------------------------------------------------------
    # Communication Payload Byte Profiling
    # -----------------------------------------------------------------------

    def measure_communication_payloads(
        self,
        weights: np.ndarray,
        num_clients: int = 5
    ) -> Dict[str, Any]:
        """
        Measures exact byte footprints of serialized tensors, signatures, transactions, and blocks.
        """
        priv_pem, pub_pem = CryptoManager.generate_keypair()
        sample_hash = hashlib.sha256(weights.tobytes()).hexdigest()
        signature = CryptoManager.sign_message(priv_pem, sample_hash)

        # Raw tensor bytes
        raw_nbytes = int(weights.nbytes)
        pickle_bytes = len(pickle.dumps(weights))

        # Signature string bytes
        sig_str_bytes = len(signature.encode("utf-8"))

        # Transaction JSON bytes
        tx = Transaction(
            client_id=0,
            round_num=1,
            weights_hash=sample_hash,
            signature=signature,
            validation_metrics={"norm_passed": True, "cos_sim": 0.95, "loss_passed": True},
            status="ACCEPTED",
            reputation_before=1.0,
            reputation_after=1.05
        )
        tx_dict = tx.to_dict()
        tx_json_bytes = len(json.dumps(tx_dict).encode("utf-8"))

        # Block JSON bytes (with 5 transactions)
        txs = [copy.deepcopy(tx) for _ in range(num_clients)]
        block = Block(
            index=1,
            previous_hash="0" * 64,
            transactions=txs,
            global_model_hash=sample_hash,
            validator_id=0
        )
        block_json_bytes = len(json.dumps(block.to_dict()).encode("utf-8"))

        # Estimated network payload per client per round:
        # Upstream per client: model weights + signature + metadata
        client_upstream_bytes = pickle_bytes + sig_str_bytes + len(json.dumps({"client_id": 0, "round": 1}).encode("utf-8"))
        # Downstream broadcast per client: global model weights + reputation vector (N floats)
        server_downstream_bytes = pickle_bytes + len(json.dumps({"reputations": [1.0] * num_clients}).encode("utf-8"))
        # Total network payload per round
        total_round_network_bytes = (client_upstream_bytes * num_clients) + (server_downstream_bytes * num_clients)

        return {
            "parameter_elements": int(len(weights)),
            "raw_tensor_nbytes": raw_nbytes,
            "serialized_pickle_bytes": pickle_bytes,
            "signature_string_bytes": sig_str_bytes,
            "transaction_json_bytes": tx_json_bytes,
            "block_json_bytes_5tx": block_json_bytes,
            "client_upstream_bytes_per_round": client_upstream_bytes,
            "client_upstream_kb": float(client_upstream_bytes / 1024),
            "server_downstream_bytes_per_round": server_downstream_bytes,
            "server_downstream_kb": float(server_downstream_bytes / 1024),
            "total_round_network_bytes": total_round_network_bytes,
            "total_round_network_kb": float(total_round_network_bytes / 1024),
            "total_round_network_mb": float(total_round_network_bytes / (1024 * 1024))
        }

    # -----------------------------------------------------------------------
    # Ledger Construction & Mining Microbenchmarks
    # -----------------------------------------------------------------------

    def benchmark_ledger_operations(
        self,
        num_transactions: int = 5,
        num_trials: int = 50,
        warm_up: int = 5
    ) -> Dict[str, Dict[str, float]]:
        """
        Benchmarks Merkle root calculation, block header calculation, and block forging.
        """
        priv_pem, pub_pem = CryptoManager.generate_keypair()
        sample_hash = hashlib.sha256(b"dummy_weights").hexdigest()
        signature = CryptoManager.sign_message(priv_pem, sample_hash)

        txs = [
            Transaction(
                client_id=i,
                round_num=1,
                weights_hash=sample_hash,
                signature=signature,
                validation_metrics={"norm_passed": True},
                status="ACCEPTED",
                reputation_before=1.0,
                reputation_after=1.05
            )
            for i in range(num_transactions)
        ]

        # Warm-up
        for _ in range(warm_up):
            bc = Blockchain(committee_size=3)
            for tx in txs:
                bc.add_transaction(tx)
            _ = bc.forge_block(global_model_hash=sample_hash, validator_id=0)
            _ = bc.is_chain_valid()

        merkle_times = []
        forge_times = []
        chain_valid_times = []

        for _ in range(num_trials):
            # Merkle root calculation
            dummy_block = Block(
                index=1,
                previous_hash="0" * 64,
                transactions=txs,
                global_model_hash=sample_hash
            )
            t0 = time.perf_counter_ns()
            _ = dummy_block.calculate_merkle_root()
            merkle_times.append((time.perf_counter_ns() - t0) / 1e6)

            # Forge block
            bc = Blockchain(committee_size=3)
            for tx in txs:
                bc.add_transaction(tx)
            t0 = time.perf_counter_ns()
            _ = bc.forge_block(global_model_hash=sample_hash, validator_id=0)
            forge_times.append((time.perf_counter_ns() - t0) / 1e6)

            # Chain validity check
            t0 = time.perf_counter_ns()
            _ = bc.is_chain_valid()
            chain_valid_times.append((time.perf_counter_ns() - t0) / 1e6)

        def _stats(arr: List[float]) -> Dict[str, float]:
            return {
                "mean_ms": float(np.mean(arr)),
                "median_ms": float(np.median(arr)),
                "std_ms": float(np.std(arr)),
                "p50_ms": float(np.percentile(arr, 50)),
                "p95_ms": float(np.percentile(arr, 95)),
                "min_ms": float(np.min(arr)),
                "max_ms": float(np.max(arr)),
                "trials": len(arr)
            }

        return {
            "merkle_root_calc": _stats(merkle_times),
            "forge_block_pot": _stats(forge_times),
            "chain_validation_pot": _stats(chain_valid_times)
        }

    # -----------------------------------------------------------------------
    # Comprehensive Environment Metadata
    # -----------------------------------------------------------------------

    @staticmethod
    def get_environment_metadata() -> Dict[str, Any]:
        """Captures hardware, OS, and software environment metadata for reproducibility."""
        return {
            "os_name": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "machine_arch": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version.split()[0],
            "torch_version": torch.__version__,
            "torch_cuda_available": torch.cuda.is_available(),
            "numpy_version": np.__version__
        }
