import json

with open("data/processed/stage2d/multi_attack_benchmarks.json", "r") as f:
    d1 = json.load(f)

with open("data/processed/stage2d/multi_attack_benchmarks_v2.json", "r") as f:
    d2 = json.load(f)

s3_v1 = d1["scenarios"]["s3_targeted_labelflip_defended"]
s3_v2 = d2["scenarios"]["s3_targeted_labelflip_defended"]

print("=== S3 V1 (Original) ===")
print("Config:", s3_v1["config"])
for r in s3_v1["round_history"]:
    print(f"Round {r['round']}: Acc={r['accuracy']*100:.2f}%, CleanAcc={r.get('clean_accuracy', 0)*100:.2f}%, ASR={r.get('asr', 0)*100:.2f}%, Rej={r['rejected_client_ids']}, NumRej={r['num_rejected']}, Loss={r['loss']:.4f}")

print("\n=== S3 V2 (Corrected v2) ===")
print("Config:", s3_v2["config"])
for r in s3_v2["round_history"]:
    print(f"Round {r['round']}: Acc={r['accuracy']*100:.2f}%, CleanAcc={r.get('clean_accuracy', 0)*100:.2f}%, ASR={r.get('asr', 0)*100:.2f}%, Rej={r['rejected_client_ids']}, NumRej={r['num_rejected']}, Loss={r['loss']:.4f}")
