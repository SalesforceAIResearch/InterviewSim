# Copyright (c) 2026 Salesforce, Inc.
# SPDX-License-Identifier: CC-BY-NC-4.0
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0
# International License. See LICENSE.txt in the repository root.

"""Small callable protocols for user-supplied text and embedding models."""

from __future__ import annotations

import math
from typing import Iterable, Protocol, Sequence, TypeAlias, runtime_checkable


Embedding: TypeAlias = tuple[float, ...]


@runtime_checkable
class Model(Protocol):
    """A callable that maps one prompt to one generated string."""

    def __call__(self, prompt: str, /) -> str:
        """Generate text for a prompt."""


@runtime_checkable
class Embedder(Protocol):
    """A batch callable that maps strings to numeric vectors."""

    def __call__(self, texts: Sequence[str], /) -> Sequence[Sequence[float]]:
        """Embed texts in input order."""


def call_model(model: Model, prompt: str) -> str:
    """Call a supplied model and validate its boundary types."""

    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-blank string")
    if not callable(model):
        raise TypeError("model must be callable")
    output = model(prompt)
    if not isinstance(output, str):
        raise TypeError("model output must be a string")
    return output


def call_embedder(embedder: Embedder, texts: Iterable[str]) -> tuple[Embedding, ...]:
    """Call a supplied batch embedder and validate finite equal-width vectors."""

    if not callable(embedder):
        raise TypeError("embedder must be callable")
    batch = tuple(texts)
    if not batch:
        return ()
    if any(not isinstance(text, str) or not text.strip() for text in batch):
        raise ValueError("embedding inputs must be non-blank strings")

    raw_vectors = embedder(batch)
    if isinstance(raw_vectors, (str, bytes)) or not isinstance(raw_vectors, Sequence):
        raise TypeError("embedder output must be a sequence of vectors")
    if len(raw_vectors) != len(batch):
        raise ValueError("embedder must return one vector per input")

    vectors: list[Embedding] = []
    width: int | None = None
    for row_index, raw_vector in enumerate(raw_vectors):
        if isinstance(raw_vector, (str, bytes)) or not isinstance(raw_vector, Sequence):
            raise TypeError(f"embedding {row_index} must be a numeric sequence")
        vector: list[float] = []
        for value in raw_vector:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"embedding {row_index} contains a non-number")
            number = float(value)
            if not math.isfinite(number):
                raise ValueError(f"embedding {row_index} contains a non-finite number")
            vector.append(number)
        if not vector:
            raise ValueError("embedding vectors must not be empty")
        if width is None:
            width = len(vector)
        elif len(vector) != width:
            raise ValueError("embedding vectors must have equal dimensions")
        vectors.append(tuple(vector))
    return tuple(vectors)
