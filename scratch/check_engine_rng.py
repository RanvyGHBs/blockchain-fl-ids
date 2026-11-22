import numpy as np
import torch
import random
from src.federated.trust_engine import MultiCriteriaTrustEngine
from src.federated.orchestrator import FederatedOrchestrator

# Compare step by step in Round 1
# Check what happens during defense_active:
# 1. trust_engine.evaluate_updates
# 2. reputation_mgr.update_reputation
# 3. blockchain.add_transaction / select_validator / forge_block
print("Checking MultiCriteriaTrustEngine evaluate_updates...")
te = MultiCriteriaTrustEngine(122, 2)
# Does te.evaluate_updates touch torch / np random state?
s_np = np.random.get_state()[1][0]
s_py = random.getstate()
s_th = torch.get_rng_state()

# Let's run a test
print("RNG state before evaluate_updates recorded.")
