# WP2.1 — Formal Client-Level Privacy Mechanism Implementation Report

**Project:** Blockchain-Assisted Privacy-Preserving Federated Learning for Network Intrusion Detection with Trust-Based Security and Cryptographic Auditing  
**Workspace:** `C:\Users\is043\.gemini\antigravity\scratch\blockchain-fl-ids`  
**Milestone:** WP2 — Formal Client-Level Privacy Mechanism & Accounting  
**Deliverable:** WP2.1 Mechanism Implementation Report  
**Date:** 2026-11-23  

---

## 1. Executive Summary

This report provides the formal mathematical specification, architectural design, and implementation documentation for the client-level Differential Privacy (DP) mechanism developed in Work Package 2 (WP2). 

The mechanism replaces heuristic absolute-weight perturbation with a mathematically sound client-level privacy framework built upon:
1. **Replace-one-client-dataset adjacency** ($\mathcal{D} \sim_{\text{replace}} \mathcal{D}'$) over a federation of $K = 5$ nodes.
2. **Complete client update vector L2-norm clipping** bounded strictly by threshold $C > 0$.
3. **Provable global L2 sensitivity** $S = 2C$.
4. **Calibrated Gaussian perturbation** with variance $\sigma_{\text{noise}}^2 I_d = 4\sigma^2 C^2 I_d$ (standard deviation $\sigma_{\text{noise}} = 2\sigma C$).
5. **Exact model weight reconstruction** $\widetilde{w}_k^{(t)} = w^{(t)} + \widetilde{\Delta w}_k^{(t)}$ preserving end-to-end compatibility with downstream trust verification, cryptographic signing, and blockchain auditing.

All components have been implemented in `src/privacy/mechanism.py`, integrated into `src/federated/orchestrator.py`, and verified against 25 unit and integration tests.

---

## 2. Mathematical Specification

### 2.1. Client-Level Adjacency Relation

In federated learning for Network Intrusion Detection, network nodes (clients) train on local traffic flow partitions. Protecting individual packet flows or records is insufficient if an attacker can infer an entire enterprise's participation or presence. Therefore, we formalize privacy at the **client dataset** granularity.

Let the global federation dataset be partitioned across $K$ fixed clients:
$$\mathcal{D} = (D_1, D_2, \dots, D_K)$$
Two federated datasets $\mathcal{D}, \mathcal{D}' \in \mathscr{D}^K$ are **replace-one-client adjacent** ($\mathcal{D} \sim_{\text{replace}} \mathcal{D}'$) if and only if they differ by at most one client's entire training dataset:
$$\mathcal{D} \sim_{\text{replace}} \mathcal{D}' \iff \exists ! k^* \in \{1, \dots, K\} \text{ s.t. } D_{k^*} \ne D_{k^*}' \quad \text{and} \quad \forall j \ne k^*, D_j = D_j'$$

### 2.2. Complete Client Update Vector Definition

At communication round $t$, each client $k \in \{1, \dots, K\}$ receives the global model parameter vector $w^{(t)} \in \mathbb{R}^d$. The client runs local Stochastic Gradient Descent (SGD) on private dataset $D_k$ for $E = 1$ epoch, yielding updated parameters $w_k^{(t)}$.

The client's **model update vector** represents the parameter difference:
$$\Delta w_k^{(t)} = w_k^{(t)} - w^{(t)} \in \mathbb{R}^d$$
Applying privacy to the update vector $\Delta w_k^{(t)}$ rather than absolute weights $w_k^{(t)}$ is essential: absolute weights incorporate the public broadcast vector $w^{(t)}$, whose norm grows with model initialization and depth. Perturbing absolute weights unnecessarily injects variance proportional to $\|w^{(t)}\|_2$ rather than the localized training progress $\|\Delta w_k^{(t)}\|_2$.

### 2.3. Complete Vector L2 Clipping Operator

To ensure bounded sensitivity regardless of client data distribution or loss landscape, the mechanism projects the entire flattened update vector $\Delta w_k^{(t)}$ onto the L2-ball of radius $C > 0$:

$$\bar{\Delta w}_k^{(t)} = \Pi_C\left(\Delta w_k^{(t)}\right) = \Delta w_k^{(t)} \cdot \min\left(1, \frac{C}{\|\Delta w_k^{(t)}\|_2}\right)$$

Where:
- $\|\Delta w_k^{(t)}\|_2 = \sqrt{\sum_{i=1}^d (\Delta w_{k,i}^{(t)})^2}$ is the standard Euclidean norm across all $d$ model parameters.
- If $\|\Delta w_k^{(t)}\|_2 \le C$, the update is preserved identically: $\bar{\Delta w}_k^{(t)} = \Delta w_k^{(t)}$.
- If $\|\Delta w_k^{(t)}\|_2 > C$, the update is scaled strictly to norm $C$, preserving exact vector direction (cosine similarity $= 1.0$).
- If $\|\Delta w_k^{(t)}\|_2 = 0$, $\bar{\Delta w}_k^{(t)} = \mathbf{0}$.

### 2.4. Global L2 Sensitivity Derivation

Let $f_t: \mathscr{D} \to \mathbb{R}^d$ denote the client update function mapping a client dataset $D_k$ to the clipped update vector $\bar{\Delta w}_k^{(t)}$ given global model $w^{(t)}$.

For any two adjacent datasets $\mathcal{D} \sim_{\text{replace}} \mathcal{D}'$ differing on client $k^*$:
- For all unaffected clients $j \ne k^*$, $D_j = D_j' \implies \bar{\Delta w}_j^{(t)} = \bar{\Delta w}_j'^{(t)}$, so the difference is zero.
- For the substituted client $k^*$, the two clipped updates satisfy $\|\bar{\Delta w}_{k^*}^{(t)}\|_2 \le C$ and $\|\bar{\Delta w}_{k^*}'^{(t)}\|_2 \le C$.

Applying the triangle inequality:
$$S = \sup_{\mathcal{D} \sim_{\text{replace}} \mathcal{D}'} \left\| f_t(\mathcal{D}) - f_t(\mathcal{D}') \right\|_2 = \sup_{D_{k^*}, D_{k^*}'} \left\| \bar{\Delta w}_{k^*}^{(t)} - \bar{\Delta w}_{k^*}'^{(t)} \right\|_2 \le \left\| \bar{\Delta w}_{k^*}^{(t)} \right\|_2 + \left\| \bar{\Delta w}_{k^*}'^{(t)} \right\|_2 \le C + C = 2C$$

> [!IMPORTANT]
> **Sensitivity is Strictly $S = 2C$**: Under replace-one adjacency, replacing $D_{k^*}$ with $D_{k^*}'$ can reverse the trajectory of the client update, achieving worst-case separation of opposite boundary vectors of norm $C$, giving $\|C\mathbf{u} - (-C\mathbf{u})\|_2 = 2C$. Any claim that $S = C$ under replace-one adjacency is mathematically invalid and underestimates privacy loss by a factor of 4.

### 2.5. Calibrated Gaussian Perturbation

To guarantee $(\alpha, \epsilon_{\text{RDP}}(\alpha))$-Rényi Differential Privacy, independent zero-mean Gaussian noise is added to the clipped update vector:
$$n_k^{(t)} \sim \mathcal{N}\left(0, \sigma_{\text{noise}}^2 I_d\right)$$
Where the noise standard deviation is scaled to the global sensitivity $S = 2C$ via the noise multiplier parameter $\sigma \ge 0$:
$$\sigma_{\text{noise}} = S \cdot \sigma = 2\sigma C$$
The privatized update vector is:
$$\widetilde{\Delta w}_k^{(t)} = \bar{\Delta w}_k^{(t)} + n_k^{(t)}$$

### 2.6. Model Weight Reconstruction

The client reconstructs privatized absolute model weights before transmission:
$$\widetilde{w}_k^{(t)} = w^{(t)} + \widetilde{\Delta w}_k^{(t)} = w^{(t)} + \bar{\Delta w}_k^{(t)} + n_k^{(t)}$$
This guarantees that the server and downstream pipeline receive model weights $\widetilde{w}_k^{(t)}$ of standard dimensionality, requiring zero modification to server aggregation functions (`FedAvg`, `TrimmedMean`, `CoordinateMedian`, `MultiKrum`).

---

## 3. Module Architecture: `src/privacy/mechanism.py`

The core privacy mechanism is implemented in `ClientLevelDPMechanism` in `src/privacy/mechanism.py`.

```
src/privacy/
├── __init__.py           # Exports ClientLevelDPMechanism, RDPAccountant, DEFAULT_RDP_ORDERS
├── mechanism.py          # Complete vector L2 clipping, Gaussian perturbation, weight privatization
├── rdp_accountant.py     # Rényi Differential Privacy tracking, discrete-order optimization
└── differential.py       # Legacy LocalDifferentialPrivacy retained for regression compatibility
```

### 3.1. Class Interface and Method Contract

```python
class ClientLevelDPMechanism:
    def __init__(self, clip_norm: float = 1.0, noise_multiplier: float = 0.01, seed: Optional[int] = None)
    def clip_update(self, update_vector: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]
    def perturb_update(self, clipped_update: np.ndarray, seed: Optional[int] = None) -> Tuple[np.ndarray, Dict[str, Any]]
    def privatize_update(self, update_vector: np.ndarray, seed: Optional[int] = None) -> Tuple[np.ndarray, Dict[str, Any]]
    def privatize_client_weights(self, local_weights: np.ndarray, global_weights: np.ndarray, seed: Optional[int] = None) -> Tuple[np.ndarray, Dict[str, Any]]
```

### 3.2. Detailed Implementation Logic

1. **Initialization (`__init__`)**:
   - Validates that `clip_norm` is a positive, finite, real float ($C > 0$).
   - Validates that `noise_multiplier` is a non-negative, finite, real float ($\sigma \ge 0$).
   - Computes sensitivity $S = 2.0 \times C$ and standard deviation $\sigma_{\text{noise}} = S \times \sigma = 2.0 \times \sigma \times C$.

2. **Clipping (`clip_update`)**:
   - Flattens the input array into a contiguous 1D array.
   - Enforces finite value checks (`np.all(np.isfinite(...))`); immediately raises `ValueError` if NaN or Inf values are encountered.
   - Computes Euclidean norm $L_2 = \sqrt{\sum v_i^2}$.
   - If $L_2 == 0$, returns a zero vector without division.
   - If $L_2 > 0$, scales by $\min(1, C / L_2)$.
   - **Numerical Projection Safeguard**: Due to IEEE 754 float32 rounding, $(\Delta w / \text{factor})$ can occasionally produce a norm of $C \times (1 + 10^{-7})$. If the computed norm exceeds $C \times (1 + 10^{-5})$, the vector is projected exactly: $v \leftarrow v \times (C / \|v\|_2)$.
   - Returns both the clipped array and a telemetry dictionary containing `original_norm`, `clipped_norm`, `clip_factor`, `is_clipped`, and `parameter_dimension`.

3. **Gaussian Perturbation (`perturb_update`)**:
   - Validates that the clipped input is finite.
   - Draws independent Gaussian noise from $\mathcal{N}(0, \sigma_{\text{noise}}^2)$ of dimension $d$.
   - Supports isolated deterministic seeding via `np.random.RandomState(seed)` for unit testing and reproducibility without polluting global PRNG state.

4. **Weight Privatization (`privatize_client_weights`)**:
   - Verifies that `local_weights` and `global_weights` have matching shapes.
   - Computes local update $\Delta w = w_{\text{local}} - w_{\text{global}}$.
   - Executes `privatize_update(delta_w, seed)`.
   - Reconstructs $\widetilde{w} = w_{\text{global}} + \widetilde{\Delta w}$.
   - Telemetry includes all clipping and noise properties plus `final_perturbed_weights_norm`.

---

## 4. Integration into Federated Orchestrator

The mechanism integrates directly into the federated execution loop of `src/federated/orchestrator.py`:

```mermaid
flowchart TD
    A[Start Round t] --> B[Server Broadcasts w^t]
    B --> C[Client k Runs Local Training -> w_k^t]
    C --> D[Compute Update: Δw_k^t = w_k^t - w^t]
    D --> E[ClientLevelDPMechanism.privatize_client_weights]
    E --> F[Output: Perturbed Weights ~w_k^t]
    F --> G[Client Signs Model Hash: ECDSA.sign]
    G --> H[Transmit ~w_k^t + Sig + n_k to Server]
    H --> I[Server Verifies ECDSA Signature on ~w_k^t]
    I --> J[Trust Engine Evaluates Validation Metrics on ~w_k^t]
    J --> K[Blockchain Ledger Commits Transaction Hash of ~w_k^t]
    K --> L[Aggregation: FedAvg/Median on ~w_k^t]
    L --> M[RDPAccountant.step: Record Round Release]
    M --> N[Updated Global Model w^{t+1}]
```

### Key Integration Properties:
1. **Isolated Execution**: When `dp_enabled=True` in the configuration, `orchestrator.setup()` initializes `self.dp_mechanism = ClientLevelDPMechanism(...)` and `self.rdp_accountant = RDPAccountant()`.
2. **Deterministic Seed Routing**: Client DP perturbation uses `client_dp_seed = (self.seed * 1000) + (r * 100) + cid`, guaranteeing independent draws across clients and rounds while ensuring bit-for-bit test reproducibility.
3. **End-of-Round Summary**: The final results dictionary returned by `orchestrator.run()` includes `dp_summary` containing the complete RDP spectrum, optimal $\epsilon(\delta)$, and formal limitation notes.
4. **Baseline Invariance**: When `dp_enabled=False`, `self.dp_mechanism` and `self.rdp_accountant` remain `None`, and zero overhead or modification is applied, preserving baseline behavior.

---

## 5. Verification and Validation

The implementation was verified through `tests/test_wp2_privacy.py`, covering:
- Zero vector preservation ($\|v\|_2 = 0 \implies \bar{v} = \mathbf{0}$).
- Under-norm preservation ($\|v\|_2 < C \implies \bar{v} = v$).
- Exact-norm preservation ($\|v\|_2 = C \implies \bar{v} = v$).
- Over-norm clipping ($\|v\|_2 = 5.0, C = 1.5 \implies \|\bar{v}\|_2 = 1.5$, cosine similarity $= 1.0$).
- Extreme-norm scaling ($\|v\|_2 = 10^6 \implies \|\bar{v}\|_2 \le C$).
- Rejection of NaN and Inf arrays with `ValueError`.
- Parameter boundary validation ($C \le 0, \sigma < 0$).
- Empirical noise standard deviation verification ($M = 2000$ draws, empirical std matches $2\sigma C$ within $3\sigma / \sqrt{2M}$).
- Empirical inter-coordinate independence (maximum pairwise correlation $|r| < 0.12$).
- Seed reproducibility (identical seed $\implies$ identical array, distinct seed $\implies$ distinct array).

**Verification Result:** All 25 unit and integration tests passed cleanly.
