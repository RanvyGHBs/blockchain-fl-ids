"""
Stage 2C Test Suite: Dynamic Model Architecture & Multi-Track Integration.

Verifies end-to-end dynamic parameterization of:
1. FederatedOrchestrator routing across Track A (NSL-KDD) and Track B (Custom datasets).
2. Dynamic input dimension (D) and class count (C) adaptation for IDSNet, FederatedServer,
   FederatedClient, and MultiCriteriaTrustEngine.
3. Multi-class classification metrics (Macro/Weighted Precision, Recall, F1) across
   FederatedOrchestrator.evaluate(), FederatedServer.evaluate(), and FederatedClient.evaluate().
4. Adversarial attack injection and Multi-Criteria Trust defense on multi-class models.
5. Strict 3-way research data isolation (no test data leakage to trust validation or training).
6. FastFeatureExplainer dynamic class naming for multi-class and binary architectures.
7. 100% backward compatibility and regression protection for Track A.
"""

import unittest
import numpy as np
import pandas as pd
import torch

from src.data.custom_loader import CustomDatasetLoader
from src.data.nsl_kdd import NSLKDDLoader
from src.federated.orchestrator import FederatedOrchestrator
from src.federated.server import FederatedServer
from src.federated.client import FederatedClient
from src.trust.evaluator import MultiCriteriaTrustEngine
from src.models.ids_net import IDSNet
from src.xai.explainer import FastFeatureExplainer


class TestStage2CDynamicArchitecture(unittest.TestCase):

    def test_01_orchestrator_iris_multiclass_dynamic_routing(self):
        """Verify FederatedOrchestrator dynamically configures for Iris (D=4, C=3)."""
        config = {
            "scenario_name": "stage2c_iris_test",
            "track": "Track B",
            "dataset": "iris",
            "seed": 42,
            "device": "cpu",
            "num_clients": 3,
            "num_rounds": 2,
            "local_epochs": 1,
            "batch_size": 16,
            "lr": 0.01,
            "defense_enabled": False,
        }
        orch = FederatedOrchestrator(config)
        self.assertEqual(orch.input_dim, 4)
        self.assertEqual(orch.num_classes, 3)
        self.assertEqual(len(orch.class_names), 3)

        results = orch.run()
        self.assertEqual(results["track"], "Track B")
        self.assertEqual(results["dataset"], "iris")
        self.assertEqual(results["input_dim"], 4)
        self.assertEqual(results["num_classes"], 3)
        self.assertIn("final_f1_score_macro", results)
        self.assertIn("final_precision_macro", results)
        self.assertIn("final_recall_macro", results)
        self.assertGreaterEqual(results["final_accuracy"], 0.0)
        self.assertTrue(results["chain_valid"])

    def test_02_orchestrator_wine_multiclass_dynamic_routing(self):
        """Verify FederatedOrchestrator dynamically configures for Wine (D=13, C=3)."""
        config = {
            "scenario_name": "stage2c_wine_test",
            "track": "Track B",
            "dataset": "wine",
            "seed": 42,
            "device": "cpu",
            "num_clients": 3,
            "num_rounds": 2,
            "local_epochs": 1,
            "batch_size": 16,
            "lr": 0.01,
            "defense_enabled": False,
        }
        orch = FederatedOrchestrator(config)
        self.assertEqual(orch.input_dim, 13)
        self.assertEqual(orch.num_classes, 3)

        results = orch.run()
        self.assertEqual(results["input_dim"], 13)
        self.assertEqual(results["num_classes"], 3)
        self.assertIsInstance(results["final_accuracy"], float)
        self.assertIsInstance(results["final_f1_score_macro"], float)

    def test_03_orchestrator_breast_cancer_binary_routing(self):
        """Verify FederatedOrchestrator dynamically configures for Breast Cancer (D=30, C=2)."""
        config = {
            "scenario_name": "stage2c_breast_cancer_test",
            "track": "Track B",
            "dataset": "breast_cancer",
            "seed": 42,
            "device": "cpu",
            "num_clients": 3,
            "num_rounds": 2,
            "local_epochs": 1,
            "batch_size": 32,
            "defense_enabled": False,
        }
        orch = FederatedOrchestrator(config)
        self.assertEqual(orch.input_dim, 30)
        self.assertEqual(orch.num_classes, 2)

        results = orch.run()
        self.assertEqual(results["input_dim"], 30)
        self.assertEqual(results["num_classes"], 2)
        self.assertGreaterEqual(results["final_accuracy"], 0.0)

    def test_04_orchestrator_custom_loader_direct_injection(self):
        """Verify passing a CustomDatasetLoader instance directly to orchestrator."""
        np.random.seed(99)
        N = 120
        df = pd.DataFrame({
            "num1": np.random.randn(N),
            "num2": np.random.uniform(10, 50, N),
            "cat1": np.random.choice(["X", "Y", "Z"], N),
            "target": np.random.choice([0, 1, 2, 3], N)  # 4 classes
        })
        loader = CustomDatasetLoader(source=df, target_column="target", dataset_name="Synthetic4Class", seed=99)

        config = {
            "scenario_name": "stage2c_loader_injection",
            "loader": loader,
            "seed": 99,
            "device": "cpu",
            "num_clients": 3,
            "num_rounds": 2,
            "batch_size": 16,
            "defense_enabled": False,
        }
        orch = FederatedOrchestrator(config)
        # 2 numeric + 3 one-hot columns = 5 features; 4 classes
        self.assertEqual(orch.input_dim, 5)
        self.assertEqual(orch.num_classes, 4)

        results = orch.run()
        self.assertEqual(results["input_dim"], 5)
        self.assertEqual(results["num_classes"], 4)
        self.assertEqual(len(results["round_history"]), 3)  # round 0, 1, 2

    def test_05_multiclass_adversarial_attack_and_trust_defense(self):
        """Verify MultiCriteriaTrustEngine successfully detects and rejects attacks on multi-class models."""
        config = {
            "scenario_name": "stage2c_multiclass_defense",
            "track": "Track B",
            "dataset": "wine",
            "seed": 42,
            "device": "cpu",
            "num_clients": 4,
            "num_rounds": 2,
            "local_epochs": 1,
            "batch_size": 16,
            "lr": 0.01,
            "attack_enabled": True,
            "malicious_client_ids": [2],
            "attack_type": "gaussian_noise",
            "defense_enabled": True,
        }
        orch = FederatedOrchestrator(config)
        self.assertEqual(orch.num_classes, 3)

        results = orch.run()
        round_1 = results["round_history"][1]
        self.assertIn(2, round_1["rejected_client_ids"])
        self.assertGreater(round_1["num_rejected"], 0)
        # Slashed reputation for attacker
        rep_attacker = results["reputation_summary"]["reputations"][2]
        self.assertLess(rep_attacker, 1.0)
        self.assertTrue(results["chain_valid"])

    def test_06_multiclass_label_flip_attack_handling(self):
        """Verify label-flip attack setup dynamically handles multi-class targets."""
        config = {
            "scenario_name": "stage2c_label_flip_multiclass",
            "track": "Track B",
            "dataset": "iris",
            "seed": 42,
            "device": "cpu",
            "num_clients": 3,
            "num_rounds": 1,
            "local_epochs": 1,
            "batch_size": 16,
            "attack_enabled": True,
            "malicious_client_ids": [1],
            "attack_type": "label_flip",
            "label_flip_source": 1,
            "label_flip_target": 2,
            "defense_enabled": True,
        }
        orch = FederatedOrchestrator(config)
        self.assertEqual(orch.num_classes, 3)
        results = orch.run()
        self.assertEqual(results["num_classes"], 3)
        self.assertEqual(len(results["round_history"]), 2)

    def test_07_strict_data_isolation_validation_benchmark_not_test(self):
        """Verify that trust validation never touches or leaks held-out test data."""
        loader = CustomDatasetLoader(source="iris", seed=42)
        X_train, y_train, X_val, y_val, X_test, y_test = loader.preprocess_isolated(val_size=0.15, test_size=0.20)

        config = {
            "scenario_name": "stage2c_isolation_test",
            "X_train": X_train, "y_train": y_train,
            "X_val": X_val, "y_val": y_val,
            "X_test": X_test, "y_test": y_test,
            "num_classes": 3,
            "seed": 42,
            "device": "cpu",
            "num_clients": 3,
            "num_rounds": 1,
            "defense_enabled": True,
        }
        orch = FederatedOrchestrator(config)
        orch.setup()

        # Run 1 round
        val_data = (orch.X_val, orch.y_val)
        self.assertFalse(np.shares_memory(orch.X_test, val_data[0]))
        self.assertFalse(np.shares_memory(orch.y_test, val_data[1]))
        self.assertEqual(len(val_data[0]), len(X_val))

        round_record = orch._run_round(1, val_data)
        self.assertIn("accuracy", round_record)
        self.assertIn("precision_macro", round_record)

    def test_08_evaluate_method_contract_and_macro_weighted_metrics(self):
        """Verify evaluate() on orchestrator, server, and client supports multi-class metrics."""
        np.random.seed(42)
        d, c = 8, 3
        server = FederatedServer(input_dim=d, num_classes=c, device="cpu")
        client = FederatedClient(
            client_id=0, client_name="TestNode",
            X_local=np.random.rand(30, d).astype(np.float32),
            y_local=np.random.randint(0, c, size=30).astype(np.int64),
            input_dim=d, num_classes=c, device="cpu"
        )

        X_eval = np.random.rand(40, d).astype(np.float32)
        y_eval = np.random.randint(0, c, size=40).astype(np.int64)

        # Server evaluate
        s_eval = server.evaluate(X_eval, y_eval, batch_size=16)
        for key in ["accuracy", "precision", "recall", "f1_score", "precision_macro", "recall_macro", "f1_score_macro", "confusion_matrix"]:
            self.assertIn(key, s_eval)
        self.assertEqual(len(s_eval["confusion_matrix"]), c)

        # Client evaluate
        c_eval = client.evaluate(X_eval, y_eval, batch_size=16)
        for key in ["accuracy", "precision", "recall", "f1_score", "precision_macro", "recall_macro", "f1_score_macro"]:
            self.assertIn(key, c_eval)

        # Orchestrator evaluate
        config = {
            "scenario_name": "eval_contract_test",
            "X_train": np.random.rand(60, d).astype(np.float32),
            "y_train": np.random.randint(0, c, size=60).astype(np.int64),
            "X_test": X_eval, "y_test": y_eval,
            "num_classes": c,
            "seed": 42,
            "device": "cpu",
            "num_clients": 3,
            "num_rounds": 1,
        }
        orch = FederatedOrchestrator(config)
        orch.setup()
        o_eval = orch.evaluate()
        self.assertIn("precision_macro", o_eval)
        self.assertIn("f1_score_macro", o_eval)

    def test_09_fast_feature_explainer_multiclass_and_binary(self):
        """Verify FastFeatureExplainer outputs human-readable labels for multi-class and binary models."""
        # 1. Multi-Class Model with class_names
        model_3c = IDSNet(input_dim=4, num_classes=3)
        explainer_3c = FastFeatureExplainer(
            model_3c, feature_names=["sepal_l", "sepal_w", "petal_l", "petal_w"],
            class_names=["Setosa", "Versicolour", "Virginica"]
        )
        sample = np.array([5.1, 3.5, 1.4, 0.2], dtype=np.float32)
        exp_res = explainer_3c.explain_flow(sample, top_k=3)
        self.assertIn(exp_res["class_label"], ["Setosa", "Versicolour", "Virginica"])
        self.assertEqual(len(exp_res["top_features"]), 3)

        # 2. Binary Model default backward compatibility
        model_2c = IDSNet(input_dim=10, num_classes=2)
        explainer_2c = FastFeatureExplainer(model_2c, feature_names=[f"f_{i}" for i in range(10)])
        exp_bin = explainer_2c.explain_flow(np.random.rand(10).astype(np.float32), top_k=3)
        self.assertIn(exp_bin["class_label"], ["Attack", "Normal"])

    def test_10_track_a_backward_compatibility_regression(self):
        """Verify Track A synthetic workflow runs without regression and returns standard contract."""
        np.random.seed(7)
        d, c = 20, 2
        X_tr = np.random.rand(100, d).astype(np.float32)
        y_tr = np.random.randint(0, c, size=100).astype(np.int64)
        X_te = np.random.rand(50, d).astype(np.float32)
        y_te = np.random.randint(0, c, size=50).astype(np.int64)

        config = {
            "scenario_name": "track_a_regression_check",
            "seed": 7,
            "device": "cpu",
            "num_clients": 3,
            "num_rounds": 2,
            "local_epochs": 1,
            "batch_size": 32,
            "lr": 0.005,
            "aggregation_algorithm": "fedavg",
            "attack_enabled": False,
            "defense_enabled": False,
            "dp_enabled": False,
            "X_train": X_tr, "y_train": y_tr,
            "X_test": X_te, "y_test": y_te,
            "feature_names": [f"feat_{i}" for i in range(d)],
        }
        orch = FederatedOrchestrator(config)
        self.assertEqual(orch.input_dim, 20)
        self.assertEqual(orch.num_classes, 2)
        results = orch.run()

        expected_keys = [
            "scenario_name", "final_accuracy", "final_f1_score", "final_precision",
            "final_recall", "final_loss", "total_time_sec", "round_history",
            "attack_log", "dp_accounting", "blockchain_summary", "reputation_summary",
            "chain_valid", "xai_demo"
        ]
        for k in expected_keys:
            self.assertIn(k, results)
        self.assertTrue(results["chain_valid"])
        self.assertEqual(len(results["round_history"]), 3)


if __name__ == "__main__":
    unittest.main()
