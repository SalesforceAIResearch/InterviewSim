# Copyright (c) 2026 Salesforce, Inc.
# SPDX-License-Identifier: CC-BY-NC-4.0
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0
# International License. See LICENSE.txt in the repository root.

from __future__ import annotations

import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

fixture_generator = importlib.import_module("scripts.generate_synthetic_sample")
GENERATOR = ROOT / "scripts" / "generate_synthetic_sample.py"


def run_generator(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GENERATOR), *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.mark.parametrize(
    "protected_directory",
    ["src", "docs", "tests", "scripts"],
)
def test_generator_refuses_other_repository_directories(
    protected_directory: str,
) -> None:
    marker = ROOT / protected_directory
    completed = run_generator("--output", protected_directory, "--force")

    assert completed.returncode != 0
    assert marker.exists()
    assert "must be examples/synthetic_examples" in completed.stderr


def test_generator_refuses_default_overwrite_without_force() -> None:
    completed = run_generator()

    assert completed.returncode != 0
    assert (ROOT / "examples" / "synthetic_examples" / "manifest.json").is_file()
    assert "pass --force" in completed.stderr


def test_generator_supports_guarded_external_output(tmp_path: Path) -> None:
    output = tmp_path / "fixture"

    first = run_generator("--output", str(output))
    second = run_generator("--output", str(output), "--force")

    assert first.returncode == 0
    assert second.returncode == 0
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    prepared = json.loads(
        (output / "personalities" / "PERSONALITY_010" / "prepared_input.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["fixture_id"] == "SYNTHETIC_EXAMPLES"
    assert len(prepared["interviews"]) == 5
    assert all(len(item["qa_pairs"]) == 3 for item in prepared["interviews"])
    assert not (output / "entity_registry.json").exists()


def test_fixture_documents_are_deterministic() -> None:
    first = fixture_generator.build_fixture_documents()
    second = fixture_generator.build_fixture_documents()

    assert first == second
    assert {fixture_generator.serialize(document) for document in first.values()} == {
        fixture_generator.serialize(document) for document in second.values()
    }


def test_canonical_questions_and_responses_are_natural_and_opaque() -> None:
    documents = fixture_generator.build_fixture_documents()
    questions: set[str] = set()
    roles: set[str] = set()

    for ordinal in range(1, 11):
        pid = f"PERSONALITY_{ordinal:03d}"
        prepared = documents[f"personalities/{pid}/prepared_input.json"]
        roles.add(prepared["personality"]["profile"])
        pairs = [pair for interview in prepared["interviews"] for pair in interview["qa_pairs"]]
        assert len(pairs) == 15
        for pair in pairs:
            assert "PERSONALITY_" not in pair["question"]
            assert "PERSONALITY_" not in pair["response"]
            assert pair["question"].endswith(("?", "."))
            assert len(pair["response"].split()) >= 8
            assert 2 <= sum(pair["response"].count(mark) for mark in ".!?") <= 4
            questions.add(pair["question"])

    assert len(roles) == 10
    assert len(questions) == 150


def test_latest_interview_is_the_only_holdout() -> None:
    documents = fixture_generator.build_fixture_documents()

    for ordinal in range(1, 11):
        pid = f"PERSONALITY_{ordinal:03d}"
        split = documents[f"personalities/{pid}/split.json"]
        assert split["train_sequences"] == [1, 2, 3, 4]
        assert split["test_sequences"] == [5]
        assert split["counts"] == {
            "train_interviews": 4,
            "test_interviews": 1,
            "train_qas": 12,
            "test_qas": 3,
        }


def test_mcq_distractors_are_readable_semantic_alternatives() -> None:
    documents = fixture_generator.build_fixture_documents()

    for ordinal in range(1, 11):
        pid = f"PERSONALITY_{ordinal:03d}"
        collection = documents[f"personalities/{pid}/mcqs_4_option.json"]
        for mcq in collection["mcqs"]:
            options = mcq["options"]
            assert {option["kind"] for option in options} == set(fixture_generator.OPTION_KINDS)
            assert len({option["text"] for option in options}) == 4
            assert all(len(option["text"].split()) >= 10 for option in options)
            assert all("PERSONALITY_" not in option["text"] for option in options)


def test_manifest_contains_profile_registry_without_entity_file() -> None:
    documents = fixture_generator.build_fixture_documents()
    manifest = documents["manifest.json"]

    assert "entity_registry.json" not in documents
    assert len(manifest["profile_registry"]) == 10
    assert all(entry["allowed_tags"] for entry in manifest["profile_registry"])
