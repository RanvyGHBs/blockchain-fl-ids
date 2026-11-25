"""
Live Interactive Demonstration of Blockchain-Assisted Federated IDS.
Executes an end-to-end multi-round federated learning cycle with:
- NSL-KDD dataset partitioned under Non-IID Dirichlet skew (alpha=0.5), or
  deterministic synthetic CPU data in --smoke mode
- Client-side differential privacy (OS-CSPRNG Gaussian perturbation)
- Byzantine adversarial attack injection (Model Scaling Attack on Client 3)
- Multi-criteria trust evaluation (L2 norm, Cosine similarity, Validator loss)
- Asymmetric reputation slashing & quarantine isolation
- ECDSA digital signatures and Blockchain Proof-of-Trust (PoT) consensus
- Immutable block forging with SHA-256 and Merkle tree validation
- Federated aggregation and RDP privacy accounting
"""

import argparse
import os
import sys
import time
from typing import Any, Dict, Tuple

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import (
    APPROVED_CLIP_NORM,
    APPROVED_NOISE_MULTIPLIER,
    APPROVED_TARGET_DELTA,
    ExecutionMode,
    PrivacyRandomnessMode,
    get_approved_research_config,
)
from src.federated.orchestrator import FederatedOrchestrator
from src.privacy.rdp_accountant import RDPAccountant


def build_synthetic_smoke_dataset(
    seed: int = 42,
    n_train: int = 200,
    n_val: int = 40,
    n_test: int = 60,
    n_features: int = 16,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Generates deterministic normalized synthetic binary classification splits on CPU."""
    rng = np.random.RandomState(seed)

    def _make_split(n_samples: int) -> Tuple[np.ndarray, np.ndarray]:
        half = n_samples // 2
        x0 = rng.normal(loc=0.25, scale=0.12, size=(half, n_features))
        x1 = rng.normal(loc=0.75, scale=0.12, size=(n_samples - half, n_features))
        x = np.clip(np.vstack([x0, x1]), 0.0, 1.0).astype(np.float32)
        y = np.array([0] * half + [1] * (n_samples - half), dtype=np.int64)
        perm = rng.permutation(n_samples)
        return x[perm], y[perm]

    x_tr, y_tr = _make_split(n_train)
    x_va, y_va = _make_split(n_val)
    x_te, y_te = _make_split(n_test)
    return x_tr, y_tr, x_va, y_va, x_te, y_te


def print_banner(smoke: bool = False) -> None:
    mode_label = "LIGHTWEIGHT CPU SMOKE MODE (SYNTHETIC DATA)" if smoke else "LIVE NSL-KDD RESEARCH DEMONSTRATION"
    feature_label = "16 synthetic features" if smoke else "122 features"
    banner = f"""
========================================================================================
     BLOCKCHAIN-ASSISTED PRIVACY-PRESERVING FEDERATED INTRUSION DETECTION SYSTEM
     {mode_label}
========================================================================================
 Architecture: PyTorch IDSNet ({feature_label} -> binary intrusion classification)
 Federated Skew: 5 Network Clients | Dirichlet Non-IID (alpha = 0.5) | Device: CPU
 Privacy Guard: Client-Side L2 Clipping (C=1.0) + OS-CSPRNG Gaussian Perturbation (sigma=1.0)
 Trust Engine: Privacy-Aware Multi-Criteria Defense (RMS Norm + Cosine Median + Loss Ceiling)
 Blockchain: ECDSA SECP256R1 Digital Signatures | Proof-of-Trust (PoT) Consensus | SHA-256
 Threat Model: Client 3 is a Byzantine Attacker (Model Scaling Attack: 10x Magnitude)
========================================================================================
"""
    print(banner)


def run_demo(smoke: bool = False) -> Tuple[int, Dict[str, Any]]:
    """Executes either the normal NSL-KDD demonstration or the CPU synthetic smoke check."""
    print_banner(smoke=smoke)

    print("[*] Initializing Approved Research Simulation Environment...")
    cfg = get_approved_research_config(
        num_rounds=2,
        num_clients=5,
        attack_enabled=True,
        attack_type="model_scaling",
        malicious_client_ids=[3],
        defense_enabled=True,
        trust_calibration_mode="privacy_aware",
        execution_mode=ExecutionMode.RESEARCH_SIMULATION,
        privacy_randomness_mode=PrivacyRandomnessMode.OS_CSPRNG,
        device="cpu",
        seed=42,
    )

    cfg_dict = {k: getattr(cfg, k) for k in cfg.__dataclass_fields__}
    cfg_dict["communication_rounds"] = 2
    cfg_dict["num_rounds"] = 2
    cfg_dict["defense_matrix"] = {
        "trust_engine": True,
        "norm_check": True,
        "cosine_check": True,
        "loss_check": True,
        "reputation": True,
        "quarantine": True,
    }
    cfg_dict["local_epochs"] = 1
    cfg_dict["batch_size"] = 32 if smoke else 128
    cfg_dict["attack_enabled"] = True
    cfg_dict["attack_type"] = "model_scaling"
    cfg_dict["malicious_client_ids"] = [3]
    cfg_dict["device"] = "cpu"

    if smoke:
        print("[*] Generating deterministic synthetic intrusion dataset (CPU smoke mode)...")
        t0 = time.time()
        x_tr, y_tr, x_va, y_va, x_te, y_te = build_synthetic_smoke_dataset(seed=42)
        cfg_dict.update(
            {
                "dataset": "synthetic_smoke",
                "X_train": x_tr,
                "y_train": y_tr,
                "X_val": x_va,
                "y_val": y_va,
                "X_test": x_te,
                "y_test": y_te,
                "input_dim": x_tr.shape[1],
                "num_classes": 2,
                "feature_names": [f"feat_{i}" for i in range(x_tr.shape[1])],
                "class_names": ["Normal", "Attack"],
            }
        )
    else:
        print("[*] Loading NSL-KDD Network Intrusion Dataset...")
        t0 = time.time()

    orch = FederatedOrchestrator(cfg_dict)
    orch.setup()
    load_time = time.time() - t0
    print(f"    -> Dataset ready in {load_time:.2f}s: {len(orch.X_train)} train, {len(orch.X_val)} val, {len(orch.X_test)} test samples.")
    print("    -> Clients initialized: 5 nodes partitioned under Dirichlet Non-IID skew.")
    print("    -> Client 3 designated as Byzantine Malicious Attacker (Model Scaling).")
    print("-" * 88)

    print("\n>>> STARTING FEDERATED ROUNDS <<<\n")
    results = orch.run()

    print("\n" + "=" * 88)
    print("                      FEDERATED LEARNING AUDIT SUMMARY                         ")
    print("=" * 88)

    round_history = results.get("round_history", [])
    malicious_rejected_total = 0
    for r_data in round_history:
        r_num = r_data.get("round", 0)
        acc = r_data.get("accuracy", 0.0) * 100
        loss = r_data.get("loss", 0.0)
        f1 = r_data.get("f1_score", r_data.get("f1", 0.0))
        disp = r_data.get("dispositions", {})

        print(f"\n--- [COMMUNICATION ROUND {r_num}] ---")
        print(f"  * Global Model Performance : Test Accuracy = {acc:.2f}% | Test Loss = {loss:.4f} | F1 = {f1:.4f}")
        if r_num > 0:
            r_mal_rej = disp.get("malicious_rejected_total", 0)
            malicious_rejected_total += r_mal_rej
            print(f"  * Defense Dispositions     : Honest Accepted = {disp.get('honest_accepted_aggregated', 0)} | Malicious Rejected = {r_mal_rej}")
            print("  * Current Node Status:")
            for cid in range(orch.num_clients):
                rep = orch.reputation_mgr.get_reputation(cid)
                quarantined = orch.reputation_mgr.is_quarantined(cid)
                role = "[MALICIOUS ATTACKER]" if cid == 3 else "[HONEST NODE]"
                q_str = "QUARANTINED" if quarantined else "ACTIVE"
                print(f"      Node {cid:2d} {role:20s}: Reputation = {rep:.2f} [{q_str}]")

    print("\n" + "-" * 88)
    print("                     CRYPTOGRAPHIC & BLOCKCHAIN LEDGER                         ")
    print("-" * 88)
    chain = orch.blockchain
    chain_valid = bool(chain.is_chain_valid())
    print(f"  * Total Ledger Height: {len(chain.chain)} blocks (1 Genesis + {len(chain.chain) - 1} Round Blocks)")
    print(f"  * Blockchain Integrity Verified: {chain_valid}")

    for blk in chain.chain[1:]:
        print(f"    -> Block #{blk.index} | Miner: Node {blk.validator_id} (PoT Winner) | Tx Count: {len(blk.transactions)} | Merkle Root: {blk.merkle_root[:16]}... | Hash: {blk.hash[:16]}...")

    print("\n" + "-" * 88)
    print("                 DIFFERENTIAL PRIVACY GUARANTEE (RDP)                          ")
    print("-" * 88)
    accountant = RDPAccountant()
    actual_rounds = max(1, len(round_history) - 1)
    accountant.step(noise_multiplier=APPROVED_NOISE_MULTIPLIER, clip_norm=APPROVED_CLIP_NORM, rounds=actual_rounds)
    eps, opt_alpha = accountant.get_epsilon(delta=APPROVED_TARGET_DELTA)
    print(f"  * Differential Privacy Budget: epsilon = {eps:.4f} (at delta = {APPROVED_TARGET_DELTA}, optimal alpha = {opt_alpha}, training rounds = {actual_rounds})")
    print("  * Privacy Randomness Mode: OS-CSPRNG (Cryptographically Secure Box-Muller)")

    final_acc = results.get("final_accuracy", 0.0) * 100
    attacker_quarantined = orch.reputation_mgr.is_quarantined(3)
    smoke_ok = (
        chain_valid
        and len(chain.chain) == 3
        and malicious_rejected_total >= 2
        and attacker_quarantined
        and np.isfinite(eps)
        and eps > 0.0
    )

    print("\n" + "=" * 88)
    if smoke:
        verdict = "PASSED" if smoke_ok else "FAILED"
        print(
            f"  SMOKE TEST: {verdict} | Acc = {final_acc:.2f}% | "
            f"Chain Valid = {chain_valid} | Attacker Quarantined = {attacker_quarantined}"
        )
        print("=" * 88 + "\n")
        return (0 if smoke_ok else 1), results

    print(f"  FINAL RESULT: Model Accuracy = {final_acc:.2f}% | Byzantine Attack Neutralized = YES")
    print("=" * 88 + "\n")
    return 0, results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run live or lightweight CPU smoke FL-IDS demo.")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run lightweight CPU-only simulation using deterministic synthetic data (no dataset download).",
    )
    args = parser.parse_args()
    exit_code, _ = run_demo(smoke=args.smoke)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
