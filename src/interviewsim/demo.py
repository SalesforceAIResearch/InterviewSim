# Copyright (c) 2026 Salesforce, Inc.
# SPDX-License-Identifier: CC-BY-NC-4.0
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0
# International License. See LICENSE.txt in the repository root.

"""Offline end-to-end demonstration logic for the synthetic fixture."""

from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path
import re
from typing import Sequence

from .evaluation import (
    BigFiveRating,
    BigFiveTrait,
    PersonalityLevel,
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
)
from .mcq import (
    AtomicItem,
    MCQItem,
    OptionKind,
    build_atomic_item_prompt,
    build_mcq_answering_prompt,
    build_mcq_generation_prompt,
    mcq_reward,
    option_labels,
    parse_atomic_item,
    parse_mcq_answers,
    parse_mcq_generation,
    score_mcq_answers,
    shuffle_mcq_item,
)
from .prompts import (
    ChronologicalPromptBuilder,
    HybridPromptBuilder,
    LongProfilePromptBuilder,
    ProfilePromptBuilder,
    RandomPromptBuilder,
    ResponsePromptContext,
    RetrievalPromptBuilder,
    SimplePromptBuilder,
)
from .schema import load_prepared_interviews
from .split import qa_pairs_from_interviews, temporal_train_test_split
from .statistics import paired_sign_flip_test


_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")
_EMBEDDING_DIMENSIONS = 24


def deterministic_local_embedder(
    texts: Sequence[str],
) -> tuple[tuple[float, ...], ...]:
    """Embed text with a stable signed token-hashing bag of words."""

    vectors: list[tuple[float, ...]] = []
    for text in texts:
        vector = [0.0] * _EMBEDDING_DIMENSIONS
        for token in _TOKEN_PATTERN.findall(text.casefold()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:2], "big") % _EMBEDDING_DIMENSIONS
            sign = 1.0 if digest[2] & 1 else -1.0
            vector[index] += sign
        vectors.append(tuple(vector))
    return tuple(vectors)


def _representative_content_similarity() -> tuple[float, int]:
    judgments = tuple(
        parse_content_similarity(output)
        for output in (
            '{"score":4,"explanation":"TOKEN_EXPLANATION_001"}',
            '{"score":3,"explanation":"TOKEN_EXPLANATION_002"}',
            '{"score":5,"explanation":"TOKEN_EXPLANATION_003"}',
        )
    )
    aggregate = aggregate_content_similarity(judgments)
    return aggregate.mean_score, aggregate.count


def _representative_factual_consistency() -> tuple[float, dict[str, int]]:
    judgments = tuple(
        parse_factual_consistency(output)
        for output in (
            '{"label":"Entailment","explanation":"TOKEN_EXPLANATION_001"}',
            '{"label":"Neutral","explanation":"TOKEN_EXPLANATION_002"}',
            '{"label":"Contradiction","explanation":"TOKEN_EXPLANATION_003"}',
        )
    )
    counts = Counter(judgment.label.value for judgment in judgments)
    return contradiction_ratio(judgments), dict(sorted(counts.items()))


def _representative_personality_similarity(
    responses: tuple[str, ...],
) -> tuple[int, dict[str, str], float]:
    runs = {}
    for trait in BigFiveTrait:
        build_personality_similarity_prompt(trait, responses)
        runs[trait] = tuple(
            parse_personality_trait(
                (
                    f"<rate>{level.value}</rate> "
                    f"<justification>TOKEN_{trait.value.upper()}_{index}</justification>"
                ),
                trait=trait,
            )
            for index, level in enumerate(
                (
                    PersonalityLevel.HIGH,
                    PersonalityLevel.HIGH,
                    PersonalityLevel.NEUTRAL,
                ),
                start=1,
            )
        )
    voted = vote_big_five(runs)
    neutral = BigFiveRating(
        PersonalityLevel.NEUTRAL,
        PersonalityLevel.NEUTRAL,
        PersonalityLevel.NEUTRAL,
        PersonalityLevel.NEUTRAL,
        PersonalityLevel.NEUTRAL,
    )
    return (
        len(runs),
        {trait.value: level.value for trait, level in voted.as_dict().items()},
        big_five_alignment(neutral, voted),
    )


def _mcq_generation_output(atomic_item: AtomicItem, option_count: int) -> str:
    options = [
        (f'{{"kind":"correct","text":"{atomic_item.answer}"}}'),
        '{"kind":"opposite_negation","text":"TOKEN_OPTION_OPPOSITE"}',
        '{"kind":"near_miss","text":"TOKEN_OPTION_NEAR"}',
    ]
    if option_count == 4:
        options.append(('{"kind":"plausible_misconception","text":"TOKEN_OPTION_PLAUSIBLE"}'))
    return (
        "{"
        f'"question":"{atomic_item.question}",'
        f'"options":[{",".join(options)}],'
        '"correct_answer":"A"'
        "}"
    )


def _representative_mcq(
    atomic_item: AtomicItem,
    option_count: int,
) -> tuple[MCQItem, dict[str, object]]:
    build_mcq_generation_prompt(atomic_item, option_count=option_count)
    unshuffled = parse_mcq_generation(
        _mcq_generation_output(atomic_item, option_count),
        atomic_item=atomic_item,
        option_count=option_count,
    )
    item = shuffle_mcq_item(unshuffled, seed=17)
    labels = option_labels(option_count)
    labels_by_kind = {option.kind: label for label, option in zip(labels, item.options)}
    rewards = {
        "correct": mcq_reward(labels_by_kind[OptionKind.CORRECT], item),
        "opposite_negation": mcq_reward(
            labels_by_kind[OptionKind.OPPOSITE_NEGATION],
            item,
        ),
        "near_miss": mcq_reward(labels_by_kind[OptionKind.NEAR_MISS], item),
        "invalid": mcq_reward("TOKEN_INVALID", item),
    }
    if option_count == 4:
        rewards["plausible_misconception"] = mcq_reward(
            labels_by_kind[OptionKind.PLAUSIBLE_MISCONCEPTION],
            item,
        )
    return item, {
        "option_count": option_count,
        "correct_label": item.correct_label,
        "rewards": rewards,
    }


def run_synthetic_demo(prepared_input: str | Path) -> dict[str, object]:
    """Run every public offline component and return a compact summary."""

    data = load_prepared_interviews(prepared_input)
    split = temporal_train_test_split(data.interviews)
    context = ResponsePromptContext.from_prepared(data)
    training_qa_pairs = qa_pairs_from_interviews(split.train)
    test_qa_pairs = qa_pairs_from_interviews(split.test)
    target = test_qa_pairs[0]

    builders = {
        "simple": SimplePromptBuilder(),
        "profile": ProfilePromptBuilder(),
        "long_profile": LongProfilePromptBuilder(),
        "chronological": ChronologicalPromptBuilder(example_count=4),
        "random": RandomPromptBuilder(example_count=4, seed=17),
        "retrieval": RetrievalPromptBuilder(
            deterministic_local_embedder,
            example_count=4,
        ),
        "hybrid": HybridPromptBuilder(
            deterministic_local_embedder,
            k1=2,
            k2=2,
        ),
    }
    generation_prompts = {
        name: builder.build(target.question, context) for name, builder in builders.items()
    }

    build_content_similarity_prompt(
        target.response,
        "TOKEN_GENERATED_ANSWER",
        question=target.question,
        personality_id=data.personality_id,
    )
    content_mean, content_count = _representative_content_similarity()

    held_out_responses = tuple(qa_pair.response for qa_pair in test_qa_pairs)
    build_fact_summary_prompt(held_out_responses)
    fact_summary = parse_fact_summary(
        ('{"summary":"TOKEN_FACT_SUMMARY","explanation":"TOKEN_SUMMARY_EXPLANATION"}')
    )
    build_factual_consistency_prompt(
        fact_summary_text(fact_summary),
        "TOKEN_GENERATED_ANSWER",
        question=target.question,
        personality_id=data.personality_id,
    )
    contradiction, factual_counts = _representative_factual_consistency()

    response_collection = tuple(qa_pair.response for qa_pair in training_qa_pairs[:3])
    trait_prompt_count, voted_levels, alignment = _representative_personality_similarity(
        response_collection
    )

    build_atomic_item_prompt(target)
    atomic_item = parse_atomic_item(
        "Atomic Question: TOKEN_ATOMIC_QUESTION\nAtomic Answer: TOKEN_ATOMIC_ANSWER"
    )
    item_three, mcq_three = _representative_mcq(atomic_item, 3)
    item_four, mcq_four = _representative_mcq(atomic_item, 4)
    mcq_items = (item_three, item_four)
    build_mcq_answering_prompt(
        mcq_items,
        personality_description="TOKEN_PROFILE",
        interview_context=("TOKEN_CONTEXT_001", "TOKEN_CONTEXT_002"),
    )
    answer_output = "\n".join(
        f"Q{index}: {item.correct_label}" for index, item in enumerate(mcq_items, start=1)
    )
    parsed_answers = parse_mcq_answers(answer_output, mcq_items)
    mcq_score = score_mcq_answers(
        parsed_answers,
        mcq_items,
    )

    permutation = paired_sign_flip_test(
        (0.8, 0.7, 0.9, 0.6),
        (0.5, 0.6, 0.7, 0.5),
    )

    return {
        "input": {
            "schema_version": data.schema_version,
            "personality_id": data.personality_id,
            "interviews": len(data.interviews),
            "qa_pairs": len(training_qa_pairs) + len(test_qa_pairs),
        },
        "split": {
            "train_interviews": len(split.train),
            "test_interviews": len(split.test),
            "train_qa_pairs": len(training_qa_pairs),
            "test_qa_pairs": len(test_qa_pairs),
        },
        "generation": {
            "strategies": tuple(builders),
            "prompt_count": len(generation_prompts),
            "all_prompts_non_empty": all(generation_prompts.values()),
            "hybrid_k1": 2,
            "hybrid_k2": 2,
            "hybrid_profile_free": (
                data.personality.profile not in generation_prompts["hybrid"]
                and data.personality.long_profile not in generation_prompts["hybrid"]
            ),
        },
        "content_similarity": {
            "judgment_count": content_count,
            "raw_mean": content_mean,
        },
        "factual_consistency": {
            "label_counts": factual_counts,
            "contradiction_ratio": contradiction,
        },
        "fact_summary": {
            "held_out_response_count": len(held_out_responses),
            "parsed": bool(fact_summary.summary and fact_summary.explanation),
            "fields": ("summary", "explanation"),
        },
        "personality_similarity": {
            "trait_prompt_count": trait_prompt_count,
            "runs_per_trait": 3,
            "voted_levels": voted_levels,
            "alignment": alignment,
        },
        "mcq": {
            "formats": (mcq_three, mcq_four),
            "batch_size": len(mcq_items),
            "parsed_answer_count": len(parsed_answers),
            "exact_accuracy": mcq_score.exact_accuracy,
            "mean_reward": mcq_score.mean_reward,
        },
        "permutation_test": {
            "observed_difference": permutation.observed_difference,
            "p_value": permutation.p_value,
            "exact": permutation.exact,
            "evaluated_permutations": permutation.evaluated_permutations,
        },
    }
