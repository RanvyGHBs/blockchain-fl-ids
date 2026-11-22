"""
Adversarial Attack Simulation Engine.
Implements Model Poisoning (Gaussian Noise, Sign Flipping, Model Scaling, Sybil Coalition, Adaptive Byzantine)
and Data Poisoning (Label Flipping, Targeted Label Flipping).
"""

from src.attacks.model_poisoning import (
    apply_gaussian_noise_attack,
    apply_sign_flipping_attack,
    apply_model_scaling_attack
)
from src.attacks.data_poisoning import apply_label_flipping_attack
from src.attacks.targeted_poisoning import (
    apply_targeted_label_flipping_attack,
    compute_attack_success_rate,
    compute_clean_accuracy
)
from src.attacks.sybil_coalition import (
    generate_sybil_coalition_updates,
    evaluate_median_distortion
)
from src.attacks.adaptive_byzantine import (
    generate_adaptive_byzantine_update,
    verify_evasion_criteria
)

__all__ = [
    "apply_gaussian_noise_attack",
    "apply_sign_flipping_attack",
    "apply_model_scaling_attack",
    "apply_label_flipping_attack",
    "apply_targeted_label_flipping_attack",
    "compute_attack_success_rate",
    "compute_clean_accuracy",
    "generate_sybil_coalition_updates",
    "evaluate_median_distortion",
    "generate_adaptive_byzantine_update",
    "verify_evasion_criteria"
]
