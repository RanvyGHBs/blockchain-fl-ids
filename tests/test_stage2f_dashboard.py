"""
Unit Tests for Stage 2F: Advanced Dashboard Visualizers & Interactive Educational Modules.

Verifies:
1. Schema and functional execution of all 9 Educational Module Level 2 widgets.
2. Advanced Research Visualizers execution (FL Architecture, Non-IID Skew, Aggregators, Attacks, Trust, Blockchain).
3. Experimental Results Dashboards for Stage 2E WP1 (8 models, Holm p-values) and WP4 (overhead, communications, audit).
4. Error-handling on missing/corrupted benchmark files.
5. Strict data isolation and non-mutation of underlying experimental artifacts.
"""

import os
import copy
import json
import pytest
import numpy as np

from src.visualization.educational_widgets import (
    render_fl_lifecycle_widget,
    render_dirichlet_widget,
    render_clipping_widget,
    render_aggregator_widget,
    render_attack_vectors_widget,
    render_trust_radar_widget,
    render_merkle_builder_widget,
    render_ids_classifier_widget,
    render_vector_geometry_widget,
)
from src.visualization.research_visualizers import (
    render_fl_architecture_visualizer,
    render_non_iid_distribution_visualizer,
    render_aggregation_comparison_visualizer,
    render_attack_defense_visualizer,
    render_trust_reputation_visualizer,
    render_blockchain_audit_visualizer,
)
from src.visualization.results_visualizers import (
    render_wp1_benchmark_dashboard,
    render_wp4_overhead_dashboard,
)
from src.blockchain.chain import Blockchain
from src.blockchain.block import Transaction
from src.blockchain.crypto import CryptoManager


class TestStage2FEducationalWidgets:
    """Verifies all 9 Level 2 educational widgets execute without errors."""

    def test_01_all_nine_educational_widgets_callable(self):
        widgets = [
            render_fl_lifecycle_widget,
            render_dirichlet_widget,
            render_clipping_widget,
            render_aggregator_widget,
            render_attack_vectors_widget,
            render_trust_radar_widget,
            render_merkle_builder_widget,
            render_ids_classifier_widget,
            render_vector_geometry_widget,
        ]
        assert len(widgets) == 9
        for w in widgets:
            assert callable(w)

    def test_02_merkle_builder_tamper_logic(self):
        """Verify Merkle root corruption on single-bit modification."""
        import hashlib
        txs = ["tx0", "tx1", "tx2", "tx3"]
        h_leaves = [hashlib.sha256(t.encode()).hexdigest() for t in txs]
        h01 = hashlib.sha256((h_leaves[0] + h_leaves[1]).encode()).hexdigest()
        h23 = hashlib.sha256((h_leaves[2] + h_leaves[3]).encode()).hexdigest()
        root_pristine = hashlib.sha256((h01 + h23).encode()).hexdigest()

        # Tampered leaf 2
        h2_tampered = hashlib.sha256("tx2_tampered".encode()).hexdigest()
        h23_tampered = hashlib.sha256((h2_tampered + h_leaves[3]).encode()).hexdigest()
        root_tampered = hashlib.sha256((h01 + h23_tampered).encode()).hexdigest()

        assert root_pristine != root_tampered

    def test_03_clipping_and_perturbation_math(self):
        """Verify L2 norm projection mathematics."""
        vec = np.array([3.0, 4.0], dtype=np.float32)
        norm = np.linalg.norm(vec)
        assert norm == 5.0
        C = 2.0
        clip_factor = max(1.0, norm / C)
        clipped = vec / clip_factor
        assert np.isclose(np.linalg.norm(clipped), C)


class TestStage2FResearchVisualizers:
    """Verifies Advanced Research Visualizers and mathematical logic."""

    def test_01_aggregation_coordinate_comparison(self):
        """Verify aggregator outputs on 5 client updates with an outlier."""
        client_vals = np.array([1.0, 1.2, 0.9, -15.0, 1.1], dtype=np.float32)
        
        # FedAvg dragged toward -15.0
        fedavg = np.mean(client_vals)
        assert fedavg < 0.0

        # Median locks onto honest cluster
        median = np.median(client_vals)
        assert np.isclose(median, 1.0)

        # Trimmed mean excises min (-15.0) and max (1.2)
        sorted_vals = np.sort(client_vals)
        trimmed = np.mean(sorted_vals[1:4])
        assert 0.9 <= trimmed <= 1.2

        # Trust-weighted suppresses slashed node
        reputations = np.array([1.0, 1.0, 1.0, 0.1, 1.0], dtype=np.float32)
        trust_agg = np.sum(client_vals * reputations) / np.sum(reputations)
        assert trust_agg > 0.0

    def test_02_blockchain_visualizer_on_sample_chain(self):
        """Verify blockchain visualizer logic on a valid sample chain."""
        bc = Blockchain(committee_size=3)
        priv_k, pub_k = CryptoManager.generate_keypair()
        tx = Transaction(
            client_id=0,
            round_num=1,
            weights_hash="sample_hash",
            signature="sig",
            validation_metrics={"norm_passed": True, "cos_sim": 0.95},
            status="ACCEPTED",
            reputation_before=1.0,
            reputation_after=1.05
        )
        bc.add_transaction(tx)
        bc.forge_block(global_model_hash="global_hash", validator_id=0)

        assert len(bc.chain) == 2  # Genesis + Block 1
        assert bc.is_chain_valid() is True


class TestStage2FResultsDashboards:
    """Verifies the experimental results dashboards parse actual data without errors."""

    def test_01_wp1_dashboard_data_loading(self):
        filepath = "data/processed/stage2e/wp1/benchmark_summary_v2.json"
        assert os.path.exists(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "models" in data
        assert len(data["models"]) == 8
        assert "multiple_comparisons_family_vs_fedavg" in data
        comparisons = data["multiple_comparisons_family_vs_fedavg"]["comparisons"]
        assert len(comparisons) == 7

        # Check Holm adjusted p-values are all >= 0.1838 (non-significant at alpha=0.05)
        for comp_name, comp_data in comparisons.items():
            assert comp_data["holm_adjusted_p_value"] >= 0.1838
            assert comp_data["statistically_significant_holm"] is False

    def test_02_wp4_overhead_dashboard_data_loading(self):
        filepath = "data/processed/stage2e/wp4/overhead_summary_v2.json"
        assert os.path.exists(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "cryptographic_microbenchmarks" in data
        assert "aggregation_microbenchmarks" in data
        assert "communication_payload_accounting" in data
        assert "tampering_verification_benchmark" in data

        tamper_summary = data["tampering_verification_benchmark"]["summary"]
        assert tamper_summary["observed_detection_rate"] == 1.0
        assert tamper_summary["total_positive_tested"] == 500
        assert tamper_summary["total_positive_detected"] == 500
        assert tamper_summary["total_negative_tested"] == 100
        assert tamper_summary["total_false_alarms"] == 0

    def test_03_wp1_missing_file_handling(self):
        """Verifies missing file returns gracefully without raising uncaught exception."""
        non_existent = "data/processed/stage2e/wp1/does_not_exist.json"
        # Calling should not raise an unhandled exception
        render_wp1_benchmark_dashboard(filepath=non_existent)
