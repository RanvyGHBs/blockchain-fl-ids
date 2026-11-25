"""
Configuration and Execution Mode Architecture for Federated Learning and Privacy (WP2.4).
Defines execution modes (TEST, RESEARCH_SIMULATION, DEPLOYMENT), privacy randomness modes,
startup validation rules, and calibrated research baseline parameters.
"""

from enum import Enum
from typing import Dict, Any, Optional, Union, Iterable
import math
from dataclasses import dataclass, field


def _require_int(name: str, val: Any, min_val: Optional[int] = None) -> int:
    """Validates an integer configuration value (rejecting booleans and non-integers)."""
    if isinstance(val, bool) or not isinstance(val, int):
        raise ValueError(f"{name} must be an integer, got {val!r}")
    if min_val is not None and val < min_val:
        raise ValueError(f"{name} must be >= {min_val}, got {val}")
    return val


def _require_finite_float(
    name: str,
    val: Any,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    min_inclusive: bool = True,
    max_inclusive: bool = True,
) -> float:
    """Validates a finite numeric configuration value within optional bounds."""
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise ValueError(f"{name} must be a real number, got {val!r}")
    fval = float(val)
    if math.isnan(fval) or math.isinf(fval):
        raise ValueError(f"{name} must be a finite real number, got {val!r}")
    if min_val is not None:
        if (min_inclusive and fval < min_val) or (not min_inclusive and fval <= min_val):
            op = ">=" if min_inclusive else ">"
            raise ValueError(f"{name} must be {op} {min_val}, got {fval}")
    if max_val is not None:
        if (max_inclusive and fval > max_val) or (not max_inclusive and fval >= max_val):
            op = "<=" if max_inclusive else "<"
            raise ValueError(f"{name} must be {op} {max_val}, got {fval}")
    return fval


def validate_reputation_params(
    client_ids: Optional[Iterable[Any]] = None,
    initial_reputation: float = 1.0,
    reward_delta: float = 0.05,
    slash_delta: float = 0.35,
    quarantine_threshold: float = 0.40,
    probation_rounds: int = 3,
) -> None:
    """Validates ReputationManager initialization parameters."""
    if client_ids is not None:
        cids = list(client_ids)
        if not cids:
            raise ValueError("client_ids must not be empty")
        for cid in cids:
            _require_int("client_id", cid, min_val=0)
    _require_finite_float("initial_reputation", initial_reputation, min_val=0.0, max_val=1.0)
    _require_finite_float("reward_delta", reward_delta, min_val=0.0, max_val=1.0)
    _require_finite_float("slash_delta", slash_delta, min_val=0.0, max_val=1.0)
    _require_finite_float("quarantine_threshold", quarantine_threshold, min_val=0.0, max_val=1.0)
    _require_int("probation_rounds", probation_rounds, min_val=1)


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

    # 3. Validate Federated & DP parameters
    num_clients = _require_int("num_clients", cfg_dict.get("num_clients", 5), min_val=1)
    batch_size = _require_int("batch_size", cfg_dict.get("batch_size", 64), min_val=1)
    local_epochs = _require_int("local_epochs", cfg_dict.get("local_epochs", 2), min_val=1)
    learning_rate = _require_finite_float(
        "learning_rate", cfg_dict.get("learning_rate", 0.001), min_val=0.0, min_inclusive=False
    )
    fedprox_mu = _require_finite_float("fedprox_mu", cfg_dict.get("fedprox_mu", 0.01), min_val=0.0)

    has_comm = "communication_rounds" in cfg_dict and cfg_dict["communication_rounds"] is not None
    has_num = "num_rounds" in cfg_dict and cfg_dict["num_rounds"] is not None
    if has_comm:
        comm_rounds = _require_int("communication_rounds", cfg_dict["communication_rounds"], min_val=1)
    if has_num:
        num_rounds = _require_int("num_rounds", cfg_dict["num_rounds"], min_val=1)
    if has_comm and has_num and comm_rounds != num_rounds:
        raise ValueError(
            f"Inconsistent round configuration: communication_rounds={comm_rounds} != num_rounds={num_rounds}"
        )
    if has_comm:
        rounds = comm_rounds
    elif has_num:
        rounds = num_rounds
    else:
        rounds = APPROVED_COMMUNICATION_ROUNDS

    dp_enabled = bool(cfg_dict.get("dp_enabled", False))
    dp_clip_norm = _require_finite_float(
        "dp_clip_norm", cfg_dict.get("dp_clip_norm", APPROVED_CLIP_NORM), min_val=0.0, min_inclusive=False
    )
    dp_noise_multiplier = _require_finite_float(
        "dp_noise_multiplier", cfg_dict.get("dp_noise_multiplier", APPROVED_NOISE_MULTIPLIER), min_val=0.0
    )
    dp_target_delta = _require_finite_float(
        "dp_target_delta",
        cfg_dict.get("dp_target_delta", APPROVED_TARGET_DELTA),
        min_val=0.0,
        max_val=1.0,
        min_inclusive=False,
        max_inclusive=False,
    )

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

    # 4. Validate Trust, Calibration & Blockchain settings
    cal_mode_raw = str(cfg_dict.get("trust_calibration_mode", "uncalibrated")).lower().strip()
    if cal_mode_raw in ("calibrated", "privacy_aware", "dp_aware"):
        trust_calibration_mode = "privacy_aware"
    else:
        trust_calibration_mode = "uncalibrated"

    norm_threshold_factor = _require_finite_float(
        "norm_threshold_factor", cfg_dict.get("norm_threshold_factor", 2.5), min_val=0.0, min_inclusive=False
    )
    cosine_threshold = _require_finite_float(
        "cosine_threshold", cfg_dict.get("cosine_threshold", 0.2), min_val=-1.0, max_val=1.0
    )
    reputation_decay = _require_finite_float(
        "reputation_decay", cfg_dict.get("reputation_decay", 0.85), min_val=0.0, max_val=1.0
    )
    norm_margin_factor = _require_finite_float(
        "norm_margin_factor", cfg_dict.get("norm_margin_factor", 1.25), min_val=0.0, min_inclusive=False
    )
    norm_min_factor = _require_finite_float(
        "norm_min_factor", cfg_dict.get("norm_min_factor", 0.75), min_val=0.0
    )
    if norm_min_factor > norm_margin_factor:
        raise ValueError(
            f"Inconsistent norm bounds: norm_min_factor={norm_min_factor} > norm_margin_factor={norm_margin_factor}"
        )
    calibrated_cosine_threshold = _require_finite_float(
        "calibrated_cosine_threshold", cfg_dict.get("calibrated_cosine_threshold", 0.10), min_val=-1.0, max_val=1.0
    )
    calibrated_loss_factor = _require_finite_float(
        "calibrated_loss_factor", cfg_dict.get("calibrated_loss_factor", 5.0), min_val=0.0, min_inclusive=False
    )
    difficulty = _require_int("difficulty", cfg_dict.get("difficulty", 2), min_val=0)
    committee_size = _require_int("committee_size", cfg_dict.get("committee_size", 3), min_val=1)

    attack_enabled = bool(cfg_dict.get("attack_enabled", False))
    malicious_client_ids = list(cfg_dict.get("malicious_client_ids", []))
    for cid in malicious_client_ids:
        _require_int("malicious_client_id", cid, min_val=0)
    if attack_enabled and any(cid >= num_clients for cid in malicious_client_ids):
        raise ValueError(
            f"Inconsistent attack configuration: malicious_client_ids={malicious_client_ids} "
            f"contains ID >= num_clients ({num_clients})"
        )

    rep_keys = ("initial_reputation", "reward_delta", "slash_delta", "quarantine_threshold", "probation_rounds")
    if any(k in cfg_dict for k in rep_keys):
        validate_reputation_params(
            initial_reputation=cfg_dict.get("initial_reputation", 1.0),
            reward_delta=cfg_dict.get("reward_delta", 0.05),
            slash_delta=cfg_dict.get("slash_delta", 0.35),
            quarantine_threshold=cfg_dict.get("quarantine_threshold", 0.40),
            probation_rounds=cfg_dict.get("probation_rounds", 3),
        )

    # Construct validated FLConfig object
    validated = FLConfig(
        execution_mode=execution_mode,
        privacy_randomness_mode=privacy_randomness_mode,
        num_clients=num_clients,
        num_rounds=rounds,
        batch_size=batch_size,
        local_epochs=local_epochs,
        learning_rate=learning_rate,
        fedprox_mu=fedprox_mu,
        aggregation_algorithm=str(cfg_dict.get("aggregation_algorithm", "fedavg")),
        seed=int(cfg_dict.get("seed", 42)),
        device=str(cfg_dict.get("device", "cpu")),
        dp_enabled=dp_enabled,
        dp_clip_norm=dp_clip_norm,
        dp_noise_multiplier=dp_noise_multiplier,
        dp_target_delta=dp_target_delta,
        communication_rounds=rounds,
        defense_enabled=bool(cfg_dict.get("defense_enabled", True)),
        norm_threshold_factor=norm_threshold_factor,
        cosine_threshold=cosine_threshold,
        reputation_decay=reputation_decay,
        trust_calibration_mode=trust_calibration_mode,
        norm_margin_factor=norm_margin_factor,
        norm_min_factor=norm_min_factor,
        calibrated_cosine_threshold=calibrated_cosine_threshold,
        calibrated_loss_factor=calibrated_loss_factor,
        attack_enabled=attack_enabled,
        malicious_client_ids=malicious_client_ids,
        attack_type=cfg_dict.get("attack_type", None),
        difficulty=difficulty,
        committee_size=committee_size
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
    if "num_rounds" in kwargs and "communication_rounds" not in kwargs:
        base_params["communication_rounds"] = kwargs["num_rounds"]
    elif "communication_rounds" in kwargs and "num_rounds" not in kwargs:
        base_params["num_rounds"] = kwargs["communication_rounds"]
    base_params.update(kwargs)
    return validate_config(base_params)
