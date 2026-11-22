import sys
sys.path.insert(0, '.')
import numpy as np
import hashlib
from src.federated.aggregators import aggregate_fedavg, aggregate_trust_weighted
from src.blockchain.crypto import CryptoManager

print("=== Task 1 Controlled Diagnostic: FedAvg vs Trust-Weighted FedAvg ===")

# Create controlled dummy client updates
np.random.seed(42)
cids = [0, 1, 2, 4] # Rejection of client 3 as in Round 3 of S2b/S3
client_updates = [np.random.randn(100).astype(np.float32) for _ in cids]
sample_counts = [5000, 6000, 5500, 4800] # Representative Dirichlet sample counts
reputations = [1.0, 1.0, 1.0, 1.0] # Production reputations of accepted clients

update_hashes = [CryptoManager.sha256_hash(w.tobytes().hex()) for w in client_updates]

# Normalized coefficients
total_samples = sum(sample_counts)
fedavg_coeffs = [n / total_samples for n in sample_counts]

eff_weights = [n * r for n, r in zip(sample_counts, reputations)]
total_eff = sum(eff_weights)
trust_coeffs = [eff / total_eff for eff in eff_weights]

print("\n--- Diagnostic Input Data ---")
for cid, uhash, count, rep, c_fed, c_tr in zip(cids, update_hashes, sample_counts, reputations, fedavg_coeffs, trust_coeffs):
    print(f"Client {cid}: Update Hash = {uhash[:16]}... | Samples = {count} | Rep = {rep:.2f} | FedAvg Coeff = {c_fed:.6f} | Trust Coeff = {c_tr:.6f}")

# Execute production aggregators
w_fedavg = aggregate_fedavg(client_updates, sample_counts)
w_trust = aggregate_trust_weighted(client_updates, sample_counts, reputations)

h_fedavg = CryptoManager.sha256_hash(w_fedavg.tobytes().hex())
h_trust = CryptoManager.sha256_hash(w_trust.tobytes().hex())
diff_l2 = float(np.linalg.norm(w_fedavg - w_trust))

print("\n--- Aggregation Outputs (Uniform Reputations [1.0, 1.0, 1.0, 1.0]) ---")
print(f"FedAvg Model Hash:        {h_fedavg}")
print(f"Trust-Weighted Model Hash: {h_trust}")
print(f"L2 Difference Vector Norm: {diff_l2:.10e}")
print(f"Bitwise Identical?        {h_fedavg == h_trust}")

# Diagnostic Part B: What if reputations are NON-UNIFORM?
print("\n--- Diagnostic Counterfactual: Non-Uniform Reputations [1.0, 0.8, 0.5, 0.2] ---")
non_uniform_reps = [1.0, 0.8, 0.5, 0.2]
eff_weights_nu = [n * r for n, r in zip(sample_counts, non_uniform_reps)]
total_eff_nu = sum(eff_weights_nu)
trust_coeffs_nu = [eff / total_eff_nu for eff in eff_weights_nu]

for cid, count, rep, c_fed, c_tr in zip(cids, sample_counts, non_uniform_reps, fedavg_coeffs, trust_coeffs_nu):
    print(f"Client {cid}: Samples = {count} | Rep = {rep:.2f} | FedAvg Coeff = {c_fed:.6f} | Trust Coeff = {c_tr:.6f}")

w_trust_nu = aggregate_trust_weighted(client_updates, sample_counts, non_uniform_reps)
h_trust_nu = CryptoManager.sha256_hash(w_trust_nu.tobytes().hex())
diff_nu = float(np.linalg.norm(w_fedavg - w_trust_nu))

print(f"Trust-Weighted (Non-Uniform) Model Hash: {h_trust_nu}")
print(f"L2 Difference Norm (Non-Uniform vs FedAvg): {diff_nu:.6f}")
print(f"Different from FedAvg? {h_fedavg != h_trust_nu}")
