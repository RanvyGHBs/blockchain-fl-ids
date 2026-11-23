"""
Formal Client-Level Differential Privacy Mechanism for Federated Learning (WP2).
Implements complete client-update vector L2-norm clipping and Gaussian perturbation
under replace-one-client-dataset adjacency with global sensitivity S = 2C.
"""

from typing import Dict, Any, Tuple, Optional
import math
import numpy as np


class ClientLevelDPMechanism:
    """
    Client-Level Differential Privacy Mechanism for Federated Learning.
    
    Guarantees:
        Adjacency: Replace-one-client-dataset adjacency (D ~ D').
        Clipping: Complete model update vector L2-norm bounded by C.
        Global L2 Sensitivity: S = 2C.
        Perturbation: Gaussian noise n ~ N(0, (2 * sigma * C)^2 * I_d).
        Per-Round RDP Bound: epsilon_RDP(alpha) <= alpha / (2 * sigma^2).
    """

    def __init__(self, clip_norm: float = 1.0, noise_multiplier: float = 0.01, seed: Optional[int] = None):
        """
        Initializes the client-level DP mechanism.

        Args:
            clip_norm: Global L2 clipping threshold C > 0.
            noise_multiplier: Ratio sigma >= 0 defining noise std relative to sensitivity.
            seed: Optional seed for deterministic testing. If None, uses entropy from OS.
        """
        if not isinstance(clip_norm, (int, float)) or math.isnan(clip_norm) or math.isinf(clip_norm) or clip_norm <= 0:
            raise ValueError(f"clip_norm must be a positive finite real number, got {clip_norm}")
        if not isinstance(noise_multiplier, (int, float)) or math.isnan(noise_multiplier) or math.isinf(noise_multiplier) or noise_multiplier < 0:
            raise ValueError(f"noise_multiplier must be a non-negative finite real number, got {noise_multiplier}")

        self.clip_norm = float(clip_norm)
        self.noise_multiplier = float(noise_multiplier)
        self.seed = seed
        self.sensitivity = 2.0 * self.clip_norm
        self.noise_std = self.sensitivity * self.noise_multiplier  # 2 * sigma * C

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
            seed: Optional seed for isolated reproducible draw. If None, uses unseeded PRNG.
            
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
            noise = np.zeros(d, dtype=np.float32)
        else:
            rng = np.random.RandomState(seed) if seed is not None else np.random.RandomState(self.seed)
            if seed is None and self.seed is None:
                noise = np.random.normal(0.0, effective_std, size=d).astype(np.float32)
            else:
                noise = rng.normal(0.0, effective_std, size=d).astype(np.float32)

        perturbed_update = (flat_clipped + noise).astype(np.float32)
        perturbed_norm = float(np.linalg.norm(perturbed_update))

        meta = {
            "noise_std": float(effective_std),
            "sensitivity": float(self.sensitivity),
            "noise_multiplier": float(self.noise_multiplier),
            "perturbed_norm": perturbed_norm,
            "noise_l2_norm": float(np.linalg.norm(noise))
        }
        return perturbed_update, meta

    def privatize_update(self, update_vector: np.ndarray, seed: Optional[int] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Executes the full client-level privacy mechanism:
        1. L2-norm clipping: Delta w -> bar{Delta w} with ||bar{Delta w}||_2 <= C
        2. Gaussian perturbation: bar{Delta w} + N(0, 4 * sigma^2 * C^2 * I_d)
        
        Args:
            update_vector: Raw model update Delta w = w_client - w_global.
            seed: Optional seed for isolated reproducible draw.
            
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
            seed: Optional seed for isolated reproducible draw.
            
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
