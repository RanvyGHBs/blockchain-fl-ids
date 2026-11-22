import sys
sys.path.insert(0, '.')
import torch
import numpy as np
from src.data.nsl_kdd import NSLKDDLoader
from src.federated.orchestrator import FederatedOrchestrator

loader = NSLKDDLoader(binary=True, seed=42)
X_train, y_train, X_val, y_val, X_test, y_test = loader.preprocess_isolated()

# Test 1: Run S2 fresh
torch.manual_seed(42)
np.random.seed(42)
cfg_s2 = {
    "scenario_name": "S2",
    "track": "Track A",
    "seed": 42,
    "device": "cpu",
    "num_clients": 5,
    "num_rounds": 1,
    "local_epochs": 1,
    "batch_size": 64,
    "lr": 0.002,
    "attack_enabled": True,
    "attack_type": "targeted_label_flip",
    "malicious_client_ids": [3],
    "label_flip_source": 1,
    "label_flip_target": 0,
    "label_flip_ratio": 1.0,
    "defense_enabled": False,
    "aggregation_algorithm": "fedavg",
    "X_train": X_train.copy(),
    "y_train": y_train.copy(),
    "X_val": X_val.copy(),
    "y_val": y_val.copy(),
    "X_test": X_test.copy(),
    "y_test": y_test.copy(),
}
orch2 = FederatedOrchestrator(cfg_s2)
res2 = orch2.run()

# Test 2: Run S2b fresh with the exact same seed reset
torch.manual_seed(42)
np.random.seed(42)
cfg_s2b = dict(cfg_s2)
cfg_s2b["scenario_name"] = "S2b"
cfg_s2b["defense_enabled"] = True
orch2b = FederatedOrchestrator(cfg_s2b)
res2b = orch2b.run()

print("\n--- COMPARISON WITH EXACT SEED RESET ---")
print("S2 fresh Acc:", res2["final_accuracy"], "Loss:", res2["final_loss"])
print("S2b fresh Acc:", res2b["final_accuracy"], "Loss:", res2b["final_loss"])
print("Difference:", abs(res2["final_accuracy"] - res2b["final_accuracy"]))
