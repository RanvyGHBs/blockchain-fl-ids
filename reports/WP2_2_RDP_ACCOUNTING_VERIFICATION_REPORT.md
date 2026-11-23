# WP2.2 — Rényi Differential Privacy Accounting Verification Report

**Project:** Blockchain-Assisted Privacy-Preserving Federated Learning for Network Intrusion Detection with Trust-Based Security and Cryptographic Auditing  
**Workspace:** `C:\Users\is043\.gemini\antigravity\scratch\blockchain-fl-ids`  
**Milestone:** WP2 — Formal Client-Level Privacy Mechanism & Accounting  
**Deliverable:** WP2.2 RDP Accounting Verification Report  
**Date:** 2026-11-23  

---

## 1. Executive Summary

This report documents the mathematical foundation, discrete optimization procedure, and empirical verification of the **Rényi Differential Privacy (RDP)** accounting system developed in Work Package 2 (WP2).

The implementation (`src/privacy/rdp_accountant.py::RDPAccountant`) tracks the cumulative privacy expenditure across $T$ adaptive rounds of federated model training without relying on naive advanced composition theorems (which introduce loose constants). It provides tight, exact conversion to standard approximate $(\epsilon, \delta)$-differential privacy by minimizing the privacy loss across a configurable discrete set of 17 Rényi orders $\alpha \in [1.25, 128.0]$.

### Key Mathematical Findings
1. **Invariance to Clipping Threshold $C$:** Under replace-one client adjacency ($S = 2C$) and Gaussian perturbation ($\sigma_{\text{noise}} = 2\sigma C$), the per-round RDP bound is $\epsilon_{\text{RDP}}(\alpha) = \frac{\alpha S^2}{2\sigma_{\text{noise}}^2} = \frac{\alpha}{2\sigma^2}$. The clipping threshold $C$ cancels out algebraically.
2. **Strict Linear Composition:** Conditioned on the history of prior rounds $\mathcal{T}_{<t}$ and current global model $w^{(t)}$, the $L_2$-norm clipping operator unconditionally enforces sensitivity $S_t \le 2C$ in every round $t$. Consequently, RDP accumulates strictly additively: $\epsilon_{\text{RDP}}^{(T)}(\alpha) = \sum_{t=1}^T \frac{\alpha}{2\sigma_t^2} = \frac{T\alpha}{2\sigma^2}$.
3. **Discrete Order Minimization:** Converting cumulative RDP to $(\epsilon, \delta)$-DP via discrete grid search over $\mathcal{A}_{\text{orders}}$ achieves near-optimal bounds while remaining completely deterministic, numerically stable, and free from continuous optimization solver dependencies.

---

## 2. Theoretical Foundations

### 2.1. Rényi Differential Privacy (RDP)

Introduced by Mironov (2017), Rényi Differential Privacy is based on the Rényi divergence of order $\alpha > 1$ between probability distributions $P$ and $Q$:

$$D_\alpha(P \| Q) = \frac{1}{\alpha - 1} \ln \int \left( \frac{P(x)^\alpha}{Q(x)^{\alpha - 1}} \right) dx$$

A randomized mechanism $\mathcal{M}$ satisfies $(\alpha, \epsilon_{\text{RDP}}(\alpha))$-RDP if for all adjacent datasets $\mathcal{D} \sim \mathcal{D}'$:
$$D_\alpha\left( \mathcal{M}(\mathcal{D}) \,\|\, \mathcal{M}(\mathcal{D}') \right) \le \epsilon_{\text{RDP}}(\alpha)$$

### 2.2. Gaussian Mechanism RDP Bound

For a function $f: \mathscr{D} \to \mathbb{R}^d$ with global $L_2$ sensitivity $S = \sup_{\mathcal{D} \sim \mathcal{D}'} \|f(\mathcal{D}) - f(\mathcal{D}')\|_2$, the Gaussian mechanism $\mathcal{M}(\mathcal{D}) = f(\mathcal{D}) + \mathcal{N}(0, \sigma_{\text{noise}}^2 I_d)$ has exact Rényi divergence:

$$D_\alpha\left( \mathcal{N}(f(\mathcal{D}), \sigma_{\text{noise}}^2 I_d) \,\|\, \mathcal{N}(f(\mathcal{D}'), \sigma_{\text{noise}}^2 I_d) \right) = \frac{\alpha \|f(\mathcal{D}) - f(\mathcal{D}')\|_2^2}{2 \sigma_{\text{noise}}^2}$$

Taking the supremum over all adjacent pairs $\mathcal{D} \sim \mathcal{D}'$:
$$\epsilon_{\text{RDP}}(\alpha) = \frac{\alpha S^2}{2 \sigma_{\text{noise}}^2}$$

### 2.3. Exact Substitution for Client-Level Mechanism

In our client-level mechanism under replace-one-client-dataset adjacency:
- Global sensitivity: $S = 2C$
- Gaussian noise standard deviation: $\sigma_{\text{noise}} = 2\sigma C$

Substituting these into the RDP equation:
$$\epsilon_{\text{RDP}}(\alpha) = \frac{\alpha (2C)^2}{2 (2\sigma C)^2} = \frac{\alpha \cdot 4C^2}{2 \cdot 4\sigma^2 C^2} = \frac{\alpha}{2\sigma^2}$$

This proves that:
1. The per-round RDP expenditure is purely a function of the Rényi order $\alpha$ and the dimensionless noise multiplier $\sigma$.
2. The physical clipping bound $C$ affects the gradient scale and model accuracy, but does not alter the formal privacy guarantee when noise is calibrated proportionally.

---

## 3. Composition and Conversion

### 3.1. Composition Across Adaptive Rounds

In federated learning, round $t$ depends on the broadcast model $w^{(t)}$, which is a function of updates from rounds $1, \dots, t-1$. 

Standard DP composition theorems can become complex under adaptive mechanisms. However, RDP possesses an exact composition property for adaptive sequences (Mironov, 2017, Proposition 1):

If $\mathcal{M}_1, \dots, \mathcal{M}_T$ are sequentially composed mechanisms where $\mathcal{M}_t$ conditionally satisfies $(\alpha, \epsilon_t(\alpha))$-RDP given the outputs of all previous mechanisms $\mathcal{M}_1, \dots, \mathcal{M}_{t-1}$, then the composed mechanism $\mathcal{M}_{1:T}$ satisfies:
$$\epsilon_{\text{RDP}}^{(T)}(\alpha) = \sum_{t=1}^T \epsilon_t(\alpha)$$

Because our mechanism enforces $L_2$ clipping $\|\bar{\Delta w}_k^{(t)}\|_2 \le C$ unconditionally on client updates at round $t$, the conditional sensitivity $S_t \le 2C$ holds regardless of $w^{(t)}$ or historical updates. Thus, for constant noise multiplier $\sigma$:
$$\epsilon_{\text{RDP}}^{(T)}(\alpha) = \sum_{t=1}^T \frac{\alpha}{2\sigma^2} = \frac{T\alpha}{2\sigma^2}$$

### 3.2. Conversion to Approximate $(\epsilon, \delta)$-DP

To interpret privacy in standard $(\epsilon, \delta)$-DP terms, we use the conversion lemma (Balle & Wang, 2018; Mironov, 2017):

If a mechanism satisfies $(\alpha, \epsilon_{\text{RDP}}(\alpha))$-RDP for any $\alpha > 1$, then for any target failure probability $\delta \in (0, 1)$, it satisfies $(\epsilon(\delta), \delta)$-differential privacy with:
$$\epsilon(\delta) \le \epsilon_{\text{RDP}}(\alpha) + \frac{\ln(1/\delta)}{\alpha - 1}$$

To obtain the tightest guarantee, we minimize over all admissible orders $\alpha \in \mathcal{A}_{\text{orders}}$:
$$\epsilon^*(\delta) = \min_{\alpha \in \mathcal{A}_{\text{orders}}} \left[ \frac{T\alpha}{2\sigma^2} + \frac{\ln(1/\delta)}{\alpha - 1} \right]$$

### 3.3. Discrete Candidate Orders $\mathcal{A}_{\text{orders}}$

Continuous optimization of $\alpha$ can introduce floating-point solver instabilities. We define a discrete, monotonic evaluation grid covering orders from near-linear ($1.25$) to high moment orders ($128.0$):
$$\mathcal{A}_{\text{orders}} = \{1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 16.0, 24.0, 32.0, 64.0, 128.0\}$$

---

## 4. Empirical Privacy Accounting Matrix

The following table presents the exact composed $(\epsilon, \delta)$-DP guarantees computed by `RDPAccountant` at target $\delta = 10^{-5}$ across communication rounds $T \in \{1, 5, 10, 20\}$ and noise multipliers $\sigma \in \{0.1, 0.5, 1.0, 2.0\}$:

| Rounds ($T$) | Noise Multiplier ($\sigma$) | Optimal Order ($\alpha^*$) | Composed RDP ($\epsilon_{\text{RDP}}(\alpha^*)$) | Tail Term ($\frac{\ln(1/\delta)}{\alpha^* - 1}$) | Total $\epsilon(\delta = 10^{-5})$ | Privacy Regime |
|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **1** | 0.1 | 1.50 | 75.0000 | 23.0259 | **98.0259** | Weak / Uncalibrated |
| **1** | 0.5 | 3.00 | 6.0000 | 5.7565 | **11.7565** | Moderate |
| **1** | 1.0 | 6.00 | 3.0000 | 2.3026 | **5.3026** | Strong Single-Round |
| **1** | 2.0 | 10.00 | 1.2500 | 1.2792 | **2.5292** | Very Strong Single-Round |
| **5** | 0.1 | 1.25 | 312.5000 | 46.0517 | **358.5517** | Unbounded |
| **5** | 0.5 | 2.00 | 20.0000 | 11.5129 | **31.5129** | Moderate Multi-Round |
| **5** | 1.0 | 3.00 | 7.5000 | 5.7565 | **13.2565** | Defensible |
| **5** | 2.0 | 5.00 | 3.1250 | 2.8782 | **6.0032** | Strong Multi-Round |
| **10** | 0.1 | 1.25 | 625.0000 | 46.0517 | **671.0517** | Unbounded |
| **10** | 0.5 | 1.75 | 39.0000 | 15.3506 | **50.3506** | Degraded |
| **10** | 1.0 | 2.50 | 12.5000 | 7.6753 | **20.1753** | Practical Benchmark |
| **10** | 2.0 | 4.00 | 5.0000 | 3.8376 | **8.8376** | High Privacy |
| **20** | 0.1 | 1.25 | 1250.0000 | 46.0517 | **1296.0517** | Unbounded |
| **20** | 0.5 | 1.50 | 60.0000 | 23.0259 | **83.0259** | Degraded |
| **20** | 1.0 | 2.00 | 20.0000 | 11.5129 | **31.5129** | Moderate Long-Horizon |
| **20** | 2.0 | 3.00 | 7.5000 | 5.7565 | **13.2565** | Defensible Long-Horizon |

### Observations:
1. **Order Shift ($\alpha^*$):** As round count $T$ increases, the optimal order $\alpha^*$ shifts downward toward smaller orders (e.g. from $\alpha^* = 6.0$ down to $\alpha^* = 2.0$ for $\sigma = 1.0$). This matches the analytical behavior where the first term grows with $T$, forcing the minimizer to favor smaller $\alpha$.
2. **Noise Multiplier Scaling:** Moving from $\sigma = 0.5$ to $\sigma = 1.0$ reduces $\epsilon$ at $T = 10$ from $50.35$ to $20.18$ (a $59.9\%$ privacy improvement). Moving to $\sigma = 2.0$ yields $\epsilon = 8.84$, achieving a strong single-digit privacy guarantee for a 10-round intrusion detection federation.

---

## 5. Implementation Verification in `tests/test_wp2_privacy.py`

The accountant was verified across seven dedicated test routines:
1. `test_default_orders_validity`: Validates that all default orders are strictly $> 1.0$, sorted, and complete.
2. `test_invalid_orders_rejection`: Confirms that non-positive, non-finite, empty, or $\le 1.0$ orders immediately raise `ValueError`.
3. `test_per_round_rdp_values`: Verifies that `step(sigma=0.5)` produces exact theoretical values $2.0 \times \alpha$ across test orders.
4. `test_multi_round_linear_composition`: Confirms that 5 rounds of $\sigma = 0.4$ accumulate exactly $5 \times \frac{\alpha}{2(0.4)^2}$.
5. `test_discrete_order_minimization`: Confirms exact mathematical correspondence between automated `get_epsilon(1e-5)` output and manually evaluated discrete candidate minima.
6. `test_delta_validation`: Confirms that $\delta \le 0$, $\delta \ge 1$, NaN, or Inf values are rejected with `ValueError`.
7. `test_monotonicity_wrt_rounds_and_noise`: Verifies that $\epsilon(\delta)$ is strictly monotonically increasing with round count $T$ and strictly monotonically decreasing with noise multiplier $\sigma$.
8. `test_round_zero_edge_case`: Verifies that an accountant initialized with zero steps returns $(\epsilon = 0.0, \alpha^* = \alpha_{\min})$.

**Verification Result:** All RDP accountant tests passed with zero errors.
