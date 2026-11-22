import json

with open('data/processed/stage2d/multi_attack_benchmarks_v3.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

for k in ['s6_adaptive_byzantine_undefended', 's6b_parameterized_byzantine_fedavg_defended']:
    sc = d['scenarios'][k]
    print(f"\nScenario: {k}")
    r2 = sc['round_history'][2]
    print(f"  Round 2: rej={r2.get('rejected_client_ids')}")
    print(f"  Dispositions: {r2.get('dispositions')}")
