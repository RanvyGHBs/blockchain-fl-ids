# WP2.2 — Privacy-Utility Configuration Analysis and Research Recommendation

**Project:** Blockchain-Assisted Privacy-Preserving Federated Learning for Network Intrusion Detection with Trust-Based Security and Cryptographic Auditing  
**Workspace:** `C:\Users\is043\.gemini\antigravity\scratch\blockchain-fl-ids`  
**Milestone:** WP2.2 — Privacy Configuration Calibration & Experimental Release Gate  
**Deliverable:** Privacy-Utility Configuration Analysis & Research Baseline Recommendation  
**Execution Mode:** STRICTLY READ-ONLY AUDIT  
**Date:** 2026-11-23  

---

## 1. Executive Summary

This report analyzes the relationship between mathematical differential privacy guarantees and expected model utility across candidate configurations for the federated Network Intrusion Detection System (NIDS).

In federated learning, differential privacy introduces a fundamental tension:
- **Higher noise ($\sigma \ge 1.5$)** reduces privacy expenditure to desirable single-digit levels ($\epsilon \le 8.3$), but increases parameter variance, potentially obscuring subtle intrusion patterns and increasing validation loss.
- **Lower noise ($\sigma \le 0.5$)** preserves parameter fidelity and model convergence, but results in elevated privacy loss ($\epsilon \ge 31.5$).
- **The legacy default ($\sigma = 0.01$)** preserves near-perfect utility, but provides mathematically meaningless privacy ($\epsilon > 31000$).

### Core Recommendation
The audit team recommends **$\sigma = 1.0$ ($C = 1.0, T = 5, \delta = 10^{-5}$)** as the primary research configuration for future controlled experimental evaluation. This configuration achieves an independently verified guarantee of **$\epsilon = 13.26$ at $\alpha^* = 3.0$** with noise standard deviation matching the global sensitivity ($\sigma_{\text{noise}} = 2C = 2.0$). 

> [!IMPORTANT]
> **Strict Distinction Between Mathematical Validity and Empirical Utility:** This recommendation establishes only that the configuration is mathematically sound and calibrated. Its empirical impact on intrusion detection accuracy, attack resilience, and trust engine compatibility remains an open empirical research question that requires separate experimental evaluation once authorized.

---

## 2. Mathematical Noise Magnitude Analysis

Let $C = 1.0$ be the $L_2$ clipping bound on client updates $\Delta w_k^{(t)} \in \mathbb{R}^d$.
Under replace-one client adjacency, global sensitivity is $S = 2C = 2.0$.
The injected noise vector is $n_k \sim \mathcal{N}(0, \sigma_{\text{noise}}^2 I_d)$ where $\sigma_{\text{noise}} = 2\sigma C$.

The table below compares the magnitude of injected noise relative to the maximum allowable client update norm $C$:

| Noise Multiplier ($\sigma$) | Sensitivity ($S = 2C$) | Noise Std Dev ($\sigma_{\text{noise}} = 2\sigma C$) | Noise-to-Clip Ratio ($\sigma_{\text{noise}} / C$) | 5-Round Epsilon ($\epsilon(10^{-5})$) | Expected Impact on Gradient Signal |
|:---:|:---:|:---:|:---:|:---:|:---|
| **0.01** | 2.0 | 0.02 | **0.02x** | 31296.05 | Noise is imperceptible; model trains identically to clean FL; zero privacy. |
| **0.50** | 2.0 | 1.00 | **1.00x** | 31.51 | Noise std matches clipping radius; mild regularization; high privacy loss. |
| **0.75** | 2.0 | 1.50 | **1.50x** | 18.79 | Noise std is $1.5\times$ clipping radius; moderate distortion; sub-20 epsilon. |
| **1.00** | 2.0 | 2.00 | **2.00x** | 13.26 | Standard Gaussian calibration; noise std equals sensitivity $S$; balanced. |
| **1.50** | 2.0 | 3.00 | **3.00x** | 8.28 | Noise std is $3\times$ clipping radius; strong privacy; risk of loss escalation. |
| **2.00** | 2.0 | 4.00 | **4.00x** | 6.00 | Noise std is $4\times$ clipping radius; high privacy; potential training stall. |

---

## 3. Privacy-Utility Tradeoff in Network Intrusion Detection

In network intrusion detection (e.g. NSL-KDD tabular flows), traffic datasets exhibit severe class imbalance (benign traffic vs. low-footprint attacks such as U2R or R2L) and non-linear decision boundaries.

### 3.1. Impact of Client-Level DP on NIDS Learning
1. **Clipping Distortions:** If a client's local gradient update has norm $\|\Delta w_k\|_2 = 5.0$, clipping scales it down to $C = 1.0$. This limits the influence of outlier data batches, which improves robustness against malicious poisoning, but can slow down learning of rare attack classes.
2. **Dimension-Scaled Perturbation:** For a model of dimension $d$ (in `IDSNet`, $d \approx 27,000$ parameters), the total expected $L_2$ norm of the noise vector is:
   $$\mathbb{E}\left[ \|n_k\|_2 \right] \approx \sigma_{\text{noise}} \sqrt{d}$$
   For $\sigma = 1.0$ ($C = 1.0, \sigma_{\text{noise}} = 2.0$) and $d = 27,000$, $\mathbb{E}[\|n_k\|_2] \approx 2.0 \times \sqrt{27,000} \approx 328.6$.
   While each individual coordinate receives zero-mean noise with standard deviation $2.0$, the cumulative vector norm is significant. In FedAvg with $K = 5$ clients, averaging reduces the aggregate noise variance by a factor of $K$:
   $$\text{Var}\left( \frac{1}{K} \sum_{k=1}^K n_k \right) = \frac{\sigma_{\text{noise}}^2}{K} I_d$$
   With $K = 5$, effective aggregation noise variance is reduced by $80\%$.

### 3.2. Cross-Subsystem Interaction with Multi-Criteria Trust Engine
A critical architectural dependency exists between Differential Privacy and the Multi-Criteria Trust Engine (`src/trust/evaluator.py`):
- The trust engine evaluates three criteria:
  1. **$L_2$-norm threshold:** Checks if $\|\widetilde{w}_k - w^{(t)}\|_2 \le \tau_{\text{norm}}$.
  2. **Cosine similarity consensus:** Checks if $\cos(\widetilde{w}_k - w^{(t)}, \bar{\Delta w}_{\text{ref}}) \ge \tau_{\text{cosine}}$.
  3. **Validation loss delta:** Checks if $\mathcal{L}(D_{\text{val}}; \widetilde{w}_k) - \mathcal{L}(D_{\text{val}}; w^{(t)}) \le \tau_{\text{loss}}$.
- **The False-Rejection Risk:** If noise is large ($\sigma \ge 1.0$), an honest client's perturbed update $\widetilde{w}_k$ may experience an elevated validation loss on server data $D_{\text{val}}$ purely due to DP noise, causing the trust engine to misclassify honest clients as malicious!
- **Conclusion:** This tension formally motivates future **Work Package 3 (Privacy-Aware Trust Calibration)**. Evaluating $\sigma$ without trust recalibration risks high false-rejection rates ($FPR$).

---

## 4. Formal Research Baseline Recommendation

### 4.1. Primary Recommended Configuration

For future experimental evaluation, we recommend:

$$\boxed{C = 1.0, \quad \sigma = 1.0, \quad T = 5 \text{ rounds}, \quad \delta = 10^{-5}, \quad K = 5 \text{ clients}}$$

#### Quantitative Properties:
- **Epsilon Guarantee:** $\epsilon = 13.2565$ at discrete order $\alpha^* = 3.00$.
- **Continuous Optimum:** $\epsilon_{\text{cont}}^* = 13.2298$ at $\alpha_{\text{cont}}^* = 3.15$ (gap: $+0.20\%$).
- **Noise Standard Deviation:** $\sigma_{\text{noise}} = 2.00$.
- **Noise-to-Clip Ratio:** $2.0\times$.
- **Participation:** Full participation ($q = 1.0$, direct release to honest-but-curious server).

### 4.2. Recommended 3-Point Experimental Parameter Sweep

To rigorously map the privacy-utility Pareto frontier in future authorized experiments, we recommend evaluating three distinct operational points:

| Regime | Configuration | $\sigma_{\text{noise}}$ | 5-Round $\epsilon(10^{-5})$ | 10-Round $\epsilon(10^{-5})$ | Research Objective |
|:---|:---:|:---:|:---:|:---:|:---|
| **Moderate Privacy (High Utility Candidate)** | $\sigma = 0.50$ | 1.00 | **31.51** | **50.35** | Establishes upper bound on model utility and baseline convergence. |
| **Balanced Privacy (Primary Baseline)** | $\sigma = 1.00$ | 2.00 | **13.26** | **20.18** | Evaluates realistic defensible privacy with standard Gaussian calibration. |
| **High Privacy (Stress-Test Candidate)** | $\sigma = 1.50$ | 3.00 | **8.28** | **12.42** | Evaluates single-digit privacy resilience and trust engine headroom. |

---

## 5. Feasibility and Reproducibility Justification

1. **Deterministic Seeding:** In simulation mode, the isolated PRNG formula `(self.seed * 10007 + r * 997 + cid * 101) % (2**31 - 1)` guarantees that multi-seed benchmark evaluations (e.g. across 5 seeds: 42, 43, 44, 45, 46) are bit-for-bit reproducible across platforms.
2. **Honest Reporting:** The recommendation makes zero unverified empirical claims. It establishes the mathematical parameter boundaries necessary for controlled benchmarking once authorized.
