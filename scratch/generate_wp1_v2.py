import json
import numpy as np
import scipy.stats as stats

# Load original summary
with open("data/processed/stage2e/wp1/benchmark_summary.json") as f:
    orig = json.load(f)

v2 = {
    "metadata": {
        "version": "2.0 (Audited & Methodologically Corrected)",
        "milestone": "Stage 2E.3.1",
        "description": "Multi-seed statistical baseline evaluation with family-wise Holm-Bonferroni correction and qualified statistical power interpretation.",
        "seeds": orig["seeds"],
        "num_seeds": orig["num_seeds"],
        "num_rounds": orig["num_rounds"],
        "sampling_unit": "Seed-level experimental run (n=5). Individual test set evaluations (N=22,544) serve as measurement observations, not independent replications.",
        "methodological_corrections": [
            "Applied Holm-Bonferroni step-down correction across the family of 7 comparisons vs FedAvg.",
            "Replaced 'Ceiling' and 'Floor' language with 'Reference'.",
            "Replaced 'Zero-Degradation Guarantee' with 'No Measurable Clean-Performance Degradation Observed Across Five Pilot Seeds'.",
            "Replaced post-hoc 'Fully Powered' claims with prospective sample-size planning ranges.",
            "Qualified Coordinate Median degradation mechanism as not yet conclusively isolated."
        ]
    },
    "models": {
        "centralized_ids": {
            "label": "Centralized IDS Reference",
            "per_seed_accuracy": orig["models"]["centralized_ids"]["per_seed_accuracy"],
            "per_seed_f1_macro": orig["models"]["centralized_ids"]["per_seed_f1_macro"],
            "accuracy_stats": orig["models"]["centralized_ids"]["accuracy_stats"],
            "f1_macro_stats": orig["models"]["centralized_ids"]["f1_macro_stats"]
        },
        "local_silos": {
            "label": "Local-Silo Reference",
            "per_seed_accuracy": orig["models"]["local_silos"]["per_seed_accuracy"],
            "per_seed_f1_macro": orig["models"]["local_silos"]["per_seed_f1_macro"],
            "accuracy_stats": orig["models"]["local_silos"]["accuracy_stats"],
            "f1_macro_stats": orig["models"]["local_silos"]["f1_macro_stats"]
        },
        "fedavg": {
            "label": "Standard FedAvg Baseline",
            "per_seed_accuracy": orig["models"]["fedavg"]["per_seed_accuracy"],
            "per_seed_f1_macro": orig["models"]["fedavg"]["per_seed_f1_macro"],
            "accuracy_stats": orig["models"]["fedavg"]["accuracy_stats"],
            "f1_macro_stats": orig["models"]["fedavg"]["f1_macro_stats"]
        },
        "trust_weighted": {
            "label": "Trust-Weighted FedAvg (Stage 2D Architecture)",
            "observation_note": "No Measurable Clean-Performance Degradation Observed Across Five Pilot Seeds",
            "per_seed_accuracy": orig["models"]["trust_weighted"]["per_seed_accuracy"],
            "per_seed_f1_macro": orig["models"]["trust_weighted"]["per_seed_f1_macro"],
            "accuracy_stats": orig["models"]["trust_weighted"]["accuracy_stats"],
            "f1_macro_stats": orig["models"]["trust_weighted"]["f1_macro_stats"]
        },
        "foolsgold": {
            "label": "FoolsGold (Standalone Sybil Defense)",
            "per_seed_accuracy": orig["models"]["foolsgold"]["per_seed_accuracy"],
            "per_seed_f1_macro": orig["models"]["foolsgold"]["per_seed_f1_macro"],
            "accuracy_stats": orig["models"]["foolsgold"]["accuracy_stats"],
            "f1_macro_stats": orig["models"]["foolsgold"]["f1_macro_stats"]
        },
        "trimmed_mean": {
            "label": "Trimmed Mean (beta=0.2)",
            "per_seed_accuracy": orig["models"]["trimmed_mean"]["per_seed_accuracy"],
            "per_seed_f1_macro": orig["models"]["trimmed_mean"]["per_seed_f1_macro"],
            "accuracy_stats": orig["models"]["trimmed_mean"]["accuracy_stats"],
            "f1_macro_stats": orig["models"]["trimmed_mean"]["f1_macro_stats"]
        },
        "multikrum_f1": {
            "label": "Multi-Krum (f=1, m=1)",
            "per_seed_accuracy": orig["models"]["multikrum_f1"]["per_seed_accuracy"],
            "per_seed_f1_macro": orig["models"]["multikrum_f1"]["per_seed_f1_macro"],
            "accuracy_stats": orig["models"]["multikrum_f1"]["accuracy_stats"],
            "f1_macro_stats": orig["models"]["multikrum_f1"]["f1_macro_stats"]
        },
        "coordinate_median": {
            "label": "Coordinate Median",
            "qualification_note": "Coordinate Median showed substantial clean-performance degradation under the tested NSL-KDD partitioning and configuration. The mechanism behind this degradation has not yet been conclusively isolated.",
            "per_seed_accuracy": orig["models"]["coordinate_median"]["per_seed_accuracy"],
            "per_seed_f1_macro": orig["models"]["coordinate_median"]["per_seed_f1_macro"],
            "accuracy_stats": orig["models"]["coordinate_median"]["accuracy_stats"],
            "f1_macro_stats": orig["models"]["coordinate_median"]["f1_macro_stats"]
        }
    },
    "multiple_comparisons_family_vs_fedavg": {
        "family_size_m": 7,
        "family_alpha": 0.05,
        "procedure": "Holm-Bonferroni Step-Down Procedure",
        "comparisons": {}
    },
    "prospective_power_planning": {
        "status": "Pilot study effect-size estimates. Confirmatory sample-size planning requires prospective effect-size assumptions.",
        "planning_assumptions": {
            "alpha": 0.05,
            "target_power": 0.80,
            "two_sided": True
        },
        "plausible_sample_size_scenarios": {
            "large_effect_dz_1_0": {"assumed_dz": 1.0, "required_N": 8},
            "medium_large_effect_dz_0_8": {"assumed_dz": 0.8, "required_N": 13},
            "medium_effect_dz_0_5": {"assumed_dz": 0.5, "required_N": 32},
            "small_medium_effect_dz_0_4": {"assumed_dz": 0.4, "required_N": 50}
        }
    }
}

# Compute Holm-Bonferroni
fedavg_accs = np.array(orig["models"]["fedavg"]["per_seed_accuracy"])
comp_keys = [
    "centralized_ids", "coordinate_median", "local_silos",
    "foolsgold", "multikrum_f1", "trimmed_mean", "trust_weighted"
]

raw_comps = []
for k in comp_keys:
    m_accs = np.array(orig["models"][k]["per_seed_accuracy"])
    diffs = m_accs - fedavg_accs
    mean_d = float(np.mean(diffs))
    std_d = float(np.std(diffs, ddof=1))
    
    if std_d < 1e-12:
        t_stat, p_val, dz = 0.0, 1.0, 0.0
    else:
        res = stats.ttest_rel(m_accs, fedavg_accs)
        t_stat, p_val, dz = float(res.statistic), float(res.pvalue), float(mean_d / std_d)
        
    raw_comps.append({
        "model_key": k,
        "mean_difference": mean_d,
        "std_difference": std_d,
        "t_stat": t_stat,
        "df": 4,
        "raw_p_value": p_val,
        "cohens_d_z": dz
    })

# Sort ascending by raw p-value
raw_comps.sort(key=lambda x: x["raw_p_value"])
m_total = len(raw_comps)
cum_max_p = 0.0
step_down_stopped = False

for rank, item in enumerate(raw_comps, start=1):
    threshold = 0.05 / (m_total - rank + 1)
    unclipped_adj = (m_total - rank + 1) * item["raw_p_value"]
    cum_max_p = max(cum_max_p, unclipped_adj)
    holm_adj_p = min(1.0, cum_max_p)
    raw_sig = item["raw_p_value"] < 0.05
    
    if not step_down_stopped:
        if item["raw_p_value"] <= threshold:
            holm_sig = True
        else:
            holm_sig = False
            step_down_stopped = True
    else:
        holm_sig = False
        
    v2["multiple_comparisons_family_vs_fedavg"]["comparisons"][item["model_key"]] = {
        "rank": rank,
        "mean_difference": item["mean_difference"],
        "std_difference": item["std_difference"],
        "t_statistic": item["t_stat"],
        "degrees_of_freedom": 4,
        "cohens_d_z": item["cohens_d_z"],
        "raw_p_value": item["raw_p_value"],
        "holm_threshold": threshold,
        "holm_adjusted_p_value": holm_adj_p,
        "statistically_significant_raw": raw_sig,
        "statistically_significant_holm": holm_sig,
        "interpretation": (
            "Statistically significant under unadjusted test, but not significant after Holm-Bonferroni FWER control."
            if raw_sig and not holm_sig else
            "Not statistically significant before or after Holm-Bonferroni correction."
            if not raw_sig else
            "Statistically significant after Holm-Bonferroni correction."
        )
    }

with open("data/processed/stage2e/wp1/benchmark_summary_v2.json", "w") as f:
    json.dump(v2, f, indent=2)

print("Generated benchmark_summary_v2.json successfully.")
