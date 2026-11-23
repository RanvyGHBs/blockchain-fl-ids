import json

with open('data/processed/wp3/ablation_benchmarks.json') as f:
    a = json.load(f)

print("=== DYNAMIC DEFENSE MATRIX ABLATION MATRIX ===")
for r in a['runs']:
    print(f"{r['ablation_name']:25s} | FPR: {r['honest_fpr']:.4f} | DetRate: {r['malicious_detection_rate']:.4f} | Acc: {r['final_accuracy']:.4f}")

with open('data/processed/wp3/noise_sensitivity_benchmarks.json') as f:
    s = json.load(f)

print("\n=== NOISE SENSITIVITY SWEEP RESULTS ===")
for r in s['runs']:
    print(f"Sigma: {r['sigma']:.1f} | Mode: {r['calibration_mode']:15s} | FPR: {r['honest_fpr']:.4f} | Acc: {r['final_accuracy']:.4f}")
