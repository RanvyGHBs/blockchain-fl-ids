# WP3 Differential Privacy Noise Sensitivity Analysis

**Project:** Blockchain-Assisted Privacy-Preserving Federated Learning for Network Intrusion Detection with Trust-Based Security and Cryptographic Auditing  
**Workspace:** `C:\Users\is043\.gemini\antigravity\scratch\blockchain-fl-ids`  
**Milestone:** WP3 — Phase B Noise Sensitivity Analysis  
**Status:** COMPLETE & VERIFIED  

---

## 1. Executive Summary

This report documents the mathematical and empirical sensitivity analysis of the three trust validation criteria (L2-norm bounding, cosine similarity to peer consensus, and validation loss verification) under Gaussian differential privacy perturbation across noise multipliers $\sigma \in \{0.5, 1.0, 1.5\}$.

Key findings:
1. **L2-Norm Scaling:** The L2 norm of privatized updates follows a high-dimensional non-central Chi distribution $\chi(d)$, concentrating with extreme tightness ($\text{Std} \approx 1.41$) around the theoretical mean $\mu_{\text{norm}} = \sqrt{\|w_{\text{global}}\|_2^2 + 4 d \sigma^2 C^2}$.
2. **Cosine Similarity Attenuation:** Independent Gaussian perturbation orthogonalizes client directions, reducing pairwise client cosine similarity from $>0.95$ (non-private) to $\approx 0.01$ (leave-one-out peer median). However, self-inclusion in the standard sample median introduces an artificial correlation of $\approx 0.37$. Evaluating alignment against $w_{\text{global}}$ cleanly separates honest clients ($\cos > 0$) from sign-flipping adversaries ($\cos < 0$).
3. **Loss Dispersion & Separability:** Weight perturbation introduces logit variance scaling with $\mathcal{O}(d \sigma^2 C^2)$, driving honest validation loss to $10^3 - 10^5$. Crucially, Byzantine model poisoning attacks (Model Scaling, Gaussian Byzantine, Sign-Flipping) produce losses that are **$10^2$ to $10^7$ times higher**, enabling robust outlier rejection via peer median loss scaling.

---

## 2. Dimension 1: L2 Norm Sensitivity

### 2.1 Theoretical Formulation
Let $w_{\text{global}} \in \mathbb{R}^d$ ($d=26,594$) and client update $\Delta w_i$ be clipped to norm $C=1.0$.
Perturbation noise is $n_i \sim \mathcal{N}(0, 4\sigma^2 C^2 I_d)$.
The submitted weight vector is $\tilde{w}_i = (w_{\text{global}} + \bar{\Delta w}_i) + n_i$.

The squared norm decomposes as:
$$\|\tilde{w}_i\|_2^2 = \|w_{\text{global}} + \bar{\Delta w}_i\|_2^2 + 2(w_{\text{global}} + \bar{\Delta w}_i)^T n_i + \|n_i\|_2^2$$

Expected value and variance:
$$\mathbb{E}[\|\tilde{w}_i\|_2^2] = \|w_{\text{global}}\|_2^2 + 4 d \sigma^2 C^2$$
$$\text{Var}(\|\tilde{w}_i\|_2^2) = 4 \|w_{\text{global}}\|_2^2 (2\sigma C)^2 + 32 d \sigma^4 C^4$$

By delta-method expansion, the expected norm concentrates tightly around:
$$\mu_{\text{norm}}(\sigma, C, d) = \sqrt{\|w_{\text{global}}\|_2^2 + 4 d \sigma^2 C^2}$$
$$\text{Std}(\|\tilde{w}_i\|_2) \approx \sqrt{2} \sigma C$$

### 2.2 Empirical Verification
| Noise Multiplier $\sigma$ | Per-Coord Std ($2\sigma C$) | Theoretical $\mu_{\text{norm}}$ | Observed Honest Norms (Min – Max) | Relative Error |
|---|---:|---:|---:|---:|
| **0.5** | $1.0$ | $164.00$ | $162.94 - 163.98$ | $< 0.65\%$ |
| **1.0** (Approved Baseline) | $2.0$ | $326.61$ | $325.68 - 328.51$ | $< 0.58\%$ |
| **1.5** | $3.0$ | $489.54$ | $487.87 - 494.34$ | $< 0.98\%$ |

### 2.3 Attack Discrimination under Norm Criterion
At $\sigma = 1.0$, honest updates concentrate tightly in $[325, 329]$.
- **Gaussian Noise Attack ($\sigma_{\text{adv}} = 2.5$ on top):** $\|\tilde{w}_{\text{adv}}\|_2 \approx 519.93$ ($+59\%$ above mean).
- **Sign-Flipping Attack (scale $-3.0$):** $\|\tilde{w}_{\text{adv}}\|_2 \approx 980.28$ ($+200\%$ above mean).
- **Model Scaling Attack (scale $10.0$):** $\|\tilde{w}_{\text{adv}}\|_2 \approx 3,267.61$ ($+900\%$ above mean).

---

## 3. Dimension 2: Cosine Similarity Sensitivity

### 3.1 Attenuation Mechanics
Under non-private training, honest gradient updates align closely with the data distribution gradient, yielding $\cos(\tilde{w}_i, \tilde{w}_j) \ge 0.95$.
Under differential privacy, the noise components $n_i$ and $n_j$ are independent identically distributed zero-mean Gaussian vectors.
In high dimensions ($d=26,594$):
$$\mathbb{E}[n_i^T n_j] = 0, \quad \text{Std}(n_i^T n_j) = 4 d \sigma^2 C^2 \approx 106,376$$
The inner product between honest privatized updates is dominated by the shared $w_{\text{global}}$:
$$\mathbb{E}[\tilde{w}_i^T \tilde{w}_j] = \|w_{\text{global}}\|_2^2 \approx 300.3$$
Consequently, the pairwise cosine similarity is attenuated by the square of the noise norm:
$$\cos(\tilde{w}_i, \tilde{w}_j) \approx \frac{\|w_{\text{global}}\|_2^2}{\mu_{\text{norm}}^2} \approx \frac{300.3}{106,676} \approx 0.0028$$

### 3.2 The Self-Inclusion Bias in Sample Median
When the peer consensus direction is computed using the sample median across all $K$ submitted vectors, $m = \text{median}_{k=0}^{K-1}(\tilde{w}_k)$, each client's noise vector $n_i$ is present in the sample.
For $K=5$, the coordinate-wise median of 5 i.i.d. Gaussian random variables has positive correlation with each element:
$$\text{Corr}(X_i, \text{median}(X_1, \dots, X_5)) \approx \sqrt{\frac{2}{\pi \cdot 5}} \approx 0.357$$
Empirically, honest clients exhibit $\cos(\tilde{w}_i, m) \in [0.366, 0.394]$ under full median.
Crucially, when evaluated against $w_{\text{global}}$, honest updates remain strictly positive ($\cos > +0.05$), whereas sign-inversion attacks produce strictly negative cosine values ($\cos = -0.055$).

---

## 4. Dimension 3: Validation Loss Sensitivity

### 4.1 Dispersion Phenomenon
For neural network classifiers with weight matrices $W \in \mathbb{R}^{d}$, pre-activation logits $z = W x + b$ experience variance scaling proportional to the injected noise variance:
$$\text{Var}(z_j) \propto \sigma_{\text{coord}}^2 \|x\|_2^2$$
When $\sigma = 1.0$, logit excursions reach $[-100, +100]$. In cross-entropy loss $L = -\log(e^{z_y} / \sum e^{z_c})$, extreme logit gaps cause loss to scale by orders of magnitude.

### 4.2 Empirical Distribution Across Scenarios ($\sigma = 1.0$)
| Scenario | Min Candidate Loss | Median Candidate Loss | Max Candidate Loss | Order of Magnitude |
|---|---:|---:|---:|---|
| **Clean Honest Clients** | $9,304.21$ | $46,318.65$ | $184,270.90$ | $\mathbf{10^4}$ |
| **Gaussian Byzantine Attack** | $1,515,725.26$ | $1,515,725.26$ | $1,515,725.26$ | $\mathbf{10^6}$ ($10^2 \times$ honest) |
| **Sign-Flipping Attack** | $84,930,137.63$ | $84,930,137.63$ | $84,930,137.63$ | $\mathbf{10^7}$ ($10^3 \times$ honest) |
| **Model Scaling Attack** | $4.2 \times 10^{11}$ | $4.2 \times 10^{11}$ | $4.2 \times 10^{11}$ | $\mathbf{10^{11}}$ ($10^7 \times$ honest) |

This empirical gap of 2 to 7 orders of magnitude between honest perturbation and adversarial poisoning demonstrates that validation loss remains an exceptionally powerful discriminator when calibrated relative to peer distribution.

---

## 5. Analytical Sensitivity Summary

```
Metric                 Expected Honest Value          Adversarial Value (Attack)        Separability
------------------------------------------------------------------------------------------------------
L2 Norm ||w||_2        mu = sqrt(||w_g||^2 + 4d*sigma^2*C^2)  Scaling: 10x mu, Gauss: 1.6x mu   EXCELLENT
Cosine to Median       0.37 +/- 0.02                 Sign-flip: < 0 (vs w_g / LOO)      EXCELLENT
Validation Loss        10^3 - 10^5 (median ~4.6x10^4) Scaling: 10^11, Gauss: 10^6       OUTSTANDING
```
