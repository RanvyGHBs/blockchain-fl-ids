import json
import numpy as np

with open("data/processed/stage2e/wp1/per_seed_runs.json") as f:
    runs = json.load(f)

seeds = [42, 101, 2024, 777, 999]
print("=== COORDINATE MEDIAN VS FEDAVG TRAJECTORY PER SEED ===")
for i, s in enumerate(seeds):
    fed = runs["fedavg"][i]
    med = runs["coordinate_median"][i]
    trm = runs["trimmed_mean"][i]
    krm = runs["multikrum_f1"][i]
    print(f"Seed {s:4d} | FedAvg: {fed['accuracy']*100:6.2f}% (F1: {fed['f1_macro']:.4f}) | Median: {med['accuracy']*100:6.2f}% (F1: {med['f1_macro']:.4f}) | Trimmed: {trm['accuracy']*100:6.2f}% | MultiKrum: {krm['accuracy']*100:6.2f}%")
