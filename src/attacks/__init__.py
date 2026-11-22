"""
Adversarial Attack Simulation Engine.
Implements Model Poisoning (Gaussian Noise, Sign Flipping, Model Scaling)
and Data Poisoning (Label Flipping).
"""

from src.attacks.model_poisoning import (
    apply_gaussian_noise_attack,
    apply_sign_flipping_attack,
    apply_model_scaling_attack
)
from src.attacks.data_poisoning import apply_label_flipping_attack

__all__ = [
    "apply_gaussian_noise_attack",
    "apply_sign_flipping_attack",
    "apply_model_scaling_attack",
    "apply_label_flipping_attack"
]
