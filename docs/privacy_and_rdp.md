# Differential Privacy and RDP Accounting

This document details the formal **Client-Level Differential Privacy** mechanism, operating-system cryptographic randomness integration, Rényi Differential Privacy (RDP) accounting, and operational privacy boundaries implemented in [src/privacy/mechanism.py](../src/privacy/mechanism.py), [src/privacy/rdp_accountant.py](../src/privacy/rdp_accountant.py), and [src/config.py](../src/config.py).

> **Note on Legacy Perturbation:** The codebase also retains [src/privacy/differential.py](../src/privacy/differential.py) (`LocalDifferentialPrivacy`), an earlier Stage 2 clipping + Gaussian perturbation helper using standard NumPy PRNG with $\sigma = 0.01$ **without formal privacy accounting**. It is preserved solely for legacy Stage 2/UI backwards compatibility and is explicitly rejected by `validate_config()` and `FederatedOrchestrator` when running in formal `RESEARCH_SIMULATION` or `DEPLOYMENT` modes.

---

## 1. Threat Model and Adjacency Definition

- **Adjacency Unit:** **Replace-one-client-dataset adjacency** ($\mathcal{D} \sim \mathcal{D}'$), protecting the entire local dataset $\mathcal{D}_k$ of any individual simulated client participant against an honest-but-curious coordinator observing submitted model weights.
- **Sampling Rate:** Full client participation every round ($q = 1.0$, no subsampling privacy amplification claimed).
- **Sensitivity Bound:** For any client update $\Delta w_k = w_k - w_{\text{global}} \in \mathbb{R}^d$ ($d = 26,594$ for `IDSNet` on NSL-KDD), complete update-vector L2 clipping enforces $\|\bar{\Delta w}_k\|_2 \le C$. Under replace-one-client-dataset adjacency, replacing one client's local dataset can shift the clipped update vector by at most the diameter of the L2 ball of radius $C$:
  $$S = \sup_{\mathcal{D} \sim \mathcal{D}'} \|\bar{\Delta w}(\mathcal{D}) - \bar{\Delta w}(\mathcal{D}')\|_2 = 2C$$

---

## 2. Mechanism Mechanics (`ClientLevelDPMechanism`)

In `privatize_client_weights(local_weights, global_weights)`:

1. **Compute Client Update:**
   $$\Delta w_k = w_k - w_{\text{global}}$$
2. **Complete Update-Vector L2 Clipping (`clip_update()`):**
   $$\bar{\Delta w}_k = \Delta w_k \cdot \min\left(1.0, \; \frac{C}{\|\Delta w_k\|_2}\right)$$
   If floating-point rounding causes $\|\bar{\Delta w}_k\|_2$ to exceed $C(1 + 10^{-5})$, a hard projection re-scales the float32 vector strictly inside radius $C$.
3. **Gaussian Perturbation (`perturb_update()`):**
   $$\tilde{\Delta w}_k = \bar{\Delta w}_k + n_k, \qquad n_k \sim \mathcal{N}\left(0, \; (2\sigma C)^2 I_d\right)$$
   Notice that the noise standard deviation per coordinate is $\sigma_{\text{noise}} = S \cdot \sigma = 2\sigma C$.
4. **Reconstruct Privatized Weights:**
   $$\tilde{w}_k = w_{\text{global}} + \tilde{\Delta w}_k$$
   In `ExecutionMode.RESEARCH_SIMULATION` and `ExecutionMode.DEPLOYMENT`, all steps 1–4 execute inside `client.privatize_local_weights()` before returning anything to the orchestrator.

---

## 3. OS-Backed Cryptographic Randomness & Execution Modes

Standard Mersenne Twister (`np.random.RandomState`) is predictable if seed state or sufficient outputs are exposed. To decouple unit-test reproducibility from cryptographic unpredictability, `src/config.py` enforces three explicit execution modes:

| Execution Mode (`ExecutionMode`) | Privacy Randomness (`PrivacyRandomnessMode`) | Zero-Noise (`sigma = 0`) Allowed? | Intended Use |
|---|---|---|---|
| `TEST` | `DETERMINISTIC_TEST` (MT19937 with explicit seed) or `OS_CSPRNG` | Yes (flagged non-private in metadata) | Fast unit tests and regression checks |
| `RESEARCH_SIMULATION` | `OS_CSPRNG` **mandatory** (seeds rejected) | **No** (raises `ValueError`); also rejects legacy $\sigma = 0.01$ | Controlled scientific experiments |
| `DEPLOYMENT` | `OS_CSPRNG` **mandatory**, client-local execution only | **No** (raises `ValueError`); `orchestrator.dp_mechanism = None` | Architectural separation with zero central noise generation |

### Box-Muller OS-CSPRNG Sampler (`generate_csprng_gaussian()`)
1. Reads $16 \cdot \lceil d/2 \rceil$ cryptographically random bytes directly from the OS kernel (`os.urandom`: `BCryptGenRandom`/`CryptGenRandom` on Windows, `getrandom`/`/dev/urandom` on Linux). Fails closed by raising `RuntimeError` if OS entropy reads short or fails.
2. Splits bytes into pairs of 64-bit unsigned integers, shifts right by 11 bits, and offsets by $0.5$ to map strictly onto the open interval $(0, 1)$ with 53-bit IEEE 754 precision:
   $$u_1, u_2 \in \left[2^{-54}, \; 1 - 2^{-54}\right]$$
   avoiding $\ln(0)$ singularities.
3. Applies Box-Muller transformation and scales by $\sigma_{\text{noise}} = 2\sigma C$:
   $$Z_0 = \sqrt{-2\ln u_1}\cos(2\pi u_2), \quad Z_1 = \sqrt{-2\ln u_1}\sin(2\pi u_2)$$

---

## 4. Rényi Differential Privacy (RDP) Accounting

`RDPAccountant` ([src/privacy/rdp_accountant.py](../src/privacy/rdp_accountant.py)) tracks cumulative privacy loss analytically over 17 discrete Rényi orders:
$$\alpha \in \{1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 16.0, 24.0, 32.0, 64.0, 128.0\}$$

- **Per-Round RDP (Gaussian mechanism with sensitivity $2C$ and noise std $2\sigma C$):**
  $$\epsilon_{\text{RDP}}(\alpha) \le \frac{\alpha}{2\sigma^2}$$
- **Composition across $T$ rounds ($q = 1.0$):**
  $$\epsilon_{\text{RDP}}^{(T)}(\alpha) = \sum_{t=1}^T \frac{\alpha}{2\sigma_t^2} = \frac{T \cdot \alpha}{2\sigma^2}$$
- **Conversion to $(\epsilon, \delta)$-DP:**
  $$\epsilon(\delta) = \min_{\alpha \in \text{orders}} \left[ \epsilon_{\text{RDP}}^{(T)}(\alpha) + \frac{\ln(1/\delta)}{\alpha - 1} \right]$$

### Approved Baseline Privacy Configuration (`WP2.2` / `WP2.4`)

Defined and enforced in code inside `src/config.py` (`APPROVED_*` constants, `FLConfig`, `validate_config()`, and `get_approved_research_config()`):
- Clients: $K = 5$ (full participation $q = 1.0$)
- L2 Clipping Bound: $C = 1.0$ (Global sensitivity $S = 2.0$)
- Noise Multiplier: $\sigma = 1.0$ (Coordinate Gaussian std $\sigma_{\text{noise}} = 2.0$)
- Communication Rounds: $T = 5$
- Failure Probability: $\delta = 10^{-5}$
- **Resulting Discrete Optimal Order & Privacy Bound:**
  At discrete order **$\alpha^* = 3.0$**,
  $$\epsilon_{\text{RDP}}^{(5)}(3.0) = \frac{5 \times 3.0}{2 \times 1.0^2} = 7.5, \qquad \frac{\ln(10^5)}{3.0 - 1} \approx 5.7565$$
  $$\mathbf{\epsilon = 13.2565 \quad (\approx 13.26)}$$

> **Note on `config/default.yaml`:** `config/default.yaml` is a legacy/reference YAML snapshot (retaining earlier Stage 2 parameters such as `num_rounds: 10`, `dp_enabled: false`, `reward_delta: 0.1`, `slash_delta: 0.4`, and `quarantine_threshold: 0.35`). It is not loaded by any runtime module, script, test, or dashboard component; active runtime defaults come from `src/config.py` (and `ReputationManager` defaults in `src/trust/reputation.py`).

---

## 5. Assumptions and Limitations

1. **Moderate Privacy Budget ($\epsilon \approx 13.26$):** Chosen intentionally during WP2.2 calibration as a utility-privacy balance for a 5-round deep neural network with $d = 26,594$ parameters; it does not provide an $\epsilon < 1$ theoretical guarantee, and privacy cost grows linearly with $T$ under full participation without subsampling.
2. **Metadata Exclusions:** Fixed Dirichlet dataset sizes $|D_k|$, cryptographic signatures, and validation losses recorded on the simulated ledger are outside the perturbation mechanism. Client training records are protected downstream by the DP post-processing property because `MultiCriteriaTrustEngine` only inspects perturbed weights $\tilde{w}_k$, though validation loss telemetry depends on the validator's held-out slice `D_val`.
3. **Host OS Trust Assumption:** OS-CSPRNG relies on the host operating system entropy pool; it protects against PRNG seed recovery in simulation/software, not against privileged compromise of the host OS kernel or VM snapshot cloning without entropy reseeding.
4. **No Physical Hardware Security Module / Networking:** Does not use hardware TPM/HSM chips or independent physical host isolation.
