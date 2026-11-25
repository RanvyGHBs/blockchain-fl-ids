# Experiments and Frozen Benchmark Results

All completed benchmark outputs and audit reports are permanently frozen and tracked via SHA-256 in [FINAL_RESEARCH_ARTIFACT_CHECKSUM_REGISTRY.md](../reports/FINAL_RESEARCH_ARTIFACT_CHECKSUM_REGISTRY.md) (25/25 artifacts verified). Every figure below comes directly from those frozen JSON files and verified reports.

---

## 1. Common Experimental Configuration (`Track A`)

- **Dataset:** Canonical NSL-KDD (`122` encoded features from `41` raw attributes, binary intrusion classification: Normal `0` vs. Attack `1`).
- **3-Way Split:** `124,973` client training pool + `1,000` isolated trust validation benchmark (`D_val`) + `22,544` held-out test set (`KDDTest+`).
- **Topology & Skew:** $K = 5$ simulated clients partitioned via Non-IID Dirichlet ($\alpha = 0.5$), `IDSNet` (`26,594` trainable parameters).
- **Approved WP2/WP3 Privacy Baseline:** $C = 1.0$, $\sigma = 1.0$, $T = 5$ rounds, $\delta = 10^{-5}$, OS-CSPRNG Box-Muller sampling, discrete RDP $\alpha^* = 3.0 \implies \mathbf{\epsilon = 13.2565}$.

---

## 2. WP1 — Clean Multi-Seed Baselines (No Attack, No DP)

Evaluated across 5 pilot seeds (`[42, 101, 2024, 777, 999]`, $T = 3$ rounds) in [benchmark_summary_v2.json](../data/processed/stage2e/wp1/benchmark_summary_v2.json):

| Model / Aggregator | Mean Accuracy $\pm$ Std | 95% CI ($df=4$) | Mean Macro F1 | Holm-Adjusted $p$ vs FedAvg |
|---|---|---|---:|---:|
| Centralized IDS Reference | $78.77\% \pm 1.64\%$ | `[0.7674, 0.8081]` | `0.7876` | `0.1839` (NS) |
| Local-Silo Reference | $76.81\% \pm 0.64\%$ | `[0.7602, 0.7760]` | `0.7675` | `0.3970` (NS) |
| **Standard FedAvg** | **$72.50\% \pm 4.33\%$** | `[0.6713, 0.7787]` | `0.7211` | Reference |
| **Trust-Weighted FedAvg** | **$72.50\% \pm 4.33\%$** | `[0.6713, 0.7787]` | `0.7211` | `1.0000` (NS) |
| FoolsGold (Standalone) | $67.81\% \pm 10.78\%$ | `[0.5443, 0.8119]` | `0.6588` | `1.0000` (NS) |
| Trimmed Mean ($\beta = 0.2$) | $66.36\% \pm 18.23\%$ | `[0.4372, 0.8900]` | `0.6231` | `1.0000` (NS) |
| Multi-Krum ($f = 1, m = 1$) | $66.02\% \pm 16.18\%$ | `[0.4593, 0.8612]` | `0.5912` | `1.0000` (NS) |
| Coordinate Median | $56.93\% \pm 14.47\%$ | `[0.3896, 0.7490]` | `0.4653` | `0.2084` (NS) |

**Key WP1 Finding:** After Holm-Bonferroni FWER control across the 7 comparisons ($df=4$), **none** of the pairwise accuracy differences against FedAvg reach statistical significance at $\alpha = 0.05$. On clean Non-IID data across all 5 pilot seeds, Trust-Weighted defense produced identical accuracy to standard FedAvg (no clean-performance degradation observed in those 5 seeds).

---

## 3. Stage 2 & Stage 2D — Legacy Non-DP Attack Benchmarks

- **Stage 2 ([stage2_results.json](../data/processed/stage2_results.json), $T=5$, Seed 42, non-DP attacks):**
  - Undefended Sign-Flip collapsed to **43.08%** accuracy (`F1 = 0.2594`), whereas Defended Trust-Weighted FL maintained **74.59%** accuracy (`F1 = 0.7433`), $+31.51\text{ pp}$ advantage, quarantining the attacker (`Node 3`) in Rounds 3–5.
  - Defended Gaussian Noise achieved **70.95%** accuracy (`F1 = 0.6986`, 100% attacker update rejection).
  - Note: Scenario S6 (`56.92%`) used legacy heuristic clipping ($\sigma = 0.01$ without formal RDP accounting).
- **Stage 2D ([multi_attack_benchmarks_v3.json](../data/processed/stage2d/multi_attack_benchmarks_v3.json), $T=3$, 18 matched scenarios, non-DP):**
  - `Gaussian Noise` & `Sign-Flip`: Defended Trust-Weighted recovered from `56.93%` / `56.92%` undefended accuracy to **`78.12%`**, achieving **100.0% MURR** and **0.0% honest FPR**.
  - `Sybil Coalition` (Clients 2 & 3): Defended achieved **100.0% MURR** (`83.78%` acc) vs `0.0%` undefended Median.
  - `Targeted Label-Flip` (non-DP): Reduced Attack Success Rate from `46.75%` to `36.33%` (`33.3% MURR`, `78.22%` acc).
  - `Parameterized Stealth-Constrained Byzantine`: Explicitly evades static norm/cosine geometric margins (`0.0% MURR`) by construction, demonstrating the boundary of static thresholds.

---

## 4. WP2 / WP3 / WP3.1 — Calibrated Trust Under Formal Differential Privacy

Evaluated with $C = 1.0, \sigma = 1.0, T = 5, \delta = 10^{-5}$ ($\epsilon = 13.2565$) across **50 paired multi-seed runs** ([multi_seed_benchmarks.json](../data/processed/wp3/multi_seed_benchmarks.json), [statistical_summary.json](../data/processed/wp3/statistical_summary.json)):

### 4.1 Multi-Seed Honest FPR, Malicious Detection Rate (MDR), and Test Accuracy

| Scenario | Engine Mode | Pooled Honest FPR | Pooled Malicious Detection (MDR) | Mean Test Accuracy $\pm$ Std | Mean Test F1 $\pm$ Std |
|---|---|---:|---:|---:|---:|
| **`clean_dp`** | Uncalibrated | $125/125 = 100.0\%$ | N/A | $47.92\% \pm 6.74\%$ | $0.3180 \pm 0.0804$ |
| **`clean_dp`** | **Calibrated** | **$5/125 = 4.0\%$** | N/A | $48.48\% \pm 6.18\%$ | $0.3931 \pm 0.0913$ |
| **`gaussian_noise`** | Uncalibrated | $100/100 = 100.0\%$ | $25/25 = 100.0\%$ | $47.92\% \pm 6.74\%$ | $0.3180 \pm 0.0804$ |
| **`gaussian_noise`** | **Calibrated** | **$3/100 = 3.0\%$** | **$25/25 = 100.0\%$** | $46.54\% \pm 3.63\%$ | $0.3690 \pm 0.0309$ |
| **`model_scaling`** | Uncalibrated | $88/88 = 100.0\%$ | $22/22 = 100.0\%$ | $47.92\% \pm 6.74\%$ | $0.3180 \pm 0.0804$ |
| **`model_scaling`** | **Calibrated** | **$1/100 = 1.0\%$** | **$22/22 = 100.0\%$** | $50.17\% \pm 16.71\%$ | $0.4411 \pm 0.1929$ |
| **`sign_flip`** | Uncalibrated | $40/40 = 100.0\%$ | $10/10 = 100.0\%$ | $47.91\% \pm 6.74\%$ | $0.3180 \pm 0.0804$ |
| **`sign_flip`** | **Calibrated** | **$3/100 = 3.0\%$** | **$10/10 = 100.0\%$** | $51.85\% \pm 9.15\%$ | $0.4224 \pm 0.0445$ |
| **`label_flip`** | Uncalibrated | $40/40 = 100.0\%$ | $10/10 = 100.0\%$ | $47.91\% \pm 6.74\%$ | $0.3180 \pm 0.0804$ |
| **`label_flip`** | **Calibrated** | **$1/100 = 1.0\%$** | **$3/25 = 12.0\%$** | $57.64\% \pm 14.35\%$ | $0.5370 \pm 0.1725$ |

*(Note: Uncalibrated attack runs quarantine malicious and honest clients by Round 2; denominators match actual submitted rounds before quarantine.)*

### 4.2 Paired Hypothesis Tests ($N = 5$ Seeds, $df = 4$, Holm-Bonferroni $m = 5$)

| Scenario | Metric | Mean Paired Diff (Cal − Uncal) | $t$-stat | Raw $p$ | Holm-Adj $p$ | Cohen's $d_z$ | Significant? |
|---|---|---:|---:|---:|---:|---:|:---:|
| `model_scaling` | **Honest FPR** | **$-0.9900$** | $-99.000$ | $6.24 \times 10^{-8}$ | **$3.12 \times 10^{-7}$** | $-44.274$ | **YES** |
| `label_flip` | **Honest FPR** | **$-0.9900$** | $-99.000$ | $6.24 \times 10^{-8}$ | **$3.12 \times 10^{-7}$** | $-44.274$ | **YES** |
| `gaussian_noise` | **Honest FPR** | **$-0.9700$** | $-79.200$ | $1.52 \times 10^{-7}$ | **$4.57 \times 10^{-7}$** | $-35.419$ | **YES** |
| `sign_flip` | **Honest FPR** | **$-0.9700$** | $-48.500$ | $1.08 \times 10^{-6}$ | **$2.16 \times 10^{-6}$** | $-21.690$ | **YES** |
| `clean_dp` | **Honest FPR** | **$-0.9600$** | $-30.984$ | $6.47 \times 10^{-6}$ | **$6.47 \times 10^{-6}$** | $-13.856$ | **YES** |
| All 5 scenarios | **Test Accuracy** | $-1.38\%$ to $+9.73\%$ | $-0.339$ to $+1.515$ | $0.2045$ to $0.7515$ | **`1.0000`** | $-0.152$ to $+0.677$ | **NO** |

### 4.3 Tier Ablation & Noise Sensitivity (Single-Seed Explorations on Seed 42)
- **Tier Ablation ([ablation_benchmarks.json](../data/processed/wp3/ablation_benchmarks.json)):** Tested on Seed 42 under `gaussian_noise`: `cosine_only` failed detection (`0.0%` MDR), `cosine_loss` detected `66.7%` (`2/3` submissions), while `norm_only`, `loss_only`, `norm_cosine`, `norm_loss`, and `full_three_tier` achieved `100.0%` MDR and `0.0%` honest FPR on Seed 42.
- **Noise Sensitivity ([noise_sensitivity_benchmarks.json](../data/processed/wp3/noise_sensitivity_benchmarks.json)):** Tested on Seed 42 (`clean_dp`) at $\sigma \in \{0.5, 1.0, 1.5\}$: Calibrated FPR was `0.0%` on Seed 42 across all three noise levels vs `100.0%` uncalibrated. *(WP3.1 reconciliation confirmed why Seed 42 yields 0% while 5-seed pooled FPRs are 1–4%: Seed 777 & Seed 101 experienced occasional boundary draws.)*

---

## 5. WP4 — Overhead Profiling & Audit Verification

From [overhead_summary_v2.json](../data/processed/stage2e/wp4/overhead_summary_v2.json) and [serialization_and_negative_control_audit.json](../data/processed/stage2e/wp4/serialization_and_negative_control_audit.json) (CPU microbenchmarks, 100 trials each):

- **Cryptographic Primitives:** ECDSA P-256 Sign = `0.1540 ms`, Verify = `0.1968 ms`, SHA-256 Hash = `0.0072 ms`.
- **Ledger Operations (5 tx block):** Merkle Root = `0.0071 ms`, Forge PoT Block = `0.0146 ms`, Chain Validation = `0.0147 ms`.
- **Aggregators ($d=26,594, K=5$):** FedAvg = `0.124 ms`, Trust-Weighted = `0.226 ms`, Multi-Krum = `0.723 ms`, FoolsGold = `1.155 ms`, Trimmed Mean = `2.658 ms`, Coordinate Median = `2.848 ms`.
- **Serialization & Communication Accounting:**
  - Trainable float32 payload: `26,594 * 4 = 106,376 bytes` + `161 bytes` Pickle container = `106,537 bytes` (`104.04 KiB`).
  - Per-client upstream (`weights + 96B sig + 28B meta`) = `106,661 bytes` (`104.16 KiB` / `106.66 KB`).
  - Per-client downstream (`weights + 42B meta`) = `106,579 bytes` (`104.08 KiB` / `106.58 KB`).
  - Modeled 5-client round bandwidth: **`1,041.21 KiB` (`1,066.20 KB`)** unicast / **`624.89 KiB` (`639.88 KB`)** multicast.
- **Finite Synthetic Tamper Verification:** `500/500` synthetic tampering trials detected across 5 categories; `0/100` false alarms on repeated verifications of the 4-block pristine ledger template.

---

## 6. End-to-End Integration Verification

Executed in [tests/test_end_to_end_pipeline.py](../tests/test_end_to_end_pipeline.py) (`RESEARCH_SIMULATION`, OS-CSPRNG): confirms non-overlapping 3-way splits, client privacy boundary enforcement, tampered ECDSA payload rejection, post-hoc ledger tamper detection, RDP $\epsilon = 13.2565$ at $T=5$, and dynamic telemetry outputs.
