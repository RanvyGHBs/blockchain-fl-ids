import json
import numpy as np

with open('data/processed/stage2d/multi_attack_benchmarks_v3.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

s6 = d['scenarios']['s6_adaptive_byzantine_undefended']
s6b = d['scenarios']['s6b_parameterized_byzantine_fedavg_defended']

print("S6 Round 1 hash:", s6['round_history'][1]['global_weights_hash'])
print("S6b Round 1 hash:", s6b['round_history'][1]['global_weights_hash'])
print("Are Round 1 hashes identical?", s6['round_history'][1]['global_weights_hash'] == s6b['round_history'][1]['global_weights_hash'])

print("S6 Round 2 hash:", s6['round_history'][2]['global_weights_hash'])
print("S6b Round 2 hash:", s6b['round_history'][2]['global_weights_hash'])
