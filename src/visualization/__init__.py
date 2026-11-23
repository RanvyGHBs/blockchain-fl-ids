"""
Visualization and Interactive Educational Components for Stage 2F.
Provides reusable research visualizers, educational interactive widgets, and experimental results dashboards.
"""

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

__all__ = [
    "render_fl_lifecycle_widget",
    "render_dirichlet_widget",
    "render_clipping_widget",
    "render_aggregator_widget",
    "render_attack_vectors_widget",
    "render_trust_radar_widget",
    "render_merkle_builder_widget",
    "render_ids_classifier_widget",
    "render_vector_geometry_widget",
    "render_fl_architecture_visualizer",
    "render_non_iid_distribution_visualizer",
    "render_aggregation_comparison_visualizer",
    "render_attack_defense_visualizer",
    "render_trust_reputation_visualizer",
    "render_blockchain_audit_visualizer",
    "render_wp1_benchmark_dashboard",
    "render_wp4_overhead_dashboard",
]
