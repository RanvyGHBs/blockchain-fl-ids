"""
Stage 2: Federated Learning Orchestrator.
High-level pipeline integrating FL Server, Trust Engine, Blockchain, Reputation,
Differential Privacy, ECDSA signing, and XAI into a single cohesive training loop.

This orchestrator produces rich per-round metrics, adversarial detection logs,
blockchain audit trails, and DP accounting records—suitable for academic reporting.
"""

import time
import json
import os
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import torch

from src.data.nsl_kdd import NSLKDDLoader
from src.data.custom_loader import CustomDatasetLoader
from src.data.partitioner import FederatedPartitioner
from src.models.ids_net import IDSNet
from src.federated.client import FederatedClient
from src.federated.server import FederatedServer
from src.federated.aggregators import (
    aggregate_fedavg, aggregate_trimmed_mean, aggregate_median, aggregate_trust_weighted
)
from src.attacks.model_poisoning import (
    apply_gaussian_noise_attack, apply_sign_flipping_attack, apply_model_scaling_attack
)
from src.attacks.data_poisoning import apply_label_flipping_attack
from src.trust.evaluator import MultiCriteriaTrustEngine
from src.trust.reputation import ReputationManager
from src.blockchain.crypto import CryptoManager
from src.blockchain.block import Transaction
from src.blockchain.chain import Blockchain
from src.privacy.differential import LocalDifferentialPrivacy
from src.xai.explainer import FastFeatureExplainer


# ---------------------------------------------------------------------------
# Attack registry
# ---------------------------------------------------------------------------
ATTACK_REGISTRY = {
    "gaussian_noise": lambda w, seed: apply_gaussian_noise_attack(w, std=2.5, seed=seed),
    "sign_flip":      lambda w, seed: apply_sign_flipping_attack(w, scale=-3.0),
    "model_scaling":  lambda w, seed: apply_model_scaling_attack(w, scale_factor=10.0),
    "label_flip":     None,  # Handled at data-loading time
}


class FederatedOrchestrator:
    """
    Coordinates a complete multi-round Federated Learning experiment with:
    - Non-IID Dirichlet data partitioning
    - Local training (standard or FedProx)
    - Optional Differential Privacy
    - Multi-Criteria Trust validation (norm + cosine + loss)
    - ECDSA digital signatures per update
    - Blockchain block mining (Proof-of-Trust consensus)
    - Asymmetric reputation slashing & quarantine
    - Pluggable aggregation algorithms
    - Per-round evaluation metrics
    - Adversarial attack injection

    Usage::

        orch = FederatedOrchestrator(config)
        results = orch.run()
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.scenario_name = config.get("scenario_name", "unnamed_scenario")
        self.seed = config.get("seed", 42)
        self.device = config.get("device", "cpu")

        # Federated hyperparams
        self.num_clients = config.get("num_clients", 5)
        self.num_rounds = config.get("num_rounds", 5)
        self.local_epochs = config.get("local_epochs", 1)
        self.batch_size = config.get("batch_size", 64)
        self.lr = config.get("lr", 0.002)
        self.fedprox_mu = config.get("fedprox_mu", 0.0)
        self.aggregation = config.get("aggregation_algorithm", "fedavg")

        # Attack configuration
        self.attack_enabled = config.get("attack_enabled", False)
        self.malicious_client_ids: List[int] = config.get("malicious_client_ids", [3])
        self.attack_type = config.get("attack_type", "gaussian_noise")
        self.label_flip_source = config.get("label_flip_source", 1)
        self.label_flip_target = config.get("label_flip_target", 0)

        # Defense / blockchain
        self.defense_enabled = config.get("defense_enabled", False)
        self.dp_enabled = config.get("dp_enabled", False)
        self.dp_clip_norm = config.get("dp_clip_norm", 1.0)
        self.dp_noise_multiplier = config.get("dp_noise_multiplier", 0.01)

        # Track routing and dataset loading
        self.track = config.get("track", "Track A")
        self.dataset_name = config.get("dataset", "nsl_kdd")
        self.loader = config.get("loader")

        # Data arrays
        self.X_train: Optional[np.ndarray] = config.get("X_train")
        self.y_train: Optional[np.ndarray] = config.get("y_train")
        self.X_val: Optional[np.ndarray]   = config.get("X_val")
        self.y_val: Optional[np.ndarray]   = config.get("y_val")
        self.X_test: Optional[np.ndarray]  = config.get("X_test")
        self.y_test: Optional[np.ndarray]  = config.get("y_test")
        self.feature_names: List[str]      = config.get("feature_names", [])
        self.class_names: List[str]        = config.get("class_names", [])

        # Auto-route dataset loading if data arrays were not directly passed
        if self.X_train is None:
            self._load_dataset_from_track_or_loader()

        assert self.X_train is not None, "X_train must be provided in config or loadable via track/loader."
        assert self.X_test is not None, "X_test must be provided in config or loadable via track/loader."

        self.input_dim = config.get("input_dim", self.X_train.shape[1])
        if "num_classes" in config and config["num_classes"] is not None:
            self.num_classes = int(config["num_classes"])
        else:
            all_y = [y for y in (self.y_train, self.y_val, self.y_test) if y is not None]
            if all_y:
                self.num_classes = max(2, int(len(np.unique(np.concatenate(all_y)))))
            else:
                self.num_classes = 2

        # Trust engine thresholds
        trust_cfg = config.get("trust_config", {})
        self.norm_threshold_factor = trust_cfg.get("norm_threshold_factor", 2.5)
        self.cosine_threshold      = trust_cfg.get("cosine_threshold", 0.15)
        self.loss_increase_threshold = trust_cfg.get("loss_increase_threshold", 1.5)

        # Internal components (initialized in setup())
        self.clients:     List[FederatedClient]    = []
        self.client_keys: Dict[int, Tuple[str,str]] = {}
        self.server:      Optional[FederatedServer] = None
        self.trust_engine: Optional[MultiCriteriaTrustEngine] = None
        self.reputation_mgr: Optional[ReputationManager]      = None
        self.blockchain:    Optional[Blockchain]               = None
        self.dp_engine:     Optional[LocalDifferentialPrivacy] = None

        # Per-round telemetry
        self.round_logs: List[Dict[str, Any]] = []
        self.dp_accounting: List[Dict[str, Any]] = []
        self.attack_log: List[Dict[str, Any]] = []

    def _load_dataset_from_track_or_loader(self):
        """Loads and preprocesses datasets with strict 3-way isolation based on track/loader configuration."""
        if self.loader is not None:
            res = self.loader.preprocess_isolated()
            if len(res) == 6:
                self.X_train, self.y_train, self.X_val, self.y_val, self.X_test, self.y_test = res
            elif len(res) == 4:
                self.X_train, self.y_train, self.X_test, self.y_test = res
            self.feature_names = getattr(self.loader, "feature_columns", self.feature_names)
            if hasattr(self.loader, "class_names") and self.loader.class_names:
                self.class_names = self.loader.class_names
            if hasattr(self.loader, "num_classes") and self.loader.num_classes:
                self.num_classes = self.loader.num_classes
        elif self.track == "Track B" or self.dataset_name in CustomDatasetLoader.PRESETS or self.dataset_name in ("breast_cancer", "iris", "wine"):
            loader = CustomDatasetLoader(source=self.dataset_name, seed=self.seed)
            self.X_train, self.y_train, self.X_val, self.y_val, self.X_test, self.y_test = loader.preprocess_isolated()
            self.feature_names = loader.feature_columns
            self.class_names = loader.class_names
            self.num_classes = loader.num_classes
        else:
            # Default: Track A (NSL-KDD)
            loader = NSLKDDLoader(binary=True, seed=self.seed)
            self.X_train, self.y_train, self.X_val, self.y_val, self.X_test, self.y_test = loader.preprocess_isolated()
            self.feature_names = loader.feature_columns
            self.class_names = loader.get_class_names()
            self.num_classes = 2

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_clients(self):
        partitioner = FederatedPartitioner(
            num_clients=self.num_clients, non_iid=True, alpha=0.5, seed=self.seed
        )
        splits = partitioner.partition(self.X_train, self.y_train)

        self.clients = []
        self.client_keys = {}

        for cid in range(self.num_clients):
            Xc, yc = splits[cid]

            # Data poisoning (label flip) applied at data-loading time
            if (self.attack_enabled
                    and cid in self.malicious_client_ids
                    and self.attack_type == "label_flip"):
                src_cls = self.label_flip_source
                tgt_cls = self.label_flip_target
                # Safeguard for Non-IID slices: if target source_class not in yc, pick first available class
                if src_cls not in yc and len(yc) > 0:
                    src_cls = int(yc[0])
                    tgt_cls = (src_cls + 1) % self.num_classes
                yc = apply_label_flipping_attack(
                    yc, source_class=src_cls, target_class=tgt_cls, flip_ratio=1.0, seed=self.seed
                )
                print(f"  [Attack Setup] Label-Flip injected on Client {cid}: {src_cls} -> {tgt_cls}")

            client = FederatedClient(
                client_id=cid,
                client_name=f"Network-Node-{cid}",
                X_local=Xc,
                y_local=yc,
                input_dim=self.input_dim,
                num_classes=self.num_classes,
                device=self.device,
                seed=self.seed + cid
            )
            self.clients.append(client)

            priv_k, pub_k = CryptoManager.generate_keypair()
            self.client_keys[cid] = (priv_k, pub_k)

    def setup(self):
        """Initialises all components for a fresh experiment run."""
        self._setup_clients()

        self.server = FederatedServer(
            input_dim=self.input_dim, num_classes=self.num_classes,
            aggregation_algorithm=self.aggregation, device=self.device, seed=self.seed
        )

        self.trust_engine = MultiCriteriaTrustEngine(
            input_dim=self.input_dim, num_classes=self.num_classes,
            norm_threshold_factor=self.norm_threshold_factor,
            cosine_threshold=self.cosine_threshold,
            loss_increase_threshold=self.loss_increase_threshold,
            device=self.device
        )

        self.reputation_mgr = ReputationManager(
            client_ids=list(range(self.num_clients))
        )

        self.blockchain = Blockchain(committee_size=3)

        if self.dp_enabled:
            self.dp_engine = LocalDifferentialPrivacy(
                clip_norm=self.dp_clip_norm,
                noise_multiplier=self.dp_noise_multiplier,
                seed=self.seed
            )

    # ------------------------------------------------------------------
    # Round execution
    # ------------------------------------------------------------------

    def _run_round(self, r: int, val_data: Tuple[np.ndarray, np.ndarray]) -> Dict[str, Any]:
        current_global_weights = self.server.get_global_weights()
        round_t0 = time.time()

        client_raw_weights: Dict[int, np.ndarray] = {}
        client_signatures:  Dict[int, str]        = {}
        sample_counts:      Dict[int, int]        = {}
        dp_meta_round:      Dict[int, Dict]       = {}

        # ---- Step A: Local Training ----
        for client in self.clients:
            if self.reputation_mgr.is_quarantined(client.client_id):
                continue

            client.set_global_weights(current_global_weights)
            client.local_train(
                epochs=self.local_epochs, batch_size=self.batch_size,
                lr=self.lr, fedprox_mu=self.fedprox_mu,
                global_weights=current_global_weights
            )
            weights = client.get_local_weights()

            # Apply DP noise if enabled
            if self.dp_enabled and self.dp_engine is not None:
                weights, dp_meta = self.dp_engine.privatize(weights)
                dp_meta_round[client.client_id] = dp_meta

            # Apply model poisoning (non-label-flip attacks)
            if (self.attack_enabled
                    and client.client_id in self.malicious_client_ids
                    and self.attack_type != "label_flip"):
                attack_fn = ATTACK_REGISTRY.get(self.attack_type)
                if attack_fn:
                    weights = attack_fn(weights, self.seed + r)
                    self.attack_log.append({
                        "round": r, "client_id": client.client_id,
                        "attack_type": self.attack_type
                    })

            # ECDSA digital signature on weight hash
            w_hash = CryptoManager.sha256_hash(weights.tobytes().hex())
            sig = CryptoManager.sign_message(self.client_keys[client.client_id][0], w_hash)

            client_raw_weights[client.client_id] = weights
            client_signatures[client.client_id]  = sig
            sample_counts[client.client_id]       = client.num_samples

        # ---- Step B: Trust Validation & Blockchain Recording ----
        accepted_weights: List[np.ndarray] = []
        accepted_counts:  List[int]        = []
        accepted_reps:    List[float]      = []
        rejected_cids:    List[int]        = []
        validation_reports: Dict[int, Dict] = {}

        if self.defense_enabled and len(client_raw_weights) > 1:
            validation_reports = self.trust_engine.evaluate_updates(
                client_raw_weights, current_global_weights, val_data
            )
            self.reputation_mgr.update_reputation(validation_reports)

            for cid, report in validation_reports.items():
                is_valid = report["is_valid"]
                status_str = "ACCEPTED" if is_valid else "REJECTED"
                rep_history = self.reputation_mgr.reputation_history[cid]
                rep_before = rep_history[-2] if len(rep_history) >= 2 else 1.0
                rep_after  = self.reputation_mgr.reputations[cid]

                tx = Transaction(
                    client_id=cid,
                    round_num=r,
                    weights_hash=CryptoManager.sha256_hash(
                        client_raw_weights[cid].tobytes().hex()
                    ),
                    signature=client_signatures[cid],
                    validation_metrics=report,
                    status=status_str,
                    reputation_before=rep_before,
                    reputation_after=rep_after
                )
                self.blockchain.add_transaction(tx)

                if is_valid:
                    accepted_weights.append(client_raw_weights[cid])
                    accepted_counts.append(sample_counts[cid])
                    accepted_reps.append(rep_after)
                else:
                    rejected_cids.append(cid)
                    print(
                        f"  [🚨 Trust Alert] Round {r}: Client {cid} REJECTED "
                        f"| Reason: {report['reason'][:80]}"
                    )

            # Proof-of-Trust block mining
            validator_id = self.blockchain.select_validator(
                self.reputation_mgr.get_all_reputations()
            )
            new_block_hash = CryptoManager.sha256_hash(
                self.server.get_global_weights_hash() + f"_round_{r}"
            )
            self.blockchain.forge_block(
                global_model_hash=new_block_hash, validator_id=validator_id
            )
        else:
            # No defense: accept all updates naively
            for cid, w in client_raw_weights.items():
                accepted_weights.append(w)
                accepted_counts.append(sample_counts[cid])
                accepted_reps.append(1.0)

        # ---- Step C: Aggregation ----
        if len(accepted_weights) > 0:
            if self.aggregation == "fedavg":
                new_weights = aggregate_fedavg(accepted_weights, accepted_counts)
            elif self.aggregation == "trimmed_mean":
                new_weights = aggregate_trimmed_mean(accepted_weights, beta=0.2)
            elif self.aggregation == "median":
                new_weights = aggregate_median(accepted_weights)
            elif self.aggregation == "trust_weighted":
                new_weights = aggregate_trust_weighted(
                    accepted_weights, accepted_counts, accepted_reps
                )
            else:
                new_weights = aggregate_fedavg(accepted_weights, accepted_counts)
            self.server.set_global_weights(new_weights)

        # ---- Step D: Global Evaluation ----
        eval_bs = min(self.batch_size, len(self.X_test)) if len(self.X_test) > 0 else 32
        eval_metrics = self.server.evaluate(self.X_test, self.y_test, batch_size=eval_bs)
        round_duration = time.time() - round_t0

        # Build reputation snapshot
        rep_snapshot = {
            cid: self.reputation_mgr.get_reputation(cid)
            for cid in range(self.num_clients)
        }

        round_record = {
            "round": r,
            "accuracy": eval_metrics["accuracy"],
            "precision": eval_metrics["precision"],
            "recall": eval_metrics["recall"],
            "f1_score": eval_metrics["f1_score"],
            "precision_macro": eval_metrics.get("precision_macro", eval_metrics["precision"]),
            "recall_macro": eval_metrics.get("recall_macro", eval_metrics["recall"]),
            "f1_score_macro": eval_metrics.get("f1_score_macro", eval_metrics["f1_score"]),
            "loss": eval_metrics["loss"],
            "num_active_clients": len(accepted_weights),
            "rejected_client_ids": rejected_cids,
            "num_rejected": len(rejected_cids),
            "reputation_snapshot": rep_snapshot,
            "global_weights_hash": self.server.get_global_weights_hash(),
            "blockchain_height": len(self.blockchain.chain),
            "duration_sec": round_duration,
        }

        if dp_meta_round:
            self.dp_accounting.append({"round": r, "dp_meta": dp_meta_round})

        print(
            f"  Round {r:>2}/{self.num_rounds} | "
            f"Acc: {eval_metrics['accuracy']*100:.2f}% | "
            f"F1: {eval_metrics['f1_score']:.4f} | "
            f"Loss: {eval_metrics['loss']:.4f} | "
            f"Rejected: {len(rejected_cids)} | "
            f"Chain Height: {len(self.blockchain.chain)} | "
            f"Time: {round_duration:.2f}s"
        )

        return round_record

    # ------------------------------------------------------------------
    # Main run loop
    # ------------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        """Execute all federated rounds and return a comprehensive results dict."""
        print(f"\n{'='*70}")
        print(f"SCENARIO: {self.scenario_name}")
        print(f"{'='*70}")
        print(
            f"  Track: {self.track} | Dataset: {self.dataset_name} | "
            f"Features (D): {self.input_dim} | Classes (C): {self.num_classes} | "
            f"Clients: {self.num_clients} | Rounds: {self.num_rounds} | "
            f"Aggregation: {self.aggregation.upper()} | "
            f"Attack: {'ON (' + self.attack_type + ')' if self.attack_enabled else 'OFF'} | "
            f"Defense: {'ON' if self.defense_enabled else 'OFF'} | "
            f"DP: {'ON' if self.dp_enabled else 'OFF'}"
        )

        self.setup()

        # Strict 3-Way Isolation: determine trust validation benchmark
        if self.X_val is not None and self.y_val is not None:
            val_data = (self.X_val, self.y_val)
        elif self.config.get("val_data") is not None:
            val_data = self.config["val_data"]
        else:
            # Fallback: slice from X_train without leaking held-out test data
            val_size = min(1000, max(1, len(self.X_train) // 10))
            val_indices = np.random.RandomState(self.seed).choice(
                len(self.X_train), size=val_size, replace=False
            )
            val_data = (self.X_train[val_indices], self.y_train[val_indices])

        # Round 0 — initial evaluation (untrained global model)
        eval_bs = min(self.batch_size, len(self.X_test)) if len(self.X_test) > 0 else 32
        init_eval = self.server.evaluate(self.X_test, self.y_test, batch_size=eval_bs)
        self.round_logs = [{
            "round": 0,
            "accuracy": init_eval["accuracy"],
            "precision": init_eval["precision"],
            "recall":    init_eval["recall"],
            "f1_score":  init_eval["f1_score"],
            "precision_macro": init_eval.get("precision_macro", init_eval["precision"]),
            "recall_macro":    init_eval.get("recall_macro", init_eval["recall"]),
            "f1_score_macro":  init_eval.get("f1_score_macro", init_eval["f1_score"]),
            "loss":      init_eval["loss"],
            "num_active_clients": 0,
            "rejected_client_ids": [],
            "num_rejected": 0,
            "reputation_snapshot": {
                cid: self.reputation_mgr.get_reputation(cid)
                for cid in range(self.num_clients)
            },
            "global_weights_hash": self.server.get_global_weights_hash(),
            "blockchain_height": 1,  # genesis block
            "duration_sec": 0.0,
        }]
        print(
            f"  Round  0/{self.num_rounds} | "
            f"Acc: {init_eval['accuracy']*100:.2f}% | "
            f"F1: {init_eval['f1_score']:.4f} | "
            f"Loss: {init_eval['loss']:.4f} | (baseline)"
        )

        total_start = time.time()
        for r in range(1, self.num_rounds + 1):
            record = self._run_round(r, val_data)
            self.round_logs.append(record)

        total_time = time.time() - total_start
        final = self.round_logs[-1]

        # XAI demonstration on a single test sample
        xai_demo = None
        if self.feature_names and len(self.X_test) > 0:
            try:
                explainer = FastFeatureExplainer(
                    self.server.global_model,
                    feature_names=self.feature_names,
                    device=self.device,
                    class_names=self.class_names
                )
                sample_idx = 42 % len(self.X_test)
                xai_demo = explainer.explain_flow(self.X_test[sample_idx], top_k=min(5, self.input_dim))
                xai_demo["sample_idx"] = sample_idx
                xai_demo["true_label"] = int(self.y_test[sample_idx])
            except Exception as e:
                xai_demo = {"error": str(e)}

        # Build final results
        results = {
            "scenario_name": self.scenario_name,
            "track": self.track,
            "dataset": self.dataset_name,
            "input_dim": self.input_dim,
            "num_classes": self.num_classes,
            "config": {
                k: v for k, v in self.config.items()
                if k not in ("X_train", "y_train", "X_val", "y_val", "X_test", "y_test", "feature_names", "class_names", "val_data", "loader")
            },
            "final_accuracy":        final["accuracy"],
            "final_f1_score":        final["f1_score"],
            "final_precision":       final["precision"],
            "final_recall":          final["recall"],
            "final_f1_score_macro":  final.get("f1_score_macro", final["f1_score"]),
            "final_precision_macro": final.get("precision_macro", final["precision"]),
            "final_recall_macro":    final.get("recall_macro", final["recall"]),
            "final_loss":            final["loss"],
            "total_time_sec":        total_time,
            "round_history":         self.round_logs,
            "attack_log":            self.attack_log,
            "dp_accounting":         self.dp_accounting,
            "blockchain_summary":    self.blockchain.get_audit_summary(),
            "reputation_summary":    self.reputation_mgr.get_status_summary(),
            "chain_valid":           self.blockchain.is_chain_valid(),
            "xai_demo":              xai_demo,
        }

        print(f"\n  ✅ Scenario Complete | "
              f"Final Acc: {final['accuracy']*100:.2f}% | "
              f"F1: {final['f1_score']:.4f} | "
              f"Total Time: {total_time:.1f}s | "
              f"Chain Valid: {results['chain_valid']}")

        return results

    def evaluate(self, X_eval: Optional[np.ndarray] = None, y_eval: Optional[np.ndarray] = None,
                 batch_size: Optional[int] = None, average: str = "weighted") -> Dict[str, Any]:
        """
        Evaluates the current global model on provided or held-out test data.
        Returns loss, accuracy, precision, recall, f1_score (both weighted and macro), and confusion matrix.
        """
        if self.server is None:
            raise RuntimeError("Orchestrator server must be initialized via setup() or run() before evaluation.")
        X = self.X_test if X_eval is None else X_eval
        y = self.y_test if y_eval is None else y_eval
        assert X is not None and y is not None, "Evaluation data (X, y) must be available."
        bs = min(self.batch_size, len(X)) if batch_size is None else batch_size
        return self.server.evaluate(X, y, batch_size=bs, average=average)
