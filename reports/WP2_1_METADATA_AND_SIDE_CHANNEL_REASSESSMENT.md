# WP2.1 — Independent Metadata and Side-Channel Reassessment Report

**Project:** Blockchain-Assisted Privacy-Preserving Federated Learning for Network Intrusion Detection with Trust-Based Security and Cryptographic Auditing  
**Workspace:** `C:\Users\is043\.gemini\antigravity\scratch\blockchain-fl-ids`  
**Milestone:** WP2.1 — Independent Privacy Guarantee Verification  
**Audit Component:** Task E (Metadata and Side-Channel Audit)  
**Execution Mode:** STRICTLY READ-ONLY AUDIT  
**Date:** 2026-11-23  

---

## 1. Executive Summary

This report delivers a comprehensive audit of all metadata, cryptographic artifacts, validation scores, and side-channel vectors emitted by the federated learning protocol in `src/federated/`, `src/trust/`, and `src/blockchain/`.

Differential Privacy guarantees apply strictly to the outputs of the randomized mechanism. If side-channel metadata or unperturbed telemetry is transmitted alongside the privatized weights, the empirical privacy guarantee can be partially or completely compromised.

### Key Audit Findings
1. **Data Processing Inequality Protection Confirmed for Cryptographic & Ledger Artifacts:** Model hashes, ECDSA signatures, trust validation metrics, reputation scores, and blockchain transactions are computed exclusively from the already privatized weights $\widetilde{w}_k^{(t)}$ and independent server validation data. By the Data Processing Inequality (DPI), these downstream artifacts introduce zero additional privacy loss.
2. **Sample Count ($n_k$) Exposure:** Raw client dataset sizes $n_k = |D_k|$ are transmitted in the clear and used as weighting coefficients in `aggregate_fedavg`. This requires the formal privacy guarantee to operate under the **fixed partition cardinality assumption**, where partition sizes are treated as public configuration parameters.
3. **Simulation Telemetry Isolation:** The unclipped update norm `original_norm` is computed inside `ClientLevelDPMechanism` and logged in `results["dp_accounting"]`. In this simulation testbed, it resides in orchestrator memory; in a distributed production deployment, this field must be strictly retained on client edge devices and never transmitted over the network.

---

## 2. Theoretical Grounding: Data Processing Inequality

### 2.1. Theorem Formulation

Let $X \in \mathscr{D}$ represent a client's private training dataset.  
Let $\mathcal{M}: \mathscr{D} \to \mathcal{Y}$ be a randomized mechanism satisfying $(\epsilon, \delta)$-differential privacy (or $(\alpha, \epsilon_{\text{RDP}}(\alpha))$-RDP).  
Let $g: \mathcal{Y} \times \mathcal{Z}_{\text{public}} \to \mathcal{W}$ be any deterministic or randomized post-processing algorithm with access only to $\mathcal{M}(X)$ and independent/public data $Z \in \mathcal{Z}_{\text{public}}$.

Then the composed output $W = g(\mathcal{M}(X), Z)$ satisfies the identical $(\epsilon, \delta)$-DP (or RDP) guarantee as $\mathcal{M}(X)$.

### 2.2. Strict Non-Applicability Condition

If $g$ directly queries private dataset $X$ through an alternate, unperturbed pathway $g(X, \mathcal{M}(X))$, the Markov chain $X \to \mathcal{M}(X) \to W$ is broken. In that event, $W$ is **not** protected by the DP guarantee of $\mathcal{M}(X)$ and must be separately accounted for.

---

## 3. Comprehensive Field-Level Exposure Matrix

The table below catalogs every data element generated, transmitted, or logged during round execution in `src/federated/orchestrator.py`:

| Field Name | Source Code Origin | Data-Dependent? | Released To | Covered by DP? | Public / Excluded Status | Privacy Risk Level |
|:---|:---|:---:|:---:|:---:|:---|:---:|
| `weights` ($\widetilde{w}_k$) | `mechanism.py:180` | **YES** | Server, Mempool, Trust Engine | **YES (Primary)** | Direct Gaussian release ($\sigma_{\text{noise}} = 2\sigma C$) | **LOW** (Formally bounded by $(\epsilon, \delta)$) |
| `w_hash` | `orchestrator.py:544` | **YES** | Server, Blockchain Ledger | **YES (DPI)** | Deterministic SHA-256 hash of $\widetilde{w}_k$ | **NONE** |
| `sig` | `orchestrator.py:545` | **YES** | Server, Blockchain Ledger | **YES (DPI)** | ECDSA signature on `w_hash` | **NONE** |
| `sample_counts` ($n_k$) | `client.py:32` | **YES** (Dataset size) | Server, FedAvg Aggregator | **NO** | Excluded (Public fixed partition metadata) | **MODERATE** (Requires fixed size assumption) |
| `client_id` ($cid$) | `orchestrator.py:338` | **NO** | Server, Blockchain Ledger | N/A | Public federation metadata ($cid \in \{0..4\}$) | **NONE** |
| `round_num` ($r$) | `orchestrator.py:458` | **NO** | Server, Blockchain Ledger | N/A | Public sequence index | **NONE** |
| `status` | `orchestrator.py:591` | **YES** (Derived) | Blockchain Ledger | **YES (DPI)** | Server thresholding on privatized update | **NONE** |
| `reputation` | `reputation.py:50` | **YES** (Derived) | Blockchain Ledger | **YES (DPI)** | Moving average of validation reports | **NONE** |
| `validation_metrics` | `evaluator.py:80` | **YES** (Derived) | Blockchain Ledger | **YES (DPI)** | Computed on server $D_{\text{val}}$ using $\widetilde{w}_k$ | **NONE** |
| `timestamp` | `block.py:30` | **NO** | Blockchain Ledger | N/A | Execution clock timestamp | **NEGLIGIBLE** |
| `global_model_hash` | `orchestrator.py:628` | **YES** (Derived) | Blockchain Ledger | **YES (DPI)** | SHA-256 of aggregated model $w^{(t)}$ | **NONE** |
| `validator_id` | `orchestrator.py:625` | **NO** | Blockchain Ledger | **YES (DPI)** | Selected via public reputation scores | **NONE** |
| `dp_meta.original_norm` | `mechanism.py:64` | **YES** (Exact norm) | Orchestrator Memory | **NO** | Simulation Telemetry (Must NOT be transmitted) | **HIGH** if exposed; **NONE** if edge-local |
| `dp_meta.clipped_norm` | `mechanism.py:73` | **YES** (Bounded norm)| Orchestrator Memory | **YES** (Bounded by $C$) | Simulation Telemetry | **LOW** |
| `dp_summary` | `rdp_accountant.py:156`| **NO** | Experiment Results | N/A | Static hyperparameter summary | **NONE** |

---

## 4. Deep-Dive Audits of Critical Pathways

### 4.1. Sample Counts ($n_k$) and Aggregation Weights

In `src/federated/orchestrator.py` (line 549):
```python
sample_counts[client.client_id] = client.num_samples
```
And in `src/federated/aggregators.py` (lines 28–29):
```python
for w, n in zip(client_weights, sample_counts):
    weights_sum += (n / total_samples) * w
```

#### Detailed Findings:
1. **Direct Exposure:** The sample count $n_k$ is transmitted as an integer alongside the privatized weights.
2. **Impact on Adjacency:** Under standard Differential Privacy, if two adjacent datasets $\mathcal{D} \sim \mathcal{D}'$ have different cardinalities ($|D_{k^*}| \ne |D_{k^*}'|$), the server can distinguish them trivially by inspecting $n_{k^*}$, regardless of how much noise is added to $\widetilde{w}_k^*$.
3. **Formal Resolution:** The formal guarantee is mathematically valid under the **fixed partition cardinality model**, where:
   $$|D_k| = |D_k'| = n_k \quad \forall \mathcal{D} \sim_{\text{replace}} \mathcal{D}'$$
   In our research setup, data partitions are established once via Dirichlet sampling ($\text{Dir}(\alpha=0.5)$) and remained fixed across all subsequent training rounds.
4. **Production Recommendation:** In dynamic environments where dataset sizes vary over time, $n_k$ must either be protected using the Laplace mechanism ($n_k + \text{Lap}(1/\epsilon_n)$) or the federation must adopt uniform weighting ($p_k = 1/K$).

### 4.2. Trust Engine Validation Metrics & Blockchain Transactions

In `src/trust/evaluator.py`, `evaluate_updates()` receives:
- `candidate_weights`: A dictionary of privatized weights $\{\widetilde{w}_k\}$.
- `current_global_weights`: The public global model $w^{(t)}$.
- `val_data`: The server's independent, disjoint validation dataset $D_{\text{val}}$.

The trust engine computes:
1. $L_2$ update norm: $\|\widetilde{w}_k - w^{(t)}\|_2$ (function of $\widetilde{w}_k$ and $w^{(t)}$).
2. Cosine similarity: $\cos(\widetilde{w}_k - w^{(t)}, \bar{\Delta w}_{\text{ref}})$ (function of $\widetilde{w}_k$).
3. Validation loss increase: $\mathcal{L}(D_{\text{val}}; \widetilde{w}_k) - \mathcal{L}(D_{\text{val}}; w^{(t)})$ (function of server data $D_{\text{val}}$ and $\widetilde{w}_k$).

#### Finding:
Because $D_{\text{val}}$ is independent of the private client datasets $D_k$, and candidate weights are already privatized, all validation metrics, reputation scores, and blockchain transactions are pure post-processing operations. They satisfy the Markov property $D_k \to \widetilde{w}_k \to \text{Report}_k$, guaranteeing that **zero additional dataset leakage occurs**.

### 4.3. Simulation Telemetry vs. Production Deployment

In `src/privacy/mechanism.py` (lines 81–88):
```python
meta = {
    "original_norm": original_norm,
    "clipped_norm": clipped_norm,
    "clip_factor": float(clip_factor),
    "clip_norm_bound": self.clip_norm,
    "is_clipped": bool(original_norm > self.clip_norm),
    "parameter_dimension": int(flat_update.size)
}
```
In `orchestrator.py` (line 793):
```python
self.dp_accounting.append({"round": r, "dp_meta": dp_meta_round})
```

#### Finding:
`original_norm` represents the unclipped Euclidean norm of the raw gradient update $\|\Delta w_k\|_2$, which is highly sensitive. In the current repository, this metadata is logged solely in orchestrator memory for experimental visualization and audit dashboards.
- **Audit Requirement:** In any physical distributed deployment (where clients run on edge hardware and communicate via RPC/REST to the server), `dp_meta` must remain on the edge device and must be stripped from the network transmission payload.

---

## 5. Audit Verdict

| Side-Channel / Metadata Channel | DPI Protection Status | Mitigation / Assumption Required | Status |
|:---|:---:|:---|:---:|
| Digital Signatures (ECDSA) | Fully Protected | Signed payload is $\text{SHA-256}(\widetilde{w}_k)$ | **VERIFIED** |
| Blockchain Ledger Records | Fully Protected | Transactions record hashes of privatized weights | **VERIFIED** |
| Trust & Reputation Metrics | Fully Protected | Evaluated on server $D_{\text{val}}$ using privatized weights | **VERIFIED** |
| Client Sample Counts ($n_k$) | Not Covered by DP | Restricted to fixed/public partition cardinality | **QUALIFIED** |
| Update Norm Telemetry | Not Covered by DP | Must remain edge-local in distributed deployments | **RESTRICTED** |

**Task E Verdict:** **PASS WITH RESTRICTIONS** (Data Processing Inequality holds for all released cryptographic and validation artifacts; sample sizes are restricted to fixed public metadata).
