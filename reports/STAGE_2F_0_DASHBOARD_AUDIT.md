# Stage 2F.0 — Comprehensive Dashboard & Educational Visualizer Audit

**Project:** Blockchain-Assisted Privacy-Preserving Federated Learning for Network Intrusion Detection with Trust-Based Security and Cryptographic Auditing  
**Workspace:** `C:\Users\is043\.gemini\antigravity\scratch\blockchain-fl-ids`  
**Milestone:** Stage 2F — Advanced Dashboard Visualizers & Interactive Educational Modules  
**Phase:** Phase 0 — Pre-Implementation Repository & Dashboard Audit  
**Date:** 2026-11-23  

---

## 1. Executive Summary

This audit assesses the state of the existing dashboard application (`app.py`), the educational content registry (`src/education/content.py`), the analytics extraction pipeline (`src/federated/analytics.py`), and experimental data artifacts. The purpose is to establish an exact baseline of what exists, identify previously deferred visualizations (particularly in educational Modules 3–8 and advanced research visualizers), and define a structured, non-disruptive implementation mapping for Stage 2F.

### Baseline Status
- **Existing Test Suite:** 141 passing tests across 16 test modules.
- **Historical Benchmark Checksums:** 16 baseline files intact and verified bit-for-bit.
- **Strict Boundaries:** WP2 (Differential Privacy Mechanisms & Accounting), WP3 (Privacy-Aware Trust Calibration), and WP5 (Adversarial Extensions) remain strictly LOCKED. The underlying research algorithms, experimental datasets, and historical artifacts will remain untouched.

---

## 2. Existing Dashboard Architecture

The dashboard is implemented as a single-entry Streamlit application (`app.py`, 1,213 lines) supporting interactive simulation, live PyTorch model execution, explainable AI diagnosis, and educational exploration.

### 2.1 Architectural Characteristics
- **Framework:** Streamlit (`>=1.28.0`), Plotly (`>=5.17.0`), Matplotlib (`>=3.7.0`), PyTorch (`>=2.0.0`).
- **Page Layout:** `layout="wide"`, `initial_sidebar_state="expanded"`.
- **CSS Styling:** Custom CSS classes embedded at the head of `app.py`:
  - `.status-banner-normal`: Emerald gradient for healthy network operation.
  - `.status-banner-alert`: Crimson gradient for active threat isolation.
  - `.node-card`: Dark slate container for participant metadata and reputation standing.
  - `.story-step`: Indigo-bordered container for 5-step defense progression.
  - `.edu-card`: Cobalt-bordered card for conceptual explanations.
- **State Management:** Uses `st.session_state` to maintain:
  - Active dataset track signature (`active_spec`)
  - Server coordinator instance (`st.session_state.server`)
  - Cryptographic audit ledger (`st.session_state.blockchain`)
  - Asymmetric reputation engine (`st.session_state.reputation_mgr`)
  - Round-by-round simulation history (`st.session_state.simulation_history`)
  - Defense log timeline (`st.session_state.recent_defense_events`)
  - Last executed storyboard cache (`st.session_state.last_storyboard`)
- **Data Caching:** `@st.cache_resource(show_spinner=False)` on dataset loaders (`load_track_a_dataset`, `load_track_b_preset`) guarantees that preprocessing, one-hot encoding, and 3-way train/val/test splits occur once per session.
- **Dual-Track Workflow:**
  - **Track A:** Core NSL-KDD cybersecurity benchmark (122 features, binary classification, 5 simulated nodes).
  - **Track B:** General tabular adaptability (Breast Cancer, Iris, Wine, and custom CSV uploads with strict 3-way isolation).

---

## 3. Six Dashboard Sections & Current Capabilities

| Section | Title | Primary Components & Current Capabilities | Limitations / Deferred Needs |
| :--- | :--- | :--- | :--- |
| **Section 1** | **🌐 System Overview** | • Global health banner (`OPERATIONAL` vs `ACTIVE THREAT`).<br>• 4 KPIs: Participants, Threat Containment, Trust Index, Ledger Height.<br>• 5 Simulated Participant Cards with Dirichlet sample counts and trust scores.<br>• Recent autonomous defense timeline.<br>• Level 2 Expander: Stacked bar chart of $\text{Dir}(\alpha=0.5)$ class counts. | • Static node cards lack interactive topology visualization.<br>• Does not dynamically illustrate the physical vs. simulated architectural distinction. |
| **Section 2** | **⚙️ FL & Defense Studio** | • Track A/B switcher and 3-way research isolation panel.<br>• Preset selector for Scenarios S1 through S7.<br>• Dynamic hyperparameter controls (rounds, flip ratios, sybil intensity, stealth factors).<br>• Live PyTorch execution via `FederatedOrchestrator`.<br>• 6 Stage 2D cumulative metrics (Global Acc, Clean Acc, ASR, MUDR, MURR, FPR).<br>• 5-Step Defense & Recovery Storyboard.<br>• Level 2 Expander: Convergence line chart. | • Lacks interactive step-by-step lifecycle workflow animation.<br>• Aggregator selection does not provide visual coordinate-wise comparison before execution. |
| **Section 3** | **🛡️ Trust & Governance** | • Asymmetric governance explainer card (+0.05 / -0.35, 0.40 quarantine, 3 probation).<br>• Dynamic reputation trajectory chart with 0.40 threshold.<br>• Participant standing and probation table.<br>• Level 2 Expander: LaTeX formulas for Norm, Cosine, and Loss Delta. | • Lacks interactive multi-criteria radar/gauge visualizer showing how candidate updates pass/fail each tier in real-time. |
| **Section 4** | **⛓️ Blockchain Audit** | • Cryptographic health banner (`is_chain_valid()`).<br>• 4 KPIs: Blocks, Audited Txs, Accepted Updates, Slashed Attacks.<br>• Interactive Block Inspector with hash, Merkle root, and validator ID.<br>• Transaction ledger table with digital signature verification.<br>• Non-repudiation explanation.<br>• Level 2 Expander: Raw JSON block header viewer. | • Lacks interactive tamper injection simulator demonstrating Merkle root / hash-pointer cascade failure.<br>• Needs explicit reinforcement of local simulation status. |
| **Section 5** | **📊 Research Intelligence** | • 3 Headline research cards (+31.51 pp advantage, 100.0% isolation, ledger validity).<br>• Historical Stage 2 empirical benchmark table (S1–S6).<br>• Round-by-round accuracy convergence curves.<br>• Real-time packet flow classifier with FastFeatureExplainer (XAI top-5 attributions and plain-English translation table).<br>• Level 2 Expander: Non-IID false-positive analysis text. | • **CRITICAL GAP:** Missing experimental results from Stage 2E Work Package 1 (5-seed pilot, 8 models, Holm p-values).<br>• **CRITICAL GAP:** Missing Stage 2E Work Package 4 results (cryptographic microbenchmarks, aggregation overhead, byte-level communication, tamper audit). |
| **Section 6** | **🎓 Learn & Explore** | • Module selector dropdown (Modules 1–9).<br>• 5 progressive learning tabs (Understand, Visualize, Math, Technical, Quiz).<br>• Knowledge check quizzes with instant grading and explanation.<br>• Linkages to active source code and operational dashboard sections. | • **MAJOR DEFICIENCY:** Interactive Level 2 visualizers only exist for Modules 1, 2, and 9. Modules 3–8 fall back to static text via `st.info()`. |

---

## 4. Nine Educational Modules & Five Learning Levels

Each of the 9 modules registered in `src/education/content.py` implements a structured 5-level pedagogical hierarchy:

| Level | Name | Purpose & Implementation | Status |
| :---: | :--- | :--- | :---: |
| **Level 1** | **Understand** | Plain-English executive summary, real-world intuitive analogy, practical significance, and core concept bullet points. | **Complete (9/9)** |
| **Level 2** | **Visualize** | Interactive visual demonstration, parameter sliders, process animations, or dynamic diagrams. | **Incomplete (3/9 active, 6/9 deferred)** |
| **Level 3** | **Mathematical Foundations** | Rigorous LaTeX mathematical formulations, variable definitions table, and step-by-step worked numerical calculation. | **Complete (9/9)** |
| **Level 4** | **Technical Deep-Dive** | Algorithmic pseudocode, systems trade-offs, engineering limitations, and architectural realities. | **Complete (9/9)** |
| **Level 5** | **Knowledge Check** | 1–2 multiple-choice questions with unique options, verified correct answer keys, and pedagogical feedback explanations. | **Complete (9/9)** |

### Module-by-Module Educational Inventory

| Module ID | Module Title | Primary Subject | Level 2 `demo_type` Specified in Content | Current Level 2 State in `app.py` |
| :--- | :--- | :--- | :--- | :--- |
| `module_1` | Federated Learning Fundamentals | Collaborative training, client-server coordination, communication rounds | `fl_lifecycle` | **Active:** 4 static story-step cards. Needs interactive round selection. |
| `module_2` | Non-IID Data & Statistical Heterogeneity | Statistical skew, class imbalance, Dirichlet distribution | `dirichlet_slider` | **Active:** Dirichlet alpha slider with bar chart. Needs per-client breakdown. |
| `module_3` | Privacy-Preserving Machine Learning | L2 clipping, Gaussian perturbation, empirical vs. formal DP | `clipping_visualizer` | **DEFERRED:** Falls back to `st.info()`. |
| `module_4` | Federated Aggregation Algorithms | FedAvg, Median, Trimmed Mean, Trust-Weighted | `aggregator_comparison` | **DEFERRED:** Falls back to `st.info()`. |
| `module_5` | Security Threats & Poisoning Attacks | Label-flipping, Gaussian noise, sign-flipping, scaling | `attack_vectors` | **DEFERRED:** Falls back to `st.info()`. |
| `module_6` | Multi-Criteria Trust & Reputation Management | 3-tier inspection, asymmetric slashing, quarantine | `trust_radar` | **DEFERRED:** Falls back to `st.info()`. |
| `module_7` | Blockchain & Cryptography | SHA-256, Merkle trees, ECDSA signatures, PoT | `merkle_builder` | **DEFERRED:** Falls back to `st.info()`. |
| `module_8` | Network Intrusion Detection Systems (IDS) | NSL-KDD benchmark, MLP architecture, XAI attributions | `ids_classifier` | **DEFERRED:** Falls back to `st.info()`. |
| `module_9` | Mathematical Foundations | Vector norms, cosine similarity, high-dimensional geometry | `vector_geometry` | **Active:** Vector angle slider, 2D vector plot, cosine metric. |

---

## 5. Identification of Previously Deferred Visualizations

The audit confirms that the following visualizations were deferred in Stage 2A and must be resolved in Stage 2F:

### 5.1 Educational Module Level 2 Visualizers (Modules 3–8)
1. **Module 3 (`clipping_visualizer`):** Interactive L2-norm clipping visualizer. Requires a vector magnitude slider, clipping threshold $C$ slider, unclipped vs. clipped vector representation on a 2D circle/sphere, and calibrated Gaussian noise injection overlay ($\sigma \cdot C$). Must clearly contrast empirical perturbation against formal DP accounting.
2. **Module 4 (`aggregator_comparison`):** Interactive aggregator comparison tool. Requires an outlier injection slider allowing users to manipulate client update values (e.g. $[1.0, 1.2, 0.9, 1.1, X]$) and dynamically observe how FedAvg, Coordinate Median, Trimmed Mean ($\beta=0.2$), and Trust-Weighted aggregators respond.
3. **Module 5 (`attack_vectors`):** Adversarial attack vector geometry visualizer. Requires interactive selection between Honest updates, Sign-Flipping ($-3.0 \times w$), Gaussian Noise ($\mathcal{N}(0, \sigma^2)$), and Model Scaling ($10 \times w$), showing vector orientations, angles, and distances relative to the consensus cluster.
4. **Module 6 (`trust_radar`):** Multi-Criteria Trust Filter simulator. Interactive widget allowing users to adjust candidate update norm, cosine angle, and validation loss delta, displaying a dynamic 3-tier pass/fail evaluation matrix with a Plotly radar or gauge visualization.
5. **Module 7 (`merkle_builder`):** Interactive 4-transaction Merkle Tree Builder. Displays transactions $T_0..T_3$, intermediate hashes $H_{01}, H_{23}$, and the Merkle Root. Includes an interactive "Tamper Transaction" toggle demonstrating instant Merkle root corruption and verification failure.
6. **Module 8 (`ids_classifier`):** Interactive IDSNet Architecture and Flow Inspector. Visualizes the 4-layer MLP topology ($122 \to 128 \to 64 \to 32 \to 2$) with layer-by-layer forward activation flow and feature attribution bars.

### 5.2 Advanced Research Visualizers (Dashboard Sections 1–5)
1. **Federated Learning Architecture Visualizer (Phase 1.1):** An interactive lifecycle map showing the 5 simulated nodes, local dataset partitions, local training iterations, weight uploads, server aggregation, and global broadcast, with an interactive communication round selector.
2. **Non-IID Data Distribution Visualizer (Phase 1.2):** Enhanced exploration of the $\alpha=0.5$ Dirichlet partition on NSL-KDD, showing per-node class ratios, sample counts, and why class skew induces gradient divergence.
3. **Aggregation Algorithm Comparison Visualizer (Phase 1.3):** Dedicated research visualizer comparing all 6 implemented aggregators (FedAvg, Coordinate Median, Trimmed Mean, Trust-Weighted, Multi-Krum, FoolsGold), detailing client weighting, coordinate-wise sorting, and Byzantine exclusion.
4. **Attack and Defense Visualizer (Phase 1.4):** Interactive exploration of Stage 2D scenarios (Gaussian noise, sign-flipping, label-flipping, sybil coalition, parameterized stealth Byzantine perturbation).
5. **Trust and Reputation Visualizer (Phase 1.5):** Visualizer displaying the exact configured parameters ($\tau_{\text{norm}}=2.5$, $\tau_{\cos}=0.15$, $\tau_{\text{loss}}=1.5$, $+0.05$ reward, $-0.35$ slash, $0.40$ quarantine, 3-round probation).
6. **Blockchain Audit Visualizer (Phase 1.6):** Interactive block sequence explorer with block hash chaining, previous-hash cryptographic pointers, and controlled tampering demonstrations.

### 5.3 Experimental Results Visualizers (Dashboard Section 5)
1. **WP1 Multi-Seed Baseline Comparison (Phase 3.1):** Must consume `data/processed/stage2e/wp1/benchmark_summary_v2.json` to present the 5-seed pilot results across 8 paradigms (Centralized IDS, Local-Silo, FedAvg, Trust-Weighted, FoolsGold, Trimmed Mean, Multi-Krum, Coordinate Median) with mean accuracy, std, macro F1, difference vs. FedAvg, raw p-values, and Holm-adjusted p-values ($p_{\text{adj}} \ge 0.1839$).
2. **WP4 Computational Overhead & Blockchain Audit (Phase 3.2):** Must consume `data/processed/stage2e/wp4/overhead_summary_v2.json` and `serialization_and_negative_control_audit.json` to present cryptographic microbenchmarks (ECDSA sign/verify, SHA-256), aggregation microbenchmarks, serialized communication byte accounting ($104.16$ KiB up / $104.08$ KiB down, $161$-byte pickle container reconciliation), and qualified tampering audit results ($500/500$ detected, $0/100$ false alarms qualified as repeated checks on 1 pristine template).

---

## 6. Existing Reusable Components & UI Patterns

The codebase contains several high-quality patterns that should be reused and extended:
1. **`FastFeatureExplainer` (`src/xai/explainer.py`):** Real-time Input $\times$ Gradient sensitivity attribution for neural network inference.
2. **`compute_research_headline_metrics` (`src/federated/analytics.py`):** Robust error-handling and metric derivation from JSON artifacts.
3. **`FederatedPartitioner` (`src/data/partitioner.py`):** Deterministic Dirichlet partitioning and class distribution statistics.
4. **`ReputationManager` (`src/trust/reputation.py`):** History tracking and status summaries for trust scoring.
5. **`Blockchain` & `Block` (`src/blockchain/`):** Full transaction serialization, Merkle root calculation, and hash derivation.
6. **Plotly Styling Conventions:** Dark template (`plotly_dark`), custom color palettes, and responsive figure sizing.

---

## 7. Missing Functionality Summary

1. **No Interactive Visualizers for Modules 3–8:** Level 2 in `app.py` has no code for `clipping_visualizer`, `aggregator_comparison`, `attack_vectors`, `trust_radar`, `merkle_builder`, or `ids_classifier`.
2. **Section 5 Lacks Stage 2E Empirical Benchmarks:** Section 5 only displays Stage 2 results (`stage2_results.json`). It does not display WP1 multi-seed statistical baselines or WP4 computational overhead / blockchain audit data.
3. **No Interactive Tampering Demonstration:** The blockchain section only shows static mined blocks and transactions without an interactive way to demonstrate how tampering invalidates the chain.
4. **Theme Support Needs Dynamic Contrast:** Hardcoded `plotly_dark` throughout `app.py` requires dynamic theme detection or universal neutral-palette styling to ensure readability if the user toggles light mode.

---

## 8. Proposed Implementation Mapping

To keep `app.py` clean, maintainable, and modular without monolithic code bloat, visualizers will be structured into specialized helper modules in `src/visualization/`:

```
src/visualization/
├── __init__.py
├── educational_widgets.py    <-- Level 2 interactive widgets for Modules 1–9
├── research_visualizers.py   <-- FL architecture, non-IID, aggregators, trust, blockchain
└── results_visualizers.py    <-- WP1 multi-seed baselines & WP4 overhead/audit visualizers
```

### Mapping of Capabilities to Modules

1. **`src/visualization/educational_widgets.py`**:
   - `render_fl_lifecycle_widget()` (Module 1: interactive round & stage step selector)
   - `render_dirichlet_widget()` (Module 2: alpha slider with multi-class distribution)
   - `render_clipping_widget()` (Module 3: L2 norm threshold slider, unclipped vs clipped vector, noise overlay)
   - `render_aggregator_widget()` (Module 4: outlier injection slider, comparison table and bar chart for 4 aggregators)
   - `render_attack_vectors_widget()` (Module 5: interactive attack geometry, angle & magnitude comparisons)
   - `render_trust_radar_widget()` (Module 6: 3-tier trust evaluation simulator with pass/fail indicators)
   - `render_merkle_builder_widget()` (Module 7: 4-transaction Merkle tree with interactive tampering toggle)
   - `render_ids_classifier_widget()` (Module 8: MLP layer activation flow & flow diagnosis inspector)
   - `render_vector_geometry_widget()` (Module 9: vector orientation, dot product, cosine similarity)

2. **`src/visualization/research_visualizers.py`**:
   - `render_fl_architecture_visualizer()` (Section 1 & 2: 5 simulated clients, data isolation, weight transmission)
   - `render_non_iid_distribution_visualizer()` (Section 1: Dirichlet $\alpha=0.5$ class heterogeneity analysis)
   - `render_aggregation_comparison_visualizer()` (Section 2: comparative analysis of 6 aggregation algorithms)
   - `render_attack_defense_visualizer()` (Section 2: interactive Stage 2D attack and defense scenarios)
   - `render_trust_reputation_visualizer()` (Section 3: 3-tier inspection, asymmetric scoring, quarantine dynamics)
   - `render_blockchain_audit_visualizer()` (Section 4: tamper-evident ledger, block inspector, controlled tampering demonstration)

3. **`src/visualization/results_visualizers.py`**:
   - `render_wp1_benchmark_dashboard()` (Section 5: 5-seed pilot, 8 models, Holm p-values, non-significance badges)
   - `render_wp4_overhead_dashboard()` (Section 5: crypto microbenchmarks, aggregator latencies, communication payload accounting, qualified tamper audit results)

4. **`app.py`**:
   - Integrate visualization calls into Section 1 through Section 6.
   - Refine theme handling and responsive styles.

5. **`tests/test_stage2f_dashboard.py`**:
   - Comprehensive test suite covering data loading, calculation accuracy, widget rendering, and theme safety.

---

## 9. Files Expected to Change

| File Path | Type | Planned Modifications |
| :--- | :---: | :--- |
| `reports/STAGE_2F_0_DASHBOARD_AUDIT.md` | New | Comprehensive pre-implementation audit report (this document). |
| `src/visualization/__init__.py` | New | Module exports. |
| `src/visualization/educational_widgets.py` | New | Interactive visualizers for all 9 educational modules across Level 2. |
| `src/visualization/research_visualizers.py` | New | Advanced research visualizers for FL architecture, non-IID, aggregators, attacks, trust, and blockchain. |
| `src/visualization/results_visualizers.py` | New | Experimental results dashboard components for WP1 and WP4. |
| `app.py` | Modified | Integration of new visualizers into Sections 1–6, UI/UX polish, theme adaptation. |
| `tests/test_stage2f_dashboard.py` | New | Automated unit tests for all new dashboard components and calculations. |
| `reports/STAGE_2F_IMPLEMENTATION_REPORT.md` | New | Final implementation report detailing completed components. |
| `reports/STAGE_2F_VISUALIZATION_CATALOG.md` | New | Catalog of all implemented visualizers, parameters, and screenshots. |
| `reports/STAGE_2F_FINAL_VERIFICATION_REPORT.md` | New | Verification report with test execution results and checksum validation. |

---

## 10. Audit Conclusion & Gating Confirmation

The audit of the repository, dashboard, educational modules, and empirical data sources is complete. All previously deferred visualizers and missing analytical dashboards have been inventoried and mapped to concrete, non-disruptive implementation modules.

**Implementation Authorization Checklist:**
- [x] Dashboard architecture audited.
- [x] Six sections and nine educational modules reviewed.
- [x] Deferred visualizers identified and specified.
- [x] Clean modular implementation mapping established.
- [x] Core research algorithms, datasets, and historical artifacts remain strictly isolated.

Phase 0 is complete. Proceeding to Phase 1 through Phase 6 implementation.
