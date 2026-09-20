# Copyright (c) 2026 Salesforce, Inc.
# SPDX-License-Identifier: CC-BY-NC-4.0
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0
# International License. See LICENSE.txt in the repository root.

from __future__ import annotations

import json
from pathlib import Path

import pytest

from interviewsim import (
    SchemaValidationError,
    load_prepared_interviews,
    loads_prepared_interviews,
    qa_pairs_from_interviews,
    temporal_train_test_split,
)


def _payload(count: int = 10) -> dict[str, object]:
    interviews = [
        {
            "interview_id": f"i_{index:03d}",
            "sequence": index,
            "qa_pairs": [
                {
                    "qa_id": f"q_{index:03d}",
                    "question": f"tok_question_{index:03d}",
                    "response": f"tok_response_{index:03d}",
                    "tags": [f"tok_tag_{index:03d}"],
                }
            ],
        }
        for index in range(count)
    ]
    return {
        "schema_version": "1.0",
        "personality_id": "p_001",
        "personality": {
            "profile": "tok_profile_short",
            "long_profile": "tok_profile_long",
        },
        "interviews": list(reversed(interviews)),
    }


def test_loads_synthetic_ten_contract() -> None:
    data = loads_prepared_interviews(json.dumps(_payload()))

    assert data.schema_version == "1.0"
    assert data.personality_id == "p_001"
    assert data.personality.long_profile == "tok_profile_long"
    assert len(data.interviews) == 10
    assert data.interviews[0].qa_pairs[0].tags == ("tok_tag_009",)


def test_loads_from_local_path(tmp_path: Path) -> None:
    path = tmp_path / "prepared_input.json"
    path.write_text(json.dumps(_payload()), encoding="utf-8")

    assert load_prepared_interviews(path).schema_version == "1.0"


def test_schema_rejects_unknown_fields_and_duplicate_sequences() -> None:
    payload = _payload()
    payload["tok_unknown"] = "tok_value"
    with pytest.raises(SchemaValidationError, match="unknown field"):
        loads_prepared_interviews(json.dumps(payload))

    payload = _payload()
    interviews = payload["interviews"]
    assert isinstance(interviews, list)
    interviews[0]["sequence"] = interviews[1]["sequence"]
    with pytest.raises(SchemaValidationError, match="sequence values must be unique"):
        loads_prepared_interviews(json.dumps(payload))


def test_schema_requires_all_qa_pair_fields() -> None:
    payload = _payload()
    interviews = payload["interviews"]
    assert isinstance(interviews, list)
    del interviews[0]["qa_pairs"][0]["tags"]

    with pytest.raises(SchemaValidationError, match="missing required field 'tags'"):
        loads_prepared_interviews(json.dumps(payload))


def test_temporal_split_holds_out_latest_twenty_percent_interviews() -> None:
    data = loads_prepared_interviews(json.dumps(_payload()))

    split = temporal_train_test_split(data.interviews)

    assert tuple(interview.sequence for interview in split.train) == tuple(range(8))
    assert tuple(interview.sequence for interview in split.test) == (8, 9)
    assert tuple(qa_pair.qa_id for qa_pair in qa_pairs_from_interviews(split.train)) == (
        *(f"q_{index:03d}" for index in range(8)),
    )


def test_temporal_split_uses_ceiling() -> None:
    data = loads_prepared_interviews(json.dumps(_payload(6)))

    split = temporal_train_test_split(data.interviews)

    assert len(split.train) == 4
    assert len(split.test) == 2
