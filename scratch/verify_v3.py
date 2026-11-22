import json
import sys

with open('data/processed/stage2d/multi_attack_benchmarks_v3.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

scenarios = d['scenarios']
print(f'Total scenarios: {len(scenarios)}')

init_hashes = {k: v.get('initial_model_weights_hash') for k, v in scenarios.items()}
unique_hashes = set(init_hashes.values())
print(f'Unique initial model hashes count: {len(unique_hashes)}')
for h in unique_hashes:
    print(f'  Initial model hash: {h}')

print("\nDetailed Scenario Checks:")
for k, sc in scenarios.items():
    acc = sc['final_accuracy'] * 100
    asr = sc.get('final_asr')
    asr_str = f"{asr * 100:.2f}%" if asr is not None else "None (N/A)"
    murr = sc.get('cumulative_murr')
    murr_str = f"{murr * 100:.1f}%" if murr is not None else "None"
    fpr = sc.get('cumulative_fpr')
    fpr_str = f"{fpr * 100:.1f}%" if fpr is not None else "None"
    cfg_hash = sc.get('config_hash')[:12]
    
    # Check conservation
    disp = sc['cumulative_dispositions']
    mal = disp['malicious']
    hon = disp['honest']
    mal_cons = (mal['submitted'] == mal['rejected_crypto'] + mal['rejected_trust'] + mal['accepted_aggregated'])
    hon_cons = (hon['submitted'] == hon['rejected_crypto'] + hon['rejected_trust'] + hon['accepted_aggregated'])
    
    print(f"{k:<45} | Acc: {acc:.2f}% | ASR: {asr_str:<12} | MURR: {murr_str:<6} | FPR: {fpr_str:<6} | MalCons: {mal_cons} | HonCons: {hon_cons}")
