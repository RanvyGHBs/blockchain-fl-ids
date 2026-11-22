# Stage 2E — Comprehensive Experimental Protocol & Metric Formulations
## Privacy-Preserving, Blockchain-Audited Federated Learning for Network Intrusion Detection

**Project:** Blockchain-Assisted Privacy-Preserving Federated Learning for Network Intrusion Detection with Trust-Based Security and Cryptographic Auditing  
**Workspace:** `C:\Users\is043\.gemini\antigravity\scratch\blockchain-fl-ids`  
**Milestone:** Stage 2E (Research Gap Analysis, Architecture Proposal & Experimental Roadmap)  
**Status:** PROPOSED EXPERIMENTAL PROTOCOL (Planning Only — Zero Code Modifications)  
**Date:** November 2026  

---

## 1. Introduction and Protocol Purpose

This document establishes the rigorous experimental protocol for evaluating the federated network intrusion detection system proposed in Stage 2E. It defines the exact datasets, non-IID partitioning schemes, adversarial threat models, mathematical formulations for all primary and secondary evaluation metrics, multi-seed statistical significance testing procedures, differential privacy parameterizations, and empirical overhead profiling methods.

Adherence to this protocol guarantees that all future experimental results generated in Stage 2E are statistically sound, reproducible across random seeds, mathematically auditable, and directly comparable to state-of-the-art literature baselines.

---

## 2. Experimental Environment & Setup

### 2.1 Hardware and Software Environment
- **Operating System:** Microsoft Windows 11 Enterprise (x86_64)
- **Runtime Environment:** Python 3.13.7, PyTorch 2.15.0+cpu, NumPy 2.3.3, Scikit-Learn 1.6.1
- **Execution Target:** CPU deterministic execution (`torch.use_deterministic_algorithms(True)`, `torch.set_num_threads(4)`)
- **Random Number Generators (RNG):** Strict per-scenario and per-round re-seeding across Python `random`, `numpy.random`, `torch.manual_seed`, and `torch.cuda.manual_seed_all` (if available).

### 2.2 Datasets & Feature Engineering
Experiments utilize preprocessed network telemetry from two established benchmark datasets:
1. **UNSW-NB15:**
   - 42 input features (flow features, basic features, content features, time features).
   - Attack categories (Multiclass): Normal, Generic, Exploits, Fuzzers, DoS, Reconnaissance, Analysis, Backdoor, Shellcode, Worms.
   - Standard Scaler normalization fitted strictly on training partitions; categorical encoding via deterministic label mapping.
2. **CIC-IDS2017:**
   - 78 network flow features (packet lengths, inter-arrival times, flag counts, sub-flow statistics).
   - Classes: Benign, DoS/DDoS, PortScan, Botnet, Infiltration, Web Attack, Brute Force.
   - Inf/NaN sanitization, variance threshold filtering, and MinMax scaling.

### 2.3 Non-IID Dirichlet Data Partitioning
To model heterogeneous, decentralized network environments (e.g., enterprise branches, campus networks, IoT edge nodes), training data is partitioned among $N$ simulated clients using a Dirichlet distribution over class proportions:
$$p_{c, i} \sim \text{Dirichlet}(\alpha \cdot \mathbf{1}_{C})$$
where $p_{c, i}$ denotes the proportion of class $c$ allocated to client $i$, and $\alpha$ is the concentration parameter:
- $\alpha = 0.1$: **Extreme Non-IID skew** (severe label imbalance; clients host only 1–2 classes).
- $\alpha = 0.5$: **Moderate Non-IID skew** (default standard benchmark condition).
- $\alpha = 1.0$: **Mild Non-IID skew** (moderate diversity across all participants).
- **Uniform (IID Control):** Stratified uniform sampling across clients.

### 2.4 Multi-Seed Ensemble Configuration
To eliminate single-seed variance, every experimental scenario is evaluated across $S = 5$ independent, standardized random seeds:
$$\mathcal{S} = \{42, 101, 2024, 777, 999\}$$

---

## 3. Mathematical Metric Formulations

### 3.1 Primary Performance Metrics (Model Utility)

Let $C$ denote the set of classes, $N_{\text{val}}$ denote the total validation samples, and $\hat{y}_k, y_k$ represent the predicted and ground-truth labels for sample $k$.

#### 3.1.1 Macro-Averaged Accuracy
$$\text{Accuracy} = \frac{1}{N_{\text{val}}} \sum_{k=1}^{N_{\text{val}}} \mathbb{I}(\hat{y}_k = y_k)$$

#### 3.1.2 Macro-Averaged F1-Score
For each class $c \in C$:
$$\text{Precision}_c = \frac{TP_c}{TP_c + FP_c}, \quad \text{Recall}_c = \frac{TP_c}{TP_c + FN_c}$$
$$\text{F1}_c = \frac{2 \cdot \text{Precision}_c \cdot \text{Recall}_c}{\text{Precision}_c + \text{Recall}_c + \epsilon_{\text{stab}}}$$
$$\text{F1}_{\text{macro}} = \frac{1}{|C|} \sum_{c \in C} \text{F1}_c$$
where $\epsilon_{\text{stab}} = 10^{-8}$ prevents division by zero.

---

### 3.2 Security, Robustness & Adversarial Metrics

#### 3.2.1 Attack Success Rate (ASR)
For targeted adversarial scenarios (e.g., source attack class $y_{\text{src}} \to$ target benign class $y_{\text{tgt}}$):
$$\text{ASR} = \frac{\sum_{k: y_k = y_{\text{src}}} \mathbb{I}(\hat{y}_k = y_{\text{tgt}})}{\sum_{k: y_k = y_{\text{src}}} 1}$$
*Note: Evaluated strictly on the isolated validation split for targeted classes.*

#### 3.2.2 Cumulative Malicious Update Rejection Rate (MURR)
Measures the proportion of submitted malicious parameter updates correctly identified and rejected by the defense layer across all $T$ rounds:
$$\text{MURR} = \begin{cases} \frac{\sum_{t=1}^T |\mathcal{U}_{\text{rejected}}^{\text{mal}}(t)|}{\sum_{t=1}^T |\mathcal{U}_{\text{submitted}}^{\text{mal}}(t)|}, & \text{if } \sum_{t=1}^T |\mathcal{U}_{\text{submitted}}^{\text{mal}}(t)| > 0 \\ \text{N/A}, & \text{if } \sum_{t=1}^T |\mathcal{U}_{\text{submitted}}^{\text{mal}}(t)| = 0 \end{cases}$$

#### 3.2.3 Prevented Update Rate via Quarantine (PURQ)
Quantifies malicious updates prevented from entering the verification pipeline because the client was placed in active quarantine:
$$\text{PURQ} = \frac{\sum_{t=1}^T |\mathcal{U}_{\text{quarantined}}^{\text{mal}}(t)|}{\sum_{t=1}^T \left( |\mathcal{U}_{\text{submitted}}^{\text{mal}}(t)| + |\mathcal{U}_{\text{quarantined}}^{\text{mal}}(t)| \right)}$$

#### 3.2.4 False Positive Rejection Rate (FPR)
Measures the proportion of benign, honest client updates incorrectly rejected by the defense layer (e.g., due to extreme Non-IID skew or differential privacy noise):
$$\text{FPR} = \frac{\sum_{t=1}^T |\mathcal{U}_{\text{rejected}}^{\text{honest}}(t)|}{\sum_{t=1}^T |\mathcal{U}_{\text{submitted}}^{\text{honest}}(t)|}$$

---

### 3.3 Statistical Aggregation and Significance Testing

For any metric $M \in \{\text{Accuracy}, \text{F1}_{\text{macro}}, \text{ASR}, \text{MURR}, \text{FPR}\}$ evaluated across $S = 5$ random seeds:

#### 3.3.1 Sample Mean ($\mu$) and Sample Standard Deviation ($\sigma$)
$$\bar{M} = \frac{1}{S} \sum_{s=1}^S M_s, \quad s_M = \sqrt{\frac{1}{S-1} \sum_{s=1}^S (M_s - \bar{M})^2}$$

#### 3.3.2 95% Confidence Interval (Student's $t$-Distribution)
$$\text{CI}_{0.95} = \left[ \bar{M} - t_{S-1, 0.975} \cdot \frac{s_M}{\sqrt{S}}, \quad \bar{M} + t_{S-1, 0.975} \cdot \frac{s_M}{\sqrt{S}} \right]$$
For $S = 5$ seeds, degrees of freedom $\nu = 4$, critical value $t_{4, 0.975} = 2.776$.

#### 3.3.3 Paired Welch's $t$-Test
When comparing our proposed defense against a baseline (e.g., Proposed Trust-Weighted FedAvg vs FoolsGold across identical seeds $s \in \mathcal{S}$):
$$t = \frac{\bar{M}_1 - \bar{M}_2}{\sqrt{\frac{s_1^2}{S_1} + \frac{s_2^2}{S_2}}}$$
with Welch-Satterthwaite degrees of freedom:
$$\nu \approx \frac{\left( \frac{s_1^2}{S_1} + \frac{s_2^2}{S_2} \right)^2}{\frac{(s_1^2 / S_1)^2}{S_1 - 1} + \frac{(s_2^2 / S_2)^2}{S_2 - 1}}$$
Null Hypothesis $H_0: \mu_1 = \mu_2$; Alternative Hypothesis $H_1: \mu_1 \neq \mu_2$. Differences are statistically significant at $p < 0.05$.

#### 3.3.4 Wilcoxon Signed-Rank Test (Non-Parametric)
For differences $d_s = M_{1, s} - M_{2, s}$:
1. Exclude pairs where $d_s = 0$.
2. Rank absolute differences $|d_s|$ from smallest to largest with average ranks assigned to ties.
3. Compute test statistic:
   $$W = \min(W^+, W^-), \quad W^+ = \sum_{d_s > 0} \text{Rank}(|d_s|), \quad W^- = \sum_{d_s < 0} \text{Rank}(|d_s|)$$

---

### 3.4 Formal Differential Privacy Accounting

#### 3.4.1 Client-Level $L_2$-Sensitivity and Gradient Clipping
For client update $\Delta w_i = w_i^{(t)} - w^{(t-1)}$:
$$\Delta \tilde{w}_i = \frac{\Delta w_i}{\max\left(1, \frac{\|\Delta w_i\|_2}{C}\right)}$$
where $C$ is the clipping threshold, guaranteeing $L_2$ global sensitivity $\Delta_2 = C$.

#### 3.4.2 Calibrated Gaussian Perturbation
$$\Delta \hat{w}_i = \Delta \tilde{w}_i + \mathcal{N}\left(0, \sigma_{\text{DP}}^2 C^2 \mathbf{I}_d\right)$$
where $\sigma_{\text{DP}}$ is the noise multiplier and $d$ is parameter dimensionality.

#### 3.4.3 Rényi Differential Privacy (RDP) Composition
For Rényi order $\alpha > 1$, the Gaussian mechanism satisfies $(\alpha, \epsilon_{\text{RDP}}(\alpha))$-RDP with:
$$\epsilon_{\text{RDP}}(\alpha) = \frac{\alpha C^2}{2 \sigma_{\text{DP}}^2 C^2} = \frac{\alpha}{2 \sigma_{\text{DP}}^2}$$
Under sequential composition over $T$ federated rounds:
$$\epsilon_{\text{total}}(\alpha) = \sum_{t=1}^T \epsilon_{\text{RDP}}^{(t)}(\alpha) = \frac{T \alpha}{2 \sigma_{\text{DP}}^2}$$

#### 3.4.4 Conversion to Canonical $(\epsilon, \delta)$-Differential Privacy
By Mironov (CSF 2017), $(\alpha, \epsilon_{\text{total}}(\alpha))$-RDP converts to standard $(\epsilon, \delta)$-DP for any target $\delta \in (0, 1)$ via:
$$\epsilon(\delta) = \min_{\alpha > 1} \left\{ \epsilon_{\text{total}}(\alpha) + \frac{\ln(1/\delta)}{\alpha - 1} \right\} = \min_{\alpha > 1} \left\{ \frac{T \alpha}{2 \sigma_{\text{DP}}^2} + \frac{\ln(1/\delta)}{\alpha - 1} \right\}$$
Analytical minimization yields the optimal Rényi order $\alpha^*$:
$$\frac{d}{d\alpha} \left[ \frac{T \alpha}{2 \sigma_{\text{DP}}^2} + \frac{\ln(1/\delta)}{\alpha - 1} \right] = \frac{T}{2 \sigma_{\text{DP}}^2} - \frac{\ln(1/\delta)}{(\alpha - 1)^2} = 0$$
$$\alpha^* = 1 + \sqrt{\frac{2 \sigma_{\text{DP}}^2 \ln(1/\delta)}{T}}$$
Substituting $\alpha^*$ back into the conversion yields the closed-form privacy bound:
$$\epsilon^*(\delta) = \frac{T}{2 \sigma_{\text{DP}}^2} + \sqrt{\frac{2 T \ln(1/\delta)}{\sigma_{\text{DP}}^2}}$$

#### 3.4.5 Noise-Tolerance Calibration for Multi-Criteria Trust Engine
To prevent formal DP noise from triggering false-positive rejection of honest clients ($\text{FPR} \gg 0$), the Multi-Criteria Trust Engine adjusts its acceptance thresholds as a function of $\sigma_{\text{DP}}$:
$$\tau_{\text{cosine}}(\sigma_{\text{DP}}) = \tau_{\text{base}} - \kappa_1 \cdot \sigma_{\text{DP}} \cdot \frac{C}{\sqrt{d}}$$
$$\tau_{\text{loss}}(\sigma_{\text{DP}}) = \tau_{\text{loss, base}} + \kappa_2 \cdot \sigma_{\text{DP}}^2$$
where $\kappa_1 = 0.5, \kappa_2 = 1.0$ are empirical calibration coefficients.

---

### 3.5 Computational and Communication Overhead Profiling

#### 3.5.1 Communication Bandwidth Metrics
- **Upstream Client Payload per Round ($B_{\text{up}}^{(i)}$):**
  $$B_{\text{up}}^{(i)} = \text{Bytes}(\text{weights}) + \text{Bytes}(\text{ECDSA\_sig}) + \text{Bytes}(\text{client\_meta})$$
- **Downstream Server Payload per Round ($B_{\text{down}}$):**
  $$B_{\text{down}} = \text{Bytes}(\text{global\_weights}) + \text{Bytes}(\text{reputations}) + \text{Bytes}(\text{quarantine\_list})$$
- **Total Network Footprint per Round ($B_{\text{round}}$):**
  $$B_{\text{round}} = B_{\text{down}} \cdot N_{\text{clients}} + \sum_{i=1}^{N_{\text{active}}} B_{\text{up}}^{(i)}$$
- **Ledger Storage Growth per Round ($B_{\text{ledger}}$):**
  $$B_{\text{ledger}} = \text{sizeof}(\text{BlockHeader}) + \sum_{i=1}^{N_{\text{tx}}} \text{sizeof}(\text{TransactionRecord})$$

#### 3.5.2 Computation Latency Metrics (Milliseconds)
Measured via high-precision `time.perf_counter_ns()`:
1. $T_{\text{sign}}$: Client-side ECDSA P-256 signature generation time.
2. $T_{\text{verify\_batch}}$: Server-side ECDSA signature verification for all active clients.
3. $T_{\text{merkle}}$: Merkle tree leaf hashing and root synthesis.
4. $T_{\text{trust}}$: Multi-criteria trust score calculation (cosine, performance, loss delta).
5. $T_{\text{reputation}}$: Beta distribution update and quarantine rule evaluation.
6. $T_{\text{aggregate}}$: Global model aggregation execution.
7. $T_{\text{block\_commit}}$: Audit ledger block serialization, SHA-256 hashing, and disk write.

---

### 3.6 Cryptographic Ledger Tamper-Evidence Metrics

#### 3.6.1 Tamper Detection Probability ($P_D$)
$$P_D = \frac{\sum_{m=1}^{M_{\text{tamper}}} \mathbb{I}(\text{AuditVerifier.verify\_chain}(\mathcal{L}_m) = \text{False})}{M_{\text{tamper}}}$$
Target: $P_D = 1.000$ (100.0% deterministic detection of all injected tampering events).

#### 3.6.2 False Alarm Probability ($P_{\text{FA}}$)
$$P_{\text{FA}} = \frac{\sum_{k=1}^{K_{\text{honest}}} \mathbb{I}(\text{AuditVerifier.verify\_chain}(\mathcal{L}_k) = \text{False})}{K_{\text{honest}}}$$
Target: $P_{\text{FA}} = 0.000$ (0.0% false alarms on untampered legitimate chains).

#### 3.6.3 Audit Verification Latency ($T_{\text{audit}}$)
Total wall-clock time required to verify an audit ledger of $T$ blocks containing $T \times N$ client transactions.

---

## 4. Comprehensive Experimental Scenario Matrix

The experimental matrix comprises four structured evaluation groups totaling 24 rigorous scenarios, designed to provide comprehensive empirical evidence for scholarly publication.

### Group 1: Baseline Architecture Comparison (Clean Environment, No Adversaries)
*Objective:* Quantify performance bounds and prove collaboration gain under Non-IID skew ($\alpha = 0.5$).

| ID | Model / Architecture | Aggregation / Mechanism | Defense Active | Expected Acc (%) | Expected F1 (%) | Purpose |
|:---|:---|:---|:---:|:---:|:---:|:---|
| **B1** | Centralized-IDS | Unified Global SGD | N/A | $\sim 82.0 - 86.0$ | $\sim 0.78 - 0.82$ | Empirical Upper Bound |
| **B2** | Local Silos | Isolated Client SGD | None | $\sim 68.0 - 72.0$ | $\sim 0.60 - 0.66$ | Uncooperative Lower Bound |
| **B3** | Standard FedAvg | Classic McMahan FedAvg | None | $\sim 78.0 - 81.0$ | $\sim 0.72 - 0.76$ | Baseline Standard FL |
| **B4** | Multi-Krum | Blanchard et al. (2017) | Geometric Krum | $\sim 77.0 - 80.0$ | $\sim 0.71 - 0.75$ | Baseline Byzantine Defense |
| **B5** | FoolsGold | Fung et al. (2020) | Historical Cosine | $\sim 77.5 - 80.5$ | $\sim 0.71 - 0.75$ | Baseline Sybil Defense |
| **B6** | Proposed System | Trust-Weighted FedAvg | Multi-Criteria | $\sim 78.5 - 81.5$ | $\sim 0.73 - 0.77$ | Proposed Framework Baseline |

---

### Group 2: Defense Robustness Benchmark Across Adversarial Attacks
*Objective:* Comparative evaluation of defenses under 20% malicious clients ($N_{\text{mal}} = 2, N_{\text{honest}} = 8$).

| ID | Attack Vector | Attack Configuration | Defenses Compared | Target Evaluation Metrics |
|:---|:---|:---|:---|:---|
| **R1** | Targeted Label-Flip | Exploits $\to$ Normal ($2 \to 0$) | FedAvg vs Krum vs FoolsGold vs Proposed | Accuracy, F1, ASR, MURR, FPR |
| **R2** | Untargeted Noise | Gaussian $\mu=0, \sigma=2.0$ | FedAvg vs Krum vs FoolsGold vs Proposed | Accuracy, F1, MURR, FPR |
| **R3** | Scaled Sign-Flip | Multiplier $\lambda = -3.0$ | FedAvg vs Krum vs FoolsGold vs Proposed | Accuracy, F1, MURR, FPR |
| **R4** | Intermittent Sneak | Rounds 1, 3: Attack; Round 2: Honest | FedAvg vs Krum vs FoolsGold vs Proposed | Accuracy, F1, ASR, MURR, FPR |
| **R5** | Sybil Attack | 4 Coordinated Clones ($N=12$) | FedAvg vs Krum vs FoolsGold vs Proposed | Accuracy, F1, ASR, MURR, FPR |
| **R6** | Free-Rider Attack | Replay Old Global Weights | FedAvg vs Krum vs FoolsGold vs Proposed | Accuracy, Fairness, MURR |

---

### Group 3: Formal Differential Privacy Tradeoff Sweep
*Objective:* Measure utility degradation and defense stability across privacy budgets $(\epsilon, \delta = 10^{-5})$.

| ID | Noise Multiplier $\sigma_{\text{DP}}$ | Clipping Norm $C$ | Computed $\epsilon$ (RDP) | Calibrated Trust Engine | Primary Metrics |
|:---|:---:|:---:|:---:|:---:|:---|
| **P1** | 0.00 (No DP) | $\infty$ | $\infty$ | Disabled | Acc, F1, FPR, ASR (Baseline) |
| **P2** | 0.05 (Weak DP) | 1.0 | $\sim 18.4$ | Active | Acc, F1, FPR, ASR |
| **P3** | 0.10 (Moderate DP) | 1.0 | $\sim 9.6$ | Active | Acc, F1, FPR, ASR |
| **P4** | 0.20 (Standard DP) | 1.0 | $\sim 4.9$ | Active | Acc, F1, FPR, ASR |
| **P5** | 0.50 (Strict DP) | 1.0 | $\sim 2.1$ | Active | Acc, F1, FPR, ASR |
| **P6** | 0.20 (Uncalibrated) | 1.0 | $\sim 4.9$ | **Uncalibrated (Ablation)** | Acc, F1, **FPR (Expect Spike)** |

---

### Group 4: Non-IID Dirichlet Sensitivity Ablation
*Objective:* Assess robustness of trust scoring across data distribution skews.

| ID | Dirichlet Parameter $\alpha$ | Data Heterogeneity Level | Defense Configuration | Primary Metrics |
|:---:|:---:|:---|:---|:---|
| **D1** | $\infty$ (Uniform) | IID (Synthetic Control) | Proposed Trust-Weighted FedAvg | Acc, F1, FPR, MURR |
| **D2** | 1.0 | Mild Non-IID | Proposed Trust-Weighted FedAvg | Acc, F1, FPR, MURR |
| **D3** | 0.5 | Moderate Non-IID (Standard) | Proposed Trust-Weighted FedAvg | Acc, F1, FPR, MURR |
| **D4** | 0.1 | Extreme Non-IID | Proposed Trust-Weighted FedAvg | Acc, F1, FPR, MURR |

---

## 5. Statistical Execution & Reporting Standards

1. **Deterministic Run Invariance:** Each seed $s \in \mathcal{S}$ must produce identical results when executed independently.
2. **Reporting Format:** All benchmark outputs will report values as $\bar{M} \pm s_M$ (e.g., $80.24\% \pm 0.45\%$) alongside 95% Confidence Intervals.
3. **Artifact Integrity:** All raw multi-seed runs will be persisted to `data/processed/stage2e/multi_seed_benchmarks.json` with an accompanying cryptographic SHA-256 checksum.
