"""
Stage 2D: Parameterized Stealth-Constrained Byzantine Perturbation Module.
Implements a parameterized stealth-constrained Byzantine perturbation using geometric threshold alignment
to evaluate Multi-Criteria Trust filters:
1. Tier-1 Norm Bounding: Scales ||w_adv||_2 <= tau_norm * ||w_global||_2 * (1 - epsilon).
2. Tier-2 Cosine Consensus: Blends perturbation with peer direction to guarantee cos(w_adv, w_peer) >= tau_cos + epsilon.
3. Tier-3 Validation Loss: Modulates perturbation magnitude via a stealth factor to avoid immediate validation loss spikes.

Threat Model Clarification:
This implementation is a parameterized stealth-constrained perturbation using geometric threshold alignment
against static multi-criteria filtering boundaries. It is NOT a closed-loop feedback-adaptive attacker.
"""

from typing import Optional, Dict, Any, Tuple
import numpy as np


def generate_adaptive_byzantine_update(
    honest_weights: np.ndarray,
    global_weights: np.ndarray,
    median_vector: Optional[np.ndarray] = None,
    norm_threshold_factor: float = 2.5,
    cosine_threshold: float = 0.15,
    loss_headroom: float = 0.5,
    stealth_factor: float = 0.8,
    target_direction: Optional[np.ndarray] = None,
    seed: Optional[int] = None
) -> np.ndarray:
    """
    Synthesizes a parameterized stealth-constrained Byzantine perturbation using geometric threshold
    alignment engineered to evaluate Tier-1 and Tier-2 trust thresholds while inducing parameter drift
    (not a closed-loop feedback-adaptive attack).
    
    Args:
        honest_weights: The authentic weights computed by the client during local SGD.
        global_weights: The current global weights distributed at the start of the round.
        median_vector: Estimated peer consensus direction (or global_weights if peer median unknown).
        norm_threshold_factor: Multiplier for maximum allowable L2 norm (default 2.5).
        cosine_threshold: Minimum cosine similarity to pass Tier-2 filter (default 0.15).
        loss_headroom: Desired safety buffer below the loss threshold.
        stealth_factor: Tuning parameter in (0, 1] balancing aggressiveness vs stealthiness.
                        Higher stealth factor stays closer to consensus; lower is more aggressive.
        target_direction: Adversarial disturbance direction (e.g. inverted gradient or targeted shift).
        seed: Random seed for perturbation.

    Returns:
        Calibrated adversarial weight vector as a float32 numpy array.
    """
    if seed is not None:
        rng = np.random.RandomState(seed)
    else:
        rng = np.random.RandomState()

    reference_vector = median_vector if median_vector is not None else honest_weights
    global_norm = float(np.linalg.norm(global_weights))
    max_norm_allowed = max(1.0, global_norm * norm_threshold_factor)

    # 1. Determine adversarial disturbance direction
    if target_direction is not None:
        adv_dir = target_direction.astype(np.float32)
        adv_dir_norm = np.linalg.norm(adv_dir)
        if adv_dir_norm > 1e-9:
            adv_dir = adv_dir / adv_dir_norm
    else:
        # Default: Invert the local gradient direction (w_global - w_honest) and add controlled noise
        grad = (honest_weights - global_weights)
        grad_norm = np.linalg.norm(grad)
        if grad_norm > 1e-9:
            inv_grad = -grad / grad_norm
        else:
            inv_grad = -honest_weights / (np.linalg.norm(honest_weights) + 1e-9)

        noise = rng.normal(0.0, 1.0, size=honest_weights.shape).astype(np.float32)
        noise_norm = np.linalg.norm(noise)
        if noise_norm > 1e-9:
            noise = noise / noise_norm
        adv_dir = (0.7 * inv_grad + 0.3 * noise).astype(np.float32)

    # 2. Blend adversarial direction with reference direction to satisfy Cosine Consensus
    # We want: cos(w_adv, reference_vector) >= cosine_threshold + epsilon_safety
    epsilon_safety = 0.10
    target_min_cosine = min(0.90, cosine_threshold + epsilon_safety)

    ref_norm = np.linalg.norm(reference_vector)
    ref_unit = reference_vector / (ref_norm + 1e-9)

    # Decompose adv_dir into orthogonal component to reference_vector
    proj_coeff = float(np.dot(adv_dir, ref_unit))
    orth_dir = adv_dir - proj_coeff * ref_unit
    orth_norm = np.linalg.norm(orth_dir)
    if orth_norm > 1e-9:
        orth_unit = orth_dir / orth_norm
    else:
        orth_unit = np.zeros_like(adv_dir)

    # Construct unit direction with controlled cosine to reference:
    # cos(theta) = cos_val => sin(theta) = sqrt(1 - cos_val^2)
    # Blend according to stealth factor: higher stealth factor -> higher cosine
    effective_cosine = target_min_cosine + (1.0 - target_min_cosine) * (0.3 + 0.6 * stealth_factor)
    effective_cosine = min(0.95, max(target_min_cosine, effective_cosine))

    sin_val = np.sqrt(max(0.0, 1.0 - effective_cosine ** 2))
    calibrated_unit = (effective_cosine * ref_unit + sin_val * orth_unit).astype(np.float32)

    # 3. Scale magnitude to strictly satisfy Tier-1 L2 Norm bound
    # ||w_adv|| <= max_norm_allowed * (1 - norm_margin)
    norm_margin = 0.10
    target_norm = min(
        float(np.linalg.norm(honest_weights)) * (1.0 + 0.5 * (1.0 - stealth_factor)),
        max_norm_allowed * (1.0 - norm_margin)
    )

    w_adv = (calibrated_unit * target_norm).astype(np.float32)

    # Final guarantee check: if norm still exceeds ceiling, project strictly down
    final_norm = float(np.linalg.norm(w_adv))
    if final_norm > max_norm_allowed * (1.0 - norm_margin):
        w_adv = (w_adv / final_norm) * (max_norm_allowed * (1.0 - norm_margin))

    return w_adv.astype(np.float32)


def verify_evasion_criteria(
    candidate_weights: np.ndarray,
    global_weights: np.ndarray,
    median_vector: np.ndarray,
    norm_threshold_factor: float = 2.5,
    cosine_threshold: float = 0.15
) -> Dict[str, Any]:
    """
    Evaluates whether an adaptive Byzantine update satisfies the mathematical
    evasion criteria for Tier-1 (Norm) and Tier-2 (Cosine) filters.
    """
    cand_norm = float(np.linalg.norm(candidate_weights))
    glob_norm = float(np.linalg.norm(global_weights))
    max_allowed_norm = max(1.0, glob_norm * norm_threshold_factor)
    norm_evaded = cand_norm <= max_allowed_norm

    med_norm = float(np.linalg.norm(median_vector))
    norm_prod = cand_norm * med_norm
    if norm_prod > 1e-9:
        cos_sim = float(np.dot(candidate_weights, median_vector) / norm_prod)
    else:
        cos_sim = 1.0

    cosine_evaded = cos_sim >= cosine_threshold

    return {
        "candidate_norm": cand_norm,
        "max_allowed_norm": max_allowed_norm,
        "norm_evaded": norm_evaded,
        "cosine_similarity": cos_sim,
        "cosine_threshold": cosine_threshold,
        "cosine_evaded": cosine_evaded,
        "both_tiers_evaded": norm_evaded and cosine_evaded
    }
