import json
import numpy as np

with open("data/processed/stage2d/multi_attack_benchmarks_v2.json", "r") as f:
    data = json.load(f)

pairs = [
    ("s2_targeted_labelflip_undefended", "s2b_targeted_labelflip_fedavg_defended", "S2 vs S2b (Targeted Label Flip)"),
    ("s4_sybil_coalition_median_undefended", "s4b_sybil_coalition_median_defended", "S4 vs S4b (Sybil Coalition)"),
    ("s6_adaptive_byzantine_undefended", "s6b_parameterized_byzantine_fedavg_defended", "S6 vs S6b (Parameterized Byzantine)")
]

for k1, k2, title in pairs:
    s1 = data["scenarios"][k1]
    s2 = data["scenarios"][k2]
    print("=" * 80)
    print(f"ANALYSIS: {title}")
    print("=" * 80)
    print(f"{'Field':<30} | {k1:<25} | {k2:<25}")
    print("-" * 80)
    
    cfg1 = s1["config"]
    cfg2 = s2["config"]
    all_keys = sorted(list(set(cfg1.keys()) | set(cfg2.keys())))
    for k in all_keys:
        v1 = cfg1.get(k)
        v2 = cfg2.get(k)
        diff_marker = "DIFF" if v1 != v2 else ""
        print(f"{k:<30} | {str(v1):<25} | {str(v2):<25} {diff_marker}")
    
    print("\nRound Progression:")
    print(f"  {k1} (Final Acc: {s1['final_accuracy']*100:.2f}%, F1: {s1['final_f1_score']:.4f}):")
    for r in s1["round_history"]:
        print(f"    R{r['round']}: Acc={r['accuracy']*100:.2f}%, Loss={r['loss']:.4f}, Rej={r.get('rejected_client_ids', [])}, ASR={r.get('asr', 0)*100:.2f}%")
    print(f"  {k2} (Final Acc: {s2['final_accuracy']*100:.2f}%, F1: {s2['final_f1_score']:.4f}):")
    for r in s2["round_history"]:
        print(f"    R{r['round']}: Acc={r['accuracy']*100:.2f}%, Loss={r['loss']:.4f}, Rej={r.get('rejected_client_ids', [])}, ASR={r.get('asr', 0)*100:.2f}%")
    print()
