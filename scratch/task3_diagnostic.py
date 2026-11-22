import sys
sys.path.insert(0, '.')
import platform
import numpy as np
import torch
import random
from src.federated.orchestrator import FederatedOrchestrator
from src.data.nsl_kdd import NSLKDDLoader
from src.blockchain.crypto import CryptoManager

print("=== Task 3: Runtime Environment & Determinism Inspection ===")
print("Python Version:   ", sys.version.replace('\n', ' '))
print("PyTorch Version:  ", torch.__version__)
print("NumPy Version:    ", np.__version__)
print("Operating System: ", platform.platform())
print("Processor:        ", platform.processor())
print("CUDA Available:   ", torch.cuda.is_available())
if torch.cuda.is_available():
    print("CUDA Device:      ", torch.cuda.get_device_name(0))
    print("cuDNN Version:    ", torch.backends.cudnn.version())
    print("cuDNN Deterministic:", torch.backends.cudnn.deterministic)
    print("cuDNN Benchmark:  ", torch.backends.cudnn.benchmark)
print("torch.are_deterministic_algorithms_enabled():", torch.are_deterministic_algorithms_enabled())

# Load isolated NSL-KDD
loader = NSLKDDLoader(binary=True, seed=42)
X_train, y_train, X_val, y_val, X_test, y_test = loader.preprocess_isolated()

cfg = {
    "scenario_name": "determ_test",
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
    "attack_type": "targeted_label_flip",
    "malicious_client_ids": [3],
    "label_flip_source": 1,
    "label_flip_target": 0,
    "label_flip_ratio": 1.0,
    "defense_enabled": True,
    "aggregation_algorithm": "fedavg",
    "X_train": X_train.copy(), "y_train": y_train.copy(),
    "X_val": X_val.copy(), "y_val": y_val.copy(),
    "X_test": X_test.copy(), "y_test": y_test.copy(),
    "feature_names": loader.feature_columns,
    "class_names": loader.get_class_names(),
}

print("\n--- Running Run 1 ---")
random.seed(42); np.random.seed(42); torch.manual_seed(42)
orch1 = FederatedOrchestrator(dict(cfg))
res1 = orch1.run()

print("\n--- Running Run 2 ---")
random.seed(42); np.random.seed(42); torch.manual_seed(42)
orch2 = FederatedOrchestrator(dict(cfg))
res2 = orch2.run()

# Compare initial model hashes
h_init_1 = res1["initial_model_weights_hash"]
h_init_2 = res2["initial_model_weights_hash"]
print(f"\nInitial Model Hash 1: {h_init_1}")
print(f"Initial Model Hash 2: {h_init_2}")
print(f"Initial Model Hashes Match? {h_init_1 == h_init_2}")

# Compare client partition hashes
p_hashes_1 = [CryptoManager.sha256_hash(c.X_local.tobytes().hex()) for c in orch1.clients]
p_hashes_2 = [CryptoManager.sha256_hash(c.X_local.tobytes().hex()) for c in orch2.clients]
print(f"Client Partitions Match across all clients? {p_hashes_1 == p_hashes_2}")

# Compare round 1 & 2 model hashes
r1_h1 = res1["round_history"][1]["global_weights_hash"]
r1_h2 = res2["round_history"][1]["global_weights_hash"]
print(f"Round 1 Global Weights Match? {r1_h1 == r1_h2} ({r1_h1[:16]}... vs {r1_h2[:16]}...)")

r2_h1 = res1["round_history"][2]["global_weights_hash"]
r2_h2 = res2["round_history"][2]["global_weights_hash"]
print(f"Round 2 Global Weights Match? {r2_h1 == r2_h2} ({r2_h1[:16]}... vs {r2_h2[:16]}...)")

# Compare final metrics
print(f"Final Accuracy 1: {res1['final_accuracy']*100:.4f}% | 2: {res2['final_accuracy']*100:.4f}%")
print(f"Final Loss 1:     {res1['final_loss']:.6f} | 2: {res2['final_loss']:.6f}")
print(f"Final ASR 1:      {res1['final_asr']*100:.4f}% | 2: {res2['final_asr']*100:.4f}%")
print(f"Identical Evaluation Metrics? {res1['final_accuracy'] == res2['final_accuracy'] and res1['final_loss'] == res2['final_loss']}")
