"""
Model Poisoning Attacks for Federated Learning.
Adversaries manipulate local model weights before transmitting them to the aggregator.
"""

from typing import Dict, Any
import numpy as np


def apply_gaussian_noise_attack(weights: np.ndarray, std: float = 1.5, seed: int = None) -> np.ndarray:
    """
    Gaussian Noise Attack:
    Adds zero-mean Gaussian perturbation to the honest model weights.
    w_poisoned = w_honest + N(0, std^2)
    """
    if seed is not None:
        np.random.seed(seed)
    noise = np.random.normal(0.0, std, size=weights.shape).astype(np.float32)
    return weights + noise


def apply_sign_flipping_attack(weights: np.ndarray, scale: float = -2.0) -> np.ndarray:
    """
    Sign-Flipping Attack:
    Inverts the sign of weights and scales them.
    w_poisoned = scale * w_honest
    """
    return (scale * weights).astype(np.float32)


def apply_model_scaling_attack(weights: np.ndarray, scale_factor: float = 10.0) -> np.ndarray:
    """
    Model Scaling Attack:
    Scales local weights by a large factor so that upon aggregation,
    the adversary's update dominates the global model.
    """
    return (scale_factor * weights).astype(np.float32)
