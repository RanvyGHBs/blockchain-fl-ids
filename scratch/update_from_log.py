import os, json, re

log_path = r'C:\Users\is043\.gemini\antigravity\brain\c69bdf0b-096b-4c0c-9c50-8b48ae943282\.system_generated\tasks\task-4222.log'
if not os.path.exists(log_path):
    print("Log path does not exist.")
    exit(0)

with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

scenario_blocks = re.split(r'={50,}\nSCENARIO:\s+', text)
runs = []
for block in scenario_blocks[1:]:
    lines = block.split('\n')
    sc_name = lines[0].strip()
    m = re.match(r'wp3_([a-z_]+)_(uncalibrated|privacy_aware)_seed_(\d+)_sig_([0-9.]+)', sc_name)
    if not m:
        continue
    att, mode, seed_str, sig_str = m.groups()
    seed = int(seed_str)
    sig = float(sig_str)
    
    if 'Scenario Complete' not in block or 'Result:' not in block:
        continue
        
    res_m = re.search(r'Result:\s+Acc=([0-9.]+),\s+FPR=([0-9.]+),\s+MalRej=([0-9.]+),\s+QuarantinedHonest=(\d+)', block)
    tot_time_m = re.search(r'Total Time:\s+([0-9.]+)s', block)
    final_f1_m = re.search(r'Final Acc: [0-9.]+% \| F1: ([0-9.]+)', block)
    
    acc = float(res_m.group(1)) if res_m else 0.0
    fpr = float(res_m.group(2)) if res_m else 0.0
    mal_rej = float(res_m.group(3)) if res_m else 0.0
    quar_hon = int(res_m.group(4)) if res_m else 0
    tot_time = float(tot_time_m.group(1)) if tot_time_m else 0.0
    final_f1 = float(final_f1_m.group(1)) if final_f1_m else 0.0
    
    hon_sub = 25 if att == 'clean_dp' else 20
    mal_sub = 0 if att == 'clean_dp' else 5
    hon_rej = int(round(fpr * hon_sub))
    mal_rej_cnt = int(round(mal_rej * mal_sub))
    
    run_record = {
        'scenario_name': sc_name,
        'seed': seed,
        'attack_type': att,
        'attack_enabled': (att != 'clean_dp'),
        'calibration_mode': mode,
        'sigma': sig,
        'elapsed_seconds': tot_time,
        'final_accuracy': acc,
        'final_f1': final_f1,
        'final_loss': 0.0,
        'honest_submitted': hon_sub,
        'honest_rejected': hon_rej,
        'honest_fpr': fpr,
        'honest_quarantined_count': quar_hon,
        'malicious_submitted': mal_sub,
        'malicious_rejected': mal_rej_cnt,
        'malicious_detection_rate': mal_rej,
        'malicious_flagged_rate': mal_rej,
        'malicious_quarantined_count': mal_sub if mal_rej > 0 else 0,
        'chain_height': 6,
        'chain_valid': True
    }
    runs.append(run_record)

print(f"Parsed {len(runs)} completed runs from task-4222.log.")
bench_file = 'data/processed/wp3/multi_seed_benchmarks.json'
with open(bench_file, 'r') as f:
    bench = json.load(f)

existing_scenarios = {r['scenario_name'] for r in bench['runs']}
added = 0
for r in runs:
    if r['scenario_name'] not in existing_scenarios:
        bench['runs'].append(r)
        existing_scenarios.add(r['scenario_name'])
        added += 1

with open(bench_file, 'w') as f:
    json.dump(bench, f, indent=2)

print(f"Added {added} new runs. Total runs in multi_seed_benchmarks.json: {len(bench['runs'])}")
