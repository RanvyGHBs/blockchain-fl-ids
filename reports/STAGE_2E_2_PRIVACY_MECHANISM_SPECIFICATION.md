# Stage 2E.2 — Formal Specification of the Recommended Privacy Mechanism
## Methodological Specification for Update Perturbation & Privacy Accounting

**Project:** Blockchain-Assisted Privacy-Preserving Federated Learning for Network Intrusion Detection with Trust-Based Security and Cryptographic Auditing  
**Workspace:** `C:\Users\is043\.gemini\antigravity\scratch\blockchain-fl-ids`  
**Milestone:** Stage 2E.2 (Privacy Mechanism Feasibility & Statistical Protocol Clarification)  
**Status:** METHODOLOGICAL SPECIFICATION (Planning Only — Zero Code Modifications)  
**Date:** November 2026  

---

## 1. Specification Overview

Following the comparative analysis in `STAGE_2E_2_PRIVACY_UNIT_FEASIBILITY.md`, this document provides the formal mathematical specification for the recommended privacy perturbation mechanism. 

The mechanism is designed specifically to study the central research question:
> **How can a federated intrusion detection system reliably distinguish malicious client updates from legitimate statistical deviations introduced by privacy-preserving perturbation?**

To maintain absolute scientific defensibility, this document explicitly separates the **operational update perturbation mechanism** (which provides exact sensitivity bounding via clipping) from the **formal privacy accounting requirements** (which require theoretical validation before any $(\epsilon, \delta)$ claims may be asserted).

---

## 2. Mathematical Specification of the Operational Mechanism

### 2.1 Privacy Unit and Adjacency Relation
- **Target Privacy Unit:** The complete parameter contribution of client $i$ during communication round $t$.
- **Adjacency Definition:** Let $\mathcal{D} = \{D_1, \dots, D_N\}$ denote the distributed dataset partitioned across $N$ network participants. Two distributed datasets $\mathcal{D}, \mathcal{D}'$ are adjacent at the client level under replacement if they differ by the complete partition of at most one client:
  $$\mathcal{D} \sim_{\text{client}} \mathcal{D}' \iff \exists ! k \in \{1, \dots, N\} \text{ s.t. } D_k \neq D_k' \text{ and } \forall j \neq k, D_j = D_j'$$
  Under addition/removal adjacency, $\mathcal{D}' = \mathcal{D} \setminus \{D_k\}$.

### 2.2 Model Update Definition
At the start of round $t$, client $i$ synchronizes its local model parameters with the broadcast global weights $\mathbf{w}_{\text{global}}^{(t-1)} \in \mathbb{R}^d$.  
Client $i$ executes local training (standard SGD or FedProx) over its private dataset $D_i$ for $E$ epochs, producing terminal local weights $\mathbf{w}_i^{(t)}$.  
The **raw local update delta** is defined as:
$$\Delta \mathbf{w}_i^{(t)} \triangleq \mathbf{w}_i^{(t)} - \mathbf{w}_{\text{global}}^{(t-1)} \in \mathbb{R}^d$$

### 2.3 Update Clipping Location & Operator
Clipping is executed **locally at the client**, immediately upon completion of local training, prior to noise addition, and prior to cryptographic signing.  
The clipping operator $\mathcal{C}_C: \mathbb{R}^d \to \mathbb{R}^d$ projects the update delta onto the $L_2$ ball of radius $C$:
$$\Delta \mathbf{w}_{i, \text{clipped}}^{(t)} = \mathcal{C}_C\left(\Delta \mathbf{w}_i^{(t)}\right) \triangleq \Delta \mathbf{w}_i^{(t)} \cdot \min\left(1, \frac{C}{\|\Delta \mathbf{w}_i^{(t)}\|_2}\right)$$
where $C > 0$ is the clipping threshold hyperparameter.

### 2.4 Mathematical Sensitivity Bound
Because the image of $\mathcal{C}_C$ is strictly bounded by $\|\mathcal{C}_C(\mathbf{v})\|_2 \le C$ for **all** vectors $\mathbf{v} \in \mathbb{R}^d$, the global $L_2$ sensitivity $\Delta_2$ of the clipped update with respect to client adjacency is mathematically exact:
- **Under Addition/Removal Adjacency ($\mathcal{D}' = \mathcal{D} \setminus \{D_k\}$):**
  $$\Delta_2 = \sup_{\mathcal{D} \sim \mathcal{D}'} \|\mathcal{C}_C(\Delta \mathbf{w}_k) - \mathbf{0}\|_2 = C$$
- **Under Replacement Adjacency ($D_k \to D_k'$):**
  $$\Delta_2 = \sup_{\mathcal{D} \sim \mathcal{D}'} \|\mathcal{C}_C(\Delta \mathbf{w}_k) - \mathcal{C}_C(\Delta \mathbf{w}_k')\|_2 \le 2C$$

*Methodological Guarantee:* This sensitivity bound holds unconditionally, independent of local loss landscape non-convexity, learning rate schedules, or data distributions.

### 2.5 Calibrated Gaussian Perturbation
Client $i$ perturbs its clipped update delta by drawing an independent stochastic noise vector:
$$\mathbf{n}_i^{(t)} \sim \mathcal{N}\left(\mathbf{0}, \sigma^2 C^2 \mathbf{I}_d\right)$$
producing the privatized released update:
$$\Delta \mathbf{w}_{i, \text{private}}^{(t)} = \Delta \mathbf{w}_{i, \text{clipped}}^{(t)} + \mathbf{n}_i^{(t)}$$
where:
- $C$: $L_2$ clipping bound ($C = 1.0$ standard default).
- $\sigma$: Noise multiplier hyperparameter ($\sigma \in [0.01, 0.50]$; $\sigma = 0.20$ default evaluation target).
- $d$: Parameter dimension of the network IDS model ($d = 122 \times H_1 + H_1 \times H_2 + \dots$).

The client transmits the signed tuple $\left( \Delta \mathbf{w}_{i, \text{private}}^{(t)}, \text{Sign}_{\text{sk}_i}\left(\text{SHA256}(\Delta \mathbf{w}_{i, \text{private}}^{(t)})\right) \right)$ to the server.

---

## 3. Explicit Distinction of Operational Boundaries

To eliminate the terminological ambiguities identified in Stage 2E.1, the table below explicitly contrasts the operations:

| Operation | Mathematical Definition | Execution Location | Purpose in Framework |
|:---|:---|:---|:---|
| **Complete Client Update Clipping** | $\Delta \mathbf{w} \cdot \min(1, C/\|\Delta \mathbf{w}\|_2)$ | Client-side (post-SGD) | Bounds client-level update sensitivity to $C$ |
| **Per-Example Gradient Clipping** | $\nabla \ell_j \cdot \min(1, C_{\text{ex}}/\|\nabla \ell_j\|_2)$ | Client-side (inner SGD loop) | Bounds example-level gradient sensitivity |
| **Local Client Noise Addition** | $\Delta \mathbf{w}_{\text{clipped}} + \mathcal{N}(0, \sigma^2 C^2 \mathbf{I})$ | Client-side (pre-transmission) | Protects client update against untrusted server/peers |
| **Central Aggregator Noise Addition** | $\sum \Delta \mathbf{w}_i + \mathcal{N}(0, \sigma^2 C^2 \mathbf{I})$ | Server-side (post-aggregation) | Protects global model against downstream consumers |

*Architectural Confirmation:* Our research framework implements **Complete Client Update Clipping** with **Local Client Noise Addition**. This represents the local perturbation model where the server's trust engine evaluates noisy client vectors directly.

---

## 4. Analysis of Rényi Differential Privacy (RDP) Accounting

### 4.1 Mechanism Classification
The operational mechanism corresponds to the **Local Gaussian Mechanism** $\mathcal{M}_{\sigma, C}: \mathcal{D}_i \to \mathbb{R}^d$ applied independently by each client in each communication round.

### 4.2 Client Participation & Subsampling Reality
- In our standard experimental setup, total simulated clients $N = 5$.
- In each round $t \in \{1, \dots, T\}$, all active (non-quarantined) clients participate.
- Therefore, the client sampling probability is:
  $$q = \frac{N_{\text{active}}}{N} = \frac{5}{5} = 1.0$$
- **Subsampling Amplification Analysis:**  
  Subsampled Gaussian mechanism accountants (e.g., Wang et al., AISTATS 2019; Mironov et al., 2019) require random Poisson subsampling with $q \ll 1.0$. Because client selection in our baseline simulation is deterministic full participation ($q = 1.0$), **subsampling amplification is mathematically inapplicable**.

### 4.3 RDP Formulation for Full Participation
For Rényi order $\alpha > 1$, the standard Gaussian mechanism with sensitivity $\Delta_2 = C$ and noise scale $\sigma C$ provides Rényi divergence:
$$R_\alpha(\mathcal{M}) = \frac{\alpha \Delta_2^2}{2 (\sigma C)^2} = \frac{\alpha C^2}{2 \sigma^2 C^2} = \frac{\alpha}{2 \sigma^2}$$
Under sequential composition across $T$ rounds where the same client participates in every round without subsampling:
$$R_\alpha\left(\mathcal{M}^{\circ T}\right) = \sum_{t=1}^T R_\alpha(\mathcal{M}_t) = \frac{T \alpha}{2 \sigma^2}$$

### 4.4 Conversion to Canonical $(\epsilon, \delta)$-Differential Privacy
By Mironov (CSF 2017), the cumulative RDP converts to standard $(\epsilon, \delta)$-DP for any specified target $\delta \in (0, 1)$ via:
$$\epsilon(\delta) = \min_{\alpha > 1} \left\{ \frac{T \alpha}{2 \sigma^2} + \frac{\ln(1/\delta)}{\alpha - 1} \right\}$$
Analytical minimization yields the optimal order $\alpha^* = 1 + \sqrt{\frac{2 \sigma^2 \ln(1/\delta)}{T}}$, resulting in the closed-form bound:
$$\epsilon^*(\delta) = \frac{T}{2 \sigma^2} + \sqrt{\frac{2 T \ln(1/\delta)}{\sigma^2}}$$

### 4.5 Quantitative Assessment for the 5-Client Simulation
Evaluating this bound over $T = 5$ rounds with target $\delta = 10^{-5}$:
- At $\sigma = 0.05$: $\epsilon^* \approx 1000 + 480 \approx 1480$ (vacuous).
- At $\sigma = 0.10$: $\epsilon^* \approx 250 + 240 \approx 490$ (vacuous).
- At $\sigma = 0.20$: $\epsilon^* \approx 62.5 + 120 \approx 182.5$ (large).
- At $\sigma = 0.50$: $\epsilon^* \approx 10.0 + 48.0 \approx 58.0$.
- At $\sigma = 1.50$: $\epsilon^* \approx 1.11 + 16.0 \approx 17.1$.

**Crucial Scholarly Finding:**  
In a small cross-silo federated network ($N=5$) where clients participate in every round ($q=1.0$), the mathematical client-level privacy guarantee $\epsilon$ is inevitably large unless noise is scaled to levels ($\sigma \ge 1.5$) that completely destroy model accuracy. This is not a flaw in our accounting; it is a fundamental theoretical reality of differential privacy without subsampling amplification.

---

## 5. Required Evidence Before Formal Privacy Claims

To prevent academic overclaiming, the planning package establishes explicit criteria that must be satisfied before any formal privacy claims may be asserted:

1. **Unit Test Verification of Analytical Accountant:**  
   The numerical RDP accountant must be unit-tested against the analytical closed-form equation across multiple orders $\alpha \in [1.5, 64.0]$ to verify numerical convergence to within $10^{-6}$ precision.
2. **Empirical Noise Vector Validation:**  
   Empirical testing must verify that generated noise vectors $\mathbf{n}_i$ possess zero mean, spherical covariance $\sigma^2 C^2 \mathbf{I}$, and correct dimension $d$.
3. **Formal Scope Statement in Publications:**  
   Research publications and technical reports must explicitly document that:
   - Noise is added locally to client update deltas;
   - Client participation is full ($q=1.0$);
   - The primary research contribution is investigating the **systemic impact of noise on the trust engine**, not claiming a state-of-the-art small-$\epsilon$ client-level privacy bound in a 5-node silo.

---

## 6. Mandatory Terminology Invariance

Throughout Stage 2E planning, implementation, and reporting, the mechanism must be referred to strictly as:

> **Clipping-based Gaussian update perturbation (without formal privacy accounting)**

### Forbidden Claims
The following assertions are strictly prohibited until the verification criteria in Section 5 are fully satisfied:
- "Local Differential Privacy (LDP) is guaranteed."
- "Formal client-level $(\epsilon, \delta)$-differential privacy has been achieved."
- "Formal example-level differential privacy is established."
- "Keeping raw data local guarantees differential privacy."
