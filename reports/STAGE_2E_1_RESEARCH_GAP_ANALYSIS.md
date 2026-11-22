# Stage 2E.1 — Research Gap Analysis & Methodological Revision
## Privacy-Aware Trust Calibration for Blockchain-Audited Federated Network Intrusion Detection

**Project:** Blockchain-Assisted Privacy-Preserving Federated Learning for Network Intrusion Detection with Trust-Based Security and Cryptographic Auditing  
**Workspace:** `C:\Users\is043\.gemini\antigravity\scratch\blockchain-fl-ids`  
**Milestone:** Stage 2E.1 (Methodological Corrections & Planning Package Revision)  
**Status:** REVISED PLANNING DOCUMENT (Planning Only — Zero Code Modifications)  
**Date:** November 2026  

---

## 1. Executive Summary & Revised Research Focus

This document establishes the revised research gap analysis for the Stage 2E research cycle, replacing the initial assumptions of Stage 2E with an internally consistent, methodologically rigorous foundation.

### 1.1 The Central Research Contribution
The central research direction of this project is:
> **Privacy-Aware Trust Calibration for Blockchain-Audited Federated Network Intrusion Detection**

The central research question is formulated as:
> **How can a federated intrusion detection system reliably distinguish malicious client updates from legitimate statistical deviations introduced by privacy-preserving perturbation?**

### 1.2 Core Research Motivation: The Privacy–Security Conflict
In a federated network intrusion detection system (FL-IDS), edge participants (e.g., enterprise branches, campus networks, datacenter enclaves) collaborate to train deep learning models without sharing sensitive raw packet flows or connection records. To mitigate gradient inversion and membership inference attacks, clients perturb their updates using privacy-preserving mechanisms (such as clipping-based Gaussian perturbation).

However, this introduces an inherent structural conflict with trust-based Byzantine defenses:
1. **Client-Side Perturbation:** Honest clients add stochastic noise to their parameter updates to protect local training records.
2. **Geometric & Loss Trust Evaluation:** The server inspects parameter vector geometry ($L_2$ norm, cosine similarity against peer consensus) and validation-loss impact to identify malicious model poisoning or evasion attacks.
3. **Reputation Slashing & Quarantine:** Updates exhibiting high angular divergence or loss degradation are flagged as malicious, penalizing client reputation and triggering quarantine.
4. **False-Positive Defense Failure:** A legitimate client whose update deviates solely due to privacy perturbation risks being misclassified as an adversary, slashed, and quarantined. Conversely, if trust thresholds are relaxed naively, actual adversaries can hide poison within the noise margin.

**Methodological Stance for Stage 2E.1:**  
We do **not** assume that a simple heuristic threshold formula $\tau = f(C, \sigma, d)$ is automatically sufficient. Instead, Stage 2E proposes an empirical and theoretical investigation to determine whether, and under what conditions, trust evaluation can be calibrated to account for legitimate privacy-induced variation without weakening detection of malicious poisoning.

---

## 2. Reconciliation with Existing Stage 2D Architecture

The initial Stage 2E proposal inadvertently introduced a fictitious "Beta Reputation & Two-Strike Quarantine" mechanism that conflicted with the actual codebase. This revision reconciles all planning directly with the verified Stage 2D implementation.

### 2.1 The Implemented Stage 2D Baseline Architecture `[Existing and Implemented]`
As verified in `src/trust/evaluator.py`, `src/trust/reputation.py`, and `src/federated/orchestrator.py`:
- **Multi-Criteria Trust Engine (`MultiCriteriaTrustEngine`):**
  - **Tier 1 (L2-Norm Bounding):** Enforces $\|\mathbf{w}_i\|_2 \le \max(1.0, \|\mathbf{w}_{\text{global}}\|_2 \times \gamma)$ with default factor $\gamma = 2.5$.
  - **Tier 2 (Cosine Similarity against Peer Median):** Enforces $\cos(\mathbf{w}_i, \mathbf{w}_{\text{median}}) \ge \tau_{\text{cosine}}$ with default threshold $\tau_{\text{cosine}} = 0.15$.
  - **Tier 3 (Validation-Loss Verification):** Evaluates candidate weights on a balanced validation slice; rejects if relative loss increase exceeds $\tau_{\text{loss}} = 1.5$ (i.e., $\frac{\mathcal{L}_{\text{cand}} - \mathcal{L}_{\text{base}}}{\max(0.01, \mathcal{L}_{\text{base}})} > 1.5$).
- **Dynamic Reputation & Quarantine Manager (`ReputationManager`):**
  - Initial reputation: $R_0 = 1.0$ for all clients.
  - **Reward delta:** $+0.05$ per valid round (capped at $1.0$).
  - **Asymmetric penalty (slashing):** $-0.35$ per invalid round (bounded at $0.0$).
  - **Quarantine threshold:** $R_t < 0.40$ places the client into active quarantine.
  - **Probation policy:** Quarantined clients enter shadow probation; requires $3$ consecutive valid rounds during probation to achieve readmission (readmission baseline reputation reset to $0.50$).
- **Cryptographic Audit Ledger (`Blockchain`, `Block`, `CryptoManager`):**
  - Simulated locally as an append-only JSON hash-chain with SHA-256 block header chaining, local Merkle transaction trees, and ECDSA P-256 digital signatures on update hashes.

### 2.2 Reconciled Architectural Boundaries
1. The proposed "Beta Reputation & Two-Strike Quarantine" model is **fully removed** from the architecture.
2. The Stage 2D asymmetric slashing ($+0.05 / -0.35$, threshold $0.40$, 3-round probation) is preserved as the frozen baseline.
3. Privacy-aware calibration is designed strictly as a proposed parameter-adjustment extension to the existing `MultiCriteriaTrustEngine`.

---

## 3. Formalization of Privacy Mechanism & Accounting

### 3.1 Terminology and Current Implementation Baseline
The current Stage 2D codebase (`src/privacy/differential.py`) implements:
> **Clipping-based Gaussian update perturbation (without formal privacy accounting)**

It applies heuristic $L_2$-norm clipping and Gaussian noise to absolute model parameter vectors without formal sensitivity bounds, subsampling proofs, or composition accountants. Keeping raw traffic logs local to client silos does **not** alone provide a formal privacy guarantee, as unperturbed model updates can leak training samples through gradient inversion or membership inference.

### 3.2 Formal Privacy Requirements for Stage 2E

#### A. Privacy Unit and Adjacency `[Requires Theoretical Validation]`
The privacy mechanism must explicitly define its unit of protection:
- **Client-Level Differential Privacy:** Protects the presence or absence of an entire client's dataset in the federated training process. Two dataset collections $\mathcal{D}$ and $\mathcal{D}'$ are adjacent if they differ by the complete data partition of one client: $\mathcal{D}' = \mathcal{D} \setminus \{D_i\}$.
- **Example-Level Differential Privacy:** Protects the presence or absence of a single network flow record within a client's local dataset $D_i$. Two local datasets $D_i$ and $D_i'$ are adjacent if they differ by exactly one record: $|D_i \oplus D_i'| = 1$.

*Methodological Rule:* Stage 2E must explicitly distinguish client-level from example-level privacy and formulate the sensitivity bound strictly in terms of the selected adjacency definition.

#### B. Update Clipping Mechanism `[Proposed for Stage 2E]`
Clipping must operate on the local parameter update $\Delta \mathbf{w}_i^{(t)} = \mathbf{w}_i^{(t)} - \mathbf{w}_{\text{global}}^{(t-1)}$, not the raw absolute weight vector:
$$\Delta \mathbf{w}_{i, \text{clipped}}^{(t)} = \Delta \mathbf{w}_i^{(t)} \times \min\left(1, \frac{C}{\|\Delta \mathbf{w}_i^{(t)}\|_2}\right)$$
- Clipping occurs independently at each client prior to noise addition.
- The clipping threshold $C$ bounds the local update sensitivity to $\|\Delta \mathbf{w}_{i, \text{clipped}}^{(t)}\|_2 \le C$.

#### C. Gaussian Perturbation `[Proposed for Stage 2E]`
Noise is added to the clipped update vector:
$$\Delta \mathbf{w}_{i, \text{private}}^{(t)} = \Delta \mathbf{w}_{i, \text{clipped}}^{(t)} + \mathcal{N}\left(0, \sigma^2 C^2 \mathbf{I}_d\right)$$
where $C$ is the clipping bound, $\sigma$ is the noise multiplier, and $d$ is the model parameter dimension.

#### D. Sampling, Composition, and Accounting `[Requires Theoretical Validation]`
A valid privacy accountant cannot rely on a simplified textbook formula. The accountant must formally account for:
1. Client participation rate (deterministic vs random subsampling of clients).
2. Number of global communication rounds $T$.
3. Repeated participation of the same client across multiple rounds.
4. The exact noise multiplier $\sigma$ and sensitivity bound $C$.
5. Composition across rounds (e.g., via Rényi Differential Privacy (RDP) composition or Gaussian Differential Privacy).

*Methodological Rule:* Until the exact mechanism, adjacency relation, and composition proofs are implemented and verified against unit tests, no formal $(\epsilon, \delta)$-DP or Local Differential Privacy claims may be asserted.

---

## 4. Theory and Methodology of Privacy–Trust Calibration

### 4.1 Why Simple Threshold Formulas Are Insufficient
The initial Stage 2E proposal suggested adjusting the cosine threshold via $\tau = \tau_0 - \kappa \sigma \frac{C}{\sqrt{d}}$. This formulation is an unvalidated heuristic because privacy-induced variation in deep neural networks does not manifest as isotropic white noise in parameter space.

Update geometry and validation loss are influenced by complex interacting variables:
- **Parameter Distribution:** Gradients concentrate in specific layers (e.g., classification head vs bottleneck layers).
- **Data Heterogeneity (Non-IID Skew):** Dirichlet concentration $\alpha$ causes natural angular divergence among honest clients even without privacy noise.
- **Client Sample Size:** Clients with smaller local datasets exhibit higher gradient variance.
- **Model State / Convergence Stage:** Early rounds exhibit large parameter updates; late rounds exhibit small updates where Gaussian noise dominates the signal.
- **Noise Realization:** Random Gaussian draws can occasionally generate extreme angular deviations.

### 4.2 Distinguishing Calibration Approaches
The revised research plan strictly distinguishes three levels of calibration:
1. **Theoretically Derived Calibration Bound:** A mathematically proven upper bound on the angular divergence and loss deviation induced by Gaussian perturbation with parameters $(C, \sigma, d)$ under Lipschitz continuity and gradient boundedness assumptions.
2. **Empirically Estimated Calibration Threshold:** A threshold estimated from Monte Carlo profiling of honest client updates across standardized seeds under controlled clean conditions.
3. **Heuristic Calibration Threshold:** An experimentally selected static or linear adjustment rule tuned to balance detection rates.

### 4.3 Proposed Empirical Calibration Methodology
Stage 2E proposes a four-step experimental methodology:
1. **Honest Baseline Noise Profiling:** Measure the distribution of $L_2$ norms, cosine similarities to peer median, and validation loss deltas for honest clients across a sweep of noise multipliers $\sigma \in \{0.0, 0.01, 0.05, 0.1, 0.2, 0.5\}$ under both IID and Non-IID Dirichlet partitions.
2. **False-Positive Threshold Identification:** Identify the empirical noise threshold $\sigma_{\text{crit}}$ at which honest clients begin triggering false-positive rejections under the existing Stage 2D trust parameters ($\tau_{\text{cosine}} = 0.15, \tau_{\text{loss}} = 1.5$).
3. **Calibration Formulation:** Formulate empirical and theoretical calibration adjustments $\tau_{\text{cosine}}(\sigma)$ and $\tau_{\text{loss}}(\sigma)$.
4. **Poisoning Detection Preservation Stress Test:** Evaluate whether calibrated thresholds maintain high Malicious Update Rejection Rate (MURR) and low Attack Success Rate (ASR) against targeted label-flipping, sign-flipping, and noise-injection adversaries.

---

## 5. Statistical Rigor & Experimental Design Revision

### 5.1 Pilot Ensemble vs Final Sample Size
The 5-seed ensemble ($S = \{42, 101, 2024, 777, 999\}$) proposed in Stage 2E is designated as an **initial statistical pilot**, not a definitive claim of statistical finality. 
- The pilot will quantify metric variance across seeds.
- If variance across seeds is substantial or confidence intervals overlap across competing defenses, a formal statistical power analysis will determine the necessary sample size ($S = 10$ or higher) for final claims.

### 5.2 Correct Statistical Hypothesis Testing Terminology
The contradictory term *"Paired Welch's t-test"* is expunged. The revised experimental protocol establishes strict test-selection rules:
- **Paired $t$-Test:** Employed when comparing two algorithms or defense configurations evaluated on **matched experiments** sharing identical initial weights, Dirichlet partitions, and random seeds. Requires verification of normality of pair differences (e.g., via Shapiro-Wilk test).
- **Welch's Independent-Samples $t$-Test:** Employed when comparing two independent groups where random seeds or client groupings are not matched, and unequal variances are assumed.
- **Wilcoxon Signed-Rank Test:** Employed as the mandatory non-parametric alternative for matched pairs when the sample size is small ($S=5$) or normality of differences cannot be established.
- **Mann-Whitney U Test:** Employed for independent group comparisons when distributional assumptions are violated.

### 5.3 Controlled Comparison Standards
In compliance with Stage 2D.4 determinism:
- Every comparison pair (e.g., Calibrated Trust vs Uncalibrated Trust, or Proposed vs Baseline) must strictly match:
  1. Initial global model weights hash.
  2. Dataset partition indices and client sample assignments.
  3. Batch permutation sequences.
  4. Local training hyperparameters (epochs, learning rate, batch size).
  5. Attack hyperparameters and target classes.
- Effect sizes (e.g., Cohen's $d$ for parametric tests, rank-biserial correlation for non-parametric tests) must accompany all $p$-values to distinguish statistical significance from practical operational importance.

---

## 6. Baseline Algorithms Review & Assumption Validation

### 6.1 Multi-Krum (Blanchard et al., NeurIPS 2017) `[Proposed for Stage 2E]`
- **Algorithm Principle:** Selects the candidate update that minimizes the sum of Euclidean distances to its $n - f - 2$ closest neighbors.
- **Theoretical Byzantine Assumption:** Multi-Krum mathematically requires:
  $$n \ge 2f + 3$$
  where $n$ is total participating clients and $f$ is the number of Byzantine/malicious clients.
- **Validation against Project Setup:**
  - In our standard 5-client benchmark ($n = 5$):
    - If $f = 2$ (40% adversaries): $2(2) + 3 = 7 > 5$. **The Byzantine assumption is mathematically violated.**
    - If $f = 1$ (20% adversaries): $2(1) + 3 = 5 \le 5$. **The condition holds with exact equality.**
- **Integration Rule:** Multi-Krum baseline comparisons are only theoretically valid under configurations where $n \ge 2f + 3$. For $f=2$, the client pool must be scaled to $n \ge 7$. Running Multi-Krum under $n=5, f=2$ constitutes an out-of-spec stress test and must be documented as such.

### 6.2 FoolsGold (Fung et al., IEEE TIFS 2020) `[Proposed for Stage 2E]`
- **Algorithm Principle:** Designed specifically to mitigate Sybil attacks by computing pairwise cosine similarities between client historical update trajectories. Clients that repeatedly submit highly correlated updates are penalized with reduced aggregation weights.
- **Integration with Existing Architecture:**
  - FoolsGold operates on historical gradient vectors $\Delta \mathbf{w}_i^{(t)}$.
  - In our framework, `MultiCriteriaTrustEngine` already computes cosine similarity to the peer median. 
  - Applying FoolsGold alongside our trust engine risks redundant penalization. Therefore, FoolsGold must be evaluated as an **alternative standalone aggregator baseline**, replacing trust-weighted FedAvg, rather than stacked redundantly.

---

## 7. Dataset Scope & Isolation Discipline

### 7.1 Primary Dataset: NSL-KDD
To prevent scope explosion and preserve benchmark integrity, **NSL-KDD remains the primary benchmark dataset** for all Stage 2E core evaluations.

### 7.2 Strict Five-Stage Data Isolation Protocol `[Existing and Implemented]`
All data operations must strictly maintain the established isolation boundaries:
1. **Raw Split:** NSL-KDD is partitioned into Development Data (train) and Held-Out Test Data (test).
2. **Development Split:** Development Data is partitioned into Client-Training Pool and Server Trust-Validation Benchmark.
3. **Preprocessing Fitting:** `StandardScaler` and categorical encoders are fitted **exclusively** on the Client-Training Pool.
4. **Transform Only:** Trust-Validation and Held-Out Test sets are transformed using the fitted preprocessor; they are never used to fit scalers.
5. **Evaluation Isolation:** The Held-Out Test set is evaluated strictly once per round to assess global model generalization. It is never accessed during local training, trust validation, threshold calibration, or hyperparameter selection.

*Optional Future Datasets:* UNSW-NB15 and CIC-IDS2017 are classified as `[Optional Future Extension]`. They require dedicated preprocessing pipelines, label mapping schemas, and baseline tuning before any experimental integration.

---

## 8. Overhead Profiling & Blockchain Audit Formulation

### 8.1 Empirical Profiling Boundaries `[Proposed for Stage 2E]`
The overhead profiler must measure:
- **Payload Sizes (Bytes):** Exact serialized sizes of client update vectors, ECDSA signatures, metadata, and broadcast model packages.
- **Computational Latency (Milliseconds):** Measured via `time.perf_counter_ns()`:
  - Client ECDSA signing latency.
  - Server ECDSA batch verification latency.
  - Multi-criteria trust evaluation latency.
  - Aggregation computation latency.
  - Block header hashing and Merkle root calculation latency.
  - Chain audit verification latency.
- *Methodological Distinction:* Computational latency on the local host must be explicitly distinguished from simulated network propagation delay.

### 8.2 Accurate Characterization of the Blockchain Subsystem `[Existing and Implemented]`
The blockchain implementation in `src/blockchain/` is a **tamper-evident, cryptographically verifiable local audit ledger**, not a decentralized Byzantine consensus network.
- It employs SHA-256 block chaining, Merkle trees, and ECDSA P-256 signatures to provide cryptographic non-repudiation and tamper-evidence.
- It does **not** feature peer-to-peer gossip protocols, proof-of-work/stake consensus, or distributed state replication.
- Claims of "absolute immutability" or "production-grade decentralization" are methodologically invalid and must not be made.

### 8.3 Tamper-Evidence Verification Protocol `[Proposed for Stage 2E]`
Tamper detection performance must be evaluated over an explicitly defined **finite test suite**:
1. **Payload Modification:** Altering model hash or transaction metadata in an intermediate block.
2. **Block Deletion:** Removing an intermediate block from the chain.
3. **Block Reordering:** Transposing two consecutive blocks.
4. **Hash-Chain Inconsistency:** Overwriting `prev_hash` without recalculating subsequent block headers.
5. **Merkle-Root Inconsistency:** Modifying a transaction record without updating the Merkle root.

*Methodological Rule:* Detection probability $P_D$ and false-alarm rate $P_{\text{FA}}$ must be reported strictly over this finite set of synthetic test cases (e.g., $N=100$ trials per test case). Universal mathematical guarantees ($P_D = 1.0$ for all possible attacks) must not be claimed. ECDSA verifies signer authenticity, not whether an update is semantically benign.

---

## 9. Reorganized Work Packages (WP1 to WP5)

The implementation roadmap is reorganized into five sequential, logically dependent packages:

1. **WP1: Multi-Seed Statistical Baseline Evaluation**
   - Establish reproducible multi-seed baseline performance across $S=5$ seeds.
   - Benchmark Centralized-IDS, Local Silos, FedAvg, and validated Byzantine baselines (Multi-Krum where $n \ge 2f + 3$, FoolsGold).
2. **WP2: Formal Privacy Mechanism and Accounting**
   - Formulate exact adjacency (client-level vs example-level).
   - Implement client-side update clipping on $\Delta \mathbf{w}_i$ and calibrated Gaussian noise.
   - Formally derive and verify an RDP or moments accountant.
3. **WP3: Privacy-Aware Trust Calibration (Central Research Contribution)**
   - Profile honest-client noise sensitivity under clean conditions.
   - Investigate empirical and theoretical calibration adjustments to `MultiCriteriaTrustEngine`.
   - Measure false-positive reduction and poisoning-detection preservation.
4. **WP4: Computational Overhead & Blockchain Audit Evaluation**
   - Instrument communication byte counters and execution latency timers.
   - Implement `AuditVerifier` and execute finite tamper-evidence stress tests.
5. **WP5: Optional Adversarial Extension**
   - Explore complex multi-attack evasion scenarios (adaptive Byzantine, Sybil coalitions) as an optional post-core extension.

---

## 10. Summary Status of Planning Components

| Component / Subsystem | Status Label | Notes |
|:---|:---|:---|
| Multi-Criteria Trust Engine (L2, Cosine, Loss) | `[Existing and Implemented]` | Verified in `src/trust/evaluator.py` |
| Asymmetric Reputation (+0.05 / -0.35, Q < 0.40, 3-round probation) | `[Existing and Implemented]` | Verified in `src/trust/reputation.py` |
| Heuristic Gaussian Perturbation (uncalibrated) | `[Existing and Implemented]` | Implemented in `src/privacy/differential.py` |
| Tamper-Evident Local Audit Ledger (SHA-256, Merkle, ECDSA) | `[Existing and Implemented]` | Implemented in `src/blockchain/` |
| NSL-KDD 5-Stage Data Isolation Pipeline | `[Existing and Implemented]` | Verified in `src/data/` |
| Multi-Seed Statistical Pilot ($S=5$) | `[Proposed for Stage 2E]` | Requires pilot evaluation and power analysis |
| Baselines (Centralized, Silo, Multi-Krum, FoolsGold) | `[Proposed for Stage 2E]` | Requires Multi-Krum $n \ge 2f + 3$ validation |
| Update Clipping on $\Delta \mathbf{w}$ & Privacy Accountant | `[Requires Theoretical Validation]` | Must formally establish adjacency & composition |
| Privacy-Aware Trust Calibration $\tau(\sigma)$ | `[Requires Experimental Validation]` | Central research contribution to be investigated |
| Automated Audit Verifier & Tamper Stress Tests | `[Proposed for Stage 2E]` | Finite test set evaluation |
| Alternate Datasets (UNSW-NB15, CIC-IDS2017) | `[Optional Future Extension]` | Deferred to preserve primary scope |
| Advanced Evasion & Sybil Extension (WP5) | `[Optional Future Extension]` | Deferrable post-core |
