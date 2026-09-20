# Copyright (c) 2026 Salesforce, Inc.
# SPDX-License-Identifier: CC-BY-NC-4.0
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0
# International License. See LICENSE.txt in the repository root.

"""Typed validation for one prepared input file per personality.

The accepted root contains ``schema_version``, ``personality_id``,
``personality``, and ``interviews``. Each interview has an explicit sequence
and prepared question-response pairs. Unknown fields are rejected.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


class SchemaValidationError(ValueError):
    """Raised when prepared interview data does not match the public schema."""

    def __init__(self, path: str, message: str) -> None:
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}")


def _validate_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    if "\x00" in value:
        raise ValueError(f"{field_name} must not contain null characters")
    return value


@dataclass(frozen=True, slots=True)
class Personality:
    """Short and long public profile text."""

    profile: str
    long_profile: str

    def __post_init__(self) -> None:
        _validate_text(self.profile, "profile")
        _validate_text(self.long_profile, "long_profile")


@dataclass(frozen=True, slots=True)
class QAPair:
    """One prepared question-response pair."""

    qa_id: str
    question: str
    response: str
    tags: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_text(self.qa_id, "qa_id")
        _validate_text(self.question, "question")
        _validate_text(self.response, "response")
        if not isinstance(self.tags, tuple):
            raise TypeError("tags must be a tuple")
        if len(set(self.tags)) != len(self.tags):
            raise ValueError("tags must not contain duplicates")
        for tag in self.tags:
            _validate_text(tag, "tag")


@dataclass(frozen=True, slots=True)
class Interview:
    """A sequence-addressable group of prepared question-response pairs."""

    interview_id: str
    sequence: int
    qa_pairs: tuple[QAPair, ...]

    def __post_init__(self) -> None:
        _validate_text(self.interview_id, "interview_id")
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int):
            raise TypeError("sequence must be an integer")
        if self.sequence < 0:
            raise ValueError("sequence must not be negative")
        if not isinstance(self.qa_pairs, tuple):
            raise TypeError("qa_pairs must be a tuple")
        if not self.qa_pairs:
            raise ValueError("qa_pairs must not be empty")
        if any(not isinstance(qa_pair, QAPair) for qa_pair in self.qa_pairs):
            raise TypeError("qa_pairs must contain QAPair values")
        qa_ids = [qa_pair.qa_id for qa_pair in self.qa_pairs]
        if len(set(qa_ids)) != len(qa_ids):
            raise ValueError("qa_id values must be unique within an interview")


@dataclass(frozen=True, slots=True)
class PreparedInterviewData:
    """Validated prepared input for one personality."""

    schema_version: str
    personality_id: str
    personality: Personality
    interviews: tuple[Interview, ...]

    def __post_init__(self) -> None:
        _validate_text(self.schema_version, "schema_version")
        _validate_text(self.personality_id, "personality_id")
        if not isinstance(self.personality, Personality):
            raise TypeError("personality must be a Personality")
        if not isinstance(self.interviews, tuple):
            raise TypeError("interviews must be a tuple")
        if not self.interviews:
            raise ValueError("interviews must not be empty")
        if any(not isinstance(interview, Interview) for interview in self.interviews):
            raise TypeError("interviews must contain Interview values")
        interview_ids = [interview.interview_id for interview in self.interviews]
        sequences = [interview.sequence for interview in self.interviews]
        qa_ids = [qa_pair.qa_id for interview in self.interviews for qa_pair in interview.qa_pairs]
        if len(set(interview_ids)) != len(interview_ids):
            raise ValueError("interview_id values must be unique")
        if len(set(sequences)) != len(sequences):
            raise ValueError("sequence values must be unique")
        if len(set(qa_ids)) != len(qa_ids):
            raise ValueError("qa_id values must be unique")


def _object(value: object, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(path, "expected an object")
    if not all(isinstance(key, str) for key in value):
        raise SchemaValidationError(path, "object keys must be strings")
    return value


def _array(value: object, path: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise SchemaValidationError(path, "expected an array")
    return value


def _fields(
    value: Mapping[str, Any],
    path: str,
    *,
    required: set[str],
) -> None:
    missing = required - value.keys()
    if missing:
        raise SchemaValidationError(path, f"missing required field {sorted(missing)[0]!r}")
    unknown = value.keys() - required
    if unknown:
        raise SchemaValidationError(path, f"unknown field {sorted(unknown)[0]!r}")


def _text(value: object, path: str) -> str:
    try:
        return _validate_text(value, path.rsplit(".", 1)[-1])
    except ValueError as error:
        raise SchemaValidationError(path, str(error)) from error


def _integer(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemaValidationError(path, "expected an integer")
    if value < 0:
        raise SchemaValidationError(path, "must not be negative")
    return value


def _parse_personality(value: object, path: str) -> Personality:
    item = _object(value, path)
    _fields(item, path, required={"profile", "long_profile"})
    return Personality(
        profile=_text(item["profile"], f"{path}.profile"),
        long_profile=_text(item["long_profile"], f"{path}.long_profile"),
    )


def _parse_qa_pair(value: object, path: str) -> QAPair:
    item = _object(value, path)
    _fields(
        item,
        path,
        required={"qa_id", "question", "response", "tags"},
    )
    raw_tags = _array(item["tags"], f"{path}.tags")
    tags = tuple(_text(tag, f"{path}.tags[{index}]") for index, tag in enumerate(raw_tags))
    if len(set(tags)) != len(tags):
        raise SchemaValidationError(f"{path}.tags", "values must be unique")
    return QAPair(
        qa_id=_text(item["qa_id"], f"{path}.qa_id"),
        question=_text(item["question"], f"{path}.question"),
        response=_text(item["response"], f"{path}.response"),
        tags=tags,
    )


def _parse_interview(value: object, path: str) -> Interview:
    item = _object(value, path)
    _fields(
        item,
        path,
        required={"interview_id", "sequence", "qa_pairs"},
    )
    raw_qa_pairs = _array(item["qa_pairs"], f"{path}.qa_pairs")
    if not raw_qa_pairs:
        raise SchemaValidationError(f"{path}.qa_pairs", "must not be empty")
    qa_pairs = tuple(
        _parse_qa_pair(qa_pair, f"{path}.qa_pairs[{index}]")
        for index, qa_pair in enumerate(raw_qa_pairs)
    )
    qa_ids = [qa_pair.qa_id for qa_pair in qa_pairs]
    if len(set(qa_ids)) != len(qa_ids):
        raise SchemaValidationError(f"{path}.qa_pairs", "qa_id values must be unique")
    return Interview(
        interview_id=_text(item["interview_id"], f"{path}.interview_id"),
        sequence=_integer(item["sequence"], f"{path}.sequence"),
        qa_pairs=qa_pairs,
    )


def parse_prepared_interviews(value: object) -> PreparedInterviewData:
    """Validate a decoded prepared input object."""

    root = _object(value, "$")
    _fields(
        root,
        "$",
        required={"schema_version", "personality_id", "personality", "interviews"},
    )
    raw_interviews = _array(root["interviews"], "$.interviews")
    if not raw_interviews:
        raise SchemaValidationError("$.interviews", "must not be empty")
    interviews = tuple(
        _parse_interview(interview, f"$.interviews[{index}]")
        for index, interview in enumerate(raw_interviews)
    )
    interview_ids = [interview.interview_id for interview in interviews]
    sequences = [interview.sequence for interview in interviews]
    qa_ids = [qa_pair.qa_id for interview in interviews for qa_pair in interview.qa_pairs]
    if len(set(interview_ids)) != len(interview_ids):
        raise SchemaValidationError("$.interviews", "interview_id values must be unique")
    if len(set(sequences)) != len(sequences):
        raise SchemaValidationError("$.interviews", "sequence values must be unique")
    if len(set(qa_ids)) != len(qa_ids):
        raise SchemaValidationError("$.interviews", "qa_id values must be unique")
    return PreparedInterviewData(
        schema_version=_text(root["schema_version"], "$.schema_version"),
        personality_id=_text(root["personality_id"], "$.personality_id"),
        personality=_parse_personality(root["personality"], "$.personality"),
        interviews=interviews,
    )


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number {value!r} is not allowed")


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field {key!r}")
        result[key] = value
    return result


def loads_prepared_interviews(text: str | bytes | bytearray) -> PreparedInterviewData:
    """Decode and validate prepared interview JSON text."""

    try:
        value = json.loads(
            text,
            parse_constant=_reject_constant,
            object_pairs_hook=_unique_pairs,
        )
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
        raise SchemaValidationError("$", f"invalid JSON: {error}") from error
    return parse_prepared_interviews(value)


def load_prepared_interviews(path: str | Path) -> PreparedInterviewData:
    """Load one prepared input JSON file from local storage."""

    return loads_prepared_interviews(Path(path).read_text(encoding="utf-8"))
