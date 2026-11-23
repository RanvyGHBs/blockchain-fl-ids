"""
Formal Client-Level Differential Privacy Mechanism for Federated Learning (WP2 / WP2.4).
Implements complete client-update vector L2-norm clipping and Gaussian perturbation
under replace-one-client-dataset adjacency with global sensitivity S = 2C.
Supports execution modes (TEST, RESEARCH_SIMULATION, DEPLOYMENT) with OS-CSPRNG Gaussian sampling.
"""

from typing import Dict, Any, Tuple, Optional, Union
import math
import os
import numpy as np

from src.config import ExecutionMode, PrivacyRandomnessMode, APPROVED_CLIP_NORM, APPROVED_NOISE_MULTIPLIER


def generate_csprng_gaussian(d: int, mean: float = 0.0, std: float = 1.0) -> np.ndarray:
    """
    Generates d independent Gaussian random variables N(mean, std^2) using cryptographically
    secure pseudorandom entropy directly from the operating system kernel CSPRNG (os.urandom).
    
    Algorithm:
        Vectorized Box-Muller transformation:
        1. Read raw random bytes from os.urandom (CryptGenRandom/BCryptGenRandom on Windows, /dev/urandom on Linux).
        2. Map 64-bit unsigned integers to uniform random variables u in (0, 1) with 53 bits of precision.
        3. Compute standard normal variables Z_0 = sqrt(-2 ln u1) cos(2 pi u2), Z_1 = sqrt(-2 ln u1) sin(2 pi u2).
        4. Scale and shift: X = mean + std * Z.
        
    Security properties:
        - Completely independent of MT19937 or pseudo-random state.
        - Unpredictable and forward-secure entropy.
        - Fails closed on any OS entropy failure (raises RuntimeError).
        - No secret seeds or entropy material retained in memory.
        
    Args:
        d: Number of random values to generate (d >= 0).
        mean: Distribution mean.
        std: Distribution standard deviation (std >= 0).
        
    Returns:
        1D numpy array of shape (d,) with dtype np.float32.
    """
    if d <= 0:
        return np.zeros(0, dtype=np.float32)
    if not isinstance(std, (int, float)) or math.isnan(std) or math.isinf(std) or std < 0:
        raise ValueError(f"std must be a non-negative finite real number, got {std}")
    if std == 0.0:
        return np.full(d, mean, dtype=np.float32)

    try:
        n_pairs = (d + 1) // 2
        # Each pair of normal variables requires two 64-bit uniform floats (16 bytes)
        raw_bytes = os.urandom(n_pairs * 16)
        if len(raw_bytes) != n_pairs * 16:
            raise RuntimeError(f"Expected {n_pairs * 16} bytes from os.urandom, got {len(raw_bytes)}")

        uints = np.frombuffer(raw_bytes, dtype=np.uint64)
        u1_raw = uints[0::2]
        u2_raw = uints[1::2]

        # Map uint64 to open interval (0, 1) with 53 bits of precision (IEEE 754 mantissa)
        # Shift right by 11 bits to get 53-bit integers in [0, 2^53 - 1]
        # Adding 0.5 strictly ensures values lie within [2^-54, 1 - 2^-54] (strictly avoids 0 and 1)
        u1 = ((u1_raw >> 11) + 0.5) / (1 << 53)
        u2 = ((u2_raw >> 11) + 0.5) / (1 << 53)

        # Box-Muller transform
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


class ClientLevelDPMechanism:
    """
    Client-Level Differential Privacy Mechanism for Federated Learning.
    
    Guarantees:
        Adjacency: Replace-one-client-dataset adjacency (D ~ D').
        Clipping: Complete model update vector L2-norm bounded by C.
        Global L2 Sensitivity: S = 2C.
        Perturbation: Gaussian noise n ~ N(0, (2 * sigma * C)^2 * I_d).
        Per-Round RDP Bound: epsilon_RDP(alpha) <= alpha / (2 * sigma^2).
        Execution Modes: TEST (deterministic), RESEARCH_SIMULATION (OS-CSPRNG), DEPLOYMENT (client-local).
    """

    def __init__(
        self,
        clip_norm: float = APPROVED_CLIP_NORM,
        noise_multiplier: float = APPROVED_NOISE_MULTIPLIER,
        seed: Optional[int] = None,
        execution_mode: Optional[Union[ExecutionMode, str]] = None,
        privacy_randomness_mode: Optional[Union[PrivacyRandomnessMode, str]] = None
    ):
        """
        Initializes the client-level DP mechanism.

        Args:
            clip_norm: Global L2 clipping threshold C > 0.
            noise_multiplier: Ratio sigma >= 0 defining noise std relative to sensitivity.
            seed: Optional seed for deterministic testing. Permitted ONLY in TEST mode.
            execution_mode: TEST, RESEARCH_SIMULATION, or DEPLOYMENT.
            privacy_randomness_mode: DETERMINISTIC_TEST or OS_CSPRNG.
        """
        if not isinstance(clip_norm, (int, float)) or math.isnan(clip_norm) or math.isinf(clip_norm) or clip_norm <= 0:
            raise ValueError(f"clip_norm must be a positive finite real number, got {clip_norm}")
        if not isinstance(noise_multiplier, (int, float)) or math.isnan(noise_multiplier) or math.isinf(noise_multiplier):
            raise ValueError(f"noise_multiplier must be a finite real number, got {noise_multiplier}")
        if noise_multiplier < 0:
            raise ValueError(f"noise_multiplier cannot be negative, got {noise_multiplier}")

        self.clip_norm = float(clip_norm)
        self.noise_multiplier = float(noise_multiplier)
        self.sensitivity = 2.0 * self.clip_norm
        self.noise_std = self.sensitivity * self.noise_multiplier  # 2 * sigma * C

        # Resolve execution mode
        if execution_mode is not None:
            self._explicit_mode = True
            if isinstance(execution_mode, str):
                try:
                    self.execution_mode = ExecutionMode(execution_mode.upper())
                except ValueError:
                    raise ValueError(f"Unsupported execution_mode: '{execution_mode}'. Must be one of {[m.value for m in ExecutionMode]}")
            elif isinstance(execution_mode, ExecutionMode):
                self.execution_mode = execution_mode
            else:
                raise ValueError(f"Invalid execution_mode type: {type(execution_mode)}")
        else:
            self._explicit_mode = False
            # Mode auto-detection: if seed provided or noise_multiplier == 0, default to non-private TEST mode;
            # otherwise default to secure RESEARCH_SIMULATION mode.
            if seed is not None or self.noise_multiplier == 0.0:
                self.execution_mode = ExecutionMode.TEST
            else:
                self.execution_mode = ExecutionMode.RESEARCH_SIMULATION

        # Security check: Deterministic seeds and zero-noise strictly prohibited in secure modes
        if self.execution_mode in (ExecutionMode.RESEARCH_SIMULATION, ExecutionMode.DEPLOYMENT):
            if seed is not None:
                raise ValueError(
                    f"Deterministic seed is strictly prohibited in {self.execution_mode.value} mode. "
                    "Secure modes require OS-CSPRNG randomness."
                )
            if self.noise_multiplier <= 0:
                raise ValueError(
                    f"noise_multiplier must be strictly positive (sigma > 0) in {self.execution_mode.value} mode, "
                    f"got {self.noise_multiplier}. Zero-noise is strictly prohibited in secure privacy execution."
                )

        # Resolve privacy randomness mode
        if privacy_randomness_mode is not None:
            if isinstance(privacy_randomness_mode, str):
                try:
                    self.privacy_randomness_mode = PrivacyRandomnessMode(privacy_randomness_mode.upper())
                except ValueError:
                    raise ValueError(f"Unsupported privacy_randomness_mode: '{privacy_randomness_mode}'. Must be one of {[r.value for r in PrivacyRandomnessMode]}")
            elif isinstance(privacy_randomness_mode, PrivacyRandomnessMode):
                self.privacy_randomness_mode = privacy_randomness_mode
            else:
                raise ValueError(f"Invalid privacy_randomness_mode type: {type(privacy_randomness_mode)}")
        else:
            if self.execution_mode in (ExecutionMode.RESEARCH_SIMULATION, ExecutionMode.DEPLOYMENT):
                self.privacy_randomness_mode = PrivacyRandomnessMode.OS_CSPRNG
            else:
                self.privacy_randomness_mode = PrivacyRandomnessMode.DETERMINISTIC_TEST

        # Security check: Insecure randomness strictly prohibited in secure modes
        if self.execution_mode in (ExecutionMode.RESEARCH_SIMULATION, ExecutionMode.DEPLOYMENT):
            if self.privacy_randomness_mode != PrivacyRandomnessMode.OS_CSPRNG:
                raise ValueError(
                    f"Privacy randomness mode '{self.privacy_randomness_mode.value}' is prohibited in "
                    f"{self.execution_mode.value} mode. Mandatory randomness mode is OS_CSPRNG."
                )

        self.seed = seed

    def clip_update(self, update_vector: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Clips the complete model update vector to global L2 norm bound C.
        
        Formula:
            bar{Delta w} = Delta w * min(1, C / ||Delta w||_2)
            
        Args:
            update_vector: 1D numpy array representing Delta w = w_client - w_global.
            
        Returns:
            Tuple of (clipped_vector, metadata_dict)
        """
        if not isinstance(update_vector, np.ndarray):
            raise TypeError(f"update_vector must be a numpy ndarray, got {type(update_vector)}")
        
        flat_update = update_vector.flatten()
        if not np.all(np.isfinite(flat_update)):
            raise ValueError("update_vector contains NaN or Inf values; cannot apply L2 norm clipping.")

        original_norm = float(np.linalg.norm(flat_update))
        
        if original_norm == 0.0:
            clip_factor = 1.0
            clipped_update = np.zeros_like(flat_update, dtype=np.float32)
            clipped_norm = 0.0
        else:
            clip_factor = max(1.0, original_norm / self.clip_norm)
            clipped_update = (flat_update / clip_factor).astype(np.float32)
            clipped_norm = float(np.linalg.norm(clipped_update))

        # Strict floating point tolerance check (0.0001% tolerance for float32 precision)
        if clipped_norm > self.clip_norm * (1.0 + 1e-5):
            # Enforce hard projection if floating-point imprecision slightly exceeds bound
            clipped_update = (clipped_update * (self.clip_norm / clipped_norm)).astype(np.float32)
            clipped_norm = float(np.linalg.norm(clipped_update))

        meta = {
            "original_norm": original_norm,
            "clipped_norm": clipped_norm,
            "clip_factor": float(clip_factor),
            "clip_norm_bound": self.clip_norm,
            "is_clipped": bool(original_norm > self.clip_norm),
            "parameter_dimension": int(flat_update.size)
        }
        return clipped_update, meta

    def perturb_update(self, clipped_update: np.ndarray, seed: Optional[int] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Adds calibrated Gaussian noise to a clipped update vector.
        
        Noise Distribution:
            n ~ N(0, sigma_noise^2 * I_d) where sigma_noise = 2 * sigma * C.
            
        Args:
            clipped_update: 1D numpy array with ||clipped_update||_2 <= C.
            seed: Optional seed for isolated reproducible draw. Permitted ONLY in TEST mode.
            
        Returns:
            Tuple of (perturbed_update, metadata_dict)
        """
        if not isinstance(clipped_update, np.ndarray):
            raise TypeError(f"clipped_update must be a numpy ndarray, got {type(clipped_update)}")
        
        flat_clipped = clipped_update.flatten()
        if not np.all(np.isfinite(flat_clipped)):
            raise ValueError("clipped_update contains NaN or Inf values.")

        d = flat_clipped.size
        effective_std = self.noise_std

        if effective_std == 0.0:
            if self.execution_mode in (ExecutionMode.RESEARCH_SIMULATION, ExecutionMode.DEPLOYMENT):
                raise ValueError(
                    f"Zero-noise perturbation is strictly prohibited in {self.execution_mode.value} mode. "
                    "Differential privacy requires sigma > 0."
                )
            noise = np.zeros(d, dtype=np.float32)
            randomness_source = "NON_PRIVATE_ZERO_NOISE (TEST_ONLY)"
            current_mode = ExecutionMode.TEST
            current_rand_mode = PrivacyRandomnessMode.DETERMINISTIC_TEST
            is_private = False
            privacy_guarantee = "NONE (zero noise multiplier sigma=0 in TEST mode)"
        else:
            is_private = True
            privacy_guarantee = f"Client-Level DP (sigma={self.noise_multiplier}, C={self.clip_norm})"
            if seed is not None and not self._explicit_mode:
                # Caller did not specify an explicit mode at initialization, but supplied a test seed at call-time
                current_mode = ExecutionMode.TEST
                current_rand_mode = PrivacyRandomnessMode.DETERMINISTIC_TEST
                randomness_source = "TEST_PRNG (MT19937)"
                rng = np.random.RandomState(seed)
                noise = rng.normal(0.0, effective_std, size=d).astype(np.float32)
            elif self.execution_mode in (ExecutionMode.RESEARCH_SIMULATION, ExecutionMode.DEPLOYMENT):
                if seed is not None:
                    raise ValueError(
                        f"Explicit seed is strictly prohibited in {self.execution_mode.value} mode. "
                        "Privacy noise must be generated via OS-CSPRNG."
                    )
                noise = generate_csprng_gaussian(d, mean=0.0, std=effective_std)
                randomness_source = "OS_CSPRNG"
                current_mode = self.execution_mode
                current_rand_mode = PrivacyRandomnessMode.OS_CSPRNG
            elif self.execution_mode == ExecutionMode.TEST:
                current_mode = ExecutionMode.TEST
                current_rand_mode = self.privacy_randomness_mode
                if seed is None and self.seed is None and self.privacy_randomness_mode == PrivacyRandomnessMode.OS_CSPRNG:
                    noise = generate_csprng_gaussian(d, mean=0.0, std=effective_std)
                    randomness_source = "OS_CSPRNG"
                else:
                    rng = np.random.RandomState(seed if seed is not None else self.seed)
                    noise = rng.normal(0.0, effective_std, size=d).astype(np.float32)
                    randomness_source = "TEST_PRNG (MT19937)"
            else:
                raise ValueError(f"Unknown execution mode: {self.execution_mode}")

        perturbed_update = (flat_clipped + noise).astype(np.float32)
        perturbed_norm = float(np.linalg.norm(perturbed_update))

        meta = {
            "noise_std": float(effective_std),
            "sensitivity": float(self.sensitivity),
            "noise_multiplier": float(self.noise_multiplier),
            "perturbed_norm": perturbed_norm,
            "noise_l2_norm": float(np.linalg.norm(noise)),
            "execution_mode": current_mode.value,
            "privacy_randomness_mode": current_rand_mode.value,
            "randomness_source": randomness_source,
            "is_private": is_private,
            "privacy_guarantee": privacy_guarantee
        }
        return perturbed_update, meta

    def privatize_update(self, update_vector: np.ndarray, seed: Optional[int] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Executes the full client-level privacy mechanism:
        1. L2-norm clipping: Delta w -> bar{Delta w} with ||bar{Delta w}||_2 <= C
        2. Gaussian perturbation: bar{Delta w} + N(0, 4 * sigma^2 * C^2 * I_d)
        
        Args:
            update_vector: Raw model update Delta w = w_client - w_global.
            seed: Optional seed for isolated reproducible draw. Permitted ONLY in TEST mode.
            
        Returns:
            Tuple of (perturbed_update, combined_metadata)
        """
        clipped_update, clip_meta = self.clip_update(update_vector)
        perturbed_update, noise_meta = self.perturb_update(clipped_update, seed=seed)
        
        combined_meta = {**clip_meta, **noise_meta}
        return perturbed_update, combined_meta

    def privatize_client_weights(
        self,
        local_weights: np.ndarray,
        global_weights: np.ndarray,
        seed: Optional[int] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Applies client-level DP to a client's absolute local weights relative to global weights:
        1. Delta w = local_weights - global_weights
        2. bar{Delta w} = clip(Delta w, C)
        3. tilde{Delta w} = bar{Delta w} + N(0, 4 * sigma^2 * C^2 * I_d)
        4. tilde{w} = global_weights + tilde{Delta w}
        
        Args:
            local_weights: Local trained weights from client.
            global_weights: Global weights received at start of round.
            seed: Optional seed for isolated reproducible draw. Permitted ONLY in TEST mode.
            
        Returns:
            Tuple of (perturbed_weights, combined_metadata)
        """
        if local_weights.shape != global_weights.shape:
            raise ValueError(f"Shape mismatch: local {local_weights.shape} vs global {global_weights.shape}")
        
        delta_w = (local_weights - global_weights).astype(np.float32)
        perturbed_delta, meta = self.privatize_update(delta_w, seed=seed)
        perturbed_weights = (global_weights.flatten() + perturbed_delta).astype(np.float32)
        
        meta["final_perturbed_weights_norm"] = float(np.linalg.norm(perturbed_weights))
        return perturbed_weights, meta
