# Stage 2E.1 — Comprehensive Experimental Protocol & Metric Formulations
## Privacy-Aware Trust Calibration for Blockchain-Audited Federated Network Intrusion Detection

**Project:** Blockchain-Assisted Privacy-Preserving Federated Learning for Network Intrusion Detection with Trust-Based Security and Cryptographic Auditing  
**Workspace:** `C:\Users\is043\.gemini\antigravity\scratch\blockchain-fl-ids`  
**Milestone:** Stage 2E.1 (Methodological Corrections & Planning Package Revision)  
**Status:** REVISED EXPERIMENTAL PROTOCOL (Planning Only — Zero Code Modifications)  
**Date:** November 2026  

---

## 1. Experimental Environment & Setup

### 1.1 Hardware and Software Environment
- **Operating System:** Microsoft Windows 11 Enterprise (x86_64)
- **Runtime Environment:** Python 3.13.7, PyTorch 2.15.0+cpu, NumPy 2.3.3, Scikit-Learn 1.6.1
- **Execution Target:** Deterministic CPU execution (`torch.use_deterministic_algorithms(True)`, `torch.set_num_threads(4)`)
- **Random Number Generators (RNG):** Strict per-scenario and per-round re-seeding across Python `random`, `numpy.random`, `torch.manual_seed`, and `torch.cuda.manual_seed_all` (if available), following the Stage 2D.4 determinism discipline.

### 1.2 Primary Dataset: NSL-KDD
All core experimental evaluations are conducted strictly on **NSL-KDD** to ensure benchmark continuity, manageable computational overhead, and rigorous comparison against Stage 2D baselines.
- **Input Dimension:** 122 preprocessed numerical and one-hot encoded features.
- **Classification Tasks:**
  - Binary classification: Normal (0) vs Attack (1).
  - Multiclass classification: Normal, DoS, Probe, R2L, U2R.
- **Isolation Protocol:** Five-stage strict data isolation protocol:
  1. `Raw Split`: Partitioned into Development Data (`KDDTrain+.txt`) and Held-Out Test Data (`KDDTest+.txt`).
  2. `Development Split`: Development data partitioned into Client-Training Pool ($N$ client partitions) and Server Trust-Validation Slice (balanced benchmark).
  3. `Preprocessor Fitting`: `StandardScaler` and categorical encoders fitted **exclusively** on the Client-Training Pool.
  4. `Transform Only`: Server Trust-Validation slice and Held-Out Test set are transformed using the pre-fitted transformer objects; they never participate in fitting.
  5. `Evaluation Isolation`: Held-Out Test set is evaluated strictly once per round to assess global model generalization. It is never used for training, trust evaluation, threshold calibration, or hyperparameter selection.
- *Optional Future Datasets:* UNSW-NB15 and CIC-IDS2017 are classified as `[Optional Future Extension]`. Their inclusion is deferred until separate preprocessors and baseline benchmarks are formally validated.

### 1.3 Non-IID Dirichlet Partitioning
Data heterogeneity among the $N=5$ clients (and scaled cohorts) is controlled via a Dirichlet distribution over class proportions:
$$\mathbf{p}_{c} \sim \text{Dirichlet}(\alpha \cdot \mathbf{1}_N)$$
- $\alpha = 0.5$: Moderate Non-IID skew (standard benchmark condition).
- $\alpha = 0.1$: Extreme Non-IID skew (stress-test condition).
- $\alpha = 1.0$: Mild Non-IID skew.
- IID Uniform Control: Stratified random sampling across clients.

### 1.4 Statistical Multi-Seed Pilot Ensemble
To quantify variability without assuming statistical finality:
- **Pilot Ensemble Size:** $S = 5$ independent standardized seeds:
  $$\mathcal{S}_{\text{pilot}} = \{42, 101, 2024, 777, 999\}$$
- **Power Analysis Requirement:** If standard deviations across the pilot ensemble result in overlapping confidence intervals between proposed defenses and baselines, a statistical power analysis will determine whether expanding to $S = 10$ seeds is necessary for definitive publication claims.

---

## 2. Mathematical Formulations for All Metrics

### 2.1 Model Utility Metrics

Let $N_{\text{eval}}$ denote the number of samples in the evaluation set, with ground truth labels $y_k$ and predicted labels $\hat{y}_k \in \{0, 1, \dots, C-1\}$.

#### 2.1.1 Macro-Averaged Accuracy
$$\text{Accuracy} = \frac{1}{N_{\text{eval}}} \sum_{k=1}^{N_{\text{eval}}} \mathbb{I}(\hat{y}_k = y_k)$$

#### 2.1.2 Macro-Averaged F1-Score
For each class $c \in \{0, \dots, C-1\}$:
$$\text{Precision}_c = \frac{TP_c}{TP_c + FP_c + \epsilon}, \quad \text{Recall}_c = \frac{TP_c}{TP_c + FN_c + \epsilon}$$
$$\text{F1}_c = \frac{2 \cdot \text{Precision}_c \cdot \text{Recall}_c}{\text{Precision}_c + \text{Recall}_c + \epsilon}$$
$$\text{F1}_{\text{macro}} = \frac{1}{C} \sum_{c=0}^{C-1} \text{F1}_c$$
where $\epsilon = 10^{-8}$ prevents division by zero.

---

### 2.2 Adversarial Robustness & Defense Metrics

In compliance with the Stage 2D.4 cumulative disposition accounting:

#### 2.2.1 Attack Success Rate (ASR)
Evaluated strictly for targeted attacks (e.g., source class $y_{\text{src}} \to$ target class $y_{\text{tgt}}$) on the isolated test set:
$$\text{ASR} = \frac{\sum_{k: y_k = y_{\text{src}}} \mathbb{I}(\hat{y}_k = y_{\text{tgt}})}{\sum_{k: y_k = y_{\text{src}}} 1}$$

#### 2.2.2 Cumulative Malicious Update Rejection Rate (MURR)
Measures the proportion of submitted malicious updates successfully rejected by trust verification across all $T$ rounds:
$$\text{MURR} = \begin{cases} 
\frac{\sum_{t=1}^T |\mathcal{U}_{\text{rejected}}^{\text{mal}}(t)|}{\sum_{t=1}^T |\mathcal{U}_{\text{submitted}}^{\text{mal}}(t)|}, & \text{if } \sum_{t=1}^T |\mathcal{U}_{\text{submitted}}^{\text{mal}}(t)| > 0 \\ 
\text{None (N/A)}, & \text{if } \sum_{t=1}^T |\mathcal{U}_{\text{submitted}}^{\text{mal}}(t)| = 0 
\end{cases}$$
*Methodological Rule:* Never report 100% when no malicious updates were submitted. Report `None` or `N/A`.

#### 2.2.3 Prevented Update Rate via Quarantine (PURQ)
Measures malicious update attempts prevented from being submitted because the client was in active quarantine:
$$\text{PURQ} = \frac{\sum_{t=1}^T |\mathcal{U}_{\text{quarantined}}^{\text{mal}}(t)|}{\sum_{t=1}^T \left( |\mathcal{U}_{\text{submitted}}^{\text{mal}}(t)| + |\mathcal{U}_{\text{quarantined}}^{\text{mal}}(t)| \right)}$$

#### 2.2.4 False Positive Rejection Rate (FPR)
Measures the proportion of submitted honest updates incorrectly rejected by the trust engine:
$$\text{FPR} = \begin{cases} 
\frac{\sum_{t=1}^T |\mathcal{U}_{\text{rejected}}^{\text{honest}}(t)|}{\sum_{t=1}^T |\mathcal{U}_{\text{submitted}}^{\text{honest}}(t)|}, & \text{if } \sum_{t=1}^T |\mathcal{U}_{\text{submitted}}^{\text{honest}}(t)| > 0 \\ 
\text{None (N/A)}, & \text{if } \sum_{t=1}^T |\mathcal{U}_{\text{submitted}}^{\text{honest}}(t)| = 0 
\end{cases}$$

---

### 2.3 Statistical Aggregation & Hypothesis Testing

For any metric $M$ evaluated across the $S = 5$ pilot seeds $\mathcal{S}_{\text{pilot}}$:

#### 2.3.1 Sample Mean and Sample Standard Deviation
$$\bar{M} = \frac{1}{S} \sum_{s=1}^S M_s, \quad s_M = \sqrt{\frac{1}{S-1} \sum_{s=1}^S (M_s - \bar{M})^2}$$

#### 2.3.2 95% Confidence Interval (Student's $t$-Distribution)
$$\text{CI}_{0.95} = \left[ \bar{M} - t_{S-1, 0.975} \cdot \frac{s_M}{\sqrt{S}}, \quad \bar{M} + t_{S-1, 0.975} \cdot \frac{s_M}{\sqrt{S}} \right]$$
For $S = 5$ seeds, degrees of freedom $\nu = 4$, critical value $t_{4, 0.975} \approx 2.776$.

#### 2.3.3 Matched-Pairs Testing: Paired $t$-Test
When comparing two defenses evaluated on **matched experiments** (identical seeds $s$, initial weights, and partitions):
1. Compute pairwise differences: $d_s = M_{1, s} - M_{2, s}$.
2. Mean difference $\bar{d} = \frac{1}{S} \sum d_s$ and standard deviation $s_d = \sqrt{\frac{1}{S-1} \sum (d_s - \bar{d})^2}$.
3. Test statistic:
   $$t = \frac{\bar{d}}{s_d / \sqrt{S}}, \quad \text{df} = S - 1$$
4. **Effect Size (Cohen's $d_z$ for paired samples):**
   $$d_z = \frac{\bar{d}}{s_d}$$
   Interpretation: $|d_z| \ge 0.8$ indicates a large effect.

#### 2.3.4 Non-Parametric Matched Testing: Wilcoxon Signed-Rank Test
Mandatory alternative when normality of differences cannot be verified or when sample size is small ($S=5$):
1. Compute differences $d_s = M_{1, s} - M_{2, s}$, exclude pairs with $d_s = 0$.
2. Rank absolute differences $|d_s|$ in ascending order.
3. Compute sum of positive ranks $W^+$ and negative ranks $W^-$:
   $$W = \min(W^+, W^-)$$
4. Report exact two-tailed $p$-value from the Wilcoxon distribution table for $n = 5$.

#### 2.3.5 Independent Groups Testing: Welch's $t$-Test
Employed only when comparing independent, unmatched groups with potentially unequal variances:
$$t = \frac{\bar{M}_1 - \bar{M}_2}{\sqrt{\frac{s_1^2}{S_1} + \frac{s_2^2}{S_2}}}, \quad \nu \approx \frac{\left( \frac{s_1^2}{S_1} + \frac{s_2^2}{S_2} \right)^2}{\frac{(s_1^2 / S_1)^2}{S_1 - 1} + \frac{(s_2^2 / S_2)^2}{S_2 - 1}}$$

*Methodological Rule:* Never use the phrase "Paired Welch's t-test". Use Paired $t$-test for matched runs; use Welch's $t$-test for independent groups.

---

### 2.4 Formal Privacy Mechanism Formulations `[Requires Theoretical Validation]`

#### 2.4.1 Adjacency Relations
- **Example-Level Adjacency:** Two local datasets $D, D'$ are adjacent if $|D \oplus D'| = 1$. The sensitivity $C$ bounds the impact of any single network flow record.
- **Client-Level Adjacency:** Two global datasets $\mathcal{D}, \mathcal{D}'$ are adjacent if they differ by an entire client's dataset. The sensitivity bounds the impact of any single client.

#### 2.4.2 Update Clipping on $\Delta \mathbf{w}_i$ `[Proposed for Stage 2E]`
Clipping operates independently at each client on the parameter update delta $\Delta \mathbf{w}_i^{(t)} = \mathbf{w}_i^{(t)} - \mathbf{w}_{\text{global}}^{(t-1)}$:
$$\Delta \mathbf{w}_{i, \text{clipped}}^{(t)} = \Delta \mathbf{w}_i^{(t)} \times \min\left(1, \frac{C}{\|\Delta \mathbf{w}_i^{(t)}\|_2}\right)$$
guaranteeing $L_2$-sensitivity $\|\Delta \mathbf{w}_{i, \text{clipped}}^{(t)}\|_2 \le C$.

#### 2.4.3 Gaussian Perturbation
$$\Delta \mathbf{w}_{i, \text{private}}^{(t)} = \Delta \mathbf{w}_{i, \text{clipped}}^{(t)} + \mathcal{N}\left(0, \sigma^2 C^2 \mathbf{I}_d\right)$$
where $C$ is the clipping norm threshold, $\sigma$ is the noise multiplier, and $d$ is parameter dimension.

#### 2.4.4 Rényi Differential Privacy (RDP) Composition `[Requires Theoretical Validation]`
For Rényi order $\alpha > 1$, the Gaussian mechanism provides RDP guarantee:
$$\epsilon_{\text{RDP}}(\alpha) = \frac{\alpha}{2 \sigma^2}$$
Over $T$ sequentially composed rounds:
$$\epsilon_{\text{total}}(\alpha) = \sum_{t=1}^T \frac{\alpha}{2 \sigma_t^2} = \frac{T \alpha}{2 \sigma^2}$$
Converted to $(\epsilon, \delta)$-DP for specified $\delta = 10^{-5}$:
$$\epsilon^*(\delta) = \min_{\alpha > 1} \left\{ \frac{T \alpha}{2 \sigma^2} + \frac{\ln(1/\delta)}{\alpha - 1} \right\} = \frac{T}{2 \sigma^2} + \sqrt{\frac{2 T \ln(1/\delta)}{\sigma^2}}$$
*Pre-condition:* Formal privacy claims are prohibited until sampling assumptions, adjacency definition, and accountant implementation are unit-tested and verified.

---

### 2.5 Privacy-Aware Trust Calibration Methodology `[Requires Experimental Validation]`

The protocol investigates three calibration models against the uncalibrated baseline:

1. **Model 0: Uncalibrated Baseline (Stage 2D frozen):**
   $$\tau_{\text{cosine}} = 0.15, \quad \tau_{\text{loss}} = 1.5$$
2. **Model 1: Empirically Estimated Calibration Thresholds:**
   Derived from Monte Carlo profiling of honest client updates under noise multiplier $\sigma$:
   $$\tau_{\text{cosine}}^{\text{emp}}(\sigma) = Q_{0.01}(\cos(\Delta \mathbf{w}_{\text{honest}}, \Delta \mathbf{w}_{\text{median}}))$$
   $$\tau_{\text{loss}}^{\text{emp}}(\sigma) = Q_{0.99}\left(\frac{\mathcal{L}_{\text{cand}} - \mathcal{L}_{\text{base}}}{\max(0.01, \mathcal{L}_{\text{base}})}\right)$$
3. **Model 2: Theoretically Derived Linear Bound `[Requires Theoretical Validation]`:**
   $$\tau_{\text{cosine}}^{\text{theo}}(\sigma) = 0.15 - \kappa_1 \cdot \sigma \cdot \frac{C}{\sqrt{d}}$$
   $$\tau_{\text{loss}}^{\text{theo}}(\sigma) = 1.5 + \kappa_2 \cdot \sigma^2$$

---

### 2.6 Computational & Communication Overhead Metrics `[Proposed for Stage 2E]`

#### 2.6.1 Bandwidth Profiling (Bytes)
- **Upstream Payload per Client per Round ($B_{\text{up}}^{(i)}$):**
  $$B_{\text{up}}^{(i)} = \text{len}(\text{pickle}(\Delta \mathbf{w}_i)) + \text{len}(\text{sig}_{\text{ECDSA}}) + \text{len}(\text{metadata})$$
- **Downstream Payload per Round ($B_{\text{down}}$):**
  $$B_{\text{down}} = \text{len}(\text{pickle}(\mathbf{w}_{\text{global}})) + \text{len}(\mathbf{R}) + \text{len}(\mathcal{Q})$$
- **Total Round Network Footprint ($B_{\text{round}}$):**
  $$B_{\text{round}} = N \cdot B_{\text{down}} + \sum_{i \in \text{Active}} B_{\text{up}}^{(i)}$$

#### 2.6.2 Computation Latency Profiling (Milliseconds)
Measured via high-precision `time.perf_counter_ns()`:
- $T_{\text{sign}}$: Client-side ECDSA P-256 signing time.
- $T_{\text{verify\_batch}}$: Server-side ECDSA signature batch verification.
- $T_{\text{trust}}$: `MultiCriteriaTrustEngine` execution time.
- $T_{\text{reputation}}$: `ReputationManager` update and quarantine logic.
- $T_{\text{aggregate}}$: Aggregation algorithm computation time.
- $T_{\text{ledger\_commit}}$: Block serialization, SHA-256 header hashing, and Merkle tree generation.
- $T_{\text{audit\_verify}}$: Post-training full-chain audit verification.

---

### 2.7 Finite Tamper-Evidence Verification Metrics `[Proposed for Stage 2E]`

Evaluated across an explicit finite suite of $K=5$ synthetic tamper injection scenarios ($N=100$ trials each):
1. `tamper_payload`: Corrupt transaction data / model hash in Block $t \in [1, T-1]$.
2. `delete_block`: Remove Block $t$ from the chain.
3. `reorder_blocks`: Transpose Block $t$ and Block $t+1$.
4. `corrupt_hash_chain`: Overwrite `prev_hash` of Block $t+1$.
5. `corrupt_merkle_root`: Alter the Merkle root in Block $t$ header.

- **Detection Probability on Finite Test Suite ($P_D$):**
  $$P_D = \frac{\sum_{k=1}^K \sum_{i=1}^{100} \mathbb{I}(\text{AuditVerifier.verify}(\mathcal{L}_{k, i}) = \text{False})}{K \times 100}$$
- **False Alarm Probability on Pristine Chains ($P_{\text{FA}}$):**
  $$P_{\text{FA}} = \frac{\sum_{j=1}^{100} \mathbb{I}(\text{AuditVerifier.verify}(\mathcal{L}_{\text{pristine}, j}) = \text{False})}{100}$$

---

## 3. Comprehensive Experimental Scenario Matrix

### Group 1: Multi-Seed Baseline Architecture Comparison (Clean Environment)
*Evaluated across all 5 pilot seeds on NSL-KDD under Non-IID Dirichlet $\alpha = 0.5$.*

| ID | Model / Baseline | Aggregator | Byzantine Condition | Primary Evaluation Metrics |
|:---|:---|:---|:---|:---|
| **B1** | Centralized-IDS | Global SGD | N/A (Upper Bound) | Accuracy, F1, Loss |
| **B2** | Local Silos | Isolated Client SGD | None (Lower Bound) | Accuracy, F1, Variance across clients |
| **B3** | Standard FedAvg | Classic FedAvg | None | Accuracy, F1, Convergence rounds |
| **B4** | Multi-Krum | Multi-Krum | $n=5, f=1$ ($n \ge 2f + 3$ holds) | Accuracy, F1, Selection stability |
| **B5** | FoolsGold | FoolsGold Standalone | Sybil Mitigation | Accuracy, F1, Client weight entropy |
| **B6** | Proposed Core | Trust-Weighted FedAvg | Multi-Criteria Engine | Accuracy, F1, Reputation trajectory |

---

### Group 2: Privacy Noise Sensitivity & Trust Calibration Sweep
*Clean environment (no adversaries), testing honest client false positives under noise.*

| ID | Noise Multiplier $\sigma$ | Clipping Bound $C$ | Trust Engine Configuration | Primary Evaluation Metrics |
|:---|:---:|:---:|:---|:---|
| **C1** | 0.00 (No noise) | $\infty$ | Uncalibrated ($\tau_{\text{cos}}=0.15, \tau_{\text{loss}}=1.5$) | Accuracy, F1, FPR (Expect FPR = 0%) |
| **C2** | 0.05 (Low noise) | 1.0 | Uncalibrated | Accuracy, F1, FPR, Mean Cosine Sim |
| **C3** | 0.10 (Moderate) | 1.0 | Uncalibrated | Accuracy, F1, FPR, Mean Cosine Sim |
| **C4** | 0.20 (Standard) | 1.0 | Uncalibrated (Expect FPR spike) | Accuracy, F1, FPR, Quarantine Count |
| **C5** | 0.50 (High noise) | 1.0 | Uncalibrated (Severe FPR) | Accuracy, F1, FPR, Quarantine Count |
| **C6** | 0.20 (Standard) | 1.0 | **Empirically Calibrated $\tau_{\text{emp}}(\sigma)$** | Accuracy, F1, FPR (Expect FPR reduction) |
| **C7** | 0.20 (Standard) | 1.0 | **Theoretically Calibrated $\tau_{\text{theo}}(\sigma)$** | Accuracy, F1, FPR (Evaluate theoretical model) |

---

### Group 3: Poisoning Detection Preservation Under Calibrated Trust
*Adversarial environment: 20% malicious clients ($N_{\text{mal}}=1, N_{\text{honest}}=4$ for $N=5$, or $N_{\text{mal}}=2, N_{\text{honest}}=6$ for $N=8$).*

| ID | Attack Vector | Noise Scale $\sigma$ | Defense Configuration | Primary Evaluation Metrics |
|:---|:---|:---:|:---|:---|
| **R1** | Targeted Label-Flip ($2 \to 0$) | 0.20 | Uncalibrated Trust vs Calibrated Trust | Accuracy, F1, ASR, MURR, FPR |
| **R2** | Untargeted Noise ($\mu=0, \sigma=2.0$) | 0.20 | Uncalibrated Trust vs Calibrated Trust | Accuracy, F1, MURR, FPR |
| **R3** | Scaled Sign-Flip ($\lambda = -3.0$) | 0.20 | Uncalibrated Trust vs Calibrated Trust | Accuracy, F1, MURR, FPR |
| **R4** | Targeted Label-Flip ($2 \to 0$) | 0.20 | Multi-Krum Baseline ($n \ge 2f + 3$) | Accuracy, F1, ASR, Rejection Rate |
| **R5** | Targeted Label-Flip ($2 \to 0$) | 0.20 | FoolsGold Baseline Standalone | Accuracy, F1, ASR, Weight Penalty |

---

### Group 4: Overhead & Tamper-Evidence Benchmarks
*Measures computational cost, bandwidth footprint, and ledger auditability.*

| ID | Benchmark Task | Configuration | Primary Evaluation Metrics |
|:---|:---|:---|:---|
| **O1** | Communication Footprint | 5 rounds, 5 clients, NSL-KDD | Total Upstream/Downstream Bytes per round |
| **O2** | Computational Latency | 5 rounds, 5 clients, NSL-KDD | Timings for ECDSA, Trust, Aggregation, Ledger |
| **T1** | Finite Tamper Stress Test | 5 tamper cases, 100 trials each | Detection Rate $P_D$, Verification Time $T_{\text{audit}}$ |
| **T2** | False Alarm Stress Test | 100 pristine chains | False Alarm Rate $P_{\text{FA}}$, Latency $T_{\text{audit}}$ |
