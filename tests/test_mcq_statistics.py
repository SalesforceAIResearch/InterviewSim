# Copyright (c) 2026 Salesforce, Inc.
# SPDX-License-Identifier: CC-BY-NC-4.0
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0
# International License. See LICENSE.txt in the repository root.

from __future__ import annotations

import pytest

from interviewsim import (
    AtomicItem,
    OptionKind,
    QAPair,
    build_answer_prompt,
    build_atomic_item_prompt,
    build_distractor_prompt,
    build_mcq_answering_prompt,
    build_mcq_generation_prompt,
    exact_accuracy,
    mcq_reward,
    option_labels,
    paired_sign_flip_test,
    parse_atomic_item,
    parse_distractors,
    parse_mcq_answer,
    parse_mcq_answers,
    parse_mcq_generation,
    score_mcq_answers,
    shuffle_mcq_item,
    shuffle_options,
)


def _qa_pair() -> QAPair:
    return QAPair(
        qa_id="q_001",
        question="tok_question",
        response="tok_response",
        tags=("tok_tag",),
    )


def _three_option_output() -> str:
    return (
        '{"distractors":['
        '{"kind":"opposite_negation","text":"tok_opposite"},'
        '{"kind":"near_miss","text":"tok_near"}]}'
    )


def _four_option_output() -> str:
    return (
        '{"distractors":['
        '{"kind":"opposite_negation","text":"tok_opposite"},'
        '{"kind":"near_miss","text":"tok_near"},'
        '{"kind":"plausible_misconception","text":"tok_plausible"}]}'
    )


def _generation_output(option_count: int) -> str:
    options = [
        '{"kind":"correct","text":"tok_answer"}',
        '{"kind":"opposite_negation","text":"tok_opposite"}',
        '{"kind":"near_miss","text":"tok_near"}',
    ]
    if option_count == 4:
        options.append('{"kind":"plausible_misconception","text":"tok_plausible"}')
    return (
        '{"question":"tok_item_question","options":['
        + ",".join(options)
        + '],"correct_answer":"A"}'
    )


def test_atomic_prompt_and_exact_two_line_parser() -> None:
    prompt = build_atomic_item_prompt(_qa_pair())
    item = parse_atomic_item("Atomic Question: tok_item_question\nAtomic Answer: tok_answer")

    assert "Target exactly one factual claim" in prompt
    assert "do not add, infer, or assume" in prompt
    assert item == AtomicItem("tok_item_question", "tok_answer")
    with pytest.raises(ValueError, match="invalid atomic-item output"):
        parse_atomic_item("Atomic Question: tok_a\nAtomic Answer: tok_b\nExtra: tok_c")


def test_three_and_four_option_generation_contracts() -> None:
    atomic_item = AtomicItem("tok_item_question", "tok_answer")
    three_prompt = build_distractor_prompt(atomic_item, option_count=3)
    four_prompt = build_distractor_prompt(atomic_item, option_count=4)
    three = parse_distractors(
        _three_option_output(),
        option_count=3,
        correct_answer=atomic_item.answer,
    )
    four = parse_distractors(
        _four_option_output(),
        option_count=4,
        correct_answer=atomic_item.answer,
    )

    assert "3 answer options" in three_prompt
    assert "plausible_misconception" not in three_prompt
    assert "4 answer options" in four_prompt
    assert "Keep options similar in structure" in four_prompt
    assert {option.kind for option in three} == {
        OptionKind.OPPOSITE_NEGATION,
        OptionKind.NEAR_MISS,
    }
    assert {option.kind for option in four} == {
        OptionKind.OPPOSITE_NEGATION,
        OptionKind.NEAR_MISS,
        OptionKind.PLAUSIBLE_MISCONCEPTION,
    }


@pytest.mark.parametrize("option_count", (3, 4))
def test_primary_mcq_generation_is_complete_and_pre_shuffle(
    option_count: int,
) -> None:
    atomic_item = AtomicItem("tok_item_question", "tok_answer")
    prompt = build_mcq_generation_prompt(
        atomic_item,
        option_count=option_count,
    )
    unshuffled = parse_mcq_generation(
        _generation_output(option_count),
        atomic_item=atomic_item,
        option_count=option_count,
    )
    first = shuffle_mcq_item(unshuffled, seed=11)
    second = shuffle_mcq_item(unshuffled, seed=11)

    assert "before shuffling" in prompt
    assert "Required pre-shuffle order and kinds" in prompt
    assert unshuffled.correct_label == "A"
    assert unshuffled.options[0].kind is OptionKind.CORRECT
    assert first == second


@pytest.mark.parametrize(
    ("option_count", "output"),
    ((3, _three_option_output()), (4, _four_option_output())),
)
def test_deterministic_shuffle_supports_both_sizes(
    option_count: int,
    output: str,
) -> None:
    atomic_item = AtomicItem("tok_item_question", "tok_answer")
    distractors = parse_distractors(output, option_count=option_count)
    first = shuffle_options(atomic_item, distractors, seed=9)
    second = shuffle_options(atomic_item, distractors, seed=9)

    assert first == second
    assert len(first.options) == option_count
    assert first.correct_label in option_labels(option_count)
    assert OptionKind.CORRECT in {option.kind for option in first.options}


def test_answer_prompt_and_parser_use_exact_appendix_shape() -> None:
    item = shuffle_options(
        AtomicItem("tok_item_question", "tok_answer"),
        parse_distractors(_four_option_output(), option_count=4),
        seed=9,
    )
    prompt = build_answer_prompt(
        item,
        personality_description="tok_profile",
        interview_context=("tok_context_a", "tok_context_b"),
    )
    parsed = parse_mcq_answer(
        f"Q1: {item.correct_label}",
        option_count=len(item.options),
    )

    assert "Do not use outside knowledge" in prompt
    assert "Include no reasoning" in prompt
    assert "tok_profile" in prompt
    assert parsed == item.correct_label
    with pytest.raises(ValueError, match="invalid or unavailable"):
        parse_mcq_answer('{"answer":"A"}', option_count=4)


def test_batched_answering_validates_every_item_and_scores_semantic_kinds() -> None:
    atomic_item = AtomicItem("tok_item_question", "tok_answer")
    item_three = shuffle_mcq_item(
        parse_mcq_generation(
            _generation_output(3),
            atomic_item=atomic_item,
            option_count=3,
        ),
        seed=3,
    )
    item_four = shuffle_mcq_item(
        parse_mcq_generation(
            _generation_output(4),
            atomic_item=atomic_item,
            option_count=4,
        ),
        seed=4,
    )
    items = (item_three, item_four)
    opposite_label = next(
        label
        for label, option in zip(option_labels(4), item_four.options)
        if option.kind is OptionKind.OPPOSITE_NEGATION
    )
    prompt = build_mcq_answering_prompt(
        items,
        personality_description="tok_profile",
        interview_context=("tok_context",),
    )
    answers = parse_mcq_answers(
        f"Q1: {item_three.correct_label}\nQ2: {opposite_label}",
        items,
    )
    score = score_mcq_answers(answers, items)

    assert "Q1." in prompt
    assert "Q2." in prompt
    assert "exactly one label per item" in prompt
    assert score.exact_accuracy == pytest.approx(0.5)
    assert score.rewards == (1.0, -1.0)
    assert score.mean_reward == pytest.approx(0.0)
    with pytest.raises(ValueError, match="unavailable label for Q1"):
        parse_mcq_answers(f"Q1: D\nQ2: {item_four.correct_label}", items)
    with pytest.raises(ValueError, match="answer count"):
        parse_mcq_answers(f"Q1: {item_three.correct_label}", items)


def test_exact_accuracy_and_kind_sensitive_reward() -> None:
    item = shuffle_options(
        AtomicItem("tok_item_question", "tok_answer"),
        parse_distractors(_four_option_output(), option_count=4),
        seed=9,
    )
    labels = option_labels(len(item.options))
    label_by_kind = {option.kind: label for label, option in zip(labels, item.options)}

    assert exact_accuracy(("A", "B", "C"), ("A", "C", "C")) == pytest.approx(2.0 / 3.0)
    assert mcq_reward(label_by_kind[OptionKind.CORRECT], item) == 1.0
    assert mcq_reward(label_by_kind[OptionKind.OPPOSITE_NEGATION], item) == -1.0
    assert mcq_reward(label_by_kind[OptionKind.NEAR_MISS], item) == -0.5
    assert mcq_reward(label_by_kind[OptionKind.PLAUSIBLE_MISCONCEPTION], item) == -0.5
    assert mcq_reward(None, item) == -0.5
    assert mcq_reward("tok_invalid", item) == -0.5


def test_exact_paired_sign_flip_test() -> None:
    result = paired_sign_flip_test((2.0, 2.0), (0.0, 0.0))
    greater = paired_sign_flip_test(
        (2.0, 2.0),
        (0.0, 0.0),
        alternative="greater",
    )

    assert result.observed_difference == pytest.approx(2.0)
    assert result.p_value == pytest.approx(0.5)
    assert result.evaluated_permutations == 4
    assert result.exact is True
    assert greater.p_value == pytest.approx(0.25)


def test_sampled_sign_flip_test_is_seeded() -> None:
    first = paired_sign_flip_test(
        (3.0, 2.0, 1.0),
        (0.0, 0.0, 0.0),
        exact_max_pairs=0,
        permutations=101,
        seed=5,
    )
    second = paired_sign_flip_test(
        (3.0, 2.0, 1.0),
        (0.0, 0.0, 0.0),
        exact_max_pairs=0,
        permutations=101,
        seed=5,
    )

    assert first == second
    assert first.exact is False
