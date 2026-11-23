"""
Stage 2E.3.2 Closure Unit Tests: Serialization Size and Negative Control Diversity.

Verifies:
1. Exact parameter count, raw float32 byte count, serialized byte count, and 161-byte pickle container breakdown.
2. Exclusion of BatchNorm non-trainable buffers from model weight vector.
3. Symmetric payload representation between upstream and downstream serialization.
4. Exact negative-control trial count, single pristine ledger structure, and 0/100 false alarms.
"""

import copy
import pickle
import pickletools
import numpy as np
import pytest
import torch

from src.models.ids_net import IDSNet
from src.evaluation.overhead_profiler import OverheadProfiler
from src.blockchain.audit_verifier import SyntheticTamperSuite, AuditVerifier
from run_stage2e_wp4 import build_sample_pristine_chain


class TestSerializationByteAccounting:
    """Verifies the exact byte-level deconstruction of serialized model payloads."""

    def test_parameter_counts_and_raw_bytes(self):
        """Verify trainable parameters total 26,594 float32 elements (106,376 bytes)."""
        model = IDSNet(input_dim=122, num_classes=2)
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        assert total_params == 26594, f"Expected 26,594 parameters, got {total_params}"

        raw_param_bytes = total_params * 4  # float32 = 4 bytes
        assert raw_param_bytes == 106376, f"Expected 106,376 bytes, got {raw_param_bytes}"

    def test_batchnorm_buffers_excluded_from_weight_vector(self):
        """Verify get_weights_vector() excludes non-trainable BatchNorm buffers."""
        model = IDSNet(input_dim=122, num_classes=2)
        weights_vec = model.get_weights_vector()

        # Vector length must match trainable parameters exactly
        assert isinstance(weights_vec, np.ndarray)
        assert weights_vec.dtype == np.float32
        assert len(weights_vec) == 26594

        # Verify BatchNorm buffers exist in model but are NOT in get_weights_vector()
        buffers = dict(model.named_buffers())
        assert len(buffers) == 9  # 3 x (running_mean, running_var, num_batches_tracked)

        total_buffer_elements = sum(b.numel() for b in buffers.values())
        assert total_buffer_elements == 451  # 224 + 224 + 3

        # Parameter tensors count
        param_tensors = list(model.parameters())
        assert len(param_tensors) == 14  # 4 linear (w+b) + 3 bn (w+b) = 8 + 6 = 14

    def test_pickle_serialization_container_breakdown(self):
        """Verify the exact 161-byte pickle container overhead."""
        model = IDSNet(input_dim=122, num_classes=2)
        weights_vec = model.get_weights_vector()
        serialized = pickle.dumps(weights_vec)

        total_serialized_bytes = len(serialized)
        assert total_serialized_bytes == 106537, f"Expected 106,537 bytes, got {total_serialized_bytes}"

        raw_data_bytes = weights_vec.nbytes
        assert raw_data_bytes == 106376

        container_overhead = total_serialized_bytes - raw_data_bytes
        assert container_overhead == 161, f"Expected exactly 161 bytes overhead, got {container_overhead}"

        # Disassemble opcodes and verify presence of NumPy reconstruction & dtype metadata
        ops = list(pickletools.genops(serialized))
        op_names = [op[0].name for op in ops]

        assert "PROTO" in op_names
        assert "FRAME" in op_names
        assert "STACK_GLOBAL" in op_names
        assert "BUILD" in op_names
        assert "STOP" in op_names

        # Verify NumPy reconstruct target and dtype in opcodes
        unicode_args = [op[1] for op in ops if op[0].name == "SHORT_BINUNICODE"]
        assert "_reconstruct" in unicode_args
        assert "f4" in unicode_args

    def test_symmetric_upstream_downstream_payload(self):
        """Verify upstream update and downstream model share the identical serialized size."""
        model = IDSNet(input_dim=122, num_classes=2)
        weights_vec = model.get_weights_vector()
        serialized_downstream = pickle.dumps(weights_vec)

        # In OverheadProfiler, client update is serialized model delta or weight vector
        client_update = model.get_weights_vector()
        serialized_upstream = pickle.dumps(client_update)

        assert len(serialized_upstream) == len(serialized_downstream) == 106537


class TestNegativeControlDiversity:
    """Verifies the construction and diversity characteristics of the negative control suite."""

    def test_negative_control_execution_and_false_alarm_rate(self):
        """Verify 100 negative controls execute with 0 false alarms."""
        pristine_chain, pub_keys = build_sample_pristine_chain(num_rounds=3, num_clients=5)
        verifier = AuditVerifier(public_keys=pub_keys)
        suite = SyntheticTamperSuite(verifier=verifier)
        expected_height = len(pristine_chain.chain)

        assert expected_height == 4  # Genesis + Round 1 + Round 2 + Round 3

        # Run 100 negative trials as done in run_finite_tamper_benchmark
        false_alarms = 0
        for _ in range(100):
            cloned = copy.deepcopy(pristine_chain)
            audit = suite.verifier.verify_chain(cloned, expected_height=expected_height)
            if not audit["is_valid"]:
                false_alarms += 1

        assert false_alarms == 0, f"Expected 0 false alarms, got {false_alarms}"

    def test_negative_control_structural_diversity(self):
        """Audit the structural diversity of the 100 negative control trials.

        Quantifies that the 100 trials represent repeated checks of 1 pristine ledger
        rather than 100 diverse legitimate ledgers.
        """
        pristine_chain, _ = build_sample_pristine_chain(num_rounds=3, num_clients=5)

        # Generate trial ledgers as done in run_tamper_suite
        ledgers = [copy.deepcopy(pristine_chain) for _ in range(100)]

        # Unique ledger objects (after deepcopy, objects differ, but content is identical)
        unique_hashes = set()
        block_counts = set()
        tx_counts = set()
        index_sets = set()

        for ledger in ledgers:
            # Hash of all block hashes concatenated
            ledger_signature = tuple(b.hash for b in ledger.chain)
            unique_hashes.add(ledger_signature)
            block_counts.add(len(ledger.chain))
            total_txs = sum(len(b.transactions) for b in ledger.chain)
            tx_counts.add(total_txs)
            indices = tuple(b.index for b in ledger.chain)
            index_sets.add(indices)

        assert len(unique_hashes) == 1, "Expected 1 unique ledger signature across all 100 trials"
        assert block_counts == {4}, "Expected all trials to have block height 4"
        assert tx_counts == {15}, "Expected all trials to have 15 transactions (5 clients x 3 rounds)"
        assert index_sets == {(0, 1, 2, 3)}, "Expected identical block indices (0, 1, 2, 3)"
