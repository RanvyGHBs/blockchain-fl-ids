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
from src.attacks.targeted_poisoning import (
    apply_targeted_label_flipping_attack, compute_attack_success_rate, compute_clean_accuracy
)
from src.attacks.sybil_coalition import (
    generate_sybil_coalition_updates, evaluate_median_distortion
)
from src.attacks.adaptive_byzantine import (
    generate_adaptive_byzantine_update, verify_evasion_criteria
)
from src.federated.analytics import (
    compute_mudr, compute_murr, compute_fpr, compute_puaa, compute_stage2d_defense_metrics
)
from src.trust.evaluator import MultiCriteriaTrustEngine
from src.trust.reputation import ReputationManager
from src.blockchain.crypto import CryptoManager
from src.blockchain.block import Transaction
from src.blockchain.chain import Blockchain
from src.privacy.differential import LocalDifferentialPrivacy
from src.privacy.mechanism import ClientLevelDPMechanism
from src.privacy.rdp_accountant import RDPAccountant
from src.xai.explainer import FastFeatureExplainer


# ---------------------------------------------------------------------------
# Attack registry
# ---------------------------------------------------------------------------
ATTACK_REGISTRY = {
    "gaussian_noise": lambda w, seed: apply_gaussian_noise_attack(w, std=2.5, seed=seed),
    "sign_flip":      lambda w, seed: apply_sign_flipping_attack(w, scale=-3.0),
    "model_scaling":  lambda w, seed: apply_model_scaling_attack(w, scale_factor=10.0),
    "label_flip":     None,  # Handled at data-loading time
    "targeted_label_flip": None,  # Handled at data-loading time
    "sybil_coalition": None,      # Handled during round execution
    "adaptive_byzantine": None,   # Handled during round execution
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
        self.malicious_client_ids: List[int] = config.get("malicious_client_ids", [3]) if self.attack_enabled else []
        self.attack_type = config.get("attack_type", "gaussian_noise")
        self.label_flip_source = config.get("label_flip_source", 1)
        self.label_flip_target = config.get("label_flip_target", 0)
        self.label_flip_ratio = float(config.get("label_flip_ratio", 1.0))
        self.sybil_intensity = float(config.get("sybil_intensity", 2.0))
        self.adaptive_stealth_factor = float(config.get("adaptive_stealth_factor", 0.8))
        self.adaptive_loss_headroom = float(config.get("adaptive_loss_headroom", 0.5))

        # Defense / blockchain / Dynamic Defense Matrix
        self.defense_enabled = config.get("defense_enabled", False)
        defense_matrix = config.get("defense_matrix", {})
        self.enable_trust_engine = bool(defense_matrix.get("trust_engine", self.defense_enabled))
        self.enable_norm_check = bool(defense_matrix.get("norm_check", True))
        self.enable_cosine_check = bool(defense_matrix.get("cosine_check", True))
        self.enable_loss_check = bool(defense_matrix.get("loss_check", True))
        self.enable_reputation = bool(defense_matrix.get("reputation", self.defense_enabled))
        self.enable_quarantine = bool(defense_matrix.get("quarantine", self.defense_enabled))
        self.enable_signature_verify = bool(defense_matrix.get("signature_verify", True))
        self.enable_blockchain = bool(defense_matrix.get("blockchain", self.defense_enabled))

        self.dp_enabled = config.get("dp_enabled", False)
        self.dp_clip_norm = float(config.get("dp_clip_norm", 1.0))
        self.dp_noise_multiplier = float(config.get("dp_noise_multiplier", 0.01))
        self.dp_target_delta = float(config.get("dp_target_delta", 1e-5))
        self.clean_baseline_acc: Optional[float] = None

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

        # Establish deterministic class-to-index mapping from training targets
        self._normalize_target_labels()

        # Strict 3-Way Isolation: derive fallback validation benchmark from X_train
        # BEFORE client partitioning, ensuring validation and client training sets are disjoint.
        self._val_data_prepared = False
        self.val_data: Optional[Tuple[np.ndarray, np.ndarray]] = None
        self._prepare_validation_data()

        self.input_dim = config.get("input_dim", self.X_train.shape[1])

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
        self.dp_engine:      Optional[LocalDifferentialPrivacy] = None
        self.dp_mechanism:   Optional[ClientLevelDPMechanism]  = None
        self.rdp_accountant: Optional[RDPAccountant]           = None

        # Per-round telemetry
        self.round_logs: List[Dict[str, Any]] = []
        self.dp_accounting: List[Dict[str, Any]] = []
        self.attack_log: List[Dict[str, Any]] = []
        self.cumulative_accounting: Dict[str, Dict[str, int]] = {
            "malicious": {
                "submitted": 0,
                "rejected_trust": 0,
                "rejected_crypto": 0,
                "rejected_total": 0,
                "flagged_trust": 0,
                "accepted_aggregated": 0,
                "prevented_quarantine": 0,
            },
            "honest": {
                "submitted": 0,
                "rejected_trust": 0,
                "rejected_crypto": 0,
                "rejected_total": 0,
                "flagged_trust": 0,
                "accepted_aggregated": 0,
                "prevented_quarantine": 0,
            }
        }

    @staticmethod
    def _map_label_array(labels: np.ndarray, mapping: Dict[Any, int], split_name: str) -> np.ndarray:
        unseen = [val for val in labels if val not in mapping]
        if unseen:
            unique_unseen = sorted(list(set(unseen)), key=lambda x: (str(type(x)), x))
            clean_unseen = [x.item() if hasattr(x, "item") else x for x in unique_unseen]
            clean_vocab = [x.item() if hasattr(x, "item") else x for x in mapping.keys()]
            raise ValueError(
                f"Unseen label(s) {clean_unseen} encountered in {split_name} set. "
                f"Expected labels from training vocabulary: {clean_vocab}"
            )
        return np.array([mapping[val] for val in labels], dtype=np.int64)

    def _normalize_target_labels(self):
        """
        Establishes one consistent class-to-index mapping (0..C-1) from the training label vocabulary.
        Transforms training, validation, and test targets using this single mapping.
        Rejects unseen validation or test labels with a descriptive ValueError.
        Preserves human-readable class names for reporting.
        """
        unique_train = np.unique(self.y_train)
        is_already_contiguous = (
            np.issubdtype(self.y_train.dtype, np.integer) and
            set(unique_train) == set(range(len(unique_train)))
        )

        if is_already_contiguous:
            mapping = {int(c): int(c) for c in range(len(unique_train))}
            if not self.class_names:
                self.class_names = [str(c) for c in range(len(unique_train))]
        else:
            sorted_classes = sorted(list(unique_train), key=lambda x: (str(type(x)), x))
            mapping = {cls: idx for idx, cls in enumerate(sorted_classes)}
            self.class_names = [str(c) for c in sorted_classes]
            self.y_train = self._map_label_array(self.y_train, mapping, "training")

        if self.y_val is not None:
            self.y_val = self._map_label_array(self.y_val, mapping, "validation")

        if self.y_test is not None:
            self.y_test = self._map_label_array(self.y_test, mapping, "test")

        if "num_classes" in self.config and self.config["num_classes"] is not None:
            self.num_classes = max(int(self.config["num_classes"]), len(mapping))
        else:
            self.num_classes = max(2, len(mapping))

    def _prepare_validation_data(self):
        """
        Prepares validation benchmark ensuring strict 3-way research isolation.
        When raw arrays are passed without X_val, extracts a dedicated validation slice
        from X_train and removes those samples from the client-training pool BEFORE
        partitioning.
        """
        if self._val_data_prepared:
            return

        if self.X_val is not None and self.y_val is not None:
            self.val_data = (self.X_val, self.y_val)
        elif self.config.get("val_data") is not None:
            self.val_data = self.config["val_data"]
            self.X_val, self.y_val = self.val_data
        else:
            # Fallback: slice validation benchmark from X_train
            n_train = len(self.X_train)
            if n_train > 1:
                desired_val = min(1000, max(1, n_train // 10))
                val_size = min(desired_val, n_train - 1)
                rng = np.random.RandomState(self.seed)
                all_idx = np.arange(n_train)
                val_idx = rng.choice(all_idx, size=val_size, replace=False)
                pool_idx = np.setdiff1d(all_idx, val_idx)

                self.X_val = self.X_train[val_idx]
                self.y_val = self.y_train[val_idx]
                self.X_train = self.X_train[pool_idx]
                self.y_train = self.y_train[pool_idx]
                self.val_data = (self.X_val, self.y_val)
            else:
                # N == 1 edge case: keep in training pool and mirror reference for validation
                self.X_val = self.X_train.copy()
                self.y_val = self.y_train.copy()
                self.val_data = (self.X_val, self.y_val)

        self._val_data_prepared = True

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
        # Ensure validation benchmark is isolated before partitioning client-training pool
        self._prepare_validation_data()

        # Clear previous setup-phase attack logs to prevent duplicates on repeated setup()
        self.attack_log = [e for e in self.attack_log if e.get("phase") != "setup"]

        partitioner = FederatedPartitioner(
            num_clients=self.num_clients, non_iid=True, alpha=0.5, seed=self.seed
        )
        splits = partitioner.partition(self.X_train, self.y_train)

        self.clients = []
        self.client_keys = {}

        for cid in range(self.num_clients):
            Xc, yc = splits[cid]

            # Data poisoning (label flip / targeted label flip) applied at data-loading time.
            # Permanently poisons the client's local training dataset once during client setup (Phase: "setup", Round: 0).
            # It takes effect in every subsequent local training epoch on that client.
            if (self.attack_enabled
                    and cid in self.malicious_client_ids
                    and self.attack_type in ("label_flip", "targeted_label_flip")):
                src_cls = self.label_flip_source
                tgt_cls = self.label_flip_target
                # Safeguard for Non-IID slices: if target source_class not in yc, pick first available class
                if src_cls not in yc and len(yc) > 0:
                    src_cls = int(yc[0])
                    tgt_cls = (src_cls + 1) % self.num_classes

                yc, flipped_count = apply_targeted_label_flipping_attack(
                    yc, source_class=src_cls, target_class=tgt_cls, flip_ratio=self.label_flip_ratio, seed=self.seed
                )
                print(f"  [Attack Setup] Label-Flip injected on Client {cid}: {src_cls} -> {tgt_cls} ({flipped_count} samples, ratio={self.label_flip_ratio})")

                # Telemetry logging: record only if samples were actually modified
                if flipped_count > 0:
                    self.attack_log.append({
                        "round": 0,
                        "phase": "setup",
                        "client_id": cid,
                        "attack_type": self.attack_type,
                        "source_class": int(src_cls),
                        "target_class": int(tgt_cls),
                        "flipped_samples": int(flipped_count),
                        "flip_ratio": float(self.label_flip_ratio)
                    })

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
        import random
        random.seed(self.seed)
        np.random.seed(self.seed)
        torch.manual_seed(self.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(self.seed)

        self._setup_clients()

        self.cumulative_accounting = {
            "malicious": {
                "submitted": 0,
                "rejected_trust": 0,
                "rejected_crypto": 0,
                "rejected_total": 0,
                "flagged_trust": 0,
                "accepted_aggregated": 0,
                "prevented_quarantine": 0,
            },
            "honest": {
                "submitted": 0,
                "rejected_trust": 0,
                "rejected_crypto": 0,
                "rejected_total": 0,
                "flagged_trust": 0,
                "accepted_aggregated": 0,
                "prevented_quarantine": 0,
            }
        }

        self.server = FederatedServer(
            input_dim=self.input_dim, num_classes=self.num_classes,
            aggregation_algorithm=self.aggregation, device=self.device, seed=self.seed
        )

        self.trust_engine = MultiCriteriaTrustEngine(
            input_dim=self.input_dim, num_classes=self.num_classes,
            norm_threshold_factor=self.norm_threshold_factor,
            cosine_threshold=self.cosine_threshold,
            loss_increase_threshold=self.loss_increase_threshold,
            enable_norm_check=self.enable_norm_check,
            enable_cosine_check=self.enable_cosine_check,
            enable_loss_check=self.enable_loss_check,
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
            self.dp_mechanism = ClientLevelDPMechanism(
                clip_norm=self.dp_clip_norm,
                noise_multiplier=self.dp_noise_multiplier,
                seed=self.seed
            )
            self.rdp_accountant = RDPAccountant()

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

        # Track clients quarantined before round starts
        quarantined_cids = [
            client.client_id for client in self.clients
            if self.enable_quarantine and self.reputation_mgr.is_quarantined(client.client_id)
        ]
        prevented_malicious = [cid for cid in quarantined_cids if cid in self.malicious_client_ids]
        prevented_honest = [cid for cid in quarantined_cids if cid not in self.malicious_client_ids]

        # ---- Step A: Local Training ----
        for client in self.clients:
            if client.client_id in quarantined_cids:
                continue

            client.set_global_weights(current_global_weights)
            client.local_train(
                epochs=self.local_epochs, batch_size=self.batch_size,
                lr=self.lr, fedprox_mu=self.fedprox_mu,
                global_weights=current_global_weights,
                round_num=r
            )
            weights = client.get_local_weights()

            # Apply DP noise if enabled
            if self.dp_enabled:
                if self.dp_mechanism is not None:
                    client_dp_seed = (self.seed * 10007 + r * 997 + client.client_id * 101) % (2**31 - 1)
                    weights, dp_meta = self.dp_mechanism.privatize_client_weights(
                        local_weights=weights,
                        global_weights=current_global_weights,
                        seed=client_dp_seed
                    )
                elif self.dp_engine is not None:
                    weights, dp_meta = self.dp_engine.privatize(weights)
                dp_meta_round[client.client_id] = dp_meta

            # Apply model poisoning (non-label-flip attacks)
            if (self.attack_enabled
                    and client.client_id in self.malicious_client_ids
                    and self.attack_type not in ("label_flip", "targeted_label_flip")):
                if self.attack_type == "adaptive_byzantine":
                    weights = generate_adaptive_byzantine_update(
                        honest_weights=weights,
                        global_weights=current_global_weights,
                        norm_threshold_factor=self.norm_threshold_factor,
                        cosine_threshold=self.cosine_threshold,
                        loss_headroom=self.adaptive_loss_headroom,
                        stealth_factor=self.adaptive_stealth_factor,
                        seed=self.seed + r
                    )
                    self.attack_log.append({
                        "round": r, "client_id": client.client_id,
                        "attack_type": "adaptive_byzantine",
                        "stealth_factor": self.adaptive_stealth_factor
                    })
                elif self.attack_type == "sybil_coalition":
                    sybil_dict = generate_sybil_coalition_updates(
                        base_weights=current_global_weights,
                        coalition_client_ids=[client.client_id],
                        intensity=self.sybil_intensity,
                        seed=self.seed + r
                    )
                    weights = sybil_dict[client.client_id]
                    self.attack_log.append({
                        "round": r, "client_id": client.client_id,
                        "attack_type": "sybil_coalition",
                        "intensity": self.sybil_intensity
                    })
                else:
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

        # Submitted client groups in this round
        submitted_malicious = [cid for cid in client_raw_weights if cid in self.malicious_client_ids]
        submitted_honest = [cid for cid in client_raw_weights if cid not in self.malicious_client_ids]

        # ---- Step B: Cryptographic Verification & Trust Validation ----
        sig_verified_cids: List[int] = []
        sig_rejected_cids: List[int] = []
        for cid, w in client_raw_weights.items():
            if self.enable_signature_verify:
                w_hash = CryptoManager.sha256_hash(w.tobytes().hex())
                pub_k = self.client_keys[cid][1]
                if CryptoManager.verify_signature(pub_k, w_hash, client_signatures[cid]):
                    sig_verified_cids.append(cid)
                else:
                    sig_rejected_cids.append(cid)
                    print(f"  [🚨 Crypto Alert] Round {r}: Client {cid} rejected due to INVALID SIGNATURE")
            else:
                sig_verified_cids.append(cid)

        candidate_weights = {cid: client_raw_weights[cid] for cid in sig_verified_cids}

        accepted_weights: List[np.ndarray] = []
        accepted_counts:  List[int]        = []
        accepted_reps:    List[float]      = []
        trust_flagged_cids: List[int]      = []
        trust_rejected_cids: List[int]     = []
        accepted_cids: List[int]           = []
        validation_reports: Dict[int, Dict] = {}

        defense_active = self.enable_trust_engine and len(candidate_weights) > 1

        if defense_active:
            validation_reports = self.trust_engine.evaluate_updates(
                candidate_weights, current_global_weights, val_data
            )
            if self.enable_reputation:
                self.reputation_mgr.update_reputation(validation_reports)

            for cid, report in validation_reports.items():
                is_valid = report["is_valid"]
                status_str = "ACCEPTED" if is_valid else "REJECTED"
                rep_history = self.reputation_mgr.reputation_history[cid]
                rep_before = rep_history[-2] if len(rep_history) >= 2 else 1.0
                rep_after  = self.reputation_mgr.reputations[cid]

                if self.enable_blockchain:
                    tx = Transaction(
                        client_id=cid,
                        round_num=r,
                        weights_hash=CryptoManager.sha256_hash(
                            candidate_weights[cid].tobytes().hex()
                        ),
                        signature=client_signatures[cid],
                        validation_metrics=report,
                        status=status_str,
                        reputation_before=rep_before,
                        reputation_after=rep_after
                    )
                    self.blockchain.add_transaction(tx)

                if is_valid:
                    accepted_weights.append(candidate_weights[cid])
                    accepted_counts.append(sample_counts[cid])
                    accepted_reps.append(rep_after)
                    accepted_cids.append(cid)
                else:
                    trust_flagged_cids.append(cid)
                    trust_rejected_cids.append(cid)
                    print(
                        f"  [🚨 Trust Alert] Round {r}: Client {cid} REJECTED "
                        f"| Reason: {report['reason'][:80]}"
                    )

            if self.enable_blockchain:
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
            # Trust defense disabled: accept all signature-verified updates naively
            for cid in sig_verified_cids:
                accepted_weights.append(candidate_weights[cid])
                accepted_counts.append(sample_counts[cid])
                accepted_reps.append(1.0)
                accepted_cids.append(cid)

        # Explicit Dispositions Breakdown
        crypto_rejected_malicious = [cid for cid in sig_rejected_cids if cid in self.malicious_client_ids]
        crypto_rejected_honest = [cid for cid in sig_rejected_cids if cid not in self.malicious_client_ids]
        trust_flagged_malicious = [cid for cid in trust_flagged_cids if cid in self.malicious_client_ids]
        trust_flagged_honest = [cid for cid in trust_flagged_cids if cid not in self.malicious_client_ids]
        trust_rejected_malicious = [cid for cid in trust_rejected_cids if cid in self.malicious_client_ids]
        trust_rejected_honest = [cid for cid in trust_rejected_cids if cid not in self.malicious_client_ids]
        accepted_malicious = [cid for cid in accepted_cids if cid in self.malicious_client_ids]
        accepted_honest = [cid for cid in accepted_cids if cid not in self.malicious_client_ids]

        all_rejected_cids = list(sig_rejected_cids) + list(trust_rejected_cids)
        rejected_malicious_round = [cid for cid in all_rejected_cids if cid in self.malicious_client_ids]
        rejected_honest_round = [cid for cid in all_rejected_cids if cid not in self.malicious_client_ids]

        # Update cumulative accounting state
        self.cumulative_accounting["malicious"]["submitted"] += len(submitted_malicious)
        self.cumulative_accounting["malicious"]["rejected_trust"] += len(trust_rejected_malicious)
        self.cumulative_accounting["malicious"]["rejected_crypto"] += len(crypto_rejected_malicious)
        self.cumulative_accounting["malicious"]["rejected_total"] += len(rejected_malicious_round)
        self.cumulative_accounting["malicious"]["flagged_trust"] += len(trust_flagged_malicious)
        self.cumulative_accounting["malicious"]["accepted_aggregated"] += len(accepted_malicious)
        self.cumulative_accounting["malicious"]["prevented_quarantine"] += len(prevented_malicious)

        self.cumulative_accounting["honest"]["submitted"] += len(submitted_honest)
        self.cumulative_accounting["honest"]["rejected_trust"] += len(trust_rejected_honest)
        self.cumulative_accounting["honest"]["rejected_crypto"] += len(crypto_rejected_honest)
        self.cumulative_accounting["honest"]["rejected_total"] += len(rejected_honest_round)
        self.cumulative_accounting["honest"]["flagged_trust"] += len(trust_flagged_honest)
        self.cumulative_accounting["honest"]["accepted_aggregated"] += len(accepted_honest)
        self.cumulative_accounting["honest"]["prevented_quarantine"] += len(prevented_honest)

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

        # ---- Step D: Global Evaluation & Stage 2D Metrics ----
        eval_bs = min(self.batch_size, len(self.X_test)) if len(self.X_test) > 0 else 32
        eval_metrics = self.server.evaluate(self.X_test, self.y_test, batch_size=eval_bs)
        round_duration = time.time() - round_t0

        # Predictions for ASR and clean accuracy
        y_preds = eval_metrics.get("predictions", None)
        if y_preds is None and len(self.X_test) > 0:
            y_preds = self.server.predict(self.X_test, batch_size=eval_bs)
        else:
            y_preds = np.array(y_preds) if y_preds is not None else np.array([])

        is_targeted_attack = (
            self.attack_enabled
            and self.attack_type in ("label_flip", "targeted_label_flip")
            and self.label_flip_source is not None
            and self.label_flip_target is not None
            and len(self.X_test) > 0
        )
        if is_targeted_attack:
            asr = float(compute_attack_success_rate(self.y_test, y_preds, self.label_flip_source, self.label_flip_target))
            clean_acc = float(compute_clean_accuracy(self.y_test, y_preds, self.label_flip_source))
        else:
            asr = None
            clean_acc = float(eval_metrics["accuracy"])

        # Round metrics (using submitted malicious as denominator; None if zero submitted)
        round_mudr = compute_mudr(trust_flagged_cids, submitted_malicious)
        round_murr = compute_murr(all_rejected_cids, submitted_malicious)
        round_fpr = compute_fpr(all_rejected_cids, submitted_honest)
        round_puaa = compute_puaa(all_rejected_cids, submitted_malicious)

        # Cumulative metrics up to round r
        cum_mal_sub = self.cumulative_accounting["malicious"]["submitted"]
        cum_mal_rej = self.cumulative_accounting["malicious"]["rejected_total"]
        cum_mal_acc = self.cumulative_accounting["malicious"]["accepted_aggregated"]
        cum_mal_flag = self.cumulative_accounting["malicious"]["flagged_trust"]
        cum_hon_sub = self.cumulative_accounting["honest"]["submitted"]
        cum_hon_rej = self.cumulative_accounting["honest"]["rejected_total"]

        cum_murr = float(cum_mal_rej / cum_mal_sub) if cum_mal_sub > 0 else None
        cum_puaa = float(cum_mal_acc / cum_mal_sub) if cum_mal_sub > 0 else None
        cum_mudr = float(cum_mal_flag / cum_mal_sub) if cum_mal_sub > 0 else None
        cum_fpr = float(cum_hon_rej / cum_hon_sub) if cum_hon_sub > 0 else None

        quarantined_count = len([cid for cid in range(self.num_clients) if self.reputation_mgr.is_quarantined(cid)])
        degradation = max(0.0, (self.clean_baseline_acc - eval_metrics["accuracy"])) if self.clean_baseline_acc is not None else 0.0

        # Build reputation snapshot
        rep_snapshot = {
            cid: self.reputation_mgr.get_reputation(cid)
            for cid in range(self.num_clients)
        }

        round_record = {
            "round": r,
            "accuracy": eval_metrics["accuracy"],
            "clean_accuracy": clean_acc,
            "asr": asr,
            "mudr": round_mudr,
            "murr": round_murr,
            "fpr": round_fpr,
            "puaa": round_puaa,
            "cumulative_mudr": cum_mudr,
            "cumulative_murr": cum_murr,
            "cumulative_fpr": cum_fpr,
            "cumulative_puaa": cum_puaa,
            "quarantined_count": quarantined_count,
            "prevented_from_submission": len(prevented_malicious) + len(prevented_honest),
            "prevented_malicious_submissions": len(prevented_malicious),
            "dispositions": {
                "malicious_submitted": len(submitted_malicious),
                "malicious_rejected_trust": len(trust_rejected_malicious),
                "malicious_rejected_crypto": len(crypto_rejected_malicious),
                "malicious_rejected_total": len(rejected_malicious_round),
                "malicious_flagged_trust": len(trust_flagged_malicious),
                "malicious_accepted_aggregated": len(accepted_malicious),
                "malicious_prevented_quarantine": len(prevented_malicious),
                "honest_submitted": len(submitted_honest),
                "honest_rejected_trust": len(trust_rejected_honest),
                "honest_rejected_crypto": len(crypto_rejected_honest),
                "honest_rejected_total": len(rejected_honest_round),
                "honest_flagged_trust": len(trust_flagged_honest),
                "honest_accepted_aggregated": len(accepted_honest),
                "honest_prevented_quarantine": len(prevented_honest),
            },
            "performance_degradation": degradation,
            "precision": eval_metrics["precision"],
            "recall": eval_metrics["recall"],
            "f1_score": eval_metrics["f1_score"],
            "precision_macro": eval_metrics.get("precision_macro", eval_metrics["precision"]),
            "recall_macro": eval_metrics.get("recall_macro", eval_metrics["recall"]),
            "f1_score_macro": eval_metrics.get("f1_score_macro", eval_metrics["f1_score"]),
            "loss": eval_metrics["loss"],
            "num_active_clients": len(accepted_weights),
            "rejected_client_ids": all_rejected_cids,
            "num_rejected": len(all_rejected_cids),
            "reputation_snapshot": rep_snapshot,
            "global_weights_hash": self.server.get_global_weights_hash(),
            "blockchain_height": len(self.blockchain.chain),
            "duration_sec": round_duration,
        }

        if dp_meta_round:
            self.dp_accounting.append({"round": r, "dp_meta": dp_meta_round})
            if self.dp_enabled and self.rdp_accountant is not None:
                self.rdp_accountant.step(
                    noise_multiplier=self.dp_noise_multiplier,
                    clip_norm=self.dp_clip_norm,
                    rounds=1
                )

        print(
            f"  Round {r:>2}/{self.num_rounds} | "
            f"Acc: {eval_metrics['accuracy']*100:.2f}% | "
            f"F1: {eval_metrics['f1_score']:.4f} | "
            f"Loss: {eval_metrics['loss']:.4f} | "
            f"Rejected: {len(all_rejected_cids)} | "
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
        initial_model_weights_hash = self.server.get_global_weights_hash()
        cleaned_config = {
            k: v for k, v in self.config.items()
            if k not in ("X_train", "y_train", "X_val", "y_val", "X_test", "y_test", "feature_names", "class_names", "val_data", "loader")
        }
        config_hash = CryptoManager.sha256_hash(json.dumps(cleaned_config, sort_keys=True, default=str))

        # Strict 3-Way Isolation: retrieve prepared validation benchmark
        val_data = self.val_data

        # Round 0 — initial evaluation (untrained global model)
        eval_bs = min(self.batch_size, len(self.X_test)) if len(self.X_test) > 0 else 32
        init_eval = self.server.evaluate(self.X_test, self.y_test, batch_size=eval_bs)
        self.clean_baseline_acc = float(init_eval["accuracy"])
        self.round_logs = [{
            "round": 0,
            "accuracy": init_eval["accuracy"],
            "clean_accuracy": init_eval["accuracy"],
            "asr": None,
            "mudr": None,
            "murr": None,
            "fpr": None,
            "puaa": None,
            "cumulative_mudr": None,
            "cumulative_murr": None,
            "cumulative_fpr": None,
            "cumulative_puaa": None,
            "quarantined_count": 0,
            "prevented_from_submission": 0,
            "prevented_malicious_submissions": 0,
            "dispositions": {
                "malicious_submitted": 0,
                "malicious_rejected_trust": 0,
                "malicious_rejected_crypto": 0,
                "malicious_rejected_total": 0,
                "malicious_flagged_trust": 0,
                "malicious_accepted_aggregated": 0,
                "malicious_prevented_quarantine": 0,
                "honest_submitted": 0,
                "honest_rejected_trust": 0,
                "honest_rejected_crypto": 0,
                "honest_rejected_total": 0,
                "honest_flagged_trust": 0,
                "honest_accepted_aggregated": 0,
                "honest_prevented_quarantine": 0,
            },
            "performance_degradation": 0.0,
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

        # Calculate cumulative metrics across all rounds
        cum_mal_sub = self.cumulative_accounting["malicious"]["submitted"]
        cum_mal_rej = self.cumulative_accounting["malicious"]["rejected_total"]
        cum_mal_acc = self.cumulative_accounting["malicious"]["accepted_aggregated"]
        cum_mal_flag = self.cumulative_accounting["malicious"]["flagged_trust"]
        cum_hon_sub = self.cumulative_accounting["honest"]["submitted"]
        cum_hon_rej = self.cumulative_accounting["honest"]["rejected_total"]

        cum_murr = float(cum_mal_rej / cum_mal_sub) if cum_mal_sub > 0 else None
        cum_puaa = float(cum_mal_acc / cum_mal_sub) if cum_mal_sub > 0 else None
        cum_mudr = float(cum_mal_flag / cum_mal_sub) if cum_mal_sub > 0 else None
        cum_fpr = float(cum_hon_rej / cum_hon_sub) if cum_hon_sub > 0 else None

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
            "initial_model_weights_hash": initial_model_weights_hash,
            "config_hash": config_hash,
            "config": {
                k: v for k, v in self.config.items()
                if k not in ("X_train", "y_train", "X_val", "y_val", "X_test", "y_test", "feature_names", "class_names", "val_data", "loader")
            },
            "final_accuracy":        final["accuracy"],
            "final_clean_accuracy":  final.get("clean_accuracy", final["accuracy"]),
            "final_asr":             final.get("asr"),
            "final_mudr":            cum_mudr,
            "final_murr":            cum_murr,
            "final_fpr":             cum_fpr,
            "final_puaa":            cum_puaa,
            "cumulative_mudr":       cum_mudr,
            "cumulative_murr":       cum_murr,
            "cumulative_fpr":        cum_fpr,
            "cumulative_puaa":       cum_puaa,
            "final_round_mudr":      final.get("mudr"),
            "final_round_murr":      final.get("murr"),
            "final_round_fpr":       final.get("fpr"),
            "final_round_puaa":      final.get("puaa"),
            "final_quarantined_count": final.get("quarantined_count", 0),
            "final_degradation":     final.get("performance_degradation", 0.0),
            "cumulative_dispositions": dict(self.cumulative_accounting),
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
            "dp_summary":            self.rdp_accountant.summary(delta=self.dp_target_delta) if (self.dp_enabled and self.rdp_accountant is not None) else None,
            "blockchain_summary":    self.blockchain.get_audit_summary(),
            "reputation_summary":    self.reputation_mgr.get_status_summary(),
            "chain_valid":           self.blockchain.is_chain_valid(),
            "xai_demo":              xai_demo,
            "stage2d_metrics": {
                "initial_model_weights_hash": initial_model_weights_hash,
                "config_hash": config_hash,
                "cumulative_murr": cum_murr,
                "cumulative_mudr": cum_mudr,
                "cumulative_puaa": cum_puaa,
                "cumulative_fpr": cum_fpr,
                "final_murr": cum_murr,
                "final_mudr": cum_mudr,
                "final_puaa": cum_puaa,
                "final_fpr": cum_fpr,
                "final_round_murr": final.get("murr"),
                "final_round_mudr": final.get("mudr"),
                "final_round_puaa": final.get("puaa"),
                "final_round_fpr": final.get("fpr"),
                "final_clean_accuracy": final.get("clean_accuracy", final["accuracy"]),
                "final_asr": final.get("asr"),
                "final_quarantined_count": final.get("quarantined_count", 0),
                "final_degradation": final.get("performance_degradation", 0.0),
                "cumulative_dispositions": dict(self.cumulative_accounting)
            },
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
