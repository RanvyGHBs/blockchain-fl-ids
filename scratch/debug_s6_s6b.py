import copy
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

cfg_s6 = dict(base_cfg, scenario_name="S6", defense_enabled=False)
cfg_s6b = dict(base_cfg, scenario_name="S6b", defense_enabled=True)

# Step by step execution
orch_s6 = FederatedOrchestrator(cfg_s6)
orch_s6b = FederatedOrchestrator(cfg_s6b)

orch_s6.setup()
orch_s6b.setup()

# Check client weights after round 1
orch_s6._run_round(1, orch_s6.val_data)
orch_s6b._run_round(1, orch_s6b.val_data)

print("Round 1 global weights diff:", np.linalg.norm(orch_s6.server.get_global_weights() - orch_s6b.server.get_global_weights()))

# Now check client 0 training in round 2:
c0_s6 = orch_s6.clients[0]
c0_s6b = orch_s6b.clients[0]

c0_s6.set_global_weights(orch_s6.server.get_global_weights())
c0_s6b.set_global_weights(orch_s6b.server.get_global_weights())

# Check RNG states
print("np.random state match before R2 client 0:", np.random.get_state()[1][0] == np.random.get_state()[1][0])
print("torch RNG state match before R2 client 0:", torch.equal(torch.get_rng_state(), torch.get_rng_state()))

# Train client 0 in S6
c0_s6.local_train(epochs=1, batch_size=64, lr=0.002, round_num=2)
w0_s6 = c0_s6.get_local_weights()

# Train client 0 in S6b
# But wait! S6 already advanced torch RNG state when training client 0!
