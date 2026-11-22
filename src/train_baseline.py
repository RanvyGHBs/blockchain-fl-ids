"""
Stage 1 Centralized Baseline Training & Non-IID Partitioning Verification.
Trains a centralized IDS classifier on NSL-KDD to establish benchmark performance,
evaluates precision/recall/F1, and verifies Dirichlet client partitioning.
"""

import os
import json
import time
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

from src.data.nsl_kdd import NSLKDDLoader
from src.data.partitioner import FederatedPartitioner
from src.models.ids_net import IDSNet


def evaluate_model(model: nn.Module, data_loader: DataLoader, criterion: nn.Module, device: str = "cpu"):
    model.eval()
    total_loss = 0.0
    all_preds = []
    all_targets = []

    with torch.no_grad():
        for X_batch, y_batch in data_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            total_loss += loss.item() * len(y_batch)
            preds = torch.argmax(outputs, dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_targets.extend(y_batch.cpu().numpy())

    avg_loss = total_loss / len(data_loader.dataset)
    all_preds = np.array(all_preds)
    all_targets = np.array(all_targets)

    acc = accuracy_score(all_targets, all_preds)
    prec = precision_score(all_targets, all_preds, average="weighted", zero_division=0)
    rec = recall_score(all_targets, all_preds, average="weighted", zero_division=0)
    f1 = f1_score(all_targets, all_preds, average="weighted", zero_division=0)
    cm = confusion_matrix(all_targets, all_preds).tolist()

    return {
        "loss": float(avg_loss),
        "accuracy": float(acc),
        "precision": float(prec),
        "recall": float(rec),
        "f1_score": float(f1),
        "confusion_matrix": cm
    }


def main():
    print("=" * 70)
    print("STAGE 1: DATA PIPELINE, NON-IID PARTITIONING & BASELINE MODEL")
    print("=" * 70)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[Device] Using compute device: {device}")

    # 1. Load and preprocess dataset
    print("\n--- 1. Loading & Preprocessing NSL-KDD Dataset ---")
    loader = NSLKDDLoader(raw_dir="data/raw", processed_dir="data/processed", binary=True, seed=42)
    X_train, y_train, X_test, y_test = loader.preprocess(force=False)
    input_dim = loader.get_feature_dimension()
    num_classes = 2

    print(f"X_train shape: {X_train.shape}, y_train class counts: {np.bincount(y_train)}")
    print(f"X_test shape:  {X_test.shape}, y_test class counts:  {np.bincount(y_test)}")
    print(f"Feature Dimension: {input_dim} normalized input features")

    # 2. Test Non-IID Dirichlet Partitioner
    print("\n--- 2. Verifying Non-IID Dirichlet Client Partitioner (5 Clients, alpha=0.5) ---")
    partitioner = FederatedPartitioner(num_clients=5, non_iid=True, alpha=0.5, seed=42)
    client_splits = partitioner.partition(X_train, y_train)
    stats = partitioner.get_distribution_stats(client_splits)

    for cid, counts in stats["client_class_counts"].items():
        total = stats["client_sample_counts"][cid]
        norm_pct = (counts.get(0, 0) / total) * 100 if total > 0 else 0
        att_pct = (counts.get(1, 0) / total) * 100 if total > 0 else 0
        print(f"  Client {cid}: {total} samples | Normal: {counts.get(0,0)} ({norm_pct:.1f}%) | Attack: {counts.get(1,0)} ({att_pct:.1f}%)")

    # 3. Build & Train Centralized Baseline IDS Classifier
    print("\n--- 3. Training Centralized PyTorch IDS Classifier Baseline ---")
    train_dataset = TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train))
    test_dataset = TensorDataset(torch.from_numpy(X_test), torch.from_numpy(y_test))

    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=128, shuffle=False)

    model = IDSNet(input_dim=input_dim, num_classes=num_classes).to(device)
    print(f"Model Architecture:\n{model}")
    print(f"Total Trainable Parameters: {model.get_parameter_count():,}")

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    epochs = 5
    start_time = time.time()
    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * len(y_batch)

        epoch_loss = running_loss / len(train_dataset)
        val_metrics = evaluate_model(model, test_loader, criterion, device)
        print(f"Epoch [{epoch}/{epochs}] | Train Loss: {epoch_loss:.4f} | Test Acc: {val_metrics['accuracy']*100:.2f}% | F1: {val_metrics['f1_score']:.4f}")

    total_training_time = time.time() - start_time
    final_metrics = evaluate_model(model, test_loader, criterion, device)
    final_metrics["training_time_sec"] = float(total_training_time)
    final_metrics["weights_hash"] = model.get_weights_hash()

    print("\n" + "=" * 70)
    print("STAGE 1 FINAL EVALUATION METRICS:")
    print(f"  Test Accuracy: {final_metrics['accuracy'] * 100:.2f}%")
    print(f"  Precision:     {final_metrics['precision']:.4f}")
    print(f"  Recall:        {final_metrics['recall']:.4f}")
    print(f"  F1-Score:      {final_metrics['f1_score']:.4f}")
    print(f"  Confusion Matrix: {final_metrics['confusion_matrix']}")
    print(f"  Model Hash:    {final_metrics['weights_hash'][:16]}...")
    print(f"  Training Time: {final_metrics['training_time_sec']:.2f} seconds")
    print("=" * 70)

    # Save metrics and weights
    os.makedirs("data/processed", exist_ok=True)
    metrics_path = "data/processed/baseline_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(final_metrics, f, indent=4)
    torch.save(model.state_dict(), "data/processed/baseline_model.pth")
    print(f"[Success] Stage 1 baseline artifacts saved to {metrics_path} and data/processed/baseline_model.pth")


if __name__ == "__main__":
    main()
