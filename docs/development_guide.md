# Development Guide

This guide covers setting up a local development environment, understanding the repository layout, running the dashboard and test suite, executing supported experiment runners, and preserving frozen research artifacts.

---

## 1. Repository Layout

```text
blockchain-fl-ids/
├── README.md
├── CITATION.cff
├── .gitignore
├── pyproject.toml                        # Pytest markers & Ruff lint configuration
├── requirements.txt                      # Core runtime & dashboard dependencies
├── requirements-dev.txt                  # Development & testing dependencies (pytest, ruff)
├── app.py                              # 6-section Streamlit web application
├── config/
│   └── default.yaml                    # Default FL, DP, trust, and ledger parameters
├── data/
│   ├── raw/                            # KDDTrain+.txt, KDDTest+.txt (untracked raw data + .gitkeep)
│   └── processed/                      # Cached arrays (.npy, git-ignored) + frozen benchmark JSONs
├── docs/
│   ├── architecture.md
│   ├── privacy_and_rdp.md
│   ├── trust_and_attacks.md
│   ├── blockchain_auditing.md
│   ├── experiments_and_results.md
│   ├── development_guide.md
│   ├── release_checklist.md
│   └── project_history/
├── reports/                            # Frozen audit reports, claim matrix & 25-artifact registry
├── scripts/
│   ├── run_live_demo.py                # 2-round live terminal demonstration (WP3 + CSPRNG + PoT)
│   ├── run_wp3_experiments.py          # Resumable 5-seed WP3 benchmark & ablation suite
│   ├── generate_report_figures.py      # Matplotlib figure utility (outputs to submission_report/)
│   ├── capture_dashboard_screenshots.py# Headless Chrome capture utility
│   ├── experiments/                    # Historical stage experiment runners
│   │   ├── run_benchmark.py
│   │   ├── run_stage2.py
│   │   ├── run_stage2d.py
│   │   ├── run_stage2e_wp1.py
│   │   └── run_stage2e_wp4.py
│   └── maintenance/
│       └── verify_checksums_and_tests.py # SHA-256 frozen artifact verifier + pytest runner
├── src/                                # Core library modules
├── tests/                              # 23 test modules (unit + @pytest.mark.integration NSL-KDD suite)
└── submission_report/                  # Git-ignored academic report workspace
```

---

## 2. Environment Setup

### Prerequisites
- Python **3.10 to 3.13** (verified on Python 3.13.7 with CPU PyTorch)
- Git

### Create Virtual Environment & Install Dependencies
```bash
python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows PowerShell:
# .\.venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

- **Runtime dependencies ([requirements.txt](../requirements.txt)):** `torch`, `numpy`, `pandas`, `scipy` (`>=1.14.1` for Python 3.13 compatibility), `scikit-learn`, `cryptography`, `streamlit`, `plotly`, plus optional script plotting (`matplotlib`) and legacy unimported declarations (`pyyaml`, `tqdm`).
- **Development dependencies ([requirements-dev.txt](../requirements-dev.txt)):** `pytest>=7.4.0` and `ruff>=0.8.0`.
- **Packaging Note (`pip install -e .`):** Project imports use top-level `src.*` paths (`pythonpath = ["."]` in `pyproject.toml`). Shipping an editable package named `src` globally would collide with other `src` layouts, so migrating to a dedicated package namespace is deferred as a separate refactoring task to preserve frozen modules and SHA-256 test files unchanged.

---

## 3. Dataset Setup & Integration Test Separation

`data/raw/` is git-ignored. Tests that genuinely invoke `NSLKDDLoader()` against canonical NSL-KDD (`tests/test_stage1.py`, `tests/test_end_to_end_pipeline.py`, `test_wp3_calibrated_trust.py::test_08_orchestrator_integration`, and `test_education.py` tests `09–12`) are marked with `@pytest.mark.integration` so offline unit and synthetic tests can run without downloading the full NSL-KDD dataset.

Verify Track A preprocessing locally when NSL-KDD is present (or allow automatic download / synthetic fallback):
```bash
python -c "from src.data.nsl_kdd import NSLKDDLoader; loader = NSLKDDLoader(); X_tr, y_tr, X_val, y_val, X_te, y_te = loader.preprocess_isolated(); print('Pool:', X_tr.shape, 'Val:', X_val.shape, 'Test:', X_te.shape)"
```
Expected dimensions on canonical NSL-KDD: `Pool: (124973, 122)`, `Val: (1000, 122)`, `Test: (22544, 122)`.

---

## 4. Running the Application & Local Checks

### Launch Streamlit Dashboard
```bash
streamlit run app.py
```

### Lightweight CPU Smoke Demo vs. Full NSL-KDD Demo
```bash
# Fast CPU-only synthetic demo (suitable for fast laptop verification; no dataset download):
python scripts/run_live_demo.py --smoke

# Full 2-round NSL-KDD demonstration:
python scripts/run_live_demo.py
```

### Run Test Suite & Configuration Validation
```bash
# Offline unit & synthetic suite (skips NSL-KDD @pytest.mark.integration tests)
python -m pytest tests/ -m "not integration" -v

# Full local suite (includes @pytest.mark.integration NSL-KDD tests)
python -m pytest tests/ -q

# Configuration & Reputation validation tests only
python -m pytest tests/test_config_validation.py -v

# End-to-end NSL-KDD integration test only
python -m pytest tests/test_end_to_end_pipeline.py -v
```

### Lint Checks (Ruff) & Checksum Verification
```bash
# Repo-wide correctness lint rules (configured in pyproject.toml)
ruff check app.py src scripts tests

# Stricter hygiene check on maintained entrypoints and validation tests
ruff check --select E4,E7,E9,F src/config.py src/trust/reputation.py scripts/run_live_demo.py scripts/maintenance/verify_checksums_and_tests.py scripts/experiments/ tests/test_config_validation.py tests/test_smoke_demo.py tests/test_stage2d2_integrity_hardening.py tests/test_stage2e_3_2_closure.py

# Checksum audit of 25 frozen artifacts (use --checksums-only to skip pytest)
python scripts/maintenance/verify_checksums_and_tests.py
python scripts/maintenance/verify_checksums_and_tests.py --checksums-only
```

---

## 5. Experiment Runners & Output Paths

> **Warning — Preserving Frozen Artifacts:**
> Running the historical scripts below overwrites their corresponding output JSONs inside `data/processed/`. **Do NOT execute these runners if your goal is to preserve the frozen 25-artifact research registry unchanged** (the verification script above checks exact SHA-256 digests).

| Script | Scope | Default Output Location |
|---|---|---|
| `scripts/run_live_demo.py` | Quick interactive 2-round CLI demo (non-overwriting) | Console stdout only |
| `scripts/run_wp3_experiments.py` | WP3 5-seed DP benchmarks, ablations, noise sweep | `data/processed/wp3/*.json` |
| `scripts/experiments/run_benchmark.py` | Early 4-scenario comparative benchmark | `data/processed/benchmark_results.json` |
| `scripts/experiments/run_stage2.py` | Stage 2 6-scenario controlled benchmark (S1–S6) | `data/processed/stage2_results.json` |
| `scripts/experiments/run_stage2d.py` | Stage 2D 18-scenario multi-attack benchmark | `data/processed/stage2d/multi_attack_benchmarks_v3.json` |
| `scripts/experiments/run_stage2e_wp1.py` | WP1 5-seed baseline comparison | `data/processed/stage2e/wp1/*.json` |
| `scripts/experiments/run_stage2e_wp4.py` | WP4 CPU, serialization & tamper audit benchmark (Stage 2E.3) | `data/processed/stage2e/wp4/overhead_summary.json` |

*(Note: `run_stage2e_wp4.py` generates Stage 2E.3 `overhead_summary.json`; the audited Stage 2E.3.1 revision `data/processed/stage2e/wp4/overhead_summary_v2.json` is a separate derived artifact documented in [STAGE_2E_3_1_WP4_OVERHEAD_AND_AUDIT_CORRECTION_REPORT.md](../reports/STAGE_2E_3_1_WP4_OVERHEAD_AND_AUDIT_CORRECTION_REPORT.md). Similarly, `run_stage2e_wp1.py` generates `per_seed_runs.json` and `benchmark_summary.json`, whereas `benchmark_summary_v2.json` is its separate audited revision, and `run_benchmark.py` outputs `data/processed/benchmark_results.json`, which is not tracked in the frozen 25-artifact registry.)*

---

## 6. Preserving Frozen Research Evidence

1. Never edit or overwrite files listed in [FINAL_RESEARCH_ARTIFACT_CHECKSUM_REGISTRY.md](../reports/FINAL_RESEARCH_ARTIFACT_CHECKSUM_REGISTRY.md) (`data/processed/stage2_results.json`, `data/processed/stage2d/*.json`, `data/processed/stage2e/**`, `data/processed/wp3/*.json`, registered `reports/*.md`, and `tests/test_stage2e_3_1_corrections.py`).
2. Keep `reports/` tracked in Git as permanent audit evidence.
3. Keep `submission_report/`, `scratch/`, and `.vscode/` excluded via `.gitignore`.
