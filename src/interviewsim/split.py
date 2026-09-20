# Copyright (c) 2026 Salesforce, Inc.
# SPDX-License-Identifier: CC-BY-NC-4.0
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0
# International License. See LICENSE.txt in the repository root.

"""Deterministic interview-level temporal splitting."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

from .schema import Interview, QAPair


TEST_FRACTION = 0.2


@dataclass(frozen=True, slots=True)
class TemporalSplit:
    """Training interviews followed by chronologically held-out interviews."""

    train: tuple[Interview, ...]
    test: tuple[Interview, ...]

    def __post_init__(self) -> None:
        if not self.train:
            raise ValueError("train partition must not be empty")
        if not self.test:
            raise ValueError("test partition must not be empty")
        if self.train[-1].sequence >= self.test[0].sequence:
            raise ValueError("train sequences must precede test sequences")


def sort_interviews(interviews: Iterable[Interview]) -> tuple[Interview, ...]:
    """Order interviews by sequence with identifier tie breaking."""

    values = tuple(interviews)
    if any(not isinstance(interview, Interview) for interview in values):
        raise TypeError("all values must be Interview instances")
    interview_ids = [interview.interview_id for interview in values]
    sequences = [interview.sequence for interview in values]
    if len(set(interview_ids)) != len(interview_ids):
        raise ValueError("interview_id values must be unique")
    if len(set(sequences)) != len(sequences):
        raise ValueError("sequence values must be unique")
    return tuple(sorted(values, key=lambda interview: (interview.sequence, interview.interview_id)))


def temporal_train_test_split(interviews: Iterable[Interview]) -> TemporalSplit:
    """Hold out the latest ceiling of 20 percent of whole interviews."""

    ordered = sort_interviews(interviews)
    test_count = math.ceil(len(ordered) * TEST_FRACTION)
    if len(ordered) - test_count < 1:
        raise ValueError("at least two interviews are required for a temporal split")
    boundary = len(ordered) - test_count
    return TemporalSplit(train=ordered[:boundary], test=ordered[boundary:])


def qa_pairs_from_interviews(interviews: Iterable[Interview]) -> tuple[QAPair, ...]:
    """Flatten QA pairs from interviews in chronological and within-file order."""

    return tuple(
        qa_pair for interview in sort_interviews(interviews) for qa_pair in interview.qa_pairs
    )
