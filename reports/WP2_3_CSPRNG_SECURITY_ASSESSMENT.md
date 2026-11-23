# WP2.3 — CSPRNG Security Assessment and Threat Model Evaluation

**Project:** Blockchain-Assisted Privacy-Preserving Federated Learning for Network Intrusion Detection with Trust-Based Security and Cryptographic Auditing  
**Workspace:** `C:\Users\is043\.gemini\antigravity\scratch\blockchain-fl-ids`  
**Milestone:** WP2.3 — Independent Cryptographic Randomness & Gaussian Noise Security Audit  
**Deliverable:** CSPRNG Security Assessment & Threat Model Vulnerability Analysis  
**Execution Mode:** STRICTLY READ-ONLY AUDIT  
**Date:** 2026-11-23  

---

## 1. Executive Summary

This report delivers a formal cryptographic security assessment of the pseudorandom number generators (PRNGs) employed by the federated learning differential privacy mechanism.

Differential privacy mechanisms theoretically assume that perturbation noise is sampled from an ideal, unpredictable probability distribution. If an attacker can predict, reconstruct, or invert the pseudo-random stream, the differential privacy guarantee is nullified regardless of the theoretical RDP bound.

### Key Assessment Findings
1. **Mersenne Twister (MT19937) is Not a CSPRNG:** The project uses `np.random.RandomState`, which implements 32-bit MT19937. MT19937 is explicitly non-cryptographic; its internal state consists of 624 32-bit integers that can be completely reconstructed after observing 624 outputs.
2. **Deterministic Seed Exposure Vulnerability:** In `src/federated/orchestrator.py`, the random seed is derived directly from the public experiment configuration parameter `self.seed`. Any server that knows or guesses `self.seed` can reconstruct the exact noise vector $n_k^{(t)}$ and subtract it to reveal the unperturbed clipped update $\bar{\Delta w}_k^{(t)}$.
3. **Classification:** The current implementation is classified as **Statistically suitable but not cryptographically secure**. It is scientifically valid for controlled algorithmic simulation, but insecure for untrusted distributed deployment.

---

## 2. Cryptographic Classification of Randomness Components

| Subsystem Component | Exact Implementation | Algorithm / Mechanism | Cryptographic Classification | Operational Security Assessment |
|:---|:---|:---|:---:|:---|
| **DP Noise Generator** | `np.random.RandomState` (`mechanism.py:118`) | Mersenne Twister (MT19937) | **Statistically Suitable (Non-CSPRNG)** | Invertible after 624 outputs; vulnerable to state reconstruction. |
| **Unseeded Fallback** | `np.random.normal` (`mechanism.py:120`) | Global MT19937 (`mtrand._rand`) | **Statistically Suitable (Non-CSPRNG)** | Initialized from OS entropy, but advances via non-cryptographic MT19937 recurrence. |
| **Seed Derivation Engine** | `orchestrator.py:492` | Linear Congruential Formula | **Deterministic Test Randomness** | Seed is an explicit function of `self.seed`, `r`, and `cid`; 100% predictable by coordinator. |
| **PyTorch Layer Init** | `torch.manual_seed` (`orchestrator.py:392`) | PyTorch CPU/CUDA PRNG | **Statistically Suitable (Non-CSPRNG)** | Used for model weight initialization; standard practice in ML. |
| **Digital Signing (ECDSA)** | `CryptoManager.sign_message` (`crypto.py:38`) | `ecdsa.SigningKey` (secp256k1) | **Cryptographically Secure (CSPRNG)** | Uses Python `os.urandom` internally for RFC 6979 / CSPRNG nonce generation. |
| **OS Entropy Providers** | `os.urandom`, `secrets` | OS Kernel CSPRNG | **Not Used in DP Pathway** | Excluded from `src/privacy/mechanism.py`. |

---

## 3. Cryptographic Vulnerability Analysis of MT19937

### 3.1. Mathematical Architecture of MT19937
The 32-bit Mersenne Twister produces a sequence of pseudo-random words $x_k \in \mathbb{F}_2^{32}$ via a linear feedback shift register (LFSR) with state space dimension 19,937 bits ($N = 624$ words of 32 bits each):
$$x_{k+N} = x_{k+M} \oplus ((x_k \text{ AND } \mathbf{u}) \mid (x_{k+1} \text{ AND } \mathbf{l})) A$$
Where:
- $N = 624$, $M = 397$.
- $\mathbf{u}$ and $\mathbf{l}$ are upper and lower bit masks.
- $A$ is a companion matrix.

The output word $y_k$ is produced by applying a linear tempering transform $T$:
$$y_1 = x \oplus (x \gg u)$$
$$y_2 = y_1 \oplus ((y_1 \ll s) \text{ AND } \mathbf{b})$$
$$y_3 = y_2 \oplus ((y_2 \ll t) \text{ AND } \mathbf{c})$$
$$y = y_3 \oplus (y_3 \gg l)$$

### 3.2. The Inversion Attack (Untempering)
Every operation in the tempering transformation $T$ is linear over $\mathbb{F}_2$ and **strictly invertible**:
- Right shift and XOR can be inverted bit-by-bit from MSB to LSB.
- Left shift, bitwise AND, and XOR can be inverted bit-by-bit from LSB to MSB.

Consequently, if an attacker observes 624 consecutive 32-bit outputs ($y_0, \dots, y_{623}$), the attacker can uniquely reconstruct the internal state vector $\mathbf{x} = (x_0, \dots, x_{623})$. Once reconstructed, the attacker can simulate the generator indefinitely in both forward and backward directions.

In our neural network (`IDSNet`), each update contains $d \approx 27,000$ float32 parameters. A single client update draws 27,000 values, which exceeds the 624-word inversion threshold by a factor of 43.

---

## 4. Threat Model Assessment

The implementation was evaluated against six adversarial threat scenarios:

### 4.1. Threat 1: Honest-but-Curious Aggregation Server
- **Vulnerability:** **CRITICAL IN SIMULATION MODE.**
- **Analysis:** In the federated orchestrator, `self.seed` is part of the simulation configuration dictionary. An honest-but-curious server running this simulation code knows `self.seed = 42`.
- **Attack Execution:**
  1. Server computes $\text{seed}_{r, cid} = (42 \times 10007 + r \times 997 + cid \times 101) \pmod{2^{31} - 1}$.
  2. Server instantiates `rng = np.random.RandomState(seed_{r, cid})`.
  3. Server samples $n_{cid}^{(r)} = \text{rng.normal}(0.0, 2.0, \text{size}=d)$.
  4. Server subtracts noise from received update:
     $$\bar{\Delta w}_{cid}^{(r)} = \widetilde{\Delta w}_{cid}^{(r)} - n_{cid}^{(r)}$$
  5. The server recovers the unperturbed, clipped client gradient update with **$100\%$ precision**. Privacy loss is total.

### 4.2. Threat 2: Server Attempting to Predict Noise Without Knowing `self.seed`
- **Vulnerability:** **MODERATE / THEORETICAL.**
- **Analysis:** If the server does not know `self.seed`, it observes only the noisy update $\widetilde{\Delta w}_k = \bar{\Delta w}_k + n_k$. Because the clean update $\bar{\Delta w}_k$ is unknown, the server does not directly observe the raw outputs of MT19937, making direct untempering non-trivial. However, because `client_dp_seed` is drawn from a small 31-bit keyspace ($2^{31} - 1 \approx 2.14 \times 10^9$), an attacker with GPU brute-force capability can search the seed space to find the seed minimizing model reconstruction residual.

### 4.3. Threat 3: Malicious Client Manipulating Local Noise
- **Vulnerability:** **INHERENT TO LOCAL DIFFERENTIAL PRIVACY.**
- **Analysis:** In client-level local DP, clients generate their own noise. A Byzantine or malicious client (e.g., Client 3 injecting sign-flip attacks) can intentionally disable noise ($\sigma = 0$) or inject adversarial perturbations disguised as Gaussian noise. This is why multi-criteria trust evaluation (Tier 1-3 screening) is essential to detect malicious updates.

### 4.4. Threat 4: Repeated Generator State or Seed Reuse
- **Vulnerability:** **MITIGATED WITHIN RUN; PRESENT ACROSS RUNS.**
- **Analysis:** Within a single experiment run, the linear congruential multiplier ($997 \times r + 101 \times cid$) guarantees that seeds do not collide across rounds $r \le 100$ and clients $cid \le 5$. However, if an experiment is restarted with identical configuration, identical noise vectors are generated.

### 4.5. Threat 5: Accidental Logging of Random State
- **Vulnerability:** **MITIGATED.**
- **Analysis:** Inspection of `src/federated/orchestrator.py` and `src/blockchain/block.py` confirms that neither `client_dp_seed` nor the internal MT19937 state array is written to disk, committed to blockchain transactions, or logged to console output.

### 4.6. Threat 6: Compromised Client Operating System / Process
- **Vulnerability:** **OUT OF SCOPE.**
- **Analysis:** If an attacker achieves code execution inside the client runtime, all local datasets and private keys are compromised. Differential privacy protects against an adversarial observer on the network channel, not endpoint compromise.

---

## 5. Security Recommendations for Future Implementation

To transition from controlled simulation to distributed production deployment, the following changes are recommended:

1. **Adopt Cryptographically Secure Gaussian Sampling:**
   Replace `np.random.RandomState` with a CSPRNG-backed sampler:
   - Use Python's `secrets.token_bytes()` or `os.urandom()` to seed a modern cryptographic stream cipher (e.g., ChaCha20 or AES-CTR in counter mode).
   - Alternatively, integrate an audited DP library (e.g. OpenDP / Google DP) that implements secure discrete Gaussian sampling to prevent floating-point side-channel vulnerabilities (Mironov, 2012).
2. **Decouple Client Noise Generation from Coordinator:**
   Remove `seed=client_dp_seed` from `FederatedOrchestrator._run_round()`. In physical deployment, edge clients must invoke `privatize_client_weights(..., seed=None)`, guaranteeing that the server has zero prior knowledge of client entropy.

---

## 6. Audit Verdict

The Gaussian noise generation engine is **statistically valid for algorithmic simulation**, but **cryptographically insecure for distributed adversarial deployment**.
