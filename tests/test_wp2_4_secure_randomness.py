"""
Test Suite for WP2.4: Secure Randomness Integration & Privacy Execution Separation.

Covers:
1. Deterministic TEST mode (reproducibility, seed isolation).
2. Secure RESEARCH_SIMULATION mode (OS-CSPRNG, fresh noise, independent streams, empirical std, fail-closed).
3. Execution-mode security (validation, rejection of insecure modes/seeds/legacy sigma, no silent fallback).
4. Orchestrator seed isolation (experiment seed separation, deployment client-local privacy, no seed distribution).
5. Mathematical and parameter invariant preservation (clipping, sensitivity 2C, noise scale 2*sigma*C, RDP).
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import math
from unittest import mock
import pytest
import numpy as np
import torch

from src.config import (
    ExecutionMode, PrivacyRandomnessMode, FLConfig, validate_config,
    get_approved_research_config, APPROVED_CLIP_NORM, APPROVED_NOISE_MULTIPLIER,
    APPROVED_TARGET_DELTA, APPROVED_COMMUNICATION_ROUNDS, LEGACY_UNCALIBRATED_NOISE_MULTIPLIER
)
from src.privacy.mechanism import ClientLevelDPMechanism, generate_csprng_gaussian
from src.privacy.rdp_accountant import RDPAccountant
from src.federated.orchestrator import FederatedOrchestrator
from src.federated.client import FederatedClient


# =====================================================================
# 1. Deterministic TEST Mode Tests
# =====================================================================

class TestDeterministicTestMode:
    """Verifies deterministic TEST mode isolation and reproducibility."""

    def test_same_seed_reproduces_same_noise(self):
        """Identical test seed produces identical perturbation vector."""
        mech1 = ClientLevelDPMechanism(
            clip_norm=1.0, noise_multiplier=1.0, seed=12345,
            execution_mode=ExecutionMode.TEST,
            privacy_randomness_mode=PrivacyRandomnessMode.DETERMINISTIC_TEST
        )
        mech2 = ClientLevelDPMechanism(
            clip_norm=1.0, noise_multiplier=1.0, seed=12345,
            execution_mode=ExecutionMode.TEST,
            privacy_randomness_mode=PrivacyRandomnessMode.DETERMINISTIC_TEST
        )
        v = np.ones(100, dtype=np.float32) * 0.5
        pert1, meta1 = mech1.privatize_update(v)
        pert2, meta2 = mech2.privatize_update(v)

        assert np.array_equal(pert1, pert2)
        assert meta1["execution_mode"] == "TEST"
        assert meta1["privacy_randomness_mode"] == "DETERMINISTIC_TEST"
        assert "TEST_PRNG" in meta1["randomness_source"]

    def test_different_seeds_produce_different_noise(self):
        """Distinct test seeds produce distinct noise draws."""
        mech1 = ClientLevelDPMechanism(
            clip_norm=1.0, noise_multiplier=1.0, seed=111,
            execution_mode=ExecutionMode.TEST
        )
        mech2 = ClientLevelDPMechanism(
            clip_norm=1.0, noise_multiplier=1.0, seed=222,
            execution_mode=ExecutionMode.TEST
        )
        v = np.ones(100, dtype=np.float32) * 0.5
        pert1, _ = mech1.privatize_update(v)
        pert2, _ = mech2.privatize_update(v)

        assert not np.array_equal(pert1, pert2)

    def test_test_mode_explicit_metadata_label(self):
        """All outputs in TEST mode are explicitly labelled as deterministic test outputs."""
        mech = ClientLevelDPMechanism(
            clip_norm=1.0, noise_multiplier=1.0, seed=42,
            execution_mode=ExecutionMode.TEST
        )
        v = np.zeros(50, dtype=np.float32)
        _, meta = mech.privatize_update(v)
        assert meta["execution_mode"] == "TEST"
        assert meta["privacy_randomness_mode"] == "DETERMINISTIC_TEST"
        assert "randomness_source" in meta


# =====================================================================
# 2. Secure RESEARCH_SIMULATION Mode Tests
# =====================================================================

class TestSecureResearchSimulationMode:
    """Verifies OS-CSPRNG Gaussian noise generation under RESEARCH_SIMULATION."""

    def test_csprng_gaussian_shape_and_dtype(self):
        """generate_csprng_gaussian returns correct shape and float32 dtype."""
        d = 1000
        noise = generate_csprng_gaussian(d, mean=0.0, std=2.0)
        assert isinstance(noise, np.ndarray)
        assert noise.shape == (d,)
        assert noise.dtype == np.float32

    def test_fresh_noise_on_every_invocation(self):
        """Consecutive invocations with identical parameters produce fresh, distinct noise."""
        mech = ClientLevelDPMechanism(
            clip_norm=1.0, noise_multiplier=1.0,
            execution_mode=ExecutionMode.RESEARCH_SIMULATION
        )
        v = np.ones(500, dtype=np.float32) * 0.1
        pert1, meta1 = mech.privatize_update(v)
        pert2, meta2 = mech.privatize_update(v)

        assert not np.array_equal(pert1, pert2)
        assert meta1["execution_mode"] == "RESEARCH_SIMULATION"
        assert meta1["privacy_randomness_mode"] == "OS_CSPRNG"
        assert meta1["randomness_source"] == "OS_CSPRNG"

    def test_noise_empirical_moments(self):
        """
        Validates empirical mean and standard deviation of OS-CSPRNG Gaussian noise.
        N=5000 samples, std = 2.0.
        """
        C = 1.0
        sigma = 1.0
        expected_std = 2.0 * sigma * C  # 2.0
        mech = ClientLevelDPMechanism(
            clip_norm=C, noise_multiplier=sigma,
            execution_mode=ExecutionMode.RESEARCH_SIMULATION
        )
        d = 5000
        zero_v = np.zeros(d, dtype=np.float32)
        pert, meta = mech.privatize_update(zero_v)

        emp_mean = float(np.mean(pert))
        emp_std = float(np.std(pert))

        # 4 standard errors tolerance
        mean_tol = 4.0 * expected_std / math.sqrt(d)
        std_tol = 4.0 * expected_std / math.sqrt(2 * d)

        assert abs(emp_mean - 0.0) < mean_tol, f"Mean {emp_mean} exceeds tolerance {mean_tol}"
        assert abs(emp_std - expected_std) < std_tol, f"Std {emp_std} exceeds tolerance {std_tol}"

    def test_no_secret_state_in_metadata(self):
        """Metadata never exposes random seeds, keys, generator state, or entropy bytes."""
        mech = ClientLevelDPMechanism(
            clip_norm=1.0, noise_multiplier=1.0,
            execution_mode=ExecutionMode.RESEARCH_SIMULATION
        )
        v = np.zeros(10, dtype=np.float32)
        _, meta = mech.privatize_update(v)

        forbidden_keys = {"seed", "key", "state", "entropy", "raw_bytes", "prng_state"}
        for k in meta:
            assert k.lower() not in forbidden_keys
            assert "secret" not in k.lower()

    def test_fail_closed_on_entropy_failure(self):
        """If OS entropy source fails, mechanism raises RuntimeError without falling back."""
        with mock.patch("os.urandom", side_effect=OSError("OS entropy source exhausted")):
            with pytest.raises(RuntimeError, match="failed"):
                generate_csprng_gaussian(100, mean=0.0, std=1.0)

        with mock.patch("os.urandom", side_effect=OSError("OS entropy source exhausted")):
            mech = ClientLevelDPMechanism(
                clip_norm=1.0, noise_multiplier=1.0,
                execution_mode=ExecutionMode.RESEARCH_SIMULATION
            )
            with pytest.raises(RuntimeError, match="failed"):
                mech.privatize_update(np.ones(10, dtype=np.float32))

    def test_zero_noise_restricted_to_test_mode(self):
        """Zero noise multiplier is restricted to explicitly non-private TEST mode and labelled non-private."""
        mech = ClientLevelDPMechanism(
            clip_norm=1.0, noise_multiplier=0.0,
            execution_mode=ExecutionMode.TEST
        )
        v = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        pert, meta = mech.privatize_update(v)
        assert np.allclose(pert, v)
        assert meta["noise_std"] == 0.0
        assert meta["is_private"] is False
        assert "NONE" in meta["privacy_guarantee"]
        assert meta["randomness_source"] == "NON_PRIVATE_ZERO_NOISE (TEST_ONLY)"

    def test_sigma_zero_rejected_in_research_simulation(self):
        """sigma = 0 in RESEARCH_SIMULATION is strictly rejected."""
        with pytest.raises(ValueError, match="noise_multiplier must be strictly positive"):
            ClientLevelDPMechanism(
                clip_norm=1.0, noise_multiplier=0.0,
                execution_mode=ExecutionMode.RESEARCH_SIMULATION
            )

        with pytest.raises(ValueError, match="dp_noise_multiplier must be strictly positive"):
            validate_config({
                "execution_mode": ExecutionMode.RESEARCH_SIMULATION,
                "dp_enabled": True,
                "dp_noise_multiplier": 0.0
            })

    def test_sigma_zero_rejected_in_deployment(self):
        """sigma = 0 in DEPLOYMENT is strictly rejected."""
        with pytest.raises(ValueError, match="noise_multiplier must be strictly positive"):
            ClientLevelDPMechanism(
                clip_norm=1.0, noise_multiplier=0.0,
                execution_mode=ExecutionMode.DEPLOYMENT
            )

        with pytest.raises(ValueError, match="dp_noise_multiplier must be strictly positive"):
            validate_config({
                "execution_mode": ExecutionMode.DEPLOYMENT,
                "dp_enabled": True,
                "dp_noise_multiplier": 0.0
            })

    def test_negative_sigma_rejected_in_all_modes(self):
        """Negative sigma is rejected across all modes."""
        for mode in [ExecutionMode.TEST, ExecutionMode.RESEARCH_SIMULATION, ExecutionMode.DEPLOYMENT]:
            with pytest.raises(ValueError, match="negative"):
                ClientLevelDPMechanism(
                    clip_norm=1.0, noise_multiplier=-0.5,
                    execution_mode=mode
                )

    def test_positive_sigma_accepted_in_approved_research_config(self):
        """sigma > 0 in approved research config is accepted."""
        cfg = get_approved_research_config()
        assert cfg.dp_noise_multiplier == 1.0
        assert cfg.dp_noise_multiplier > 0


# =====================================================================
# 3. Execution-Mode Security & Startup Validation Tests
# =====================================================================

class TestExecutionModeSecurity:
    """Verifies strict execution-mode boundaries and startup validation."""

    def test_unsupported_execution_mode_rejected(self):
        """Unknown execution modes raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported execution_mode"):
            validate_config({"execution_mode": "INVALID_MODE"})

    def test_research_simulation_rejects_deterministic_seed(self):
        """RESEARCH_SIMULATION mode strictly rejects passing deterministic seed to mechanism."""
        with pytest.raises(ValueError, match="Deterministic seed is strictly prohibited in RESEARCH_SIMULATION"):
            ClientLevelDPMechanism(
                clip_norm=1.0, noise_multiplier=1.0, seed=42,
                execution_mode=ExecutionMode.RESEARCH_SIMULATION
            )

    def test_research_simulation_rejects_seed_in_perturb_update(self):
        """RESEARCH_SIMULATION mode strictly rejects passing seed to perturb_update."""
        mech = ClientLevelDPMechanism(
            clip_norm=1.0, noise_multiplier=1.0,
            execution_mode=ExecutionMode.RESEARCH_SIMULATION
        )
        with pytest.raises(ValueError, match="Explicit seed is strictly prohibited in RESEARCH_SIMULATION"):
            mech.perturb_update(np.ones(10, dtype=np.float32), seed=999)

    def test_research_simulation_rejects_insecure_randomness_mode(self):
        """RESEARCH_SIMULATION rejects DETERMINISTIC_TEST randomness mode."""
        with pytest.raises(ValueError, match="Insecure randomness mode"):
            validate_config({
                "execution_mode": ExecutionMode.RESEARCH_SIMULATION,
                "privacy_randomness_mode": PrivacyRandomnessMode.DETERMINISTIC_TEST
            })

    def test_deployment_mode_rejects_deterministic_seed(self):
        """DEPLOYMENT mode strictly rejects passing deterministic seed."""
        with pytest.raises(ValueError, match="Deterministic seed is strictly prohibited in DEPLOYMENT"):
            ClientLevelDPMechanism(
                clip_norm=1.0, noise_multiplier=1.0, seed=42,
                execution_mode=ExecutionMode.DEPLOYMENT
            )

    def test_legacy_uncalibrated_sigma_rejected_in_research_simulation(self):
        """Legacy uncalibrated sigma=0.01 is rejected when dp_enabled is True in RESEARCH_SIMULATION."""
        with pytest.raises(ValueError, match="Legacy uncalibrated sigma=0.01 is strictly rejected"):
            validate_config({
                "execution_mode": ExecutionMode.RESEARCH_SIMULATION,
                "dp_enabled": True,
                "dp_noise_multiplier": 0.01
            })

    def test_approved_research_config_validates_successfully(self):
        """get_approved_research_config returns a valid configuration with baseline parameters."""
        cfg = get_approved_research_config()
        assert cfg.execution_mode == ExecutionMode.RESEARCH_SIMULATION
        assert cfg.privacy_randomness_mode == PrivacyRandomnessMode.OS_CSPRNG
        assert cfg.dp_clip_norm == APPROVED_CLIP_NORM
        assert cfg.dp_noise_multiplier == APPROVED_NOISE_MULTIPLIER
        assert cfg.dp_target_delta == APPROVED_TARGET_DELTA
        assert cfg.communication_rounds == APPROVED_COMMUNICATION_ROUNDS


# =====================================================================
# 4. Orchestrator Isolation & Client-Local Privacy Tests
# =====================================================================

class TestOrchestratorSeedIsolation:
    """Verifies orchestrator seed isolation and deployment client-local privacy."""

    @pytest.fixture
    def synthetic_data(self):
        rng = np.random.RandomState(42)
        N = 100
        D = 10
        C = 2
        X = rng.randn(N, D).astype(np.float32)
        y = rng.randint(0, C, size=N).astype(np.int64)
        return X, y

    def test_orchestrator_research_simulation_fresh_noise(self, synthetic_data):
        """In RESEARCH_SIMULATION, orchestrator does not use experiment seed to generate noise."""
        X, y = synthetic_data
        config = {
            "execution_mode": "RESEARCH_SIMULATION",
            "privacy_randomness_mode": "OS_CSPRNG",
            "num_clients": 3,
            "num_rounds": 1,
            "batch_size": 16,
            "dp_enabled": True,
            "dp_clip_norm": 1.0,
            "dp_noise_multiplier": 1.0,
            "dp_target_delta": 1e-5,
            "seed": 42,
            "dataset": "synthetic",
            "X_train": X[:70],
            "y_train": y[:70],
            "X_test": X[70:],
            "y_test": y[70:],
            "input_dim": 10,
            "num_classes": 2
        }

        # Run twice with the exact same experiment seed (42)
        orch1 = FederatedOrchestrator(config)
        res1 = orch1.run()

        orch2 = FederatedOrchestrator(config)
        res2 = orch2.run()

        # Non-private components (model init weights) are identical
        assert res1["initial_model_weights_hash"] == res2["initial_model_weights_hash"]

        # Private components (DP noise) are fresh and distinct!
        meta1_c0 = res1["dp_accounting"][0]["dp_meta"][0]
        meta2_c0 = res2["dp_accounting"][0]["dp_meta"][0]
        assert meta1_c0["execution_mode"] == "RESEARCH_SIMULATION"
        assert meta1_c0["privacy_randomness_mode"] == "OS_CSPRNG"
        assert meta1_c0["noise_l2_norm"] != meta2_c0["noise_l2_norm"]

    def test_orchestrator_deployment_mode_client_local_privacy(self, synthetic_data):
        """In DEPLOYMENT mode, central orchestrator has dp_mechanism=None and clients privatize locally."""
        X, y = synthetic_data
        config = {
            "execution_mode": "DEPLOYMENT",
            "privacy_randomness_mode": "OS_CSPRNG",
            "num_clients": 3,
            "num_rounds": 1,
            "batch_size": 16,
            "dp_enabled": True,
            "dp_clip_norm": 1.0,
            "dp_noise_multiplier": 1.0,
            "dp_target_delta": 1e-5,
            "seed": 42,
            "dataset": "synthetic",
            "X_train": X[:70],
            "y_train": y[:70],
            "X_test": X[70:],
            "y_test": y[70:],
            "input_dim": 10,
            "num_classes": 2
        }

        orch = FederatedOrchestrator(config)
        orch.setup()

        # Orchestrator does NOT hold central dp_mechanism
        assert orch.dp_mechanism is None

        # Each client holds its own local dp_mechanism configured for DEPLOYMENT
        for client in orch.clients:
            assert client.dp_mechanism is not None
            assert client.dp_mechanism.execution_mode == ExecutionMode.DEPLOYMENT
            assert client.dp_mechanism.privacy_randomness_mode == PrivacyRandomnessMode.OS_CSPRNG

        # Execute round
        res = orch.run()
        assert res["execution_mode"] == "DEPLOYMENT"
        assert res["chain_valid"] is True
        assert len(res["dp_accounting"]) == 1
        meta_c0 = res["dp_accounting"][0]["dp_meta"][0]
        assert meta_c0["execution_mode"] == "DEPLOYMENT"
        assert meta_c0["privacy_randomness_mode"] == "OS_CSPRNG"


# =====================================================================
# 5. Privacy Mathematical Invariants Preservation Tests
# =====================================================================

class TestPrivacyMathematicalInvariants:
    """Verifies that WP2.4 preserves clipping, sensitivity S=2C, and RDP bounds."""

    def test_clipping_and_sensitivity_invariants(self):
        """Clipping to C and sensitivity S=2C are preserved exactly."""
        C = 1.5
        mech = ClientLevelDPMechanism(
            clip_norm=C, noise_multiplier=1.0,
            execution_mode=ExecutionMode.RESEARCH_SIMULATION
        )
        assert mech.sensitivity == 2.0 * C
        assert mech.noise_std == 2.0 * 1.0 * C

        v = np.ones(200, dtype=np.float32) * 5.0
        clipped, meta = mech.clip_update(v)
        assert meta["clipped_norm"] <= C * (1.0 + 1e-5)
        assert np.isclose(meta["clipped_norm"], C, atol=1e-5)

    def test_rdp_accountant_preservation(self):
        """RDP accountant computes identical epsilon for approved research baseline."""
        accountant = RDPAccountant()
        # 5 rounds with sigma = 1.0
        accountant.step(noise_multiplier=1.0, rounds=5)
        eps, alpha = accountant.get_epsilon(delta=1e-5)

        # Baseline value: approx 13.2565
        assert np.isclose(eps, 13.2565, atol=1e-3)
        assert alpha in accountant.orders


class TestDataflowAndTrustBoundaries:
    """Verifies that unperturbed weights never cross the client boundary in RESEARCH_SIMULATION and DEPLOYMENT."""

    def test_client_local_privatization_in_research_simulation(self):
        """Client-local privatization produces perturbed weights before transmission to orchestrator."""
        client = FederatedClient(
            client_id=0,
            client_name="Test-Node-0",
            X_local=np.ones((10, 10), dtype=np.float32),
            y_local=np.zeros(10, dtype=np.int64),
            input_dim=10,
            num_classes=2,
            dp_mechanism=ClientLevelDPMechanism(
                clip_norm=1.0, noise_multiplier=1.0,
                execution_mode=ExecutionMode.RESEARCH_SIMULATION
            )
        )
        global_w = np.zeros(client.get_local_weights().size, dtype=np.float32)
        priv_w, meta = client.privatize_local_weights(global_w)

        # Raw local weights are distinct from privatized weights
        raw_w = client.get_local_weights()
        assert not np.array_equal(raw_w, priv_w)
        assert meta["is_private"] is True
        assert meta["execution_mode"] == "RESEARCH_SIMULATION"
        assert meta["privacy_randomness_mode"] == "OS_CSPRNG"
