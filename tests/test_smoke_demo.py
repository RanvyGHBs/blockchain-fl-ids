"""
Lightweight CPU Smoke Demo Verification Tests.

Verifies scripts/run_live_demo.py --smoke executes real FL/DP/Trust/Blockchain/RDP
components on deterministic synthetic CPU data without downloading NSL-KDD or
mutating any frozen artifacts.
"""

import subprocess
import sys
from unittest import mock

from scripts.run_live_demo import run_demo


def test_smoke_demo_runs_offline_without_nsl_kdd():
    """Verify --smoke exercises the real pipeline while never calling NSLKDDLoader."""
    with mock.patch(
        "src.data.nsl_kdd.NSLKDDLoader.preprocess_isolated",
        side_effect=AssertionError("Smoke mode must not load NSL-KDD"),
    ):
        exit_code, results = run_demo(smoke=True)

    assert exit_code == 0
    assert results["chain_valid"] is True
    assert results["execution_mode"] == "RESEARCH_SIMULATION"
    assert results["dataset"] == "synthetic_smoke"
    assert len(results["round_history"]) == 3  # Round 0 baseline + 2 rounds


def test_smoke_demo_cli_entrypoint():
    """Verify python scripts/run_live_demo.py --smoke exits 0 cleanly."""
    proc = subprocess.run(
        [sys.executable, "scripts/run_live_demo.py", "--smoke"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "SMOKE TEST: PASSED" in proc.stdout
    assert "Blockchain Integrity Verified: True" in proc.stdout
