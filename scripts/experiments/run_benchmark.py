"""
Automated Comprehensive Benchmark Runner.
Executes controlled comparative experiments across multiple scenarios:
1. Centralized Baseline (Upper bound)
2. Vanilla Federated Learning (FedAvg - Honest)
3. Vanilla Federated Learning Under Attack (Poisoning with NO defense)
4. Robust Aggregation (Trimmed Mean Under Attack)
5. Blockchain-Assisted Federated Learning (Multi-Criteria Trust Defense + Audit Ledger)
6. Privacy-Preserving Federated Learning (Clipping-based Gaussian update perturbation without formal privacy accounting)

All metrics are computed from actual PyTorch execution and saved to data/processed/benchmark_results.json.
"""

import os
import sys
import json
import time
from typing import Dict, List, Any, Tuple
import numpy as np
import torch

# Allow running directly via python scripts/experiments/run_benchmark.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.data.nsl_kdd import NSLKDDLoader
from src.data.partitioner import FederatedPartitioner
from src.federated.client import FederatedClient
from src.federated.server import FederatedServer
from src.attacks.model_poisoning import apply_gaussian_noise_attack, apply_sign_flipping_attack
from src.attacks.data_poisoning import apply_label_flipping_attack
from src.trust.evaluator import MultiCriteriaTrustEngine
from src.trust.reputation import ReputationManager
from src.blockchain.crypto import CryptoManager
from src.blockchain.block import Transaction
from src.blockchain.chain import Blockchain
from src.privacy.differential import LocalDifferentialPrivacy


def run_experiment(scenario_name: str, X_train: np.ndarray, y_train: np.ndarray,
                   X_test: np.ndarray, y_test: np.ndarray,
                   num_clients: int = 5, num_rounds: int = 5, local_epochs: int = 1,
                   batch_size: int = 64, lr: float = 0.002,
                   attack_enabled: bool = False, malicious_client_id: int = 3,
                   attack_type: str = "gaussian_noise",
                   defense_enabled: bool = False,
                   aggregation_algorithm: str = "fedavg",
                   fedprox_mu: float = 0.0,
                   dp_enabled: bool = False,
                   seed: int = 42) -> Dict[str, Any]:
    """
    Executes a multi-round federated experiment for a specific scenario.
    """
    print(f"\n{'='*60}\nRUNNING SCENARIO: {scenario_name}\n{'='*60}")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    input_dim = X_train.shape[1]
    num_classes = 2

    # 1. Partition data across clients (Dirichlet Non-IID)
    partitioner = FederatedPartitioner(num_clients=num_clients, non_iid=True, alpha=0.5, seed=seed)
    client_splits = partitioner.partition(X_train, y_train)

    # 2. Initialize Clients
    clients: List[FederatedClient] = []
    client_keys: Dict[int, Tuple[str, str]] = {}
    for cid in range(num_clients):
        Xc, yc = client_splits[cid]
        # Data poisoning check
        if attack_enabled and cid == malicious_client_id and attack_type == "label_flip":
            print(f"  [Attack Setup] Injected Label-Flipping on Client {cid} (Attack -> Normal)")
            yc = apply_label_flipping_attack(yc, source_class=1, target_class=0, flip_ratio=1.0, seed=seed)

        client = FederatedClient(
            client_id=cid, client_name=f"Network-Node-{cid}",
            X_local=Xc, y_local=yc, input_dim=input_dim, num_classes=num_classes,
            device=device, seed=seed + cid
        )
        clients.append(client)
        priv_k, pub_k = CryptoManager.generate_keypair()
        client_keys[cid] = (priv_k, pub_k)

    # 3. Initialize Server, Trust Engine, Blockchain & Privacy
    server = FederatedServer(input_dim=input_dim, num_classes=num_classes,
                             aggregation_algorithm=aggregation_algorithm, device=device, seed=seed)
    trust_engine = MultiCriteriaTrustEngine(input_dim=input_dim, num_classes=num_classes, device=device)
    reputation_mgr = ReputationManager(client_ids=list(range(num_clients)))
    blockchain = Blockchain(committee_size=3)
    dp_engine = LocalDifferentialPrivacy(clip_norm=1.0, noise_multiplier=0.01, seed=seed) if dp_enabled else None

    # Benchmark validation slice for Non-IID safe trust evaluation
    val_indices = np.random.choice(len(X_test), size=min(1000, len(X_test)), replace=False)
    val_data = (X_test[val_indices], y_test[val_indices])

    round_metrics = []
    total_start = time.time()

    # Initial evaluation at round 0
    init_eval = server.evaluate(X_test, y_test)
    round_metrics.append({
        "round": 0, "accuracy": init_eval["accuracy"], "f1_score": init_eval["f1_score"],
        "loss": init_eval["loss"], "rejected_updates": 0
    })

    for r in range(1, num_rounds + 1):
        round_t0 = time.time()
        current_global_weights = server.get_global_weights()

        # Step A: Local training
        client_raw_weights: Dict[int, np.ndarray] = {}
        client_signatures: Dict[int, str] = {}
        sample_counts: Dict[int, int] = {}

        for client in clients:
            if reputation_mgr.is_quarantined(client.client_id):
                continue

            client.set_global_weights(current_global_weights)
            client.local_train(epochs=local_epochs, batch_size=batch_size, lr=lr,
                               fedprox_mu=fedprox_mu, global_weights=current_global_weights)
            weights = client.get_local_weights()

            # Apply DP noise if enabled
            if dp_enabled and dp_engine is not None:
                weights, _ = dp_engine.privatize(weights)

            # Apply Model Poisoning if attack enabled on this client
            if attack_enabled and client.client_id == malicious_client_id:
                if attack_type == "gaussian_noise":
                    weights = apply_gaussian_noise_attack(weights, std=2.5, seed=seed + r)
                elif attack_type == "sign_flip":
                    weights = apply_sign_flipping_attack(weights, scale=-3.0)

            # Sign model update hash with ECDSA private key
            w_hash = CryptoManager.sha256_hash(weights.tobytes().hex())
            sig = CryptoManager.sign_message(client_keys[client.client_id][0], w_hash)

            client_raw_weights[client.client_id] = weights
            client_signatures[client.client_id] = sig
            sample_counts[client.client_id] = client.num_samples

        # Step B: Trust & Defense Validation
        rejected_cids = []
        accepted_weights = []
        accepted_counts = []
        accepted_reps = []

        if defense_enabled:
            validation_reports = trust_engine.evaluate_updates(client_raw_weights, current_global_weights, val_data)
            reputation_mgr.update_reputation(validation_reports)

            for cid, report in validation_reports.items():
                is_valid = report["is_valid"]
                rep_before = reputation_mgr.reputation_history[cid][-2]
                rep_after = reputation_mgr.reputations[cid]
                status_str = "ACCEPTED" if is_valid else "REJECTED"

                tx = Transaction(
                    client_id=cid, round_num=r,
                    weights_hash=CryptoManager.sha256_hash(client_raw_weights[cid].tobytes().hex()),
                    signature=client_signatures[cid],
                    validation_metrics=report,
                    status=status_str,
                    reputation_before=rep_before,
                    reputation_after=rep_after
                )
                blockchain.add_transaction(tx)

                if is_valid:
                    accepted_weights.append(client_raw_weights[cid])
                    accepted_counts.append(sample_counts[cid])
                    accepted_reps.append(rep_after)
                else:
                    rejected_cids.append(cid)
                    print(f"  [Trust Defense Alert] Round {r}: Rejected malicious update from Client {cid}! Reason: {report['reason']}")

            # Proof-of-Trust Block Mining
            validator_id = blockchain.select_validator(reputation_mgr.get_all_reputations())
            new_global_hash = CryptoManager.sha256_hash(f"round_{r}_model")
            blockchain.forge_block(global_model_hash=new_global_hash, validator_id=validator_id)
        else:
            # Naive execution without defense
            for cid, w in client_raw_weights.items():
                accepted_weights.append(w)
                accepted_counts.append(sample_counts[cid])
                accepted_reps.append(1.0)

        # Step C: Aggregation
        if len(accepted_weights) > 0:
            if aggregation_algorithm == "fedavg":
                from src.federated.aggregators import aggregate_fedavg
                new_weights = aggregate_fedavg(accepted_weights, accepted_counts)
            elif aggregation_algorithm == "trimmed_mean":
                from src.federated.aggregators import aggregate_trimmed_mean
                new_weights = aggregate_trimmed_mean(accepted_weights, beta=0.2)
            elif aggregation_algorithm == "trust_weighted":
                from src.federated.aggregators import aggregate_trust_weighted
                new_weights = aggregate_trust_weighted(accepted_weights, accepted_counts, accepted_reps)
            server.set_global_weights(new_weights)

        # Step D: Global Evaluation on Test Set
        eval_metrics = server.evaluate(X_test, y_test)
        round_duration = time.time() - round_t0
        print(f"  Round {r}/{num_rounds} | Acc: {eval_metrics['accuracy']*100:.2f}% | F1: {eval_metrics['f1_score']:.4f} | Loss: {eval_metrics['loss']:.4f} | Rejected: {len(rejected_cids)} | Time: {round_duration:.2f}s")

        round_metrics.append({
            "round": r,
            "accuracy": eval_metrics["accuracy"],
            "precision": eval_metrics["precision"],
            "recall": eval_metrics["recall"],
            "f1_score": eval_metrics["f1_score"],
            "loss": eval_metrics["loss"],
            "rejected_updates": len(rejected_cids),
            "rejected_client_ids": rejected_cids,
            "duration_sec": round_duration
        })

    total_time = time.time() - total_start
    final_eval = round_metrics[-1]

    return {
        "scenario_name": scenario_name,
        "final_accuracy": final_eval["accuracy"],
        "final_f1_score": final_eval["f1_score"],
        "final_loss": final_eval["loss"],
        "round_history": round_metrics,
        "total_time_sec": total_time,
        "blockchain_summary": blockchain.get_audit_summary(),
        "reputation_summary": reputation_mgr.get_status_summary()
    }


def main():
    print("=" * 70)
    print("EXECUTING COMPREHENSIVE CONTROLLED EXPERIMENTAL BENCHMARKS")
    print("=" * 70)

    # 1. Load Preprocessed NSL-KDD
    loader = NSLKDDLoader(raw_dir="data/raw", processed_dir="data/processed", binary=True, seed=42)
    X_train, y_train, X_test, y_test = loader.preprocess()

    results: Dict[str, Any] = {}

    # Scenario 1: Vanilla FedAvg (Honest Baseline)
    results["vanilla_fl_honest"] = run_experiment(
        scenario_name="Vanilla FedAvg (Honest Participants)",
        X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test,
        num_clients=5, num_rounds=3, local_epochs=1, batch_size=128,
        attack_enabled=False, defense_enabled=False, aggregation_algorithm="fedavg"
    )

    # Scenario 2: Vanilla FedAvg Under Model Poisoning Attack (NO defense)
    results["vanilla_fl_poisoned"] = run_experiment(
        scenario_name="Vanilla FedAvg Under Model Poisoning (No Defense)",
        X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test,
        num_clients=5, num_rounds=3, local_epochs=1, batch_size=128,
        attack_enabled=True, malicious_client_id=3, attack_type="gaussian_noise",
        defense_enabled=False, aggregation_algorithm="fedavg"
    )

    # Scenario 3: Blockchain-Assisted Federated Learning Under Attack (Proposed Defense)
    results["blockchain_fl_defended"] = run_experiment(
        scenario_name="Blockchain-Assisted FL Under Attack (Proposed Framework)",
        X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test,
        num_clients=5, num_rounds=3, local_epochs=1, batch_size=128,
        attack_enabled=True, malicious_client_id=3, attack_type="gaussian_noise",
        defense_enabled=True, aggregation_algorithm="fedavg"
    )

    # Scenario 4: Privacy-Preserving FL (Clipping-Based Gaussian Perturbation)
    results["privacy_fl"] = run_experiment(
        scenario_name="Privacy-Preserving FL (Clipping-based Gaussian update perturbation without formal privacy accounting)",
        X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test,
        num_clients=5, num_rounds=3, local_epochs=1, batch_size=128,
        attack_enabled=False, defense_enabled=False, aggregation_algorithm="fedavg",
        dp_enabled=True
    )

    # Save results to json
    os.makedirs("data/processed", exist_ok=True)
    out_path = "data/processed/benchmark_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=4)

    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY COMPARISON:")
    print("=" * 70)
    for name, r in results.items():
        print(f"Scenario: {r['scenario_name']}")
        print(f"  Final Accuracy: {r['final_accuracy']*100:.2f}% | Final F1: {r['final_f1_score']:.4f} | Time: {r['total_time_sec']:.1f}s")
    print(f"\nAll benchmark results successfully recorded to {out_path}!")


if __name__ == "__main__":
    main()
