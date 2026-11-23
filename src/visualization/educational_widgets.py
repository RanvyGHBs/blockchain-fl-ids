"""
Educational Interactive Visualizers for Section 6: Learn & Explore (Level 2).
Implements rich interactive demonstrations for all 9 Educational Modules:
Module 1: FL Lifecycle
Module 2: Dirichlet Skew Slider
Module 3: L2 Clipping & Gaussian Noise Visualizer
Module 4: Robust Aggregation Outlier Comparison
Module 5: Adversarial Attack Vector Geometry
Module 6: Multi-Criteria Trust Radar / Inspection Widget
Module 7: Binary Merkle Tree Builder & Tamper Demonstrator
Module 8: IDSNet Deep Learning Architecture & Flow Classifier
Module 9: Vector Mathematics & Cosine Geometry
"""

import hashlib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def render_fl_lifecycle_widget():
    """Module 1 Level 2: Interactive Federated Learning Lifecycle."""
    st.markdown("#### 🔄 Interactive FL Communication Round Simulator")
    st.caption("Step through the 4 core phases of a collaborative federated training round.")

    step_choice = st.select_slider(
        "Communication Step",
        options=[
            "1. Server Broadcast",
            "2. Local Client SGD",
            "3. Update Upload",
            "4. Robust Aggregation"
        ],
        value="1. Server Broadcast"
    )

    step_details = {
        "1. Server Broadcast": {
            "title": "Phase 1: Global Weight Broadcast",
            "desc": "The central coordinator serializes the current global model parameter vector w^t and transmits it downstream to all registered client nodes.",
            "data_flow": "Server -> All Clients (Downstream: 104.08 KiB)",
            "privacy_note": "Broadcast model contains only aggregated knowledge; no individual client samples are revealed.",
            "color": "#3b82f6"
        },
        "2. Local Client SGD": {
            "title": "Phase 2: On-Device Private Training",
            "desc": "Each client trains the model on its private local flow records for E=1 epoch using stochastic gradient descent. Raw packet logs remain strictly within local RAM.",
            "data_flow": "Local Client Memory (Zero network transmission)",
            "privacy_note": "100% Data Sovereignty: No raw network traffic logs are shared across organizations.",
            "color": "#10b981"
        },
        "3. Update Upload": {
            "title": "Phase 3: Serialized Model Update Upload",
            "desc": "Clients compute weight delta w_k, sign the model hash with their private ECDSA key, and transmit the serialized update (106,537 bytes) upstream.",
            "data_flow": "Clients -> Server (Upstream: 104.16 KiB per client)",
            "privacy_note": "ECDSA SECP256R1 signature ensures non-repudiation and prevents in-transit tampering.",
            "color": "#f59e0b"
        },
        "4. Robust Aggregation": {
            "title": "Phase 4: Trust Evaluation & Global Update",
            "desc": "The server verifies digital signatures, filters out Byzantine outliers through the Multi-Criteria Trust Filter, aggregates surviving updates, and mints an audit block.",
            "data_flow": "Server In-Memory Aggregation -> Audit Ledger Block",
            "privacy_note": "Trust-weighted FedAvg neutralizes malicious contributors while preserving honest convergence.",
            "color": "#8b5cf6"
        }
    }

    info = step_details[step_choice]
    st.markdown(f"""
    <div style="background-color: #1e293b; border-left: 6px solid {info['color']}; padding: 16px; border-radius: 8px;">
        <h4 style="margin-top:0; color: {info['color']};">{info['title']}</h4>
        <p style="font-size: 14px; color: #f8fafc;">{info['desc']}</p>
        <p style="font-size: 13px; color: #94a3b8;"><b>Data Movement:</b> <code>{info['data_flow']}</code></p>
        <p style="font-size: 13px; color: #a7f3d0;"><b>Security & Privacy Guarantee:</b> {info['privacy_note']}</p>
    </div>
    """, unsafe_allow_html=True)


def render_dirichlet_widget():
    """Module 2 Level 2: Non-IID Dirichlet Skew Simulator."""
    st.markdown("#### 📊 Interactive Dirichlet Concentration Parameter (α) Simulator")
    st.caption("Adjust α to observe how class distributions transition from balanced (IID) to highly specialized (Non-IID).")

    alpha_val = st.slider("Dirichlet Concentration Parameter (α)", min_value=0.1, max_value=5.0, value=0.5, step=0.1)
    
    # 5 clients, 2 classes (Normal vs Attack)
    rng = np.random.RandomState(42)
    props = rng.dirichlet(np.repeat(alpha_val, 5), size=2)  # shape (2, 5)

    c1, c2 = st.columns([1, 1])
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Normal Traffic", x=[f"Node-{i}" for i in range(5)], y=props[0], marker_color="#10b981"))
        fig.add_trace(go.Bar(name="Attack Traffic", x=[f"Node-{i}" for i in range(5)], y=props[1], marker_color="#ef4444"))
        fig.update_layout(
            barmode="group",
            title=f"Sample Class Allocation (α = {alpha_val:.1f})",
            yaxis_title="Class Probability Proportion",
            template="plotly_dark",
            height=280
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        interpretation = "Severe Non-IID Skew: Individual clients hold highly skewed data; Node specialization creates divergent local gradients." if alpha_val < 1.0 else "Moderately Balanced / IID: Class proportions are relatively uniform across all client nodes."
        st.markdown(f"""
        <div style="background-color: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #334155;">
            <h5 style="margin-top:0;">Interpretation: α = {alpha_val:.1f}</h5>
            <p style="font-size: 13px; color: #cbd5e1;">{interpretation}</p>
            <p style="font-size: 12px; color: #94a3b8;">
                • <b>Low α (&le; 0.5):</b> Models real-world networks where subnets specialize in distinct traffic.<br>
                • <b>High α (&ge; 2.0):</b> Models synthetic academic benchmarks with homogeneous distributions.
            </p>
        </div>
        """, unsafe_allow_html=True)


def render_clipping_widget():
    """Module 3 Level 2: L2 Clipping & Gaussian Noise Visualizer."""
    st.markdown("#### 🔒 Interactive L2-Norm Clipping & Gaussian Perturbation Simulator")
    st.caption("Demonstrating how L2-norm bounding constrains parameter update sensitivity before noise addition.")

    c1, c2 = st.columns([1, 1])
    with c1:
        raw_norm = st.slider("Raw Candidate Update Magnitude (||w||_2):", min_value=0.5, max_value=8.0, value=4.5, step=0.5)
        clip_c = st.slider("L2 Clipping Bound (C):", min_value=1.0, max_value=5.0, value=2.0, step=0.5)
        noise_sigma = st.slider("Gaussian Noise Multiplier (σ):", min_value=0.0, max_value=0.2, value=0.05, step=0.01)

    # Compute clipped norm and effective noise
    is_clipped = raw_norm > clip_c
    clipped_norm = clip_c if is_clipped else raw_norm
    effective_noise_std = noise_sigma * clip_c

    with c2:
        st.markdown(f"""
        <div style="background-color: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid {'#f59e0b' if is_clipped else '#10b981'};">
            <h5 style="margin-top:0;">Perturbation Summary:</h5>
            <div style="font-size: 13px; color: #f8fafc;">
                • <b>Raw L2 Norm:</b> {raw_norm:.2f}<br>
                • <b>Clipping Status:</b> <span style="color: {'#f59e0b' if is_clipped else '#10b981'}; font-weight: bold;">
                    {'CLIPPED (Projected to radius C)' if is_clipped else 'UNCLIPPED (Within sphere)'}
                </span><br>
                • <b>Post-Clipping Norm:</b> {clipped_norm:.2f}<br>
                • <b>Gaussian Noise std (σ · C):</b> {effective_noise_std:.4f}
            </div>
            <div style="font-size: 11px; color: #94a3b8; margin-top: 8px;">
                <b>Methodological Clarification:</b> This is <i>clipping-based Gaussian update perturbation (without formal privacy accounting)</i>. 
                Full differential privacy requires bounding per-sample sensitivity and tracking multi-round Rényi DP composition.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 2D Circular Projection Visualization
    theta = np.linspace(0, 2 * np.pi, 100)
    fig = go.Figure()
    # Clipping sphere
    fig.add_trace(go.Scatter(x=clip_c * np.cos(theta), y=clip_c * np.sin(theta), mode="lines",
                             name=f"Clipping Sphere (Radius C={clip_c:.1f})", line=dict(dash="dash", color="#3b82f6")))
    # Unclipped vector
    fig.add_trace(go.Scatter(x=[0, raw_norm * 0.707], y=[0, raw_norm * 0.707], mode="lines+markers",
                             name=f"Raw Update (Norm={raw_norm:.2f})", line=dict(color="#ef4444", width=3)))
    # Clipped vector
    fig.add_trace(go.Scatter(x=[0, clipped_norm * 0.707], y=[0, clipped_norm * 0.707], mode="lines+markers",
                             name=f"Clipped Update (Norm={clipped_norm:.2f})", line=dict(color="#10b981", width=3)))

    fig.update_layout(
        title="2D Projection of Vector Bounding onto Clipping Sphere",
        xaxis=dict(range=[-8.5, 8.5], zeroline=True),
        yaxis=dict(range=[-8.5, 8.5], zeroline=True),
        template="plotly_dark",
        height=320
    )
    st.plotly_chart(fig, use_container_width=True)


def render_aggregator_widget():
    """Module 4 Level 2: Robust Aggregation Outlier Comparison."""
    st.markdown("#### ⚖️ Interactive Aggregator Outlier Resilience Comparison")
    st.caption("Inject a controllable Byzantine outlier into a 5-party coordinate update to observe aggregator responses.")

    c1, c2 = st.columns([1, 1])
    with c1:
        outlier_val = st.slider("Adversary Injected Outlier Coordinate Value:", min_value=-50.0, max_value=50.0, value=25.0, step=2.5)
        st.caption("Honest participants submit normal updates clustered around ground truth: [1.0, 1.2, 0.9, 1.1].")

    # 5-client values
    vals = np.array([1.0, 1.2, 0.9, outlier_val, 1.1], dtype=np.float32)
    # Calculations
    val_fedavg = float(np.mean(vals))
    val_median = float(np.median(vals))
    val_trimmed = float(np.mean(np.sort(vals)[1:4]))  # beta=0.2 (trims min and max)
    reps = np.array([1.0, 1.0, 1.0, 0.1, 1.0], dtype=np.float32)  # Slashed reputation for outlier
    val_trust = float(np.sum(vals * reps) / np.sum(reps))

    with c2:
        res_df = pd.DataFrame([
            {"Aggregator": "FedAvg (Arithmetic Mean)", "Output": f"{val_fedavg:.3f}", "Deviation from Truth": f"{abs(val_fedavg - 1.05):.3f}", "Resilience": "❌ Subverted"},
            {"Aggregator": "Coordinate Median", "Output": f"{val_median:.3f}", "Deviation from Truth": f"{abs(val_median - 1.05):.3f}", "Resilience": "✅ Protected"},
            {"Aggregator": "Trimmed Mean (β=0.2)", "Output": f"{val_trimmed:.3f}", "Deviation from Truth": f"{abs(val_trimmed - 1.05):.3f}", "Resilience": "✅ Protected"},
            {"Aggregator": "Trust-Weighted FedAvg", "Output": f"{val_trust:.3f}", "Deviation from Truth": f"{abs(val_trust - 1.05):.3f}", "Resilience": "✅ Protected"}
        ])
        st.dataframe(res_df, use_container_width=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["FedAvg", "Median", "Trimmed Mean", "Trust-Weighted"],
        y=[val_fedavg, val_median, val_trimmed, val_trust],
        marker_color=["#ef4444", "#10b981", "#3b82f6", "#8b5cf6"]
    ))
    fig.add_hline(y=1.05, line_dash="dash", line_color="#10b981", annotation_text="Honest Consensus (~1.05)")
    fig.update_layout(title="Aggregated Coordinate Value vs. Honest Ground Truth", template="plotly_dark", height=280)
    st.plotly_chart(fig, use_container_width=True)


def render_attack_vectors_widget():
    """Module 5 Level 2: Adversarial Attack Vector Geometry."""
    st.markdown("#### 🚨 Interactive Adversarial Vector Geometry Visualizer")
    st.caption("Explore how different poisoning strategies manipulate weight vector orientation and magnitude.")

    atk_type = st.radio("Select Poisoning Attack Vector to Simulate:", ["Sign-Flipping Attack", "Gaussian Noise Attack", "Model Scaling Attack"], horizontal=True)

    honest_u = np.array([1.0, 0.5])
    fig = go.Figure()

    # Honest Vector
    fig.add_trace(go.Scatter(x=[0, honest_u[0]], y=[0, honest_u[1]], mode="lines+markers+text",
                             name="Honest Update (w_honest)", text=["", "Honest Update"],
                             line=dict(color="#10b981", width=3), textposition="top right"))

    if atk_type == "Sign-Flipping Attack":
        gamma = st.slider("Sign-Flip Scaling Factor (γ < 0):", min_value=-5.0, max_value=-0.5, value=-3.0, step=0.5)
        adv_u = gamma * honest_u
        fig.add_trace(go.Scatter(x=[0, adv_u[0]], y=[0, adv_u[1]], mode="lines+markers+text",
                                 name=f"Sign-Flipped Update ({gamma}·w)", text=["", f"Sign-Flipped ({gamma:.1f}x)"],
                                 line=dict(color="#f97316", width=3), textposition="bottom left"))
        explanation = f"Sign-flipping rotates the vector exactly 180° backward (cos θ = -1.0) with magnitude scaled by {abs(gamma):.1f}x, dragging optimization away from convergence."

    elif atk_type == "Gaussian Noise Attack":
        std_val = st.slider("Noise Standard Deviation (σ):", min_value=0.5, max_value=4.0, value=2.5, step=0.5)
        np.random.seed(42)
        noise = np.random.normal(0, std_val, size=2)
        adv_u = honest_u + noise
        fig.add_trace(go.Scatter(x=[0, adv_u[0]], y=[0, adv_u[1]], mode="lines+markers+text",
                                 name=f"Gaussian Noise Update (std={std_val})", text=["", "Noise Update"],
                                 line=dict(color="#ef4444", width=3), textposition="top left"))
        explanation = f"Gaussian noise scatters the update vector in an arbitrary direction with exploded L2 norm ({np.linalg.norm(adv_u):.2f}), triggering norm bounding defense."

    else:
        scale_val = st.slider("Model Scaling Factor (s):", min_value=2.0, max_value=10.0, value=5.0, step=1.0)
        adv_u = scale_val * honest_u
        fig.add_trace(go.Scatter(x=[0, adv_u[0]], y=[0, adv_u[1]], mode="lines+markers+text",
                                 name=f"Scaled Update ({scale_val}x)", text=["", f"Scaled ({scale_val}x)"],
                                 line=dict(color="#a855f7", width=3), textposition="top right"))
        explanation = f"Model scaling amplifies the vector magnitude ({np.linalg.norm(adv_u):.2f}) along the same direction to dominate the FedAvg weighted sum."

    fig.update_layout(
        title=f"Vector Plane: {atk_type}",
        xaxis=dict(range=[-6, 6], zeroline=True),
        yaxis=dict(range=[-6, 6], zeroline=True),
        template="plotly_dark",
        height=320
    )
    st.plotly_chart(fig, use_container_width=True)
    st.info(f"💡 **Geometric Insight:** {explanation}")


def render_trust_radar_widget():
    """Module 6 Level 2: Multi-Criteria Trust Radar Widget."""
    st.markdown("#### 🛡️ Interactive 3-Tier Multi-Criteria Inspection Simulator")
    st.caption("Adjust candidate update parameters and evaluate the 3 inspection tiers simultaneously.")

    c1, c2 = st.columns([1, 1])
    with c1:
        norm_ratio = st.slider("Candidate L2-Norm Factor (||w_k|| / ||w_global||):", 0.5, 5.0, 1.2, 0.1)
        cos_sim = st.slider("Cosine Similarity to Peer Median:", -1.0, 1.0, 0.85, 0.05)
        loss_delta = st.slider("Validation Loss Delta on Benchmark Slice:", -0.5, 3.5, 0.1, 0.1)

    t1_pass = norm_ratio <= 2.5
    t2_pass = cos_sim >= 0.15
    t3_pass = loss_delta <= 1.5
    verdict = t1_pass and t2_pass and t3_pass

    with c2:
        # Radar chart showing relative metric alignment
        categories = ["Norm Compliance", "Cosine Consensus", "Loss Delta Safety"]
        # Normalize scores to [0, 100] scale
        norm_score = max(0, min(100, (2.5 / max(norm_ratio, 0.1)) * 100))
        cos_score = max(0, min(100, ((cos_sim - (-1.0)) / 2.0) * 100))
        loss_score = max(0, min(100, (1.5 / max(loss_delta + 0.5, 0.1)) * 100))

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=[norm_score, cos_score, loss_score],
            theta=categories,
            fill='toself',
            name="Candidate Update",
            line=dict(color="#10b981" if verdict else "#ef4444")
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title=f"Inspection Radar: {'✅ ACCEPTED' if verdict else '❌ REJECTED'}",
            template="plotly_dark",
            height=280
        )
        st.plotly_chart(fig, use_container_width=True)

    status_cols = st.columns(3)
    with status_cols[0]:
        st.metric("Tier 1: Norm Bounding", f"{norm_ratio:.2f}x", "PASS (<= 2.5x)" if t1_pass else "FAIL (Exploded)", delta_color="normal" if t1_pass else "inverse")
    with status_cols[1]:
        st.metric("Tier 2: Cosine Consensus", f"{cos_sim:.2f}", "PASS (>= 0.15)" if t2_pass else "FAIL (Inverted)", delta_color="normal" if t2_pass else "inverse")
    with status_cols[2]:
        st.metric("Tier 3: Loss Delta", f"{loss_delta:.2f}", "PASS (<= 1.5)" if t3_pass else "FAIL (Spiked)", delta_color="normal" if t3_pass else "inverse")


def render_merkle_builder_widget():
    """Module 7 Level 2: Merkle Tree Builder & Tamper Demonstrator."""
    st.markdown("#### ⛓️ Interactive 4-Transaction Merkle Tree Builder & Tamper Demonstration")
    st.caption("Observe binary hash pairing and evaluate how a single bit modification corrupts the Merkle Root.")

    tx0_val = st.text_input("Transaction 0 Payload:", value="Client 0 Update: w_0 = [0.12, -0.45, 0.88]")
    tx1_val = st.text_input("Transaction 1 Payload:", value="Client 1 Update: w_1 = [0.10, -0.42, 0.91]")
    tx2_val = st.text_input("Transaction 2 Payload:", value="Client 2 Update: w_2 = [0.15, -0.48, 0.84]")
    tx3_val = st.text_input("Transaction 3 Payload:", value="Client 3 Update: w_3 = [0.11, -0.44, 0.89]")

    tamper_tx2 = st.checkbox("🚨 Inject Tampering into Transaction 2 (Simulate Adversary Modifying Model Hash)")

    def sha(txt: str) -> str:
        return hashlib.sha256(txt.encode("utf-8")).hexdigest()

    h0 = sha(tx0_val)
    h1 = sha(tx1_val)
    h2 = sha(tx2_val + ("_MALICIOUS_MODIFICATION" if tamper_tx2 else ""))
    h3 = sha(tx3_val)

    h01 = sha(h0 + h1)
    h23 = sha(h2 + h3)
    merkle_root = sha(h01 + h23)

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown(f"""
        <div style="background-color: #1e293b; padding: 14px; border-radius: 8px; font-size: 13px;">
            <b>Leaf Hashes:</b><br>
            • H(T0): <code>{h0[:16]}...</code><br>
            • H(T1): <code>{h1[:16]}...</code><br>
            • H(T2): <code style="color: {'#ef4444' if tamper_tx2 else '#a7f3d0'};">{h2[:16]}...</code><br>
            • H(T3): <code>{h3[:16]}...</code><br>
            <hr style="border-color: #334155; margin: 8px 0;">
            <b>Intermediate Branch Hashes:</b><br>
            • H01 = SHA256(H0 + H1): <code>{h01[:16]}...</code><br>
            • H23 = SHA256(H2 + H3): <code style="color: {'#ef4444' if tamper_tx2 else '#a7f3d0'};">{h23[:16]}...</code><br>
            <hr style="border-color: #334155; margin: 8px 0;">
            <b>Mined Merkle Root:</b><br>
            <code style="color: {'#ef4444' if tamper_tx2 else '#3b82f6'}; font-weight: bold; font-size: 14px;">{merkle_root[:24]}...</code>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        if tamper_tx2:
            st.error("❌ **AUDIT INTEGRITY VIOLATION DETECTED!**")
            st.markdown("""
            Altering Transaction 2 altered leaf hash $H_2$.  
            This cascaded into branch hash $H_{23}$, which changed the computed Merkle Root.  
            When compared against the recorded block header, the verifier rejects the block immediately with `MERKLE_ROOT_MISMATCH`.
            """)
        else:
            st.success("✅ **CRYPTOGRAPHIC ROOT VALID**")
            st.markdown("""
            All 4 transaction hashes pair perfectly into intermediate branch digests.  
            The resulting 32-byte Merkle root binds the entire batch into the block header with complete tamper-evidence.
            """)


def render_ids_classifier_widget():
    """Module 8 Level 2: IDSNet Deep Learning Architecture & Flow Classifier."""
    st.markdown("#### 🎯 Interactive IDSNet Neural Network Architecture Visualizer")
    st.caption("Inspect the 4-layer MLP topology and forward feature activation flow for network intrusion detection.")

    layers = [
        {"layer": "Input Layer", "dim": "122 Features", "desc": "Normalized NSL-KDD tabular flow descriptors (duration, protocol, error rates)."},
        {"layer": "Linear 1 + BatchNorm + ReLU", "dim": "128 Neurons", "desc": "High-dimensional feature extraction with batch normalization and dropout (0.2)."},
        {"layer": "Linear 2 + BatchNorm + ReLU", "dim": "64 Neurons", "desc": "Intermediate representation condensing flow patterns."},
        {"layer": "Linear 3 + BatchNorm + ReLU", "dim": "32 Neurons", "desc": "Low-dimensional latent space capturing core intrusion signatures."},
        {"layer": "Classifier Head", "dim": "2 Classes", "desc": "Linear projection yielding raw logits for Normal (0) vs Attack (1)."}
    ]

    selected_l = st.selectbox("Inspect Architecture Layer:", [l["layer"] for l in layers])
    curr_l = next(l for l in layers if l["layer"] == selected_l)

    st.markdown(f"""
    <div style="background-color: #1e293b; border-left: 5px solid #3b82f6; padding: 14px; border-radius: 6px; margin-bottom: 12px;">
        <h5 style="margin-top:0; color: #60a5fa;">{curr_l['layer']} ({curr_l['dim']})</h5>
        <p style="font-size: 13px; color: #cbd5e1;">{curr_l['desc']}</p>
    </div>
    """, unsafe_allow_html=True)

    # Layer architecture bar chart
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["Input (122)", "Dense 1 (128)", "Dense 2 (64)", "Dense 3 (32)", "Output (2)"],
        y=[122, 128, 64, 32, 2],
        marker_color=["#64748b", "#3b82f6", "#10b981", "#8b5cf6", "#f59e0b"],
        text=[122, 128, 64, 32, 2],
        textposition="auto"
    ))
    fig.update_layout(
        title="IDSNet Layer Dimension Profile",
        yaxis_title="Neuron Count / Feature Dimension",
        template="plotly_dark",
        height=260
    )
    st.plotly_chart(fig, use_container_width=True)


def render_vector_geometry_widget():
    """Module 9 Level 2: Vector Mathematics & Cosine Geometry."""
    st.markdown("#### 📐 Interactive 2D Vector Geometry & Cosine Similarity Simulator")
    st.caption("Adjust the vector angle to observe the relationship between directional alignment and cosine similarity.")

    angle = st.slider("Candidate Vector Angle θ (degrees):", min_value=0, max_value=180, value=180, step=15)
    rad = np.radians(angle)
    cos_val = np.cos(rad)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.metric("Cosine Similarity cos(θ):", f"{cos_val:.3f}", "Aligned (+1)" if cos_val > 0.5 else ("Sign-Flipped (-1)" if cos_val < -0.5 else "Orthogonal (0)"))
        st.markdown(f"""
        <div style="font-size: 13px; color: #cbd5e1; background-color: #1e293b; padding: 12px; border-radius: 6px;">
            <b>High-Dimensional Geometry Insight:</b><br>
            In our 26,594-dimensional model space, randomly perturbed vectors are almost exactly orthogonal (cos θ &approx; 0.0). 
            A measured similarity of <b>cos θ &approx; -1.0</b> is a definitive mathematical proof of deliberate sign-flipping.
        </div>
        """, unsafe_allow_html=True)

    with col2:
        fig = go.Figure()
        # Reference vector
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 0], mode="lines+markers+text", name="Consensus w_med",
                                 text=["", "Peer Consensus"], textposition="top right", line=dict(color="#3b82f6", width=3)))
        # Candidate vector
        fig.add_trace(go.Scatter(x=[0, np.cos(rad)], y=[0, np.sin(rad)], mode="lines+markers+text", name="Candidate w_k",
                                 text=["", f"Candidate (θ={angle}°\ncos={cos_val:.2f})"], textposition="top right",
                                 line=dict(color="#10b981" if cos_val >= 0.15 else "#ef4444", width=3)))

        fig.update_layout(
            title="2D Vector Orientation",
            xaxis=dict(range=[-1.2, 1.2], zeroline=True),
            yaxis=dict(range=[-1.2, 1.2], zeroline=True),
            template="plotly_dark",
            height=280
        )
        st.plotly_chart(fig, use_container_width=True)
