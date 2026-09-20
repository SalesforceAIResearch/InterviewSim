# Copyright (c) 2026 Salesforce, Inc.
# SPDX-License-Identifier: CC-BY-NC-4.0
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0
# International License. See LICENSE.txt in the repository root.

"""Appendix-aligned multiple-choice generation and scoring."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import random
import re
from typing import Any, Mapping

from .schema import QAPair


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-blank string")
    return value


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate field {key!r}")
        result[key] = value
    return result


def _json_object(output: str) -> Mapping[str, Any]:
    text = _text(output, "model output").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) < 3 or lines[-1].strip() != "```":
            raise ValueError("incomplete fenced JSON")
        text = "\n".join(lines[1:-1]).strip()
    try:
        value = json.loads(text, object_pairs_hook=_unique_pairs)
    except (json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"invalid model JSON: {error}") from error
    if not isinstance(value, Mapping):
        raise ValueError("model output must be a JSON object")
    return value


def _option_count(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("option_count must be an integer")
    if value not in {3, 4}:
        raise ValueError("option_count must be 3 or 4")
    return value


@dataclass(frozen=True, slots=True)
class AtomicItem:
    """One standalone question with one exact correct answer."""

    question: str
    answer: str

    def __post_init__(self) -> None:
        _text(self.question, "question")
        _text(self.answer, "answer")


def build_atomic_item_prompt(qa_pair: QAPair) -> str:
    """Build the appendix prompt for one atomic question-answer pair."""

    if not isinstance(qa_pair, QAPair):
        raise TypeError("qa_pair must be a QAPair")
    return "\n\n".join(
        (
            (
                "Role: Editor converting one interview question-response pair into "
                "one atomic question-answer pair."
            ),
            (
                "Goal: Produce one concise, factual, self-contained question that "
                "has one short answer. Use only facts explicitly stated in the "
                "original response; do not add, infer, or assume information."
            ),
            (
                "Rules:\n"
                "- Target exactly one factual claim.\n"
                "- Prefer explicit yes/no, time, number, or other concrete answers.\n"
                "- Keep the speaking and referenced subjects unchanged.\n"
                "- Output exactly one pair."
            ),
            f"Original question:\n{qa_pair.question}",
            f"Original response:\n{qa_pair.response}",
            (
                "Return exactly two lines:\n"
                "Atomic Question: <single direct question>\n"
                "Atomic Answer: <short direct answer>"
            ),
        )
    )


_ATOMIC_OUTPUT = re.compile(r"Atomic Question:\s*(\S.*)\nAtomic Answer:\s*(\S.*)\s*")


def parse_atomic_item(output: str) -> AtomicItem:
    """Parse the strict two-line atomic-item output."""

    match = _ATOMIC_OUTPUT.fullmatch(_text(output, "model output"))
    if match is None:
        raise ValueError("invalid atomic-item output")
    return AtomicItem(question=match.group(1).strip(), answer=match.group(2).strip())


class OptionKind(str, Enum):
    """Exact serialized semantic role of an MCQ option."""

    CORRECT = "correct"
    OPPOSITE_NEGATION = "opposite_negation"
    NEAR_MISS = "near_miss"
    PLAUSIBLE_MISCONCEPTION = "plausible_misconception"


@dataclass(frozen=True, slots=True)
class MCQOption:
    """Option text paired with its semantic role."""

    text: str
    kind: OptionKind

    def __post_init__(self) -> None:
        _text(self.text, "option text")
        if not isinstance(self.kind, OptionKind):
            raise TypeError("kind must be an OptionKind")


def _required_kinds(option_count: int) -> set[OptionKind]:
    _option_count(option_count)
    kinds = {
        OptionKind.CORRECT,
        OptionKind.OPPOSITE_NEGATION,
        OptionKind.NEAR_MISS,
    }
    if option_count == 4:
        kinds.add(OptionKind.PLAUSIBLE_MISCONCEPTION)
    return kinds


def _paper_option_kinds(option_count: int) -> tuple[OptionKind, ...]:
    _option_count(option_count)
    kinds = (
        OptionKind.CORRECT,
        OptionKind.OPPOSITE_NEGATION,
        OptionKind.NEAR_MISS,
    )
    if option_count == 4:
        return (*kinds, OptionKind.PLAUSIBLE_MISCONCEPTION)
    return kinds


def build_mcq_generation_prompt(
    atomic_item: AtomicItem,
    *,
    option_count: int = 4,
) -> str:
    """Build the primary paper-style pre-shuffle MCQ generation prompt."""

    if not isinstance(atomic_item, AtomicItem):
        raise TypeError("atomic_item must be an AtomicItem")
    kinds = _paper_option_kinds(option_count)
    rendered_kinds = "\n".join(
        f"{chr(ord('A') + index)}. {kind.value}" for index, kind in enumerate(kinds)
    )
    output_options = ", ".join(f'{{"kind": "{kind.value}", "text": "..."}}' for kind in kinds)
    return "\n\n".join(
        (
            (
                f"Task: Generate one diagnostic multiple-choice question with "
                f"{option_count} options before shuffling."
            ),
            (
                "Constraints:\n"
                "- Do not introduce facts not present in the atomic answer.\n"
                "- Include exactly one fully correct option.\n"
                "- Keep all options similar in structure, length, and tone.\n"
                "- Keep incorrect options plausible.\n"
                "- Do not include meta-language or explanations."
            ),
            f"Required pre-shuffle order and kinds:\n{rendered_kinds}",
            f"Atomic question:\n{atomic_item.question}",
            f"Atomic answer:\n{atomic_item.answer}",
            (
                "Return exactly one JSON object: "
                f'{{"question": "{atomic_item.question}", '
                f'"options": [{output_options}], "correct_answer": "A"}}'
            ),
        )
    )


def parse_mcq_generation(
    output: str,
    *,
    atomic_item: AtomicItem,
    option_count: int = 4,
) -> MCQItem:
    """Parse and validate a complete paper-style pre-shuffle MCQ."""

    if not isinstance(atomic_item, AtomicItem):
        raise TypeError("atomic_item must be an AtomicItem")
    expected_kinds = _paper_option_kinds(option_count)
    value = _json_object(output)
    if set(value) != {"question", "options", "correct_answer"}:
        raise ValueError("MCQ generation requires question, options, and correct_answer only")
    question = _text(value["question"], "question")
    if question != atomic_item.question:
        raise ValueError("generated question must match the atomic question")
    if value["correct_answer"] != "A":
        raise ValueError("correct_answer must be A before shuffling")
    raw_options = value["options"]
    if not isinstance(raw_options, list) or len(raw_options) != option_count:
        raise ValueError("options must match option_count")
    options: list[MCQOption] = []
    for index, (raw_option, expected_kind) in enumerate(zip(raw_options, expected_kinds)):
        if not isinstance(raw_option, Mapping):
            raise TypeError(f"option {index} must be an object")
        if set(raw_option) != {"kind", "text"}:
            raise ValueError(f"option {index} must contain kind and text only")
        if raw_option["kind"] != expected_kind.value:
            raise ValueError("option kinds must use the required pre-shuffle order")
        options.append(
            MCQOption(
                text=_text(raw_option["text"], f"option {index} text"),
                kind=expected_kind,
            )
        )
    if options[0].text != atomic_item.answer:
        raise ValueError("correct option must match the atomic answer")
    return MCQItem(question=question, options=tuple(options))


def build_distractor_prompt(
    atomic_item: AtomicItem,
    *,
    option_count: int = 4,
) -> str:
    """Build the appendix-style diagnostic option-generation prompt."""

    if not isinstance(atomic_item, AtomicItem):
        raise TypeError("atomic_item must be an AtomicItem")
    _option_count(option_count)
    kinds = [
        (
            "opposite_negation",
            "directly contradicts or negates the correct answer",
        ),
        (
            "near_miss",
            "is close to the correct answer but wrong in one critical aspect",
        ),
    ]
    if option_count == 4:
        kinds.append(
            (
                "plausible_misconception",
                "is a believable but incorrect misunderstanding",
            )
        )
    rendered_kinds = "\n".join(f"- {kind}: {description}" for kind, description in kinds)
    output_items = ", ".join(f'{{"kind": "{kind}", "text": "..."}}' for kind, _ in kinds)
    return "\n\n".join(
        (
            (
                f"Task: Create one diagnostic multiple-choice item with "
                f"{option_count} answer options."
            ),
            (
                "Constraints:\n"
                "- Do not introduce facts not present in the atomic answer.\n"
                "- Exactly one answer is fully correct.\n"
                "- Keep options similar in structure, length, and tone.\n"
                "- Incorrect options must remain plausible.\n"
                "- Do not include meta-language or explain options."
            ),
            f"Required distractor kinds:\n{rendered_kinds}",
            f"Question:\n{atomic_item.question}",
            f"Correct answer:\n{atomic_item.answer}",
            ("The correct option is added first by the framework before deterministic shuffling."),
            f'Return exactly one JSON object: {{"distractors": [{output_items}]}}',
        )
    )


def parse_distractors(
    output: str,
    *,
    option_count: int = 4,
    correct_answer: str | None = None,
) -> tuple[MCQOption, ...]:
    """Parse the exact distractor kinds for a three- or four-option item."""

    _option_count(option_count)
    value = _json_object(output)
    if set(value) != {"distractors"}:
        raise ValueError("distractor output must contain only the distractors field")
    raw_options = value["distractors"]
    if not isinstance(raw_options, list):
        raise TypeError("distractors must be an array")
    options: list[MCQOption] = []
    for index, raw_option in enumerate(raw_options):
        if not isinstance(raw_option, Mapping):
            raise TypeError(f"distractor {index} must be an object")
        if set(raw_option) != {"kind", "text"}:
            raise ValueError(f"distractor {index} must contain kind and text only")
        raw_kind = raw_option["kind"]
        if not isinstance(raw_kind, str):
            raise TypeError(f"distractor {index} kind must be a string")
        try:
            kind = OptionKind(raw_kind)
        except ValueError as error:
            raise ValueError(f"unknown distractor kind {raw_kind!r}") from error
        if kind is OptionKind.CORRECT:
            raise ValueError("correct is not a distractor kind")
        options.append(
            MCQOption(
                text=_text(raw_option["text"], f"distractor {index} text"),
                kind=kind,
            )
        )
    required = _required_kinds(option_count) - {OptionKind.CORRECT}
    if {option.kind for option in options} != required or len(options) != len(required):
        raise ValueError("distractor kinds do not match option_count")
    normalized = tuple(option.text.strip().casefold() for option in options)
    if len(set(normalized)) != len(normalized):
        raise ValueError("distractor text must be unique")
    if correct_answer is not None:
        answer = _text(correct_answer, "correct_answer").strip().casefold()
        if answer in normalized:
            raise ValueError("a distractor matches the correct answer")
    return tuple(options)


def option_labels(count: int) -> tuple[str, ...]:
    """Return labels for a supported three- or four-option item."""

    _option_count(count)
    return tuple(chr(ord("A") + index) for index in range(count))


@dataclass(frozen=True, slots=True)
class MCQItem:
    """A shuffled item carrying the semantic kind of every option."""

    question: str
    options: tuple[MCQOption, ...]

    def __post_init__(self) -> None:
        _text(self.question, "question")
        if not isinstance(self.options, tuple):
            raise TypeError("options must be a tuple")
        if any(not isinstance(option, MCQOption) for option in self.options):
            raise TypeError("options must contain MCQOption values")
        if len(self.options) not in {3, 4}:
            raise ValueError("items must contain three or four options")
        if {option.kind for option in self.options} != _required_kinds(len(self.options)):
            raise ValueError("option kinds do not match item size")
        normalized = tuple(option.text.strip().casefold() for option in self.options)
        if len(set(normalized)) != len(normalized):
            raise ValueError("option text must be unique")

    @property
    def correct_label(self) -> str:
        """Return the label assigned to the correct option."""

        index = next(
            index for index, option in enumerate(self.options) if option.kind is OptionKind.CORRECT
        )
        return option_labels(len(self.options))[index]

    def option_for_label(self, label: str) -> MCQOption | None:
        """Resolve an exact option label, returning None for invalid input."""

        labels = option_labels(len(self.options))
        if label not in labels:
            return None
        return self.options[labels.index(label)]


def shuffle_mcq_item(mcq_item: MCQItem, *, seed: int = 0) -> MCQItem:
    """Reproducibly shuffle a validated pre-shuffle MCQ item."""

    if not isinstance(mcq_item, MCQItem):
        raise TypeError("mcq_item must be an MCQItem")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    serialized_options = "\x00".join(
        f"{option.kind.value}\x00{option.text}" for option in mcq_item.options
    )
    material = f"{seed}\x00{mcq_item.question}\x00{serialized_options}".encode("utf-8")
    shuffled = list(mcq_item.options)
    random.Random(int.from_bytes(hashlib.sha256(material).digest(), "big")).shuffle(shuffled)
    return MCQItem(question=mcq_item.question, options=tuple(shuffled))


def shuffle_options(
    atomic_item: AtomicItem,
    distractors: Sequence[MCQOption],
    *,
    seed: int = 0,
) -> MCQItem:
    """Add the correct option and reproducibly shuffle three or four options."""

    if not isinstance(atomic_item, AtomicItem):
        raise TypeError("atomic_item must be an AtomicItem")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    if isinstance(distractors, (str, bytes)) or not isinstance(distractors, Sequence):
        raise TypeError("distractors must be a sequence of MCQOption values")
    options = (MCQOption(atomic_item.answer, OptionKind.CORRECT), *tuple(distractors))
    unshuffled = MCQItem(question=atomic_item.question, options=options)
    return shuffle_mcq_item(unshuffled, seed=seed)


def build_mcq_answering_prompt(
    mcq_items: Sequence[MCQItem],
    *,
    personality_description: str | None = None,
    interview_context: Iterable[str] = (),
) -> str:
    """Build the primary paper-style prompt for one or more MCQ items."""

    if isinstance(mcq_items, (str, bytes)) or not isinstance(mcq_items, Sequence):
        raise TypeError("mcq_items must be a sequence of MCQItem values")
    items = tuple(mcq_items)
    if not items:
        raise ValueError("at least one MCQ item is required")
    if any(not isinstance(item, MCQItem) for item in items):
        raise TypeError("mcq_items must contain MCQItem values")
    if personality_description is not None:
        personality_description = _text(personality_description, "personality_description")
    if isinstance(interview_context, (str, bytes)):
        raise TypeError("interview_context must be an iterable of strings")
    context = tuple(_text(value, "interview context") for value in interview_context)
    sections = [
        (
            "Task: Answer the multiple-choice questions using only the supplied "
            "personality information and interview context."
        ),
        (
            "Rules:\n"
            "- Do not use outside knowledge.\n"
            "- Choose exactly one available option for every item.\n"
            "- Do not refuse.\n"
            "- Include no reasoning, qualifiers, or extra text."
        ),
    ]
    if personality_description is not None:
        sections.append(f"Personality:\n{personality_description}")
    if context:
        sections.append("Interview context:\n" + "\n\n".join(context))
    rendered_items = []
    output_lines = []
    for index, item in enumerate(items, start=1):
        labels = option_labels(len(item.options))
        rendered_options = "\n".join(
            f"{label}. {option.text}" for label, option in zip(labels, item.options)
        )
        rendered_items.append(f"Q{index}. {item.question}\n{rendered_options}")
        output_lines.append(f"Q{index}: <option letter>")
    sections.extend(
        (
            "Questions:\n\n" + "\n\n".join(rendered_items),
            ("Return exactly one label per item in this format:\n" + "\n".join(output_lines)),
        )
    )
    return "\n\n".join(sections)


def build_answer_prompt(
    mcq_item: MCQItem,
    *,
    personality_description: str | None = None,
    interview_context: Iterable[str] = (),
) -> str:
    """Build the single-item convenience form of the answering prompt."""

    return build_mcq_answering_prompt(
        (mcq_item,),
        personality_description=personality_description,
        interview_context=interview_context,
    )


def _parse_answer_lines(
    output: str,
    option_counts: tuple[int, ...],
) -> tuple[str, ...]:
    text = _text(output, "answer").strip()
    lines = text.splitlines()
    if len(lines) != len(option_counts):
        raise ValueError("answer count does not match item count")
    answers: list[str] = []
    for index, (line, option_count) in enumerate(
        zip(lines, option_counts),
        start=1,
    ):
        match = re.fullmatch(rf"Q{index}:\s*([A-Z])", line.strip())
        labels = option_labels(option_count)
        if match is None or match.group(1) not in labels:
            raise ValueError(f"invalid or unavailable label for Q{index}")
        answers.append(match.group(1))
    return tuple(answers)


def parse_mcq_answers(
    output: str,
    mcq_items: Sequence[MCQItem],
) -> tuple[str, ...]:
    """Parse exactly one validated label for every MCQ item."""

    if isinstance(mcq_items, (str, bytes)) or not isinstance(mcq_items, Sequence):
        raise TypeError("mcq_items must be a sequence of MCQItem values")
    items = tuple(mcq_items)
    if not items:
        raise ValueError("at least one MCQ item is required")
    if any(not isinstance(item, MCQItem) for item in items):
        raise TypeError("mcq_items must contain MCQItem values")
    return _parse_answer_lines(
        output,
        tuple(len(item.options) for item in items),
    )


def parse_mcq_answer(output: str, *, option_count: int) -> str:
    """Parse the single-item convenience answer form."""

    return _parse_answer_lines(output, (_option_count(option_count),))[0]


def exact_accuracy(predictions: Sequence[object], answers: Sequence[object]) -> float:
    """Return the fraction of predictions exactly equal to their answers."""

    if isinstance(predictions, (str, bytes)) or isinstance(answers, (str, bytes)):
        raise TypeError("predictions and answers must be sequences")
    if len(predictions) != len(answers):
        raise ValueError("predictions and answers must have equal lengths")
    if not predictions:
        raise ValueError("at least one answer is required")
    return sum(prediction == answer for prediction, answer in zip(predictions, answers)) / len(
        answers
    )


def mcq_reward(prediction: str | None, mcq_item: MCQItem) -> float:
    """Return +1 for correct, -1 for opposite-negation, and -0.5 otherwise."""

    if not isinstance(mcq_item, MCQItem):
        raise TypeError("mcq_item must be an MCQItem")
    if prediction is None or not isinstance(prediction, str):
        return -0.5
    option = mcq_item.option_for_label(prediction)
    if option is None:
        return -0.5
    if option.kind is OptionKind.CORRECT:
        return 1.0
    if option.kind is OptionKind.OPPOSITE_NEGATION:
        return -1.0
    return -0.5


@dataclass(frozen=True, slots=True)
class MCQAnswerScore:
    """Exact accuracy and semantic-kind rewards for an MCQ batch."""

    predictions: tuple[str | None, ...]
    correct_answers: tuple[str, ...]
    exact_accuracy: float
    rewards: tuple[float, ...]
    mean_reward: float


def score_mcq_answers(
    predictions: Sequence[str | None],
    mcq_items: Sequence[MCQItem],
) -> MCQAnswerScore:
    """Score a batch while preserving each selected option's semantic kind."""

    if isinstance(predictions, (str, bytes)) or not isinstance(predictions, Sequence):
        raise TypeError("predictions must be a sequence")
    if isinstance(mcq_items, (str, bytes)) or not isinstance(mcq_items, Sequence):
        raise TypeError("mcq_items must be a sequence")
    prediction_values = tuple(predictions)
    items = tuple(mcq_items)
    if not items:
        raise ValueError("at least one MCQ item is required")
    if len(prediction_values) != len(items):
        raise ValueError("predictions and MCQ items must have equal lengths")
    if any(not isinstance(item, MCQItem) for item in items):
        raise TypeError("mcq_items must contain MCQItem values")
    correct_answers = tuple(item.correct_label for item in items)
    rewards = tuple(
        mcq_reward(prediction, item) for prediction, item in zip(prediction_values, items)
    )
    return MCQAnswerScore(
        predictions=prediction_values,
        correct_answers=correct_answers,
        exact_accuracy=exact_accuracy(prediction_values, correct_answers),
        rewards=rewards,
        mean_reward=sum(rewards) / len(rewards),
    )
