"""
Stage 2E.3 — WP1 Execution Runner: Multi-Seed Statistical Baselines.
Evaluates:
- Centralized-IDS (ceiling)
- Local Silos (uncooperative floor)
- Standard FedAvg
- Coordinate Median
- Trimmed Mean (trim_ratio=0.2)
- Multi-Krum (f=1, m=1)
- FoolsGold (standalone Sybil aggregator)
- Trust-Weighted FedAvg (Stage 2D baseline)

Across the 5-seed pilot: [42, 101, 2024, 777, 999].
Saves output artifacts to:
- data/processed/stage2e/wp1/per_seed_runs.json
- data/processed/stage2e/wp1/benchmark_summary.json
"""

import sys
import os
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.evaluation.benchmark_suite import MultiSeedBenchmarkSuite


def main():
    print("=" * 80)
    print("STAGE 2E.3 — WP1: MULTI-SEED STATISTICAL BASELINE EVALUATION")
    print("Dataset: NSL-KDD (Binary Classification, Strict 3-Way Research Isolation)")
    print("Seeds: [42, 101, 2024, 777, 999]")
    print("=" * 80)

    t0 = time.time()
    suite = MultiSeedBenchmarkSuite(
        seeds=[42, 101, 2024, 777, 999],
        num_rounds=3,
        device="cpu",
        output_dir="data/processed/stage2e/wp1"
    )

    summary = suite.run_clean_baselines_suite()
    elapsed = time.time() - t0

    print("\n" + "=" * 80)
    print(f"WP1 Benchmark Evaluation Completed in {elapsed:.2f} seconds.")
    print("=" * 80)
    print("\n--- Model Performance Summary (Mean +- Std [95% CI]) ---")
    for model_name, mdata in summary["models"].items():
        acc_stats = mdata["accuracy_stats"]
        f1_stats = mdata["f1_macro_stats"]
        print(
            f"{model_name:<20}: "
            f"Acc = {acc_stats['mean']*100:.2f}% +- {acc_stats['std']*100:.2f}% {acc_stats['ci_95_str']} | "
            f"F1 = {f1_stats['mean']:.4f} +- {f1_stats['std']:.4f} {f1_stats['ci_95_str']}"
        )

    print("\n--- Matched Paired t-Test vs FedAvg ---")
    for comp_name, comp_data in summary["comparisons_vs_fedavg"].items():
        tt = comp_data["paired_t_test"]
        wt = comp_data["wilcoxon_test"]
        print(
            f"{comp_name:<20} vs FedAvg: "
            f"t = {tt['t_stat']:+.4f}, p = {tt['p_value']:.4f}, d_z = {tt['cohens_d_z']:+.4f} | "
            f"Wilcoxon W = {wt['w_stat']:.1f}, p = {wt['p_value']:.4f}"
        )


if __name__ == "__main__":
    main()
