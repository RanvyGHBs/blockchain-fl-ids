import json, os

bench_file = 'data/processed/wp3/multi_seed_benchmarks.json'
abl_file = 'data/processed/wp3/ablation_benchmarks.json'
sens_file = 'data/processed/wp3/noise_sensitivity_benchmarks.json'
stat_file = 'data/processed/wp3/statistical_summary.json'

if os.path.exists(bench_file):
    with open(bench_file) as f:
        b = json.load(f)
    print(f"Multi-seed runs completed: {len(b['runs'])} / 50")
    from collections import Counter
    c = Counter((r['attack_type'], r['calibration_mode']) for r in b['runs'])
    for k, v in sorted(c.items()):
        print(f"  {k}: {v}/5")

if os.path.exists(abl_file):
    with open(abl_file) as f:
        a = json.load(f)
    print(f"Ablation runs completed: {len(a['runs'])} / 8")
else:
    print("Ablation: pending")

if os.path.exists(sens_file):
    with open(sens_file) as f:
        s = json.load(f)
    print(f"Sensitivity runs completed: {len(s['runs'])} / 6")
else:
    print("Sensitivity: pending")

print("Statistical summary ready:", os.path.exists(stat_file))
