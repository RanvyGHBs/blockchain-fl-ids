"""
Stage 2D Benchmark Runner: Advanced Attack Scenarios & Multi-Attack Defense Studio (v2).
Executes systematic benchmarks across adversarial attack models with matched controls:
1. Honest Baseline (FedAvg)
2. Targeted Label-Flipping (Undefended FedAvg vs Defended FedAvg [S2b] vs Defended Trust-Weighted [S3])
3. Sybil Coalition Attack (Undefended Median vs Defended Median [S4b] vs Defended Trust-Weighted [S5])
4. Parameterized Byzantine Perturbation (Undefended FedAvg vs Defended FedAvg [S6b] vs Defended Trust-Weighted [S7])
   * Threat model: Parameterized stealth-constrained Byzantine perturbation using geometric threshold alignment
     (not a closed-loop feedback-adaptive attack).
5. Gaussian Noise Poisoning (Undefended vs Defended)
6. Sign-Flipping Attack (Undefended vs Defended)
7. Dynamic Defense Matrix Ablation Suite (Tier-by-Tier ablation)

Saves all experimental results strictly to:
  data/processed/stage2d/multi_attack_benchmarks_v2.json
Preserves data/processed/stage2_results.json and historical multi_attack_benchmarks.json byte-for-byte identical.
"""

import os
import json
import time
import random
from typing import Dict, Any
import numpy as np
import torch

from src.data.nsl_kdd import NSLKDDLoader
from src.federated.orchestrator import FederatedOrchestrator


def run_stage2d_benchmarks(num_rounds: int = 3, seed: int = 42, output_filename: str = "multi_attack_benchmarks_v3.json") -> Dict[str, Any]:
    print("=" * 80)
    print("STAGE 2D: ADVANCED ATTACK SCENARIOS & MULTI-ATTACK DEFENSE BENCHMARKS (v3)")
    print("=" * 80)

    # Load NSL-KDD with strict 3-way isolation
    loader = NSLKDDLoader(binary=True, seed=seed)
    X_train, y_train, X_val, y_val, X_test, y_test = loader.preprocess_isolated()
    feature_names = loader.feature_columns
    class_names = loader.get_class_names()

    base_config = {
        "track": "Track A",
        "dataset": "nsl_kdd",
        "seed": seed,
        "device": "cpu",
        "num_clients": 5,
        "num_rounds": num_rounds,
        "local_epochs": 1,
        "batch_size": 64,
        "lr": 0.002,
        "X_train": X_train.copy(),
        "y_train": y_train.copy(),
        "X_val": X_val.copy(),
        "y_val": y_val.copy(),
        "X_test": X_test.copy(),
        "y_test": y_test.copy(),
        "feature_names": feature_names,
        "class_names": class_names,
    }

    scenarios = [
        # 1. Honest Baseline
        {
            "key": "s1_honest_baseline",
            "name": "S1: Honest Baseline (FedAvg)",
            "attack_enabled": False,
            "defense_enabled": False,
            "aggregation": "fedavg",
        },
        # 2. Targeted Label-Flipping
        {
            "key": "s2_targeted_labelflip_undefended",
            "name": "S2: Targeted Label-Flip (Undefended FedAvg)",
            "attack_enabled": True,
            "attack_type": "targeted_label_flip",
            "malicious_client_ids": [3],
            "label_flip_source": 1,
            "label_flip_target": 0,
            "label_flip_ratio": 1.0,
            "defense_enabled": False,
            "aggregation": "fedavg",
        },
        {
            "key": "s2b_targeted_labelflip_fedavg_defended",
            "name": "S2b: Targeted Label-Flip (Defended FedAvg)",
            "attack_enabled": True,
            "attack_type": "targeted_label_flip",
            "malicious_client_ids": [3],
            "label_flip_source": 1,
            "label_flip_target": 0,
            "label_flip_ratio": 1.0,
            "defense_enabled": True,
            "aggregation": "fedavg",
        },
        {
            "key": "s3_targeted_labelflip_defended",
            "name": "S3: Targeted Label-Flip (Defended Trust-Weighted)",
            "attack_enabled": True,
            "attack_type": "targeted_label_flip",
            "malicious_client_ids": [3],
            "label_flip_source": 1,
            "label_flip_target": 0,
            "label_flip_ratio": 1.0,
            "defense_enabled": True,
            "aggregation": "trust_weighted",
        },
        # 3. Sybil Coalition Attack
        {
            "key": "s4_sybil_coalition_median_undefended",
            "name": "S4: Sybil Coalition (Undefended Median Aggregation)",
            "attack_enabled": True,
            "attack_type": "sybil_coalition",
            "malicious_client_ids": [2, 3],
            "sybil_intensity": 2.5,
            "defense_enabled": False,
            "aggregation": "median",
        },
        {
            "key": "s4b_sybil_coalition_median_defended",
            "name": "S4b: Sybil Coalition (Defended Median Aggregation)",
            "attack_enabled": True,
            "attack_type": "sybil_coalition",
            "malicious_client_ids": [2, 3],
            "sybil_intensity": 2.5,
            "defense_enabled": True,
            "aggregation": "median",
        },
        {
            "key": "s5_sybil_coalition_defended",
            "name": "S5: Sybil Coalition (Defended Trust-Weighted)",
            "attack_enabled": True,
            "attack_type": "sybil_coalition",
            "malicious_client_ids": [2, 3],
            "sybil_intensity": 2.5,
            "defense_enabled": True,
            "aggregation": "trust_weighted",
        },
        # 4. Parameterized Byzantine Perturbation
        {
            "key": "s6_adaptive_byzantine_undefended",
            "name": "S6: Parameterized Byzantine (Undefended FedAvg)",
            "attack_enabled": True,
            "attack_type": "adaptive_byzantine",
            "malicious_client_ids": [3],
            "adaptive_stealth_factor": 0.8,
            "defense_enabled": False,
            "aggregation": "fedavg",
        },
        {
            "key": "s6b_parameterized_byzantine_fedavg_defended",
            "name": "S6b: Parameterized Byzantine (Defended FedAvg)",
            "attack_enabled": True,
            "attack_type": "adaptive_byzantine",
            "malicious_client_ids": [3],
            "adaptive_stealth_factor": 0.8,
            "defense_enabled": True,
            "aggregation": "fedavg",
        },
        {
            "key": "s7_adaptive_byzantine_defended",
            "name": "S7: Parameterized Byzantine (Defended Trust-Weighted)",
            "attack_enabled": True,
            "attack_type": "adaptive_byzantine",
            "malicious_client_ids": [3],
            "adaptive_stealth_factor": 0.8,
            "defense_enabled": True,
            "aggregation": "trust_weighted",
        },
        # 5. Gaussian Noise
        {
            "key": "s8_gaussian_noise_undefended",
            "name": "S8: Gaussian Noise Poisoning (Undefended FedAvg)",
            "attack_enabled": True,
            "attack_type": "gaussian_noise",
            "malicious_client_ids": [3],
            "defense_enabled": False,
            "aggregation": "fedavg",
        },
        {
            "key": "s9_gaussian_noise_defended",
            "name": "S9: Gaussian Noise Poisoning (Defended Trust-Weighted)",
            "attack_enabled": True,
            "attack_type": "gaussian_noise",
            "malicious_client_ids": [3],
            "defense_enabled": True,
            "aggregation": "trust_weighted",
        },
        # 6. Sign-Flipping
        {
            "key": "s10_sign_flip_undefended",
            "name": "S10: Sign-Flipping Attack (Undefended FedAvg)",
            "attack_enabled": True,
            "attack_type": "sign_flip",
            "malicious_client_ids": [3],
            "defense_enabled": False,
            "aggregation": "fedavg",
        },
        {
            "key": "s11_sign_flip_defended",
            "name": "S11: Sign-Flipping Attack (Defended Trust-Weighted)",
            "attack_enabled": True,
            "attack_type": "sign_flip",
            "malicious_client_ids": [3],
            "defense_enabled": True,
            "aggregation": "trust_weighted",
        },
        # 7. Defense Matrix Ablation Suite
        {
            "key": "s12_ablation_norm_only",
            "name": "S12: Defense Ablation (Tier 1 Norm Only)",
            "attack_enabled": True,
            "attack_type": "sign_flip",
            "malicious_client_ids": [3],
            "defense_enabled": True,
            "aggregation": "trust_weighted",
            "defense_matrix": {
                "trust_engine": True,
                "norm_check": True,
                "cosine_check": False,
                "loss_check": False,
                "reputation": True,
                "quarantine": True,
                "signature_verify": True,
                "blockchain": True
            }
        },
        {
            "key": "s13_ablation_cosine_only",
            "name": "S13: Defense Ablation (Tier 2 Cosine Only)",
            "attack_enabled": True,
            "attack_type": "sign_flip",
            "malicious_client_ids": [3],
            "defense_enabled": True,
            "aggregation": "trust_weighted",
            "defense_matrix": {
                "trust_engine": True,
                "norm_check": False,
                "cosine_check": True,
                "loss_check": False,
                "reputation": True,
                "quarantine": True,
                "signature_verify": True,
                "blockchain": True
            }
        },
        {
            "key": "s14_ablation_loss_only",
            "name": "S14: Defense Ablation (Tier 3 Loss Only)",
            "attack_enabled": True,
            "attack_type": "sign_flip",
            "malicious_client_ids": [3],
            "defense_enabled": True,
            "aggregation": "trust_weighted",
            "defense_matrix": {
                "trust_engine": True,
                "norm_check": False,
                "cosine_check": False,
                "loss_check": True,
                "reputation": True,
                "quarantine": True,
                "signature_verify": True,
                "blockchain": True
            }
        },
        {
            "key": "s15_ablation_no_quarantine",
            "name": "S15: Defense Ablation (No Quarantine)",
            "attack_enabled": True,
            "attack_type": "gaussian_noise",
            "malicious_client_ids": [3],
            "defense_enabled": True,
            "aggregation": "trust_weighted",
            "defense_matrix": {
                "trust_engine": True,
                "norm_check": True,
                "cosine_check": True,
                "loss_check": True,
                "reputation": True,
                "quarantine": False,
                "signature_verify": True,
                "blockchain": True
            }
        }
    ]

    benchmark_results: Dict[str, Any] = {
        "metadata": {
            "title": "Stage 2D Multi-Attack & Advanced Defense Evaluation Suite",
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "dataset": "NSL-KDD Cyber-Defense Benchmark (Track A)",
            "num_clients": 5,
            "num_rounds": num_rounds,
            "seed": seed,
            "total_scenarios": len(scenarios)
        },
        "scenarios": {}
    }

    t0_all = time.time()
    for sc in scenarios:
        key = sc["key"]
        print(f"\n---> Running {sc['name']}...")
        scenario_seed = sc.get("seed", seed)

        # Independently initialize all RNGs at the beginning of every scenario
        random.seed(scenario_seed)
        np.random.seed(scenario_seed)
        torch.manual_seed(scenario_seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(scenario_seed)

        cfg = dict(base_config)
        cfg["scenario_name"] = sc["name"]
        cfg["attack_enabled"] = sc["attack_enabled"]
        cfg["defense_enabled"] = sc["defense_enabled"]
        cfg["aggregation_algorithm"] = sc.get("aggregation", "fedavg")

        if "attack_type" in sc:
            cfg["attack_type"] = sc["attack_type"]
        if "malicious_client_ids" in sc:
            cfg["malicious_client_ids"] = sc["malicious_client_ids"]
        if "label_flip_source" in sc:
            cfg["label_flip_source"] = sc["label_flip_source"]
        if "label_flip_target" in sc:
            cfg["label_flip_target"] = sc["label_flip_target"]
        if "label_flip_ratio" in sc:
            cfg["label_flip_ratio"] = sc["label_flip_ratio"]
        if "sybil_intensity" in sc:
            cfg["sybil_intensity"] = sc["sybil_intensity"]
        if "adaptive_stealth_factor" in sc:
            cfg["adaptive_stealth_factor"] = sc["adaptive_stealth_factor"]
        if "defense_matrix" in sc:
            cfg["defense_matrix"] = sc["defense_matrix"]

        orch = FederatedOrchestrator(cfg)
        res = orch.run()
        benchmark_results["scenarios"][key] = res

    total_duration = time.time() - t0_all
    benchmark_results["metadata"]["total_duration_sec"] = round(total_duration, 2)

    # Save results to output_filename (default: multi_attack_benchmarks_v2.json)
    out_dir = os.path.join("data", "processed", "stage2d")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, output_filename)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_results, f, indent=2)

    print(f"\n" + "=" * 80)
    print(f"✅ STAGE 2D BENCHMARKS COMPLETE ({total_duration:.1f}s)")
    print(f"Results written to: {out_path}")
    print("=" * 80)

    return benchmark_results


if __name__ == "__main__":
    run_stage2d_benchmarks(num_rounds=3, seed=42)
