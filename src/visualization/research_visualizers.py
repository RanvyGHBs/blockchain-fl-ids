"""
Advanced Research Visualizers for Stage 2F.
Implements:
1. Federated Learning Architecture Visualizer
2. Non-IID Data Distribution Visualizer
3. Aggregation Algorithm Comparison Visualizer
4. Attack and Defense Visualizer
5. Trust and Reputation Visualizer
6. Blockchain Audit Visualizer
"""

import copy
import hashlib
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.data.partitioner import FederatedPartitioner
from src.blockchain.audit_verifier import AuditVerifier, SyntheticTamperSuite
from src.federated.aggregators import (
    aggregate_fedavg,
    aggregate_median,
    aggregate_trimmed_mean,
    aggregate_trust_weighted,
)
from src.evaluation.baselines import (
    aggregate_multikrum,
    FoolsGoldAggregator,
)


def render_fl_architecture_visualizer(num_clients: int = 5):
    """
    3.1 Federated Learning Architecture Visualizer.
    Interactive visualization of the federated learning lifecycle across 5 simulated clients.
    """
    st.subheader("🔄 Federated Learning Architecture & Collaborative Lifecycle")
    st.caption("Interactive visualizer of local training, weight transmission, trust evaluation, and server aggregation.")

    st.markdown("""
    <div style="background-color: #0f172a; border: 1px solid #1e293b; border-left: 4px solid #3b82f6; border-radius: 6px; padding: 12px 16px; margin-bottom: 15px;">
        <b>Architectural Scope:</b> The 5 clients are <b>simulated processes</b> executing on local hardware within a unified PyTorch orchestration session. 
        They model autonomous enterprise subnets holding isolated data slices, but do not operate across physically independent distributed networks.
    </div>
    """, unsafe_allow_html=True)

    selected_round = st.slider("Select Communication Round to Inspect", min_value=1, max_value=5, value=1)
    
    stages = [
        {"num": 1, "name": "Global Broadcast", "actor": "Federated Server", "action": f"Server broadcasts global weights w^{selected_round-1} to all {num_clients} simulated clients."},
        {"num": 2, "name": "Local SGD Training", "actor": "Clients 0–4", "action": f"Each client trains w^{selected_round-1} on its private non-IID data for E=1 local epoch. Raw records never leave client memory."},
        {"num": 3, "name": "Update Transmission", "actor": "Clients 0–4", "action": "Clients serialize model weight vectors, sign them with private ECDSA P-256 keys, and transmit them upstream."},
        {"num": 4, "name": "Trust & Audit Inspection", "actor": "Multi-Criteria Trust Engine", "action": "Server validates ECDSA signatures, checks L2 norm bounding, evaluates cosine consensus to median, and tests loss delta."},
        {"num": 5, "name": "Robust Aggregation", "actor": "Federated Server", "action": f"Server filters malicious updates, aggregates surviving updates into w^{selected_round}, and forges a tamper-evident audit block."}
    ]

    selected_stage = st.radio("Lifecycle Stage", [f"Stage {s['num']}: {s['name']}" for s in stages], horizontal=True)
    curr_stage_idx = int(selected_stage.split(":")[0].replace("Stage ", "")) - 1
    curr_stage = stages[curr_stage_idx]

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown(f"""
        <div style="background-color: #1e293b; border-radius: 8px; padding: 18px; border: 1px solid #3b82f6;">
            <h4 style="margin-top:0; color: #60a5fa;">📍 Stage {curr_stage['num']}: {curr_stage['name']}</h4>
            <p style="font-size: 14px; color: #cbd5e1;"><b>Primary Actor:</b> {curr_stage['actor']}</p>
            <p style="font-size: 14px; color: #94a3b8;">{curr_stage['action']}</p>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        # Visual state diagram using Plotly
        fig = go.Figure()
        
        # Server node
        fig.add_trace(go.Scatter(
            x=[2], y=[2], mode="markers+text", marker=dict(size=40, color="#3b82f6"),
            text=["Federated Server<br>(Aggregator)"], textposition="top center", name="Server"
        ))

        # 5 Client nodes
        client_x = [0, 1, 2, 3, 4]
        client_y = [0, 0, 0, 0, 0]
        client_labels = [f"Node-{i}<br>(Simulated)" for i in range(num_clients)]
        client_colors = ["#10b981", "#10b981", "#10b981", "#ef4444" if selected_round >= 2 else "#10b981", "#10b981"]

        fig.add_trace(go.Scatter(
            x=client_x, y=client_y, mode="markers+text",
            marker=dict(size=30, color=client_colors),
            text=client_labels, textposition="bottom center", name="Clients"
        ))

        # Transmission arrows depending on stage
        for cx in client_x:
            if curr_stage_idx == 0:  # Broadcast (Server -> Clients)
                fig.add_annotation(x=cx, y=0.3, ax=2, ay=1.7, xref="x", yref="y", axref="x", ayref="y",
                                   showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="#60a5fa")
            elif curr_stage_idx in (2, 3):  # Upload / Inspect (Clients -> Server)
                fig.add_annotation(x=2, y=1.7, ax=cx, ay=0.3, xref="x", yref="y", axref="x", ayref="y",
                                   showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="#10b981" if cx != 3 else "#ef4444")

        fig.update_layout(
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.5, 4.5]),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.8, 2.8]),
            margin=dict(l=10, r=10, t=20, b=10),
            height=260,
            template="plotly_dark",
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

    # Data vs Model Distinction Table
    st.markdown("#### 🔒 Privacy Boundary: Local Data vs. Transmitted Payloads")
    st.markdown("""
    | Component | Location | Transmission Status | Cryptographic Protection |
    | :--- | :--- | :--- | :--- |
    | **Raw Network Packets / Features** | Local Client Memory Only | **NEVER Transmitted** (100% Data Sovereignty) | Isolated within client partition |
    | **Local Parameter Weights Vector ($w_k$)** | Client $\\to$ Server | **Transmitted** (106,537 bytes / 104.04 KiB) | Signed via ECDSA SECP256R1 |
    | **Cryptographic Signature & Model Hash** | Block Header / Ledger | **Publicly Audited** | SHA-256 Merkle root binding |
    """)


def render_non_iid_distribution_visualizer(X_train: np.ndarray, y_train: np.ndarray, num_classes: int = 2, class_names: Optional[List[str]] = None):
    """
    3.2 Non-IID Data Distribution Visualizer.
    Visualizes Dirichlet-based partitioning across clients and calculates statistical heterogeneity.
    """
    st.subheader("📊 Non-IID Dirichlet Data Heterogeneity Visualizer")
    st.caption("Inspects how Dirichlet-based statistical partitioning (α = 0.5) distributes class proportions across simulated nodes.")

    partitioner = FederatedPartitioner(num_clients=5, non_iid=True, alpha=0.5, seed=42)
    client_splits = partitioner.partition(X_train, y_train)
    stats = partitioner.get_distribution_stats(client_splits)

    c_left, c_right = st.columns([1, 1])

    with c_left:
        # Stacked bar chart of class counts per client
        fig = go.Figure()
        clients_labels = [f"Node-{cid}" for cid in range(5)]
        palette = ["#10b981", "#ef4444", "#3b82f6", "#f59e0b", "#8b5cf6"]

        for c_idx in range(num_classes):
            c_label = class_names[c_idx] if class_names and c_idx < len(class_names) else f"Class {c_idx}"
            counts = [stats["client_class_counts"][cid].get(c_idx, 0) for cid in range(5)]
            fig.add_trace(go.Bar(name=c_label, x=clients_labels, y=counts, marker_color=palette[c_idx % len(palette)]))

        fig.update_layout(
            barmode="stack",
            title="Class Sample Counts per Simulated Node (Dirichlet α = 0.5)",
            xaxis_title="Simulated Edge Participant",
            yaxis_title="Total Flow Records",
            template="plotly_dark",
            height=340
        )
        st.plotly_chart(fig, use_container_width=True)

    with c_right:
        # Heterogeneity and entropy table
        hetero_rows = []
        for cid in range(5):
            total_samples = stats["client_sample_counts"][cid]
            class_counts = stats["client_class_counts"][cid]
            # Calculate Shannon entropy: H = -sum(p * log2(p))
            probs = [class_counts.get(c, 0) / max(total_samples, 1) for c in range(num_classes)]
            entropy = -sum(p * np.log2(p) for p in probs if p > 0)
            max_entropy = np.log2(num_classes) if num_classes > 1 else 1.0
            hetero_ratio = 1.0 - (entropy / max_entropy) if max_entropy > 0 else 0.0

            hetero_rows.append({
                "Participant": f"Node-{cid}",
                "Sample Count": f"{total_samples:,}",
                "Shannon Entropy": f"{entropy:.3f} bits",
                "Skew Index (1-H/H_max)": f"{hetero_ratio * 100:.1f}%",
                "Dominant Class": class_names[np.argmax(probs)] if class_names else f"Class {np.argmax(probs)}"
            })

        st.markdown("**Per-Participant Statistical Entropy:**")
        st.dataframe(pd.DataFrame(hetero_rows), use_container_width=True)

        st.markdown("""
        <div style="font-size: 13px; color: #cbd5e1; background-color: #1e293b; padding: 12px; border-radius: 6px;">
            <b>Why Non-IID Skew Challenges Federated Optimization:</b><br>
            Under Dirichlet concentration (α=0.5), local training updates diverge because each client optimizes against a local objective heavily biased toward its dominant traffic class. Standard cosine consensus filters would falsely reject honest specialized nodes without Tier-3 validation loss verification.
        </div>
        """, unsafe_allow_html=True)


def render_aggregation_comparison_visualizer():
    """
    3.3 Aggregation Algorithm Comparison Visualizer.
    Interactive comparison of FedAvg, Coordinate Median, Trimmed Mean, Trust-Weighted, Multi-Krum, and FoolsGold.
    """
    st.subheader("⚖️ Interactive Aggregation Algorithm Comparison Visualizer")
    st.caption("Observe how different aggregation strategies handle adversarial outliers in coordinate-wise updates.")

    st.markdown("""
    <div style="background-color: #1e293b; border-left: 4px solid #f59e0b; padding: 10px 14px; border-radius: 6px; margin-bottom: 15px; font-size: 13px; color: #fde68a;">
        ℹ️ <b>Conceptual Demonstration:</b> This interactive widget demonstrates coordinate-level aggregation mathematics on a 5-client vector coordinate. 
        It illustrates how differing algorithms respond to a controllable adversarial outlier.
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("**Simulated Coordinate Values (Clients 0–4):**")
        h0 = st.slider("Client 0 (Honest):", min_value=-5.0, max_value=5.0, value=1.0, step=0.1)
        h1 = st.slider("Client 1 (Honest):", min_value=-5.0, max_value=5.0, value=1.2, step=0.1)
        h2 = st.slider("Client 2 (Honest):", min_value=-5.0, max_value=5.0, value=0.9, step=0.1)
        h4 = st.slider("Client 4 (Honest):", min_value=-5.0, max_value=5.0, value=1.1, step=0.1)
        adv_val = st.slider("Client 3 (Adversary Update):", min_value=-20.0, max_value=20.0, value=-15.0, step=0.5)

    client_vals = np.array([h0, h1, h2, adv_val, h4], dtype=np.float32)

    # 1. FedAvg
    agg_fedavg = float(np.mean(client_vals))

    # 2. Coordinate Median
    agg_median = float(np.median(client_vals))

    # 3. Trimmed Mean (trim 1 on each side = 20%)
    sorted_vals = np.sort(client_vals)
    agg_trimmed = float(np.mean(sorted_vals[1:4]))

    # 4. Trust-Weighted (Client 3 slashed to R=0.1, others R=1.0)
    reputations = np.array([1.0, 1.0, 1.0, 0.1, 1.0], dtype=np.float32)
    agg_trust = float(np.sum(client_vals * reputations) / np.sum(reputations))

    # 5. Multi-Krum (1D equivalent: select client minimizing distance to k-f nearest neighbors)
    # With n=5, f=1: distances to 3 nearest peers
    dists = [sum(sorted(abs(client_vals[i] - client_vals))[1:4]) for i in range(5)]
    krum_idx = int(np.argmin(dists))
    agg_krum = float(client_vals[krum_idx])

    # 6. FoolsGold (cosine historical similarity dampening approximation)
    fg_weights = np.array([1.0, 1.0, 1.0, 0.05, 1.0], dtype=np.float32)
    agg_foolsgold = float(np.sum(client_vals * fg_weights) / np.sum(fg_weights))

    with c2:
        st.markdown("**Aggregated Coordinate Outputs:**")
        comp_df = pd.DataFrame([
            {"Algorithm": "FedAvg", "Output": agg_fedavg, "Byzantine Tolerance": "❌ Zero Tolerance (Drags toward outlier)"},
            {"Algorithm": "Coordinate Median", "Output": agg_median, "Byzantine Tolerance": "✅ High (Locks to peer median)"},
            {"Algorithm": "Trimmed Mean (β=0.2)", "Output": agg_trimmed, "Byzantine Tolerance": "✅ High (Excises extreme min/max)"},
            {"Algorithm": "Trust-Weighted FedAvg", "Output": agg_trust, "Byzantine Tolerance": "✅ High (Suppresses slashed nodes)"},
            {"Algorithm": "Multi-Krum", "Output": agg_krum, "Byzantine Tolerance": "✅ High (Selects consensus candidate)"},
            {"Algorithm": "FoolsGold", "Output": agg_foolsgold, "Byzantine Tolerance": "✅ High (Dampens sybil/correlated outliers)"}
        ])
        st.dataframe(comp_df, use_container_width=True)

        # Plot output comparison
        fig_agg = go.Figure()
        fig_agg.add_trace(go.Bar(
            x=["FedAvg", "Median", "Trimmed Mean", "Trust-Weighted", "Multi-Krum", "FoolsGold"],
            y=[agg_fedavg, agg_median, agg_trimmed, agg_trust, agg_krum, agg_foolsgold],
            marker_color=["#ef4444", "#10b981", "#3b82f6", "#8b5cf6", "#f59e0b", "#06b6d4"]
        ))
        fig_agg.add_hline(y=1.05, line_dash="dash", line_color="#10b981", annotation_text="Honest Ground Truth (~1.05)")
        fig_agg.update_layout(
            title="Comparison of Aggregated Values Under Attack",
            yaxis_title="Aggregated Coordinate Value",
            template="plotly_dark",
            height=280
        )
        st.plotly_chart(fig_agg, use_container_width=True)


def render_attack_defense_visualizer():
    """
    3.4 Attack and Defense Visualizer.
    Interactive demonstration of implemented Stage 2D adversarial scenarios.
    """
    st.subheader("🛡️ Adversarial Scenarios & Multi-Attack Defense Matrix")
    st.caption("Inspect implemented adversarial poisoning mechanisms and observe the defense engine's multi-criteria interception response.")

    scenarios = {
        "Gaussian Noise Poisoning": {
            "type": "model_poisoning",
            "threat": "Adversary injects high-variance zero-mean Gaussian noise (std=2.5) into weight updates.",
            "impact": "Explodes L2 parameter norm, destabilizing gradient descent across all classes.",
            "defense_action": "Intercepted by Tier-1 Dynamic L2-Norm Bounding (||w_k|| > 2.5 * ||w_global||).",
            "tier_caught": "Tier 1: L2-Norm Bounding",
            "color": "#ef4444"
        },
        "Sign-Flipping Attack": {
            "type": "model_poisoning",
            "threat": "Adversary inverts gradient directions by scaling updates with negative factor (scale = -3.0).",
            "impact": "Sabotages decision boundary optimization by actively reversing parameter updates (not gradient inversion).",
            "defense_action": "Intercepted by Tier-2 Cosine Consensus (cos(w_k, w_med) < 0.15).",
            "tier_caught": "Tier 2: Cosine Consensus",
            "color": "#f97316"
        },
        "Targeted Label-Flipping": {
            "type": "data_poisoning",
            "threat": "Adversary poisons local dataset flipping target attack classes to normal (Attack -> Normal).",
            "impact": "Blinds the IDS classifier specifically against the targeted intrusion class.",
            "defense_action": "Intercepted by Tier-3 Validation Loss Delta (ΔLoss > 1.5) on benchmark slice.",
            "tier_caught": "Tier 3: Validation Loss Delta",
            "color": "#eab308"
        },
        "Sybil Coalition": {
            "type": "coordinated_model_poisoning",
            "threat": "Multiple cooperating nodes submit correlated inverted updates to drag coordinate medians.",
            "impact": "Overpowers naive coordinate median aggregation by colluding on the same direction.",
            "defense_action": "Intercepted by Cosine Consensus + Asymmetric Slashing and Quarantine isolation.",
            "tier_caught": "Tier 2 Cosine + Multi-Round Quarantine",
            "color": "#a855f7"
        },
        "Parameterized Stealth Byzantine Perturbation": {
            "type": "stealth_byzantine",
            "threat": "Perturbation calibrated to hover just beneath geometric norm and cosine thresholds.",
            "impact": "Attempts parameter drift over repeated rounds (parameterized threshold-aligned, not feedback-adaptive).",
            "defense_action": "Caught by Tier-3 benchmark loss testing or progressive reputation decay.",
            "tier_caught": "Tier 3 Benchmark Loss Delta",
            "color": "#06b6d4"
        }
    }

    selected_atk = st.selectbox("Select Attack Scenario to Inspect", list(scenarios.keys()))
    atk_info = scenarios[selected_atk]

    col_a1, col_a2 = st.columns([1, 1])
    with col_a1:
        st.markdown(f"""
        <div style="background-color: #1e293b; border-radius: 8px; padding: 16px; border-left: 6px solid {atk_info['color']};">
            <h4 style="margin-top:0; color: {atk_info['color']};">{selected_atk}</h4>
            <p style="font-size: 13px; color: #f8fafc;"><b>Adversarial Vector:</b> {atk_info['threat']}</p>
            <p style="font-size: 13px; color: #94a3b8;"><b>System Impact:</b> {atk_info['impact']}</p>
            <p style="font-size: 13px; color: #a7f3d0;"><b>Defense Mechanism:</b> {atk_info['defense_action']}</p>
        </div>
        """, unsafe_allow_html=True)

    with col_a2:
        # Visual representation of vector displacement
        fig = go.Figure()
        # Honest cluster
        fig.add_trace(go.Scatter(x=[1.0, 1.1, 0.9, 1.05], y=[0.1, -0.05, 0.08, 0.0], mode="markers",
                                marker=dict(size=14, color="#10b981"), name="Honest Nodes (0,1,2,4)"))
        # Peer median
        fig.add_trace(go.Scatter(x=[1.0], y=[0.0], mode="markers+text",
                                marker=dict(size=18, color="#3b82f6", symbol="star"),
                                text=["Peer Median"], textposition="top center", name="Consensus Median"))

        if "Gaussian" in selected_atk:
            fig.add_trace(go.Scatter(x=[4.5], y=[-3.8], mode="markers+text",
                                    marker=dict(size=16, color="#ef4444"), text=["Node-3 (Gaussian Noise)"],
                                    textposition="top center", name="Malicious Node 3"))
        elif "Sign" in selected_atk:
            fig.add_trace(go.Scatter(x=[-2.5], y=[0.0], mode="markers+text",
                                    marker=dict(size=16, color="#f97316"), text=["Node-3 (Sign-Flipped)"],
                                    textposition="top center", name="Malicious Node 3"))
        elif "Label" in selected_atk:
            fig.add_trace(go.Scatter(x=[0.6], y=[1.8], mode="markers+text",
                                    marker=dict(size=16, color="#eab308"), text=["Node-3 (Label-Flipped)"],
                                    textposition="top center", name="Malicious Node 3"))
        elif "Sybil" in selected_atk:
            fig.add_trace(go.Scatter(x=[-1.5, -1.5], y=[-0.2, 0.2], mode="markers+text",
                                    marker=dict(size=16, color="#a855f7"), text=["Node-2 (Sybil)", "Node-3 (Sybil)"],
                                    textposition="top center", name="Sybil Coalition"))
        else:
            fig.add_trace(go.Scatter(x=[0.7], y=[0.3], mode="markers+text",
                                    marker=dict(size=16, color="#06b6d4"), text=["Node-3 (Stealth)"],
                                    textposition="top center", name="Stealth Byzantine"))

        fig.update_layout(
            title=f"Update Vector Orientation: {selected_atk}",
            xaxis=dict(title="Dimension 1", range=[-3.5, 5.5]),
            yaxis=dict(title="Dimension 2", range=[-4.5, 2.5]),
            template="plotly_dark",
            height=280
        )
        st.plotly_chart(fig, use_container_width=True)


def render_trust_reputation_visualizer():
    """
    3.5 Trust and Reputation Visualizer.
    Visualizes the multi-criteria trust engine, asymmetric reputation scoring, quarantine, and probation.
    """
    st.subheader("🛡️ Multi-Criteria Trust Filter & Asymmetric Reputation Visualizer")
    st.caption("Interactive simulator for update validation against exact configured operational parameters.")

    # Display configured parameters
    p1, p2, p3, p4 = st.columns(4)
    with p1: st.metric("Tier 1: L2 Norm Factor", "2.50x", "Maximum Global Norm")
    with p2: st.metric("Tier 2: Cosine Threshold", "0.150", "Minimum Peer Similarity")
    with p3: st.metric("Tier 3: Loss Delta Threshold", "1.500", "Maximum Benchmark Loss Increase")
    with p4: st.metric("Quarantine Threshold", "0.400", "Autonomous Isolation Trigger")

    st.markdown("---")
    st.markdown("#### 🧪 Test a Candidate Update Against the Multi-Criteria Filter")

    t_col1, t_col2 = st.columns([1, 1])
    with t_col1:
        cand_norm_ratio = st.slider("Candidate L2 Norm Ratio (||w_k|| / ||w_global||):", min_value=0.1, max_value=5.0, value=1.2, step=0.1)
        cand_cos_sim = st.slider("Candidate Cosine Similarity to Peer Median:", min_value=-1.0, max_value=1.0, value=0.85, step=0.05)
        cand_loss_delta = st.slider("Candidate Validation Loss Delta (ΔLoss):", min_value=-0.5, max_value=4.0, value=0.05, step=0.05)
        current_rep = st.slider("Candidate Current Reputation Score:", min_value=0.0, max_value=1.0, value=0.90, step=0.05)

    # Evaluation logic
    norm_passed = cand_norm_ratio <= 2.5
    cosine_passed = cand_cos_sim >= 0.15
    loss_passed = cand_loss_delta <= 1.5

    all_passed = norm_passed and cosine_passed and loss_passed

    if all_passed:
        new_rep = min(1.0, current_rep + 0.05)
        status_text = "ACCEPTED (Honest Update)"
        badge_color = "#10b981"
    else:
        new_rep = max(0.0, current_rep - 0.35)
        status_text = "REJECTED (Adversarial Slashed)"
        badge_color = "#ef4444"

    is_quarantined = new_rep < 0.40

    with t_col2:
        st.markdown(f"""
        <div style="background-color: #1e293b; border-radius: 8px; padding: 18px; border: 1px solid {badge_color};">
            <h4 style="margin-top:0; color: {badge_color};">Verdict: {status_text}</h4>
            <div style="font-size: 14px; margin-bottom: 8px;">
                • Tier 1 (Norm <= 2.5): {'✅ PASS' if norm_passed else '❌ FAIL (Norm Exceeded)'}<br>
                • Tier 2 (Cosine >= 0.15): {'✅ PASS' if cosine_passed else '❌ FAIL (Direction Inverted)'}<br>
                • Tier 3 (ΔLoss <= 1.5): {'✅ PASS' if loss_passed else '❌ FAIL (Benchmark Loss Exploded)'}
            </div>
            <hr style="border-color: #334155; margin: 10px 0;">
            <div style="font-size: 14px;">
                <b>Reputation Transition:</b> {current_rep:.3f} &rarr; <b>{new_rep:.3f}</b> ({'+0.05' if all_passed else '-0.35'})<br>
                <b>Quarantine Status:</b> <span style="color: {'#ef4444' if is_quarantined else '#10b981'}; font-weight: bold;">
                    {'⛔ QUARANTINED (Excluded from future rounds)' if is_quarantined else '✅ ACTIVE (Eligible)'}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_blockchain_audit_visualizer(blockchain: Any):
    """
    3.6 Blockchain Audit Visualizer.
    Interactive representation of the locally simulated audit ledger with controlled tampering demonstration.
    """
    st.subheader("⛓️ Cryptographic Audit Ledger & Tamper Detection Visualizer")
    st.caption("Inspect block chaining, Merkle roots, and evaluate the automated verifier's tamper detection performance.")

    st.markdown("""
    <div style="background-color: #0f172a; border: 1px solid #1e293b; border-left: 4px solid #8b5cf6; border-radius: 6px; padding: 12px 16px; margin-bottom: 15px; font-size: 13px; color: #cbd5e1;">
        <b>Architectural Context:</b> This is a <b>locally simulated, centrally orchestrated, tamper-evident audit ledger</b>. 
        It models cryptographic auditability and Proof-of-Trust validator election, but does not implement decentralized P2P gossip consensus or proof-of-work mining.
    </div>
    """, unsafe_allow_html=True)

    chain = getattr(blockchain, "chain", [])
    if not chain:
        st.info("No mined blocks present in session state yet. Execute a simulation to populate the ledger.")
        return

    # Visual Chain Timeline
    block_indices = [b.index for b in chain]
    st.markdown("**Cryptographic Block Pointer Sequence:**")
    
    cols = st.columns(len(chain))
    for idx, b in enumerate(chain):
        with cols[idx]:
            is_genesis = (b.index == 0)
            st.markdown(f"""
            <div style="background-color: #1e293b; border: 1px solid {'#3b82f6' if not is_genesis else '#64748b'}; border-radius: 6px; padding: 10px; font-size: 12px;">
                <b>Block #{b.index}</b><br>
                <span style="color: #94a3b8;">Hash:</span> <code>{b.hash[:8]}...</code><br>
                <span style="color: #94a3b8;">Prev:</span> <code>{b.previous_hash[:8]}...</code><br>
                <span style="color: #a7f3d0;">Txs:</span> {len(b.transactions)}
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 🚨 Controlled Tampering Stress-Test Demonstration")
    st.caption("Inject a controlled synthetic tampering fault into an in-memory clone of the blockchain and run AuditVerifier.")

    tc1, tc2 = st.columns([1, 1])
    with tc1:
        target_b_idx = st.selectbox("Target Block to Tamper", [b.index for b in chain if b.index > 0], index=0 if len(chain) > 1 else None)
        tamper_mode = st.selectbox("Tampering Category", [
            "Payload Modification (Corrupt Transaction Model Hash)",
            "Hash Chain Corruption (Break Previous-Hash Pointer)",
            "Merkle Root Inconsistency (Directly Alter Header Merkle Root)",
            "Block Deletion (Excise Intermediate Block)"
        ])
        run_tamper_btn = st.button("🧪 Inject Tampering & Verify Audit", type="secondary")

    with tc2:
        if run_tamper_btn and target_b_idx is not None:
            # Deepcopy to never mutate real session ledger
            cloned_bc = copy.deepcopy(blockchain)
            suite = SyntheticTamperSuite()
            verifier = AuditVerifier()

            if "Payload" in tamper_mode:
                cloned_bc = suite.generate_tampered_ledger(cloned_bc, "payload_modification", seed=42)
            elif "Hash Chain" in tamper_mode:
                cloned_bc = suite.generate_tampered_ledger(cloned_bc, "hash_chain_modification", seed=42)
            elif "Merkle" in tamper_mode:
                cloned_bc = suite.generate_tampered_ledger(cloned_bc, "merkle_root_inconsistency", seed=42)
            else:
                cloned_bc = suite.generate_tampered_ledger(cloned_bc, "block_deletion", seed=42)

            audit_res = verifier.verify_chain(cloned_bc)

            if not audit_res["is_valid"]:
                st.error(f"🚨 **TAMPERING DETECTED!** Verification successfully caught corruption.")
                st.markdown(f"• **Failure Category:** `{audit_res['failure_category']}`")
                st.markdown(f"• **Corrupted Block Index:** `{audit_res['corrupted_block_index']}`")
                st.markdown(f"• **Audit Latency:** `{audit_res['audit_latency_ms']:.3f} ms`")
                st.markdown(f"• **Specific Violations:**")
                for v in audit_res["violations"]:
                    st.write(f"  - `{v}`")
            else:
                st.success("Verification Passed (Unexpected for tampered chain)")
        else:
            st.info("Select a block and tampering mode, then click 'Inject Tampering' to observe audit detection.")
