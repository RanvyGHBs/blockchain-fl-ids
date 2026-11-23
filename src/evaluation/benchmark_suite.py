"""
Multi-Seed Statistical Benchmark Suite.
Coordinates matched experimental evaluation across the 5-seed pilot ensemble:
[42, 101, 2024, 777, 999]
Executes Centralized, Local Silos, FedAvg, Median, Trimmed Mean, Multi-Krum, FoolsGold, and Trust-Weighted FedAvg.
Computes descriptive statistics, 95% Confidence Intervals, Paired t-tests (with Cohen's d_z),
Welch's independent t-tests, and Wilcoxon signed-rank tests with prospective power analysis.
"""

import os
import time
import json
import random
import hashlib
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import scipy.stats as stats
import torch

from src.data.nsl_kdd import NSLKDDLoader
from src.federated.orchestrator import FederatedOrchestrator
from src.evaluation.baselines import CentralizedBaseline, LocalSiloBaseline, aggregate_multikrum, FoolsGoldAggregator


# ---------------------------------------------------------------------------
# Statistical Analysis Functions
# ---------------------------------------------------------------------------

def compute_descriptive_stats(values: List[float]) -> Dict[str, Any]:
    """
    Computes sample mean, sample standard deviation, and 95% Student's t confidence interval.
    """
    arr = np.array(values, dtype=np.float64)
    n = len(arr)
    if n == 0:
        return {"mean": 0.0, "std": 0.0, "ci_95": [0.0, 0.0], "n": 0}
    if n == 1:
        return {"mean": float(arr[0]), "std": 0.0, "ci_95": [float(arr[0]), float(arr[0])], "n": 1}

    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))
    se = std / np.sqrt(n)

    # Critical value from Student's t distribution with n - 1 degrees of freedom
    t_crit = float(stats.t.ppf(0.975, df=n - 1))
    ci_lower = float(mean - t_crit * se)
    ci_upper = float(mean + t_crit * se)

    return {
        "mean": mean,
        "std": std,
        "se": se,
        "ci_95": [ci_lower, ci_upper],
        "ci_95_str": f"[{ci_lower:.4f}, {ci_upper:.4f}]",
        "t_crit": t_crit,
        "n": n
    }


def paired_t_test(values_a: List[float], values_b: List[float]) -> Dict[str, Any]:
    """
    Computes matched Paired t-test and Cohen's d_z effect size.
    Used for matched experimental runs evaluated on identical seeds and partitions.
    """
    arr_a = np.array(values_a, dtype=np.float64)
    arr_b = np.array(values_b, dtype=np.float64)
    if len(arr_a) != len(arr_b):
        raise ValueError(f"Lengths must match for paired t-test: len(a)={len(arr_a)} vs len(b)={len(arr_b)}")

    n = len(arr_a)
    if n < 2:
        return {"t_stat": 0.0, "p_value": 1.0, "df": 0, "cohens_d_z": 0.0, "significant": False}

    diffs = arr_a - arr_b
    mean_d = float(np.mean(diffs))
    std_d = float(np.std(diffs, ddof=1))

    if std_d < 1e-12:
        # Zero variance in differences
        return {
            "t_stat": 0.0 if abs(mean_d) < 1e-12 else float("inf"),
            "p_value": 1.0 if abs(mean_d) < 1e-12 else 0.0,
            "df": n - 1,
            "mean_difference": mean_d,
            "cohens_d_z": 0.0,
            "significant": False
        }

    res = stats.ttest_rel(arr_a, arr_b)
    t_stat = float(res.statistic)
    p_val = float(res.pvalue)
    cohens_d_z = float(mean_d / std_d)

    return {
        "t_stat": t_stat,
        "p_value": p_val,
        "df": n - 1,
        "mean_difference": mean_d,
        "std_difference": std_d,
        "cohens_d_z": cohens_d_z,
        "significant": bool(p_val < 0.05)
    }


def welch_t_test(values_a: List[float], values_b: List[float]) -> Dict[str, Any]:
    """
    Computes Welch's independent-samples t-test for unmatched groups with unequal variances.
    """
    res = stats.ttest_ind(values_a, values_b, equal_var=False)
    # Welch-Satterthwaite degrees of freedom
    s1, s2 = np.var(values_a, ddof=1), np.var(values_b, ddof=1)
    n1, n2 = len(values_a), len(values_b)
    df_denom = ((s1 / n1) ** 2 / (n1 - 1)) + ((s2 / n2) ** 2 / (n2 - 1))
    df = ((s1 / n1) + (s2 / n2)) ** 2 / max(1e-12, df_denom)

    return {
        "t_stat": float(res.statistic),
        "p_value": float(res.pvalue),
        "df": float(df),
        "significant": bool(res.pvalue < 0.05)
    }


def wilcoxon_signed_rank_test(values_a: List[float], values_b: List[float]) -> Dict[str, Any]:
    """
    Computes Wilcoxon signed-rank test.
    Important Limitation: With n=5 matched pairs, the minimum possible two-sided p-value is 0.0625 (> 0.05).
    Therefore, for n=5, results must be interpreted as exploratory rank analysis.
    """
    arr_a = np.array(values_a, dtype=np.float64)
    arr_b = np.array(values_b, dtype=np.float64)
    diffs = arr_a - arr_b

    # Filter zero differences
    nonzero_diffs = diffs[diffs != 0]
    n_nonzero = len(nonzero_diffs)

    if n_nonzero < 3:
        return {
            "w_stat": 0.0,
            "p_value": 1.0,
            "n_nonzero": n_nonzero,
            "note": "Too few non-zero differences for Wilcoxon test.",
            "significant": False
        }

    try:
        res = stats.wilcoxon(arr_a, arr_b, alternative="two-sided")
        w_stat = float(res.statistic)
        p_val = float(res.pvalue)
    except Exception as e:
        w_stat = 0.0
        p_val = 1.0

    return {
        "w_stat": w_stat,
        "p_value": p_val,
        "n_nonzero": n_nonzero,
        "min_possible_p_value_n5": 0.0625,
        "is_exploratory_due_to_small_sample": bool(n_nonzero <= 5),
        "significant": bool(p_val < 0.05)
    }


def prospective_power_analysis(effect_size_dz: float, alpha: float = 0.05, power: float = 0.80) -> Dict[str, Any]:
    """
    Calculates prospective sample size required to achieve target statistical power.
    Formula: N = ((z_{1 - alpha/2} + z_{1 - beta}) / d_z)^2
    """
    z_alpha = float(stats.norm.ppf(1 - alpha / 2))
    z_beta = float(stats.norm.ppf(power))
    if effect_size_dz <= 0.0:
        return {"required_sample_size": 9999, "power": power, "alpha": alpha}

    n_exact = ((z_alpha + z_beta) / effect_size_dz) ** 2
    n_required = int(np.ceil(n_exact))

    return {
        "target_power": power,
        "significance_level": alpha,
        "hypothesized_effect_size_dz": effect_size_dz,
        "z_alpha_half": z_alpha,
        "z_beta": z_beta,
        "required_sample_size": max(2, n_required)
    }


# ---------------------------------------------------------------------------
# Multi-Seed Benchmark Suite Coordinator
# ---------------------------------------------------------------------------

class MultiSeedBenchmarkSuite:
    """
    Executes controlled multi-seed benchmark evaluations across the 5 pilot seeds:
    [42, 101, 2024, 777, 999].
    Guarantees strict matched conditions across algorithms and datasets.
    """

    DEFAULT_SEEDS = [42, 101, 2024, 777, 999]

    def __init__(
        self,
        seeds: Optional[List[int]] = None,
        num_rounds: int = 3,
        device: str = "cpu",
        output_dir: str = "data/processed/stage2e/wp1"
    ):
        self.seeds = seeds or list(self.DEFAULT_SEEDS)
        self.num_rounds = num_rounds
        self.device = device
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def reseed_environment(self, seed: int):
        """Strictly reseeds all random number generators."""
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

    def run_clean_baselines_suite(self) -> Dict[str, Any]:
        """
        Executes all non-adversarial baseline algorithms across all configured seeds.
        Baselines:
        1. Centralized-IDS
        2. Local Silo IDS
        3. Standard FedAvg
        4. Coordinate Median
        5. Trimmed Mean
        6. Multi-Krum (f=1, m=1; constraint n=5 >= 2*1+3 holds!)
        7. FoolsGold (standalone Sybil aggregator)
        8. Trust-Weighted FedAvg (Stage 2D baseline)
        """
        all_runs: Dict[str, List[Dict[str, Any]]] = {
            "centralized_ids": [],
            "local_silos": [],
            "fedavg": [],
            "coordinate_median": [],
            "trimmed_mean": [],
            "multikrum_f1": [],
            "foolsgold": [],
            "trust_weighted": []
        }

        for seed in self.seeds:
            print(f"\n--- [WP1 Benchmark] Executing Seed {seed} ---")
            self.reseed_environment(seed)

            # Load NSL-KDD with strict 3-way research isolation
            loader = NSLKDDLoader(binary=True, seed=seed)
            X_train, y_train, X_val, y_val, X_test, y_test = loader.preprocess_isolated(val_size=1000)

            # 1. Centralized Baseline
            cb = CentralizedBaseline(
                input_dim=X_train.shape[1],
                num_classes=2,
                epochs=self.num_rounds,  # Match total federated epochs
                batch_size=64,
                lr=0.002,
                device=self.device,
                seed=seed
            )
            res_cent = cb.train_and_evaluate(X_train, y_train, X_test, y_test)
            all_runs["centralized_ids"].append(res_cent)

            # 2. Setup standard federated base config
            base_fl_config = {
                "track": "Track A",
                "dataset": "nsl_kdd",
                "seed": seed,
                "device": self.device,
                "num_clients": 5,
                "num_rounds": self.num_rounds,
                "local_epochs": 1,
                "batch_size": 64,
                "lr": 0.002,
                "X_train": X_train.copy(),
                "y_train": y_train.copy(),
                "X_val": X_val.copy(),
                "y_val": y_val.copy(),
                "X_test": X_test.copy(),
                "y_test": y_test.copy(),
                "feature_names": loader.feature_columns,
                "class_names": loader.get_class_names()
            }

            # 3. Local Silos Baseline (extract partitions from orchestrator setup)
            orch_silos = FederatedOrchestrator(dict(base_fl_config, scenario_name="setup_silos"))
            orch_silos.setup()
            partitions = {c.client_id: (c.X_local, c.y_local) for c in orch_silos.clients}
            lsb = LocalSiloBaseline(
                input_dim=X_train.shape[1],
                num_classes=2,
                epochs=self.num_rounds,
                batch_size=64,
                lr=0.002,
                device=self.device,
                seed=seed
            )
            res_silos = lsb.train_and_evaluate_silos(partitions, X_test, y_test)
            all_runs["local_silos"].append(res_silos)

            # 4. Standard FedAvg
            cfg_fedavg = dict(base_fl_config, scenario_name="fedavg", attack_enabled=False, defense_enabled=False, aggregation_algorithm="fedavg")
            orch_fedavg = FederatedOrchestrator(cfg_fedavg)
            res_fedavg = orch_fedavg.run()
            all_runs["fedavg"].append(self._extract_fl_summary(res_fedavg, seed, "fedavg"))

            # 5. Coordinate Median
            cfg_med = dict(base_fl_config, scenario_name="median", attack_enabled=False, defense_enabled=False, aggregation_algorithm="median")
            orch_med = FederatedOrchestrator(cfg_med)
            res_med = orch_med.run()
            all_runs["coordinate_median"].append(self._extract_fl_summary(res_med, seed, "coordinate_median"))

            # 6. Trimmed Mean
            cfg_trim = dict(base_fl_config, scenario_name="trimmed_mean", attack_enabled=False, defense_enabled=False, aggregation_algorithm="trimmed_mean")
            orch_trim = FederatedOrchestrator(cfg_trim)
            res_trim = orch_trim.run()
            all_runs["trimmed_mean"].append(self._extract_fl_summary(res_trim, seed, "trimmed_mean"))

            # 7. Multi-Krum (f=1, m=1; clean setup)
            res_krum = self._run_custom_aggregator_fl(base_fl_config, agg_type="multikrum", seed=seed)
            all_runs["multikrum_f1"].append(res_krum)

            # 8. FoolsGold (standalone Sybil defense)
            res_fg = self._run_custom_aggregator_fl(base_fl_config, agg_type="foolsgold", seed=seed)
            all_runs["foolsgold"].append(res_fg)

            # 9. Trust-Weighted FedAvg (Stage 2D baseline)
            cfg_tw = dict(base_fl_config, scenario_name="trust_weighted", attack_enabled=False, defense_enabled=True, aggregation_algorithm="trust_weighted")
            orch_tw = FederatedOrchestrator(cfg_tw)
            res_tw = orch_tw.run()
            all_runs["trust_weighted"].append(self._extract_fl_summary(res_tw, seed, "trust_weighted"))

        # Compute summary statistics and hypothesis tests
        summary = self._compute_benchmark_summary(all_runs)

        # Save artifacts
        per_seed_path = os.path.join(self.output_dir, "per_seed_runs.json")
        with open(per_seed_path, "w") as f:
            json.dump(all_runs, f, indent=2)

        summary_path = os.path.join(self.output_dir, "benchmark_summary.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        return summary

    def _extract_fl_summary(self, res: Dict[str, Any], seed: int, model_type: str) -> Dict[str, Any]:
        """Extracts standard metric dictionary from orchestrator run."""
        final_eval = res.get("final_evaluation", {})
        return {
            "model_type": model_type,
            "seed": seed,
            "accuracy": float(res.get("final_accuracy", final_eval.get("accuracy", 0.0))),
            "f1_macro": float(res.get("final_f1_score_macro", final_eval.get("f1_macro", 0.0))),
            "precision_macro": float(res.get("final_precision_macro", final_eval.get("precision_macro", 0.0))),
            "recall_macro": float(res.get("final_recall_macro", final_eval.get("recall_macro", 0.0))),
            "execution_time_sec": float(res.get("total_time_sec", res.get("execution_time", 0.0)))
        }

    def _run_custom_aggregator_fl(self, base_fl_config: Dict[str, Any], agg_type: str, seed: int) -> Dict[str, Any]:
        """
        Executes a controlled federated round sequence using custom aggregators (Multi-Krum or FoolsGold).
        Preserves identical clients, local SGD training, and data partitions.
        """
        t0 = time.perf_counter()
        orch = FederatedOrchestrator(dict(base_fl_config, scenario_name=f"custom_{agg_type}", attack_enabled=False, defense_enabled=False))
        orch.setup()

        # Initialize aggregator state
        fg_agg = FoolsGoldAggregator(num_clients=orch.num_clients) if agg_type == "foolsgold" else None

        for round_idx in range(1, orch.num_rounds + 1):
            client_weights = []
            client_updates_dict = {}
            current_global = orch.server.get_global_weights()
            for client in orch.clients:
                client.set_global_weights(current_global)
                client.local_train(epochs=orch.local_epochs, batch_size=orch.batch_size, lr=orch.lr, round_num=round_idx)
                w = client.get_local_weights()
                client_weights.append(w)
                client_updates_dict[client.client_id] = w

            if agg_type == "multikrum":
                # Valid: n=5, f=1, m=1
                new_global, _ = aggregate_multikrum(client_weights, f=1, m=1)
            elif agg_type == "foolsgold":
                new_global, _ = fg_agg.aggregate(client_updates_dict, global_weights=current_global)
            else:
                raise ValueError(f"Unknown custom agg_type {agg_type}")

            orch.server.set_global_weights(new_global)

        # Final evaluation on held-out test set
        X_test, y_test = base_fl_config["X_test"], base_fl_config["y_test"]
        final_eval = orch.server.evaluate(X_test, y_test)
        exec_time = time.perf_counter() - t0

        return {
            "model_type": agg_type,
            "seed": seed,
            "accuracy": float(final_eval.get("accuracy", 0.0)),
            "f1_macro": float(final_eval.get("f1_score_macro", final_eval.get("f1_macro", 0.0))),
            "precision_macro": float(final_eval.get("precision_macro", 0.0)),
            "recall_macro": float(final_eval.get("recall_macro", 0.0)),
            "execution_time_sec": exec_time
        }

    def _compute_benchmark_summary(self, all_runs: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Computes statistical summaries, confidence intervals, and matched paired comparisons."""
        summary: Dict[str, Any] = {
            "seeds": self.seeds,
            "num_seeds": len(self.seeds),
            "num_rounds": self.num_rounds,
            "models": {},
            "comparisons_vs_fedavg": {}
        }

        for model_name, runs in all_runs.items():
            accs = [r["accuracy"] if "accuracy" in r else r["mean_accuracy"] for r in runs]
            f1s = [r["f1_macro"] if "f1_macro" in r else r["mean_f1_macro"] for r in runs]

            summary["models"][model_name] = {
                "per_seed_accuracy": accs,
                "per_seed_f1_macro": f1s,
                "accuracy_stats": compute_descriptive_stats(accs),
                "f1_macro_stats": compute_descriptive_stats(f1s)
            }

        # Matched Paired comparisons against standard FedAvg baseline
        fedavg_accs = summary["models"]["fedavg"]["per_seed_accuracy"]
        for model_name in all_runs.keys():
            if model_name == "fedavg":
                continue
            model_accs = summary["models"][model_name]["per_seed_accuracy"]
            summary["comparisons_vs_fedavg"][model_name] = {
                "paired_t_test": paired_t_test(model_accs, fedavg_accs),
                "wilcoxon_test": wilcoxon_signed_rank_test(model_accs, fedavg_accs)
            }

        return summary
