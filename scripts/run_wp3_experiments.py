"""
WP3 Multi-Seed Experimental Validation and Ablation Runner (Resumable).
Executes controlled comparative experiments:
1. Multi-Seed Benchmark across Seeds [42, 101, 2024, 777, 999]:
   - Clean DP Baseline (Uncalibrated vs. Calibrated)
   - Gaussian Noise Attack (Uncalibrated vs. Calibrated)
   - Model Scaling Attack (Uncalibrated vs. Calibrated)
   - Sign Flipping Attack (Uncalibrated vs. Calibrated)
   - Label Flipping Attack (Uncalibrated vs. Calibrated)
2. Dynamic Defense Matrix Ablation (8 Configurations)
3. Noise Multiplier Sensitivity Sweep (sigma in [0.5, 1.0, 1.5])
4. Statistical Hypothesis Testing & Holm-Bonferroni Correction

Results are saved incrementally to data/processed/wp3/*.json
"""

import os
import sys
import json
import time
import math
from typing import Dict, List, Any, Tuple
import numpy as np
from scipy import stats

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.nsl_kdd import NSLKDDLoader
from src.config import get_approved_research_config, ExecutionMode, PrivacyRandomnessMode
from src.federated.orchestrator import FederatedOrchestrator


SEEDS = [42, 101, 2024, 777, 999]
ATTACK_TYPES = ["clean_dp", "gaussian_noise", "model_scaling", "sign_flip", "label_flip"]


def create_scenario_config(
    seed: int,
    attack_type: str,
    calibration_mode: str,
    sigma: float = 1.0,
    enable_norm: bool = True,
    enable_cos: bool = True,
    enable_loss: bool = True,
    data_dict: Dict[str, Any] = None
) -> Dict[str, Any]:
    attack_enabled = (attack_type != "clean_dp")
    cfg = get_approved_research_config(
        num_rounds=5,
        num_clients=5,
        seed=seed,
        dp_enabled=True,
        dp_clip_norm=1.0,
        dp_noise_multiplier=sigma,
        dp_target_delta=1e-5,
        attack_enabled=attack_enabled,
        attack_type=attack_type if attack_enabled else "gaussian_noise",
        malicious_client_ids=[3] if attack_enabled else [],
        defense_enabled=True,
        trust_calibration_mode=calibration_mode
    )
    cfg_dict = {k: getattr(cfg, k) for k in cfg.__dataclass_fields__}
    cfg_dict["scenario_name"] = f"wp3_{attack_type}_{calibration_mode}_seed_{seed}_sig_{sigma}"
    cfg_dict["defense_matrix"] = {
        "trust_engine": True,
        "norm_check": enable_norm,
        "cosine_check": enable_cos,
        "loss_check": enable_loss,
        "reputation": True,
        "quarantine": True,
        "signature_verify": True,
        "blockchain": True
    }
    if data_dict:
        cfg_dict.update(data_dict)
    return cfg_dict


def run_single_experiment(cfg_dict: Dict[str, Any]) -> Dict[str, Any]:
    t0 = time.time()
    orch = FederatedOrchestrator(cfg_dict)
    res = orch.run()
    elapsed = time.time() - t0

    # Extract metrics
    cum = orch.cumulative_accounting
    hon_sub = cum["honest"]["submitted"]
    hon_rej = cum["honest"]["rejected_total"]
    mal_sub = cum["malicious"]["submitted"]
    mal_rej = cum["malicious"]["rejected_total"]
    mal_flag = cum["malicious"]["flagged_trust"]

    fpr = float(hon_rej / hon_sub) if hon_sub > 0 else 0.0
    murr = float(mal_rej / mal_sub) if mal_sub > 0 else 0.0
    mudr = float(mal_flag / mal_sub) if mal_sub > 0 else 0.0

    last_log = orch.round_logs[-1] if len(orch.round_logs) > 0 else {}
    final_acc = float(res.get("final_accuracy", 0.0))
    final_f1 = float(last_log.get("f1_score", 0.0))
    final_loss = float(last_log.get("loss", 0.0))

    quarantined = [cid for cid in range(orch.num_clients) if orch.reputation_mgr.is_quarantined(cid)]
    hon_quarantined = [cid for cid in quarantined if cid not in orch.malicious_client_ids]
    mal_quarantined = [cid for cid in quarantined if cid in orch.malicious_client_ids]

    return {
        "scenario_name": cfg_dict.get("scenario_name"),
        "seed": orch.seed,
        "attack_type": orch.attack_type if orch.attack_enabled else "clean_dp",
        "attack_enabled": orch.attack_enabled,
        "calibration_mode": orch.trust_engine.calibration_mode,
        "sigma": orch.dp_noise_multiplier,
        "elapsed_seconds": round(elapsed, 2),
        "final_accuracy": round(final_acc, 6),
        "final_f1": round(final_f1, 6),
        "final_loss": round(final_loss, 4),
        "honest_submitted": hon_sub,
        "honest_rejected": hon_rej,
        "honest_fpr": round(fpr, 6),
        "honest_quarantined_count": len(hon_quarantined),
        "malicious_submitted": mal_sub,
        "malicious_rejected": mal_rej,
        "malicious_detection_rate": round(murr, 6),
        "malicious_flagged_rate": round(mudr, 6),
        "malicious_quarantined_count": len(mal_quarantined),
        "chain_height": len(orch.blockchain.chain),
        "chain_valid": orch.blockchain.is_chain_valid(),
        "final_reputations": {cid: round(orch.reputation_mgr.get_reputation(cid), 4) for cid in range(orch.num_clients)}
    }


def main():
    print("=" * 80)
    print("STARTING WP3 EXPERIMENTAL SUITE (RESUMABLE)")
    print("=" * 80)
    out_dir = "data/processed/wp3"
    os.makedirs(out_dir, exist_ok=True)

    # 1. Preprocess NSL-KDD once
    print("\n[Step 1/4] Preprocessing NSL-KDD dataset...")
    loader = NSLKDDLoader(binary=True, seed=42)
    X_train, y_train, X_val, y_val, X_test, y_test = loader.preprocess_isolated()
    data_dict = {
        "X_train": X_train, "y_train": y_train,
        "X_val": X_val, "y_val": y_val,
        "X_test": X_test, "y_test": y_test,
        "feature_names": loader.feature_columns,
        "class_names": loader.get_class_names()
    }
    print(f"Data ready: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}, Feats={X_train.shape[1]}")

    # 2. Multi-Seed Benchmarks across 5 Seeds
    print("\n[Step 2/4] Executing Multi-Seed Paired Benchmarks...")
    bench_file = os.path.join(out_dir, "multi_seed_benchmarks.json")
    if os.path.exists(bench_file):
        with open(bench_file, "r") as f:
            benchmark_results = json.load(f)
    else:
        benchmark_results = {
            "metadata": {
                "dataset": "NSL-KDD",
                "clients": 5,
                "rounds": 5,
                "clip_norm": 1.0,
                "noise_multiplier": 1.0,
                "delta": 1e-5,
                "reported_epsilon": 13.2565,
                "seeds": SEEDS
            },
            "runs": []
        }

    completed_scenarios = {r["scenario_name"] for r in benchmark_results["runs"]}

    for att in ATTACK_TYPES:
        for seed in SEEDS:
            for mode in ["uncalibrated", "privacy_aware"]:
                sc_name = f"wp3_{att}_{mode}_seed_{seed}_sig_1.0"
                if sc_name in completed_scenarios:
                    print(f"  [Skipping Completed] {sc_name}")
                    continue

                print(f"  -> Running: attack={att}, mode={mode}, seed={seed}...")
                cfg = create_scenario_config(seed, att, mode, sigma=1.0, data_dict=data_dict)
                run_res = run_single_experiment(cfg)
                benchmark_results["runs"].append(run_res)
                completed_scenarios.add(sc_name)

                # Save incrementally
                with open(bench_file, "w") as f:
                    json.dump(benchmark_results, f, indent=2)

                print(f"     Result: Acc={run_res['final_accuracy']:.4f}, FPR={run_res['honest_fpr']:.4f}, MalRej={run_res['malicious_detection_rate']:.4f}, QuarantinedHonest={run_res['honest_quarantined_count']}")

    print(f"Multi-seed benchmarks fully completed ({len(benchmark_results['runs'])} runs).")

    # 3. Dynamic Defense Matrix Ablation (8 Configurations on Seed 42 under Gaussian Attack)
    print("\n[Step 3/4] Executing Dynamic Defense Matrix Ablation Matrix...")
    abl_file = os.path.join(out_dir, "ablation_benchmarks.json")
    if os.path.exists(abl_file):
        with open(abl_file, "r") as f:
            ablation_results = json.load(f)
    else:
        ablation_results = {"metadata": {"seed": 42, "attack_type": "gaussian_noise", "sigma": 1.0}, "runs": []}

    completed_ablations = {r.get("ablation_name") for r in ablation_results["runs"]}

    ablation_matrix = [
        {"name": "uncalibrated_baseline", "mode": "uncalibrated", "norm": True, "cos": True, "loss": True},
        {"name": "norm_only", "mode": "privacy_aware", "norm": True, "cos": False, "loss": False},
        {"name": "cosine_only", "mode": "privacy_aware", "norm": False, "cos": True, "loss": False},
        {"name": "loss_only", "mode": "privacy_aware", "norm": False, "cos": False, "loss": True},
        {"name": "norm_cosine", "mode": "privacy_aware", "norm": True, "cos": True, "loss": False},
        {"name": "norm_loss", "mode": "privacy_aware", "norm": True, "cos": False, "loss": True},
        {"name": "cosine_loss", "mode": "privacy_aware", "norm": False, "cos": True, "loss": True},
        {"name": "full_three_tier", "mode": "privacy_aware", "norm": True, "cos": True, "loss": True},
    ]

    for abl in ablation_matrix:
        if abl["name"] in completed_ablations:
            print(f"  [Skipping Completed Ablation] {abl['name']}")
            continue

        print(f"  -> Ablation: {abl['name']} (Norm={abl['norm']}, Cos={abl['cos']}, Loss={abl['loss']})...")
        cfg = create_scenario_config(
            seed=42, attack_type="gaussian_noise", calibration_mode=abl["mode"],
            enable_norm=abl["norm"], enable_cos=abl["cos"], enable_loss=abl["loss"],
            data_dict=data_dict
        )
        cfg["scenario_name"] = f"wp3_ablation_{abl['name']}"
        run_res = run_single_experiment(cfg)
        run_res["ablation_name"] = abl["name"]
        run_res["tiers_active"] = {"norm": abl["norm"], "cosine": abl["cos"], "loss": abl["loss"]}
        ablation_results["runs"].append(run_res)
        completed_ablations.add(abl["name"])

        # Save incrementally
        with open(abl_file, "w") as f:
            json.dump(ablation_results, f, indent=2)

        print(f"     Result: Acc={run_res['final_accuracy']:.4f}, FPR={run_res['honest_fpr']:.4f}, DetRate={run_res['malicious_detection_rate']:.4f}")

    print(f"Ablation benchmarks fully completed ({len(ablation_results['runs'])} runs).")

    # 4. Noise Multiplier Sensitivity Sweep (sigma in [0.5, 1.0, 1.5] on Clean DP)
    print("\n[Step 4/4] Executing Noise Sensitivity Sweep...")
    sens_file = os.path.join(out_dir, "noise_sensitivity_benchmarks.json")
    if os.path.exists(sens_file):
        with open(sens_file, "r") as f:
            sensitivity_results = json.load(f)
    else:
        sensitivity_results = {"metadata": {"seed": 42, "sigmas": [0.5, 1.0, 1.5]}, "runs": []}

    completed_sens = {r["scenario_name"] for r in sensitivity_results["runs"]}

    for sig in [0.5, 1.0, 1.5]:
        for mode in ["uncalibrated", "privacy_aware"]:
            sc_name = f"wp3_sensitivity_clean_dp_{mode}_seed_42_sig_{sig}"
            if sc_name in completed_sens:
                print(f"  [Skipping Completed Sensitivity] {sc_name}")
                continue

            print(f"  -> Sensitivity: sigma={sig}, mode={mode}...")
            cfg = create_scenario_config(seed=42, attack_type="clean_dp", calibration_mode=mode, sigma=sig, data_dict=data_dict)
            cfg["scenario_name"] = sc_name
            run_res = run_single_experiment(cfg)
            sensitivity_results["runs"].append(run_res)
            completed_sens.add(sc_name)

            # Save incrementally
            with open(sens_file, "w") as f:
                json.dump(sensitivity_results, f, indent=2)

            print(f"     Result: FPR={run_res['honest_fpr']:.4f}, Acc={run_res['final_accuracy']:.4f}")

    print(f"Sensitivity benchmarks fully completed ({len(sensitivity_results['runs'])} runs).")

    # 5. Statistical Hypothesis Testing & Holm-Bonferroni Correction
    print("\nComputing Statistical Summaries & Holm-Bonferroni Correction...")
    stat_summary = compute_statistical_summary(benchmark_results["runs"])
    stat_file = os.path.join(out_dir, "statistical_summary.json")
    with open(stat_file, "w") as f:
        json.dump(stat_summary, f, indent=2)
    print(f"Saved statistical summary to {stat_file}")

    print("\n" + "=" * 80)
    print("ALL WP3 EXPERIMENTS SUCCESSFULLY COMPLETED")
    print("=" * 80)


def compute_statistical_summary(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary = {}
    for att in ATTACK_TYPES:
        uncal_runs = [r for r in runs if r["attack_type"] == att and r["calibration_mode"] == "uncalibrated"]
        cal_runs = [r for r in runs if r["attack_type"] == att and r["calibration_mode"] == "privacy_aware"]

        uncal_runs = sorted(uncal_runs, key=lambda x: x["seed"])
        cal_runs = sorted(cal_runs, key=lambda x: x["seed"])

        uncal_fpr = np.array([r["honest_fpr"] for r in uncal_runs])
        cal_fpr = np.array([r["honest_fpr"] for r in cal_runs])

        uncal_acc = np.array([r["final_accuracy"] for r in uncal_runs])
        cal_acc = np.array([r["final_accuracy"] for r in cal_runs])

        uncal_det = np.array([r["malicious_detection_rate"] for r in uncal_runs])
        cal_det = np.array([r["malicious_detection_rate"] for r in cal_runs])

        diff_fpr = uncal_fpr - cal_fpr
        mean_diff_fpr = float(np.mean(diff_fpr))
        std_diff_fpr = float(np.std(diff_fpr, ddof=1)) if len(diff_fpr) > 1 else 0.0

        cohen_d_fpr = float(mean_diff_fpr / std_diff_fpr) if std_diff_fpr > 1e-9 else (999.0 if mean_diff_fpr > 0 else 0.0)

        if len(diff_fpr) > 1 and np.any(diff_fpr != 0):
            t_stat_fpr, p_val_fpr = stats.ttest_rel(uncal_fpr, cal_fpr)
        else:
            t_stat_fpr, p_val_fpr = 0.0, 1.0

        summary[att] = {
            "uncalibrated_fpr_mean": float(np.mean(uncal_fpr)),
            "uncalibrated_fpr_std": float(np.std(uncal_fpr, ddof=1)),
            "calibrated_fpr_mean": float(np.mean(cal_fpr)),
            "calibrated_fpr_std": float(np.std(cal_fpr, ddof=1)),
            "fpr_reduction": float(np.mean(uncal_fpr) - np.mean(cal_fpr)),
            "fpr_t_statistic": float(t_stat_fpr),
            "fpr_p_value_raw": float(p_val_fpr),
            "fpr_cohen_d": float(cohen_d_fpr),
            "uncalibrated_acc_mean": float(np.mean(uncal_acc)),
            "uncalibrated_acc_std": float(np.std(uncal_acc, ddof=1)),
            "calibrated_acc_mean": float(np.mean(cal_acc)),
            "calibrated_acc_std": float(np.std(cal_acc, ddof=1)),
            "acc_difference": float(np.mean(cal_acc) - np.mean(uncal_acc)),
            "uncalibrated_det_mean": float(np.mean(uncal_det)),
            "calibrated_det_mean": float(np.mean(cal_det)),
            "det_rate_difference": float(np.mean(cal_det) - np.mean(uncal_det)),
            "paired_runs": len(uncal_runs)
        }

    p_values = [(att, summary[att]["fpr_p_value_raw"]) for att in ATTACK_TYPES]
    p_values.sort(key=lambda x: x[1])

    m = len(p_values)
    for rank, (att, p_val) in enumerate(p_values):
        alpha_holm = 0.05 / (m - rank)
        is_significant = p_val <= alpha_holm
        summary[att]["holm_bonferroni_rank"] = rank + 1
        summary[att]["holm_bonferroni_alpha"] = float(alpha_holm)
        summary[att]["holm_bonferroni_significant"] = bool(is_significant)

    return summary


if __name__ == "__main__":
    main()
