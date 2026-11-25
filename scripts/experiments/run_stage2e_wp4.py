"""
Stage 2E.3 — WP4 Execution Runner: Computational Overhead & Blockchain Audit Evaluation.
Evaluates:
- Cryptographic microbenchmarks (ECDSA P-256 sign/verify, SHA-256)
- Aggregator microbenchmarks (FedAvg, Median, Trimmed Mean, Multi-Krum, FoolsGold, Trust-Weighted)
- Blockchain ledger operations (Merkle root, block forging, chain validation)
- Communication payload measurements (raw tensors, serialized pickle, signatures, transactions, blocks, round upstream/downstream KB)
- Synthetic tamper benchmark across 5 finite categories (500 positive trials) + negative unperturbed controls (100 trials)
- System environment metadata

Saves output to:
- data/processed/stage2e/wp4/overhead_summary.json
"""

import sys
import os
import json
import time
import hashlib
from typing import Tuple, Dict

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.blockchain.block import Transaction
from src.blockchain.chain import Blockchain
from src.blockchain.crypto import CryptoManager
from src.blockchain.audit_verifier import AuditVerifier, SyntheticTamperSuite
from src.evaluation.overhead_profiler import OverheadProfiler
from src.models.ids_net import IDSNet


def build_sample_pristine_chain(num_rounds: int = 3, num_clients: int = 5) -> Tuple[Blockchain, Dict[int, str]]:
    """Builds a realistic 4-block blockchain representing 3 federated rounds."""
    priv_keys = {}
    pub_keys = {}
    for cid in range(num_clients):
        priv_k, pub_k = CryptoManager.generate_keypair()
        priv_keys[cid] = priv_k
        pub_keys[cid] = pub_k

    bc = Blockchain(committee_size=3)

    for r in range(1, num_rounds + 1):
        round_hash = hashlib.sha256(f"global_weights_round_{r}".encode("utf-8")).hexdigest()
        for cid in range(num_clients):
            sample_hash = hashlib.sha256(f"client_{cid}_weights_round_{r}".encode("utf-8")).hexdigest()
            sig = CryptoManager.sign_message(priv_keys[cid], sample_hash)
            tx = Transaction(
                client_id=cid,
                round_num=r,
                weights_hash=sample_hash,
                signature=sig,
                validation_metrics={
                    "norm_passed": True,
                    "cos_sim": 0.94 + 0.01 * cid,
                    "loss_passed": True
                },
                status="ACCEPTED",
                reputation_before=1.0 + 0.05 * (r - 1),
                reputation_after=1.0 + 0.05 * r
            )
            bc.add_transaction(tx)
        bc.forge_block(global_model_hash=round_hash, validator_id=0)

    return bc, pub_keys


def main():
    print("=" * 80)
    print("STAGE 2E.3 — WP4: COMPUTATIONAL OVERHEAD & BLOCKCHAIN AUDIT EVALUATION")
    print("Tamper-Evident Local Audit Ledger Evaluation")
    print("=" * 80)

    output_dir = "data/processed/stage2e/wp4"
    os.makedirs(output_dir, exist_ok=True)

    profiler = OverheadProfiler()

    # 1. Hardware & Environment Metadata
    print("\n[1/5] Collecting Environment Metadata...")
    env_meta = profiler.get_environment_metadata()

    # 2. Cryptographic Microbenchmarks
    print("\n[2/5] Benchmarking Cryptographic Operations (100 trials, 10 warmup)...")
    crypto_benchmarks = profiler.benchmark_crypto_operations(num_trials=100, warm_up=10)

    # 3. Model Weight Dimension & Communication Payloads
    print("\n[3/5] Measuring Serialized Communication Payloads...")
    model = IDSNet(input_dim=122, num_classes=2)
    sample_weights = model.get_weights_vector()
    weight_dim = len(sample_weights)
    comm_payloads = profiler.measure_communication_payloads(sample_weights, num_clients=5)

    # 4. Aggregator & Ledger Microbenchmarks
    print(f"\n[4/5] Benchmarking Aggregation & Ledger Operations (Dim={weight_dim}, 100 trials)...")
    agg_benchmarks = profiler.benchmark_aggregators(weights_dim=weight_dim, num_clients=5, num_trials=100, warm_up=10)
    ledger_benchmarks = profiler.benchmark_ledger_operations(num_transactions=5, num_trials=100, warm_up=10)

    # 5. Synthetic Tampering Benchmark
    print("\n[5/5] Executing Finite Tampering Benchmark (500 positive trials, 100 negative controls)...")
    pristine_chain, pub_keys = build_sample_pristine_chain(num_rounds=3, num_clients=5)
    verifier = AuditVerifier(public_keys=pub_keys)
    tamper_suite = SyntheticTamperSuite(verifier=verifier)

    tamper_report = tamper_suite.run_finite_tamper_benchmark(
        pristine_chain=pristine_chain,
        trials_per_category=100,
        negative_trials=100,
        base_seed=42
    )

    # Compile comprehensive WP4 summary
    wp4_summary = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "environment": env_meta,
            "architecture_framing": (
                "Tamper-evident and cryptographically verifiable local audit ledger "
                "(no claims of P2P consensus, decentralized proof-of-stake, or universal immutability)"
            )
        },
        "cryptographic_microbenchmarks": crypto_benchmarks,
        "aggregation_microbenchmarks": agg_benchmarks,
        "ledger_operation_microbenchmarks": ledger_benchmarks,
        "communication_payload_analysis": comm_payloads,
        "tampering_verification_benchmark": tamper_report
    }

    summary_file = os.path.join(output_dir, "overhead_summary.json")
    with open(summary_file, "w") as f:
        json.dump(wp4_summary, f, indent=2)

    print("\n" + "=" * 80)
    print(f"WP4 Overhead and Audit Benchmark Successfully Saved to {summary_file}")
    print("=" * 80)
    print("\n--- Summary Highlights ---")
    print(f"ECDSA Sign (mean): {crypto_benchmarks['ecdsa_p256_sign']['mean_ms']:.4f} ms")
    print(f"ECDSA Verify (mean): {crypto_benchmarks['ecdsa_p256_verify']['mean_ms']:.4f} ms")
    print(f"SHA-256 (mean): {crypto_benchmarks['sha256_hash']['mean_ms']:.4f} ms")
    print(f"FedAvg Aggregation (mean): {agg_benchmarks['fedavg']['mean_ms']:.4f} ms")
    print(f"Multi-Krum Aggregation (mean): {agg_benchmarks['multikrum_f1']['mean_ms']:.4f} ms")
    print(f"FoolsGold Aggregation (mean): {agg_benchmarks['foolsgold']['mean_ms']:.4f} ms")
    print(f"Trust-Weighted Aggregation (mean): {agg_benchmarks['trust_weighted']['mean_ms']:.4f} ms")
    print(f"Merkle Root Calc (mean): {ledger_benchmarks['merkle_root_calc']['mean_ms']:.4f} ms")
    print(f"Block Forging PoT (mean): {ledger_benchmarks['forge_block_pot']['mean_ms']:.4f} ms")
    print(f"Client Upstream per Round: {comm_payloads['client_upstream_kb']:.2f} KB")
    print(f"Server Downstream per Round: {comm_payloads['server_downstream_kb']:.2f} KB")
    print(f"Total Network per Round (5 clients): {comm_payloads['total_round_network_kb']:.2f} KB")
    print(f"Tamper Detection Rate: {tamper_report['detection_statement']}")
    print(f"Tamper False Alarm Rate: {tamper_report['false_alarm_statement']}")


if __name__ == "__main__":
    main()
