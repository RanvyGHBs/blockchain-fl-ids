"""
Multi-Criteria Trust and Adversarial Defense Engine.
Implements L2-norm verification, pairwise cosine similarity, benchmark loss validation,
and dynamic asymmetric reputation management.
"""

from src.trust.evaluator import MultiCriteriaTrustEngine
from src.trust.reputation import ReputationManager

__all__ = ["MultiCriteriaTrustEngine", "ReputationManager"]
