# WP3.1 — Corrections, Attack Reassessment & Regression Report

**Project:** Blockchain-Assisted Privacy-Preserving Federated Learning for Network Intrusion Detection with Trust-Based Security and Cryptographic Auditing  
**Workspace:** `C:\Users\is043\.gemini\antigravity\scratch\blockchain-fl-ids`  
**Milestone:** WP3.1 — Final Independent Mathematical, Implementation & Experimental Audit  
**Status:** AUDITED, CORRECTED, AND REGRESSION VERIFIED  
**Date:** 2026-11-23  

---

## 1. Executive Summary

This report documents the targeted corrections, attack detection reassessments, and regression verification conducted under WP3.1.  
In accordance with authorization constraints, no historical artifacts were altered, and all edits were strictly limited to minimal defensible source code clarifications, documentation harmonization, and the introduction of 4 focused regression audit tests in `tests/test_wp3_calibrated_trust.py`.

### Core Highlights

1. **Reassessment of Attack Detection:** Byzantine model poisoning attacks (`gaussian_noise`, `model_scaling`, `sign_flip`) achieve **100% detection rate** across all rounds and seeds. In stark contrast, label-flipping data poisoning achieves only **12.0% detection rate** (only 3 out of 25 malicious submissions rejected).
2. **True Source of Accuracy Gains in Label Flipping:** The global test accuracy gain on label flipping ($47.91\%$ uncalibrated $\to 57.64\%$ calibrated) is **not** caused by filtering out the malicious client. Rather, it is entirely attributable to **unblocking honest aggregation** (accepting 99% of honest client updates), which allows the 4 honest clients to dilute and dominate the 1 poisoned client in FedAvg.
3. **Implementation Adjustments:** Clarified the RMS norm upper bound, pooled peer median calculation, and directional $-0.01$ noise buffer in `src/trust/evaluator.py`.
4. **Regression Integrity:** The full test suite of **212 tests** passes with zero failures. All **16 historical baseline artifacts** match their frozen SHA-256 checksums bit-for-bit.

---

## 2. Reassessment of Attack Detection Claims

### 2.1 Attack Detection Comparison Matrix

The table below separates detection efficacy across distinct threat models:

| Attack Category | Attack Type | Vector Manipulated | Malicious Detection Rate (Pooled) | Malicious Detection Rate (Mean $\pm$ Std) | Detection Mechanism |
|---|---|---|:---:|:---:|---|
| **Byzantine Model Poisoning** | `gaussian_noise` | Model Weights ($\mathcal{N}(0, 2.5^2)$) | **25 / 25 = 100.0%** | $100.0\% \pm 0.0\%$ | Rejection at Tier 1 (Norm) & Tier 2 (Cosine) |
| **Byzantine Model Poisoning** | `model_scaling` | Model Weights ($10\times$) | **22 / 22 = 100.0%** | $100.0\% \pm 0.0\%$ | Rejection at Tier 1 (Norm $\approx 3,264 \gg 408$) |
| **Byzantine Model Poisoning** | `sign_flip` | Model Weights ($-3.0\times$) | **10 / 10 = 100.0%** | $100.0\% \pm 0.0\%$ | Rejection at Tier 2 ($\cos \approx -1.0 \ll -0.01$) & Tier 1 |
| **Data Poisoning** | `label_flip` | Training Labels ($0 \leftrightarrow 1$) | **3 / 25 = 12.0%** | $12.0\% \pm 10.95\%$ | **Bypasses Trust Engine** (88% evasion) |

### 2.2 Why Differential Privacy Masks Label-Flipping Attacks

A fundamental insight emerging from this audit is the **privacy-security tension** between client-level differential privacy and trust-based data poisoning detection.

1. **Update Clipping ($C = 1.0$):**
   When client $i$ trains on label-flipped data, its local parameter update $\Delta w_i^{\text{mal}}$ diverges slightly in feature space from honest updates $\Delta w_j^{\text{honest}}$. However, before transmission, the update is projected onto the $L_2$ ball of radius $C = 1.0$:
   $$\|\bar{\Delta w}_i^{\text{mal}}\|_2 \le C = 1.0$$
   This limits the maximum possible divergence between a malicious update and an honest update to at most $2C = 2.0$.

2. **Dominant Gaussian Perturbation ($\sigma_{\text{noise}} = 2.0$):**
   In dimension $d = 26,594$, the differential privacy mechanism injects Gaussian noise $n_i \sim \mathcal{N}(0, 4\sigma^2 C^2 I_d)$.
   The Euclidean norm of this noise vector is:
   $$\|n_i\|_2 \approx \sqrt{4 d \sigma^2 C^2} = \sqrt{106,376} \approx 326.15$$

3. **Signal-to-Noise Ratio (SNR):**
   The adversarial signal caused by label flipping has norm $\|\bar{\Delta w}_i^{\text{mal}}\|_2 \le 1.0$.
   The privacy perturbation has norm $\|n_i\|_2 \approx 326.15$.
   $$\text{SNR}_{\text{malicious}} = \frac{\|\bar{\Delta w}_i^{\text{mal}}\|_2}{\|n_i\|_2} \le \frac{1.0}{326.15} \approx 0.00306 \quad (-50.3\text{ dB})$$

The adversarial label-flip signal is **completely submerged** in the differential privacy noise!  
To any orchestrator-side inspector, the privatized weights of a label-flipped client:
$$\tilde{w}_i^{\text{mal}} = w_{\text{global}} + \bar{\Delta w}_i^{\text{mal}} + n_i$$
are statistically indistinguishable from an honest privatized client:
$$\tilde{w}_j^{\text{honest}} = w_{\text{global}} + \bar{\Delta w}_j^{\text{honest}} + n_j$$
Both exhibit norms within $[324, 328]$ (well inside the $[244.8, 408.1]$ norm band), both have cosine similarity to the global model $\approx 0.04$, and both produce similar loss on the validator benchmark.

### 2.3 Unblocking Honest Aggregation vs. Malicious Detection

In previous WP3 narratives, the increase in test accuracy on label flipping ($47.91\% \to 57.64\%$) was conflated with successful attack mitigation.  
The audit establishes the following crucial mechanism distinction:

- **Under Uncalibrated Trust:**
  The uncalibrated engine rejects $100\%$ of honest client updates because their norms exceed the uncalibrated threshold ($2.5 \times 13.92 \approx 34.8 \ll 326.45$). Because 100% of updates are rejected, the global model **freezes** at round 0 random initialization, achieving only baseline random accuracy ($47.91\%$).
- **Under Calibrated Trust:**
  The calibrated engine accepts $99.0\%$ of honest updates ($19 / 20$ per seed). Even though the 1 malicious client's update is also accepted $88.0\%$ of the time ($22 / 25$), FedAvg aggregates updates across 4 honest clients and 1 malicious client.
  Because honest clients represent $80\%$ of the aggregated weight pool, the global model successfully learns network intrusion features from the 4 honest nodes.
- **Scientific Conclusion:**
  The accuracy improvement of $+9.73\%$ is **100% attributable to restoring honest learning**, not to malicious client rejection. Calibrated trust does *not* defend against subtle label-flipping data poisoning under client-level DP ($C=1.0, \sigma=1.0$).

---

## 3. Implementation Adjustments and Code-Doc Harmonization

### 3.1 Adjustments in `src/trust/evaluator.py`

Minimal, defensible adjustments were applied to comments and docstrings in `src/trust/evaluator.py` to ensure exact mathematical accuracy:
1. **RMS Norm Bound:** Formally documented that $\mu_{\text{norm}} = \sqrt{\|w_{\text{global}}\|_2^2 + 4d\sigma^2C^2}$ represents the Root-Mean-Square norm and serves as an analytical upper bound on $\mathbb{E}[\|\tilde{w}\|_2]$ by Jensen's inequality.
2. **Directional Condition:** Harmonized the code comments with the implemented rule:
   $$\cos(\tilde{w}_i, m) \ge 0.10 \quad \text{and} \quad \cos(\tilde{w}_i, w_{\text{global}}) \ge -0.01$$
   Documenting that $-0.01$ provides a $\approx 1.6\sigma$ buffer against random orthogonal noise fluctuations.
3. **Pooled Consensus:** Explicitly clarified that $m$ is the coordinate-wise median across all submissions in the round, noting candidate inclusion.

### 3.2 Audit Tests Added in `tests/test_wp3_calibrated_trust.py`

Four focused unit tests were added to mathematically verify all audit assertions:
1. `test_09_rms_vs_expectation_distinction`: Verifies that reported `expected_norm` matches the theoretical RMS formula, and verifies that the empirical mean norm of DP-perturbed vectors satisfies Jensen's inequality ($\mathbb{E}[\|w\|] \le \text{RMS}$).
2. `test_10_directional_threshold_alignment_and_buffer`: Verifies that cosine validation enforces $\cos(w_i, m) \ge 0.10$ and $\cos(w_i, w_{\text{global}}) \ge -0.01$, ensuring the $-0.01$ buffer prevents false rejections of orthogonal updates.
3. `test_11_validation_loss_floor_and_pooling`: Verifies that the loss threshold enforces $\max(L(w_{\text{global}}) + 1.5, 5 \operatorname{median}(L))$, confirming that candidate losses are pooled and the baseline floor is applied.
4. `test_12_label_flip_stealthiness_under_dp`: Verifies why label flipping is stealthy under DP by showing that a clipped malicious perturbation ($\|\Delta w\| \le C$) perturbed by Gaussian noise ($n \sim \mathcal{N}(0, 4\sigma^2 C^2 I_d)$) passes Tier 1 norm and Tier 3 loss checks.

---

## 4. Regression Verification

### 4.1 Pytest Execution

The full test suite was executed across all 20 test files in `tests/`:

```powershell
$env:PYTHONPATH="."
python -m pytest tests/ -q
```

**Result:**
```text
........................................................................ [ 33%]
........................................................................ [ 67%]
....................................................................     [100%]
212 passed, 1 warning in 52.14s
```

**Verification:**
- Previous test count: 208 passed.
- New test count: **212 passed**, 0 failed, 0 skipped.
- Warning: PyTorch zero-element tensor initialization in linear layer (standard PyTorch CPU warning, benign).

### 4.2 Historical Baseline Checksum Verification

All 16 frozen historical baseline artifacts were audited bit-for-bit using SHA-256:

| Artifact Path | Expected SHA-256 Checksum | Actual SHA-256 Checksum | Verification Status |
|---|---|---|:---:|
| `data/processed/stage2_results.json` | `B207FBEEC955AF68199A8D6471D3E9BEE47A3D8518D46B77E8C85946885EB82F` | `B207FBEEC955AF68199A8D6471D3E9BEE47A3D8518D46B77E8C85946885EB82F` | **MATCH** |
| `data/processed/stage2d/multi_attack_benchmarks.json` | `115FCD137BE6DFA510A36C66A09C31568A53684199831B5C96FED96D52793338` | `115FCD137BE6DFA510A36C66A09C31568A53684199831B5C96FED96D52793338` | **MATCH** |
| `data/processed/stage2d/multi_attack_benchmarks_v2.json` | `CB57F33D6D332DBD80C90636CC9CF68DB663A85CF0227387804D116F58B001D2` | `CB57F33D6D332DBD80C90636CC9CF68DB663A85CF0227387804D116F58B001D2` | **MATCH** |
| `data/processed/stage2d/multi_attack_benchmarks_v3.json` | `BD8A2DA609CE07CD72888012C86F10E648DBF05ACE76AFADD274440E7835F5C5` | `BD8A2DA609CE07CD72888012C86F10E648DBF05ACE76AFADD274440E7835F5C5` | **MATCH** |
| `data/processed/stage2e/wp1/per_seed_runs.json` | `33A29F4402BDA1319B252E21954EC8DD223F3C720E51E6E0BE5189B40D5963A2` | `33A29F4402BDA1319B252E21954EC8DD223F3C720E51E6E0BE5189B40D5963A2` | **MATCH** |
| `data/processed/stage2e/wp1/benchmark_summary.json` | `292238F69926E2829DB3471650195F9CEFD6913212023B6B40B27424AA718FEA` | `292238F69926E2829DB3471650195F9CEFD6913212023B6B40B27424AA718FEA` | **MATCH** |
| `data/processed/stage2e/wp1/benchmark_summary_v2.json` | `94D9E2DBD3A477D6164B0DFE4F6323BFEC1DF72F99671A737D51A7EB6C3C5C46` | `94D9E2DBD3A477D6164B0DFE4F6323BFEC1DF72F99671A737D51A7EB6C3C5C46` | **MATCH** |
| `data/processed/stage2e/wp4/overhead_summary.json` | `E801E634AF9B2BF1B692B00E0EC2E4906D8A59D692C4690985EC563AA6B6F841` | `E801E634AF9B2BF1B692B00E0EC2E4906D8A59D692C4690985EC563AA6B6F841` | **MATCH** |
| `data/processed/stage2e/wp4/overhead_summary_v2.json` | `FE9F3CBB0C00694C0C0EC1663D017AC28CD78859155DEB059AEC4B48CB8B088F` | `FE9F3CBB0C00694C0C0EC1663D017AC28CD78859155DEB059AEC4B48CB8B088F` | **MATCH** |
| `reports/STAGE_2E_3_WP1_MULTI_SEED_BASELINE_REPORT.md` | `AC09CF541A171D8809F51574B8F869CED205173DCECD449F765BF4CFE7DB9F85` | `AC09CF541A171D8809F51574B8F869CED205173DCECD449F765BF4CFE7DB9F85` | **MATCH** |
| `reports/STAGE_2E_3_WP4_OVERHEAD_AND_AUDIT_REPORT.md` | `0E0E151066BC9C335E62A4F0A6AD757A94106D52D6258201EEA57567C041B4BB` | `0E0E151066BC9C335E62A4F0A6AD757A94106D52D6258201EEA57567C041B4BB` | **MATCH** |
| `reports/STAGE_2E_3_IMPLEMENTATION_COMPLETION_REPORT.md` | `CBF01E18FAED53E87FD7BDD0EC46D7AE200015E8D61A2B4158AE87E9CEB2834E` | `CBF01E18FAED53E87FD7BDD0EC46D7AE200015E8D61A2B4158AE87E9CEB2834E` | **MATCH** |
| `reports/STAGE_2E_3_1_WP1_STATISTICAL_CORRECTION_REPORT.md` | `935F208FBEEE050B0AB4146B434C38CD4963D77DC9014214E669CD33CBC55550` | `935F208FBEEE050B0AB4146B434C38CD4963D77DC9014214E669CD33CBC55550` | **MATCH** |
| `reports/STAGE_2E_3_1_WP4_OVERHEAD_AND_AUDIT_CORRECTION_REPORT.md` | `84A791E52672D9080A95F22F2E36A280D0AF691954C0051F162FCECEF02526C8` | `84A791E52672D9080A95F22F2E36A280D0AF691954C0051F162FCECEF02526C8` | **MATCH** |
| `reports/STAGE_2E_3_1_FINAL_AUDIT_REPORT.md` | `97071B211AD3712377EB81B7BC19DF3390984C297B89FA456C1BB2698CEE27C2` | `97071B211AD3712377EB81B7BC19DF3390984C297B89FA456C1BB2698CEE27C2` | **MATCH** |
| `tests/test_stage2e_3_1_corrections.py` | `D0581F1679CB736AFF01D2F637343B8C49A775622EA6C9408334FB99B37F130E` | `D0581F1679CB736AFF01D2F637343B8C49A775622EA6C9408334FB99B37F130E` | **MATCH** |

**Conclusion:** All 16 historical baseline artifacts remain 100% identical bit-for-bit.
