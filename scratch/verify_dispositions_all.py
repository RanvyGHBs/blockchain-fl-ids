import json

with open("data/processed/stage2d/multi_attack_benchmarks_v2.json", "r") as f:
    data = json.load(f)

print("=" * 90)
print(f"{'Scenario':<42} | {'Round':<5} | {'M_sub':<5} | {'M_rej':<5} | {'M_acc':<5} | {'M_prev':<6} | {'Status'}")
print("=" * 90)

all_passed = True
for key, sc in data["scenarios"].items():
    # Check rounds
    for r in sc["round_history"][1:]:
        disp = r["dispositions"]
        m_sub = disp["malicious_submitted"]
        m_rej = disp["malicious_rejected_total"]
        m_acc = disp["malicious_accepted_aggregated"]
        m_prev = disp["malicious_prevented_quarantine"]
        
        h_sub = disp["honest_submitted"]
        h_rej = disp["honest_rejected_total"]
        h_acc = disp["honest_accepted_aggregated"]
        h_prev = disp["honest_prevented_quarantine"]
        
        m_ok = (m_sub == m_rej + m_acc)
        h_ok = (h_sub == h_rej + h_acc)
        
        status = "OK" if (m_ok and h_ok) else "CONSERVATION_FAIL"
        if not (m_ok and h_ok):
            all_passed = False
        print(f"{key:<42} | R{r['round']:<4} | {m_sub:<5} | {m_rej:<5} | {m_acc:<5} | {m_prev:<6} | {status}")

    # Check cumulative
    cum = sc["cumulative_dispositions"]
    c_m_sub = cum["malicious"]["submitted"]
    c_m_rej = cum["malicious"]["rejected_total"]
    c_m_acc = cum["malicious"]["accepted_aggregated"]
    c_m_prev = cum["malicious"]["prevented_quarantine"]
    c_m_ok = (c_m_sub == c_m_rej + c_m_acc)
    
    # Check consistency of murr and puaa
    if c_m_sub > 0:
        c_murr = sc["cumulative_murr"]
        c_puaa = sc["cumulative_puaa"]
        if abs((c_murr + c_puaa) - 1.0) > 1e-6:
            all_passed = False
            print(f"ERROR: PUAA + MURR != 1.0 in {key} ({c_murr} + {c_puaa})")
    else:
        if sc["cumulative_murr"] is not None or sc["cumulative_puaa"] is not None:
            all_passed = False
            print(f"ERROR: Zero submissions but MURR/PUAA is not None in {key}")

print("-" * 90)
print(f"Overall Conservation Verification: {'PASSED (100% Conserved)' if all_passed else 'FAILED'}")
