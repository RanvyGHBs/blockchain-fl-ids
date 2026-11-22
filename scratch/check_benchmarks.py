import json

with open("data/processed/stage2d/multi_attack_benchmarks_v2.json", "r") as f:
    data = json.load(f)

print(f"{'Scenario':<42} | {'Acc (%)':<8} | {'Cum MURR':<10} | {'Cum PUAA':<10} | {'ASR (%)':<8} | {'Dispositions (M_sub/M_rej/M_acc/M_prev)'}")
print("-" * 115)
for k, s in data["scenarios"].items():
    acc = f"{s['final_accuracy']*100:.2f}"
    murr = f"{s['cumulative_murr']*100:.1f}%" if s.get('cumulative_murr') is not None else "None"
    puaa = f"{s['cumulative_puaa']*100:.1f}%" if s.get('cumulative_puaa') is not None else "None"
    asr = f"{s.get('final_asr', 0.0)*100:.1f}"
    m_disp = s.get("cumulative_dispositions", {}).get("malicious", {})
    disp_str = f"{m_disp.get('submitted', 0)} / {m_disp.get('rejected_total', 0)} / {m_disp.get('accepted_aggregated', 0)} / {m_disp.get('prevented_quarantine', 0)}"
    print(f"{k:<42} | {acc:<8} | {murr:<10} | {puaa:<10} | {asr:<8} | {disp_str}")
