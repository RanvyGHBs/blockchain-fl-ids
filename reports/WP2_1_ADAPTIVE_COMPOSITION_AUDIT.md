# WP2.1 — Independent Adaptive Multi-Round Composition Audit Report

**Project:** Blockchain-Assisted Privacy-Preserving Federated Learning for Network Intrusion Detection with Trust-Based Security and Cryptographic Auditing  
**Workspace:** `C:\Users\is043\.gemini\antigravity\scratch\blockchain-fl-ids`  
**Milestone:** WP2.1 — Independent Privacy Guarantee Verification  
**Audit Component:** Task D (Adaptive Multi-Round Composition Audit)  
**Execution Mode:** STRICTLY READ-ONLY AUDIT  
**Date:** 2026-11-23  

---

## 1. Executive Summary

This report delivers the independent technical audit of the adaptive multi-round composition claim for the client-level Differential Privacy mechanism in federated learning.

In federated learning, each round's query (the global model $w^{(t)}$) is an adaptive function of all prior client updates. If the sensitivity of round $t$ depended on the data-dependent model trajectory, standard linear composition would break down.

The audit team investigated the exact execution loop in `src/federated/orchestrator.py` (`_run_round`) to verify whether:
1. The global model is a valid post-processing of previous private outputs.
2. The conditional sensitivity of each client's update at round $t$ is strictly bounded by $2C$ given any past history.
3. Fresh, independent Gaussian noise is generated at each round.
4. Privacy accounting covers all adaptive releases without omissions or double-counting.

### Key Audit Finding
**The adaptive composition claim is mathematically valid under clearly documented operational restrictions.** The mechanism applies unconditional $L_2$-norm clipping to the client update vector $\Delta w_k^{(t)} = w_k^{(t)} - w^{(t)}$ prior to perturbation. Because this projection guarantees $\|\bar{\Delta w}_k^{(t)}\|_2 \le C$ regardless of the parameter state $w^{(t)}$, the conditional sensitivity $S_t \le 2C$ holds unconditionally on every past transcript $\mathcal{T}_{<t}$.

---

## 2. Analysis of the 10 Core Architectural Questions

### 2.1. Is the global model at round $t$ a post-processing of previously privatized outputs?
**VERIFIED: YES.**  
At the end of round $t-1$, the server computes $w^{(t)}$ by applying aggregation (`FedAvg`, `TrimmedMean`, `Median`, or `TrustWeighted`) to the set of accepted client updates $\{\widetilde{w}_k^{(t-1)}\}$. Each accepted update is a function of the privatized update vector $\widetilde{\Delta w}_k^{(t-1)}$. By the Data Processing Inequality, $w^{(t)}$ contains no private dataset information beyond what was already released through the Gaussian DP mechanisms of rounds $1, \dots, t-1$.

### 2.2. Does the next client update depend on the previous private transcript?
**VERIFIED: YES.**  
In `src/federated/orchestrator.py` (line 480):
```python
client.set_global_weights(current_global_weights)
client.local_train(...)
```
Client $k$ initializes local SGD from $w^{(t)}$. Therefore, the unclipped parameter state $w_k^{(t)}$ and the raw difference $\Delta w_k^{(t)} = w_k^{(t)} - w^{(t)}$ depend directly on the past privatized transcript $\mathcal{T}_{<t}$.

### 2.3. Is the Gaussian mechanism's conditional sensitivity still bounded by $2C$?
**VERIFIED: YES.**  
Let $\mathcal{T}_{<t} = (\widetilde{w}^{(1)}, \dots, \widetilde{w}^{(t-1)})$ be any realized transcript of previous rounds, fixing the broadcast model $w^{(t)}$.
For any two adjacent datasets $D_{k^*}, D_{k^*}'$:
- The client computes updates $\Delta w_{k^*}^{(t)}$ and $\Delta w_{k^*}'^{(t)}$.
- The mechanism applies $L_2$ clipping:
  $$\bar{\Delta w}_{k^*}^{(t)} = \Pi_C\left(\Delta w_{k^*}^{(t)}\right) \implies \left\|\bar{\Delta w}_{k^*}^{(t)}\right\|_2 \le C$$
  $$\bar{\Delta w}_{k^*}'^{(t)} = \Pi_C\left(\Delta w_{k^*}'^{(t)}\right) \implies \left\|\bar{\Delta w}_{k^*}'^{(t)}\right\|_2 \le C$$
- Applying the triangle inequality:
  $$\left\| \bar{\Delta w}_{k^*}^{(t)} - \bar{\Delta w}_{k^*}'^{(t)} \right\|_2 \le \left\| \bar{\Delta w}_{k^*}^{(t)} \right\|_2 + \left\| \bar{\Delta w}_{k^*}'^{(t)} \right\|_2 \le C + C = 2C$$

Because clipping is an unconditional projection onto the closed Euclidean ball $\mathcal{B}_2(C)$, this bound holds for **every** $w^{(t)} \in \mathbb{R}^d$ and **every** transcript $\mathcal{T}_{<t}$. The sensitivity never expands beyond $2C$.

### 2.4. Is the clipping bound applied independently in every round?
**VERIFIED: YES.**  
`privatize_client_weights` is called inside the round loop `for r in range(1, num_rounds + 1)` for every active participant.

### 2.5. Does each round use fresh Gaussian randomness?
**VERIFIED: YES.**  
At each round $r$ and client $cid$, `client_dp_seed` is updated via:
$$\text{seed}_{r, cid} = (\text{base\_seed} \times 10007 + r \times 997 + cid \times 101) \pmod{2^{31} - 1}$$
Independent pseudo-random draws are generated per dimension, preventing cross-round noise cancellation attacks.

### 2.6. Are the privacy parameters fixed or data-dependent?
**VERIFIED: FIXED.**  
The clipping threshold $C$, noise multiplier $\sigma$, target failure probability $\delta$, and Rényi orders $\mathcal{A}_{\text{orders}}$ are static configuration constants chosen prior to training and never adapted based on dataset characteristics or intermediate training losses.

### 2.7. Does the server receive individual perturbed updates or only the aggregate?
**VERIFIED: INDIVIDUAL PERTURBED UPDATES.**  
In this architecture, the server receives individual updates $\widetilde{w}_k^{(t)}$ to verify individual ECDSA signatures and execute multi-criteria trust evaluation.  
Consequently, **no shuffling or aggregation amplification factor ($q = 1/K$) is claimed**. The privacy accounting correctly treats each release as a full-participation direct Gaussian mechanism ($q = 1.0$).

### 2.8. Can clients observe other clients' private metadata?
**VERIFIED: NO.**  
Network topology is a strict star network (client-to-server). Clients communicate exclusively with the coordinator and receive only the aggregated global model $w^{(t)}$. No peer-to-peer side-channels exist.

### 2.9. Are any intermediate unperturbed values exposed?
**VERIFIED: NO NETWORK EXPOSURE (SIMULATION TELEMETRY NOTED).**  
Tracing the network payload confirms that only privatized weights $\widetilde{w}_k^{(t)}$ and their digital signatures are submitted. The unclipped norm `original_norm` is recorded in `dp_meta_round` within orchestrator memory for debugging/logging, but is never serialized into blockchain transactions or transmitted to peer clients.

### 2.10. Does the accountant cover all adaptive releases?
**VERIFIED: YES.**  
`self.rdp_accountant.step(noise_multiplier=self.dp_noise_multiplier, clip_norm=self.dp_clip_norm, rounds=1)` is executed at Step D of every communication round, ensuring 1:1 correspondence between executed federated rounds and accounted privacy steps.

---

## 3. Mathematical Justification of Sequential RDP Composition

### 3.1. Formal Theorem (Mironov, 2017)

Let $\mathcal{M}_1: \mathscr{D} \to \mathcal{Y}_1$ satisfy $(\alpha, \epsilon_1(\alpha))$-RDP.  
For $t = 2, \dots, T$, let $\mathcal{M}_t: \mathscr{D} \times \mathcal{Y}_1 \times \dots \times \mathcal{Y}_{t-1} \to \mathcal{Y}_t$ be an adaptive mechanism such that for every fixed history $y_{<t} = (y_1, \dots, y_{t-1})$, the conditional mechanism $\mathcal{M}_t(\cdot, y_{<t})$ satisfies $(\alpha, \epsilon_t(\alpha))$-RDP.  
Then the composed mechanism $\mathcal{M}_{1:T}(\mathcal{D}) = (\mathcal{M}_1(\mathcal{D}), \dots, \mathcal{M}_T(\mathcal{D}, \mathcal{M}_{<T}(\mathcal{D})))$ satisfies:

$$\epsilon_{\text{RDP}}^{(T)}(\alpha) \le \sum_{t=1}^T \epsilon_t(\alpha)$$

### 3.2. Application to Our Architecture

In our system:
- At round $t$, the query function is $f_t(D_k; w^{(t)}) = \Pi_C(w_k^{(t)} - w^{(t)})$.
- Conditioned on $w^{(t)}$, the global $L_2$ sensitivity is $S_t = \sup_{D_{k^*}, D_{k^*}'} \|\Pi_C(\Delta w_{k^*}^{(t)}) - \Pi_C(\Delta w_{k^*}'^{(t)})\|_2 \le 2C$.
- The noise standard deviation is $\sigma_{\text{noise}} = 2\sigma C$.
- The conditional Rényi divergence is:
  $$\epsilon_t(\alpha) = \frac{\alpha S_t^2}{2\sigma_{\text{noise}}^2} \le \frac{\alpha (2C)^2}{2 (2\sigma C)^2} = \frac{\alpha}{2\sigma^2}$$

Because this bound holds **uniformly** for all possible broadcast weights $w^{(t)} \in \mathbb{R}^d$, the conditions of Mironov (2017) Proposition 1 are strictly satisfied. Hence:

$$\epsilon_{\text{RDP}}^{(T)}(\alpha) \le \sum_{t=1}^T \frac{\alpha}{2\sigma^2} = \frac{T\alpha}{2\sigma^2}$$

---

## 4. Required Verdict

Based on the evidence, the adaptive composition claim is classified as:

### **VERDICT: VALID WITH RESTRICTIONS**

#### Specific Operational Restrictions:
1. **Fixed Client Dataset Cardinality:** The replace-one-client-dataset adjacency relation assumes that client partition sizes $|D_k| = n_k$ are fixed public metadata (e.g. fixed Dirichlet allocations). If dataset sizes vary dynamically, $n_k$ must be privatized or uniform weighting ($p_k = 1/K$) must be used.
2. **Local Client Entropy Generation:** In real distributed deployments, clients must draw noise from local hardware entropy (`seed=None`) rather than the deterministic PRNG sequence used by the simulation testbed.
3. **Exclusion of `original_norm` Telemetry:** In distributed production, the `dp_meta` dictionary containing `original_norm` must remain on the edge client and must never be transmitted to the coordinator.
