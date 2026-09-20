# Copyright (c) 2026 Salesforce, Inc.
# SPDX-License-Identifier: CC-BY-NC-4.0
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0
# International License. See LICENSE.txt in the repository root.

from __future__ import annotations

import pytest

from interviewsim import (
    PERSONALITY_LEVEL_ORDINALS,
    BigFiveRating,
    BigFiveTrait,
    FactualConsistencyLabel,
    PersonalityLevel,
    PersonalityTraitJudgment,
    aggregate_content_similarity,
    big_five_alignment,
    build_content_similarity_prompt,
    build_fact_summary_prompt,
    build_factual_consistency_prompt,
    build_personality_similarity_prompt,
    contradiction_ratio,
    fact_summary_text,
    parse_content_similarity,
    parse_factual_consistency,
    parse_fact_summary,
    parse_personality_trait,
    vote_big_five,
    vote_personality_trait,
)


def _trait_judgment(
    trait: BigFiveTrait,
    level: PersonalityLevel,
    token: str,
) -> PersonalityTraitJudgment:
    return PersonalityTraitJudgment(
        trait=trait,
        level=level,
        explanation=token,
    )


def _rating(level: PersonalityLevel) -> BigFiveRating:
    return BigFiveRating(level, level, level, level, level)


def test_content_prompt_parser_and_raw_mean_include_explanation() -> None:
    prompt = build_content_similarity_prompt(
        "tok_reference",
        "tok_candidate",
        question="tok_question",
        personality_id="p_001",
    )
    low = parse_content_similarity('{"score":1,"explanation":"tok_explanation_low"}')
    high = parse_content_similarity(
        '```json\n{"score":5,"explanation":"tok_explanation_high"}\n```'
    )
    aggregate = aggregate_content_similarity((low, high))

    assert "same core ideas" in prompt
    assert "key content is preserved" in prompt
    assert "missing key information" in prompt
    assert '"explanation": "..."' in prompt
    assert low.explanation == "tok_explanation_low"
    assert aggregate.mean_score == pytest.approx(3.0)
    with pytest.raises(ValueError, match="requires score and explanation"):
        parse_content_similarity('{"score":3}')


def test_factual_prompt_carries_missing_information_and_uncertainty_rules() -> None:
    prompt = build_factual_consistency_prompt(
        "tok_summary",
        "tok_answer",
        question="tok_question",
        personality_id="p_001",
    )
    entailment = parse_factual_consistency('{"label":"Entailment","explanation":"tok_entailment"}')
    neutral = parse_factual_consistency('{"label":"Neutral","explanation":"tok_neutral"}')
    contradiction = parse_factual_consistency(
        '{"label":"Contradiction","explanation":"tok_contradiction"}'
    )

    assert "Missing information is not a contradiction" in prompt
    assert "If uncertain, prefer Neutral" in prompt
    assert "Opinions may evolve over time" in prompt
    assert entailment.label is FactualConsistencyLabel.ENTAILMENT
    assert contradiction_ratio((entailment, neutral, contradiction)) == pytest.approx(1.0 / 3.0)
    with pytest.raises(ValueError, match="requires label and explanation"):
        parse_factual_consistency('{"label":"Neutral"}')


def test_fact_summary_uses_only_held_out_responses_and_strict_fields() -> None:
    prompt = build_fact_summary_prompt(
        ("tok_held_out_a", "tok_held_out_b"),
    )
    summary = parse_fact_summary('{"summary":"tok_summary","explanation":"tok_explanation"}')

    assert "using only the supplied held-out responses" in prompt
    assert "Do not use external facts" in prompt
    assert "without citations, links, source identifiers, or provenance fields" in prompt
    assert "Response 1:\ntok_held_out_a" in prompt
    assert fact_summary_text(summary) == "tok_summary"
    with pytest.raises(ValueError, match="requires summary and explanation"):
        parse_fact_summary(
            ('{"summary":"tok_summary","explanation":"tok_explanation","tok_extra":"tok_value"}')
        )


def test_trait_prompt_is_specific_and_accepts_response_collection() -> None:
    prompt = build_personality_similarity_prompt(
        BigFiveTrait.OPENNESS,
        ("tok_response_a", "tok_response_b"),
    )
    judgment = parse_personality_trait(
        ("<rate>High</rate> <justification>tok_trait_explanation</justification>"),
        trait=BigFiveTrait.OPENNESS,
    )

    assert "how much openness" in prompt
    assert "curiosity" in prompt
    assert "Response 1:\ntok_response_a" in prompt
    assert "Response 2:\ntok_response_b" in prompt
    assert judgment.level is PersonalityLevel.HIGH
    assert judgment.explanation == "tok_trait_explanation"


def test_three_independent_runs_use_mode_and_confidence() -> None:
    trait = BigFiveTrait.EXTRAVERSION
    vote = vote_personality_trait(
        (
            _trait_judgment(trait, PersonalityLevel.HIGH, "tok_run_a"),
            _trait_judgment(trait, PersonalityLevel.HIGH, "tok_run_b"),
            _trait_judgment(trait, PersonalityLevel.NEUTRAL, "tok_run_c"),
        )
    )

    assert vote.level is PersonalityLevel.HIGH
    assert vote.confidence == pytest.approx(2.0 / 3.0)
    with pytest.raises(ValueError, match="exactly three"):
        vote_personality_trait((_trait_judgment(trait, PersonalityLevel.HIGH, "tok_run"),))


def test_big_five_vote_and_alignment_use_appendix_ordinals() -> None:
    runs = {
        trait: (
            _trait_judgment(trait, PersonalityLevel.LOW, "tok_run_a"),
            _trait_judgment(trait, PersonalityLevel.LOW, "tok_run_b"),
            _trait_judgment(trait, PersonalityLevel.HIGH, "tok_run_c"),
        )
        for trait in BigFiveTrait
    }
    voted = vote_big_five(runs)

    assert PERSONALITY_LEVEL_ORDINALS == {
        PersonalityLevel.LOW: 1,
        PersonalityLevel.NEUTRAL: 2,
        PersonalityLevel.HIGH: 3,
    }
    assert voted == _rating(PersonalityLevel.LOW)
    assert big_five_alignment(voted, voted) == pytest.approx(1.0)
    assert big_five_alignment(
        _rating(PersonalityLevel.LOW),
        _rating(PersonalityLevel.HIGH),
    ) == pytest.approx(0.0)
