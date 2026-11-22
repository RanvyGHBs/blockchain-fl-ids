# Stage 2E.1 — Executive Decision Summary & Authorization Gate
## Privacy-Aware Trust Calibration for Blockchain-Audited Federated Network Intrusion Detection

**Project:** Blockchain-Assisted Privacy-Preserving Federated Learning for Network Intrusion Detection with Trust-Based Security and Cryptographic Auditing  
**Workspace:** `C:\Users\is043\.gemini\antigravity\scratch\blockchain-fl-ids`  
**Milestone:** Stage 2E.1 (Methodological Corrections & Planning Package Revision)  
**Status:** REVISED PLANNING COMPLETE — STRICT AUTHORIZATION GATE (Zero Code Modifications)  
**Date:** November 2026  

---

## 1. Executive Summary & Revised Research Focus

Stage 2E.1 delivers a comprehensive, methodologically sound revision of the Stage 2E planning package. It eliminates unsupported assumptions, rectifies architectural discrepancies, formalizes privacy and statistical testing terminology, and aligns all experimental designs with the verified codebase.

### 1.1 The Central Research Contribution
> **Privacy-Aware Trust Calibration for Blockchain-Audited Federated Network Intrusion Detection**

**Central Research Question:**
> *How can a federated intrusion detection system reliably distinguish malicious client updates from legitimate statistical deviations introduced by privacy-preserving perturbation?*

**Methodological Stance:**
We do **not** claim that a simple closed-form threshold function $\tau = f(C, \sigma, d)$ is automatically sufficient before experimental validation. Instead, the research investigates the precise impact of privacy perturbation on update geometry ($L_2$ norm, cosine similarity to peer consensus) and validation loss, formulating and testing both empirical and theoretical calibration models to minimize honest-client false positives without compromising Byzantine poisoning detection.

---

## 2. Summary of Major Corrections in Stage 2E.1

| Dimension | Initial Stage 2E Proposal | Corrected Stage 2E.1 Specification |
|:---|:---|:---|
| **Trust Architecture** | Introduced fictitious "Beta Reputation & Two-Strike Quarantine" | **Retained verified Stage 2D implementation:** Asymmetric $+0.05 / -0.35$ scoring, quarantine threshold $R < 0.40$, 3-round shadow probation. Privacy calibration is framed as an extension to `MultiCriteriaTrustEngine`. |
| **Privacy Mechanism** | Claimed formal client-level DP with heuristic noise on absolute weights | **Formalized update clipping on $\Delta \mathbf{w}_i^{(t)}$:** Explicit example-level adjacency, bounded sensitivity $\|\Delta \mathbf{w}_{\text{clipped}}\|_2 \le C$, calibrated Gaussian noise. Terminology restricted to *"clipping-based Gaussian update perturbation (without formal privacy accounting)"* until accountant is verified. |
| **Calibration Theory** | Assumed static formula $\tau = \tau_0 - \kappa \sigma \frac{C}{\sqrt{d}}$ was proven | **Investigative empirical/theoretical framework:** Acknowledges dependencies on model convergence, non-IID skew, and parameter distribution. Evaluates uncalibrated vs empirical quantile vs theoretical linear bounds. |
| **Statistical Testing** | Used contradictory phrase *"Paired Welch's t-test"* | **Rigorous statistical taxonomy:** Paired $t$-test with Cohen's $d_z$ for matched runs; Welch's $t$-test for independent groups; Wilcoxon signed-rank test for small/non-normal matched pairs. |
| **Multi-Seed Scope** | Claimed 5 seeds provided definitive statistical proof | **Designated as an initial statistical pilot:** $S=5$ pilot ensemble ($42, 101, 2024, 777, 999$); formal power analysis required if confidence intervals overlap. |
| **Multi-Krum Baseline** | Included Multi-Krum unconditionally without checking assumptions | **Explicit Byzantine constraint audit:** Validated that Multi-Krum requires $n \ge 2f + 3$. Valid for $n=5, f=1$ (holds with equality); violated for $n=5, f=2$ ($5 < 7$). Multi-Krum baseline execution restricted to valid regimes. |
| **FoolsGold Baseline** | Stacked FoolsGold on top of `MultiCriteriaTrustEngine` | **Standalone baseline aggregator:** FoolsGold evaluated as an alternative aggregator to prevent redundant cosine penalization conflicts. |
| **Dataset Scope** | Added UNSW-NB15 & CIC-IDS2017 to primary scope | **NSL-KDD retained as primary dataset:** Preserves strict 5-stage data isolation; alternate datasets classified strictly as `[Optional Future Extension]`. |
| **Blockchain Characterization** | Overclaimed decentralization and consensus guarantees | **Accurate systems framing:** Characterized strictly as a *"tamper-evident, cryptographically verifiable local audit ledger"*. Evaluates $P_D$ and $P_{\text{FA}}$ over an explicit finite suite of 5 synthetic tamper test cases. |
| **Work Package Sequence** | Privacy first, Baselines second | **Reorganized logically:** WP1 (Baselines & Multi-Seed) $\to$ WP2 (Formal Privacy) $\to$ WP3 (Privacy-Aware Trust Calibration) $\to$ WP4 (Overhead & Audit) $\to$ WP5 (Optional Adversarial Extension). |

---

## 3. Recommended Implementation Scope

We recommend authorizing the **Core Stage 2E.1 Scope (WP1 + WP2 + WP3 + WP4)**:

- **WP1: Multi-Seed Statistical Baseline Evaluation** (High Priority, Low Risk, ~6h)
- **WP2: Formal Privacy Mechanism and Accounting** (High Priority, Medium Risk, ~8h)
- **WP3: Privacy-Aware Trust Calibration [CENTRAL RESEARCH]** (High Priority, Medium Risk, ~10h)
- **WP4: Computational Overhead & Blockchain Audit Evaluation** (Medium-High Priority, Low Risk, ~4h)
- *WP5: Optional Adversarial Extension* (Optional, Low-Medium Risk, ~6h) — Deferred post-core.

### Estimated Total Compute Budget
- Core Scope (WP1–WP4): ~35–45 minutes total CPU runtime on commodity hardware.

---

## 4. Remaining Theoretical & Experimental Uncertainties

To maintain strict scientific integrity, the following uncertainties are explicitly documented for experimental resolution:
1. **RDP Subsampling Verification `[Requires Theoretical Validation]`:** The exact mathematical formulation for RDP under deterministic vs subsampled client participation across multiple rounds must be derived and validated against unit tests before formal $(\epsilon, \delta)$ guarantees can be asserted.
2. **Calibration Bound in Extreme Non-IID Regimes `[Requires Experimental Validation]`:** Under severe Dirichlet skew ($\alpha = 0.1$), client updates diverge naturally due to label partitioning. Whether a single noise calibration parameter $\tau(\sigma)$ can simultaneously accommodate privacy noise and extreme label skew without allowing stealth poisoning remains an open empirical question.
3. **Poisoning vs Noise Indistinguishability Boundary `[Requires Experimental Validation]`:** For subtle targeted poisoning attacks (e.g., flipping $<5\%$ of labels), the parameter trajectory divergence may lie entirely within the standard deviation of legitimate Gaussian perturbation. The empirical boundary where an attack becomes undetectable under differential privacy must be quantified.

---

## 5. Explicit Decisions for Researcher Authorization

Please confirm your preferred options across these four decision points:

### Decision 1: Implementation Scope Package
- **[RECOMMENDED] Option 1A: Core Package (WP1 + WP2 + WP3 + WP4).** Covers multi-seed baselines, formal privacy mechanism on $\Delta \mathbf{w}_i$, privacy-aware trust calibration, empirical overhead profiling, and finite ledger tamper testing.
- **Option 1B: Full Package (WP1 + WP2 + WP3 + WP4 + WP5).** Includes additional adaptive stealth evasion and Sybil coalition experiments.
- **Option 1C: Minimal Package (WP1 alone).** Executes multi-seed baselines and hypothesis tests only.

### Decision 2: Statistical Multi-Seed Budget
- **[RECOMMENDED] Option 2A: 5-Seed Pilot Ensemble ($S=\{42, 101, 2024, 777, 999\}$) with Power Analysis.** Establishes sample variance and 95% Student's $t$ confidence intervals, scaling to $S=10$ only if confidence intervals overlap.
- **Option 2B: 3-Seed Quick Pilot ($S=\{42, 101, 2024\}$).** Faster turnaround (~20 min), wider confidence intervals.

### Decision 3: Differential Privacy Parameterization
- **[RECOMMENDED] Option 3A: Standard Edge Privacy Target ($\sigma = 0.20, C = 1.0$) with Calibration Investigation.** Evaluates uncalibrated vs empirical vs theoretical trust thresholds under clean and poisoned conditions to measure false-positive reduction.
- **Option 3B: Multi-Noise Parameter Sweep ($\sigma \in \{0.0, 0.05, 0.1, 0.2, 0.5\}$).** Comprehensive Pareto frontier evaluation.

### Decision 4: Baseline Models Selection
- **[RECOMMENDED] Option 4A: 4-Baseline Suite.** Centralized-IDS (ceiling), Local Silos (floor), Multi-Krum (under $n \ge 2f + 3$), and FoolsGold (standalone aggregator).
- **Option 4B: Bounds-Only Baselines.** Centralized-IDS and Local Silos only.

---

## 6. Verification and Integrity Attestation

We formally certify that during the entirety of Stage 2E.1:
1. **Zero Source Code Alterations:** No files in `src/` were created, modified, or touched.
2. **Zero Test Suite Alterations:** No files in `tests/` were modified; all 112 existing unit tests remain intact and passing (`112 passed, 1 warning in 26.96s`).
3. **Zero Benchmark Regressions:** No benchmark JSON files were modified or regenerated.
4. **Original Stage 2E Planning Preserved:** All five original Stage 2E documents in `reports/` remain intact without modification:
   - `STAGE_2E_RESEARCH_GAP_ANALYSIS.md` (29,068 bytes)
   - `STAGE_2E_ARCHITECTURE_PROPOSAL.md` (24,157 bytes)
   - `STAGE_2E_EXPERIMENTAL_PROTOCOL.md` (17,624 bytes)
   - `STAGE_2E_IMPLEMENTATION_ROADMAP.md` (18,560 bytes)
   - `STAGE_2E_DECISION_SUMMARY.md` (9,270 bytes)
5. **Historical Benchmark Checksums (Bit-for-Bit Frozen):**
   - `data/processed/stage2_results.json`: `b207fbeec955af68199a8d6471d3e9bee47a3d8518d46b77e8c85946885eb82f`
   - `data/processed/stage2d/multi_attack_benchmarks.json`: `115fcd137be6dfa510a36c66a09c31568a53684199831b5c96fed96d52793338`
   - `data/processed/stage2d/multi_attack_benchmarks_v2.json`: `cb57f33d6d332dbd80c90636cc9cf68db663a85cf0227387804d116f58b001d2`
   - `data/processed/stage2d/multi_attack_benchmarks_v3.json`: `bd8a2da609ce07cd72888012c86f10e648dbf05ace76afadd274440e7835f5c5`

---

## 7. Deliverables Index for Stage 2E.1

All five revised planning documents are complete and persisted in `reports/`:
1. [STAGE_2E_1_RESEARCH_GAP_ANALYSIS.md](file:///C:/Users/is043/.gemini/antigravity/scratch/blockchain-fl-ids/reports/STAGE_2E_1_RESEARCH_GAP_ANALYSIS.md)
2. [STAGE_2E_1_ARCHITECTURE_PROPOSAL.md](file:///C:/Users/is043/.gemini/antigravity/scratch/blockchain-fl-ids/reports/STAGE_2E_1_ARCHITECTURE_PROPOSAL.md)
3. [STAGE_2E_1_EXPERIMENTAL_PROTOCOL.md](file:///C:/Users/is043/.gemini/antigravity/scratch/blockchain-fl-ids/reports/STAGE_2E_1_EXPERIMENTAL_PROTOCOL.md)
4. [STAGE_2E_1_IMPLEMENTATION_ROADMAP.md](file:///C:/Users/is043/.gemini/antigravity/scratch/blockchain-fl-ids/reports/STAGE_2E_1_IMPLEMENTATION_ROADMAP.md)
5. [STAGE_2E_1_DECISION_SUMMARY.md](file:///C:/Users/is043/.gemini/antigravity/scratch/blockchain-fl-ids/reports/STAGE_2E_1_DECISION_SUMMARY.md)

---

## 8. Authorization Gate & Next Steps

**STAGE 2E.1 PLANNING IS COMPLETE.**  
This is a planning-only milestone. No implementation code has been written, and development will remain halted until explicit researcher authorization is provided.
