"""
Stage 2D: Targeted Label-Flipping Attack Module.
Adversaries manipulate specific class labels (e.g., DoS -> Normal) in local client
training partitions, attempting to poison decision boundaries for specific threat categories
while preserving benign performance on unaffected classes.

Includes:
- apply_targeted_label_flipping_attack: source-to-target class flipping with configurable ratio.
- compute_attack_success_rate (ASR): fraction of source-class samples classified as target class.
- compute_clean_accuracy: accuracy on non-source class samples (or overall clean test data).
"""

from typing import Tuple, Optional
import numpy as np


def apply_targeted_label_flipping_attack(
    y: np.ndarray,
    source_class: int,
    target_class: int,
    flip_ratio: float = 1.0,
    seed: Optional[int] = None
) -> Tuple[np.ndarray, int]:
    """
    Applies targeted label-flipping data poisoning to a local label array.
    
    Args:
        y: Original integer or categorical label array.
        source_class: Target class to be manipulated (e.g., Attack/Intrusion class).
        target_class: Benign or adversary-selected class to replace source labels (e.g., Normal class).
        flip_ratio: Fraction of source_class samples to flip (0.0 to 1.0).
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (y_poisoned, modified_count)
    """
    if source_class == target_class:
        return y.copy(), 0

    if seed is not None:
        rng = np.random.RandomState(seed)
    else:
        rng = np.random.RandomState()

    y_poisoned = y.copy()
    source_indices = np.where(y == source_class)[0]
    total_source = len(source_indices)

    if total_source == 0:
        return y_poisoned, 0

    clamp_ratio = max(0.0, min(1.0, float(flip_ratio)))
    num_to_flip = int(np.round(total_source * clamp_ratio))

    if num_to_flip == 0 and clamp_ratio > 0.0 and total_source > 0:
        num_to_flip = 1

    if num_to_flip > 0:
        selected_indices = rng.choice(source_indices, size=num_to_flip, replace=False)
        y_poisoned[selected_indices] = target_class
        return y_poisoned, num_to_flip

    return y_poisoned, 0


def compute_attack_success_rate(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    source_class: int,
    target_class: int
) -> float:
    """
    Computes the Attack Success Rate (ASR) of a targeted label-flipping attack:
        ASR = (sum_{i: y_i = source} I(y_pred_i = target)) / (sum_i I(y_i = source))

    Args:
        y_true: True ground-truth labels.
        y_pred: Predicted class labels from model.
        source_class: The targeted class intended to be misclassified.
        target_class: The adversarial destination class.

    Returns:
        ASR as a float between 0.0 and 1.0. Returns 0.0 if no source_class samples exist.
    """
    source_mask = (y_true == source_class)
    total_source = np.sum(source_mask)

    if total_source == 0:
        return 0.0

    successful_attacks = np.sum((y_pred == target_class) & source_mask)
    return float(successful_attacks / total_source)


def compute_clean_accuracy(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    source_class: Optional[int] = None
) -> float:
    """
    Computes accuracy on the clean, unaffected subset of the evaluation data.
    If source_class is specified, evaluates accuracy exclusively on samples where y_true != source_class.
    If source_class is None, evaluates standard overall accuracy.

    Args:
        y_true: True ground-truth labels.
        y_pred: Predicted class labels.
        source_class: Optional class index excluded from clean evaluation.

    Returns:
        Clean accuracy as a float between 0.0 and 1.0.
    """
    if len(y_true) == 0:
        return 0.0

    if source_class is not None:
        clean_mask = (y_true != source_class)
        if np.sum(clean_mask) == 0:
            # Fallback to overall accuracy if no other classes exist
            return float(np.mean(y_true == y_pred))
        return float(np.mean(y_true[clean_mask] == y_pred[clean_mask]))

    return float(np.mean(y_true == y_pred))
