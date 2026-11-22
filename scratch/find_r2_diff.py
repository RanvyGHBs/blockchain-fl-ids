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

# Run S6 to round 2
random.seed(42); np.random.seed(42); torch.manual_seed(42)
orch_s6 = FederatedOrchestrator(dict(base_cfg, scenario_name="S6", defense_enabled=False))
orch_s6.setup()
orch_s6._run_round(1, orch_s6.val_data)

# Run S6b to round 2
random.seed(42); np.random.seed(42); torch.manual_seed(42)
orch_s6b = FederatedOrchestrator(dict(base_cfg, scenario_name="S6b", defense_enabled=True))
orch_s6b.setup()
orch_s6b._run_round(1, orch_s6b.val_data)

# Now check state of clients before training in Round 2
print("Global weights R1 match:", np.allclose(orch_s6.server.get_global_weights(), orch_s6b.server.get_global_weights()))

# Let's see what happens inside client training in Round 2:
for cid in range(5):
    # Set global weights
    orch_s6.clients[cid].set_global_weights(orch_s6.server.get_global_weights())
    orch_s6b.clients[cid].set_global_weights(orch_s6b.server.get_global_weights())
    
    # Train client in S6
    orch_s6.clients[cid].local_train(epochs=1, batch_size=64, lr=0.002, round_num=2)
    w_s6 = orch_s6.clients[cid].get_local_weights()
    
    # Train client in S6b
    orch_s6b.clients[cid].local_train(epochs=1, batch_size=64, lr=0.002, round_num=2)
    w_s6b = orch_s6b.clients[cid].get_local_weights()
    
    diff = np.linalg.norm(w_s6 - w_s6b)
    print(f"Client {cid} R2 local weights diff: {diff:.8f}")
