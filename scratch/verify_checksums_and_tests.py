import os
import sys
import hashlib
import subprocess

EXPECTED_HASHES = {
    "data/processed/stage2_results.json": "B207FBEEC955AF68199A8D6471D3E9BEE47A3D8518D46B77E8C85946885EB82F",
    "data/processed/stage2d/multi_attack_benchmarks.json": "115FCD137BE6DFA510A36C66A09C31568A53684199831B5C96FED96D52793338",
    "data/processed/stage2d/multi_attack_benchmarks_v2.json": "CB57F33D6D332DBD80C90636CC9CF68DB663A85CF0227387804D116F58B001D2",
    "data/processed/stage2d/multi_attack_benchmarks_v3.json": "BD8A2DA609CE07CD72888012C86F10E648DBF05ACE76AFADD274440E7835F5C5",
    "data/processed/stage2e/wp1/per_seed_runs.json": "33A29F4402BDA1319B252E21954EC8DD223F3C720E51E6E0BE5189B40D5963A2",
    "data/processed/stage2e/wp1/benchmark_summary.json": "292238F69926E2829DB3471650195F9CEFD6913212023B6B40B27424AA718FEA",
    "data/processed/stage2e/wp1/benchmark_summary_v2.json": "94D9E2DBD3A477D6164B0DFE4F6323BFEC1DF72F99671A737D51A7EB6C3C5C46",
    "data/processed/stage2e/wp4/overhead_summary.json": "E801E634AF9B2BF1B692B00E0EC2E4906D8A59D692C4690985EC563AA6B6F841",
    "data/processed/stage2e/wp4/overhead_summary_v2.json": "FE9F3CBB0C00694C0C0EC1663D017AC28CD78859155DEB059AEC4B48CB8B088F",
    "reports/STAGE_2E_3_WP1_MULTI_SEED_BASELINE_REPORT.md": "AC09CF541A171D8809F51574B8F869CED205173DCECD449F765BF4CFE7DB9F85",
    "reports/STAGE_2E_3_WP4_OVERHEAD_AND_AUDIT_REPORT.md": "0E0E151066BC9C335E62A4F0A6AD757A94106D52D6258201EEA57567C041B4BB",
    "reports/STAGE_2E_3_IMPLEMENTATION_COMPLETION_REPORT.md": "CBF01E18FAED53E87FD7BDD0EC46D7AE200015E8D61A2B4158AE87E9CEB2834E",
    "reports/STAGE_2E_3_1_WP1_STATISTICAL_CORRECTION_REPORT.md": "935F208FBEEE050B0AB4146B434C38CD4963D77DC9014214E669CD33CBC55550",
    "reports/STAGE_2E_3_1_WP4_OVERHEAD_AND_AUDIT_CORRECTION_REPORT.md": "84A791E52672D9080A95F22F2E36A280D0AF691954C0051F162FCECEF02526C8",
    "reports/STAGE_2E_3_1_FINAL_AUDIT_REPORT.md": "97071B211AD3712377EB81B7BC19DF3390984C297B89FA456C1BB2698CEE27C2",
    "tests/test_stage2e_3_1_corrections.py": "D0581F1679CB736AFF01D2F637343B8C49A775622EA6C9408334FB99B37F130E",
}

print("=== VERIFYING SHA-256 CHECKSUMS ===")
all_match = True
for rel_path, expected in EXPECTED_HASHES.items():
    if not os.path.exists(rel_path):
        print(f"MISSING: {rel_path}")
        all_match = False
        continue
    with open(rel_path, "rb") as f:
        actual = hashlib.sha256(f.read()).hexdigest().upper()
    if actual == expected:
        print(f"MATCH: {rel_path}")
    else:
        print(f"MISMATCH: {rel_path} (Expected {expected}, Got {actual})")
        all_match = False

if all_match:
    print("\nALL 16 HISTORICAL ARTIFACTS VERIFIED IDENTICAL BIT-FOR-BIT!")
else:
    print("\nERROR: CHECKSUM MISMATCH FOUND!")
    sys.exit(1)

print("\n=== RUNNING FULL PYTEST SUITE ===")
res = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"], capture_output=True, text=True)
print(res.stdout)
if res.stderr:
    print(res.stderr)
sys.exit(res.returncode)
