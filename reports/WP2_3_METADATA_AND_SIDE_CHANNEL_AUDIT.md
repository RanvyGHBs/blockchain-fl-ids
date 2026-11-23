# WP2.3 — Metadata & Side-Channel Privacy Audit

**Project:** Blockchain-Assisted Privacy-Preserving Federated Learning for Network Intrusion Detection with Trust-Based Security and Cryptographic Auditing  
**Workspace:** `C:\Users\is043\.gemini\antigravity\scratch\blockchain-fl-ids`  
**Milestone:** WP2 — Formal Client-Level Privacy Mechanism & Accounting  
**Phase:** Phase 3 — Metadata and Side-Channel Review  
**Date:** 2026-11-23  

---

## 1. Executive Summary

This audit systematically reviews every field, header, metric, and telemetry record produced across the federated learning lifecycle, trust engine, reputation system, and blockchain ledger. The objective is to determine whether auxiliary data releases could leak client information or compromise the formal **Client-Level Differential Privacy** guarantee.

### Key Classifications
- **Primary Protected Release:** The perturbed model update vector $\widetilde{\Delta w}_k^{(t)}$ (and reconstructed perturbed weights $\widetilde{w}_k^{(t)} = w^{(t)} + \widetilde{\Delta w}_k^{(t)}$) is directly protected under the Client-Level Gaussian Mechanism with sensitivity $S = 2C$ and RDP accountant.
- **Post-Processing Invariance:** By the **Data Processing Inequality (DPI)**, digital signatures, hashes, validation metrics, reputation transitions, and ledger commitments computed strictly from $\widetilde{w}_k^{(t)}$ and independent validation data $D_{\text{val}}$ introduce zero privacy degradation.
- **Explicit Metadata Restriction:** Client partition cardinalities ($n_k$) and client identifiers ($k \in \{0, \dots, 4\}$) are fixed structural properties of the 5-client Dirichlet partition benchmark. The formal privacy guarantee applies under the condition that replacement datasets preserve cardinality ($|D'_k| = |D_k| = n_k$).

---

## 2. Complete Field-by-Field Privacy Classification

We evaluate every field released in the system under the five mandated classification categories:
1. **Public and fixed:** Independent of any client's training data.
2. **Public but data-dependent:** Potentially correlated with client training data.
3. **Private and not released:** Kept strictly in client local memory.
4. **Released and included in privacy analysis:** Covered directly by the Gaussian DP mechanism or the Data Processing Inequality.
5. **Unresolved:** Requires further theoretical calibration.

### Comprehensive Field Matrix

| Field / Record Name | Emitting Component | Destination / Scope | Classification Category | Privacy Impact & Mathematical Justification |
| :--- | :--- | :--- | :---: | :--- |
| **Raw Packet Records ($X_k, y_k$)** | Client Local Storage | Client RAM only | **3. Private and not released** | Never transmitted or serialized. 100% data sovereignty. |
| **Raw Gradient Updates ($\nabla F_k$)** | Client Training Loop | Client RAM only | **3. Private and not released** | Computed during backpropagation; discarded after parameter update. |
| **Unperturbed Update ($\Delta w_k$)** | Client Local State | Client RAM only | **3. Private and not released** | Kept strictly on client; never transmitted to server. |
| **Pre-Clipping Norm ($\|\Delta w_k\|_2$)** | Client Clipping Step | Client RAM only | **3. Private and not released** | Internal scalar used to compute clip factor; not broadcast. |
| **Post-Clipping Norm ($\|\bar{\Delta w}_k\|_2$)** | Client Clipping Step | Client RAM only | **3. Private and not released** | Internal scalar; never transmitted to server or ledger. |
| **Perturbed Update ($\widetilde{\Delta w}_k$)** | Client DP Mechanism | Client $\to$ Server | **4. Released & Included in Analysis** | **Primary Protected Quantity.** Satisfies $(\alpha, \frac{\alpha}{2\sigma^2})$-RDP per round. |
| **Perturbed Weights ($\widetilde{w}_k$)** | Client DP Mechanism | Client $\to$ Server | **4. Released & Included in Analysis** | $\widetilde{w}_k = w^{(t)} + \widetilde{\Delta w}_k$. Shift by public vector $w^{(t)}$ preserves DP. |
| **Model Weight Hash ($\text{SHA256}(\widetilde{w}_k)$)** | Client / Transaction | Server / Blockchain | **4. Released & Included in Analysis** | Protected by DPI. Deterministic collision-resistant hash of private release. |
| **ECDSA P-256 Signature ($\sigma_{\text{sig}}$)** | Client Signing Key | Server / Blockchain | **4. Released & Included in Analysis** | Protected by DPI. Authenticates $\text{SHA256}(\widetilde{w}_k)$ without revealing raw data. |
| **Client Sample Count ($n_k$)** | Client Metadata | Server Aggregation | **1. Public and fixed** | Fixed by Dirichlet partition configuration ($n_0=24994, \dots$). Cardinality assumed invariant. |
| **Client Identifier ($k \in \{0..4\}$)** | Client Metadata | Server / Blockchain | **1. Public and fixed** | Fixed structural index of the simulated network nodes. |
| **Round Number ($t \in \{1..T\}$)** | Orchestrator | Server / Blockchain | **1. Public and fixed** | Public orchestration counter. |
| **Global Model Weights ($w^{(t)}$)** | Server Coordinator | Broadcast to Clients | **4. Released & Included in Analysis** | Aggregate of differentially private client releases. Protected by DPI. |
| **Tier-1 Norm Metric ($\|\widetilde{w}_k\|_2$)** | Server Trust Engine | Transaction Report | **4. Released & Included in Analysis** | Computed directly on perturbed vector $\widetilde{w}_k$. Protected by DPI. |
| **Tier-2 Cosine Metric ($\cos(\widetilde{w}_k, \widetilde{w}_{\text{med}})$)** | Server Trust Engine | Transaction Report | **4. Released & Included in Analysis** | Computed directly on perturbed vectors. Protected by DPI. |
| **Tier-3 Loss Delta ($\Delta \mathcal{L}_k$)** | Server Trust Engine | Transaction Report | **4. Released & Included in Analysis** | Evaluated on independent server benchmark $D_{\text{val}}$ using $\widetilde{w}_k$. Protected by DPI. |
| **Reputation Transition ($R_{t+1}$)** | Server Reputation Mgr | Transaction / Ledger | **4. Released & Included in Analysis** | Deterministic function of validation metrics ($+0.05 / -0.35$). Protected by DPI. |
| **Quarantine Decisions** | Server Reputation Mgr | Server / Blockchain | **4. Released & Included in Analysis** | Threshold decision on $R_{t+1} < 0.40$. Protected by DPI. |
| **Previous Block Hash Pointer** | Blockchain Header | Public Ledger | **1. Public and fixed** | Cryptographic chaining of prior block header. |
| **Merkle Root Digest** | Blockchain Header | Public Ledger | **4. Released & Included in Analysis** | Binary SHA-256 tree of transaction digests. Protected by DPI. |
| **Validator Client ID** | Proof-of-Trust Engine | Block Header | **4. Released & Included in Analysis** | Selected via reputation scores derived from private releases. Protected by DPI. |

---

## 3. Detailed Side-Channel & Leakage Analysis

### 3.1 Cryptographic Signatures and Hashing
A common misconception in applied privacy research is assuming that encryption, digital signing, or cryptographic hashing provides differential privacy. 
- **Analysis:** Hashing does not introduce statistical entropy or noise. However, because ECDSA signing and SHA-256 hashing are applied strictly **after** the Gaussian perturbation step to the already-perturbed weight vector $\widetilde{w}_k^{(t)}$, the **Data Processing Inequality** guarantees that computing a signature or hash digest cannot increase the mutual information between the raw dataset $D_k$ and the released transcript.
- **Verification:** The client private signing key $sk_k$ is never exposed on-chain. The public verification key $pk_k$ is static and independent of training data.

### 3.2 Client Sample Counts ($n_k$) and Aggregation Weights
In standard FedAvg aggregation, client contributions are weighted proportionally to their sample counts:
$$p_k = \frac{n_k}{\sum_{j} n_j}$$
- **Leakage Potential:** If a client could submit an arbitrary dataset with arbitrary size $n'_k \neq n_k$, the value of $n_k$ could reveal auxiliary data-dependent properties.
- **Audit Boundary Specification:** In the NSL-KDD benchmark, sample partitions $n_k$ are determined prior to federated training by the Dirichlet partitioner ($\alpha=0.5, \text{seed}=42$).
- **Formal Guarantee Scope:** Under our replace-one-client-dataset adjacency ($\mathcal{D} \sim_{\text{replace}} \mathcal{D}'$), the replaced client dataset $D'_k$ is constrained to have identical cardinality $|D'_k| = |D_k| = n_k$. Under this definition, $n_k$ is a public fixed constant that transmits zero differential information. If variable-cardinality datasets were permitted, $n_k$ would need to be sanitized or uniform weighting ($p_k = 1/K$) would need to be enforced.

### 3.3 Multi-Criteria Trust Filter & Reputation State
- **Tier 1 (L2 Norm):** Uses $\|\widetilde{w}_k\|_2$. Because $\widetilde{w}_k$ is already differentially private, its L2 norm is a post-processed scalar.
- **Tier 2 (Cosine Consensus):** Evaluates cosine similarity between $\widetilde{w}_k$ and the median of all perturbed submissions $\widetilde{w}_{\text{med}}$. This is a post-processing function of the private releases.
- **Tier 3 (Validation Loss Delta):** Evaluates cross-entropy loss of model $\widetilde{w}_k$ on the server validation slice $D_{\text{val}}$. Because $D_{\text{val}}$ was derived during initial dataset splitting via strict 3-way isolation (prior to client partitioning), $D_{\text{val}} \cap D_k = \emptyset$. The validation loss delta is purely a function of $\widetilde{w}_k$ and independent data $D_{\text{val}}$.
- **Reputation and Quarantine Decisions:** Because reputation transitions ($R_k \to R_k + 0.05$ or $R_k - 0.35$) and quarantine state ($R_k < 0.40$) are deterministic functions of the Tier 1–3 validation outputs, they are valid post-processing operations.

### 3.4 Internal Telemetry and Audit Logging
- **Inspection of `FederatedOrchestrator`:** The orchestrator records metadata in `self.dp_accounting`, `self.round_logs`, and `self.cumulative_accounting`.
- **Sanitization Check:**
  - `original_norm` (pre-clipping norm) is logged internally in `dp_meta` for debugging and local testing.
  - **Requirement:** `original_norm` must remain strictly local to client debug structures and must never be committed to blockchain transactions or transmitted to peer clients.
  - In `src/federated/orchestrator.py`, transactions committed to the blockchain (`Transaction(...)`) store only `weights_hash`, `signature`, `validation_metrics`, and reputation values. They do not store `original_norm`.

---

## 4. Formal Scope & Guarantee Boundary Statement

To ensure complete scientific integrity, all research reporting and documentation must explicitly delineate the scope of the privacy guarantee:

> **Formal Privacy Guarantee Boundary:**  
> The $(\epsilon, \delta)$-differential privacy guarantee established in WP2 applies strictly to the sequence of client model update releases $\{\widetilde{\Delta w}_k^{(t)}\}_{k=0, t=1}^{K-1, T}$ under **replace-one-client-dataset adjacency** with fixed client partition cardinalities $|D_k| = n_k$.  
> All published blockchain hashes, digital signatures, validation metrics, reputation scores, and global model broadcasts are protected as post-processing transformations under the Data Processing Inequality.  
> The guarantee does not cover variable-cardinality dataset substitutions where $|D'_k| \neq |D_k|$.

---

## 5. Audit Recommendations & Checklist for Phase 4

1. **Verify No Raw Update Leakage:** Ensure that in `src/federated/orchestrator.py`, `client.get_local_weights()` is replaced by or encapsulated inside the DP mechanism before weights are passed to the server or trust engine.
2. **Signature Binding:** Ensure that the ECDSA signature authenticates the hash of the *perturbed* weights $\widetilde{w}_k$, not the unperturbed weights.
3. **Transaction Binding:** Ensure that the blockchain transaction records the hash of the *perturbed* weights $\widetilde{w}_k$.
4. **Accountant Synchronization:** Ensure that the RDP accountant records privacy steps only when a round executes and releases perturbed updates.
