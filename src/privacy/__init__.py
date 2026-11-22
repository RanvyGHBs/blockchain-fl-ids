"""
Privacy-Preserving Learning Subsystem.
Implements clipping-based Gaussian update perturbation (without formal privacy accounting).
"""

from src.privacy.differential import LocalDifferentialPrivacy

__all__ = ["LocalDifferentialPrivacy"]
