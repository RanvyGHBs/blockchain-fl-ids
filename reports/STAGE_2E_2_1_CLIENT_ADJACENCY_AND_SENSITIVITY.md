# Stage 2E.2.1 — Client-Level Adjacency, Sensitivity Bounding, and Local Perturbation Mechanics
## Mathematical Clarification of Adjacency Relations and Sensitivity in Federated Learning

**Project:** Blockchain-Assisted Privacy-Preserving Federated Learning for Network Intrusion Detection with Trust-Based Security and Cryptographic Auditing  
**Workspace:** `C:\Users\is043\.gemini\antigravity\scratch\blockchain-fl-ids`  
**Milestone:** Stage 2E.2.1 (Client-Level Sensitivity & Privacy Composition Verification)  
**Status:** MATHEMATICAL CLARIFICATION (Planning Only — Zero Code Modifications)  
**Date:** November 2026  

---

## 1. Executive Summary & Problem Formulation

In Stage 2E.2, the architectural review established that clipping the complete local parameter update $\Delta \mathbf{w}_i^{(t)} = \mathbf{w}_i^{(t)} - \mathbf{w}_{\text{global}}^{(t-1)}$ bounds the **client-level sensitivity** of the client's contribution, but does not bound example-level sensitivity. 

To prepare a mathematically defensible foundation for Work Package 2 (WP2), this document resolves the remaining mathematical ambiguities surrounding:
1. The exact formulation of client-level adjacency (Add/Remove-Client vs. Replace-One-Client-Dataset).
2. The rigorous $L_2$ global sensitivity derivation of the clipped update vector under each adjacency relation.
3. The operational mechanics, information exposure, and threat-model boundaries of local client-side Gaussian perturbation.

---

## 2. Mathematical Definition of Client-Level Adjacency Relations

In federated learning, a distributed dataset state across $N$ network participants is denoted as a collection of local datasets:
$$\mathcal{D} = \{D_1, D_2, \dots, D_N\}$$
where each $D_i \subset \mathcal{X} \times \mathcal{Y}$ represents the local network telemetry partition held by client $i$.

We examine the two canonical formulations of client-level adjacency.

---

### 2.1 Definition A: Add/Remove-Client Adjacency

#### 2.1.1 Formal Definition
Two federated dataset collections $\mathcal{D}$ and $\mathcal{D}'$ are adjacent under the add/remove relation if one collection contains an additional client dataset that is absent from the other:
$$\mathcal{D} \sim_{\text{add/remove}} \mathcal{D}' \iff |\mathcal{D} \Delta \mathcal{D}'| = 1$$
Specifically, there exists an index $k$ such that either:
$$\mathcal{D}' = \mathcal{D} \setminus \{D_k\} \quad \text{or} \quad \mathcal{D} = \mathcal{D}' \setminus \{D_k\}$$

#### 2.1.2 Representation of the Absent Client
In a federated aggregation round where client $k$ is absent from $\mathcal{D}'$:
- In the client update space $\mathbb{R}^d$, the absent client produces **no update**, which is formally represented in the global sum as the additive identity:
  $$\Delta \mathbf{w}_k = \mathbf{0} \in \mathbb{R}^d$$
- If the global aggregation operator is a simple sum of updates $\sum_{i} \Delta \mathbf{w}_i$, the contribution of client $k$ changes from $\Delta \mathbf{w}_k$ in $\mathcal{D}$ to $\mathbf{0}$ in $\mathcal{D}'$.

#### 2.1.3 Sensitivity Derivation Under Add/Remove
Let $\mathcal{C}_C: \mathbb{R}^d \to \mathbb{R}^d$ denote the $L_2$ clipping operator with clipping threshold $C > 0$:
$$\mathcal{C}_C(\mathbf{v}) \triangleq \mathbf{v} \cdot \min\left(1, \frac{C}{\|\mathbf{v}\|_2}\right)$$
By definition of the Euclidean norm projection onto the closed $L_2$ ball $\mathcal{B}_2(C) \triangleq \{\mathbf{u} \in \mathbb{R}^d : \|\mathbf{u}\|_2 \le C\}$, for any raw update vector $\Delta \mathbf{w}_k \in \mathbb{R}^d$:
$$\|\mathcal{C}_C(\Delta \mathbf{w}_k)\|_2 \le C$$
The difference in the output of the clipping operator between the world where client $k$ is present ($\mathcal{D}$) versus absent ($\mathcal{D}'$) is:
$$\|\mathcal{C}_C(\Delta \mathbf{w}_k) - \mathbf{0}\|_2 = \|\mathcal{C}_C(\Delta \mathbf{w}_k)\|_2 \le C$$
Taking the supremum over all possible training datasets $D_k$:
$$\Delta_{2, \text{add/remove}} \triangleq \sup_{\mathcal{D} \sim_{\text{add/remove}} \mathcal{D}'} \|\mathcal{C}_C(\Delta \mathbf{w}_k) - \mathbf{0}\|_2 = C$$

#### 2.1.4 Required Assumptions for $S = C$ Under Add/Remove
For this sensitivity bound to hold rigorously, the following conditions must be satisfied:
1. **Linear Sum Aggregation Space:** The sensitivity bound applies directly to the vector output of client $k$. If FedAvg normalization $\frac{1}{N} \sum_i \Delta \mathbf{w}_i$ is evaluated, the denominator changes from $N$ to $N-1$ when a client is removed, which introduces a non-zero sensitivity shift across all other $N-1$ client weights unless aggregation is normalized by a fixed constant $N_0$.
2. **Variable Participation Semantics:** The system must meaningfully model scenarios where the total number of clients varies between $N$ and $N-1$.
3. **Absence Equivalency:** The absent client must contribute exactly the zero vector $\mathbf{0}$.

---

### 2.2 Definition B: Replace-One-Client-Dataset Adjacency

#### 2.2.1 Formal Definition
Two federated dataset collections $\mathcal{D} = \{D_1, \dots, D_N\}$ and $\mathcal{D}' = \{D_1', \dots, D_N'\}$ are adjacent under the replacement relation if the total number of participating clients $N$ remains fixed, but exactly one client's local training dataset is replaced by an alternative dataset:
$$\mathcal{D} \sim_{\text{replace}} \mathcal{D}' \iff \exists ! k \in \{1, \dots, N\} \text{ s.t. } D_k \neq D_k' \quad \text{and} \quad \forall j \neq k, D_j = D_j'$$

#### 2.2.2 Sensitivity Derivation Under Replacement
Under dataset $D_k$, client $k$ trains locally and produces raw update $\Delta \mathbf{w}_k$. After clipping, the update is:
$$\bar{\Delta \mathbf{w}}_k = \mathcal{C}_C(\Delta \mathbf{w}_k), \quad \text{with } \|\bar{\Delta \mathbf{w}}_k\|_2 \le C$$
Under alternative dataset $D_k'$, client $k$ trains locally and produces raw update $\Delta \mathbf{w}_k'$. After clipping, the update is:
$$\bar{\Delta \mathbf{w}}_k' = \mathcal{C}_C(\Delta \mathbf{w}_k'), \quad \text{with } \|\bar{\Delta \mathbf{w}}_k'\|_2 \le C$$
The $L_2$ sensitivity is the supremum of the Euclidean distance between any two possible clipped updates:
$$\Delta_{2, \text{replace}} \triangleq \sup_{D_k, D_k'} \|\bar{\Delta \mathbf{w}}_k - \bar{\Delta \mathbf{w}}_k'\|_2$$
By the triangle inequality on the closed $L_2$ ball $\mathcal{B}_2(C)$:
$$\|\bar{\Delta \mathbf{w}}_k - \bar{\Delta \mathbf{w}}_k'\|_2 \le \|\bar{\Delta \mathbf{w}}_k\|_2 + \|\bar{\Delta \mathbf{w}}_k'\|_2 \le C + C = 2C$$

#### 2.2.3 Proof of Tightness of $S = 2C$
To demonstrate that $S = 2C$ is strictly tight and cannot be reduced without additional domain constraints, consider the worst-case geometric configuration:
Let $\mathbf{u} \in \mathbb{R}^d$ be an arbitrary unit vector ($\|\mathbf{u}\|_2 = 1$).
Suppose dataset $D_k$ induces an update that saturates the clipping bound in direction $+\mathbf{u}$:
$$\Delta \mathbf{w}_k = \lambda_1 \mathbf{u} \quad (\lambda_1 \ge C) \implies \bar{\Delta \mathbf{w}}_k = C \mathbf{u}$$
Suppose alternative dataset $D_k'$ induces an update that saturates the clipping bound in the diametrically opposite direction $-\mathbf{u}$:
$$\Delta \mathbf{w}_k' = -\lambda_2 \mathbf{u} \quad (\lambda_2 \ge C) \implies \bar{\Delta \mathbf{w}}_k' = -C \mathbf{u}$$
The resulting Euclidean distance is:
$$\|\bar{\Delta \mathbf{w}}_k - \bar{\Delta \mathbf{w}}_k'\|_2 = \|C \mathbf{u} - (-C \mathbf{u})\|_2 = \|2C \mathbf{u}\|_2 = 2C \|\mathbf{u}\|_2 = 2C$$
Thus, the global $L_2$ sensitivity under replacement is strictly:
$$S_{\text{replace}} = 2C$$

#### 2.2.4 Why Replacement Sensitivity is Exactly Double Add/Remove Sensitivity
The mathematical divergence stems directly from the geometric diameter of the constraint set:
- In **Add/Remove**, one endpoint is fixed to the origin $\mathbf{0}$ (the radius of $\mathcal{B}_2(C)$ is $C$).
- In **Replacement**, both endpoints can vary freely across the entire boundary of $\mathcal{B}_2(C)$ (the diameter of $\mathcal{B}_2(C)$ is $2C$).

---

### 2.3 Systematic Comparison and Methodological Recommendation

| Dimension | Add/Remove-Client Adjacency | Replace-One-Client-Dataset Adjacency |
|:---|:---|:---|
| **Formal Definition** | $\mathcal{D}' = \mathcal{D} \setminus \{D_k\}$ (Variable $N$) | $D_k \to D_k'$, with $D_{j \neq k}$ identical (Fixed $N$) |
| **Absent Representation** | Requires explicit zero-vector injection ($\mathbf{0}$) | Not applicable (client always submits an update) |
| **Exact $L_2$ Sensitivity ($S$)** | **$S = C$** | **$S = 2C$** |
| **Noise Std Dev Required ($\sigma S$)** | $\sigma C$ | $2 \sigma C$ |
| **Privacy Interpretation** | Protects whether a client *participated* in the network | Protects the *content* of a client's private telemetry |
| **Compatibility with Fixed Simulation** | Poor: Our simulation has a fixed cohort of $N=5$ nodes | **High:** Matches the fixed 5-client cross-silo architecture |
| **FedAvg Normalization** | Complicated: Denominator shifts between $N$ and $N-1$ | **Clean:** Denominator remains constant $N = 5$ |

#### Methodological Recommendation:
We formally recommend **Replace-One-Client-Dataset Adjacency** with sensitivity bound **$S = 2C$** for the following scholarly reasons:
1. **Realistic Threat Model in Cross-Silo FL:**  
   In enterprise federated network intrusion detection, participating entities (enterprise headquarters, regional hospitals, campus datacenters) are registered, legally contracted consortia members. Their physical participation in the federated round is known to the coordinator. The legitimate privacy concern is not hiding an institution's existence, but preventing the server or peer nodes from reconstructing or inferring the **specific network traffic flows and intrusion logs** held by that institution.
2. **Structural Consistency with Fixed-Cohort Simulation:**  
   Our experimental setup features a fixed cohort ($N=5$). Replace-one adjacency preserves the invariant that exactly $N$ updates are produced and aggregated in each round.
3. **Mathematical Defensibility:**  
   Selecting $S=C$ by assuming add/remove adjacency merely to claim a smaller noise scale would introduce artificial zero-vector semantics that do not match the running code. Selecting $S=2C$ under replacement is mathematically unassailable.

---

## 3. Specification of the Local Client-Side Gaussian Mechanism

### 3.1 Step-by-Step Mathematical Formulation

Let client $i \in \{1, \dots, N\}$ possess private telemetry dataset $D_i$ at communication round $t$.
1. **Local Parameter Update Computation:**
   $$\Delta \mathbf{w}_i^{(t)} = \mathbf{w}_i^{(t)} - \mathbf{w}_{\text{global}}^{(t-1)} \in \mathbb{R}^d$$
   where $\mathbf{w}_i^{(t)}$ is the terminal weight vector obtained after $E$ local epochs of SGD on $D_i$.
2. **Complete Client Update Clipping:**
   $$\bar{\Delta \mathbf{w}}_i^{(t)} = \mathcal{C}_C\left(\Delta \mathbf{w}_i^{(t)}\right) = \Delta \mathbf{w}_i^{(t)} \cdot \min\left(1, \frac{C}{\|\Delta \mathbf{w}_i^{(t)}\|_2}\right)$$
   guaranteeing $\|\bar{\Delta \mathbf{w}}_i^{(t)}\|_2 \le C$.
3. **Local Stochastic Perturbation:**
   $$\tilde{\Delta \mathbf{w}}_i^{(t)} = \bar{\Delta \mathbf{w}}_i^{(t)} + \mathbf{n}_i^{(t)}, \quad \text{where } \mathbf{n}_i^{(t)} \sim \mathcal{N}\left(\mathbf{0}, \sigma^2 S^2 \mathbf{I}_d\right)$$
   where:
   - $C$: Clipping threshold ($C = 1.0$).
   - $S$: $L_2$ sensitivity ($S = 2C = 2.0$ under replace-one client adjacency).
   - $\sigma$: Operational noise multiplier ($\sigma \in [0.01, 0.50]$).
   - $d$: IDSNet parameter dimension ($d = 122 \times H_1 + H_1 \times H_2 + \dots$).
4. **Cryptographic Signing and Transmission:**
   Client $i$ signs the SHA-256 hash of the privatized vector $\tilde{\Delta \mathbf{w}}_i^{(t)}$ using its ECDSA private key $\text{sk}_i$:
   $$\mu_i^{(t)} = \left( i, t, \tilde{\Delta \mathbf{w}}_i^{(t)}, \text{Sign}_{\text{sk}_i}\left(\text{SHA256}\left(\tilde{\Delta \mathbf{w}}_i^{(t)}\right)\right) \right)$$
   and transmits $\mu_i^{(t)}$ upstream to the server.

---

### 3.2 Detailed Answers to Explanatory Inquiries

#### 1. Does this mechanism provide client-level privacy under the chosen assumptions?
**Yes.** Under replace-one-client adjacency, the mapping from local dataset $D_i$ to clipped update $\bar{\Delta \mathbf{w}}_i$ has global $L_2$ sensitivity bounded by $S = 2C$. Adding Gaussian noise with variance $\sigma^2 S^2 \mathbf{I}_d$ satisfies the definition of the canonical Gaussian Mechanism for client $i$'s single-round release.

#### 2. Why is noise added locally before the server receives the update?
In our adversarial threat model, the central orchestrator and/or peer validator nodes are treated as **honest-but-curious or potentially untrusted**. If client $i$ transmitted the unperturbed clipped update $\bar{\Delta \mathbf{w}}_i^{(t)}$, an eavesdropping server or malicious peer could execute gradient inversion attacks (e.g., Deep Leakage from Gradients) to reconstruct raw network flows. Adding noise locally ensures that unperturbed updates never leave the client's secure boundary.

#### 3. What information does the server observe?
The server observes:
- The privatized vector $\tilde{\Delta \mathbf{w}}_i^{(t)} = \bar{\Delta \mathbf{w}}_i^{(t)} + \mathbf{n}_i^{(t)}$.
- The client identity $i$ and round index $t$.
- The valid ECDSA signature verifying that client $i$ generated the transmission.
- Physical network metadata (timestamp, source IP, packet length).

#### 4. Does the mechanism protect the client contribution from an honest-but-curious server?
**Yes.** Because the noise is added locally prior to transmission, the server's view of client $i$'s dataset is gated by the differential privacy guarantee. The server cannot distinguish whether client $i$ trained on $D_i$ versus an adjacent dataset $D_i'$ beyond the probability ratio bounded by $(\epsilon, \delta)$.

#### 5. Can the server still observe client identities, participation, timing, or metadata?
**Yes.** The mechanism privatizes **only the parameter update payload**. It provides zero cryptographic anonymity. The server knows exactly which clients submitted updates, when they submitted, and their packet sizes.

#### 6. Why is this not automatically example-level differential privacy?
Because clipping the aggregate update vector $\Delta \mathbf{w}_i^{(t)}$ at the end of local training does not bound how much an individual training example $(x, y) \in D_i$ influenced the parameter trajectory during multi-epoch SGD. To guarantee example-level DP, per-example gradient clipping (DP-SGD) must be performed inside the SGD optimization loop.

#### 7. Why is this not automatically Local Differential Privacy in every formal interpretation?
In classical Local Differential Privacy (LDP; Duchi et al., 2013), an individual user privatizes a single data record $x_k$ before sending it to an aggregator. Here, client $i$ is an entire enterprise holding thousands of local records, training a neural network, and releasing a 122-dimensional parameter vector. While the perturbation is executed "locally" on the client device, the mathematical privacy unit is the **entire client partition**, not an isolated individual data sample.

---

## 4. Current Mandatory Terminology

Until the accountant and perturbation mechanisms are fully implemented, unit-tested, and verified against analytical composition proofs in WP2, the mechanism must be referred to strictly as:

> **Clipping-based Gaussian update perturbation (without formal privacy accounting)**

No claims of formal client-level DP, example-level DP, or LDP may be asserted.
