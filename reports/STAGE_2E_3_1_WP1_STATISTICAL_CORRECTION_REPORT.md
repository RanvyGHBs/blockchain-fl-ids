# Stage 2E.3.1 WP1: Statistical Integrity & Multiple-Comparison Correction Report

**Project:** Blockchain-Assisted Privacy-Preserving Federated Learning for Network Intrusion Detection with Trust-Based Security and Cryptographic Auditing  
**Workspace:** `C:\Users\is043\.gemini\antigravity\scratch\blockchain-fl-ids`  
**Milestone:** Stage 2E.3.1 (Methodological Refinement & Research Integrity Audit)  
**Target Domain:** Work Package 1 (Multi-Seed Statistical Baselines)  
**Primary Dataset:** NSL-KDD (Binary Classification, 122 input features, strict 3-way research isolation)  
**Evaluated Pilot Ensemble:** Seeds `[42, 101, 2024, 777, 999]` ($n = 5$ independent matched runs)  
**Audited Artifacts:**
- Historical Summary: `data/processed/stage2e/wp1/benchmark_summary.json` (SHA-256: `292238F69926E2829DB3471650195F9CEFD6913212023B6B40B27424AA718FEA`)
- Versioned Summary: `data/processed/stage2e/wp1/benchmark_summary_v2.json`

---

## 1. Executive Summary & Audit Motivation

During the initial Stage 2E.3 delivery, eight baseline paradigms were evaluated across five random seeds on NSL-KDD. Nominal paired $t$-tests were reported for seven candidate models against standard FedAvg without controlling for multiple hypothesis testing. Furthermore, post-hoc power calculations based on observed pilot effect sizes were characterized as demonstrating that the study was "fully powered."

This audit implements critical methodological corrections:
1. **Multiple Hypothesis Testing Correction:** Evaluates the family of $m = 7$ candidate comparisons against FedAvg under the **Holm-Bonferroni step-down procedure** to strictly control the Family-Wise Error Rate (FWER) at $\alpha = 0.05$.
2. **Corrected Statistical Conclusions:** Demonstrates that while Centralized IDS and Coordinate Median achieved nominal significance under uncorrected tests ($p = 0.0263$ and $p = 0.0347$), **neither comparison survives Holm-Bonferroni correction ($p_{\text{adj}} \ge 0.1839$)**.
3. **Repudiation of Post-Hoc Power Claims:** Reframes power analysis from circular post-hoc claims into prospective sample size planning across plausible effect-size ranges for a future confirmatory study.
4. **Nomenclature and Claim Corrections:** Replaces absolutist terminology ("Ceiling", "Floor", "Zero-Degradation Guarantee") with empirically grounded, defensive descriptions.
5. **Coordinate Median Investigation:** Documents per-seed failure modes and replaces unverified causal claims with qualified, defensible interpretations.

---

## 2. Multiple-Comparison Audit (Holm-Bonferroni Correction)

### 2.1 Theoretical Framework & Family Definition
In Stage 2E.3, seven distinct model paradigms were compared against standard FedAvg using the same five-seed dataset partitions:
$$\mathcal{H} = \{ H_{0, 1}: \mu_{\text{cent}} = \mu_{\text{fed}}, \; H_{0, 2}: \mu_{\text{med}} = \mu_{\text{fed}}, \; \dots, \; H_{0, 7}: \mu_{\text{trust}} = \mu_{\text{fed}} \}$$

Conducting $m = 7$ uncorrected hypothesis tests at $\alpha = 0.05$ inflates the overall family-wise error rate to:
$$\alpha_{\text{FWER}} \le 1 - (1 - \alpha)^m = 1 - (0.95)^7 \approx 30.17\%$$

To control FWER at $\alpha = 0.05$, the **Holm-Bonferroni step-down procedure** sorts the two-sided $p$-values in ascending order:
$$p_{(1)} \le p_{(2)} \le \dots \le p_{(m)}$$
Each hypothesis $H_{(i)}$ is evaluated against the adjusted threshold:
$$\alpha_{(i)} = \frac{\alpha}{m - i + 1}$$
The test steps down from $i = 1$ to $m$. If $p_{(i)} > \alpha_{(i)}$, the procedure **terminates immediately**, failing to reject $H_{(i)}$ and all subsequent hypotheses $H_{(i+1)}, \dots, H_{(m)}$.

The Holm-adjusted $p$-value is defined as:
$$\tilde{p}_{(i)} = \min\left(1.0, \; \max_{j \le i} \left[ (m - j + 1) \cdot p_{(j)} \right]\right)$$

### 2.2 Comprehensive Multiple-Comparison Table ($m = 7, \alpha = 0.05, df = 4$)

| Rank ($i$) | Candidate Model vs FedAvg | Mean Diff ($\bar{D}$) | Cohen's $d_z$ | Paired $t$-stat | Raw $p$-value | Holm Threshold ($\alpha_{(i)}$) | Holm-Adjusted $p$ ($\tilde{p}$) | Significant (Raw) | Significant (Holm) | Corrected Scientific Conclusion |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | **Centralized IDS Reference** | $+0.0628$ | $+1.5389$ | $+3.4410$ | **$0.026270$** | $0.007143$ | **$0.183889$** | **Yes** | **No** | Large observed advantage ($+6.28\%$, $d_z = +1.54$), but not statistically significant after FWER control in $n=5$ pilot. |
| **2** | **Coordinate Median** | $-0.1557$ | $-1.4057$ | $-3.1433$ | **$0.034738$** | $0.008333$ | **$0.208426$** | **Yes** | **No** | Substantial observed degradation ($-15.57\%$, $d_z = -1.41$), but not statistically significant after FWER control in $n=5$ pilot. |
| **3** | **Local-Silo Reference** | $+0.0431$ | $+1.0464$ | $+2.3397$ | $0.079402$ | $0.010000$ | $0.397011$ | No | No | Moderate-large effect ($+4.31\%$, $d_z = +1.05$), not statistically significant before or after correction. |
| **4** | **FoolsGold (Standalone)** | $-0.0469$ | $-0.5794$ | $-1.2956$ | $0.264813$ | $0.012500$ | $1.000000$ | No | No | Moderate degradation ($-4.69\%$), not statistically significant. |
| **5** | **Multi-Krum ($f=1, m=1$)** | $-0.0647$ | $-0.4414$ | $-0.9869$ | $0.379548$ | $0.016667$ | $1.000000$ | No | No | Small-medium degradation ($-6.47\%$), high variance, not statistically significant. |
| **6** | **Trimmed Mean ($\beta=0.2$)** | $-0.0614$ | $-0.4126$ | $-0.9225$ | $0.408468$ | $0.025000$ | $1.000000$ | No | No | Small-medium degradation ($-6.14\%$), high variance, not statistically significant. |
| **7** | **Trust-Weighted FedAvg** | $0.0000$ | $0.0000$ | $0.0000$ | $1.000000$ | $0.050000$ | $1.000000$ | No | No | Identical performance on clean data (zero difference across all 5 seeds). |

### 2.3 Critical Scientific Finding
Because the rank-1 raw $p$-value ($0.0263$) exceeds the rank-1 Holm threshold ($\alpha/7 = 0.00714$):
> **The step-down procedure terminates at the very first step. None of the seven comparisons achieve statistical significance after controlling the Family-Wise Error Rate at $\alpha = 0.05$.**

This does **not** imply that the observed differences are non-existent. Centralized IDS exhibits a very large effect size ($d_z = +1.54$), and Coordinate Median exhibits a very large negative effect size ($d_z = -1.41$). However, in a five-seed pilot study, **the statistical power after multiple-comparison correction is insufficient to reject the null hypothesis at $\alpha = 0.05$**.

---

## 3. Audit of Paired Observations & Confidence Intervals

### 3.1 Verification of Seed-Level Paired Integrity
Inspection of `data/processed/stage2e/wp1/per_seed_runs.json` confirms that:
1. Five independent paired observations exist for each model, matching seeds `42`, `101`, `2024`, `777`, and `999`.
2. All federated models operated on identical Dirichlet non-IID partitions, client batch sequence permutations, and initial model weight initializations for each seed.
3. The paired $t$-test calculations, degrees of freedom ($df = n - 1 = 4$), and standard error calculations were independently recomputed and verified bit-for-bit.

### 3.2 Confidence Interval Sampling Unit Clarification
- **Sampling Unit:** The true experimental unit for all statistical inferences is the **seed-level federated run ($n = 5$)**, NOT the individual test-set examples ($N_{\text{test}} = 22,544$).
- **Distinction:**
  - Sample standard deviation ($s$) measures run-to-run variability across different random seeds.
  - Standard error ($SE = s / \sqrt{5}$) measures the precision of the estimated mean across seeds.
  - 95% Confidence Intervals are calculated as $\bar{x} \pm t_{0.975, 4} \cdot SE$, where $t_{0.975, 4} \approx 2.7764$.
  - The large test set size ($22,544$ records) ensures that within-run measurement error is low, but it does **not** inflate the degrees of freedom for the multi-seed hypothesis tests ($df = 4$).

---

## 4. Revision of Statistical Power Interpretation

### 4.1 Repudiation of "Fully Powered" Claims
The Stage 2E.3 completion report claimed that Centralized IDS and Coordinate Median were "Fully Powered ($N_{\text{req}} = 4 \le 5$)." 

**This claim was methodologically flawed for two reasons:**
1. **Post-Hoc Circularity:** Computing statistical power post-hoc using the *observed effect size* from the same small sample ($n = 5$) is tautological: whenever a small sample happens to show nominal significance ($p < 0.05$), the sample size will almost always appear "adequate" post-hoc.
2. **Multiple Testing Neglect:** The calculation assumed a single comparison ($\alpha = 0.05$), whereas the study evaluated $m = 7$ simultaneous comparisons against FedAvg ($\alpha_{\text{adjusted}} = 0.00714$).

### 4.2 Prospective Confirmatory Sample Size Planning
For a future confirmatory benchmark, sample size planning must be based on a range of prospective effect sizes ($d_z$) at two-sided $\alpha = 0.05$ and target power $1 - \beta = 0.80$:

$$N \approx \left(\frac{z_{1 - \alpha/2} + z_{1 - \beta}}{d_z}\right)^2$$

| Planning Assumption | Hypothesized Effect ($d_z$) | Single Comparison ($\alpha=0.05$) Required $N$ | Family-Wise Corrected ($\alpha=0.00714, m=7$) Required $N$ | Status & Interpretation |
| :--- | :---: | :---: | :---: | :--- |
| **Very Large Effect** | $1.50$ | $4$ seeds | **7 seeds** | Plausible for Centralized vs FedAvg |
| **Large Effect** | $1.00$ | $8$ seeds | **15 seeds** | Plausible for Local Silos vs FedAvg |
| **Medium-Large Effect** | $0.80$ | $13$ seeds | **23 seeds** | Standard Cohen benchmark |
| **Medium Effect** | $0.50$ | $32$ seeds | **58 seeds** | Plausible for subtle aggregator differences |
| **Small-Medium Effect** | $0.40$ | $50$ seeds | **90 seeds** | Subtle algorithmic differences |

**Conclusion:** The existing five-seed experiment is strictly a **pilot study**. Confirmatory claims of statistical superiority will require expanding to at least **15 to 25 seeds** to maintain power under family-wise multiple testing control.

---

## 5. Revision of Baseline Terminology & Claims

In accordance with Section 3.6 of the audit protocol, baseline terminology has been formally updated:

| Original Description | Revised Defensive Description | Methodological Rationale |
| :--- | :--- | :--- |
| **"Centralized-IDS (Ceiling)"** | **"Centralized IDS Reference"** | Centralized training is a reference architecture with full gradient visibility, not a mathematical upper bound; hyperparameter tuning or regularized federated approaches can occasionally surpass unregularized centralized models. |
| **"Local Silos (Floor)"** | **"Local-Silo Reference"** | Independent uncooperative local models serve as an uncoordinated reference baseline, not a guaranteed floor; in non-IID tabular regimes with few rounds, uncooperative local models can outperform early federated averaging. |
| **"Zero-Degradation Guarantee"** | **"No Measurable Clean-Performance Degradation Observed Across Five Pilot Seeds"** | Empirical observation across five specific seeds on NSL-KDD; does not constitute a mathematical guarantee across arbitrary datasets or hyperparameter configurations. |

---

## 6. Investigation of Coordinate Median Degradation

### 6.1 Per-Seed Trajectory Analysis
In the pilot benchmark, Coordinate Median exhibited severe clean performance degradation (mean accuracy **56.93% $\pm$ 14.47%**, macro F1 **0.4653 $\pm$ 0.2071**). An inspection of per-seed runs reveals dramatic bi-modal behavior:

```
Seed   42 | FedAvg: 78.25% (F1: 0.7818) | Median: 76.81% (F1: 0.7669) [Converged normally]
Seed  101 | FedAvg: 68.43% (F1: 0.6782) | Median: 43.08% (F1: 0.3011) [Total convergence failure]
Seed 2024 | FedAvg: 71.22% (F1: 0.7096) | Median: 64.69% (F1: 0.5939) [Partial convergence]
Seed  777 | FedAvg: 68.87% (F1: 0.6803) | Median: 43.13% (F1: 0.3021) [Total convergence failure]
Seed  999 | FedAvg: 75.72% (F1: 0.7555) | Median: 56.92% (F1: 0.3627) [Severe degradation]
```

In seeds `101` and `777`, Coordinate Median accuracy was exactly **43.08%** and **43.13%**, with macro F1 of **0.3011** and **0.3021**. This matches the trivial majority-class / random-guess floor for the test set, indicating that **training completely stalled**.

### 6.2 Empirical Support for the "Sparse Gradient" Hypothesis
Stage 2E.3 attributed this failure to "sparse gradients on tabular features discarding magnitude signals." 

**Audit Finding:** While this hypothesis is plausible in light of published literature on coordinate-wise aggregators in non-IID settings, **the pilot implementation did not log coordinate-level gradient distributions, sparsity metrics, or coordinate displacement vectors**. 

Therefore, claiming that sparse gradients caused this degradation exceeds the available empirical evidence.

### 6.3 Corrected Qualified Interpretation
In accordance with Section 3.7:

> **"Coordinate Median showed substantial clean-performance degradation under the tested NSL-KDD partitioning and configuration (mean accuracy 56.93% vs 72.50% for FedAvg; complete convergence failure in seeds 101 and 777). The exact causal mechanism behind this degradation has not yet been conclusively isolated."**

---

## 7. Summary of WP1 Methodological Changes

1. **Holm-Bonferroni correction applied:** Confirmed that no candidate model achieves statistically significant separation from FedAvg after FWER control across the 7-model family.
2. **Sampling unit affirmed:** All confidence intervals and hypothesis tests are correctly computed on $n = 5$ seed-level experimental runs ($df = 4$).
3. **Power claims corrected:** Replaced post-hoc "fully powered" claims with a prospective planning table recommending 15 to 25 seeds for confirmatory testing.
4. **Terminology updated:** Updated baseline labels to "Centralized IDS Reference", "Local-Silo Reference", and "No Measurable Clean-Performance Degradation Observed".
5. **Coordinate Median qualified:** Reframed the explanation from an unverified causal claim to a documented empirical observation with unisolated causal mechanisms.
6. **Artifact created:** `data/processed/stage2e/wp1/benchmark_summary_v2.json`.
