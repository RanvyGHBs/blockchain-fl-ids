"""
Unit and Integration Tests for Custom Dataset Ingestion Engine (Track B).
Verifies preset loading, CSV/DataFrame ingestion, missing value imputation,
categorical encoding, strict 3-way isolation, and federated simulation adaptability.
"""

import os
import io
import tempfile
import pytest
import numpy as np
import pandas as pd
import torch

from src.data.custom_loader import CustomDatasetLoader
from src.data.partitioner import FederatedPartitioner
from src.models.ids_net import IDSNet
from src.federated.client import FederatedClient
from src.federated.server import FederatedServer
from src.trust.evaluator import MultiCriteriaTrustEngine
from src.attacks.model_poisoning import apply_sign_flipping_attack


class TestCustomDatasetLoader:
    """Tests the Track B custom dataset loader and 3-way isolation."""

    def test_01_preset_breast_cancer_loading_and_shapes(self):
        """Verify Breast Cancer Wisconsin preset (binary classification, 30 features)."""
        loader = CustomDatasetLoader(source="breast_cancer", seed=42)
        X_pool, y_pool, X_val, y_val, X_test, y_test = loader.preprocess_isolated()

        assert len(X_pool) + len(X_val) + len(X_test) == 569
        assert X_pool.shape[1] == 30
        assert X_val.shape[1] == 30
        assert X_test.shape[1] == 30
        assert loader.get_num_classes() == 2
        assert loader.get_feature_dimension() == 30
        assert set(np.unique(y_pool)).issubset({0, 1})

    def test_02_preset_iris_multiclass_loading(self):
        """Verify Iris preset (multi-class 3 classes, 4 features)."""
        loader = CustomDatasetLoader(source="iris", seed=42)
        X_pool, y_pool, X_val, y_val, X_test, y_test = loader.preprocess_isolated()

        assert len(X_pool) + len(X_val) + len(X_test) == 150
        assert X_pool.shape[1] == 4
        assert loader.get_num_classes() == 3
        assert set(np.unique(y_pool)) == {0, 1, 2}

    def test_03_preset_wine_multiclass_loading(self):
        """Verify Wine preset (multi-class 3 classes, 13 features)."""
        loader = CustomDatasetLoader(source="wine", seed=42)
        X_pool, y_pool, X_val, y_val, X_test, y_test = loader.preprocess_isolated()

        assert len(X_pool) + len(X_val) + len(X_test) == 178
        assert X_pool.shape[1] == 13
        assert loader.get_num_classes() == 3
        assert set(np.unique(y_pool)) == {0, 1, 2}

    def test_04_strict_three_way_isolation_guarantees(self):
        """
        Verify that:
        1. Scaler is fitted EXCLUSIVELY on client-training pool records.
        2. Scaler n_samples_seen_ equals len(X_pool), NOT (X_pool + X_val) or total.
        3. Arrays share no memory addresses.
        4. No test or validation samples were included in scaler min/max fitting.
        """
        loader = CustomDatasetLoader(source="breast_cancer", seed=42)
        X_pool, y_pool, X_val, y_val, X_test, y_test = loader.preprocess_isolated()

        assert loader.scaler is not None
        assert loader.scaler.n_samples_seen_ == len(X_pool)
        assert loader.scaler.n_samples_seen_ < len(X_pool) + len(X_val)
        assert loader.scaler.n_samples_seen_ < 569

        # Memory independence
        assert not np.shares_memory(X_pool, X_val)
        assert not np.shares_memory(X_pool, X_test)
        assert not np.shares_memory(X_val, X_test)

    def test_05_custom_csv_dataframe_loading_with_missing_and_categorical(self):
        """Verify handling of custom DataFrame with missing values and categorical features."""
        df = pd.DataFrame({
            "age": [25, 30, np.nan, 45, 50, 22, 38, 41, 29, 60] * 5,
            "salary": [50000, 60000, 75000, np.nan, 90000, 48000, 72000, 81000, 58000, 110000] * 5,
            "dept": ["IT", "HR", "IT", "Sales", np.nan, "IT", "Sales", "HR", "IT", "Sales"] * 5,
            "churn": ["No", "No", "Yes", "Yes", "No", "No", "Yes", "No", "No", "Yes"] * 5
        })

        loader = CustomDatasetLoader(source=df, target_column="churn", seed=42)
        X_pool, y_pool, X_val, y_val, X_test, y_test = loader.preprocess_isolated()

        # All values should be imputed and finite
        assert np.all(np.isfinite(X_pool))
        assert np.all(np.isfinite(X_val))
        assert np.all(np.isfinite(X_test))

        # Check categorical columns were encoded
        assert "dept" in loader.categorical_columns
        assert loader.get_feature_dimension() >= 4
        assert loader.get_num_classes() == 2

    def test_06_model_instantiation_and_forward_pass_on_custom_datasets(self):
        """Verify IDSNet adapts dynamically to arbitrary custom dataset input_dim and num_classes."""
        for preset in ["breast_cancer", "iris", "wine"]:
            loader = CustomDatasetLoader(source=preset, seed=42)
            X_pool, y_pool, _, _, _, _ = loader.preprocess_isolated()

            input_dim = loader.get_feature_dimension()
            num_classes = loader.get_num_classes()

            model = IDSNet(input_dim=input_dim, num_classes=num_classes)
            batch = torch.from_numpy(X_pool[:8])
            logits = model(batch)

            assert logits.shape == (8, num_classes)
            # Verify weight hashing works for custom shapes
            h = model.get_weights_hash()
            assert isinstance(h, str) and len(h) == 64

    def test_07_full_federated_round_simulation_on_custom_dataset(self):
        """Verify that a full federated training round with trust defense succeeds on a custom dataset."""
        loader = CustomDatasetLoader(source="breast_cancer", seed=42)
        X_pool, y_pool, X_val, y_val, X_test, y_test = loader.preprocess_isolated()

        input_dim = loader.get_feature_dimension()
        num_classes = loader.get_num_classes()

        partitioner = FederatedPartitioner(num_clients=3, non_iid=True, alpha=0.5, seed=42)
        splits = partitioner.partition(X_pool, y_pool)

        server = FederatedServer(input_dim=input_dim, num_classes=num_classes, device="cpu")
        w_global = server.get_global_weights()

        client_weights = {}
        for cid in range(3):
            Xc, yc = splits[cid]
            c = FederatedClient(client_id=cid, client_name=f"Node-{cid}", X_local=Xc, y_local=yc, input_dim=input_dim, num_classes=num_classes, device="cpu")
            c.set_global_weights(w_global)
            c.local_train(epochs=1, batch_size=32, lr=0.005, global_weights=w_global)
            w = c.get_local_weights()
            if cid == 2:
                w = apply_sign_flipping_attack(w, scale=-2.0)
            client_weights[cid] = w

        trust_engine = MultiCriteriaTrustEngine(input_dim=input_dim, num_classes=num_classes, device="cpu")
        reports = trust_engine.evaluate_updates(client_weights, w_global, val_data=(X_val, y_val))

        assert reports[0]["is_valid"] is True
        assert reports[1]["is_valid"] is True
        assert reports[2]["is_valid"] is False  # Adversary Node 2 intercepted

        # Evaluate global model on held-out test set
        eval_res = server.evaluate(X_test, y_test)
        assert 0.0 <= eval_res["accuracy"] <= 1.0
        assert eval_res["loss"] >= 0.0

    def test_08_error_handling_invalid_inputs(self):
        """Verify informative exceptions for small, single-class, or missing-target datasets."""
        # Test case A: Dataset too small (< 20 rows)
        tiny_df = pd.DataFrame({"x": [1, 2, 3], "target": [0, 1, 0]})
        with pytest.raises(ValueError, match="too small"):
            CustomDatasetLoader(source=tiny_df).load_raw_data()

        # Test case B: Single-class target
        single_class_df = pd.DataFrame({"x": list(range(25)), "target": [1] * 25})
        with pytest.raises(ValueError, match="at least 2 classes"):
            CustomDatasetLoader(source=single_class_df).load_raw_data()

        # Test case C: Non-existent target column
        df = pd.DataFrame({"x": list(range(25)), "y": [0, 1] * 12 + [0]})
        with pytest.raises(ValueError, match="not found in dataset columns"):
            CustomDatasetLoader(source=df, target_column="non_existent_column").load_raw_data()

    def test_09_app_track_loaders_contract_and_structure(self):
        """Verify that app-level track loaders return conforming schemas and preserve isolation."""
        from app import load_track_a_dataset, load_track_b_preset, load_track_b_upload

        # Test Track A loader
        data_a = load_track_a_dataset()
        assert data_a["track"] == "Track A"
        assert data_a["X_train"].shape[1] == 122
        assert data_a["num_classes"] == 2
        assert data_a["scaler_fitted_samples"] == len(data_a["X_train"])
        assert len(data_a["X_val"]) == 1000

        # Test Track B preset loader
        for preset in ["breast_cancer", "iris", "wine"]:
            data_b = load_track_b_preset(preset)
            assert data_b["track"] == "Track B"
            assert data_b["scaler_fitted_samples"] == len(data_b["X_train"])
            assert not np.shares_memory(data_b["X_train"], data_b["X_val"])
            assert not np.shares_memory(data_b["X_train"], data_b["X_test"])

        # Test Track B upload loader
        csv_buffer = io.StringIO(
            "col1,col2,col3,label\n" +
            "\n".join([f"{i},{i*2},{i*3},{i%2}" for i in range(50)])
        )
        csv_buffer.name = "synthetic_data.csv"
        data_up = load_track_b_upload(csv_buffer, target_col="label")
        assert data_up["track"] == "Track B"
        assert data_up["name"] == "Uploaded: synthetic_data.csv"
        assert data_up["num_classes"] == 2
        assert data_up["scaler_fitted_samples"] == len(data_up["X_train"])

    def test_10_multi_track_server_respecification(self):
        """Verify server re-initialization when switching between Track A and Track B dimensions."""
        # Track A: (122, 2)
        srv_a = FederatedServer(input_dim=122, num_classes=2, device="cpu")
        assert srv_a.input_dim == 122
        assert srv_a.num_classes == 2

        # Track B (Iris): (4, 3)
        srv_b = FederatedServer(input_dim=4, num_classes=3, device="cpu")
        assert srv_b.input_dim == 4
        assert srv_b.num_classes == 3
        w_b = srv_b.get_global_weights()
        assert len(w_b) > 0

        # Verify Track B Iris forward pass
        dummy_x = np.random.randn(5, 4).astype(np.float32)
        dummy_y = np.array([0, 1, 2, 1, 0], dtype=np.int64)
        eval_b = srv_b.evaluate(dummy_x, dummy_y)
        assert "accuracy" in eval_b
        assert "loss" in eval_b
