"""
Unit tests for Stage 1 components:
- NSLKDDLoader
- FederatedPartitioner
- IDSNet model forward pass, vector serialization, and hashing.
"""

import unittest
import numpy as np
import pytest
import torch
from src.data.nsl_kdd import NSLKDDLoader
from src.data.partitioner import FederatedPartitioner
from src.models.ids_net import IDSNet


@pytest.mark.integration
class TestStage1(unittest.TestCase):

    def setUp(self):
        self.loader = NSLKDDLoader(raw_dir="data/raw", processed_dir="data/processed", binary=True, seed=42)

    def test_01_data_loading_and_shape(self):
        X_train, y_train, X_test, y_test = self.loader.preprocess(force=False)
        self.assertGreater(len(X_train), 0)
        self.assertGreater(len(X_test), 0)
        self.assertEqual(len(X_train), len(y_train))
        self.assertEqual(len(X_test), len(y_test))
        self.assertEqual(X_train.shape[1], X_test.shape[1])
        # Check normalization bounds
        self.assertGreaterEqual(float(np.min(X_train)), 0.0)
        self.assertLessEqual(float(np.max(X_train)), 1.0)

    def test_02_partitioner_non_iid(self):
        X_train, y_train, _, _ = self.loader.preprocess(force=False)
        partitioner = FederatedPartitioner(num_clients=3, non_iid=True, alpha=0.5, seed=42)
        splits = partitioner.partition(X_train, y_train)
        self.assertEqual(len(splits), 3)
        total_samples = sum(len(y) for _, y in splits.values())
        self.assertEqual(total_samples, len(y_train))

    def test_03_model_serialization_and_hashing(self):
        input_dim = self.loader.get_feature_dimension()
        model = IDSNet(input_dim=input_dim, num_classes=2)
        
        # Test forward pass
        dummy_input = torch.randn(8, input_dim)
        output = model(dummy_input)
        self.assertEqual(output.shape, (8, 2))

        # Test weight serialization
        flat_weights = model.get_weights_vector()
        self.assertIsInstance(flat_weights, np.ndarray)
        self.assertEqual(flat_weights.ndim, 1)

        # Test weight restoration
        original_hash = model.get_weights_hash()
        perturbed_weights = flat_weights + 0.01
        model.set_weights_vector(perturbed_weights)
        new_hash = model.get_weights_hash()
        self.assertNotEqual(original_hash, new_hash)

        # Restore back
        model.set_weights_vector(flat_weights)
        restored_hash = model.get_weights_hash()
        self.assertEqual(original_hash, restored_hash)


if __name__ == "__main__":
    unittest.main()
