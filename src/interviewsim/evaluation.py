# Copyright (c) 2026 Salesforce, Inc.
# SPDX-License-Identifier: CC-BY-NC-4.0
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0
# International License. See LICENSE.txt in the repository root.

"""Appendix-aligned prompt, parsing, and aggregation helpers."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
import json
import math
import re
from typing import Any, Iterable, Mapping


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-blank string")
    return value


def _optional_text(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, name)


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate field {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite number {value!r} is not allowed")


def _json_object(output: str) -> Mapping[str, Any]:
    text = _required_text(output, "judge output").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) < 3 or lines[-1].strip() != "```":
            raise ValueError("incomplete fenced JSON")
        text = "\n".join(lines[1:-1]).strip()
    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_pairs,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"invalid judge JSON: {error}") from error
    if not isinstance(value, Mapping):
        raise ValueError("judge output must be a JSON object")
    return value


@dataclass(frozen=True, slots=True)
class ContentSimilarityJudgment:
    """A five-point content score with the judge explanation."""

    score: int
    explanation: str

    def __post_init__(self) -> None:
        if isinstance(self.score, bool) or not isinstance(self.score, int):
            raise TypeError("score must be an integer")
        if not 1 <= self.score <= 5:
            raise ValueError("score must be between 1 and 5")
        _required_text(self.explanation, "explanation")


@dataclass(frozen=True, slots=True)
class ContentSimilarityAggregate:
    """Raw arithmetic mean of content-similarity judgments."""

    mean_score: float
    count: int


@dataclass(frozen=True, slots=True)
class FactSummary:
    """Structured fact summary with an auditable explanation."""

    summary: str
    explanation: str

    def __post_init__(self) -> None:
        _required_text(self.summary, "summary")
        _required_text(self.explanation, "explanation")


def build_fact_summary_prompt(held_out_responses: Iterable[str]) -> str:
    """Build a summary prompt over held-out responses only."""

    if isinstance(held_out_responses, (str, bytes)):
        raise TypeError("held_out_responses must be an iterable of strings")
    responses = tuple(
        _required_text(response, "held-out response") for response in held_out_responses
    )
    if not responses:
        raise ValueError("at least one held-out response is required")
    rendered = "\n\n".join(
        f"Response {index}:\n{response}" for index, response in enumerate(responses, start=1)
    )
    return "\n\n".join(
        (
            (
                "Task: Summarize established facts, stated opinions, and recurring "
                "characteristics using only the supplied held-out responses."
            ),
            (
                "Rules:\n"
                "- Do not use external facts or outside knowledge.\n"
                "- Do not infer details that are not explicitly supported.\n"
                "- Preserve uncertainty and changes over time.\n"
                "- Return self-contained text without citations, links, source "
                "identifiers, or provenance fields.\n"
                "- Explain how the summary stays within the supplied responses."
            ),
            f"Held-out responses:\n{rendered}",
            ('Return exactly one JSON object: {"summary": "...", "explanation": "..."}'),
        )
    )


def parse_fact_summary(output: str) -> FactSummary:
    """Parse the strict provenance-free fact-summary contract."""

    value = _json_object(output)
    if set(value) != {"summary", "explanation"}:
        raise ValueError("fact summary requires summary and explanation only")
    return FactSummary(
        summary=_required_text(value["summary"], "summary"),
        explanation=_required_text(value["explanation"], "explanation"),
    )


def fact_summary_text(fact_summary: FactSummary) -> str:
    """Return summary text for factual-consistency evaluation."""

    if not isinstance(fact_summary, FactSummary):
        raise TypeError("fact_summary must be a FactSummary")
    return fact_summary.summary


def build_content_similarity_prompt(
    reference: str,
    candidate: str,
    *,
    question: str | None = None,
    personality_id: str | None = None,
) -> str:
    """Build the appendix five-point content-similarity prompt."""

    reference = _required_text(reference, "reference")
    candidate = _required_text(candidate, "candidate")
    question = _optional_text(question, "question")
    personality_id = _optional_text(personality_id, "personality_id")
    sections = [
        (
            "Role: Expert evaluator assessing content similarity between a generated "
            "answer and its ground-truth answer."
        ),
        (
            "Evaluation focus:\n"
            "- Whether both answers convey the same core ideas.\n"
            "- Whether key content is preserved.\n"
            "- Whether important details are present.\n"
            "Do not penalize different wording with the same meaning. Penalize "
            "missing key information and contradictory information."
        ),
        (
            "Scoring:\n"
            "5 = same core ideas as the ground truth\n"
            "4 = main points preserved with minor differences\n"
            "3 = some overlap but key information is missing\n"
            "2 = limited overlap with significant differences\n"
            "1 = contradicts or misses the core content"
        ),
    ]
    if personality_id is not None:
        sections.append(f"Personality ID:\n{personality_id}")
    if question is not None:
        sections.append(f"Question:\n{question}")
    sections.extend(
        (
            f"Ground-truth answer:\n{reference}",
            f"Generated answer:\n{candidate}",
            (
                "Return exactly one JSON object: "
                '{"score": <integer from 1 to 5>, "explanation": "..."}'
            ),
        )
    )
    return "\n\n".join(sections)


def parse_content_similarity(output: str) -> ContentSimilarityJudgment:
    """Parse the required score and explanation."""

    value = _json_object(output)
    if set(value) != {"score", "explanation"}:
        raise ValueError("content judgment requires score and explanation only")
    return ContentSimilarityJudgment(
        score=value["score"],
        explanation=_required_text(value["explanation"], "explanation"),
    )


def aggregate_content_similarity(
    judgments: Iterable[ContentSimilarityJudgment],
) -> ContentSimilarityAggregate:
    """Return the raw mean of one or more content judgments."""

    values = tuple(judgments)
    if not values:
        raise ValueError("at least one content judgment is required")
    if any(not isinstance(item, ContentSimilarityJudgment) for item in values):
        raise TypeError("all values must be ContentSimilarityJudgment instances")
    return ContentSimilarityAggregate(
        mean_score=math.fsum(item.score for item in values) / len(values),
        count=len(values),
    )


class FactualConsistencyLabel(str, Enum):
    """Exact factual-consistency labels."""

    ENTAILMENT = "Entailment"
    NEUTRAL = "Neutral"
    CONTRADICTION = "Contradiction"


@dataclass(frozen=True, slots=True)
class FactualConsistencyJudgment:
    """A factual relation with the judge explanation."""

    label: FactualConsistencyLabel
    explanation: str

    def __post_init__(self) -> None:
        if not isinstance(self.label, FactualConsistencyLabel):
            raise TypeError("label must be a FactualConsistencyLabel")
        _required_text(self.explanation, "explanation")


def build_factual_consistency_prompt(
    fact_summary: str,
    generated_answer: str,
    *,
    question: str | None = None,
    personality_id: str | None = None,
) -> str:
    """Build the appendix factual-consistency classification prompt."""

    fact_summary = _required_text(fact_summary, "fact_summary")
    generated_answer = _required_text(generated_answer, "generated_answer")
    question = _optional_text(question, "question")
    personality_id = _optional_text(personality_id, "personality_id")
    sections = [
        (
            "Role: Expert fact-checker evaluating a generated answer against a fact "
            "summary of established facts, opinions, and characteristics."
        ),
        (
            "Labels:\n"
            "Contradiction = a clear, direct conflict with the summary, including "
            "facts, events, opinions, or timeline\n"
            "Entailment = consistent with and supported by the summary\n"
            "Neutral = neither contradicted nor supported, including information "
            "not covered, vague claims, or topics absent from the summary"
        ),
        (
            "Guidelines:\n"
            "- Use Contradiction only for a clear, direct conflict.\n"
            "- Missing information is not a contradiction; use Neutral.\n"
            "- Opinions may evolve over time, so evaluate them leniently.\n"
            "- Evaluate factual consistency, not writing style.\n"
            "- If uncertain, prefer Neutral."
        ),
    ]
    if personality_id is not None:
        sections.append(f"Personality ID:\n{personality_id}")
    sections.append(f"Fact summary:\n{fact_summary}")
    if question is not None:
        sections.append(f"Question:\n{question}")
    sections.extend(
        (
            f"Generated answer:\n{generated_answer}",
            (
                "Return exactly one JSON object: "
                '{"label": "Entailment|Neutral|Contradiction", '
                '"explanation": "..."}'
            ),
        )
    )
    return "\n\n".join(sections)


def parse_factual_consistency(output: str) -> FactualConsistencyJudgment:
    """Parse the required exact label and explanation."""

    value = _json_object(output)
    if set(value) != {"label", "explanation"}:
        raise ValueError("factual judgment requires label and explanation only")
    raw_label = value["label"]
    if not isinstance(raw_label, str):
        raise TypeError("factual label must be a string")
    try:
        label = FactualConsistencyLabel(raw_label)
    except ValueError as error:
        raise ValueError(f"unknown factual label {raw_label!r}") from error
    return FactualConsistencyJudgment(
        label=label,
        explanation=_required_text(value["explanation"], "explanation"),
    )


def contradiction_ratio(
    judgments: Iterable[FactualConsistencyJudgment],
) -> float:
    """Return contradictions divided by all factual judgments."""

    values = tuple(judgments)
    if not values:
        raise ValueError("at least one factual judgment is required")
    if any(not isinstance(item, FactualConsistencyJudgment) for item in values):
        raise TypeError("all values must be FactualConsistencyJudgment instances")
    return sum(item.label is FactualConsistencyLabel.CONTRADICTION for item in values) / len(values)


class BigFiveTrait(str, Enum):
    """The five personality dimensions used by the alignment metric."""

    OPENNESS = "openness"
    CONSCIENTIOUSNESS = "conscientiousness"
    EXTRAVERSION = "extraversion"
    AGREEABLENESS = "agreeableness"
    NEUROTICISM = "neuroticism"


class PersonalityLevel(str, Enum):
    """Exact ordinal personality levels."""

    LOW = "Low"
    NEUTRAL = "Neutral"
    HIGH = "High"


PERSONALITY_LEVEL_ORDINALS: Mapping[PersonalityLevel, int] = {
    PersonalityLevel.LOW: 1,
    PersonalityLevel.NEUTRAL: 2,
    PersonalityLevel.HIGH: 3,
}


_TRAIT_RUBRICS: Mapping[BigFiveTrait, tuple[str, str]] = {
    BigFiveTrait.OPENNESS: (
        "curiosity, imagination, receptiveness to new ideas, and varied interests",
        "preference for familiar approaches, concrete framing, and predictability",
    ),
    BigFiveTrait.CONSCIENTIOUSNESS: (
        "organization, reliability, planning, and attention to commitments",
        "disorganization, impulsive planning, and weak follow-through",
    ),
    BigFiveTrait.EXTRAVERSION: (
        "energetic, expressive, socially engaged, and elaborative communication",
        "reserved, brief, subdued, and minimally elaborative communication",
    ),
    BigFiveTrait.AGREEABLENESS: (
        "cooperation, empathy, trust, patience, and considerate communication",
        "confrontation, skepticism, bluntness, and low interpersonal accommodation",
    ),
    BigFiveTrait.NEUROTICISM: (
        "worry, stress sensitivity, emotional volatility, and negative affect",
        "calmness, emotional stability, resilience, and low stress reactivity",
    ),
}


@dataclass(frozen=True, slots=True)
class PersonalityTraitJudgment:
    """One independent categorical judge run for one trait."""

    trait: BigFiveTrait
    level: PersonalityLevel
    explanation: str

    def __post_init__(self) -> None:
        if not isinstance(self.trait, BigFiveTrait):
            raise TypeError("trait must be a BigFiveTrait")
        if not isinstance(self.level, PersonalityLevel):
            raise TypeError("level must be a PersonalityLevel")
        _required_text(self.explanation, "explanation")


@dataclass(frozen=True, slots=True)
class PersonalityTraitVote:
    """Modal result and vote share from three independent runs."""

    trait: BigFiveTrait
    level: PersonalityLevel
    confidence: float


@dataclass(frozen=True, slots=True)
class BigFiveRating:
    """Voted level for each Big Five trait."""

    openness: PersonalityLevel
    conscientiousness: PersonalityLevel
    extraversion: PersonalityLevel
    agreeableness: PersonalityLevel
    neuroticism: PersonalityLevel

    def __post_init__(self) -> None:
        for trait in BigFiveTrait:
            if not isinstance(getattr(self, trait.value), PersonalityLevel):
                raise TypeError(f"{trait.value} must be a PersonalityLevel")

    def as_dict(self) -> dict[BigFiveTrait, PersonalityLevel]:
        """Return trait-keyed levels in canonical order."""

        return {trait: getattr(self, trait.value) for trait in BigFiveTrait}

    def as_ordinals(self) -> dict[BigFiveTrait, int]:
        """Map Low, Neutral, and High to 1, 2, and 3."""

        return {trait: PERSONALITY_LEVEL_ORDINALS[level] for trait, level in self.as_dict().items()}


def build_personality_similarity_prompt(
    trait: BigFiveTrait,
    responses: Iterable[str],
) -> str:
    """Build one trait-specific prompt over a collection of responses."""

    if not isinstance(trait, BigFiveTrait):
        raise TypeError("trait must be a BigFiveTrait")
    if isinstance(responses, (str, bytes)):
        raise TypeError("responses must be an iterable of strings")
    values = tuple(_required_text(response, "response") for response in responses)
    if not values:
        raise ValueError("at least one response is required")
    high_indicators, low_indicators = _TRAIT_RUBRICS[trait]
    rendered = "\n\n".join(
        f"Response {index}:\n{response}" for index, response in enumerate(values, start=1)
    )
    title = trait.value.capitalize()
    return "\n\n".join(
        (
            (
                f"Analyze the following responses and evaluate how much {trait.value} "
                "the personality displays."
            ),
            f"High {title} indicators:\n{high_indicators}.",
            f"Low {title} indicators:\n{low_indicators}.",
            ("Based solely on these responses, rate the trait as Low, Neutral, or High."),
            f"Conversation responses:\n```\n{rendered}\n```",
            (
                "Return exactly: "
                "<rate>Low|Neutral|High</rate> "
                "<justification>Explanation</justification>"
            ),
        )
    )


_TRAIT_OUTPUT = re.compile(
    r"\s*<rate>(Low|Neutral|High)</rate>\s*"
    r"<justification>(.+?)</justification>\s*",
    re.DOTALL,
)


def parse_personality_trait(
    output: str,
    *,
    trait: BigFiveTrait,
) -> PersonalityTraitJudgment:
    """Parse one trait-specific appendix output."""

    if not isinstance(trait, BigFiveTrait):
        raise TypeError("trait must be a BigFiveTrait")
    text = _required_text(output, "judge output")
    match = _TRAIT_OUTPUT.fullmatch(text)
    if match is None:
        raise ValueError("invalid trait judgment output")
    return PersonalityTraitJudgment(
        trait=trait,
        level=PersonalityLevel(match.group(1)),
        explanation=_required_text(match.group(2), "explanation").strip(),
    )


def vote_personality_trait(
    judgments: Iterable[PersonalityTraitJudgment],
) -> PersonalityTraitVote:
    """Take the mode of exactly three independent runs for one trait."""

    values = tuple(judgments)
    if len(values) != 3:
        raise ValueError("exactly three trait judgments are required")
    if any(not isinstance(item, PersonalityTraitJudgment) for item in values):
        raise TypeError("all values must be PersonalityTraitJudgment instances")
    trait = values[0].trait
    if any(item.trait is not trait for item in values):
        raise ValueError("all judgments must evaluate the same trait")
    counts = Counter(item.level for item in values)
    highest = max(counts.values())
    winners = tuple(level for level, count in counts.items() if count == highest)
    level = winners[0] if len(winners) == 1 else PersonalityLevel.NEUTRAL
    return PersonalityTraitVote(
        trait=trait,
        level=level,
        confidence=highest / 3.0,
    )


def vote_big_five(
    runs: Mapping[BigFiveTrait, Iterable[PersonalityTraitJudgment]],
) -> BigFiveRating:
    """Vote three independent runs for every trait into one rating."""

    if not isinstance(runs, Mapping):
        raise TypeError("runs must be a trait-keyed mapping")
    if set(runs) != set(BigFiveTrait):
        raise ValueError("runs must contain exactly all five traits")
    voted = {trait.value: vote_personality_trait(runs[trait]).level for trait in BigFiveTrait}
    return BigFiveRating(**voted)


def big_five_alignment(reference: BigFiveRating, candidate: BigFiveRating) -> float:
    """Return one minus total five-trait ordinal distance divided by ten."""

    if not isinstance(reference, BigFiveRating):
        raise TypeError("reference must be a BigFiveRating")
    if not isinstance(candidate, BigFiveRating):
        raise TypeError("candidate must be a BigFiveRating")
    reference_values = reference.as_ordinals()
    candidate_values = candidate.as_ordinals()
    total_distance = sum(
        abs(reference_values[trait] - candidate_values[trait]) for trait in BigFiveTrait
    )
    return 1.0 - total_distance / 10.0
