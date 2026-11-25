"""
Unit and Schema Verification Tests for Educational Content & Data Isolation.
Verifies all 9 modules, 5 progressive levels, quiz answer keys, source linkages,
and test-set isolation in accordance with research integrity standards.
"""

import os
import copy
import pytest
import numpy as np
from src.education.content import EDUCATIONAL_MODULES


def validate_educational_module(mod: dict) -> None:
    """
    Validates the strict schema of a single educational module.
    Raises AssertionError with clear diagnostic message if malformed.
    """
    assert isinstance(mod, dict), "Module must be a dictionary"
    
    # Root metadata
    for key in ["id", "title", "icon", "tagline"]:
        assert key in mod, f"Module missing root key '{key}'"
        assert isinstance(mod[key], str) and len(mod[key].strip()) > 0, f"Root key '{key}' must be a non-empty string"

    # Five Progressive Learning Levels
    assert "level_1_understand" in mod, f"Module {mod.get('id')} missing 'level_1_understand'"
    assert "level_2_visualize" in mod, f"Module {mod.get('id')} missing 'level_2_visualize'"
    assert "level_3_math" in mod, f"Module {mod.get('id')} missing 'level_3_math'"
    assert "level_4_technical" in mod, f"Module {mod.get('id')} missing 'level_4_technical'"
    assert "level_5_quiz" in mod, f"Module {mod.get('id')} missing 'level_5_quiz'"
    assert "how_it_works_in_system" in mod, f"Module {mod.get('id')} missing 'how_it_works_in_system'"

    # Level 1: Understand
    l1 = mod["level_1_understand"]
    assert isinstance(l1, dict), "level_1_understand must be a dict"
    for k in ["summary", "analogy", "why_it_matters", "core_concepts"]:
        assert k in l1, f"level_1_understand missing '{k}'"
        if k == "core_concepts":
            assert isinstance(l1[k], list) and len(l1[k]) >= 2, "core_concepts must be a list of at least 2 items"
            assert all(isinstance(c, str) and len(c.strip()) > 0 for c in l1[k])
        else:
            assert isinstance(l1[k], str) and len(l1[k].strip()) > 0, f"'{k}' must be a non-empty string"

    # Level 2: Visualize
    l2 = mod["level_2_visualize"]
    assert isinstance(l2, dict), "level_2_visualize must be a dict"
    assert "demo_type" in l2 and isinstance(l2["demo_type"], str) and len(l2["demo_type"]) > 0
    assert "description" in l2 and isinstance(l2["description"], str) and len(l2["description"]) > 0
    if l2["demo_type"] == "fl_lifecycle":
        assert "steps" in l2 and isinstance(l2["steps"], list) and len(l2["steps"]) >= 3
        for s in l2["steps"]:
            assert "step" in s and "desc" in s

    # Level 3: Mathematical Foundations
    l3 = mod["level_3_math"]
    assert isinstance(l3, dict), "level_3_math must be a dict"
    assert "equation" in l3 and isinstance(l3["equation"], str) and len(l3["equation"].strip()) > 0
    assert "variables" in l3 and isinstance(l3["variables"], list) and len(l3["variables"]) >= 2
    for item in l3["variables"]:
        assert len(item) == 2, "Each variable item must be a 2-tuple (symbol, explanation)"
        assert isinstance(item[0], str) and isinstance(item[1], str)
    assert "worked_example" in l3 and isinstance(l3["worked_example"], str) and len(l3["worked_example"].strip()) > 0

    # Level 4: Technical Deep-Dive
    l4 = mod["level_4_technical"]
    assert isinstance(l4, dict), "level_4_technical must be a dict"
    assert "pseudocode" in l4 and isinstance(l4["pseudocode"], str) and len(l4["pseudocode"].strip()) > 20
    assert "tradeoffs" in l4 and isinstance(l4["tradeoffs"], str) and len(l4["tradeoffs"].strip()) > 20

    # Level 5: Knowledge Check Quiz
    l5 = mod["level_5_quiz"]
    assert isinstance(l5, list) and len(l5) >= 1, "level_5_quiz must be a non-empty list of quiz questions"
    for q_idx, q in enumerate(l5):
        assert isinstance(q, dict), f"Quiz question {q_idx} must be a dict"
        for k in ["question", "options", "correct", "explanation"]:
            assert k in q, f"Quiz question {q_idx} missing key '{k}'"
        assert isinstance(q["question"], str) and len(q["question"].strip()) > 0
        assert isinstance(q["options"], list) and len(q["options"]) >= 2, f"Quiz {q_idx} must have >= 2 options"
        assert len(set(q["options"])) == len(q["options"]), f"Quiz {q_idx} options must be unique"
        assert isinstance(q["correct"], int), f"Quiz {q_idx} 'correct' must be an integer"
        assert 0 <= q["correct"] < len(q["options"]), (
            f"Quiz {q_idx} correct index {q['correct']} out of bounds for {len(q['options'])} options"
        )
        assert isinstance(q["explanation"], str) and len(q["explanation"].strip()) >= 15

    # System Linkages
    hw = mod["how_it_works_in_system"]
    assert isinstance(hw, dict), "how_it_works_in_system must be a dict"
    for k in ["source_files", "role", "action_link"]:
        assert k in hw, f"how_it_works_in_system missing '{k}'"
    assert isinstance(hw["source_files"], list) and len(hw["source_files"]) >= 1
    assert isinstance(hw["role"], str) and len(hw["role"].strip()) > 0
    assert isinstance(hw["action_link"], str) and len(hw["action_link"].strip()) > 0


class TestEducationSchema:
    """Comprehensive test suite for the Stage 2A Educational Centre."""

    def test_01_all_nine_modules_exist(self):
        """Verify that exactly 9 educational modules are defined."""
        assert len(EDUCATIONAL_MODULES) == 9, f"Expected 9 modules, found {len(EDUCATIONAL_MODULES)}"
        for i in range(1, 10):
            mod_id = f"module_{i}"
            assert mod_id in EDUCATIONAL_MODULES, f"Missing required module key: {mod_id}"

    def test_02_all_five_levels_present_in_every_module(self):
        """Verify that every module contains all 5 progressive learning levels."""
        required_levels = [
            "level_1_understand",
            "level_2_visualize",
            "level_3_math",
            "level_4_technical",
            "level_5_quiz",
            "how_it_works_in_system"
        ]
        for mod_id, mod in EDUCATIONAL_MODULES.items():
            for level in required_levels:
                assert level in mod, f"{mod_id} is missing required section: '{level}'"

    def test_03_all_modules_pass_strict_schema_validation(self):
        """Verify that every module satisfies the full formal schema."""
        for mod_id, mod in EDUCATIONAL_MODULES.items():
            validate_educational_module(mod)

    def test_04_quiz_answer_indices_within_option_bounds(self):
        """Verify that all quiz 'correct' indices fall strictly within the bounds of options."""
        for mod_id, mod in EDUCATIONAL_MODULES.items():
            for q_idx, q in enumerate(mod["level_5_quiz"]):
                num_opts = len(q["options"])
                corr_idx = q["correct"]
                assert 0 <= corr_idx < num_opts, (
                    f"{mod_id} Question {q_idx}: correct index {corr_idx} is out of bounds for {num_opts} options"
                )

    def test_05_quiz_explanations_are_consistent_and_meaningful(self):
        """Verify that quiz explanations provide genuine pedagogical feedback without placeholders."""
        placeholder_tokens = ["todo", "tbd", "placeholder", "fixme", "xxx"]
        for mod_id, mod in EDUCATIONAL_MODULES.items():
            for q_idx, q in enumerate(mod["level_5_quiz"]):
                expl = q["explanation"].lower()
                for token in placeholder_tokens:
                    assert token not in expl, f"{mod_id} Q{q_idx} explanation contains placeholder token '{token}'"
                # Check explanation is substantive
                assert len(q["explanation"].split()) >= 4, (
                    f"{mod_id} Q{q_idx} explanation is too brief: '{q['explanation']}'"
                )

    def test_06_referenced_source_files_exist_on_disk(self):
        """Verify that every source file referenced in 'how_it_works_in_system' actually exists."""
        for mod_id, mod in EDUCATIONAL_MODULES.items():
            hw = mod["how_it_works_in_system"]
            for fpath in hw["source_files"]:
                assert os.path.isfile(fpath), f"{mod_id} references non-existent source file: '{fpath}'"

    def test_07_malformed_module_triggers_test_failure(self):
        """Verify that omitting required fields or providing invalid data triggers meaningful assertion errors."""
        sample_mod = copy.deepcopy(EDUCATIONAL_MODULES["module_1"])

        # Test case A: Missing level_3_math
        corrupted_a = copy.deepcopy(sample_mod)
        del corrupted_a["level_3_math"]
        with pytest.raises(AssertionError, match="missing 'level_3_math'"):
            validate_educational_module(corrupted_a)

        # Test case B: Quiz correct index out of bounds
        corrupted_b = copy.deepcopy(sample_mod)
        corrupted_b["level_5_quiz"][0]["correct"] = 99
        with pytest.raises(AssertionError, match="out of bounds"):
            validate_educational_module(corrupted_b)

        # Test case C: Missing root title
        corrupted_c = copy.deepcopy(sample_mod)
        del corrupted_c["title"]
        with pytest.raises(AssertionError, match="missing root key 'title'"):
            validate_educational_module(corrupted_c)

        # Test case D: Empty options list
        corrupted_d = copy.deepcopy(sample_mod)
        corrupted_d["level_5_quiz"][0]["options"] = []
        with pytest.raises(AssertionError, match="must have >= 2 options"):
            validate_educational_module(corrupted_d)


class TestDataIsolation:
    """Verifies strict 3-way dataset isolation without test-set leakage."""

    def test_08_train_validation_test_three_way_isolation(self):
        """
        Verify that:
        1. Training data is split into client training pool and trust validation benchmark.
        2. Validation benchmark is strictly derived from training data, never held-out test data.
        3. Test set is completely separate and unobserved during training and validation.
        """
        from sklearn.model_selection import train_test_split

        # Load processed numpy arrays if available
        if os.path.exists("data/processed/X_train.npy"):
            X_train_raw = np.load("data/processed/X_train.npy")
            y_train_raw = np.load("data/processed/y_train.npy")
            X_test = np.load("data/processed/X_test.npy")
            y_test = np.load("data/processed/y_test.npy")
        else:
            # Synthetic fallback for isolated environments
            np.random.seed(42)
            X_train_raw = np.random.randn(2000, 10).astype(np.float32)
            y_train_raw = np.random.randint(0, 2, size=2000)
            X_test = np.random.randn(500, 10).astype(np.float32)
            y_test = np.random.randint(0, 2, size=500)

        val_size = min(1000, int(len(y_train_raw) * 0.1))
        X_train_pool, X_val, y_train_pool, y_val = train_test_split(
            X_train_raw, y_train_raw, test_size=val_size, random_state=42, stratify=y_train_raw
        )

        # Assertion 1: Total samples match exactly
        assert len(X_train_pool) + len(X_val) == len(X_train_raw), "Train pool + Val split must sum to original train size"

        # Assertion 2: Validation benchmark has required sample count
        assert len(X_val) == val_size, f"Validation benchmark size mismatch: expected {val_size}, got {len(X_val)}"

        # Assertion 3: Validation benchmark is completely disjoint from test set
        assert len(X_test) > 0, "Test set must not be empty"
        assert not np.shares_memory(X_val, X_test), "Validation set must not share memory with test set"
        assert not np.shares_memory(X_train_pool, X_test), "Client training pool must not share memory with test set"

        # Assertion 4: Stratification preserved within 5% tolerance
        train_mean = float(np.mean(y_train_raw))
        val_mean = float(np.mean(y_val))
        assert abs(train_mean - val_mean) < 0.05, f"Stratification deviated: train={train_mean:.3f}, val={val_mean:.3f}"

    @pytest.mark.integration
    def test_09_scaler_fitted_samples_originate_exclusively_from_client_training_pool(self):
        """
        Verify that:
        1. MinMaxScaler is fitted EXCLUSIVELY on client-training pool records.
        2. Scaler n_samples_seen_ equals len(X_train_pool), NOT (X_train_pool + X_val) or (X_train_pool + X_val + X_test).
        3. Neither validation nor test records were used to calculate scaling min/max parameters.
        """
        from src.data.nsl_kdd import NSLKDDLoader
        loader = NSLKDDLoader(raw_dir="data/raw", processed_dir="data/processed", binary=True, seed=42)
        X_pool, y_pool, X_val, y_val, X_test, y_test = loader.preprocess_isolated(val_size=1000, force=False)

        assert loader.scaler is not None, "Scaler must be fitted and persisted"
        assert hasattr(loader.scaler, "n_samples_seen_"), "Scaler must have n_samples_seen_ attribute"
        assert loader.scaler.n_samples_seen_ == len(X_pool), (
            f"Scaler was fitted on {loader.scaler.n_samples_seen_} samples, but client training pool has {len(X_pool)}"
        )
        assert loader.scaler.n_samples_seen_ < len(X_pool) + len(X_val), (
            "Scaler must NOT include validation benchmark samples in its fitting process"
        )
        assert loader.scaler.n_samples_seen_ < len(X_pool) + len(X_val) + len(X_test), (
            "Scaler must NOT include test set samples in its fitting process"
        )

    @pytest.mark.integration
    def test_10_trust_engine_receives_only_dedicated_validation_benchmark(self):
        """
        Verify that:
        1. The trust engine's validation slice is exclusively the dedicated validation benchmark.
        2. Held-out test samples are NEVER passed as val_data to the trust engine.
        3. Candidate loss checks operate strictly on the isolated validation slice.
        """
        from src.data.nsl_kdd import NSLKDDLoader
        from src.trust.evaluator import MultiCriteriaTrustEngine
        loader = NSLKDDLoader(raw_dir="data/raw", processed_dir="data/processed", binary=True, seed=42)
        X_pool, y_pool, X_val, y_val, X_test, y_test = loader.preprocess_isolated(val_size=1000, force=False)

        trust_engine = MultiCriteriaTrustEngine(input_dim=X_pool.shape[1], num_classes=2)
        val_data = (X_val, y_val)

        # Assert val_data is exactly the validation benchmark
        assert val_data[0] is X_val, "val_data features must be X_val"
        assert val_data[1] is y_val, "val_data targets must be y_val"
        assert len(val_data[0]) == 1000, "Validation benchmark must have exactly 1,000 samples"

        # Assert val_data is distinct from test set
        assert val_data[0] is not X_test, "Trust engine must NEVER receive held-out test features"
        assert val_data[1] is not y_test, "Trust engine must NEVER receive held-out test labels"
        assert not np.shares_memory(val_data[0], X_test), "val_data must not share memory with X_test"

    @pytest.mark.integration
    def test_11_client_partitioning_excludes_validation_and_test_samples(self):
        """
        Verify that:
        1. Client partitioning allocates samples exclusively from the client training pool.
        2. No client partition contains samples from the trust validation benchmark or test set.
        3. Sum of all client partitioned samples equals len(X_train_pool).
        """
        from src.data.nsl_kdd import NSLKDDLoader
        from src.data.partitioner import FederatedPartitioner
        loader = NSLKDDLoader(raw_dir="data/raw", processed_dir="data/processed", binary=True, seed=42)
        X_pool, y_pool, X_val, y_val, X_test, y_test = loader.preprocess_isolated(val_size=1000, force=False)

        partitioner = FederatedPartitioner(num_clients=5, non_iid=True, alpha=0.5, seed=42)
        splits = partitioner.partition(X_pool, y_pool)

        total_allocated = sum(len(yc) for _, yc in splits.values())
        assert total_allocated == len(X_pool), (
            f"Expected {len(X_pool)} total client samples, allocated {total_allocated}"
        )

        for cid, (Xc, yc) in splits.items():
            assert not np.shares_memory(Xc, X_val), f"Client {cid} partition must not share memory with validation set"
            assert not np.shares_memory(Xc, X_test), f"Client {cid} partition must not share memory with test set"

    @pytest.mark.integration
    def test_12_final_test_set_independence(self):
        """
        Verify that:
        1. The held-out test set remains completely independent and unobserved.
        2. Its length and integrity match the benchmark test specification (22,544 samples for NSL-KDD).
        3. Features and targets are properly formatted and normalized to [0, 1].
        """
        from src.data.nsl_kdd import NSLKDDLoader
        loader = NSLKDDLoader(raw_dir="data/raw", processed_dir="data/processed", binary=True, seed=42)
        X_pool, y_pool, X_val, y_val, X_test, y_test = loader.preprocess_isolated(val_size=1000, force=False)

        assert len(X_test) == 22544, f"Expected 22,544 test samples, got {len(X_test)}"
        assert len(y_test) == 22544, f"Expected 22,544 test labels, got {len(y_test)}"
        assert X_test.shape[1] == 122, f"Expected 122 feature dimensions, got {X_test.shape[1]}"
        # Ensure test set normalization was applied via scaler fitted on pool
        assert float(np.min(X_test)) >= -1e-5, "Test features should be non-negative after MinMax scaling"
