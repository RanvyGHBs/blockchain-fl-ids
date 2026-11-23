"""
Unit Tests for Stage 2E.3.1: Statistical Integrity & Overhead Reporting Corrections.
Verifies:
1. Holm-Bonferroni multiple-comparison correction mathematics and step-down procedure.
2. Seed-level paired t-test arithmetic and degrees of freedom.
3. Confidence interval calculations (distinguishing seed-level n=5 from test-set N=22,544).
4. Communication accounting arithmetic (KiB vs KB, unicast vs broadcast models).
5. Tampering category counts and legitimate control false alarm verification.
"""

import json
import numpy as np
import scipy.stats as stats
import pytest


class TestStage2E31Corrections:

    @pytest.fixture
    def wp1_summary(self):
        with open("data/processed/stage2e/wp1/benchmark_summary.json") as f:
            return json.load(f)

    @pytest.fixture
    def wp4_summary(self):
        with open("data/processed/stage2e/wp4/overhead_summary.json") as f:
            return json.load(f)

    def test_holm_bonferroni_step_down_arithmetic(self, wp1_summary):
        """Verifies Holm-Bonferroni correction over the family of 7 comparisons vs FedAvg."""
        models = wp1_summary["models"]
        fedavg_accs = np.array(models["fedavg"]["per_seed_accuracy"])

        comparisons = [
            "centralized_ids", "local_silos", "trust_weighted",
            "foolsgold", "trimmed_mean", "multikrum_f1", "coordinate_median"
        ]

        raw_results = []
        for m in comparisons:
            m_accs = np.array(models[m]["per_seed_accuracy"])
            diffs = m_accs - fedavg_accs
            std_d = float(np.std(diffs, ddof=1))
            if std_d < 1e-12:
                p_val = 1.0
            else:
                p_val = float(stats.ttest_rel(m_accs, fedavg_accs).pvalue)
            raw_results.append((m, p_val))

        # Sort ascending by p-value
        sorted_p = sorted(raw_results, key=lambda x: x[1])
        m_hypotheses = len(sorted_p)  # 7
        alpha = 0.05

        # Rank 1: Centralized IDS
        rank_1_model, rank_1_p = sorted_p[0]
        assert rank_1_model == "centralized_ids"
        assert abs(rank_1_p - 0.026270) < 1e-4

        # Rank 1 threshold = alpha / 7
        rank_1_threshold = alpha / 7.0
        assert abs(rank_1_threshold - (0.05 / 7.0)) < 1e-6
        # Crucial test: Raw p (0.02627) > 0.00714 -> Step-down terminates immediately!
        assert rank_1_p > rank_1_threshold

        # Rank 2: Coordinate Median
        rank_2_model, rank_2_p = sorted_p[1]
        assert rank_2_model == "coordinate_median"
        assert abs(rank_2_p - 0.034738) < 1e-4
        rank_2_threshold = alpha / 6.0
        assert rank_2_p > rank_2_threshold

        # Calculate Holm adjusted p-values
        cum_max = 0.0
        holm_adj_p = {}
        for i, (name, p) in enumerate(sorted_p, start=1):
            unclipped = (m_hypotheses - i + 1) * p
            cum_max = max(cum_max, unclipped)
            holm_adj_p[name] = min(1.0, cum_max)

        # Confirm all adjusted p-values are >= 0.1838
        for name, adj_p in holm_adj_p.items():
            assert adj_p >= 0.1838
            # None are significant after Holm-Bonferroni at alpha = 0.05
            assert adj_p > 0.05

    def test_confidence_interval_sampling_unit(self, wp1_summary):
        """Verifies that 95% CIs are based on seed count n=5 (df=4) and not test-set size."""
        models = wp1_summary["models"]
        for m_name, m_data in models.items():
            accs = np.array(m_data["per_seed_accuracy"])
            n = len(accs)
            assert n == 5

            mean = float(np.mean(accs))
            std = float(np.std(accs, ddof=1))
            se = std / np.sqrt(5)
            t_crit = float(stats.t.ppf(0.975, df=4))

            assert abs(t_crit - 2.776445) < 1e-4

            expected_lower = mean - t_crit * se
            expected_upper = mean + t_crit * se

            stored_ci = m_data["accuracy_stats"]["ci_95"]
            assert abs(stored_ci[0] - expected_lower) < 1e-6
            assert abs(stored_ci[1] - expected_upper) < 1e-6

    def test_communication_accounting_exact_arithmetic(self, wp4_summary):
        """Verifies exact communication byte arithmetic, unit conversions, and unicast vs broadcast models."""
        comm = wp4_summary["communication_payload_analysis"]

        raw_bytes = comm["raw_tensor_nbytes"]
        pickle_bytes = comm["serialized_pickle_bytes"]
        sig_bytes = comm["signature_string_bytes"]
        num_clients = 5

        # Raw tensor: 26594 * 4 = 106376 bytes
        assert raw_bytes == 26594 * 4
        assert pickle_bytes == 106537
        assert sig_bytes == 96

        # Upstream per client
        client_up = comm["client_upstream_bytes_per_round"]
        assert client_up == 106661
        # In KiB (binary kibibytes, divisor 1024)
        assert abs(comm["client_upstream_kb"] - (106661 / 1024.0)) < 1e-4

        # Downstream per client
        server_down = comm["server_downstream_bytes_per_round"]
        assert server_down == 106579
        assert abs(comm["server_downstream_kb"] - (106579 / 1024.0)) < 1e-4

        # Unicast Total Round (5 * up + 5 * down)
        expected_unicast_total = (client_up * num_clients) + (server_down * num_clients)
        assert expected_unicast_total == 1066200
        assert comm["total_round_network_bytes"] == expected_unicast_total
        assert abs(comm["total_round_network_kb"] - (1066200 / 1024.0)) < 1e-4

        # Broadcast Alternative Total (5 * up + 1 * down)
        expected_broadcast_total = (client_up * num_clients) + server_down
        assert expected_broadcast_total == 639884
        broadcast_kib = expected_broadcast_total / 1024.0
        assert abs(broadcast_kib - 624.8867) < 1e-2

    def test_tampering_trial_accounting_and_fpr(self, wp4_summary):
        """Verifies tampering benchmark breakdown across categories and negative controls."""
        tamper = wp4_summary["tampering_verification_benchmark"]

        assert tamper["total_positive_tested"] == 500
        assert tamper["total_positive_detected"] == 500
        assert tamper["observed_detection_rate"] == 1.0

        assert tamper["total_negative_tested"] == 100
        assert tamper["total_false_alarms"] == 0
        assert tamper["observed_false_alarm_rate"] == 0.0

        cats = tamper["per_category_results"]
        expected_categories = [
            "payload_modification",
            "block_deletion",
            "block_reordering",
            "hash_chain_modification",
            "merkle_root_inconsistency"
        ]
        assert list(cats.keys()) == expected_categories

        for cat_name in expected_categories:
            cdata = cats[cat_name]
            assert cdata["tested"] == 100
            assert cdata["detected"] == 100
            assert cdata["detection_rate"] == 1.0
            assert cdata["mean_audit_latency_ms"] > 0.0
