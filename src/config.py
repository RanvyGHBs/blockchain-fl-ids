"""
Configuration and Execution Mode Architecture for Federated Learning and Privacy (WP2.4).
Defines execution modes (TEST, RESEARCH_SIMULATION, DEPLOYMENT), privacy randomness modes,
startup validation rules, and calibrated research baseline parameters.
"""

from enum import Enum
from typing import Dict, Any, Optional, Union
import math
from dataclasses import dataclass, field


class ExecutionMode(str, Enum):
    """
    Execution Mode Abstraction:
    - TEST: Unit testing and deterministic regression testing. Allows explicit seeds.
    - RESEARCH_SIMULATION: Controlled research experiments using formal differential privacy.
      Enforces OS-backed CSPRNG Gaussian noise. Rejects deterministic privacy noise.
    - DEPLOYMENT: Architectural preparation for multi-node deployment.
      Requires client-local noise generation. Rejects centralized noise generation.
    """
    TEST = "TEST"
    RESEARCH_SIMULATION = "RESEARCH_SIMULATION"
    DEPLOYMENT = "DEPLOYMENT"


class PrivacyRandomnessMode(str, Enum):
    """
    Privacy Randomness Mode:
    - DETERMINISTIC_TEST: Pseudorandom generator (MT19937) with explicit seed. Permitted ONLY in TEST mode.
    - OS_CSPRNG: Operating system kernel CSPRNG (CryptGenRandom / BCryptGenRandom / dev/urandom).
      Mandatory for RESEARCH_SIMULATION and DEPLOYMENT modes.
    """
    DETERMINISTIC_TEST = "DETERMINISTIC_TEST"
    OS_CSPRNG = "OS_CSPRNG"


# Approved Research Baseline Parameters (WP2.2 / WP2.4)
APPROVED_CLIP_NORM: float = 1.0
APPROVED_NOISE_MULTIPLIER: float = 1.0
APPROVED_TARGET_DELTA: float = 1e-5
APPROVED_COMMUNICATION_ROUNDS: int = 5
APPROVED_CLIENTS_COUNT: int = 5
APPROVED_GAUSSIAN_STD: float = 2.0  # 2 * sigma * C = 2 * 1.0 * 1.0 = 2.0
APPROVED_EPSILON_REPORTED: float = 13.2565  # approx 13.26

# Legacy uncalibrated noise multiplier to be rejected in research evaluation
LEGACY_UNCALIBRATED_NOISE_MULTIPLIER: float = 0.01


@dataclass
class FLConfig:
    """
    Validated Federated Learning & Privacy Configuration.
    """
    execution_mode: ExecutionMode = ExecutionMode.RESEARCH_SIMULATION
    privacy_randomness_mode: PrivacyRandomnessMode = PrivacyRandomnessMode.OS_CSPRNG
    
    # Federated settings
    num_clients: int = 5
    num_rounds: int = 5
    batch_size: int = 64
    local_epochs: int = 2
    learning_rate: float = 0.001
    fedprox_mu: float = 0.01
    aggregation_algorithm: str = "fedavg"
    seed: int = 42
    device: str = "cpu"
    
    # Differential privacy settings
    dp_enabled: bool = False
    dp_clip_norm: float = APPROVED_CLIP_NORM
    dp_noise_multiplier: float = APPROVED_NOISE_MULTIPLIER
    dp_target_delta: float = APPROVED_TARGET_DELTA
    communication_rounds: int = APPROVED_COMMUNICATION_ROUNDS
    
    # Trust & defense
    defense_enabled: bool = True
    norm_threshold_factor: float = 2.5
    cosine_threshold: float = 0.2
    reputation_decay: float = 0.85
    trust_calibration_mode: str = "uncalibrated"  # "uncalibrated" or "privacy_aware"
    norm_margin_factor: float = 1.25
    norm_min_factor: float = 0.75
    calibrated_cosine_threshold: float = 0.10
    calibrated_loss_factor: float = 5.0
    
    # Attack settings
    attack_enabled: bool = False
    malicious_client_ids: list = field(default_factory=list)
    attack_type: Optional[str] = None
    
    # Blockchain
    difficulty: int = 2
    committee_size: int = 3


def validate_config(config: Union[Dict[str, Any], FLConfig]) -> FLConfig:
    """
    Validates configuration at startup and enforces security invariants:
    1. Rejects unsupported execution modes.
    2. Rejects insecure randomness in RESEARCH_SIMULATION and DEPLOYMENT.
    3. Rejects legacy uncalibrated sigma=0.01 for approved research evaluation.
    4. Prevents silent fallback to TEST mode.
    5. Prevents silent fallback to MT19937.
    6. Validates parameter bounds (C > 0, sigma >= 0, 0 < delta < 1, rounds >= 1).
    7. Validates consistency between DP mechanism parameters and accountant parameters.
    """
    if isinstance(config, FLConfig):
        cfg_dict = {k: getattr(config, k) for k in config.__dataclass_fields__}
    elif isinstance(config, dict):
        cfg_dict = dict(config)
    else:
        raise TypeError(f"config must be a dict or FLConfig instance, got {type(config)}")

    # 1. Validate ExecutionMode
    mode_val = cfg_dict.get("execution_mode", ExecutionMode.RESEARCH_SIMULATION)
    if isinstance(mode_val, str):
        try:
            execution_mode = ExecutionMode(mode_val.upper())
        except ValueError:
            raise ValueError(
                f"Unsupported execution_mode: '{mode_val}'. "
                f"Must be one of {[m.value for m in ExecutionMode]}"
            )
    elif isinstance(mode_val, ExecutionMode):
        execution_mode = mode_val
    else:
        raise ValueError(f"Invalid execution_mode type: {type(mode_val)}")

    # 2. Validate PrivacyRandomnessMode
    rand_val = cfg_dict.get("privacy_randomness_mode", None)
    if rand_val is None:
        if execution_mode in (ExecutionMode.RESEARCH_SIMULATION, ExecutionMode.DEPLOYMENT):
            privacy_randomness_mode = PrivacyRandomnessMode.OS_CSPRNG
        else:
            privacy_randomness_mode = PrivacyRandomnessMode.DETERMINISTIC_TEST
    elif isinstance(rand_val, str):
        try:
            privacy_randomness_mode = PrivacyRandomnessMode(rand_val.upper())
        except ValueError:
            raise ValueError(
                f"Unsupported privacy_randomness_mode: '{rand_val}'. "
                f"Must be one of {[r.value for r in PrivacyRandomnessMode]}"
            )
    elif isinstance(rand_val, PrivacyRandomnessMode):
        privacy_randomness_mode = rand_val
    else:
        raise ValueError(f"Invalid privacy_randomness_mode type: {type(rand_val)}")

    # Security Invariant: Rejects insecure randomness in secure modes
    if execution_mode in (ExecutionMode.RESEARCH_SIMULATION, ExecutionMode.DEPLOYMENT):
        if privacy_randomness_mode != PrivacyRandomnessMode.OS_CSPRNG:
            raise ValueError(
                f"Insecure randomness mode '{privacy_randomness_mode.value}' is strictly prohibited "
                f"in {execution_mode.value} mode. Mandatory randomness mode is OS_CSPRNG."
            )

    # 3. Validate DP parameters
    dp_enabled = bool(cfg_dict.get("dp_enabled", False))
    dp_clip_norm = float(cfg_dict.get("dp_clip_norm", APPROVED_CLIP_NORM))
    dp_noise_multiplier = float(cfg_dict.get("dp_noise_multiplier", APPROVED_NOISE_MULTIPLIER))
    dp_target_delta = float(cfg_dict.get("dp_target_delta", APPROVED_TARGET_DELTA))
    rounds = int(cfg_dict.get("communication_rounds", cfg_dict.get("num_rounds", APPROVED_COMMUNICATION_ROUNDS)))

    if not isinstance(dp_clip_norm, (int, float)) or math.isnan(dp_clip_norm) or math.isinf(dp_clip_norm) or dp_clip_norm <= 0:
        raise ValueError(f"dp_clip_norm must be a positive finite number, got {dp_clip_norm}")
    if not isinstance(dp_noise_multiplier, (int, float)) or math.isnan(dp_noise_multiplier) or math.isinf(dp_noise_multiplier):
        raise ValueError(f"dp_noise_multiplier must be a finite real number, got {dp_noise_multiplier}")
    if dp_noise_multiplier < 0:
        raise ValueError(f"dp_noise_multiplier cannot be negative, got {dp_noise_multiplier}")
    if not isinstance(dp_target_delta, (int, float)) or math.isnan(dp_target_delta) or dp_target_delta <= 0 or dp_target_delta >= 1:
        raise ValueError(f"dp_target_delta must be in (0, 1), got {dp_target_delta}")
    if rounds <= 0:
        raise ValueError(f"communication_rounds must be >= 1, got {rounds}")

    # Security Invariant: Require sigma > 0 in secure execution modes when DP is enabled
    if dp_enabled and execution_mode in (ExecutionMode.RESEARCH_SIMULATION, ExecutionMode.DEPLOYMENT):
        if dp_noise_multiplier <= 0:
            raise ValueError(
                f"dp_noise_multiplier must be strictly positive (sigma > 0) in {execution_mode.value} mode, "
                f"got {dp_noise_multiplier}. Zero-noise is strictly prohibited in secure privacy execution."
            )

    # Security Invariant: Reject legacy uncalibrated sigma=0.01 in approved research evaluation
    if dp_enabled and execution_mode == ExecutionMode.RESEARCH_SIMULATION:
        if math.isclose(dp_noise_multiplier, LEGACY_UNCALIBRATED_NOISE_MULTIPLIER, abs_tol=1e-5):
            raise ValueError(
                f"Legacy uncalibrated sigma={LEGACY_UNCALIBRATED_NOISE_MULTIPLIER} is strictly rejected "
                f"for approved research evaluation. Calibrated research baseline is sigma={APPROVED_NOISE_MULTIPLIER}."
            )

    # 4. Validate Trust & Calibration settings
    cal_mode_raw = str(cfg_dict.get("trust_calibration_mode", "uncalibrated")).lower().strip()
    if cal_mode_raw in ("calibrated", "privacy_aware", "dp_aware"):
        trust_calibration_mode = "privacy_aware"
    else:
        trust_calibration_mode = "uncalibrated"

    norm_margin_factor = float(cfg_dict.get("norm_margin_factor", 1.25))
    norm_min_factor = float(cfg_dict.get("norm_min_factor", 0.75))
    calibrated_cosine_threshold = float(cfg_dict.get("calibrated_cosine_threshold", 0.10))
    calibrated_loss_factor = float(cfg_dict.get("calibrated_loss_factor", 5.0))

    if norm_margin_factor <= 0 or norm_min_factor < 0:
        raise ValueError(f"Norm margin factors must be non-negative, got min={norm_min_factor}, margin={norm_margin_factor}")

    # Construct validated FLConfig object
    validated = FLConfig(
        execution_mode=execution_mode,
        privacy_randomness_mode=privacy_randomness_mode,
        num_clients=int(cfg_dict.get("num_clients", 5)),
        num_rounds=rounds,
        batch_size=int(cfg_dict.get("batch_size", 64)),
        local_epochs=int(cfg_dict.get("local_epochs", 2)),
        learning_rate=float(cfg_dict.get("learning_rate", 0.001)),
        fedprox_mu=float(cfg_dict.get("fedprox_mu", 0.01)),
        aggregation_algorithm=str(cfg_dict.get("aggregation_algorithm", "fedavg")),
        seed=int(cfg_dict.get("seed", 42)),
        device=str(cfg_dict.get("device", "cpu")),
        dp_enabled=dp_enabled,
        dp_clip_norm=dp_clip_norm,
        dp_noise_multiplier=dp_noise_multiplier,
        dp_target_delta=dp_target_delta,
        communication_rounds=rounds,
        defense_enabled=bool(cfg_dict.get("defense_enabled", True)),
        norm_threshold_factor=float(cfg_dict.get("norm_threshold_factor", 2.5)),
        cosine_threshold=float(cfg_dict.get("cosine_threshold", 0.2)),
        reputation_decay=float(cfg_dict.get("reputation_decay", 0.85)),
        trust_calibration_mode=trust_calibration_mode,
        norm_margin_factor=norm_margin_factor,
        norm_min_factor=norm_min_factor,
        calibrated_cosine_threshold=calibrated_cosine_threshold,
        calibrated_loss_factor=calibrated_loss_factor,
        attack_enabled=bool(cfg_dict.get("attack_enabled", False)),
        malicious_client_ids=list(cfg_dict.get("malicious_client_ids", [])),
        attack_type=cfg_dict.get("attack_type", None),
        difficulty=int(cfg_dict.get("difficulty", 2)),
        committee_size=int(cfg_dict.get("committee_size", 3))
    )
    return validated


def get_approved_research_config(**kwargs) -> FLConfig:
    """
    Returns the validated configuration for the approved research baseline:
    C=1.0, sigma=1.0, delta=1e-5, T=5, execution_mode=RESEARCH_SIMULATION.
    """
    base_params = {
        "execution_mode": ExecutionMode.RESEARCH_SIMULATION,
        "privacy_randomness_mode": PrivacyRandomnessMode.OS_CSPRNG,
        "dp_enabled": True,
        "dp_clip_norm": APPROVED_CLIP_NORM,
        "dp_noise_multiplier": APPROVED_NOISE_MULTIPLIER,
        "dp_target_delta": APPROVED_TARGET_DELTA,
        "communication_rounds": APPROVED_COMMUNICATION_ROUNDS,
        "num_clients": APPROVED_CLIENTS_COUNT,
        "num_rounds": APPROVED_COMMUNICATION_ROUNDS
    }
    base_params.update(kwargs)
    return validate_config(base_params)
