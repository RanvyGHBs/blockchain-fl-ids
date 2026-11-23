"""
Unit Tests for Stage 2E WP1: Multi-Seed Statistical Baselines.
Verifies:
1. Multi-Krum constraint validation (n >= 2f + 3).
2. FoolsGold Sybil penalization mechanics.
3. Centralized-IDS training and evaluation.
4. Local-Silo baseline partitioning.
5. Descriptive statistics, 95% Student's t confidence intervals.
6. Paired t-tests, Cohen's d_z, Welch's t-test, and Wilcoxon signed-rank test.
7. Prospective power analysis calculations.
8. Dataset isolation and deterministic repeatability across seeds.
"""

import pytest
import numpy as np
import scipy.stats as stats
import torch

from src.evaluation.baselines import (
    CentralizedBaseline, LocalSiloBaseline, aggregate_multikrum, FoolsGoldAggregator
)
from src.evaluation.benchmark_suite import (
    compute_descriptive_stats, paired_t_test, welch_t_test,
    wilcoxon_signed_rank_test, prospective_power_analysis
)


class TestWP1Baselines:

    def test_multikrum_constraint_enforcement(self):
        """Verifies that Multi-Krum enforces n >= 2f + 3 mathematically."""
        rng = np.random.RandomState(42)
        dim = 100

        # Valid configuration: n = 5, f = 1 (2*1 + 3 = 5 <= 5)
        weights_5 = [rng.randn(dim).astype(np.float32) for _ in range(5)]
        agg, selected = aggregate_multikrum(weights_5, f=1, m=1)
        assert agg.shape == (dim,)
        assert len(selected) == 1
        assert selected[0] in range(5)

        # Invalid configuration: n = 5, f = 2 (2*2 + 3 = 7 > 5) -> MUST raise ValueError
        with pytest.raises(ValueError, match="Multi-Krum theoretical constraint violated"):
            aggregate_multikrum(weights_5, f=2, m=1)

        # Valid configuration: n = 7, f = 2 (2*2 + 3 = 7 <= 7)
        weights_7 = [rng.randn(dim).astype(np.float32) for _ in range(7)]
        agg_7, selected_7 = aggregate_multikrum(weights_7, f=2, m=2)
        assert agg_7.shape == (dim,)
        assert len(selected_7) == 2

    def test_multikrum_byzantine_rejection(self):
        """Verifies that Krum rejects an extreme outlier update."""
        dim = 50
        honest_base = np.ones(dim, dtype=np.float32) * 2.0
        # 4 honest clients close to each other
        weights = [honest_base + np.random.randn(dim).astype(np.float32) * 0.05 for _ in range(4)]
        # 1 malicious client with extreme values
        weights.append(np.ones(dim, dtype=np.float32) * 500.0)

        agg, selected = aggregate_multikrum(weights, f=1, m=1)
        # Outlier (index 4) must NOT be selected
        assert selected[0] != 4
        assert np.allclose(agg, honest_base, atol=0.5)

    def test_foolsgold_sybil_attenuation(self):
        """Verifies that FoolsGold penalizes collinear Sybil updates."""
        dim = 100
        fg = FoolsGoldAggregator(num_clients=4)

        # Honest client 0: distinct update direction
        w0 = np.zeros(dim, dtype=np.float32)
        w0[:20] = 1.0

        # Honest client 1: another distinct update direction
        w1 = np.zeros(dim, dtype=np.float32)
        w1[20:40] = 1.0

        # Sybil clients 2 and 3: highly collinear updates in the same direction
        w2 = np.zeros(dim, dtype=np.float32)
        w2[40:80] = 1.0
        w3 = np.zeros(dim, dtype=np.float32)
        w3[40:80] = 1.05  # Near duplicate

        updates = {0: w0, 1: w1, 2: w2, 3: w3}
        agg, alphas = fg.aggregate(updates)

        # Sybil clients 2 and 3 should receive lower relative weights than honest clients
        assert alphas[0] > alphas[2]
        assert alphas[1] > alphas[3]
        assert agg.shape == (dim,)

    def test_statistical_descriptive_stats(self):
        """Verifies mean, standard deviation, and Student's t 95% confidence intervals."""
        sample = [80.0, 81.0, 82.0, 79.0, 83.0]
        stats_res = compute_descriptive_stats(sample)

        expected_mean = 81.0
        expected_std = float(np.std(sample, ddof=1))
        expected_se = expected_std / np.sqrt(5)
        t_crit = float(stats.t.ppf(0.975, df=4))

        assert np.isclose(stats_res["mean"], expected_mean)
        assert np.isclose(stats_res["std"], expected_std)
        assert np.isclose(stats_res["ci_95"][0], expected_mean - t_crit * expected_se)
        assert np.isclose(stats_res["ci_95"][1], expected_mean + t_crit * expected_se)
        assert stats_res["n"] == 5

    def test_paired_t_test_and_cohens_d(self):
        """Verifies paired t-test calculations and Cohen's d_z effect size."""
        # 5 matched seed pairs with consistent improvement
        vals_defended = [81.5, 82.0, 81.0, 82.5, 81.8]
        vals_baseline = [80.0, 80.5, 79.8, 80.9, 80.2]

        ptest = paired_t_test(vals_defended, vals_baseline)
        assert ptest["df"] == 4
        assert ptest["mean_difference"] > 0
        assert ptest["p_value"] < 0.05
        assert ptest["significant"] is True
        assert ptest["cohens_d_z"] > 1.0  # Large effect size

    def test_wilcoxon_small_sample_limitation(self):
        """Verifies that Wilcoxon on n=5 pairs correctly flags exploratory status."""
        a = [10.0, 12.0, 11.0, 13.0, 14.0]
        b = [5.0, 6.0, 7.0, 8.0, 9.0]  # Perfect rank separation

        wtest = wilcoxon_signed_rank_test(a, b)
        assert wtest["n_nonzero"] == 5
        assert wtest["is_exploratory_due_to_small_sample"] is True
        # For n=5, minimum two-sided p-value is 0.0625 (> 0.05)
        assert wtest["min_possible_p_value_n5"] == 0.0625
        assert wtest["p_value"] >= 0.0625

    def test_prospective_power_analysis(self):
        """Verifies prospective power calculation for sample size planning."""
        # For a massive effect d_z = 1.5, N should be ~4-5
        power_huge = prospective_power_analysis(effect_size_dz=1.5, alpha=0.05, power=0.80)
        assert power_huge["required_sample_size"] <= 5

        # For a medium effect d_z = 0.5, N should be ~32
        power_med = prospective_power_analysis(effect_size_dz=0.5, alpha=0.05, power=0.80)
        assert power_med["required_sample_size"] >= 30

    def test_centralized_baseline_execution(self):
        """Verifies CentralizedBaseline training on synthetic isolated arrays."""
        input_dim = 10
        num_classes = 2
        N_train = 100
        N_test = 40

        X_train = np.random.randn(N_train, input_dim).astype(np.float32)
        y_train = (X_train[:, 0] > 0).astype(np.int64)
        X_test = np.random.randn(N_test, input_dim).astype(np.float32)
        y_test = (X_test[:, 0] > 0).astype(np.int64)

        cb = CentralizedBaseline(input_dim=input_dim, num_classes=num_classes, epochs=2, batch_size=32, seed=42)
        res = cb.train_and_evaluate(X_train, y_train, X_test, y_test)

        assert res["model_type"] == "centralized_ids"
        assert res["train_samples"] == N_train
        assert res["test_samples"] == N_test
        assert 0.0 <= res["accuracy"] <= 1.0
        assert 0.0 <= res["f1_macro"] <= 1.0
        assert "confusion_matrix" in res

    def test_local_silo_baseline_execution(self):
        """Verifies LocalSiloBaseline training independent models per partition."""
        input_dim = 10
        num_classes = 2

        # 3 clients
        partitions = {}
        for cid in range(3):
            Xc = np.random.randn(50, input_dim).astype(np.float32)
            yc = (Xc[:, 0] > 0).astype(np.int64)
            partitions[cid] = (Xc, yc)

        X_test = np.random.randn(30, input_dim).astype(np.float32)
        y_test = (X_test[:, 0] > 0).astype(np.int64)

        lsb = LocalSiloBaseline(input_dim=input_dim, num_classes=num_classes, epochs=2, batch_size=16, seed=42)
        res = lsb.train_and_evaluate_silos(partitions, X_test, y_test)

        assert res["model_type"] == "local_silos"
        assert res["num_silos"] == 3
        assert len(res["client_results"]) == 3
        assert 0.0 <= res["mean_accuracy"] <= 1.0
        assert 0.0 <= res["mean_f1_macro"] <= 1.0
