"""
Clipping-based Gaussian update perturbation (without formal privacy accounting).
Provides empirical parameter perturbation against basic gradient inspection
by applying L2-norm clipping and Gaussian perturbation to local model updates.
Note: This engine applies heuristic perturbation without formal privacy accounting
or mathematical (epsilon, delta)-differential privacy guarantees.
"""

from typing import Tuple
import numpy as np


class LocalDifferentialPrivacy:
    """
    Applies clipping-based Gaussian update perturbation (without formal privacy accounting)
    to client model weight vectors.
    """

    def __init__(self, clip_norm: float = 1.0, noise_multiplier: float = 0.01, seed: int = None):
        self.clip_norm = clip_norm
        self.noise_multiplier = noise_multiplier
        self.seed = seed

    def privatize(self, weights: np.ndarray) -> Tuple[np.ndarray, dict]:
        """
        Applies clipping-based Gaussian update perturbation (without formal privacy accounting):
        1. L2 Norm Clipping: w_clipped = w / max(1, ||w||_2 / C)
        2. Gaussian Mechanism: w_private = w_clipped + N(0, (sigma * C)^2 * I)
        """
        if self.seed is not None:
            np.random.seed(self.seed)

        original_norm = float(np.linalg.norm(weights))
        clip_factor = max(1.0, original_norm / self.clip_norm)
        clipped_weights = weights / clip_factor

        # Add Gaussian noise scaled by clip_norm and noise_multiplier
        sigma = self.noise_multiplier * self.clip_norm
        noise = np.random.normal(0.0, sigma, size=weights.shape).astype(np.float32)
        privatized_weights = (clipped_weights + noise).astype(np.float32)

        meta = {
            "original_norm": original_norm,
            "clipped_norm": float(np.linalg.norm(clipped_weights)),
            "noise_std": float(sigma),
            "clip_norm_threshold": self.clip_norm
        }

        return privatized_weights, meta
