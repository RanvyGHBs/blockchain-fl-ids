"""
Formal Rényi Differential Privacy (RDP) Accountant for Federated Learning (WP2).
Implements compositional RDP tracking and discrete-order approximate (epsilon, delta)-DP conversion
for client-level Gaussian perturbation across adaptive federated rounds.
"""

from typing import List, Dict, Any, Tuple, Optional, Sequence
import math
import numpy as np

# Configurable discrete set of supported Rényi orders (alpha > 1)
DEFAULT_RDP_ORDERS: List[float] = [
    1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 16.0, 24.0, 32.0, 64.0, 128.0
]


class RDPAccountant:
    """
    Rényi Differential Privacy (RDP) Accountant for Client-Level Gaussian Perturbation.
    
    Mathematical Foundations (Mironov 2017, Bun & Steinke 2016):
        - Replace-one-client-dataset global sensitivity S = 2C.
        - Noise std sigma_noise = 2 * sigma * C.
        - Per-round RDP bound:
            epsilon_RDP(alpha) <= alpha / (2 * sigma^2)
        - Composition over T adaptive rounds:
            epsilon_RDP^(T)(alpha) <= sum_{t=1}^T alpha / (2 * sigma_t^2)
        - Conversion to approximate (epsilon, delta)-DP:
            epsilon(delta) = min_{alpha > 1} [ epsilon_RDP^(T)(alpha) + ln(1 / delta) / (alpha - 1) ]
    """

    def __init__(self, orders: Optional[Sequence[float]] = None):
        """
        Initializes the RDP accountant.

        Args:
            orders: Sequence of Rényi orders alpha > 1. If None, uses DEFAULT_RDP_ORDERS.
        """
        raw_orders = list(orders) if orders is not None else DEFAULT_RDP_ORDERS
        
        # Validate orders: all must be real numbers strictly greater than 1.0
        cleaned_orders = []
        for a in raw_orders:
            if not isinstance(a, (int, float)) or math.isnan(a) or math.isinf(a) or a <= 1.0:
                raise ValueError(f"Rényi orders must be finite real numbers strictly greater than 1.0, got {a}")
            cleaned_orders.append(float(a))

        self.orders: List[float] = sorted(list(set(cleaned_orders)))
        if len(self.orders) == 0:
            raise ValueError("RDPAccountant requires at least one valid Rényi order alpha > 1.0.")

        # Cumulative RDP budget indexed by alpha
        self.cumulative_rdp: Dict[float, float] = {alpha: 0.0 for alpha in self.orders}
        
        # Execution history of privacy releases
        self.history: List[Dict[str, Any]] = []

    def step(self, noise_multiplier: float, clip_norm: float = 1.0, rounds: int = 1) -> Dict[str, Any]:
        """
        Records an executed privacy release step across one or more rounds.

        Args:
            noise_multiplier: sigma parameter defining noise std relative to sensitivity (2 * sigma * C).
            clip_norm: L2 clipping bound C > 0.
            rounds: Number of executed rounds with this mechanism configuration.

        Returns:
            Dictionary detailing the incremental RDP added by this step.
        """
        if not isinstance(noise_multiplier, (int, float)) or math.isnan(noise_multiplier) or math.isinf(noise_multiplier) or noise_multiplier <= 0:
            raise ValueError(f"noise_multiplier must be a positive finite real number, got {noise_multiplier}")
        if not isinstance(rounds, int) or rounds < 1:
            raise ValueError(f"rounds must be a positive integer, got {rounds}")

        sigma = float(noise_multiplier)
        step_rdp = {}

        for alpha in self.orders:
            # Per-round RDP: alpha / (2 * sigma^2)
            # For 'rounds' repetitions: rounds * alpha / (2 * sigma^2)
            delta_rdp = float(rounds * alpha / (2.0 * (sigma ** 2)))
            self.cumulative_rdp[alpha] += delta_rdp
            step_rdp[alpha] = delta_rdp

        step_record = {
            "step_index": len(self.history) + 1,
            "rounds_counted": rounds,
            "total_rounds_executed": sum(h["rounds_counted"] for h in self.history) + rounds,
            "noise_multiplier": sigma,
            "clip_norm": float(clip_norm),
            "sensitivity": 2.0 * float(clip_norm),
            "step_rdp": step_rdp
        }
        self.history.append(step_record)
        return step_record

    def get_rdp(self, alpha: float) -> float:
        """
        Returns cumulative RDP epsilon for a specific supported order alpha.
        """
        if alpha not in self.cumulative_rdp:
            # Calculate directly if valid order > 1.0
            if isinstance(alpha, (int, float)) and not math.isnan(alpha) and not math.isinf(alpha) and alpha > 1.0:
                total_rdp = 0.0
                for h in self.history:
                    sigma = h["noise_multiplier"]
                    rounds = h["rounds_counted"]
                    total_rdp += float(rounds * alpha / (2.0 * (sigma ** 2)))
                return total_rdp
            raise ValueError(f"Order alpha={alpha} is invalid or not in supported set.")
        return float(self.cumulative_rdp[alpha])

    def get_rdp_spectrum(self) -> Dict[float, float]:
        """
        Returns the full spectrum of cumulative RDP values across all configured orders.
        """
        return {alpha: float(self.cumulative_rdp[alpha]) for alpha in self.orders}

    def get_epsilon(self, delta: float) -> Tuple[float, float]:
        """
        Converts cumulative RDP to approximate (epsilon, delta)-DP via discrete order minimization:
            epsilon(delta) = min_{alpha > 1} [ epsilon_RDP(alpha) + ln(1 / delta) / (alpha - 1) ]

        Args:
            delta: Privacy failure parameter delta strictly in (0, 1).

        Returns:
            Tuple of (optimal_epsilon, optimal_alpha)
        """
        if not isinstance(delta, (int, float)) or math.isnan(delta) or math.isinf(delta):
            raise ValueError(f"delta must be a finite real number, got {delta}")
        if delta <= 0.0 or delta >= 1.0:
            raise ValueError(f"delta must be strictly within the open interval (0, 1), got {delta}")

        # If zero releases have occurred, privacy loss is strictly zero
        if len(self.history) == 0:
            return 0.0, self.orders[0]

        best_eps = float("inf")
        best_alpha = self.orders[0]
        log_inv_delta = math.log(1.0 / float(delta))

        for alpha in self.orders:
            rdp_val = self.cumulative_rdp[alpha]
            converted_eps = float(rdp_val + log_inv_delta / (alpha - 1.0))
            if converted_eps < best_eps:
                best_eps = converted_eps
                best_alpha = alpha

        return best_eps, best_alpha

    def get_completed_rounds(self) -> int:
        """Returns total number of privacy-relevant rounds recorded."""
        return sum(h["rounds_counted"] for h in self.history)

    def summary(self, delta: float = 1e-5) -> Dict[str, Any]:
        """
        Generates a comprehensive scientific summary of the privacy guarantee.

        Args:
            delta: Target delta parameter (default: 1e-5).

        Returns:
            Dictionary detailing parameters, bounds, assumptions, and limitations.
        """
        eps, opt_alpha = self.get_epsilon(delta)
        total_rounds = self.get_completed_rounds()
        
        last_sigma = self.history[-1]["noise_multiplier"] if self.history else None
        last_clip = self.history[-1]["clip_norm"] if self.history else None

        return {
            "mechanism": "Client-Level Gaussian Mechanism with RDP Accounting",
            "adjacency_definition": "Replace-one-client-dataset adjacency (D ~_replace D')",
            "federation_size_clients": 5,
            "completed_rounds": total_rounds,
            "total_rounds_executed": total_rounds,
            "target_delta": float(delta),
            "epsilon": float(eps),
            "optimal_epsilon": float(eps),
            "optimal_renyi_order_alpha": float(opt_alpha),
            "optimal_alpha": float(opt_alpha),
            "last_noise_multiplier_sigma": last_sigma,
            "last_clip_norm_C": last_clip,
            "sensitivity_S": 2.0 * last_clip if last_clip is not None else None,
            "noise_std_dev": 2.0 * last_sigma * last_clip if (last_sigma is not None and last_clip is not None) else None,
            "orders_evaluated_count": len(self.orders),
            "rdp_spectrum": self.get_rdp_spectrum(),
            "sampling_amplification": "None (Full client participation q = 1.0)",
            "threat_model": "Honest-but-curious server; individual client update releases protected",
            "metadata_exclusions": [
                "Fixed Dirichlet dataset partition cardinalities |D_k|",
                "Cryptographic signatures and transaction block commitments (protected via Data Processing Inequality)"
            ]
        }
