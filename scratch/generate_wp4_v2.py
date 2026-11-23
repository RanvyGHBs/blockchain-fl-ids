import json

with open("data/processed/stage2e/wp4/overhead_summary.json") as f:
    orig = json.load(f)

v2 = {
    "metadata": {
        "version": "2.0 (Audited & Methodologically Corrected)",
        "milestone": "Stage 2E.3.1",
        "description": "Computational overhead profiling and finite cryptographic audit verification with transparent communication accounting and precise architectural terminology.",
        "environment": orig["metadata"]["environment"],
        "architectural_terminology_mapping": {
            "ECDSA P-256": "Signature-based authentication and update attribution",
            "SHA-256": "Cryptographic hashing",
            "Merkle tree": "Transaction-data integrity verification",
            "Hash chain": "Tamper-evident block linkage",
            "Proof-of-Trust": "Simulated validator selection",
            "Audit verifier": "Detection of specified integrity violations",
            "Blockchain": "Locally simulated, centrally orchestrated audit ledger"
        },
        "architectural_boundaries": [
            "Framework is explicitly characterized as a tamper-evident, cryptographically verifiable local audit ledger.",
            "No claims of peer-to-peer (P2P) decentralized consensus, Proof-of-Stake/Proof-of-Work mining, or physical immutability against root filesystem compromise.",
            "A valid cryptographic signature establishes update authenticity and author attribution under the assumed key-management model; it does NOT establish that a client update is benign.",
            "A valid hash chain establishes chronological block linkage; it does NOT establish model accuracy or trustworthy training behavior."
        ]
    },
    "cryptographic_microbenchmarks": orig["cryptographic_microbenchmarks"],
    "aggregation_microbenchmarks": orig["aggregation_microbenchmarks"],
    "ledger_operation_microbenchmarks": orig["ledger_operation_microbenchmarks"],
    "communication_payload_accounting": {
        "unit_conventions": {
            "binary_kib": "1 KiB = 1,024 bytes",
            "binary_mib": "1 MiB = 1,048,576 bytes",
            "decimal_kb": "1 KB = 1,000 bytes",
            "decimal_mb": "1 MB = 1,000,000 bytes",
            "note_on_v1": "Stage 2E.3 report labeled binary kibibytes (bytes/1024) as 'KB'. Both unit systems are now explicitly reported."
        },
        "raw_component_sizes_bytes": {
            "raw_parameter_tensor_float32": orig["communication_payload_analysis"]["raw_tensor_nbytes"],
            "serialized_pickle_tensor": orig["communication_payload_analysis"]["serialized_pickle_bytes"],
            "pickle_serialization_overhead": orig["communication_payload_analysis"]["serialized_pickle_bytes"] - orig["communication_payload_analysis"]["raw_tensor_nbytes"],
            "ecdsa_p256_signature_string": orig["communication_payload_analysis"]["signature_string_bytes"],
            "client_upstream_metadata_json": 28,
            "server_downstream_metadata_json": 42,
            "transaction_record_json": orig["communication_payload_analysis"]["transaction_json_bytes"],
            "round_block_json_5tx": orig["communication_payload_analysis"]["block_json_bytes_5tx"]
        },
        "transmission_streams": {
            "client_upstream_per_client_bytes": 106661,
            "client_upstream_per_client_kib": 106661 / 1024.0,
            "client_upstream_per_client_kb": 106661 / 1000.0,
            "server_downstream_per_client_bytes": 106579,
            "server_downstream_per_client_kib": 106579 / 1024.0,
            "server_downstream_per_client_kb": 106579 / 1000.0,
            "aggregate_upstream_5_clients_bytes": 106661 * 5,
            "aggregate_upstream_5_clients_kib": (106661 * 5) / 1024.0,
            "aggregate_upstream_5_clients_kb": (106661 * 5) / 1000.0,
            "aggregate_downstream_unicast_5_clients_bytes": 106579 * 5,
            "aggregate_downstream_unicast_5_clients_kib": (106579 * 5) / 1024.0,
            "aggregate_downstream_unicast_5_clients_kb": (106579 * 5) / 1000.0,
            "aggregate_downstream_multicast_single_broadcast_bytes": 106579,
            "aggregate_downstream_multicast_single_broadcast_kib": 106579 / 1024.0,
            "aggregate_downstream_multicast_single_broadcast_kb": 106579 / 1000.0
        },
        "total_round_bandwidth_models": {
            "modeled_unicast_network": {
                "description": "Assumes server sends 5 individual unicast transmissions of global weights to 5 clients. Matches the original Stage 2E.3 1,041.21 KiB total.",
                "total_bytes": 1066200,
                "total_kib": 1066200 / 1024.0,
                "total_mib": 1066200 / (1024.0 * 1024.0),
                "total_kb": 1066200 / 1000.0,
                "total_mb": 1066200 / 1000000.0
            },
            "modeled_multicast_network": {
                "description": "Assumes server sends single broadcast/multicast of global weights received by all 5 clients.",
                "total_bytes": (106661 * 5) + 106579,
                "total_kib": ((106661 * 5) + 106579) / 1024.0,
                "total_mib": ((106661 * 5) + 106579) / (1024.0 * 1024.0),
                "total_kb": ((106661 * 5) + 106579) / 1000.0,
                "total_mb": ((106661 * 5) + 106579) / 1000000.0
            }
        },
        "exclusions_from_round_bandwidth": [
            "Block distribution across an external peer-to-peer network is excluded; ledger maintenance is simulated locally on the coordinator/validator.",
            "Raw network packet headers (TCP/IP/Ethernet framing) are excluded; measurements reflect application-layer serialized payloads."
        ]
    },
    "tampering_verification_benchmark": {
        "summary": {
            "total_positive_tested": 500,
            "total_positive_detected": 500,
            "observed_detection_rate": 1.0,
            "observed_detection_rate_pct": "100.00%",
            "detection_statement": "500/500 synthetic tampering trials were detected on this finite test suite.",
            "total_negative_tested": 100,
            "total_false_alarms": 0,
            "observed_false_alarm_rate": 0.0,
            "observed_false_alarm_rate_pct": "0.00%",
            "false_alarm_statement": "0/100 false alarms across the tested legitimate controls.",
            "mean_pristine_audit_latency_ms": orig["tampering_verification_benchmark"]["mean_pristine_audit_latency_ms"]
        },
        "per_category_breakdown": orig["tampering_verification_benchmark"]["per_category_results"],
        "experimental_diversity_and_limitations": {
            "pristine_ledger_dimensions": "4 blocks (Genesis + 3 rounds), 15 total client transactions.",
            "diversity_mechanisms": "Target block indices, transaction targets, and pseudo-random seed offsets varied deterministically across trials.",
            "limitations": [
                "Evaluates in-memory synthetic mutations on Python ledger objects, not raw serialized disk byte corruptions.",
                "Does not evaluate network packet drops, bit-level TCP transmission corruptions, or coordinator fork/equivocation attacks.",
                "Legitimate negative controls evaluated deep copies of the 4-block ledger instance rather than variable-length or high-volume ledgers.",
                "Results constitute empirical observations on a finite test suite and must not be interpreted as universal mathematical guarantees."
            ]
        }
    }
}

with open("data/processed/stage2e/wp4/overhead_summary_v2.json", "w") as f:
    json.dump(v2, f, indent=2)

print("Generated overhead_summary_v2.json successfully.")
