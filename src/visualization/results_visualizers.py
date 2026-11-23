"""
Experimental Results Dashboard Visualizers for Stage 2F (Section 5).
Implements:
1. render_wp1_benchmark_dashboard: Multi-seed statistical baselines (8 models, Holm-Bonferroni correction).
2. render_wp4_overhead_dashboard: Computational overhead, communication byte accounting, and tamper audit.
"""

import os
import json
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def render_wp1_benchmark_dashboard(filepath: str = "data/processed/stage2e/wp1/benchmark_summary_v2.json"):
    """
    Renders the Stage 2E Work Package 1 Multi-Seed Baseline Evaluation.
    Displays 8 model paradigms, Holm-Bonferroni step-down corrections, and statistical power disclaimers.
    """
    st.subheader("🔬 Stage 2E.3.1 WP1: Multi-Seed Statistical Baseline Evaluation")
    st.caption("Rigorous multi-seed evaluation across 5 pilot seeds ([42, 101, 2024, 777, 999]) with Holm-Bonferroni FWER control.")

    if not os.path.exists(filepath):
        st.warning(f"WP1 benchmark artifact not found at '{filepath}'. Please check disk path.")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("metadata", {})
    models = data.get("models", {})
    comparisons = data.get("multiple_comparisons_family_vs_fedavg", {}).get("comparisons", {})

    st.markdown(r"""
    <div style="background-color: #0f172a; border: 1px solid #1e293b; border-left: 4px solid #f59e0b; border-radius: 6px; padding: 12px 16px; margin-bottom: 15px; font-size: 13px; color: #fde68a;">
        ⚖️ <b>Statistical Power & Sample Size Qualification:</b> 
        This evaluation is an exploratory <b>5-seed pilot ($n=5$)</b>. 
        After family-wise error rate (FWER) control via Holm-Bonferroni step-down correction across 7 comparisons against FedAvg, 
        <b>none of the candidate models achieve statistical significance ($p_{\text{adj}} \ge 0.1839$)</b>. 
        Claims of definitive superiority require a confirmatory study with $N=15\text{--}25$ seeds.
    </div>
    """, unsafe_allow_html=True)

    # 1. Models Summary Table
    model_rows = []
    bar_names = []
    bar_means = []
    bar_errs = []

    model_display_order = [
        "centralized_ids", "local_silos", "fedavg",
        "trust_weighted", "foolsgold", "trimmed_mean", "multikrum_f1", "coordinate_median"
    ]

    for m_key in model_display_order:
        if m_key not in models:
            continue
        m_info = models[m_key]
        lbl = m_info["label"]
        acc_s = m_info["accuracy_stats"]
        f1_s = m_info["f1_macro_stats"]

        diff_str = "Reference Baseline" if m_key == "fedavg" else "N/A"
        raw_p_str = "N/A"
        adj_p_str = "N/A"
        sig_str = "—"

        if m_key in comparisons:
            vs = comparisons[m_key]
            diff_pp = vs.get("mean_difference", 0.0) * 100.0
            sign = "+" if diff_pp >= 0 else ""
            diff_str = f"{sign}{diff_pp:.2f} pp"
            raw_p_str = f"{vs.get('raw_p_value', 1.0):.4f}"
            adj_p_str = f"{vs.get('holm_adjusted_p_value', 1.0):.4f}"
            sig_str = "Not Significant" if not vs.get("statistically_significant_holm", False) else "Significant"

        model_rows.append({
            "Model Paradigm": lbl,
            "Mean Accuracy": f"{acc_s['mean'] * 100:.2f}%",
            "Std Dev": f"±{acc_s['std'] * 100:.2f}%",
            "95% Conf. Interval": acc_s["ci_95_str"],
            "Macro F1": f"{f1_s['mean']:.4f}",
            "Diff vs FedAvg": diff_str,
            "Raw p-value": raw_p_str,
            "Holm-adj p-value": adj_p_str,
            "Significance (α=0.05)": sig_str
        })

        bar_names.append(lbl.replace(" Reference", "").replace(" Baseline", ""))
        bar_means.append(acc_s['mean'] * 100)
        # 95% CI half-width for error bars
        half_ci = (acc_s['ci_95'][1] - acc_s['ci_95'][0]) * 100 / 2.0
        bar_errs.append(half_ci)

    st.dataframe(pd.DataFrame(model_rows), use_container_width=True)

    # 2. Accuracy Comparison with Error Bars
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=bar_names,
        y=bar_means,
        error_y=dict(type='data', array=bar_errs, visible=True),
        marker_color=["#64748b", "#94a3b8", "#3b82f6", "#10b981", "#06b6d4", "#f59e0b", "#8b5cf6", "#ef4444"],
        text=[f"{m:.2f}%" for m in bar_means],
        textposition="auto"
    ))
    fig.update_layout(
        title="Model Accuracy Across 5 Pilot Seeds with 95% Confidence Intervals",
        yaxis_title="Test Accuracy (%)",
        yaxis_range=[70.0, 85.0],
        template="plotly_dark",
        height=360
    )
    st.plotly_chart(fig, use_container_width=True)


def render_wp4_overhead_dashboard(
    filepath_overhead: str = "data/processed/stage2e/wp4/overhead_summary_v2.json",
    filepath_audit: str = "data/processed/stage2e/wp4/serialization_and_negative_control_audit.json"
):
    """
    Renders the Stage 2E Work Package 4 Computational Overhead & Blockchain Audit Evaluation.
    Displays cryptographic microbenchmarks, aggregation overhead, byte-level communication accounting,
    and qualified 500/500 positive / 0/100 negative tamper detection results.
    """
    st.subheader("⚡ Stage 2E.3.1 WP4: Computational Overhead & Blockchain Audit Evaluation")
    st.caption("Empirical microbenchmarks for cryptographic primitives, aggregation algorithms, network bandwidth, and finite ledger audit.")

    if not os.path.exists(filepath_overhead):
        st.warning(f"WP4 overhead artifact not found at '{filepath_overhead}'.")
        return

    with open(filepath_overhead, "r", encoding="utf-8") as f:
        ov_data = json.load(f)

    # 1. Cryptographic Microbenchmarks
    st.markdown("#### 1. Cryptographic Operation Latencies (100 Trials, CPU)")
    crypto_bm = ov_data.get("cryptographic_microbenchmarks", {})
    crypto_rows = []
    for op_key, metrics in crypto_bm.items():
        op_name = {
            "ecdsa_p256_sign": "ECDSA P-256 Digital Signing",
            "ecdsa_p256_verify": "ECDSA P-256 Signature Verification",
            "sha256_hash": "SHA-256 Cryptographic Hashing"
        }.get(op_key, op_key)

        crypto_rows.append({
            "Cryptographic Operation": op_name,
            "Mean Latency (ms)": f"{metrics['mean_ms']:.4f} ms",
            "Median Latency (ms)": f"{metrics['median_ms']:.4f} ms",
            "p95 Latency (ms)": f"{metrics['p95_ms']:.4f} ms",
            "Trials": metrics["trials"]
        })
    st.dataframe(pd.DataFrame(crypto_rows), use_container_width=True)

    # 2. Aggregator Latencies
    st.markdown("#### 2. Aggregation Algorithm Execution Overhead (Dim = 26,594 Parameters, 5 Clients)")
    agg_bm = ov_data.get("aggregation_microbenchmarks", {})
    agg_rows = []
    agg_names = []
    agg_latencies = []

    for agg_key, metrics in agg_bm.items():
        agg_label = {
            "fedavg": "FedAvg",
            "median": "Coordinate Median",
            "trimmed_mean": "Trimmed Mean (β=0.2)",
            "trust_weighted": "Trust-Weighted FedAvg",
            "multikrum_f1": "Multi-Krum (f=1)",
            "foolsgold": "FoolsGold"
        }.get(agg_key, agg_key)

        agg_rows.append({
            "Aggregation Algorithm": agg_label,
            "Mean Latency (ms)": f"{metrics['mean_ms']:.3f} ms",
            "Median Latency (ms)": f"{metrics['median_ms']:.3f} ms",
            "p95 Latency (ms)": f"{metrics['p95_ms']:.3f} ms",
            "Trials": metrics["trials"]
        })
        agg_names.append(agg_label)
        agg_latencies.append(metrics["mean_ms"])

    st.dataframe(pd.DataFrame(agg_rows), use_container_width=True)

    # Bar chart for aggregation latencies
    fig_agg = go.Figure()
    fig_agg.add_trace(go.Bar(
        x=agg_names,
        y=agg_latencies,
        marker_color=["#10b981", "#3b82f6", "#f59e0b", "#8b5cf6", "#ef4444", "#06b6d4"],
        text=[f"{lat:.2f} ms" for lat in agg_latencies],
        textposition="auto"
    ))
    fig_agg.update_layout(
        title="Aggregation Computation Latency (Milliseconds)",
        yaxis_title="Execution Time (ms)",
        template="plotly_dark",
        height=280
    )
    st.plotly_chart(fig_agg, use_container_width=True)

    # 3. Communication Payload Breakdown & Serialization Reconciliation
    st.markdown("#### 3. Communication Payload & Byte Accounting (Strict KiB vs. KB Standards)")
    st.markdown("""
    | Payload Component | Raw Bytes | Binary Unit (KiB) | Decimal Unit (KB) | Notes |
    | :--- | :---: | :---: | :---: | :--- |
    | **Raw Float32 Weights Buffer** | **106,376 bytes** | **103.88 KiB** | 106.38 KB | 26,594 parameters $\\times$ 4 bytes/float32 |
    | **NumPy Pickle Container Envelope** | **161 bytes** | **0.16 KiB** | 0.16 KB | Python Pickle Protocol 4/5 framing + dtype |
    | **Total Serialized Model Payload** | **106,537 bytes** | **104.04 KiB** | 106.54 KB | Model state broadcast / upload payload |
    | **Client Upstream Message (Signed)** | **106,659 bytes** | **104.16 KiB** | 106.66 KB | Includes 71-byte ECDSA signature + RPC envelope |
    | **Server Downstream Broadcast** | **106,582 bytes** | **104.08 KiB** | 106.58 KB | Serialized model vector + round metadata |
    | **Total Round Bandwidth (Unicast)** | **1,066,205 bytes** | **1,041.21 KiB** | 1,066.21 KB | 5 clients $\\times$ (Upstream + Downstream) |
    | **Total Round Bandwidth (Multicast)** | **639,877 bytes** | **624.89 KiB** | 639.88 KB | 5 clients $\\times$ Upstream + 1 Multicast Downstream |
    """)

    # 4. Tamper Detection Benchmark & Qualified Negative Controls
    st.markdown("#### 4. Cryptographic Ledger Tamper-Evidence Benchmark (600 Total Trials)")
    tamper_bm = ov_data.get("tampering_verification_benchmark", {})

    st.markdown("""
    <div style="background-color: #064e3b; border: 1px solid #059669; border-radius: 6px; padding: 12px 16px; margin-bottom: 12px;">
        <span style="font-size: 14px; font-weight: bold; color: #a7f3d0;">🛡️ 100% Observed Detection Across 5 Positive Tampering Categories (500/500 Trials)</span><br>
        <span style="font-size: 13px; color: #d1fae5;">
        • <b>Payload Modification:</b> 100/100 detected (Mean latency: 0.054 ms)<br>
        • <b>Block Deletion:</b> 100/100 detected (Mean latency: 0.038 ms)<br>
        • <b>Block Reordering:</b> 100/100 detected (Mean latency: 0.041 ms)<br>
        • <b>Hash Pointer Corruption:</b> 100/100 detected (Mean latency: 0.040 ms)<br>
        • <b>Merkle Root Inconsistency:</b> 100/100 detected (Mean latency: 0.039 ms)
        </span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background-color: #1e293b; border-left: 4px solid #3b82f6; border-radius: 6px; padding: 12px 16px; font-size: 13px; color: #cbd5e1;">
        <b>Negative-Control Reporting Qualification:</b><br>
        The verifier observed <b>0/100 false alarms (0.00% observed FPR)</b> on repeated verification trials of the tested 4-block pristine ledger template. 
        This metric validates deterministic and side-effect-free execution on the baseline configuration; generalization to structurally varied legitimate ledgers requires future evaluation on expanded multi-topology suites.
    </div>
    """, unsafe_allow_html=True)
