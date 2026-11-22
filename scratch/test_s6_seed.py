import sys
sys.path.insert(0, '.')
import torch
import numpy as np
from src.data.nsl_kdd import NSLKDDLoader
from src.federated.orchestrator import FederatedOrchestrator

loader = NSLKDDLoader(binary=True, seed=42)
X_train, y_train, X_val, y_val, X_test, y_test = loader.preprocess_isolated()

# Test S6 fresh
torch.manual_seed(42)
np.random.seed(42)
cfg_s6 = {
    "scenario_name": "S6",
    "track": "Track A",
    "seed": 42,
    "device": "cpu",
    "num_clients": 5,
    "num_rounds": 1,
    "local_epochs": 1,
    "batch_size": 64,
    "lr": 0.002,
    "attack_enabled": True,
    "attack_type": "adaptive_byzantine",
    "malicious_client_ids": [3],
    "adaptive_stealth_factor": 0.8,
    "defense_enabled": False,
    "aggregation_algorithm": "fedavg",
    "X_train": X_train.copy(),
    "y_train": y_train.copy(),
    "X_val": X_val.copy(),
    "y_val": y_val.copy(),
    "X_test": X_test.copy(),
    "y_test": y_test.copy(),
}
orch6 = FederatedOrchestrator(cfg_s6)
res6 = orch6.run()

# Test S6b fresh
torch.manual_seed(42)
np.random.seed(42)
cfg_s6b = dict(cfg_s6)
cfg_s6b["scenario_name"] = "S6b"
cfg_s6b["defense_enabled"] = True
orch6b = FederatedOrchestrator(cfg_s6b)
res6b = orch6b.run()

print("\n--- S6 vs S6b WITH EXACT SEED RESET ---")
print("S6 fresh Acc:", res6["final_accuracy"], "Loss:", res6["final_loss"])
print("S6b fresh Acc:", res6b["final_accuracy"], "Loss:", res6b["final_loss"])
print("Difference:", abs(res6["final_accuracy"] - res6b["final_accuracy"]))
