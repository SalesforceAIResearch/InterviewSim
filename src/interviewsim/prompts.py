# Copyright (c) 2026 Salesforce, Inc.
# SPDX-License-Identifier: CC-BY-NC-4.0
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0
# International License. See LICENSE.txt in the repository root.

"""Deterministic response prompts restricted to training interviews."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import random
from typing import Protocol

from .protocols import Embedder
from .retrieval import retrieve_qa_pairs
from .schema import Interview, Personality, PreparedInterviewData, QAPair
from .split import qa_pairs_from_interviews, sort_interviews, temporal_train_test_split


@dataclass(frozen=True, slots=True)
class ResponsePromptContext:
    """Profile data and the interview-level training partition."""

    personality_id: str
    personality: Personality
    training_interviews: tuple[Interview, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.personality_id, str) or not self.personality_id.strip():
            raise ValueError("personality_id must be a non-blank string")
        if not isinstance(self.personality, Personality):
            raise TypeError("personality must be a Personality")
        if not isinstance(self.training_interviews, tuple):
            raise TypeError("training_interviews must be a tuple")
        sort_interviews(self.training_interviews)

    @classmethod
    def from_prepared(cls, data: PreparedInterviewData) -> ResponsePromptContext:
        """Split prepared input and retain only training interviews."""

        if not isinstance(data, PreparedInterviewData):
            raise TypeError("data must be PreparedInterviewData")
        split = temporal_train_test_split(data.interviews)
        return cls(
            personality_id=data.personality_id,
            personality=data.personality,
            training_interviews=split.train,
        )

    @property
    def training_qa_pairs(self) -> tuple[QAPair, ...]:
        """Return chronologically flattened training QA examples."""

        return qa_pairs_from_interviews(self.training_interviews)


class ResponsePromptBuilder(Protocol):
    """Structural interface shared by response-prompt strategies."""

    def build(self, question: str, context: ResponsePromptContext) -> str:
        """Build a prompt without invoking a model."""


def _count(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must not be negative")
    return value


def _question(question: str) -> str:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-blank string")
    return question


def _format_examples(qa_pairs: tuple[QAPair, ...]) -> str:
    return "\n\n".join(
        "\n".join(
            (
                f"Example {index}",
                f"Question: {qa_pair.question}",
                f"Response: {qa_pair.response}",
            )
        )
        for index, qa_pair in enumerate(qa_pairs, start=1)
    )


def _compose(
    question: str,
    context: ResponsePromptContext,
    *,
    profile_heading: str | None = None,
    profile_text: str | None = None,
    qa_pairs: tuple[QAPair, ...] = (),
) -> str:
    question = _question(question)
    sections = [
        "Task: Write one plausible interview response.",
        f"Personality ID: {context.personality_id}",
        (
            "Requirements:\n"
            "- Answer only the new question.\n"
            "- Use only supplied profile and training examples.\n"
            "- Return response text only."
        ),
    ]
    if profile_heading is not None:
        assert profile_text is not None
        sections.append(f"{profile_heading}:\n{profile_text}")
    if qa_pairs:
        sections.append(f"Training examples:\n{_format_examples(qa_pairs)}")
    sections.append(f"New question:\n{question}\n\nResponse:")
    return "\n\n".join(sections)


@dataclass(frozen=True, slots=True)
class SimplePromptBuilder:
    """Use neither profile text nor training examples."""

    def build(self, question: str, context: ResponsePromptContext) -> str:
        return _compose(question, context)


@dataclass(frozen=True, slots=True)
class ProfilePromptBuilder:
    """Use the short profile and no QA examples."""

    def build(self, question: str, context: ResponsePromptContext) -> str:
        return _compose(
            question,
            context,
            profile_heading="Profile",
            profile_text=context.personality.profile,
        )


@dataclass(frozen=True, slots=True)
class LongProfilePromptBuilder:
    """Use the long profile and no QA examples."""

    def build(self, question: str, context: ResponsePromptContext) -> str:
        return _compose(
            question,
            context,
            profile_heading="Long profile",
            profile_text=context.personality.long_profile,
        )


@dataclass(frozen=True, slots=True)
class ChronologicalPromptBuilder:
    """Use the latest QA examples from training interviews."""

    example_count: int = 4

    def __post_init__(self) -> None:
        _count(self.example_count, "example_count")

    def build(self, question: str, context: ResponsePromptContext) -> str:
        qa_pairs = context.training_qa_pairs
        selected = qa_pairs[-self.example_count :] if self.example_count else ()
        return _compose(question, context, qa_pairs=selected)


@dataclass(frozen=True, slots=True)
class RandomPromptBuilder:
    """Use a seeded subset of QA examples from training interviews."""

    example_count: int = 4
    seed: int = 0

    def __post_init__(self) -> None:
        _count(self.example_count, "example_count")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise TypeError("seed must be an integer")

    def build(self, question: str, context: ResponsePromptContext) -> str:
        question = _question(question)
        qa_pairs = context.training_qa_pairs
        count = min(self.example_count, len(qa_pairs))
        material = f"{self.seed}\x00{context.personality_id}\x00{question}".encode("utf-8")
        generator = random.Random(int.from_bytes(hashlib.sha256(material).digest(), "big"))
        indices = sorted(generator.sample(range(len(qa_pairs)), count))
        selected = tuple(qa_pairs[index] for index in indices)
        return _compose(question, context, qa_pairs=selected)


@dataclass(frozen=True, slots=True)
class RetrievalPromptBuilder:
    """Use cosine-selected QA examples from training interviews."""

    embedder: Embedder
    example_count: int = 4

    def __post_init__(self) -> None:
        if not callable(self.embedder):
            raise TypeError("embedder must be callable")
        _count(self.example_count, "example_count")

    def build(self, question: str, context: ResponsePromptContext) -> str:
        question = _question(question)
        results = retrieve_qa_pairs(
            question,
            context.training_qa_pairs,
            self.embedder,
            k=self.example_count,
        )
        return _compose(
            question,
            context,
            qa_pairs=tuple(result.qa_pair for result in results),
        )


@dataclass(frozen=True, slots=True)
class HybridPromptBuilder:
    """Combine ``k1`` retrieved and ``k2`` most-recent training QA pairs."""

    embedder: Embedder
    k1: int = 2
    k2: int = 2

    def __post_init__(self) -> None:
        if not callable(self.embedder):
            raise TypeError("embedder must be callable")
        _count(self.k1, "k1")
        _count(self.k2, "k2")

    def build(self, question: str, context: ResponsePromptContext) -> str:
        question = _question(question)
        training_qa_pairs = context.training_qa_pairs
        retrieved = retrieve_qa_pairs(
            question,
            training_qa_pairs,
            self.embedder,
            k=self.k1,
        )
        recent = tuple(reversed(training_qa_pairs[-self.k2 :])) if self.k2 else ()
        selected: list[QAPair] = []
        seen: set[str] = set()
        for qa_pair in (*(result.qa_pair for result in retrieved), *recent):
            if qa_pair.qa_id not in seen:
                selected.append(qa_pair)
                seen.add(qa_pair.qa_id)
        return _compose(
            question,
            context,
            qa_pairs=tuple(selected),
        )
