# WP2.4 — CSPRNG Gaussian Implementation Report

**Project:** Blockchain-Assisted Privacy-Preserving Federated Learning for Network Intrusion Detection with Trust-Based Security and Cryptographic Auditing  
**Workspace:** `C:\Users\is043\.gemini\antigravity\scratch\blockchain-fl-ids`  
**Milestone:** WP2.4 — Secure Randomness Integration & Privacy Execution Separation  
**Document:** Cryptographic Gaussian Implementation & Security Verification  

---

## 1. Mathematical and Algorithmic Formulation

### 1.1 The Security Vulnerability in Conventional PRNGs
Standard software libraries (including NumPy and PyTorch CPU defaults) implement pseudo-random number generators such as the Mersenne Twister (MT19937) or PCG64. MT19937 has a state size of 19,937 bits (624 32-bit words). While it possesses excellent equidistribution properties over large periods ($2^{19937}-1$), **it is mathematically linear over $\mathbb{F}_2$**:
* Observing 624 consecutive outputs allows an attacker to invert the state transition matrix via Berlekamp-Massey or Gaussian elimination.
* Once the internal state is reconstructed, all subsequent outputs—and all preceding outputs—are known with 100% certainty.
* If a federated learning master seed is exposed or shared across clients, all Gaussian perturbation vectors added to local gradients can be subtracted by an honest-but-curious server or network eavesdropper, totally defeating differential privacy.

Merely re-seeding MT19937 using `secrets` does not solve this vulnerability; the generator itself remains linear and invertible once 624 floats are observed.

### 1.2 OS-CSPRNG Gaussian Sampling Architecture
To guarantee genuine cryptographic security, WP2.4 implements `generate_csprng_gaussian()` in `src/privacy/mechanism.py`, which acquires raw cryptographic entropy directly from the host operating system kernel and applies a direct, closed-form Box-Muller transformation.

```mermaid
flowchart TD
    Kernel["OS Kernel Entropy Pool<br/>(Windows BCryptGenRandom / Linux getrandom)"] -->|os.urandom(N*16)| RawBytes["Cryptographically Secure<br/>Raw Byte Stream"]
    RawBytes -->|np.frombuffer(dtype=uint64)| U64["Independent 64-bit Unsigned Integers<br/>(u1_raw, u2_raw)"]
    U64 -->|Shift & Map to (0, 1)| FloatUniform["High-Precision Uniform Variables<br/>u1, u2 in [2^-54, 1 - 2^-54]"]
    FloatUniform --> BoxMuller["Vectorized Box-Muller Transform<br/>R = sqrt(-2 ln u1), Theta = 2 pi u2<br/>Z0 = R cos(Theta), Z1 = R sin(Theta)"]
    BoxMuller --> Interleave["Interleave & Slice to d Coordinates<br/>Z ~ N(0, I_d)"]
    Interleave --> Scale["Scale by Noise Std<br/>noise = 2 * sigma * C * Z"]
    Scale --> Privatize["Privatized Gradient Update<br/>tilde{Delta w} = clip(Delta w, C) + noise"]
```

### 1.3 Uniform Float Mapping Precision
A critical failure mode in Box-Muller sampling is encountering $u_1 = 0.0$, which yields $\ln(0) = -\infty$, or $u_1 = 1.0$, which yields $\ln(1) = 0 \implies R = 0$. 

In `generate_csprng_gaussian()`, 64-bit unsigned integers are converted to IEEE 754 64-bit floats with 53 bits of mantissa precision:
$$u = \frac{(\text{uint64} \gg 11) + 0.5}{2^{53}}$$

Since $0 \le (\text{uint64} \gg 11) \le 2^{53} - 1$, the numerator satisfies:
$$0.5 \le (\text{uint64} \gg 11) + 0.5 \le 2^{53} - 0.5$$

Dividing by $2^{53}$ strictly bounds $u$ in the open interval:
$$2^{-54} \le u \le 1 - 2^{-54}$$
This mathematically guarantees that:
1. $u > 0$ strictly; $\ln(u)$ is always finite, negative, and strictly bounded.
2. $u < 1$ strictly; $R = \sqrt{-2\ln(u)} > 0$ strictly.
3. Every discrete point has equal probability, preventing sampling distortion.

---

## 2. Source Code Implementation Details

The implementation is housed in `src/privacy/mechanism.py`:

```python
def generate_csprng_gaussian(d: int, mean: float = 0.0, std: float = 1.0) -> np.ndarray:
    if d <= 0:
        return np.zeros(0, dtype=np.float32)
    if std == 0.0:
        return np.full(d, mean, dtype=np.float32)

    try:
        n_pairs = (d + 1) // 2
        raw_bytes = os.urandom(n_pairs * 16)
        if len(raw_bytes) != n_pairs * 16:
            raise RuntimeError(f"Expected {n_pairs * 16} bytes from os.urandom, got {len(raw_bytes)}")

        uints = np.frombuffer(raw_bytes, dtype=np.uint64)
        u1_raw = uints[0::2]
        u2_raw = uints[1::2]

        u1 = ((u1_raw >> 11) + 0.5) / (1 << 53)
        u2 = ((u2_raw >> 11) + 0.5) / (1 << 53)

        r = np.sqrt(-2.0 * np.log(u1))
        theta = (2.0 * math.pi) * u2

        z0 = r * np.cos(theta)
        z1 = r * np.sin(theta)

        z = np.empty(n_pairs * 2, dtype=np.float32)
        z[0::2] = z0.astype(np.float32)
        z[1::2] = z1.astype(np.float32)

        noise = (mean + std * z[:d]).astype(np.float32)
        return noise
    except Exception as e:
        raise RuntimeError(f"OS-backed CSPRNG Gaussian sampling failed (fail closed): {e}") from e
```

### 2.1 Fail-Closed Security Policy
If the operating system kernel entropy provider fails, runs out of file descriptors, or encounters any system-level interruption, `generate_csprng_gaussian` catches the exception and immediately raises:
`RuntimeError: OS-backed CSPRNG Gaussian sampling failed (fail closed)`
There is **zero silent fallback** to `numpy.random`, `random`, or unseeded generators. Execution halts immediately to prevent unperturbed or predictably perturbed updates from being broadcast.

### 2.2 Memory Hygiene
No secret seeds, keys, or generator states are retained in class attributes or returned in metadata. The raw random byte stream is consumed immediately within local scope and garbage collected.

---

## 3. Empirical Statistical Verification

Statistical verification tests in `tests/test_wp2_4_secure_randomness.py` evaluate $N = 5000$ Gaussian draws generated via `generate_csprng_gaussian`:
* **Expected Distribution:** $\mathcal{N}(0, \sigma_{\text{noise}}^2)$ with $\sigma_{\text{noise}} = 2\sigma C = 2.0$.
* **Empirical Mean:** Observed within 4 standard errors ($|\bar{x}| < 4 \cdot \frac{2.0}{\sqrt{5000}} \approx 0.113$).
* **Empirical Standard Deviation:** Observed within 4 standard errors ($|s - 2.0| < 4 \cdot \frac{2.0}{\sqrt{10000}} \approx 0.080$).
* **Vector Shape & Precision:** Exact 1D NumPy array of length $d$ and precision `np.float32`.
* **Zero Multiplication Edge Case:** When $\sigma = 0.0$, returns exact zero array without invoking OS entropy (`randomness_source = "DETERMINISTIC_ZERO"`).
