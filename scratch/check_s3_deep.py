import json

with open("data/processed/stage2d/multi_attack_benchmarks.json", "r") as f:
    d1 = json.load(f)

with open("data/processed/stage2d/multi_attack_benchmarks_v2.json", "r") as f:
    d2 = json.load(f)

def print_scenario_details(sc, label):
    print(f"\n--- {label} ---")
    print(f"Scenario Name: {sc.get('scenario_name')}")
    print(f"Final Acc: {sc['final_accuracy']*100:.2f}%, F1: {sc['final_f1_score']:.4f}")
    if "cumulative_murr" in sc:
        print(f"Cum MURR: {sc['cumulative_murr']}, Cum PUAA: {sc['cumulative_puaa']}")
    for r in sc["round_history"]:
        acc = r['accuracy']*100
        loss = r['loss']
        rej = r.get('rejected_client_ids', [])
        asr = r.get('asr', 0)*100
        mudr = r.get('mudr')
        murr = r.get('murr')
        print(f"  Round {r['round']}: Acc={acc:.2f}%, Loss={loss:.4f}, ASR={asr:.2f}%, Rej={rej}, MUDR={mudr}, MURR={murr}")

print_scenario_details(d1["scenarios"]["s3_targeted_labelflip_defended"], "S3 in V1")
print_scenario_details(d2["scenarios"]["s3_targeted_labelflip_defended"], "S3 in V2")
