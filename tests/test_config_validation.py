"""
Configuration and Reputation Validation Test Suite.

Verifies valid approved WP2/WP3 baseline configurations alongside rejection of
invalid client counts, round counts, DP parameters, clipping bounds, noise
parameters, reputation thresholds, reward/penalty settings, and inconsistent
parameter combinations.
"""

import math
import pytest

from src.config import (
    APPROVED_CLIENTS_COUNT,
    APPROVED_CLIP_NORM,
    APPROVED_COMMUNICATION_ROUNDS,
    APPROVED_NOISE_MULTIPLIER,
    APPROVED_TARGET_DELTA,
    ExecutionMode,
    PrivacyRandomnessMode,
    get_approved_research_config,
    validate_config,
)
from src.privacy.rdp_accountant import RDPAccountant
from src.trust.reputation import ReputationManager


class TestApprovedConfigurationPreservation:
    """Confirms active WP2/WP3 defaults stay consistent with approved baseline."""

    def test_approved_research_config_defaults(self):
        cfg = get_approved_research_config()
        assert cfg.execution_mode == ExecutionMode.RESEARCH_SIMULATION
        assert cfg.privacy_randomness_mode == PrivacyRandomnessMode.OS_CSPRNG
        assert cfg.dp_enabled is True
        assert cfg.num_clients == APPROVED_CLIENTS_COUNT == 5
        assert cfg.communication_rounds == APPROVED_COMMUNICATION_ROUNDS == 5
        assert cfg.num_rounds == APPROVED_COMMUNICATION_ROUNDS == 5
        assert cfg.dp_clip_norm == APPROVED_CLIP_NORM == 1.0
        assert cfg.dp_noise_multiplier == APPROVED_NOISE_MULTIPLIER == 1.0
        assert cfg.dp_target_delta == APPROVED_TARGET_DELTA == 1e-5
        assert cfg.norm_min_factor == 0.75
        assert cfg.norm_margin_factor == 1.25
        assert cfg.calibrated_cosine_threshold == 0.10
        assert cfg.calibrated_loss_factor == 5.0

        acct = RDPAccountant()
        acct.step(noise_multiplier=cfg.dp_noise_multiplier, rounds=cfg.communication_rounds)
        eps, alpha = acct.get_epsilon(delta=cfg.dp_target_delta)
        assert alpha == 3.0
        assert math.isclose(eps, 13.2565, abs_tol=1e-4)

    def test_reputation_manager_approved_defaults(self):
        mgr = ReputationManager(client_ids=[0, 1, 2, 3, 4])
        assert mgr.reward_delta == 0.05
        assert mgr.slash_delta == 0.35
        assert mgr.quarantine_threshold == 0.40
        assert mgr.probation_rounds == 3
        assert all(mgr.get_reputation(cid) == 1.0 for cid in range(5))

    def test_reputation_slash_magnitude_reward_quarantine_and_probation(self):
        """Confirms slash_delta is a positive magnitude subtracted internally (+0.05 / -0.35 / <0.40 / 3-round)."""
        mgr = ReputationManager(client_ids=[0, 1])

        # Reward increases up to ceiling 1.0, slash subtracts 0.35 -> 0.65 (still active)
        mgr.update_reputation({0: {"is_valid": True}, 1: {"is_valid": False}})
        assert mgr.get_reputation(0) == 1.0
        assert mgr.get_reputation(1) == 0.65
        assert not mgr.is_quarantined(1)

        # Second slash: 0.65 - 0.35 = 0.30 < 0.40 -> triggers quarantine
        mgr.update_reputation({0: {"is_valid": True}, 1: {"is_valid": False}})
        assert mgr.get_reputation(1) == 0.30
        assert mgr.is_quarantined(1)

        # 3 consecutive valid rounds in shadow probation rehabilitate client to 0.50
        for _ in range(3):
            mgr.update_reputation({1: {"is_valid": True}})
        assert not mgr.is_quarantined(1)
        assert mgr.get_reputation(1) == 0.50

    def test_get_approved_research_config_num_rounds_preserves_dp_baseline(self):
        """Changing num_rounds keeps C, sigma, delta, clients, and randomness untouched."""
        cfg = get_approved_research_config(num_rounds=2)
        assert cfg.num_rounds == 2
        assert cfg.communication_rounds == 2
        assert cfg.num_clients == APPROVED_CLIENTS_COUNT == 5
        assert cfg.dp_enabled is True
        assert cfg.dp_clip_norm == APPROVED_CLIP_NORM == 1.0
        assert cfg.dp_noise_multiplier == APPROVED_NOISE_MULTIPLIER == 1.0
        assert cfg.dp_target_delta == APPROVED_TARGET_DELTA == 1e-5
        assert cfg.execution_mode == ExecutionMode.RESEARCH_SIMULATION
        assert cfg.privacy_randomness_mode == PrivacyRandomnessMode.OS_CSPRNG

        acct = RDPAccountant()
        acct.step(noise_multiplier=cfg.dp_noise_multiplier, rounds=cfg.communication_rounds)
        eps, alpha = acct.get_epsilon(delta=cfg.dp_target_delta)
        assert math.isclose(eps, 7.8376, abs_tol=1e-4)
        assert alpha == 4.0

    def test_valid_test_mode_override_roundtrip(self):
        cfg = validate_config(
            {
                "execution_mode": "TEST",
                "privacy_randomness_mode": "DETERMINISTIC_TEST",
                "num_clients": 3,
                "num_rounds": 2,
                "dp_enabled": False,
                "dp_clip_norm": 2.0,
                "dp_noise_multiplier": 0.0,
                "dp_target_delta": 1e-4,
                "norm_min_factor": 0.5,
                "norm_margin_factor": 1.5,
            }
        )
        assert cfg.execution_mode == ExecutionMode.TEST
        assert cfg.num_clients == 3
        assert cfg.communication_rounds == 2
        assert cfg.num_rounds == 2


class TestInvalidFederatedAndDPConfiguration:
    """Verifies validate_config rejects invalid counts, DP settings, and combinations."""

    @pytest.mark.parametrize("bad_clients", [0, -1, -5, True, 2.5, "5"])
    def test_invalid_client_counts_rejected(self, bad_clients):
        with pytest.raises(ValueError, match="num_clients"):
            validate_config({"num_clients": bad_clients})

    @pytest.mark.parametrize("bad_rounds", [0, -3, False, 1.5, "5"])
    def test_invalid_round_counts_rejected(self, bad_rounds):
        with pytest.raises(ValueError, match="rounds"):
            validate_config({"num_rounds": bad_rounds})

    def test_inconsistent_round_counts_rejected(self):
        with pytest.raises(ValueError, match="Inconsistent round configuration"):
            validate_config({"num_rounds": 3, "communication_rounds": 5})

    @pytest.mark.parametrize("bad_clip", [0.0, -1.0, float("nan"), float("inf"), True])
    def test_invalid_clipping_bounds_rejected(self, bad_clip):
        with pytest.raises(ValueError, match="dp_clip_norm"):
            validate_config({"dp_clip_norm": bad_clip})

    @pytest.mark.parametrize("bad_noise", [-0.1, -5.0, float("nan"), float("inf"), False])
    def test_invalid_noise_multipliers_rejected(self, bad_noise):
        with pytest.raises(ValueError, match="dp_noise_multiplier"):
            validate_config({"dp_noise_multiplier": bad_noise})

    @pytest.mark.parametrize("bad_delta", [0.0, 1.0, -1e-5, 1.5, float("nan"), float("inf"), True])
    def test_invalid_target_delta_rejected(self, bad_delta):
        with pytest.raises(ValueError, match="dp_target_delta"):
            validate_config({"dp_target_delta": bad_delta})

    def test_inconsistent_norm_bounds_rejected(self):
        with pytest.raises(ValueError, match="Inconsistent norm bounds"):
            validate_config({"norm_min_factor": 1.5, "norm_margin_factor": 1.25})

    @pytest.mark.parametrize("bad_cos", [-1.1, 1.1, float("nan")])
    def test_invalid_cosine_threshold_rejected(self, bad_cos):
        with pytest.raises(ValueError, match="cosine_threshold"):
            validate_config({"calibrated_cosine_threshold": bad_cos})

    def test_inconsistent_malicious_client_ids_rejected(self):
        with pytest.raises(ValueError, match="Inconsistent attack configuration"):
            validate_config(
                {
                    "num_clients": 4,
                    "attack_enabled": True,
                    "malicious_client_ids": [0, 4],
                }
            )


class TestReputationParameterValidation:
    """Verifies ReputationManager rejects invalid thresholds, rewards, and penalties."""

    def test_empty_client_ids_rejected(self):
        with pytest.raises(ValueError, match="client_ids"):
            ReputationManager(client_ids=[])

    @pytest.mark.parametrize("bad_init", [-0.1, 1.1, float("nan"), True])
    def test_invalid_initial_reputation_rejected(self, bad_init):
        with pytest.raises(ValueError, match="initial_reputation"):
            ReputationManager(client_ids=[0, 1], initial_reputation=bad_init)

    @pytest.mark.parametrize("bad_thresh", [-0.05, 1.05, float("inf"), False])
    def test_invalid_quarantine_threshold_rejected(self, bad_thresh):
        with pytest.raises(ValueError, match="quarantine_threshold"):
            ReputationManager(client_ids=[0, 1], quarantine_threshold=bad_thresh)

    @pytest.mark.parametrize("bad_reward", [-0.01, 1.5, float("nan"), True])
    def test_invalid_reward_delta_rejected(self, bad_reward):
        with pytest.raises(ValueError, match="reward_delta"):
            ReputationManager(client_ids=[0, 1], reward_delta=bad_reward)

    @pytest.mark.parametrize("bad_slash", [-0.35, -0.2, 1.2, float("inf"), False])
    def test_invalid_slash_delta_rejected(self, bad_slash):
        with pytest.raises(ValueError, match="slash_delta"):
            ReputationManager(client_ids=[0, 1], slash_delta=bad_slash)

    @pytest.mark.parametrize("bad_probation", [0, -2, True, 1.5])
    def test_invalid_probation_rounds_rejected(self, bad_probation):
        with pytest.raises(ValueError, match="probation_rounds"):
            ReputationManager(client_ids=[0, 1], probation_rounds=bad_probation)

    def test_validate_config_checks_reputation_keys_when_present(self):
        with pytest.raises(ValueError, match="quarantine_threshold"):
            validate_config({"quarantine_threshold": 1.5})
