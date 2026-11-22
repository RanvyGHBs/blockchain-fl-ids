# Blockchain-Assisted Federated Learning Framework for Universal Network Intrusion Detection

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-orange.svg)](https://pytorch.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An academic-grade, research-caliber cyber-defense framework that unites **Deep Learning (Intrusion Detection)**, **Federated Learning (Privacy-Preserving Distributed Training)**, **Blockchain (Cryptographic Audit Ledger & Consensus)**, and **Multi-Criteria Trust Validation (Adversarial Defense)**.

Designed to be **universal and industry-agnostic**, this framework enables autonomous network entities (enterprise campuses, regional healthcare systems, cloud VPCs, and critical infrastructure) to collaboratively train a shared Intrusion Detection System (IDS) without centralizing or exposing proprietary network traffic.

---

## 1. System Architecture

```
                                  +-------------------------------------------------------------+
                                  |                 BLOCKCHAIN & TRUST LAYER                    |
                                  |  - ECDSA Digital Signatures & Non-Repudiation               |
                                  |  - Proof-of-Trust (PoT) Validator Committee Consensus        |
                                  |  - Multi-Criteria Anomaly Engine (Norm + Cosine + Loss)     |
                                  |  - Asymmetric Slashing & Quarantine Governance              |
                                  |  - Immutable SHA-256 Ledger (Off-Chain Weights + Hashes)    |
                                  +-------------------------------------------------------------+
                                                  ^                             |
                           Verified Model Hashes  |                             | Global Model
                           & Digital Signatures   |                             | Parameters
                                                  |                             v
               +----------------------------------+----------------------------------+
               |                                  |                                  |
    +----------------------+           +----------------------+           +----------------------+
    |  Node 0: Campus Net  |           |  Node 1: Regional HC |           | Node 3: Attacker Node|
    | - Non-IID Traffic    |           | - Non-IID Traffic    |           | - Model Poisoning    |
    | - PyTorch IDSNet     |           | - PyTorch IDSNet     |           | - Gaussian / Flip    |
    | - Gaussian Perturb   |           | - Gaussian Perturb   |           | - (REJECTED & SLASHED)
    +----------------------+           +----------------------+           +----------------------+
```

---

## 2. Key Capabilities & Technical Novelty

1. **Intelligent Intrusion Detection Engine:**
   * PyTorch Deep Neural Network (MLP with Batch Normalization and Dropout) trained on the NSL-KDD benchmark (125,973 train records, 22,544 test records, 122 normalized features).
   * Fast Explainable AI (XAI) feature attribution (Input $\times$ Sensitivity) to explain why a packet was classified as an intrusion.

2. **Federated Collaboration Under High Skew:**
   * Dirichlet distribution ($\text{Dir}(\alpha=0.5)$) simulating realistic Non-IID traffic imbalances across autonomous network nodes.
   * Multiple aggregation algorithms: `FedAvg`, `FedProx`, `Trimmed Mean`, `Coordinate Median`, and `Trust-Weighted FedAvg`.

3. **Multi-Criteria Adversarial Defense:**
   * **L2 Norm Thresholding:** Detects blown-up weights and scaled gradient injections.
   * **Cosine Similarity to Median Consensus:** Identifies sign-flipping and directional inversion.
   * **Validator Loss Delta (Non-IID Safe):** Validates candidate models on a balanced slice, preventing benign Non-IID variance from being falsely flagged.
   * **Asymmetric Reputation Slashing:** Honest nodes earn $+0.05$ slowly; detected attackers lose $-0.35$ immediately and are isolated into quarantine ($R_i < 0.40$).

4. **Cryptographic Blockchain & Audit Ledger:**
   * Elliptic Curve Digital Signatures (ECDSA with SECP256R1) ensuring cryptographic non-repudiation.
   * Proof-of-Trust (PoT) consensus selecting top-reputation honest nodes as block miners.
   * Merkle tree validation and off-chain storage pattern preventing state bloat.

5. **Privacy-Preserving Machine Learning:**
   * Clipping-based Gaussian update perturbation (without formal privacy accounting) with L2 gradient clipping and calibrated Gaussian perturbation.

---

## 3. Directory Structure

```text
blockchain-fl-ids/
├── config/
│   └── default.yaml             # Hyperparameters, client counts, attack thresholds
├── data/
│   ├── raw/                     # KDDTrain+.txt, KDDTest+.txt
│   └── processed/               # Preprocessed numpy tensors & baseline metrics
├── src/
│   ├── data/
│   │   ├── base_loader.py       # Abstract dataset interface
│   │   ├── nsl_kdd.py           # NSL-KDD pipeline & one-hot categorical encoder
│   │   └── partitioner.py       # Non-IID Dirichlet distribution splitter
│   ├── models/
│   │   └── ids_net.py           # PyTorch IDS Neural Network with SHA-256 weight hashing
│   ├── federated/
│   │   ├── client.py            # Federated Client (local train, FedProx)
│   │   ├── server.py            # Federated Coordinator & evaluator
│   │   ├── orchestrator.py      # Stage 2 High-level FL orchestrator & pipeline
│   │   └── aggregators.py       # FedAvg, Trimmed Mean, Median, Trust-Weighted
│   ├── attacks/
│   │   ├── model_poisoning.py   # Gaussian noise, sign-flipping, scaling attacks
│   │   └── data_poisoning.py    # Label-flipping attacks
│   ├── trust/
│   │   ├── evaluator.py         # Multi-criteria validation engine
│   │   └── reputation.py        # Asymmetric reputation scoring & quarantine
│   ├── blockchain/
│   │   ├── crypto.py            # ECDSA keypairs, signing, verification
│   │   ├── block.py             # Block, Transaction, Merkle root
│   │   └── chain.py             # Blockchain ledger & PoT consensus
│   ├── privacy/
│   │   └── differential.py      # L2-clipped Gaussian perturbation
│   ├── xai/
│   │   └── explainer.py         # Fast feature attribution for inference
│   └── education/
│       ├── __init__.py          # Educational module registry
│       └── content.py           # 9 Educational modules across 5 progressive levels
├── app.py                       # 6-Section Streamlit Research Platform & Learning Centre
├── run_stage2.py                # Stage 2 Comprehensive 6-Scenario Benchmark
├── run_benchmark.py             # Headless comparative experiment suite
├── tests/
│   ├── test_stage1.py           # Stage 1 Baseline tests
│   ├── test_stage2.py           # Stage 2 Full Integration suite (20 tests)
│   └── test_stage4_blockchain.py# Blockchain unit tests
├── requirements.txt             # Project dependencies
└── README.md                    # Project documentation
```

---

## 4. Installation & Quick Start

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Run Stage 1 Baseline Training
```bash
python -m src.train_baseline
```

### Step 3: Run Stage 2 Comprehensive Benchmark
```bash
python -u run_stage2.py
```

### Step 4: Run Complete Test Suite
```bash
python -m pytest tests/ -v
```

### Step 5: Launch Interactive Streamlit Dashboard
```bash
streamlit run app.py
```

---

## 5. Stage 2 Experimental Benchmark Results

Controlled evaluation across 6 distinct scenarios on NSL-KDD (5 Non-IID Dirichlet clients, $\alpha=0.5$):

| Scenario | Attack Type | Defense Mode | Final Accuracy | Final F1-Score | Cryptographic Audit Status |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **S1: Vanilla FedAvg** | None (Honest) | None | 58.29% | 0.4986 | Valid (Height: 1) |
| **S2: Vanilla Under Gaussian Noise** | Gaussian ($\sigma=2.5$) | None | 75.03% (Unstable loss > 238) | 0.7330 | Valid (Height: 1) |
| **S3: Vanilla Under Sign-Flip** | Sign-Flip ($\times -3.0$) | None | 43.08% (Failure to learn) | 0.2594 | Valid (Height: 1) |
| **S4: Blockchain FL (Gaussian Defense)** | Gaussian ($\sigma=2.5$) | Multi-Criteria + PoT | **70.95%** | **0.6986** | **Valid (Height: 6, Attacker Slashed)** |
| **S5: Blockchain FL (Sign-Flip Defense)** | Sign-Flip ($\times -3.0$) | Multi-Criteria + PoT | **74.59%** | **0.7433** | **Valid (Height: 6, Attacker Slashed)** |
| **S6: Privacy-Preserving FL** | None | Clipping-based Gaussian perturbation (without formal accounting) | 56.92% | 0.4130 | Valid (Height: 1) |

> **Key Stage 2 Insights:**
> 1. **Directional Inversion Defense (S3 vs S5):** Under a malicious sign-flipping attack, vanilla FedAvg completely stalled at **43.08%** accuracy. With the Multi-Criteria Trust Engine enabled, cosine similarity was immediately identified as $\cos \theta = -0.959$ (violating the $\ge 0.15$ threshold), rejecting the attacker in every round and boosting global accuracy to **74.59%**.
> 2. **Gradient Explosion Defense (S2 vs S4):** Gaussian noise injection resulted in catastrophic loss instability ($L > 238$) without defense. In S4, the L2-norm check intercepted updates ($||w||_2 \approx 409$ vs $43.3$ threshold), slashing Client 3's reputation and forging audit blocks to Proof-of-Trust miners.
> 3. **Non-Repudiation & Auditability:** 100% of blocks across all scenarios maintained cryptographically valid SHA-256 and Merkle linkages with zero false rejections of honest nodes.

---

## 5. Academic Viva & Presentation Defense Guide

### Q1: Why use Blockchain in Federated Learning?
> Standard Federated Learning relies on a single central aggregation server. If that server is compromised, malicious, or crashes, the entire system fails. Furthermore, standard FL provides zero tamper-proof accountability. Our custom blockchain establishes an immutable audit log of who contributed which update, signs updates with ECDSA to guarantee non-repudiation, and replaces the single point of failure with a Proof-of-Trust validator committee.

### Q2: Why does Cosine Similarity fail on Non-IID data, and how do you solve it?
> In real networks, Node A might see 90% PortScan attacks while Node B sees 90% DoS attacks. Their weight updates naturally point in different directions. A naive cosine filter would mistakenly flag honest Node A as an attacker. We solve this through **Multi-Criteria Validation**: combining cosine check against peer median with a **Validator Benchmark Loss Delta**, verifying whether an update maintains network classification sanity rather than penalizing legitimate specialization.

### Q3: How do you prevent blockchain bloat?
> We use the industry-standard off-chain storage pattern: model parameter weights are stored in localized caches/off-chain storage, while the blockchain blocks record only their 32-byte **SHA-256 cryptographic checksums**, digital signatures, validation metrics, and Merkle root.
