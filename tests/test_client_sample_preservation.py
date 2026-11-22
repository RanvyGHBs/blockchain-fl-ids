"""
Unit and Regression Tests for Client Training Sample Preservation.
Verifies that:
1. Every client training sample participates in local model updates.
2. No samples are silently discarded due to singleton-batch remainder conditions.
3. Very small partitions (N=1, N=2) train safely without BatchNorm runtime errors.
4. Dynamic batch partitioning eliminates singleton batches when N > 1.
5. Losses and model weights remain finite and updated.
"""

import pytest
import numpy as np
import torch

from src.models.ids_net import IDSNet
from src.federated.client import FederatedClient


class TestClientSamplePreservation:
    """Verifies that no client training samples are lost during local SGD."""

    @pytest.fixture
    def client_factory(self):
        """Factory for creating clients with deterministic synthetic tabular data."""
        def _create(num_samples: int, input_dim: int = 10, num_classes: int = 2, seed: int = 42):
            np.random.seed(seed)
            X = np.random.randn(num_samples, input_dim).astype(np.float32)
            y = np.random.randint(0, num_classes, size=(num_samples,), dtype=np.int64)
            return FederatedClient(
                client_id=1,
                client_name="TestNode",
                X_local=X,
                y_local=y,
                input_dim=input_dim,
                num_classes=num_classes,
                device="cpu",
                seed=seed
            )
        return _create

    def test_01_single_sample_client_trains_successfully(self, client_factory):
        """
        Verify that a client with exactly N=1 sample executes valid training:
        - No BatchNorm division-by-zero ValueError.
        - Exactly 1 sample participates in training per epoch.
        - Loss is finite and model parameters update.
        """
        client = client_factory(num_samples=1)
        w_before = client.get_local_weights().copy()

        metrics = client.local_train(epochs=1, batch_size=32, lr=0.01)

        w_after = client.get_local_weights()

        assert metrics["num_samples"] == 1
        assert metrics["samples_processed_per_epoch"] == 1
        assert metrics["total_samples_trained"] == 1
        assert np.isfinite(metrics["train_loss"])
        assert metrics["train_loss"] > 0.0
        assert np.all(np.isfinite(w_after))
        # Parameter update proof
        assert not np.allclose(w_before, w_after)

    def test_02_two_sample_client_trains_successfully(self, client_factory):
        """Verify N=2 client trains safely with full 2-sample batch."""
        client = client_factory(num_samples=2)
        w_before = client.get_local_weights().copy()

        metrics = client.local_train(epochs=2, batch_size=32, lr=0.01)

        w_after = client.get_local_weights()

        assert metrics["num_samples"] == 2
        assert metrics["samples_processed_per_epoch"] == 2
        assert metrics["total_samples_trained"] == 4  # 2 epochs * 2 samples
        assert np.isfinite(metrics["train_loss"])
        assert np.all(np.isfinite(w_after))
        assert not np.allclose(w_before, w_after)

    def test_03_sample_count_33_batch_size_32_singleton_remainder_split(self, client_factory):
        """
        Verify N=33 with batch_size=32 (would produce 32 + 1 singleton remainder):
        - Partitioning splits the remaining 33 samples into balanced batches (17 and 16).
        - Zero batches of size 1 are formed.
        - All 33 samples are processed.
        """
        # Test batch index generation
        batches = FederatedClient._build_batch_indices(num_samples=33, batch_size=32, shuffle=False)
        assert len(batches) == 2
        assert {len(batches[0]), len(batches[1])} == {16, 17}
        # Verify complete disjoint set coverage
        flattened = [idx for b in batches for idx in b]
        assert len(flattened) == 33
        assert sorted(flattened) == list(range(33))

        # Test actual client training
        client = client_factory(num_samples=33)
        metrics = client.local_train(epochs=1, batch_size=32, lr=0.005)

        assert metrics["num_samples"] == 33
        assert metrics["samples_processed_per_epoch"] == 33
        assert metrics["total_samples_trained"] == 33
        assert np.isfinite(metrics["train_loss"])
        assert np.all(np.isfinite(client.get_local_weights()))

    def test_04_sample_count_exactly_divisible_by_batch_size(self, client_factory):
        """Verify N=64 with batch_size=32 produces two clean batches of 32."""
        batches = FederatedClient._build_batch_indices(num_samples=64, batch_size=32, shuffle=False)
        assert len(batches) == 2
        assert len(batches[0]) == 32
        assert len(batches[1]) == 32

        client = client_factory(num_samples=64)
        metrics = client.local_train(epochs=2, batch_size=32, lr=0.005)

        assert metrics["samples_processed_per_epoch"] == 64
        assert metrics["total_samples_trained"] == 128
        assert np.isfinite(metrics["train_loss"])

    def test_05_arbitrary_singleton_remainders_zero_dropped_samples(self, client_factory):
        """
        Exhaustively test cases where N % batch_size == 1:
        (65, 32), (97, 32), (17, 16), (5, 4), (3, 2).
        Asserts:
        - Every batch has size >= 2.
        - Zero samples dropped.
        - Training succeeds with finite loss.
        """
        cases = [
            (65, 32),
            (97, 32),
            (17, 16),
            (5, 4),
            (3, 2)
        ]

        for num_samples, bs in cases:
            batches = FederatedClient._build_batch_indices(num_samples=num_samples, batch_size=bs, shuffle=False)
            flattened = [idx for b in batches for idx in b]
            assert len(flattened) == num_samples, f"Sample count mismatch for N={num_samples}, B={bs}"
            assert set(flattened) == set(range(num_samples)), f"Set mismatch for N={num_samples}, B={bs}"

            for b in batches:
                assert len(b) >= 2, f"Found singleton batch of size {len(b)} in N={num_samples}, B={bs}"

            client = client_factory(num_samples=num_samples)
            metrics = client.local_train(epochs=1, batch_size=bs)
            assert metrics["samples_processed_per_epoch"] == num_samples
            assert metrics["total_samples_trained"] == num_samples
            assert np.isfinite(metrics["train_loss"])

    def test_06_actual_training_batch_participation_verification(self, client_factory):
        """
        Verify that trailing samples actively participate in training by proving that
        modifying the trailing sample's label alters the resulting model weights.
        """
        # Create client with 33 samples
        client_a = client_factory(num_samples=33, seed=100)
        client_b = client_factory(num_samples=33, seed=100)

        # Invert the 33rd sample's label in client_b
        client_b.y_local[-1] = 1 - client_b.y_local[-1]

        # Train both clients with identical initialization and batch_size=32
        init_weights = client_a.get_local_weights().copy()
        client_b.set_global_weights(init_weights)

        torch.manual_seed(42)
        np.random.seed(42)
        client_a.local_train(epochs=1, batch_size=32, lr=0.01)

        torch.manual_seed(42)
        np.random.seed(42)
        client_b.local_train(epochs=1, batch_size=32, lr=0.01)

        # If the 33rd sample was skipped, client_a and client_b would have identical weights.
        # Since it participates, the final weights MUST diverge.
        assert not np.allclose(client_a.get_local_weights(), client_b.get_local_weights()), \
            "Trailing sample was not processed: model weights are identical despite label modification!"

    def test_07_fedprox_proximal_regularization_with_small_partitions(self, client_factory):
        """Verify FedProx proximal term calculates properly on small partition sizes (N=1, N=33)."""
        for n in [1, 2, 33]:
            client = client_factory(num_samples=n)
            init_weights = client.get_local_weights().copy()
            metrics = client.local_train(
                epochs=1,
                batch_size=32,
                lr=0.005,
                fedprox_mu=0.1,
                global_weights=init_weights
            )
            assert metrics["samples_processed_per_epoch"] == n
            assert np.isfinite(metrics["train_loss"])
            assert np.all(np.isfinite(client.get_local_weights()))
