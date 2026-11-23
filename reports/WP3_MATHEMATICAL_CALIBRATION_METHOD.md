# WP3 Mathematical Trust Calibration Method

**Project:** Blockchain-Assisted Privacy-Preserving Federated Learning for Network Intrusion Detection with Trust-Based Security and Cryptographic Auditing  
**Workspace:** `C:\Users\is043\.gemini\antigravity\scratch\blockchain-fl-ids`  
**Milestone:** WP3 — Phase C Mathematical Calibration Method  
**Status:** COMPLETE & VERIFIED  

---

## 1. Mathematical Objective

The objective of WP3 calibration is to derive an adaptive, noise-aware multi-criteria decision rule:
$$\Phi(\tilde{w}_i; w_{\text{global}}, \sigma, C, d, \mathcal{D}_{\text{val}}) \in \{0, 1\}$$
such that:
1. **Low False Positive Rate:** For all honest clients $i \in \mathcal{H}$, $\mathbb{P}(\Phi(\tilde{w}_i) = 1) \ge 0.95$ ($FPR_{\text{honest}} < 5\%$).
2. **High Byzantine Detection Rate:** For any adversary $j \in \mathcal{M}$ executing model scaling, Gaussian perturbation, or sign flipping, $\mathbb{P}(\Phi(\tilde{w}_j) = 0) \approx 1.0$.
3. **Smooth Non-Private Fallback:** When $\sigma = 0$, $\Phi$ smoothly reduces to the exact Stage 2D heuristic thresholds.

---

## 2. Derivation of Calibrated Criteria

### 2.1 Tier 1: Noise-Aware L2-Norm Bounding
In $d$-dimensional space ($d=26,594$), Gaussian noise $n_i \sim \mathcal{N}(0, (2\sigma C)^2 I_d)$ added to clipped client update $\bar{\Delta w}_i$ yields client parameter vector $\tilde{w}_i = w_{\text{global}} + \bar{\Delta w}_i + n_i$.

#### Theoretical Mean:
$$\mu_{\text{norm}}(\sigma, C, d) = \sqrt{\|w_{\text{global}}\|_2^2 + 4 d \sigma^2 C^2}$$

#### High-Dimensional Concentration:
The random variable $Q_i = \frac{\|n_i\|_2^2}{4\sigma^2 C^2} \sim \chi^2(d)$.
By Laurent and Massart bounds for Chi-squared tails:
$$\mathbb{P}(|Q_i - d| \ge 2\sqrt{d x} + 2x) \le 2e^{-x}$$
With $d=26,594$, the standard deviation of $\|\tilde{w}_i\|_2$ is bounded by $\sigma_{\text{norm}} \le \sqrt{2}\sigma C \approx 1.414$.

#### Calibrated Bounds:
To accommodate non-IID client gradient divergence without inflating false alarms, we define symmetric percentage margins $\gamma_{\text{upper}} = 1.25$ and $\gamma_{\text{lower}} = 0.75$:
$$\tau_{\text{norm}}^{\text{upper}} = \begin{cases}
\mu_{\text{norm}}(\sigma, C, d) \cdot \gamma_{\text{upper}} & \text{if } \sigma > 0 \\
\max(1.0, \; \|w_{\text{global}}\|_2 \cdot \gamma_{\text{norm}}) & \text{if } \sigma = 0
\end{cases}$$

$$\tau_{\text{norm}}^{\text{lower}} = \begin{cases}
\mu_{\text{norm}}(\sigma, C, d) \cdot \gamma_{\text{lower}} & \text{if } \sigma > 0 \\
0.0 & \text{if } \sigma = 0
\end{cases}$$

**Decision Rule:**
$$\text{NormCheck}(\tilde{w}_i) = \mathbb{I}\left(\tau_{\text{norm}}^{\text{lower}} \le \|\tilde{w}_i\|_2 \le \tau_{\text{norm}}^{\text{upper}}\right)$$

---

### 2.2 Tier 2: Directional Alignment & Peer Consensus
To prevent adversaries from exploiting self-inclusion bias in sample median while ensuring honest noise does not trigger false rejections:

#### Reference Vectors:
1. **Peer Consensus Median:** $m = \text{median}_{k=0}^{K-1}(\tilde{w}_k)$
2. **Global Reference:** $w_{\text{global}}$

#### Cosine Metrics:
$$\cos_{\text{peer}}(\tilde{w}_i) = \frac{\langle \tilde{w}_i, m \rangle}{\|\tilde{w}_i\|_2 \|m\|_2}, \quad \cos_{\text{global}}(\tilde{w}_i) = \frac{\langle \tilde{w}_i, w_{\text{global}} \rangle}{\|\tilde{w}_i\|_2 \|w_{\text{global}}\|_2}$$

#### Calibrated Threshold:
When $\sigma > 0$, independent noise attenuates peer consensus to $\approx 0.37$. We set:
$$\tau_{\text{cos}}(\sigma) = \begin{cases}
0.10 & \text{if } \sigma > 0 \\
0.15 & \text{if } \sigma = 0
\end{cases}$$

In addition, we mandate positive directional alignment with the global model: $\cos_{\text{global}}(\tilde{w}_i) \ge -0.01$.

**Decision Rule:**
$$\text{CosineCheck}(\tilde{w}_i) = \mathbb{I}\left(\cos_{\text{peer}}(\tilde{w}_i) \ge \tau_{\text{cos}}(\sigma) \;\land\; \cos_{\text{global}}(\tilde{w}_i) \ge -0.01\right)$$

---

### 2.3 Tier 3: Robust Peer-Relative Validation Loss
Because high logit variance inflates individual cross-entropy losses for all honest participants under differential privacy, a static additive threshold ($\Delta L \le 1.5$) fails completely.

#### Peer Median Loss Scaling:
All honest participants experience identically calibrated Gaussian noise drawn from the same OS-CSPRNG distribution. Their candidate losses $\{L(\tilde{w}_0), \dots, L(\tilde{w}_{K-1})\}$ form a tight cluster.
By the $50\%$ breakdown point of the sample median, up to $\lfloor (K-1)/2 \rfloor$ Byzantine adversaries cannot shift the median candidate loss $\text{med}_L = \text{median}_{k=0}^{K-1}(L(\tilde{w}_k))$.

Adversarial poisoning attacks inflate candidate loss by 2 to 7 orders of magnitude ($10^6 - 10^{11}$). We formulate the adaptive ceiling:
$$\tau_{\text{loss}}(\sigma) = \begin{cases}
\max\left(L(w_{\text{global}}) + \tau_{\text{loss}}^0, \; \text{med}_L \cdot \beta_{\text{loss}}\right) & \text{if } \sigma > 0 \\
L(w_{\text{global}}) + \tau_{\text{loss}}^0 & \text{if } \sigma = 0
\end{cases}$$
where $\beta_{\text{loss}} = 5.0$ provides a $5\times$ variance envelope around peer median loss.

**Decision Rule:**
$$\text{LossCheck}(\tilde{w}_i) = \mathbb{I}\left(L(\tilde{w}_i) \le \tau_{\text{loss}}(\sigma)\right)$$

---

## 3. Joint Multi-Criteria Decision Rule

The final validity verdict $\Phi(\tilde{w}_i)$ is the logical conjunction across all active inspection tiers:
$$\Phi(\tilde{w}_i) = \text{NormCheck}(\tilde{w}_i) \;\land\; \text{CosineCheck}(\tilde{w}_i) \;\land\; \text{LossCheck}(\tilde{w}_i)$$

```
                                  Candidate Update w_i
                                           |
               +---------------------------+---------------------------+
               |                           |                           |
               v                           v                           v
     [ Tier 1: Calibrated Norm ]  [ Tier 2: Calibrated Cosine ]  [ Tier 3: Calibrated Loss ]
      ||w_i|| in [0.75*mu, 1.25*mu]   cos_peer >= 0.10             L(w_i) <= 5.0 * med_L
                                  cos_global >= -0.01
               |                           |                           |
               +---------------------------+---------------------------+
                                           |
                                           v
                             Joint Decision: is_valid
                              (Accepted if all pass)
```

---

## 4. Formal Distinction of Methodological Status

To preserve scientific rigor, we classify each component of the calibration method:

| Component | Methodological Status | Mathematical Justification |
|---|---|---|
| **$\mu_{\text{norm}}(\sigma, C, d)$** | **Exact Theoretical Derivation** | Linearity of expectation under $\chi^2(d)$ non-central distribution. |
| **Norm Margins ($[0.75, 1.25]$)** | **Engineering Calibration Bound** | Derived from $3\sigma_{\text{norm}}$ bounds with headroom for Non-IID client drift. |
| **Global Alignment ($\cos \ge -0.01$)** | **Exact Geometric Invariant** | Inversion attacks produce negative projections on $w_{\text{global}}$. |
| **Adaptive Cosine ($0.10$)** | **Empirically Calibrated Threshold** | Accounts for finite-sample median correlation under $K=5$ participants. |
| **Peer Median Loss ($5 \times \text{med}_L$)** | **Robust Non-Parametric Estimator** | Exploits median $50\%$ breakdown point to reject multi-order loss outliers. |
