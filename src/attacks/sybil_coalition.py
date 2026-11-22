"""
Stage 2D: Sybil Coalition Attack Module.
Simulates multiple colluding adversaries that coordinate their weight updates
to distort robust aggregators (such as Coordinate-wise Median and Trimmed Mean).

By forming a synchronized coalition, adversaries attempt to pull aggregate coordinate
statistics past the breakdown threshold of median-based aggregation, whereas the
Multi-Criteria Trust Engine detects and slashes the colluding cluster.
"""

from typing import List, Dict, Tuple, Optional, Any
import numpy as np


def generate_sybil_coalition_updates(
    base_weights: np.ndarray,
    coalition_client_ids: List[int],
    target_direction: Optional[np.ndarray] = None,
    intensity: float = 2.0,
    seed: Optional[int] = None,
    add_noise: bool = False,
    noise_std: float = 0.01
) -> Dict[int, np.ndarray]:
    """
    Generates coordinated weight vectors for a coalition of colluding Sybil clients.
    
    All coalition members submit a synchronized update pointing in a chosen adversarial
    direction, designed to overpower coordinate-wise median or trimmed-mean filters.
    
    Args:
        base_weights: Base model weights (e.g. current global weights or an honest client's weights).
        coalition_client_ids: List of client IDs participating in the Sybil coalition.
        target_direction: Optional directional perturbation vector. If None, uses inverted weights (-base_weights).
        intensity: Scaling factor for the adversarial shift (gamma).
        seed: Random seed for optional jitter.
        add_noise: Whether to inject slight variance among coalition members to avoid exact identical hashes.
        noise_std: Standard deviation of evasion jitter.

    Returns:
        Dict mapping client_id -> coordinated adversarial weight vector.
    """
    if len(coalition_client_ids) == 0:
        return {}

    if target_direction is not None:
        direction = target_direction.astype(np.float32)
        norm = np.linalg.norm(direction)
        if norm > 1e-9:
            direction = direction / norm
        shift = (intensity * direction * (np.linalg.norm(base_weights) + 1.0)).astype(np.float32)
        coordinated_vector = (base_weights + shift).astype(np.float32)
    else:
        # Default: Inverted and scaled shift targeting model collapse
        coordinated_vector = (-intensity * base_weights).astype(np.float32)

    rng = np.random.RandomState(seed) if seed is not None else np.random.RandomState()
    coalition_updates: Dict[int, np.ndarray] = {}

    for cid in coalition_client_ids:
        if add_noise and noise_std > 0:
            jitter = rng.normal(0.0, noise_std, size=base_weights.shape).astype(np.float32)
            coalition_updates[cid] = (coordinated_vector + jitter).astype(np.float32)
        else:
            coalition_updates[cid] = coordinated_vector.copy()

    return coalition_updates


def evaluate_median_distortion(
    honest_weights_list: List[np.ndarray],
    sybil_weights_list: List[np.ndarray]
) -> Dict[str, float]:
    """
    Quantifies the mathematical distortion inflicted by a Sybil coalition on Coordinate-wise Median aggregation.
    
    Calculates:
    - honest_median: Median across honest nodes alone.
    - corrupted_median: Median across honest + Sybil nodes.
    - l2_distortion: ||corrupted_median - honest_median||_2
    - relative_distortion: l2_distortion / ||honest_median||_2

    Args:
        honest_weights_list: List of weight arrays from honest clients.
        sybil_weights_list: List of weight arrays from Sybil coalition clients.

    Returns:
        Dict containing distortion metrics.
    """
    if len(honest_weights_list) == 0:
        raise ValueError("Honest weights list cannot be empty.")

    honest_stacked = np.stack(honest_weights_list, axis=0)
    honest_median = np.median(honest_stacked, axis=0).astype(np.float32)
    honest_norm = float(np.linalg.norm(honest_median))

    if len(sybil_weights_list) == 0:
        return {
            "l2_distortion": 0.0,
            "relative_distortion": 0.0,
            "honest_median_norm": honest_norm,
            "corrupted_median_norm": honest_norm,
            "coalition_size": 0,
            "honest_size": len(honest_weights_list)
        }

    combined_list = honest_weights_list + sybil_weights_list
    combined_stacked = np.stack(combined_list, axis=0)
    corrupted_median = np.median(combined_stacked, axis=0).astype(np.float32)

    l2_distortion = float(np.linalg.norm(corrupted_median - honest_median))
    rel_distortion = float(l2_distortion / max(1e-9, honest_norm))

    return {
        "l2_distortion": l2_distortion,
        "relative_distortion": rel_distortion,
        "honest_median_norm": honest_norm,
        "corrupted_median_norm": float(np.linalg.norm(corrupted_median)),
        "coalition_size": len(sybil_weights_list),
        "honest_size": len(honest_weights_list)
    }
