import sys
sys.path.insert(0, '.')
import numpy as np
import torch
import random
from src.federated.orchestrator import FederatedOrchestrator
from src.data.nsl_kdd import NSLKDDLoader

loader = NSLKDDLoader(binary=True, seed=42)
X_train, y_train, X_val, y_val, X_test, y_test = loader.preprocess_isolated()

base_cfg = {
    "track": "Track A",
    "dataset": "nsl_kdd",
    "seed": 42,
    "device": "cpu",
    "num_clients": 5,
    "num_rounds": 2,
    "local_epochs": 1,
    "batch_size": 64,
    "lr": 0.002,
    "attack_enabled": True,
    "attack_type": "adaptive_byzantine",
    "malicious_client_ids": [3],
    "adaptive_stealth_factor": 0.8,
    "aggregation_algorithm": "fedavg",
    "X_train": X_train.copy(), "y_train": y_train.copy(),
    "X_val": X_val.copy(), "y_val": y_val.copy(),
    "X_test": X_test.copy(), "y_test": y_test.copy(),
    "feature_names": loader.feature_columns,
    "class_names": loader.get_class_names(),
}

random.seed(42); np.random.seed(42); torch.manual_seed(42)
orch_s6 = FederatedOrchestrator(dict(base_cfg, scenario_name="S6", defense_enabled=False))
orch_s6.setup()
orch_s6._run_round(1, orch_s6.val_data)

random.seed(42); np.random.seed(42); torch.manual_seed(42)
orch_s6b = FederatedOrchestrator(dict(base_cfg, scenario_name="S6b", defense_enabled=True))
orch_s6b.setup()
orch_s6b._run_round(1, orch_s6b.val_data)

c6 = orch_s6.clients[0]
c6b = orch_s6b.clients[0]

print("Xc equal?", np.array_equal(c6.X_local, c6b.X_local))
print("yc equal?", np.array_equal(c6.y_local, c6b.y_local))
print("Server R1 weights equal?", np.array_equal(orch_s6.server.get_global_weights(), orch_s6b.server.get_global_weights()))

c6.set_global_weights(orch_s6.server.get_global_weights())
c6b.set_global_weights(orch_s6b.server.get_global_weights())
print("Model weights before train equal?", np.array_equal(c6.get_local_weights(), c6b.get_local_weights()))

# Train with same seed
s_before_6 = (random.getstate(), np.random.get_state()[1][0], torch.get_rng_state())
print("Torch RNG state before S6 c0 train vs S6b c0 train equal?", torch.equal(torch.get_rng_state(), torch.get_rng_state()))
