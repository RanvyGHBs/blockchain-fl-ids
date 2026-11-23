import json

with open('data/processed/wp3/multi_seed_benchmarks.json') as f:
    d = json.load(f)

for att in ['clean_dp', 'gaussian_noise', 'model_scaling', 'sign_flip', 'label_flip']:
    print(f"\n### Scenario: {att}")
    uncal = {r['seed']: r for r in d['runs'] if r['attack_type'] == att and r['calibration_mode'] == 'uncalibrated'}
    cal = {r['seed']: r for r in d['runs'] if r['attack_type'] == att and r['calibration_mode'] == 'privacy_aware'}
    print("| Seed | Engine | Honest FPR | Malicious DetRate | Quarantined Honest | Final Accuracy | Final F1 | Total Time |")
    print("|---|---|---:|---:|---:|---:|---:|---:|")
    for s in [42, 101, 2024, 777, 999]:
        u = uncal.get(s, {})
        c = cal.get(s, {})
        print(f"| {s} | Uncalibrated | {u.get('honest_fpr', 0.0)*100:.1f}% | {u.get('malicious_detection_rate', 0.0)*100:.1f}% | {u.get('honest_quarantined_count', 0)} | {u.get('final_accuracy', 0.0)*100:.2f}% | {u.get('final_f1', 0.0):.4f} | {u.get('elapsed_seconds', 0.0):.1f}s |")
        print(f"| {s} | Calibrated | {c.get('honest_fpr', 0.0)*100:.1f}% | {c.get('malicious_detection_rate', 0.0)*100:.1f}% | {c.get('honest_quarantined_count', 0)} | {c.get('final_accuracy', 0.0)*100:.2f}% | {c.get('final_f1', 0.0):.4f} | {c.get('elapsed_seconds', 0.0):.1f}s |")
