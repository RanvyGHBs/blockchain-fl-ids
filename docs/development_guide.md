# Development Guide

This guide covers setting up a local development environment, understanding the repository layout, running the dashboard and test suite, executing supported experiment runners, and preserving frozen research artifacts.

---

## 1. Repository Layout

```text
blockchain-fl-ids/
├── README.md
├── CITATION.cff
├── .gitignore
├── pyproject.toml
├── requirements.txt
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
├── tests/                              # 21 test modules (218 tests)
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
```
For running the test suite, ensure `pytest` is installed (`pip install pytest` if not already in your environment).

---

## 3. Dataset Setup (NSL-KDD)

If `data/raw/KDDTrain+.txt` and `data/raw/KDDTest+.txt` are not already present, `NSLKDDLoader` attempts to fetch them automatically on first run (falling back to a synthetic generator only if network download fails in offline environments).

Verify Track A preprocessing and 3-way isolation:
```bash
python -c "from src.data.nsl_kdd import NSLKDDLoader; loader = NSLKDDLoader(); X_tr, y_tr, X_val, y_val, X_te, y_te = loader.preprocess_isolated(); print('Pool:', X_tr.shape, 'Val:', X_val.shape, 'Test:', X_te.shape)"
```
Expected dimensions on canonical NSL-KDD: `Pool: (124973, 122)`, `Val: (1000, 122)`, `Test: (22544, 122)`.

---

## 4. Running the Application & Tests

### Launch Streamlit Dashboard
```bash
streamlit run app.py
```

### Run Live Terminal Demonstration
Executes a 2-round `RESEARCH_SIMULATION` run under `model_scaling` attack with OS-CSPRNG DP, calibrated trust, blockchain forging, and RDP accounting:
```bash
python scripts/run_live_demo.py
```

### Run Test Suite
```bash
# Full suite (218 tests across 21 files)
pytest tests/ -q

# End-to-end integration pipeline test only
pytest tests/test_end_to_end_pipeline.py -v
```

### Run Frozen Checksum Integrity Audit & Tests Together
```bash
python scripts/maintenance/verify_checksums_and_tests.py
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
