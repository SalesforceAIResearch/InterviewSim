# Copyright (c) 2026 Salesforce, Inc.
# SPDX-License-Identifier: CC-BY-NC-4.0
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0
# International License. See LICENSE.txt in the repository root.

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from interviewsim import run_synthetic_demo


ROOT = Path(__file__).resolve().parents[1]
PREPARED_INPUT = (
    ROOT
    / "examples"
    / "synthetic_examples"
    / "personalities"
    / "PERSONALITY_001"
    / "prepared_input.json"
)


def test_demo_logic_runs_all_offline_components() -> None:
    summary = run_synthetic_demo(PREPARED_INPUT)

    assert summary["input"] == {
        "schema_version": "1.0",
        "personality_id": "PERSONALITY_001",
        "interviews": 5,
        "qa_pairs": 15,
    }
    assert summary["split"] == {
        "train_interviews": 4,
        "test_interviews": 1,
        "train_qa_pairs": 12,
        "test_qa_pairs": 3,
    }
    assert summary["generation"] == {
        "strategies": (
            "simple",
            "profile",
            "long_profile",
            "chronological",
            "random",
            "retrieval",
            "hybrid",
        ),
        "prompt_count": 7,
        "all_prompts_non_empty": True,
        "hybrid_k1": 2,
        "hybrid_k2": 2,
        "hybrid_profile_free": True,
    }
    assert summary["content_similarity"]["raw_mean"] == pytest.approx(4.0)
    assert summary["fact_summary"] == {
        "held_out_response_count": 3,
        "parsed": True,
        "fields": ("summary", "explanation"),
    }
    assert summary["factual_consistency"]["contradiction_ratio"] == pytest.approx(1.0 / 3.0)
    assert summary["personality_similarity"]["trait_prompt_count"] == 5
    assert summary["personality_similarity"]["alignment"] == pytest.approx(0.5)
    assert summary["mcq"]["exact_accuracy"] == pytest.approx(1.0)
    assert summary["mcq"]["batch_size"] == 2
    assert summary["mcq"]["parsed_answer_count"] == 2
    assert summary["mcq"]["mean_reward"] == pytest.approx(1.0)
    formats = summary["mcq"]["formats"]
    assert tuple(item["option_count"] for item in formats) == (3, 4)
    assert all(item["rewards"]["correct"] == 1.0 for item in formats)
    assert all(item["rewards"]["opposite_negation"] == -1.0 for item in formats)
    assert summary["permutation_test"]["exact"] is True


def test_demo_script_prints_only_the_json_summary() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_synthetic_demo.py")],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )

    output = json.loads(completed.stdout)
    assert completed.stderr == ""
    assert output["generation"]["prompt_count"] == 7
    assert output["split"]["test_interviews"] == 1
    assert "Task:" not in completed.stdout
    assert "Original question:" not in completed.stdout
