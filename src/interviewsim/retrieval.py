# Copyright (c) 2026 Salesforce, Inc.
# SPDX-License-Identifier: CC-BY-NC-4.0
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0
# International License. See LICENSE.txt in the repository root.

"""Offline cosine retrieval over prepared QA pairs."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable, Iterable, Sequence

from .protocols import Embedder, Embedding, call_embedder
from .schema import QAPair


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """One ranked QA pair and its cosine score."""

    qa_pair: QAPair
    score: float


def _numeric_vector(values: Iterable[float], name: str) -> Embedding:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name} must be a numeric iterable")
    vector: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} contains a non-number")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{name} contains a non-finite number")
        vector.append(number)
    if not vector:
        raise ValueError(f"{name} must not be empty")
    return tuple(vector)


def cosine_similarity(left: Iterable[float], right: Iterable[float]) -> float:
    """Compute cosine similarity, treating a zero vector as zero similarity."""

    left_vector = _numeric_vector(left, "left vector")
    right_vector = _numeric_vector(right, "right vector")
    if len(left_vector) != len(right_vector):
        raise ValueError("vectors must have equal dimensions")
    left_norm = math.sqrt(sum(value * value for value in left_vector))
    right_norm = math.sqrt(sum(value * value for value in right_vector))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    score = sum(a * b for a, b in zip(left_vector, right_vector))
    score /= left_norm * right_norm
    return max(-1.0, min(1.0, score))


def rank_qa_pairs(
    query_embedding: Iterable[float],
    qa_pairs: Sequence[QAPair],
    qa_embeddings: Sequence[Iterable[float]],
    *,
    k: int,
) -> tuple[RetrievalResult, ...]:
    """Rank QA pairs from precomputed vectors with stable tie breaking."""

    if isinstance(k, bool) or not isinstance(k, int):
        raise TypeError("k must be an integer")
    if k < 0:
        raise ValueError("k must not be negative")
    if len(qa_pairs) != len(qa_embeddings):
        raise ValueError("QA pairs and embeddings must have equal lengths")
    if any(not isinstance(qa_pair, QAPair) for qa_pair in qa_pairs):
        raise TypeError("all values must be QAPair instances")
    qa_ids = [qa_pair.qa_id for qa_pair in qa_pairs]
    if len(set(qa_ids)) != len(qa_ids):
        raise ValueError("qa_id values must be unique")
    if not qa_pairs or k == 0:
        return ()

    query_vector = _numeric_vector(query_embedding, "query embedding")
    scored = tuple(
        RetrievalResult(
            qa_pair=qa_pair,
            score=cosine_similarity(
                query_vector,
                _numeric_vector(embedding, f"QA embedding {index}"),
            ),
        )
        for index, (qa_pair, embedding) in enumerate(zip(qa_pairs, qa_embeddings))
    )
    return tuple(
        sorted(scored, key=lambda result: (-result.score, result.qa_pair.qa_id))[
            : min(k, len(scored))
        ]
    )


def retrieve_qa_pairs(
    query: str,
    qa_pairs: Iterable[QAPair],
    embedder: Embedder,
    *,
    k: int,
    text_builder: Callable[[QAPair], str] | None = None,
) -> tuple[RetrievalResult, ...]:
    """Embed a query and training QA text, then return top cosine matches."""

    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-blank string")
    values = tuple(qa_pairs)
    if text_builder is None:
        text_builder = lambda qa_pair: qa_pair.question
    texts = tuple(text_builder(qa_pair) for qa_pair in values)
    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError("text_builder must return non-blank strings")
    vectors = call_embedder(embedder, (query, *texts))
    if not values:
        if isinstance(k, bool) or not isinstance(k, int):
            raise TypeError("k must be an integer")
        if k < 0:
            raise ValueError("k must not be negative")
        return ()
    return rank_qa_pairs(vectors[0], values, vectors[1:], k=k)
