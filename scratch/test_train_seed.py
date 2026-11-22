import sys
sys.path.insert(0, '.')
import numpy as np
import torch
import random
from src.federated.client import FederatedClient

# Client with identical seed
c1 = FederatedClient(0, "node0", np.ones((100, 10), dtype=np.float32), np.ones(100, dtype=np.int64), 10, 2, seed=42)
c2 = FederatedClient(0, "node0", np.ones((100, 10), dtype=np.float32), np.ones(100, dtype=np.int64), 10, 2, seed=42)

# Case A: without torch.manual_seed in local_train, do some arbitrary torch ops on c2 before training
torch.randn(100, 100) # advance torch RNG

c1.local_train(epochs=1, batch_size=16, round_num=1)
c2.local_train(epochs=1, batch_size=16, round_num=1)
diff_unseeded = np.linalg.norm(c1.get_local_weights() - c2.get_local_weights())
print(f"Diff without torch.manual_seed in local_train: {diff_unseeded:.6f}")

# Case B: with torch.manual_seed in local_train
c3 = FederatedClient(0, "node0", np.ones((100, 10), dtype=np.float32), np.ones(100, dtype=np.int64), 10, 2, seed=42)
c4 = FederatedClient(0, "node0", np.ones((100, 10), dtype=np.float32), np.ones(100, dtype=np.int64), 10, 2, seed=42)

torch.randn(100, 100) # advance torch RNG
torch.manual_seed((42 * 10007 + 1 * 997) % (2**31 - 1))
c3.local_train(epochs=1, batch_size=16, round_num=1)

torch.randn(500, 500) # advance torch RNG differently
torch.manual_seed((42 * 10007 + 1 * 997) % (2**31 - 1))
c4.local_train(epochs=1, batch_size=16, round_num=1)

diff_seeded = np.linalg.norm(c3.get_local_weights() - c4.get_local_weights())
print(f"Diff WITH torch.manual_seed in local_train: {diff_seeded:.6f}")
