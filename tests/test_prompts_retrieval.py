# Copyright (c) 2026 Salesforce, Inc.
# SPDX-License-Identifier: CC-BY-NC-4.0
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0
# International License. See LICENSE.txt in the repository root.

from __future__ import annotations

from typing import Sequence

import pytest

from interviewsim import (
    ChronologicalPromptBuilder,
    HybridPromptBuilder,
    Interview,
    LongProfilePromptBuilder,
    Personality,
    PreparedInterviewData,
    ProfilePromptBuilder,
    QAPair,
    RandomPromptBuilder,
    ResponsePromptContext,
    RetrievalPromptBuilder,
    SimplePromptBuilder,
    call_embedder,
    call_model,
    cosine_similarity,
    rank_qa_pairs,
    retrieve_qa_pairs,
)


def _qa_pair(index: int) -> QAPair:
    return QAPair(
        qa_id=f"q_{index:03d}",
        question=f"tok_question_{index:03d}",
        response=f"tok_response_{index:03d}",
        tags=(f"tok_tag_{index:03d}",),
    )


def _prepared() -> PreparedInterviewData:
    return PreparedInterviewData(
        schema_version="1.0",
        personality_id="p_001",
        personality=Personality("tok_profile_short", "tok_profile_long"),
        interviews=tuple(
            Interview(
                interview_id=f"i_{index:03d}",
                sequence=index,
                qa_pairs=(_qa_pair(index),),
            )
            for index in reversed(range(10))
        ),
    )


def _embed(texts: Sequence[str]) -> Sequence[Sequence[float]]:
    vectors = []
    for text in texts:
        if text in {"tok_query", "tok_question_000"}:
            vectors.append((1.0, 0.0))
        else:
            vectors.append((0.0, 1.0))
    return vectors


def _embed_latest(texts: Sequence[str]) -> Sequence[Sequence[float]]:
    return [
        (1.0, 0.0) if text in {"tok_query", "tok_question_007"} else (0.0, 1.0) for text in texts
    ]


def test_callable_protocol_helpers_validate_boundaries() -> None:
    assert call_model(lambda prompt: f"{prompt}_output", "tok_prompt") == ("tok_prompt_output")
    assert call_embedder(_embed, ["tok_prompt"]) == ((0.0, 1.0),)

    with pytest.raises(ValueError, match="one vector"):
        call_embedder(lambda texts: [], ["tok_prompt"])


def test_qa_cosine_retrieval_is_stable() -> None:
    qa_pairs = (_qa_pair(1), _qa_pair(0))
    ranked = rank_qa_pairs(
        (1.0, 0.0),
        qa_pairs,
        ((1.0, 0.0), (1.0, 0.0)),
        k=2,
    )
    retrieved = retrieve_qa_pairs("tok_query", qa_pairs, _embed, k=1)

    assert cosine_similarity((1.0, 0.0), (0.0, 1.0)) == pytest.approx(0.0)
    assert tuple(result.qa_pair.qa_id for result in ranked) == ("q_000", "q_001")
    assert retrieved[0].qa_pair.qa_id == "q_000"


def test_context_derives_training_interviews_before_qa_selection() -> None:
    context = ResponsePromptContext.from_prepared(_prepared())

    assert tuple(interview.sequence for interview in context.training_interviews) == tuple(range(8))
    assert tuple(qa_pair.qa_id for qa_pair in context.training_qa_pairs) == tuple(
        f"q_{index:03d}" for index in range(8)
    )


def test_simple_and_profile_strategies() -> None:
    context = ResponsePromptContext.from_prepared(_prepared())
    simple = SimplePromptBuilder().build("tok_query", context)
    profile = ProfilePromptBuilder().build("tok_query", context)
    long_profile = LongProfilePromptBuilder().build("tok_query", context)

    assert "Training examples:" not in simple
    assert "tok_profile_short" in profile
    assert "tok_profile_long" in long_profile
    assert simple.endswith("Response:")


def test_example_strategies_never_use_held_out_interviews() -> None:
    context = ResponsePromptContext.from_prepared(_prepared())
    prompts = (
        ChronologicalPromptBuilder(example_count=2).build("tok_query", context),
        RandomPromptBuilder(example_count=4, seed=7).build("tok_query", context),
        RetrievalPromptBuilder(_embed, example_count=4).build("tok_query", context),
        HybridPromptBuilder(
            _embed,
            k1=2,
            k2=2,
        ).build("tok_query", context),
    )

    for prompt in prompts:
        assert "tok_response_008" not in prompt
        assert "tok_response_009" not in prompt
    assert "tok_response_006" in prompts[0]
    assert "tok_response_007" in prompts[0]
    assert prompts[1] == RandomPromptBuilder(example_count=4, seed=7).build("tok_query", context)
    assert "tok_response_000" in prompts[2]


def test_hybrid_is_profile_free_and_deduplicates_with_relevance_priority() -> None:
    context = ResponsePromptContext.from_prepared(_prepared())
    prompt = HybridPromptBuilder(_embed_latest, k1=1, k2=2).build(
        "tok_query",
        context,
    )

    assert "tok_profile_short" not in prompt
    assert "tok_profile_long" not in prompt
    assert prompt.count("tok_response_007") == 1
    assert prompt.count("Example ") == 2
    assert prompt.index("tok_response_007") < prompt.index("tok_response_006")
