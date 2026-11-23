# WP2.2 — Experimental Privacy Safety Checklist and Governance Audit

**Project:** Blockchain-Assisted Privacy-Preserving Federated Learning for Network Intrusion Detection with Trust-Based Security and Cryptographic Auditing  
**Workspace:** `C:\Users\is043\.gemini\antigravity\scratch\blockchain-fl-ids`  
**Milestone:** WP2.2 — Privacy Configuration Calibration & Experimental Release Gate  
**Deliverable:** Configuration Safety Checks & Governance Assessment  
**Execution Mode:** STRICTLY READ-ONLY AUDIT  
**Date:** 2026-11-23  

---

## 1. Executive Summary

This report evaluates nine critical privacy configuration safeguards required before differential privacy experiments can be authorized for release.

Each safeguard is systematically audited against the codebase and classified into one of four standard assurance tiers:
- **Verified in source:** The safeguard is fully implemented, mathematically sound, and verified in code.
- **Partially implemented:** The safeguard is implemented in specific entry points or documented as an operational restriction, but lacks complete automated enforcement across all repository scripts.
- **Missing:** The safeguard is absent from both code and documentation.
- **Not applicable:** The safeguard does not apply to the project's architecture.

### Key Governance Finding
Of the nine evaluated safeguards:
- **5 are Verified in Source**
- **4 are Partially Implemented**
- **0 are Missing**
- **0 are Not Applicable**

Because four safeguards are partially implemented—most notably the persistence of legacy default $\sigma = 0.01$ as a silent fallback—the project is classified under **APPROVED WITH RESTRICTIONS**.

---

## 2. Systematic Safeguard Evaluation Matrix

| ID | Configuration Safeguard Description | Status | Code / Documentation Location | Audit Assessment & Evidence |
|:---:|:---|:---:|:---|:---|
| **SG-01** | Legacy $\sigma = 0.01$ is clearly marked as unsuitable for privacy-guaranteed research experiments. | **Partially Implemented** | `app.py:596`<br/>`run_stage2.py:176`<br/>`orchestrator.py:127` | Marked in UI and historical run script captions as *"without formal privacy accounting"*. However, remains the silent default fallback in `orchestrator.py` if `dp_noise_multiplier` is omitted. |
| **SG-02** | Research configurations explicitly specify $C$, $\sigma$, $T$, and $\delta$. | **Partially Implemented** | `tests/test_wp2_privacy.py:413-416`<br/>`app.py:649` | Explicitly specified in WP2 unit and integration tests. Omitted in `app.py` simulation dictionary and legacy `run_benchmark.py`. |
| **SG-03** | The accountant and mechanism receive consistent parameter values. | **Verified in Source** | `orchestrator.py:448-452`<br/>`orchestrator.py:795-799` | Both `ClientLevelDPMechanism` and `RDPAccountant` receive identical `self.dp_clip_norm` and `self.dp_noise_multiplier`. Zero parameter drift. |
| **SG-04** | The exported privacy summary records the actual configuration used. | **Verified in Source** | `rdp_accountant.py:156-192`<br/>`orchestrator.py:985` | `dp_summary` exports `completed_rounds`, `target_delta`, `epsilon`, `optimal_renyi_order_alpha`, `last_noise_multiplier_sigma`, `last_clip_norm_C`, `sensitivity_S`, `noise_std_dev`, and full `rdp_spectrum`. |
| **SG-05** | Privacy reports identify the adjacency definition and observer model. | **Verified in Source** | `rdp_accountant.py:174, 187`<br/>`reports/WP2_0..WP2_2` | Reports explicitly define replace-one client dataset adjacency ($\mathcal{D} \sim_{\text{replace}} \mathcal{D}'$) and honest-but-curious server observer model with full participation ($q = 1.0$). |
| **SG-06** | No result is labelled differentially private without a corresponding valid privacy calculation. | **Verified in Source** | `stage2_results.json:22`<br/>`rdp_accountant.py:119-150` | Historical results explicitly disclaim formal privacy. In WP2, all DP claims are backed by discrete order RDP conversion. |
| **SG-07** | Deterministic test randomness is not confused with deployment-grade randomness. | **Partially Implemented** | `mechanism.py:118-123`<br/>`orchestrator.py:492` | Mechanism supports unseeded OS entropy (`seed=None`). Orchestrator injects deterministic pseudo-random seed for test repeatability. Documented as restriction for production deployments. |
| **SG-08** | Fixed client cardinalities remain an explicit assumption. | **Verified in Source** | `rdp_accountant.py:189`<br/>`reports/WP2_1_METADATA..` | Explicitly listed under `metadata_exclusions` in `summary()` and documented across WP2.0 and WP2.1 reports. |
| **SG-09** | Original unclipped update norms remain edge-local. | **Partially Implemented** | `mechanism.py:82`<br/>`orchestrator.py:793` | Unclipped `original_norm` is recorded in `self.dp_accounting` within orchestrator memory for simulation visualization. Must be filtered from RPC payloads in physical edge deployments. |

---

## 3. Detailed Audit of Partially Implemented Safeguards

### 3.1. Safeguard SG-01: Silent Fallback to Legacy $\sigma = 0.01$
- **Problem:** In `src/federated/orchestrator.py` (lines 125–128):
  ```python
  self.dp_noise_multiplier = float(config.get("dp_noise_multiplier", 0.01))
  ```
  If a new research script enables DP via `config["dp_enabled"] = True` but neglects to specify `dp_noise_multiplier`, the orchestrator executes with $\sigma = 0.01$ and reports an astronomical epsilon ($\epsilon > 31000$).
- **Required Action for Future Implementation:** When DP is enabled, `FederatedOrchestrator` should raise a `ValueError` if `dp_noise_multiplier` is not explicitly provided, eliminating silent uncalibrated execution.

### 3.2. Safeguard SG-02: Missing DP Hyperparameters in `app.py`
- **Problem:** In `app.py` (line 649), Scenario 7 passes `"dp_enabled": dp_active`, but provides no UI widgets for $C$, $\sigma$, or $\delta$.
- **Required Action for Future Implementation:** Add an interactive Differential Privacy parameter expander in the Streamlit UI allowing researchers to select calibrated noise multipliers ($\sigma \in \{0.5, 0.75, 1.0, 1.5, 2.0\}$).

### 3.3. Safeguard SG-07: PRNG Seed Governance
- **Problem:** The formula `client_dp_seed = (self.seed * 10007 + r * 997 + client.client_id * 101) % (2**31 - 1)` is hardcoded in `orchestrator.py`.
- **Assessment:** While ideal for unit tests and multi-seed benchmarking (seeds 42..46), an honest-but-curious server in a real network could reconstruct the noise vector if it learned the base seed.
- **Required Action for Future Implementation:** Introduce a boolean configuration flag `use_system_entropy: bool = False` that forces `seed=None` when deploying beyond simulated environments.

### 3.4. Safeguard SG-09: Telemetry Filtering
- **Problem:** `self.dp_accounting.append({"round": r, "dp_meta": dp_meta_round})` stores `original_norm` in orchestrator memory.
- **Assessment:** Safe in single-process Python simulation because the data never traverses an untrusted network.
- **Required Action for Future Implementation:** Add an explicit network payload serialization schema that omits `dp_meta` prior to transmission in distributed client-server environments.

---

## 4. Governance Conclusion

The system exhibits high mathematical and cryptographic discipline. None of the nine safeguards are completely missing. The four partially implemented safeguards represent operational and interface hygiene rather than mathematical flaws.

These findings justify authorizing the research configuration under **APPROVED WITH RESTRICTIONS**, requiring future experimental scripts to explicitly provide all privacy hyperparameters.
