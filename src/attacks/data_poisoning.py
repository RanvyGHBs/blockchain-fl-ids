"""
Data Poisoning / Label-Flipping Attacks.
Adversaries flip target labels in local training batches to blind the IDS model to specific cyber-attacks.
"""

from typing import Tuple
import numpy as np


def apply_label_flipping_attack(y: np.ndarray, source_class: int = 1, target_class: int = 0,
                                flip_ratio: float = 1.0, seed: int = None) -> np.ndarray:
    """
    Label-Flipping Attack:
    Flipped labels mimic insidious Trojan/backdoor training.
    For binary classification: Attack (1) is flipped to Normal (0), blinding the model to intrusions.
    """
    if seed is not None:
        np.random.seed(seed)

    y_poisoned = y.copy()
    target_indices = np.where(y == source_class)[0]

    if flip_ratio < 1.0:
        num_to_flip = int(len(target_indices) * flip_ratio)
        target_indices = np.random.choice(target_indices, size=num_to_flip, replace=False)

    y_poisoned[target_indices] = target_class
    return y_poisoned
