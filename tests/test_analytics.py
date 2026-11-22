"""
Unit and Integration Tests for Research Intelligence Analytics & Dynamic Headline Cards.
Tests accuracy advantage in percentage points, attack isolation numerator/denominator,
cryptographic ledger validity, missing/malformed file handling, and dynamic metric reactivity.
"""

import os
import json
import tempfile
import pytest
from src.federated.analytics import compute_research_headline_metrics


class TestResearchAnalytics:
    """Tests dynamic extraction of headline research cards from experiment records."""

    def test_01_accuracy_advantage_calculation_in_percentage_points(self):
        """
        Verify that:
        1. Accuracy advantage is derived as the difference in percentage points (not percent change).
        2. S5 (74.587%) - S3 (43.076%) = +31.51 pp.
        3. Formatting string matches '+31.51 pp'.
        """
        metrics = compute_research_headline_metrics(filepath="data/processed/stage2_results.json")
        m_acc = metrics["accuracy_advantage"]

        assert m_acc["status"] == "available"
        assert isinstance(m_acc["diff_pp"], float)
        assert abs(m_acc["diff_pp"] - 31.51) < 0.05
        assert m_acc["diff_formatted"] == "+31.51 pp"
        assert abs(m_acc["defended_acc"] - 74.59) < 0.05
        assert abs(m_acc["undefended_acc"] - 43.08) < 0.05
        assert "percentage points" in m_acc["summary"]
        assert "pp" in m_acc["diff_formatted"]

    def test_02_attack_isolation_numerator_and_denominator(self):
        """
        Verify that:
        1. Attack isolation computes exact numerator (rejected) and denominator (submitted).
        2. Malicious client identification is distinguished from individual update rejections.
        3. For S4/S5 records, 4/4 malicious updates were rejected (100.0%).
        4. Node 3 quarantine in Rounds 3–5 left 0 poisoned updates in aggregation.
        """
        metrics = compute_research_headline_metrics(filepath="data/processed/stage2_results.json")
        m_atk = metrics["attack_isolation"]

        assert m_atk["status"] == "available"
        assert m_atk["malicious_updates_submitted"] == 4
        assert m_atk["malicious_updates_rejected"] == 4
        assert m_atk["isolation_rate_pct"] == 100.0
        assert m_atk["isolation_formatted"] == "100.0% (4/4)"
        assert m_atk["malicious_clients_identified"] == 1
        assert m_atk["total_malicious_clients"] == 1
        assert m_atk["client_identification_pct"] == 100.0
        assert m_atk["poisoned_updates_in_aggregation"] == 0
        assert "Rounds 3" in m_atk["quarantine_rounds"]

    def test_03_cryptographic_audit_integrity_without_unverified_overhead(self):
        """
        Verify that:
        1. Cryptographic integrity is derived from actual chain_valid records (6/6 valid chains).
        2. No unverified '<2.5s' numerical overhead is claimed as a proven research metric.
        3. Overhead status is explicitly marked as unverified pending formal profiling.
        """
        metrics = compute_research_headline_metrics(filepath="data/processed/stage2_results.json")
        m_cry = metrics["cryptographic_integrity"]

        assert m_cry["status"] == "available"
        assert m_cry["valid_chains_count"] == 6
        assert m_cry["total_scenarios_evaluated"] == 6
        assert m_cry["validity_pct"] == 100.0
        assert m_cry["overhead_claim_status"] == "unverified_pending_profiling"
        # Confirm that no hardcoded numerical '<2.5s' is reported as verified
        assert "2.5" not in m_cry["summary"]
        assert "unverified" in m_cry["summary"].lower() or "pending" in m_cry["summary"].lower()

    def test_04_handling_missing_artifact_file(self):
        """Verify graceful fallback to 'unavailable' status when result file is missing."""
        metrics = compute_research_headline_metrics(filepath="non_existent_results_path.json")

        assert metrics["accuracy_advantage"]["status"] == "unavailable"
        assert metrics["attack_isolation"]["status"] == "unavailable"
        assert metrics["cryptographic_integrity"]["status"] == "unavailable"
        assert "not found" in metrics["accuracy_advantage"]["reason"].lower()

    def test_05_handling_invalid_or_malformed_json(self):
        """Verify graceful fallback when artifact file contains corrupted JSON."""
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
            f.write("{corrupted_json_syntax: true, missing_quotes: [}")
            temp_path = f.name

        try:
            metrics = compute_research_headline_metrics(filepath=temp_path)
            assert metrics["accuracy_advantage"]["status"] == "unavailable"
            assert metrics["attack_isolation"]["status"] == "unavailable"
            assert metrics["cryptographic_integrity"]["status"] == "unavailable"
            assert "failed to parse" in metrics["accuracy_advantage"]["reason"].lower()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_06_handling_partial_or_incomplete_scenarios(self):
        """Verify safe handling when specific scenarios are missing from JSON."""
        partial_data = {
            "s1_honest_fedavg": {"final_accuracy": 0.58, "chain_valid": True}
        }
        metrics = compute_research_headline_metrics(results_data=partial_data)

        # S3 and S5 missing -> accuracy unavailable
        assert metrics["accuracy_advantage"]["status"] == "unavailable"
        assert "missing" in metrics["accuracy_advantage"]["reason"].lower()
        # S4 and S5 missing -> attack isolation unavailable
        assert metrics["attack_isolation"]["status"] == "unavailable"
        # S1 present -> crypto integrity available for 1 scenario
        assert metrics["cryptographic_integrity"]["status"] == "available"
        assert metrics["cryptographic_integrity"]["total_scenarios_evaluated"] == 1
        assert metrics["cryptographic_integrity"]["valid_chains_count"] == 1

    def test_07_dynamic_metric_reactivity_on_updated_results(self):
        """Verify that headline cards automatically update when underlying experiment values change."""
        custom_experiment_data = {
            "s3_signflip_no_defense": {"final_accuracy": 0.4000, "chain_valid": True},
            "s5_blockchain_signflip_defense": {
                "final_accuracy": 0.8500,
                "chain_valid": True,
                "round_history": [
                    {"round": 0},
                    {"round": 1, "rejected_client_ids": [3], "num_active_clients": 4},
                    {"round": 2, "rejected_client_ids": [3], "num_active_clients": 4},
                    {"round": 3, "rejected_client_ids": [], "num_active_clients": 4}
                ]
            }
        }
        metrics = compute_research_headline_metrics(results_data=custom_experiment_data)

        # 85.0% - 40.0% = +45.00 pp
        assert metrics["accuracy_advantage"]["status"] == "available"
        assert metrics["accuracy_advantage"]["diff_pp"] == 45.0
        assert metrics["accuracy_advantage"]["diff_formatted"] == "+45.00 pp"

        # 2 updates submitted, 2 rejected -> 100.0%
        assert metrics["attack_isolation"]["status"] == "available"
        assert metrics["attack_isolation"]["isolation_formatted"] == "100.0% (2/2)"
        assert metrics["attack_isolation"]["isolation_rate_pct"] == 100.0

        # Partial attack leakage simulation: 1 rejected, 1 accepted
        leakage_experiment_data = {
            "s3_signflip_no_defense": {"final_accuracy": 0.4000, "chain_valid": True},
            "s5_blockchain_signflip_defense": {
                "final_accuracy": 0.7000,
                "chain_valid": True,
                "round_history": [
                    {"round": 0},
                    {"round": 1, "rejected_client_ids": [3], "num_active_clients": 4},
                    {"round": 2, "rejected_client_ids": [], "num_active_clients": 5}  # Node 3 accepted (leakage)
                ]
            }
        }
        leakage_metrics = compute_research_headline_metrics(results_data=leakage_experiment_data)
        assert leakage_metrics["attack_isolation"]["isolation_rate_pct"] == 50.0
        assert leakage_metrics["attack_isolation"]["isolation_formatted"] == "50.0% (1/2)"
        assert leakage_metrics["attack_isolation"]["poisoned_updates_in_aggregation"] == 1
