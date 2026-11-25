"""
Stage 2: Full Federated Learning Benchmark Pipeline.

Runs six controlled experimental scenarios end-to-end using the
FederatedOrchestrator and saves full analytics to data/processed/stage2_results.json.

Scenarios:
  S1  - Vanilla FedAvg (Honest baseline)
  S2  - Vanilla FedAvg under Gaussian Noise Model Poisoning (no defense)
  S3  - Vanilla FedAvg under Sign-Flip Attack (no defense)
  S4  - Blockchain-Assisted FL (Multi-Criteria Defense) under Gaussian Attack
  S5  - Blockchain-Assisted FL (Multi-Criteria Defense) under Sign-Flip Attack
  S6  - Privacy-Preserving FL (Clipping-based Gaussian update perturbation without formal privacy accounting)

Usage:
    cd blockchain-fl-ids
    python run_stage2.py
"""

import os
import sys
import json
import time
import numpy as np
import torch

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data.nsl_kdd import NSLKDDLoader
from src.federated.orchestrator import FederatedOrchestrator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(scenario_name: str, X_train, y_train, X_test, y_test, feature_names,
                 num_rounds: int = 5, **kwargs) -> dict:
    base = {
        "scenario_name": scenario_name,
        "seed": 42,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "num_clients": 5,
        "num_rounds": num_rounds,
        "local_epochs": 1,
        "batch_size": 128,
        "lr": 0.002,
        "fedprox_mu": 0.0,
        "aggregation_algorithm": "fedavg",
        "attack_enabled": False,
        "malicious_client_ids": [3],
        "attack_type": "gaussian_noise",
        "defense_enabled": False,
        "dp_enabled": False,
        "dp_clip_norm": 1.0,
        "dp_noise_multiplier": 0.01,
        "X_train": X_train, "y_train": y_train,
        "X_test": X_test, "y_test": y_test,
        "feature_names": feature_names,
        "trust_config": {
            "norm_threshold_factor": 2.5,
            "cosine_threshold": 0.15,
            "loss_increase_threshold": 1.5,
        }
    }
    base.update(kwargs)
    return base


def _print_divider(title: str):
    w = 70
    print("\n" + "=" * w)
    pad = (w - len(title) - 2) // 2
    print(" " * pad + f" {title} ")
    print("=" * w)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    _print_divider("STAGE 2  –  COMPREHENSIVE BLOCKCHAIN-FL BENCHMARK")

    # 1. Load dataset
    print("\n[1/7] Loading NSL-KDD dataset ...")
    loader = NSLKDDLoader(raw_dir="data/raw", processed_dir="data/processed",
                          binary=True, seed=42)
    X_train, y_train, X_test, y_test = loader.preprocess()
    feature_names = loader.feature_columns
    print(f"       Train: {X_train.shape}  |  Test: {X_test.shape}  "
          f"|  Features: {X_train.shape[1]}")

    results: dict = {}
    NUM_ROUNDS = 5  # Increase to 10 for publication-quality runs

    # ------------------------------------------------------------------
    # S1: Vanilla FedAvg – Honest Baseline
    # ------------------------------------------------------------------
    _print_divider("S1 | Vanilla FedAvg – Honest Baseline")
    orch = FederatedOrchestrator(_make_config(
        scenario_name="S1 – Vanilla FedAvg (Honest Baseline)",
        X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test,
        feature_names=feature_names,
        num_rounds=NUM_ROUNDS,
        attack_enabled=False, defense_enabled=False
    ))
    results["s1_honest_fedavg"] = orch.run()

    # ------------------------------------------------------------------
    # S2: Vanilla FedAvg – Gaussian Noise Attack (NO defense)
    # ------------------------------------------------------------------
    _print_divider("S2 | Vanilla FedAvg – Gaussian Noise Attack (No Defense)")
    orch = FederatedOrchestrator(_make_config(
        scenario_name="S2 – Vanilla FedAvg Under Gaussian Noise Attack (No Defense)",
        X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test,
        feature_names=feature_names,
        num_rounds=NUM_ROUNDS,
        attack_enabled=True, malicious_client_ids=[3],
        attack_type="gaussian_noise",
        defense_enabled=False
    ))
    results["s2_poisoned_no_defense"] = orch.run()

    # ------------------------------------------------------------------
    # S3: Vanilla FedAvg – Sign-Flip Attack (NO defense)
    # ------------------------------------------------------------------
    _print_divider("S3 | Vanilla FedAvg – Sign-Flip Attack (No Defense)")
    orch = FederatedOrchestrator(_make_config(
        scenario_name="S3 – Vanilla FedAvg Under Sign-Flip Attack (No Defense)",
        X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test,
        feature_names=feature_names,
        num_rounds=NUM_ROUNDS,
        attack_enabled=True, malicious_client_ids=[3],
        attack_type="sign_flip",
        defense_enabled=False
    ))
    results["s3_signflip_no_defense"] = orch.run()

    # ------------------------------------------------------------------
    # S4: Blockchain-Assisted FL – Gaussian Noise Attack (WITH defense)
    # ------------------------------------------------------------------
    _print_divider("S4 | Blockchain-Assisted FL – Gaussian Noise (Multi-Criteria Defense)")
    orch = FederatedOrchestrator(_make_config(
        scenario_name="S4 – Blockchain-Assisted FL Under Gaussian Attack (Proposed Framework)",
        X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test,
        feature_names=feature_names,
        num_rounds=NUM_ROUNDS,
        attack_enabled=True, malicious_client_ids=[3],
        attack_type="gaussian_noise",
        defense_enabled=True,
        aggregation_algorithm="trust_weighted"
    ))
    results["s4_blockchain_gaussian_defense"] = orch.run()

    # ------------------------------------------------------------------
    # S5: Blockchain-Assisted FL – Sign-Flip Attack (WITH defense)
    # ------------------------------------------------------------------
    _print_divider("S5 | Blockchain-Assisted FL – Sign-Flip (Multi-Criteria Defense)")
    orch = FederatedOrchestrator(_make_config(
        scenario_name="S5 – Blockchain-Assisted FL Under Sign-Flip Attack (Proposed Framework)",
        X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test,
        feature_names=feature_names,
        num_rounds=NUM_ROUNDS,
        attack_enabled=True, malicious_client_ids=[3],
        attack_type="sign_flip",
        defense_enabled=True,
        aggregation_algorithm="trust_weighted"
    ))
    results["s5_blockchain_signflip_defense"] = orch.run()

    # ------------------------------------------------------------------
    # S6: Privacy-Preserving FL – Clipping-Based Gaussian Update Perturbation
    # ------------------------------------------------------------------
    _print_divider("S6 | Privacy-Preserving FL – Clipping-Based Gaussian Perturbation (No Formal Accounting)")
    orch = FederatedOrchestrator(_make_config(
        scenario_name="S6 – Privacy-Preserving FL (Clipping-based Gaussian update perturbation without formal privacy accounting)",
        X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test,
        feature_names=feature_names,
        num_rounds=NUM_ROUNDS,
        attack_enabled=False, defense_enabled=False,
        dp_enabled=True, dp_clip_norm=1.0, dp_noise_multiplier=0.01
    ))
    results["s6_differential_privacy"] = orch.run()

    # ------------------------------------------------------------------
    # Save results
    # ------------------------------------------------------------------
    os.makedirs("data/processed", exist_ok=True)
    out_path = "data/processed/stage2_results.json"

    # Strip numpy types for JSON serialisation
    def _jsonify(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        raise TypeError(f"Cannot serialise {type(obj)}")

    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=_jsonify)

    # ------------------------------------------------------------------
    # Summary Table
    # ------------------------------------------------------------------
    _print_divider("STAGE 2 RESULTS SUMMARY")
    print(f"\n{'Scenario':<55} {'Acc':>8} {'F1':>8} {'Time':>8}")
    print("-" * 82)
    for key, r in results.items():
        name = r["scenario_name"][:54]
        acc  = r["final_accuracy"] * 100
        f1   = r["final_f1_score"]
        t    = r["total_time_sec"]
        print(f"{name:<55} {acc:>7.2f}% {f1:>8.4f} {t:>7.1f}s")

    print(f"\n✅ All Stage 2 results saved to {out_path}")

    # Quick blockchain integrity check across all runs
    any_invalid = any(not r["chain_valid"] for r in results.values())
    if any_invalid:
        print("⚠️  WARNING: At least one blockchain chain failed integrity verification!")
    else:
        print("🔗 All blockchain chains verified — cryptographic integrity maintained.")

    return results


if __name__ == "__main__":
    main()
