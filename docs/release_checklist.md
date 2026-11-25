# Release Preparation & GitHub Metadata Checklist

Do **not** tag or publish a release (`v1.0.0`) until all items below have been verified after committing the repository cleanup branch.

---

## 1. Pre-Release Technical Checklist

- [x] **Repository Cleanup:** Root clutter (`run_*.py`, `PROJECT_FINAL_STATUS_*.md`, `scratch/`, `.vscode/`) cleaned or untracked while keeping `reports/` and `data/processed/` intact.
- [x] **Documentation & Claim Accuracy:** Root [README.md](../README.md) redesigned as a concise project landing page; detailed specifications placed in `docs/`; all WP3.1/WP4 mathematical and architectural caveats verified against source code.
- [x] **Citation Metadata:** Root [CITATION.cff](../CITATION.cff) created and schema-checked (placeholders marked for user completion before final release).
- [ ] **License Resolution (Action Required):** No `LICENSE` file exists in the repository root. Choose and commit an explicit `LICENSE` file (e.g., MIT, Apache-2.0) and align the badge/field in `README.md` and `CITATION.cff` before publishing a release.
- [x] **Test Verification:** Full test suite (`pytest tests/ -q`) verified after repository reorganization.
- [x] **Checksum Verification:** All 25 frozen artifacts verified via `python scripts/maintenance/verify_checksums_and_tests.py`.
- [ ] **Fresh Environment Installation Check:** Test `pip install -r requirements.txt` inside a clean virtual environment (without prior cached packages) on a target OS and re-run `pytest tests/ -q`.
- [ ] **Working Dashboard Check & Screenshots:** Run `streamlit run app.py` interactively, verify all 6 tabs load cleanly without console exceptions, capture real screenshots, and embed them in `README.md`.
- [ ] **Citation Author Placeholders Replaced:** Replace placeholder author/date fields in [CITATION.cff](../CITATION.cff) with real contributor details before creating tag `v1.0.0`.

---

## 2. GitHub Repository Metadata (About & Topics)

Since automated GitHub CLI (`gh`) authentication is not active in this environment, apply these manually on GitHub (**Repository Home → ⚙️ Settings gear next to About**):

- **Description (About):**
  ```text
  Privacy-aware federated intrusion detection research simulation combining differential privacy, trust-based security and blockchain auditing.
  ```
- **Topics:**
  `federated-learning`, `differential-privacy`, `intrusion-detection`, `pytorch`, `blockchain`, `cybersecurity`, `streamlit`, `machine-learning`

*(Optional: If using GitHub CLI locally once authenticated with `gh auth login`, run:)*
```bash
gh repo edit RanvyGHBs/blockchain-fl-ids \
  --description "Privacy-aware federated intrusion detection research simulation combining differential privacy, trust-based security and blockchain auditing." \
  --add-topic federated-learning,differential-privacy,intrusion-detection,pytorch,blockchain,cybersecurity,streamlit,machine-learning
```

---

## 3. Release (`v1.0.0`) Preparation Steps

Once the branch is committed, clean-environment tests pass, real screenshots are attached, author metadata in `CITATION.cff` is filled in, and a root `LICENSE` file is committed:

1. Commit and push the cleanup branch for review/merge into `main`:
   ```bash
   git add -A
   git commit -m "chore: reorganize repository and refresh technical documentation"
   ```
2. After merging to `main`, create an annotated release tag locally and push when ready:
   ```bash
   git tag -a v1.0.0 -m "v1.0.0 - Completed NSL-KDD Federated IDS Research Simulation"
   git push origin v1.0.0
   ```
3. Publish a GitHub Release attached to `v1.0.0` summarizing the five-client simulation platform, calibrated WP3/WP3.1 trust engine, 218 passing tests, and 25 frozen SHA-256 research artifacts.
