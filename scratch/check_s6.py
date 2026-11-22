import json

with open('data/processed/stage2d/multi_attack_benchmarks_v3.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

for k in ['s6_adaptive_byzantine_undefended', 's6b_parameterized_byzantine_fedavg_defended']:
    sc = d['scenarios'][k]
    print(f"\nScenario: {k}")
    for r in sc['round_history']:
        print(f"  Round {r['round']}: acc={r['accuracy']*100:.2f}%, rej={r.get('rejected_client_ids')}, weights_hash={r['global_weights_hash'][:16]}")
