import json
import numpy as np
import scipy.stats as stats

with open("data/processed/stage2e/wp1/benchmark_summary.json") as f:
    summary = json.load(f)

seeds = summary["seeds"]
models = summary["models"]
fedavg_accs = np.array(models["fedavg"]["per_seed_accuracy"])

comparisons = [
    "centralized_ids",
    "local_silos",
    "trust_weighted",
    "foolsgold",
    "trimmed_mean",
    "multikrum_f1",
    "coordinate_median"
]

results = []
for m in comparisons:
    m_accs = np.array(models[m]["per_seed_accuracy"])
    diffs = m_accs - fedavg_accs
    mean_d = float(np.mean(diffs))
    std_d = float(np.std(diffs, ddof=1))
    n = len(diffs)
    
    if std_d < 1e-12:
        t_stat, p_val, dz = 0.0, 1.0, 0.0
    else:
        res = stats.ttest_rel(m_accs, fedavg_accs)
        t_stat = float(res.statistic)
        p_val = float(res.pvalue)
        dz = float(mean_d / std_d)
    
    results.append({
        "model": m,
        "mean_diff": mean_d,
        "std_diff": std_d,
        "t_stat": t_stat,
        "p_val": p_val,
        "cohens_dz": dz
    })

# Sort by p-value ascending for Holm-Bonferroni
sorted_res = sorted(results, key=lambda x: x["p_val"])
m_hypotheses = len(sorted_res)
alpha = 0.05

print(f"=== HOLM-BONFERRONI MULTIPLE COMPARISON CORRECTION (m={m_hypotheses}, alpha={alpha}) ===\n")
header = f"{'Rank (i)':<10}{'Model':<20}{'Mean Diff':<12}{'Cohen dz':<10}{'Raw p':<12}{'Holm Threshold':<16}{'Holm Adj p':<12}{'Raw Sig':<10}{'Holm Sig'}"
print(header)
print("-" * len(header))

cum_max_p = 0.0
step_down_stopped = False
for i, item in enumerate(sorted_res, start=1):
    threshold = alpha / (m_hypotheses - i + 1)
    unclipped_adj_p = (m_hypotheses - i + 1) * item["p_val"]
    cum_max_p = max(cum_max_p, unclipped_adj_p)
    holm_adj_p = min(1.0, cum_max_p)
    raw_sig = item["p_val"] < alpha
    
    if not step_down_stopped:
        if item["p_val"] <= threshold:
            holm_sig = True
        else:
            holm_sig = False
            step_down_stopped = True
    else:
        holm_sig = False
        
    item["rank"] = i
    item["threshold"] = threshold
    item["holm_adj_p"] = holm_adj_p
    item["raw_sig"] = raw_sig
    item["holm_sig"] = holm_sig
    print(f"{i:<10}{item['model']:<20}{item['mean_diff']:>+10.4f}  {item['cohens_dz']:>+8.4f}  {item['p_val']:>10.6f}  {threshold:>14.6f}  {holm_adj_p:>10.6f}  {str(raw_sig):<10}{str(holm_sig)}")

print("\n=== PER-SEED OBSERVATIONS ===")
for m in ["fedavg"] + comparisons:
    accs = [round(x * 100, 2) for x in models[m]["per_seed_accuracy"]]
    f1s = [round(x, 4) for x in models[m]["per_seed_f1_macro"]]
    stats_a = models[m]["accuracy_stats"]
    print(f"{m:<20}: Acc = {accs} -> Mean={stats_a['mean']*100:.2f}%, Std={stats_a['std']*100:.2f}%, CI95={stats_a['ci_95_str']}")
