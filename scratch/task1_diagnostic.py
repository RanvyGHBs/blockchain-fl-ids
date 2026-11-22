import sys
sys.path.insert(0, '.')
import json
import numpy as np
from src.federated.aggregators import aggregate_fedavg, aggregate_trust_weighted

# Load multi_attack_benchmarks_v3.json
with open('data/processed/stage2d/multi_attack_benchmarks_v3.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

s2b = d['scenarios']['s2b_targeted_labelflip_fedavg_defended']
s3 = d['scenarios']['s3_targeted_labelflip_defended']

print("=== S2b vs S3 Round-by-Round Inspection ===")
print("S2b aggregator configured:", s2b['config'].get('aggregation_algorithm'))
print("S3 aggregator configured:", s3['config'].get('aggregation_algorithm'))

for r_idx in range(1, 4):
    r_s2b = s2b['round_history'][r_idx]
    r_s3 = s3['round_history'][r_idx]
    
    print(f"\n--- Round {r_idx} ---")
    print(f"S2b rejected client IDs: {r_s2b.get('rejected_client_ids')}")
    print(f"S3 rejected client IDs: {r_s3.get('rejected_client_ids')}")
    print(f"S2b global weights hash: {r_s2b['global_weights_hash']}")
    print(f"S3 global weights hash: {r_s3['global_weights_hash']}")
    print(f"S2b reputation snapshot: {r_s2b.get('reputation_snapshot')}")
    print(f"S3 reputation snapshot: {r_s3.get('reputation_snapshot')}")
