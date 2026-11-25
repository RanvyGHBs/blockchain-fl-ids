# Trust Calibration, Byzantine Attacks, and Known Weaknesses

This document describes `MultiCriteriaTrustEngine` and `ReputationManager` ([src/trust/evaluator.py](../src/trust/evaluator.py), [src/trust/reputation.py](../src/trust/reputation.py)), the Byzantine and data-poisoning attack implementations ([src/attacks/](../src/attacks/)), and the mathematical findings and caveats established in Work Packages 3 and 3.1.

---

## 1. The DP–Trust Conflict

When client-level differential privacy is enabled ($C = 1.0, \sigma = 1.0$) on `IDSNet` ($d = 26,594$), the coordinate Gaussian perturbation $n_k \sim \mathcal{N}(0, 4\sigma^2 C^2 I_d)$ has coordinate std $2.0$ and expected Euclidean energy:
$$\mathbb{E}[\|n_k\|_2^2] = 4 d \sigma^2 C^2 = 4 \times 26,594 \times 1.0 = 106,376.0 \implies \|n_k\|_2 \approx 326.15$$

Meanwhile, the clipped model update itself has $\|\bar{\Delta w}_k\|_2 \le C = 1.0$ and the round-0/early global model norm is $\|w_{\text{global}}\|_2 \approx 13.92$.

Under the **uncalibrated** Stage 2D trust rules ($\|\tilde{w}_k\|_2 \le 2.5 \|w_{\text{global}}\|_2 \approx 34.8$, $\cos \ge 0.15$):
- **100.0% of honest DP-perturbed client updates are falsely rejected**, quarantining all honest clients by Round 2 and freezing model learning.

---

## 2. Privacy-Aware Multi-Criteria Trust Calibration (`WP3` / `WP3.1`)

Notice a critical architectural fact verified in WP3.1: the orchestrator passes **reconstructed privatized client model weights** $\tilde{w}_k = w_{\text{global}} + \bar{\Delta w}_k + n_k$ (not standalone update vectors $\tilde{\Delta w}_k$) to `MultiCriteriaTrustEngine.evaluate_updates()`. Each update must pass **all enabled tiers**:

### Tier 1: Calibrated RMS L2-Norm Check
Let $u_k = w_{\text{global}} + \bar{\Delta w}_k$. Since $\|\bar{\Delta w}_k\|_2 \le C \ll \|n_k\|_2$, approximating $\|u_k\|_2 \approx \|w_{\text{global}}\|_2$ introduces $< 0.03\%$ error at $d = 26,594$. The engine calculates:
$$\mu_{\text{RMS}} = \sqrt{\|w_{\text{global}}\|_2^2 + 4 d \sigma^2 C^2}$$
Acceptance band:
$$\|\tilde{w}_k\|_2 \in [0.75 \, \mu_{\text{RMS}}, \; 1.25 \, \mu_{\text{RMS}}]$$

**WP3.1 Mathematical Clarifications:**
- $\mu_{\text{RMS}} = \sqrt{\mathbb{E}[\|\tilde{w}_k\|_2^2]}$ is the **Root-Mean-Square (RMS) norm**, **not** the exact expected Euclidean norm $\mathbb{E}[\|\tilde{w}_k\|_2]$. By Jensen's inequality, $\mathbb{E}[\|\tilde{w}_k\|_2] < \mu_{\text{RMS}}$ (differing by $< 0.001\%$ at $d = 26,594$).
- The **$[0.75\mu_{\text{RMS}}, \, 1.25\mu_{\text{RMS}}]$ ($\pm 25\%$) window is an empirical engineering heuristic**, not a derived concentration bound. A formal $3\sigma$ non-central $\chi$ concentration band in $d = 26,594$ spans only $\pm 1.3\%$; the wider $\pm 25\%$ heuristic absorbs Non-IID parameter drift while still catching severe scaling attacks ($10\times$ scaling has norm $\approx 3,264 \gg 408.06$).

### Tier 2: Directional Peer Consensus & Global Alignment
The engine computes the **pooled coordinate-wise median** across *all* submitted candidate vectors in the current round (not leave-one-out $m_{-k}$):
$$m = \operatorname{median}_{j \in \text{submitted}} (\tilde{w}_j)$$
In `privacy_aware` mode, two directional conditions are enforced simultaneously:
$$\cos(\tilde{w}_k, \, m) \ge 0.10 \qquad \text{and} \qquad \cos(\tilde{w}_k, \, w_{\text{global}}) \ge -0.01$$

**WP3.1 Clarifications:**
- Because candidates are included in $m$ (20% share for $K=5$), $\cos(\tilde{w}_k, m)$ has slight self-inclusion bias, though with $K=5$ a single attacker ($20\%$) cannot dictate any coordinate median.
- The **$-0.01$ global alignment floor** accommodates random high-dimensional orthogonal fluctuations ($\sigma_{\cos} \approx 1/\sqrt{d} \approx 0.00613$, giving $\approx -1.63\sigma$ headroom).

### Tier 3: Validation Loss Ceiling
Each candidate model $\tilde{w}_k$ is evaluated on the orchestrator's isolated validation slice `D_val` (`1,000` samples):
$$L(\tilde{w}_k) \le \max\left(L(w_{\text{global}}) + 1.5, \; 5.0 \cdot \operatorname{median}_{j} L(\tilde{w}_j)\right)$$

**WP3.1 Clarification:**
- The additive baseline floor $L(w_{\text{global}}) + 1.5$ ensures stability during early training volatility, but makes the threshold **permissive** ($\tau_{\text{loss}} > 2.0$ when $L_{\text{global}} \approx 0.69$). Consequently, subtle data-poisoning updates pass Tier 3 easily.

---

## 3. Asymmetric Reputation and Quarantine Governance

Implemented in [src/trust/reputation.py](../src/trust/reputation.py) (`ReputationManager`):

| Parameter | Default Value | Rule |
|---|:---:|---|
| Initial Reputation | `1.0` | All participants begin with full trust `[0.0, 1.0]` |
| Honest Round Reward | `+0.05` | $R_k^{(t+1)} = \min(1.0, \; R_k^{(t)} + 0.05)$ |
| Rejected Update Slash | `-0.35` | $R_k^{(t+1)} = \max(0.0, \; R_k^{(t)} - 0.35)$ ($7\times$ faster than recovery) |
| Quarantine Threshold | `< 0.40` | $R_k < 0.40$ isolates client (2 consecutive rejections: $1.0 \to 0.65 \to 0.30$) |
| Shadow Probation | `3 rounds` | Passing 3 consecutive rounds in probation readmits client at `0.50` baseline |

Note: `FederatedOrchestrator` skips `local_train` and update submission completely for quarantined clients; those skipped rounds are tracked separately as `prevented_quarantine` so rejection denominators (`MURR`/`FPR`) are not inflated.

---

## 4. Implemented Attack Models and Robust Aggregators

### Attacks ([src/attacks/](../src/attacks/))
1. **Gaussian Noise Attack** (`model_poisoning.py`): Adds $\mathcal{N}(0, 2.5^2)$ perturbation directly to client model weights (`std=2.5` in orchestrator registry).
2. **Model Scaling Attack** (`model_poisoning.py`): Multiplies full client weights by `scale_factor=10.0`.
3. **Sign-Flipping Attack** (`model_poisoning.py`): Multiplies full client weights by `scale=-3.0` (inverts and amplifies entire parameter vector).
4. **Targeted Label-Flipping Attack** (`targeted_poisoning.py`, `data_poisoning.py`): Inverts local training labels (`1 -> 0`, i.e., Attack to Normal, with configurable `flip_ratio=1.0`) prior to local SGD.
5. **Sybil Coalition Attack** (`sybil_coalition.py`): Multiple colluding nodes (e.g., `[2, 3]`) submit coordinated shifted vectors (`-intensity * w_global`) to distort median/trimmed-mean aggregation (evaluated in Stage 2D).
6. **Parameterized Stealth-Constrained Byzantine Perturbation** (`adaptive_byzantine.py`): Synthesizes an update aligned within geometric cosine/norm margins (`cos >= tau_cos + 0.10`, `norm <= max_norm * 0.90`). Explicitly documented as a static geometric test vector, **not** a closed-loop feedback-adaptive adversary.

### Aggregators ([src/federated/aggregators.py](../src/federated/aggregators.py), [src/evaluation/baselines.py](../src/evaluation/baselines.py))
- `FedAvg` (`aggregate_fedavg`): Sample-count-weighted mean.
- `Trust-Weighted FedAvg` (`aggregate_trust_weighted`): Weighted by $n_k \cdot R_k$.
- `Trimmed Mean` (`aggregate_trimmed_mean`): Coordinate-wise trimming of top/bottom $\beta = 0.2$ fractions.
- `Coordinate Median` (`aggregate_median`): Coordinate-wise median across surviving submissions.
- `Multi-Krum` (`aggregate_multikrum`): Distance-based neighbor scoring ($n \ge 2f + 3$, evaluated in WP1).
- `FoolsGold` (`FoolsGoldAggregator`): Cosine trajectory similarity attenuation against Sybils (evaluated in WP1).

---

## 5. Known Weaknesses and Scientific Boundaries

1. **Label-Flipping Evasion Under DP (~12% Detection):**
   - Clipped label-flip update deltas have $\|\bar{\Delta w}_{\text{mal}}\|_2 \le C = 1.0$, while DP Gaussian noise has $\|n\|_2 \approx 326.15$ ($\text{SNR} \approx 0.00306 \approx -50.3\text{ dB}$).
   - Across 5 seeds in WP3, label-flipping achieved only **$3/25 = 12.0\%$** detection (evading 88% of rounds).
   - The observed mean accuracy difference on label-flipping ($+9.73$ percentage points over uncalibrated freezing) comes from **unblocking honest aggregation** (4 honest clients outvoting 1 poisoned client in FedAvg), **not** from filtering the attacker.
2. **Weight-Space vs. Update-Space Sign Flipping:**
   - Because Tier 2 compares full candidate weights $\tilde{w}_k$ against $w_{\text{global}}$ and the tested benchmark attack inverts full weights ($-3.0 \cdot w$), sign-flipping achieves 100% detection in tested runs. However, an **update-only** sign flip ($w_{\text{global}} - \Delta w_k$) stays close to $w_{\text{global}}$ ($\cos \approx +0.997$) and would bypass global weight alignment.
3. **No Statistical Significance for Test Accuracy Gains:**
   - While calibrated trust cuts honest FPR from `100%` to `1–4%` with overwhelming significance (Holm $p < 10^{-5}$), held-out test accuracy differences across $N = 5$ pilot seeds ($df = 4$) are **not** statistically significant at $\alpha = 0.05$ after Holm-Bonferroni correction (WP3 raw $p \in [0.20, 0.75]$, Holm $p = 1.0000$; WP1 clean baselines Holm $p \ge 0.1839$).
4. **Conditionality of Detection Metrics:**
   - The $100\%$ detection rate for `gaussian_noise`, `model_scaling`, and `sign_flip` applies strictly to the tested attack parameters and threat model under $K=5$ with one attacker (`Client 3`), not as a universal Byzantine guarantee.
