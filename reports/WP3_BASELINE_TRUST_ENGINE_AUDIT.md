# WP3 Baseline Trust Engine & Dataflow Audit

**Project:** Blockchain-Assisted Privacy-Preserving Federated Learning for Network Intrusion Detection with Trust-Based Security and Cryptographic Auditing  
**Workspace:** `C:\Users\is043\.gemini\antigravity\scratch\blockchain-fl-ids`  
**Milestone:** WP3 — Phase A Baseline Code & Mathematical Audit  
**Status:** COMPLETE & VERIFIED  

---

## 1. Executive Summary

This audit establishes the mathematical and operational baseline of the original Stage 2D Multi-Criteria Trust Engine (`MultiCriteriaTrustEngine`) when applied to federated learning clients operating under client-level differential privacy (WP2/WP2.4.1).

Our audit reveals that the original Stage 2D heuristic thresholds—designed exclusively for unperturbed, deterministic gradient descent updates—suffer complete operational collapse under the approved differential privacy configuration ($C=1.0, \sigma=1.0, \epsilon \approx 13.26$). Specifically:
1. **L2-Norm Bounding Collapse:** High-dimensional Gaussian perturbation ($d=26,594$) injects an expected noise norm of $\approx 326.15$, dwarfing the uncalibrated norm threshold ($43.30$). Every honest client update breaches the norm ceiling.
2. **Validation Loss Check Collapse:** Weight perturbation causes logit dispersion, raising cross-entropy validation loss by thousands, breaching the heuristic threshold $\Delta L \le 1.5$.
3. **Catastrophic Honest Quarantine:** In Round 1, **100% of honest client updates are rejected** ($FPR = 1.0$). By Round 2, all honest clients are slashed below the quarantine threshold ($R < 0.40$), resulting in complete aggregation failure.

This proves the necessity of **Work Package 3 (Privacy-Aware Multi-Criteria Trust Calibration)** to restore honest client inclusion while preserving Byzantine resilience.

---

## 2. Baseline Architecture Audit

### 2.1 The Three-Tier Inspection Pipeline
In `src/trust/evaluator.py`, `MultiCriteriaTrustEngine` evaluates candidate weights $\tilde{w}_i$ submitted by each client $i \in \{0, \dots, K-1\}$ against current global weights $w_{\text{global}}$:

```
                          Client Model Update w_i
                                     |
               +---------------------+---------------------+
               |                     |                     |
               v                     v                     v
        [ Tier 1: Norm ]     [ Tier 2: Cosine ]    [ Tier 3: Val Loss ]
     ||w_i|| <= 2.5*||w_g||   cos(w_i, med) >= 0.15   L(w_i) - L(w_g) <= 1.5
               |                     |                     |
               +---------------------+---------------------+
                                     |
                                     v
                        Joint Decision: is_valid
                       (Accepted if all 3 pass)
```

### 2.2 Original Heuristic Parameterization
| Parameter | Symbol | Uncalibrated Baseline Value | Intended Purpose |
|---|---|---:|---|
| Norm Threshold Factor | $\gamma_{\text{norm}}$ | $2.5$ | Rejects exploding gradient / scaling attacks |
| Cosine Threshold | $\tau_{\text{cos}}$ | $0.15$ | Rejects sign-inverting / direction-reversing updates |
| Loss Increase Threshold | $\tau_{\text{loss}}$ | $1.5$ | Rejects updates degrading benchmark classification |
| Reputation Reward | $\Delta R_{\text{reward}}$ | $+0.05$ | Slow incremental trust building for honest clients |
| Reputation Penalty | $\Delta R_{\text{slash}}$ | $-0.35$ | Rapid asymmetric punishment for rejected updates |
| Quarantine Threshold | $R_{\text{quarantine}}$ | $0.40$ | Excludes clients with persistent low reputation |
| Probation Duration | $T_{\text{probation}}$ | $3$ rounds | Requires 3 consecutive valid updates to readmit |

---

## 3. Dataflow & Visibility Boundary Analysis

Our audit of `src/federated/orchestrator.py` and `src/federated/client.py` confirms the following dataflow properties:
1. **Client-Side Perturbation Invariant:** Model privatization occurs strictly client-side inside `FederatedClient.privatize_local_weights()`.
2. **Payload Visibility:** The orchestrator and server receive **only** the privatized model parameter vector:
   $$\tilde{w}_i = w_{\text{global}} + \bar{\Delta w}_i + n_i, \quad n_i \sim \mathcal{N}(0, 4\sigma^2 C^2 I_d)$$
3. **Trust Engine Input:** `MultiCriteriaTrustEngine.evaluate_updates()` operates directly on $\tilde{w}_i$. The trust engine has **no visibility** into the unperturbed local weights $w_i$ or raw clipping residual $\bar{\Delta w}_i$.
4. **Cryptographic Signing:** ECDSA digital signatures are generated over the SHA-256 hash of $\tilde{w}_i$, ensuring that the blockchain transaction ledger records exactly what the trust engine validated.

---

## 4. Empirical Verification of Baseline Failure

To measure the uncalibrated trust engine's failure mode under the approved research baseline ($C=1.0, \sigma=1.0, \delta=10^{-5}, T=5, K=5$), we executed 5 independent multi-seed runs with honest clients only (`clean_dp`).

### Table 1: Uncalibrated Trust Engine Performance (Approved DP Baseline)
| Seed | Honest Submitted | Honest Rejected | Honest FPR | Final Quarantined | Chain Blocks | Final Acc |
|---|---:|---:|---:|---:|---:|---:|
| 42 | 25 | 25 | **100.0%** | 5 | 3 | 56.92% |
| 101 | 25 | 25 | **100.0%** | 5 | 3 | 43.08% |
| 2024 | 25 | 25 | **100.0%** | 5 | 3 | 43.08% |
| 777 | 25 | 25 | **100.0%** | 5 | 3 | 43.08% |
| 999 | 25 | 25 | **100.0%** | 5 | 3 | 53.42% |
| **Mean ± Std** | **25.0** | **25.0** | **100.0% ± 0.0%** | **5.0 ± 0.0** | **3.0 ± 0.0** | **47.92% ± 6.74%** |

### 4.1 Chronology of Training Collapse
- **Round 1:** Global weights have norm $\|w_{\text{global}}\|_2 \approx 17.33$. The uncalibrated threshold is $\max(1.0, 17.33 \times 2.5) = 43.32$. Honest client updates exhibit norms of $325.07 - 328.18$. All 5 updates are rejected. Reputations fall from $1.00 \to 0.65$.
- **Round 2:** Since no updates were accepted in Round 1, $w_{\text{global}}$ is unchanged. Clients train again and submit privatized updates ($\|\tilde{w}_i\| \approx 326$). All 5 updates are rejected again. Reputations fall from $0.65 \to 0.30$.
- **Round 3:** Because $0.30 < 0.40$, **all 5 clients are placed in quarantine**. Zero updates are submitted. Training terminates in complete starvation.

---

## 5. Mathematical Root Cause Summary

| Criterion | Uncalibrated Formula | Empirical Honest Value | Observed Outcome | Cause of Breakdown |
|---|---|---|---|---|
| **L2 Norm** | $\|\tilde{w}_i\|_2 \le 2.5 \|w_{\text{global}}\|_2 \approx 43.32$ | $326.61 \pm 1.41$ | **100% Rejected** | $\chi^2(d)$ noise norm ($\approx \sqrt{4 d \sigma^2 C^2}$) ignored |
| **Validation Loss** | $L(\tilde{w}_i) - L(w_{\text{global}}) \le 1.5$ | $\Delta L \in [+10^3, +10^5]$ | **100% Rejected** | High logit variance under weight perturbation ignored |
| **Cosine Similarity** | $\cos(\tilde{w}_i, m) \ge 0.15$ | $0.37 \pm 0.02$ | Passed | Self-inclusion in sample median creates artificial positive bias |

---

## 6. Audit Verdict

**FAIL — UNCALIBRATED BASELINE INCOMPATIBLE WITH DIFFERENTIAL PRIVACY.**  
The Stage 2D heuristic thresholds cannot be deployed alongside client-level differential privacy. A formal noise-aware calibration method (WP3) is mathematically necessary to distinguish between harmless differential privacy noise and genuine adversarial poisoning.
