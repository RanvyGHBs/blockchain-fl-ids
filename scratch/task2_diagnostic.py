import json

with open('data/processed/stage2d/multi_attack_benchmarks_v3.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

s4 = d['scenarios']['s4_sybil_coalition_median_undefended']
s4b = d['scenarios']['s4b_sybil_coalition_median_defended']

print("=== S4 vs S4b Inspection ===")
print("S4 Initial Model Hash: ", s4.get('initial_model_weights_hash'))
print("S4b Initial Model Hash:", s4b.get('initial_model_weights_hash'))
print("Initial Model Hashes Equal?", s4.get('initial_model_weights_hash') == s4b.get('initial_model_weights_hash'))

print("\nConfig Comparison:")
print("S4 Aggregation: ", s4['config'].get('aggregation_algorithm'))
print("S4b Aggregation:", s4b['config'].get('aggregation_algorithm'))
print("S4 Attack: ", s4['config'].get('attack_type'), s4['config'].get('malicious_client_ids'), "intensity:", s4['config'].get('sybil_intensity'))
print("S4b Attack:", s4b['config'].get('attack_type'), s4b['config'].get('malicious_client_ids'), "intensity:", s4b['config'].get('sybil_intensity'))
print("S4 Defense: ", s4['config'].get('defense_enabled'))
print("S4b Defense:", s4b['config'].get('defense_enabled'))

print("\nRound-by-Round Breakdown:")
for r in range(1, 4):
    r4 = s4['round_history'][r]
    r4b = s4b['round_history'][r]
    print(f"Round {r}:")
    print(f"  S4 : Acc = {r4['accuracy']*100:.2f}% | Loss = {r4['loss']:.4f} | Rej = {r4.get('rejected_client_ids')} | Active = {r4.get('num_active_clients')}")
    print(f"  S4b: Acc = {r4b['accuracy']*100:.2f}% | Loss = {r4b['loss']:.4f} | Rej = {r4b.get('rejected_client_ids')} | Active = {r4b.get('num_active_clients')}")

print("\nFinal Metrics:")
print(f"S4  Final Accuracy: {s4['final_accuracy']*100:.2f}% | MURR: {s4['cumulative_murr']} | PUAA: {s4['cumulative_puaa']}")
print(f"S4b Final Accuracy: {s4b['final_accuracy']*100:.2f}% | MURR: {s4b['cumulative_murr']} | PUAA: {s4b['cumulative_puaa']}")
print(f"Difference (S4b - S4): {(s4b['final_accuracy'] - s4['final_accuracy'])*100:.2f} percentage points")

print("\nDispositions:")
print("S4  Dispositions:", s4['cumulative_dispositions'])
print("S4b Dispositions:", s4b['cumulative_dispositions'])
