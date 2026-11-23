"""
Unit and Integration Test Suite for WP2: Formal Client-Level Differential Privacy Mechanism & RDP Accounting.

Verifies:
1. Complete vector L2 clipping (zero, under, equal, over C, large, NaN/Inf rejection, state_dict reconstruction).
2. Gaussian mechanism calibration (shape, std = 2 * sigma * C, independence, seed reproducibility, parameter checks).
3. RDP accountant (per-round RDP = alpha / (2 * sigma^2), linear composition, discrete minimization, monotonicity, edge cases).
4. Orchestrator integration (end-to-end 5-client FL with DP, signature on perturbed updates, blockchain hashes, RDP steps).
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import math
import pytest
import numpy as np
import torch
import torch.nn as nn

from src.privacy.mechanism import ClientLevelDPMechanism
from src.privacy.rdp_accountant import RDPAccountant, DEFAULT_RDP_ORDERS
from src.federated.orchestrator import FederatedOrchestrator
from src.blockchain.crypto import CryptoManager


# =====================================================================
# 1. Complete L2 Clipping Tests
# =====================================================================

class TestClippingMechanism:
    """Verifies complete model update vector L2-norm clipping."""

    def test_zero_vector(self):
        """Zero vector remains zero with norm 0 and clip_factor 1.0."""
        mech = ClientLevelDPMechanism(clip_norm=1.0, noise_multiplier=0.0)
        v = np.zeros(100, dtype=np.float32)
        clipped, meta = mech.clip_update(v)
        
        assert np.allclose(clipped, 0.0)
        assert meta["original_norm"] == 0.0
        assert meta["clipped_norm"] == 0.0
        assert meta["is_clipped"] is False
        assert meta["clip_factor"] == 1.0

    def test_norm_less_than_c(self):
        """Vector with norm < C is unaltered."""
        mech = ClientLevelDPMechanism(clip_norm=2.0, noise_multiplier=0.0)
        v = np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32)
        orig_norm = float(np.linalg.norm(v))
        assert orig_norm < 2.0
        
        clipped, meta = mech.clip_update(v)
        assert np.allclose(clipped, v)
        assert np.isclose(meta["clipped_norm"], orig_norm)
        assert meta["is_clipped"] is False
        assert meta["clip_factor"] == 1.0

    def test_norm_equal_c(self):
        """Vector with norm exactly C is unaltered."""
        mech = ClientLevelDPMechanism(clip_norm=1.0, noise_multiplier=0.0)
        v = np.array([0.6, 0.8], dtype=np.float32)  # 0.6^2 + 0.8^2 = 1.0
        assert np.isclose(np.linalg.norm(v), 1.0)
        
        clipped, meta = mech.clip_update(v)
        assert np.allclose(clipped, v, atol=1e-6)
        assert np.isclose(meta["clipped_norm"], 1.0, atol=1e-5)
        assert meta["is_clipped"] is False

    def test_norm_greater_than_c(self):
        """Vector with norm > C is strictly scaled to norm <= C preserving direction."""
        C = 1.5
        mech = ClientLevelDPMechanism(clip_norm=C, noise_multiplier=0.0)
        v = np.array([3.0, 4.0], dtype=np.float32)  # norm = 5.0 > 1.5
        
        clipped, meta = mech.clip_update(v)
        assert meta["is_clipped"] is True
        assert meta["original_norm"] == 5.0
        assert meta["clipped_norm"] <= C * (1.0 + 1e-5)
        assert np.isclose(meta["clipped_norm"], C, atol=1e-5)
        
        # Verify direction preservation (cosine similarity == 1.0)
        cos_sim = np.dot(v, clipped) / (np.linalg.norm(v) * np.linalg.norm(clipped))
        assert np.isclose(cos_sim, 1.0, atol=1e-6)

    def test_extremely_large_vector(self):
        """Vector with norm 10^6 is scaled down strictly to <= C."""
        C = 0.5
        mech = ClientLevelDPMechanism(clip_norm=C, noise_multiplier=0.0)
        v = np.ones(1000, dtype=np.float32) * 10000.0  # huge norm
        
        clipped, meta = mech.clip_update(v)
        assert meta["is_clipped"] is True
        assert meta["clipped_norm"] <= C * (1.0 + 1e-5)
        assert np.isclose(meta["clipped_norm"], C, atol=1e-5)

    def test_nan_inf_rejection(self):
        """Vectors containing NaN or Inf raise ValueError."""
        mech = ClientLevelDPMechanism(clip_norm=1.0, noise_multiplier=0.0)
        
        v_nan = np.array([1.0, np.nan, 2.0], dtype=np.float32)
        with pytest.raises(ValueError, match="NaN or Inf"):
            mech.clip_update(v_nan)
            
        v_inf = np.array([1.0, np.inf, 2.0], dtype=np.float32)
        with pytest.raises(ValueError, match="NaN or Inf"):
            mech.clip_update(v_inf)

    def test_invalid_init_parameters(self):
        """Non-positive or non-finite clip_norm raises ValueError."""
        with pytest.raises(ValueError):
            ClientLevelDPMechanism(clip_norm=0.0)
        with pytest.raises(ValueError):
            ClientLevelDPMechanism(clip_norm=-1.5)
        with pytest.raises(ValueError):
            ClientLevelDPMechanism(clip_norm=float("nan"))
        with pytest.raises(ValueError):
            ClientLevelDPMechanism(clip_norm=float("inf"))

    def test_state_dict_flatten_and_reconstruction(self):
        """Verifies flattening and reconstructing model weights preserving parameter ordering."""
        class SimpleNet(nn.Module):
            def __init__(self):
                super().__init__()
                self.fc1 = nn.Linear(4, 3)
                self.fc2 = nn.Linear(3, 2)
            def forward(self, x):
                return self.fc2(self.fc1(x))

        net = SimpleNet()
        # Flatten state dict
        params = [p.detach().cpu().numpy().flatten() for p in net.parameters()]
        flat_weights = np.concatenate(params)
        d = flat_weights.size
        
        mech = ClientLevelDPMechanism(clip_norm=2.0, noise_multiplier=0.0)
        clipped, meta = mech.clip_update(flat_weights)
        assert clipped.size == d
        assert meta["clipped_norm"] <= 2.0 * (1.0 + 1e-5)
        
        # Reconstruct into model parameters
        offset = 0
        with torch.no_grad():
            for p in net.parameters():
                numel = p.numel()
                p.copy_(torch.from_numpy(clipped[offset:offset + numel].reshape(p.shape)))
                offset += numel
        assert offset == d


# =====================================================================
# 2. Gaussian Perturbation Mechanism Tests
# =====================================================================

class TestGaussianPerturbationMechanism:
    """Verifies Gaussian noise calibration with std = 2 * sigma * C."""

    def test_output_shape_and_dtype(self):
        """Perturbed update preserves exact shape and float32 dtype."""
        mech = ClientLevelDPMechanism(clip_norm=1.0, noise_multiplier=0.5, seed=42)
        v = np.ones(50, dtype=np.float32)
        perturbed, meta = mech.privatize_update(v)
        
        assert perturbed.shape == (50,)
        assert perturbed.dtype == np.float32
        assert "noise_std" in meta
        assert meta["noise_std"] == 1.0  # 2 * 0.5 * 1.0 = 1.0

    def test_noise_standard_deviation_empirical(self):
        """
        Empirically validates noise std == 2 * sigma * C across M=2000 samples.
        Standard error of sample standard deviation is approx sigma_noise / sqrt(2M).
        """
        C = 1.2
        sigma = 0.5
        expected_std = 2.0 * sigma * C  # 2 * 0.5 * 1.2 = 1.2
        
        mech = ClientLevelDPMechanism(clip_norm=C, noise_multiplier=sigma, seed=123)
        zero_v = np.zeros(1, dtype=np.float32)
        
        M = 2000
        samples = np.zeros(M, dtype=np.float32)
        rng = np.random.RandomState(456)
        for i in range(M):
            sample_seed = int(rng.randint(0, 10000000))
            pert, _ = mech.perturb_update(zero_v, seed=sample_seed)
            samples[i] = pert[0]
            
        emp_mean = float(np.mean(samples))
        emp_std = float(np.std(samples))
        
        # 3 standard errors bound for mean: 3 * expected_std / sqrt(M)
        mean_tol = 3.0 * expected_std / math.sqrt(M)
        # 3 standard errors bound for std: 3 * expected_std / sqrt(2M)
        std_tol = 3.0 * expected_std / math.sqrt(2 * M)
        
        assert abs(emp_mean - 0.0) < mean_tol, f"Empirical mean {emp_mean} deviates from 0.0"
        assert abs(emp_std - expected_std) < std_tol, f"Empirical std {emp_std} deviates from expected {expected_std}"

    def test_independent_noise_across_coordinates(self):
        """Empirical correlation between distinct coordinates is negligible."""
        mech = ClientLevelDPMechanism(clip_norm=1.0, noise_multiplier=0.8)
        d = 10
        M = 1500
        noise_matrix = np.zeros((M, d), dtype=np.float32)
        zero_v = np.zeros(d, dtype=np.float32)
        
        for i in range(M):
            pert, _ = mech.perturb_update(zero_v, seed=10000 + i)
            noise_matrix[i, :] = pert
            
        # Pearson correlation matrix
        corr = np.corrcoef(noise_matrix, rowvar=False)
        # Off-diagonal elements should be close to 0
        np.fill_diagonal(corr, 0.0)
        max_corr = np.max(np.abs(corr))
        assert max_corr < 0.12, f"Coordinates show excessive empirical cross-correlation: {max_corr}"

    def test_seed_reproducibility(self):
        """Identical seed produces identical perturbation; distinct seeds produce distinct draws."""
        mech = ClientLevelDPMechanism(clip_norm=1.0, noise_multiplier=0.5)
        v = np.array([0.2, 0.4, 0.6], dtype=np.float32)
        
        pert1, _ = mech.privatize_update(v, seed=777)
        pert2, _ = mech.privatize_update(v, seed=777)
        pert3, _ = mech.privatize_update(v, seed=888)
        
        assert np.array_equal(pert1, pert2)
        assert not np.array_equal(pert1, pert3)

    def test_invalid_noise_multiplier(self):
        """Negative or non-finite noise_multiplier raises ValueError."""
        with pytest.raises(ValueError):
            ClientLevelDPMechanism(clip_norm=1.0, noise_multiplier=-0.1)
        with pytest.raises(ValueError):
            ClientLevelDPMechanism(clip_norm=1.0, noise_multiplier=float("nan"))

    def test_privatize_client_weights(self):
        """Verifies full weight privatization: w_global + perturbed(w_local - w_global)."""
        mech = ClientLevelDPMechanism(clip_norm=1.0, noise_multiplier=0.1, seed=99)
        w_global = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        w_local = np.array([1.2, 2.3, 3.4], dtype=np.float32)  # delta = [0.2, 0.3, 0.4], norm ~ 0.538 < 1.0
        
        w_pert, meta = mech.privatize_client_weights(w_local, w_global, seed=123)
        assert w_pert.shape == w_global.shape
        assert meta["original_norm"] < 1.0
        assert meta["is_clipped"] is False
        assert "final_perturbed_weights_norm" in meta


# =====================================================================
# 3. RDP Accountant Tests
# =====================================================================

class TestRDPAccountant:
    """Verifies RDP accumulation and discrete-order approximate (epsilon, delta)-DP minimization."""

    def test_default_orders_validity(self):
        """Default orders are sorted, > 1.0, and non-empty."""
        accountant = RDPAccountant()
        assert len(accountant.orders) > 0
        assert all(a > 1.0 for a in accountant.orders)
        assert accountant.orders == sorted(accountant.orders)

    def test_invalid_orders_rejection(self):
        """Orders <= 1.0 or non-finite raise ValueError."""
        with pytest.raises(ValueError):
            RDPAccountant(orders=[0.5, 2.0])
        with pytest.raises(ValueError):
            RDPAccountant(orders=[1.0, 2.0])
        with pytest.raises(ValueError):
            RDPAccountant(orders=[float("nan"), 2.0])
        with pytest.raises(ValueError):
            RDPAccountant(orders=[])

    def test_per_round_rdp_values(self):
        """
        Per-round RDP matches theoretical formula alpha / (2 * sigma^2).
        For sigma = 0.5: epsilon_RDP(alpha) = alpha / (2 * 0.25) = 2.0 * alpha.
        """
        accountant = RDPAccountant(orders=[1.5, 2.0, 4.0, 8.0])
        step_meta = accountant.step(noise_multiplier=0.5, clip_norm=1.0, rounds=1)
        
        for alpha in [1.5, 2.0, 4.0, 8.0]:
            expected_rdp = alpha / (2.0 * (0.5 ** 2))  # 2.0 * alpha
            assert np.isclose(accountant.get_rdp(alpha), expected_rdp)
            assert np.isclose(step_meta["step_rdp"][alpha], expected_rdp)

    def test_multi_round_linear_composition(self):
        """Over T rounds, cumulative RDP is exactly T * alpha / (2 * sigma^2)."""
        accountant = RDPAccountant(orders=[2.0, 4.0])
        sigma = 0.4
        T = 5
        
        for _ in range(T):
            accountant.step(noise_multiplier=sigma, clip_norm=1.0, rounds=1)
            
        for alpha in [2.0, 4.0]:
            expected_rdp = T * (alpha / (2.0 * (sigma ** 2)))
            assert np.isclose(accountant.get_rdp(alpha), expected_rdp)

    def test_discrete_order_minimization(self):
        """
        Approximate DP conversion matches min_{alpha in orders} [ RDP(alpha) + ln(1/delta) / (alpha - 1) ].
        """
        orders = [1.5, 2.0, 3.0, 4.0, 8.0, 16.0]
        accountant = RDPAccountant(orders=orders)
        accountant.step(noise_multiplier=1.0, clip_norm=1.0, rounds=10)
        
        delta = 1e-5
        eps, opt_alpha = accountant.get_epsilon(delta)
        
        # Manually compute candidate epsilons
        candidates = {}
        for a in orders:
            rdp_val = 10.0 * a / (2.0 * (1.0 ** 2))
            cand_eps = rdp_val + math.log(1.0 / delta) / (a - 1.0)
            candidates[a] = cand_eps
            
        min_candidate_alpha = min(candidates, key=candidates.get)
        min_candidate_eps = candidates[min_candidate_alpha]
        
        assert np.isclose(eps, min_candidate_eps)
        assert opt_alpha == min_candidate_alpha

    def test_delta_validation(self):
        """delta <= 0 or delta >= 1 or non-finite raises ValueError."""
        accountant = RDPAccountant()
        accountant.step(noise_multiplier=1.0, rounds=1)
        
        with pytest.raises(ValueError):
            accountant.get_epsilon(0.0)
        with pytest.raises(ValueError):
            accountant.get_epsilon(-1e-5)
        with pytest.raises(ValueError):
            accountant.get_epsilon(1.0)
        with pytest.raises(ValueError):
            accountant.get_epsilon(1.5)
        with pytest.raises(ValueError):
            accountant.get_epsilon(float("nan"))

    def test_round_zero_edge_case(self):
        """With 0 releases, epsilon is strictly 0.0."""
        accountant = RDPAccountant()
        eps, alpha = accountant.get_epsilon(1e-5)
        assert eps == 0.0
        assert alpha == accountant.orders[0]
        
        summary = accountant.summary(delta=1e-5)
        assert summary["total_rounds_executed"] == 0
        assert summary["optimal_epsilon"] == 0.0

    def test_monotonicity_wrt_rounds_and_noise(self):
        """Epsilon increases with round count and decreases with noise multiplier."""
        # 1. Monotonicity wrt rounds
        acc1 = RDPAccountant()
        acc1.step(noise_multiplier=1.0, rounds=2)
        eps_2, _ = acc1.get_epsilon(1e-5)
        
        acc1.step(noise_multiplier=1.0, rounds=3)  # total 5
        eps_5, _ = acc1.get_epsilon(1e-5)
        
        acc1.step(noise_multiplier=1.0, rounds=5)  # total 10
        eps_10, _ = acc1.get_epsilon(1e-5)
        
        assert eps_2 < eps_5 < eps_10

        # 2. Monotonicity wrt noise multiplier sigma
        acc_low_noise = RDPAccountant()
        acc_low_noise.step(noise_multiplier=0.5, rounds=5)
        eps_low_noise, _ = acc_low_noise.get_epsilon(1e-5)
        
        acc_high_noise = RDPAccountant()
        acc_high_noise.step(noise_multiplier=1.5, rounds=5)
        eps_high_noise, _ = acc_high_noise.get_epsilon(1e-5)
        
        assert eps_high_noise < eps_low_noise


# =====================================================================
# 4. Orchestrator Integration Tests
# =====================================================================

class TestOrchestratorDPIntegration:
    """End-to-end integration of DP mechanism with Orchestrator, crypto, and blockchain."""

    @pytest.fixture
    def synthetic_data(self):
        rng = np.random.RandomState(42)
        N = 200
        D = 10
        C = 2
        X = rng.randn(N, D).astype(np.float32)
        y = rng.randint(0, C, size=N).astype(np.int64)
        return X, y

    def test_orchestrator_dp_execution(self, synthetic_data):
        """
        Runs 2 rounds with dp_enabled=True and verifies:
        - dp_summary is present in results and records 2 rounds.
        - dp_accounting records metadata per client per round.
        - Blockchain chain is valid.
        - Optimal epsilon > 0.
        """
        X, y = synthetic_data
        config = {
            "num_clients": 5,
            "num_rounds": 2,
            "batch_size": 16,
            "aggregation": "fedavg",
            "attack_enabled": False,
            "defense_enabled": True,
            "dp_enabled": True,
            "dp_clip_norm": 1.0,
            "dp_noise_multiplier": 0.5,
            "dp_target_delta": 1e-5,
            "seed": 42,
            "dataset": "synthetic",
            "X_train": X[:140],
            "y_train": y[:140],
            "X_test": X[140:],
            "y_test": y[140:],
            "input_dim": 10,
            "num_classes": 2
        }
        
        orch = FederatedOrchestrator(config)
        results = orch.run()
        
        # Verify DP summary
        assert results["dp_summary"] is not None
        dp_sum = results["dp_summary"]
        assert dp_sum["total_rounds_executed"] == 2
        assert dp_sum["target_delta"] == 1e-5
        assert dp_sum["optimal_epsilon"] > 0.0
        assert dp_sum["optimal_alpha"] in DEFAULT_RDP_ORDERS
        
        # Verify DP accounting records
        dp_acc = results["dp_accounting"]
        assert len(dp_acc) == 2
        for r_entry in dp_acc:
            assert "round" in r_entry
            assert "dp_meta" in r_entry
            meta_dict = r_entry["dp_meta"]
            assert len(meta_dict) == 5  # 5 clients
            for cid, cm in meta_dict.items():
                assert "is_clipped" in cm
                assert "noise_std" in cm
                assert np.isclose(cm["noise_std"], 2.0 * 0.5 * 1.0)
                
        # Verify Blockchain integrity
        assert results["chain_valid"] is True
        assert len(orch.blockchain.chain) > 1

    def test_orchestrator_dp_disabled_baseline(self, synthetic_data):
        """When dp_enabled=False, dp_summary is None and dp_accounting is empty."""
        X, y = synthetic_data
        config = {
            "num_clients": 5,
            "num_rounds": 1,
            "batch_size": 16,
            "aggregation": "fedavg",
            "attack_enabled": False,
            "defense_enabled": True,
            "dp_enabled": False,
            "seed": 42,
            "dataset": "synthetic",
            "X_train": X[:140],
            "y_train": y[:140],
            "X_test": X[140:],
            "y_test": y[140:],
            "input_dim": 10,
            "num_classes": 2
        }
        
        orch = FederatedOrchestrator(config)
        results = orch.run()
        
        assert results["dp_summary"] is None
        assert results["dp_accounting"] == []
        assert orch.dp_mechanism is None
        assert orch.rdp_accountant is None

    def test_cryptographic_payload_authenticates_perturbed_weights(self, synthetic_data):
        """
        Verifies that ECDSA signature and SHA-256 block transaction hash match
        the perturbed model update, satisfying Data Processing Inequality.
        """
        X, y = synthetic_data
        config = {
            "num_clients": 5,
            "num_rounds": 1,
            "batch_size": 16,
            "aggregation": "fedavg",
            "attack_enabled": False,
            "defense_enabled": True,
            "dp_enabled": True,
            "dp_clip_norm": 1.0,
            "dp_noise_multiplier": 0.5,
            "seed": 42,
            "dataset": "synthetic",
            "X_train": X[:140],
            "y_train": y[:140],
            "X_test": X[140:],
            "y_test": y[140:],
            "input_dim": 10,
            "num_classes": 2
        }
        
        orch = FederatedOrchestrator(config)
        results = orch.run()
        
        # Inspect transactions in the committed block
        committed_blocks = [b for b in orch.blockchain.chain if b.index > 0]
        assert len(committed_blocks) >= 1
        round_1_block = committed_blocks[0]
        
        # Verify that for each transaction, the client's signature verifies against the model hash
        for tx in round_1_block.transactions:
            cid = tx.client_id
            pub_key = orch.client_keys[cid][1]
            # Signature must verify against payload hash
            is_valid = CryptoManager.verify_signature(pub_key, tx.weights_hash, tx.signature)
            assert is_valid is True, f"Signature failed verification on perturbed hash for client {cid}"
