import sys
sys.path.insert(0, '.')
import torch
import numpy as np
from src.trust.evaluator import MultiCriteriaTrustEngine
from src.federated.client import FederatedClient

# Two clients initialized with identical weights & data
c_s6 = FederatedClient(0, "node0", np.ones((100, 10), dtype=np.float32), np.ones(100, dtype=np.int64), 10, 2, seed=42)
c_s6b = FederatedClient(0, "node0", np.ones((100, 10), dtype=np.float32), np.ones(100, dtype=np.int64), 10, 2, seed=42)

# Simulate Round 1 ending: both clients have identical weights
# Now simulate Step B: S6b runs evaluate_updates, S6 does not!
te = MultiCriteriaTrustEngine(10, 2)
w = te.validator_model.get_weights_vector()
val_data = (np.ones((20, 10), dtype=np.float32), np.ones(20, dtype=np.int64))
te.evaluate_updates({0: w, 1: w}, w, val_data) # This changed torch RNG for S6b

# Now Round 2 starts:
# If client seeds torch.manual_seed at start of local_train:
train_seed = (42 * 10007 + 2 * 997) % (2**31 - 1)

torch.manual_seed(train_seed)
c_s6.local_train(epochs=1, batch_size=16, round_num=2)

torch.manual_seed(train_seed)
c_s6b.local_train(epochs=1, batch_size=16, round_num=2)

diff = np.linalg.norm(c_s6.get_local_weights() - c_s6b.get_local_weights())
print(f"Diff in Round 2 when client seeds local_train: {diff:.8f}")
