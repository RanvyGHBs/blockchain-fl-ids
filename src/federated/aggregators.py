"""
Federated Aggregation Algorithms.
Implements:
1. FedAvg (Standard weighted average by sample count).
2. Trimmed Mean (Coordinate-wise outlier trimming).
3. Coordinate-wise Median (Robust rank-based aggregation).
4. Trust-Weighted FedAvg (Weighted by sample count AND client reputation score).
"""

from typing import List, Dict, Optional
import numpy as np


def aggregate_fedavg(client_weights: List[np.ndarray], sample_counts: List[int]) -> np.ndarray:
    """
    Standard Federated Averaging (FedAvg):
        w_global = sum( (n_k / N_total) * w_k )
    """
    if len(client_weights) == 0:
        raise ValueError("Cannot aggregate empty client weights list.")

    total_samples = sum(sample_counts)
    if total_samples == 0:
        # Uniform average fallback
        return np.mean(client_weights, axis=0)

    weights_sum = np.zeros_like(client_weights[0])
    for w, n in zip(client_weights, sample_counts):
        weights_sum += (n / total_samples) * w

    return weights_sum.astype(np.float32)


def aggregate_trimmed_mean(client_weights: List[np.ndarray], beta: float = 0.2) -> np.ndarray:
    """
    Coordinate-wise Trimmed Mean:
    Sorts values at each coordinate and removes the top and bottom beta fraction.
    Provides Byzantine tolerance against coordinate-level outliers.
    """
    if len(client_weights) == 0:
        raise ValueError("Cannot aggregate empty client weights list.")

    stacked = np.stack(client_weights, axis=0)  # Shape: (K, D)
    k = stacked.shape[0]

    num_to_trim = int(beta * k)
    if num_to_trim == 0 or 2 * num_to_trim >= k:
        # Fall back to simple mean if K is small
        return np.mean(stacked, axis=0).astype(np.float32)

    # Sort along client axis
    sorted_weights = np.sort(stacked, axis=0)
    trimmed = sorted_weights[num_to_trim: k - num_to_trim, :]
    return np.mean(trimmed, axis=0).astype(np.float32)


def aggregate_median(client_weights: List[np.ndarray]) -> np.ndarray:
    """
    Coordinate-wise Median:
    Computes the median value across all clients for each individual weight coordinate.
    """
    if len(client_weights) == 0:
        raise ValueError("Cannot aggregate empty client weights list.")

    stacked = np.stack(client_weights, axis=0)
    return np.median(stacked, axis=0).astype(np.float32)


def aggregate_trust_weighted(client_weights: List[np.ndarray], sample_counts: List[int],
                             reputations: List[float]) -> np.ndarray:
    """
    Trust-Aware Adaptive Aggregation:
    Combines sample size and cryptographic reputation scores:
        weight_factor_k = n_k * max(0.01, R_k)
    Ensures penalized or quarantined clients have diminished or zero impact on the global model.
    """
    if len(client_weights) == 0:
        raise ValueError("Cannot aggregate empty client weights list.")

    effective_weights = [n * max(0.0, float(r)) for n, r in zip(sample_counts, reputations)]
    total_effective = sum(effective_weights)

    if total_effective <= 1e-9:
        # If all clients have zero reputation, return arithmetic mean
        return np.mean(client_weights, axis=0).astype(np.float32)

    weights_sum = np.zeros_like(client_weights[0])
    for w, eff in zip(client_weights, effective_weights):
        weights_sum += (eff / total_effective) * w

    return weights_sum.astype(np.float32)
