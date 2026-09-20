# Copyright (c) 2026 Salesforce, Inc.
# SPDX-License-Identifier: CC-BY-NC-4.0
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0
# International License. See LICENSE.txt in the repository root.

"""Paired sign-flip permutation inference with deterministic sampling."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Iterable, Literal


Alternative = Literal["two-sided", "greater", "less"]


@dataclass(frozen=True, slots=True)
class PermutationTestResult:
    """Result of a paired sign-flip permutation test."""

    observed_difference: float
    p_value: float
    pair_count: int
    effective_pair_count: int
    evaluated_permutations: int
    exact: bool
    alternative: Alternative


def _numbers(values: Iterable[float], name: str) -> tuple[float, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name} must be an iterable of numbers")
    result: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} contains a non-number")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{name} contains a non-finite number")
        result.append(number)
    return tuple(result)


def _is_extreme(value: float, observed: float, alternative: Alternative) -> bool:
    tolerance = 1e-12 * max(1.0, abs(value), abs(observed))
    if alternative == "greater":
        return value >= observed - tolerance
    if alternative == "less":
        return value <= observed + tolerance
    return abs(value) >= abs(observed) - tolerance


def paired_sign_flip_test(
    first: Iterable[float],
    second: Iterable[float],
    *,
    alternative: Alternative = "two-sided",
    exact_max_pairs: int = 20,
    permutations: int = 10_000,
    seed: int = 0,
) -> PermutationTestResult:
    """Test the paired mean difference under exchangeable difference signs.

    All sign assignments are enumerated when the number of nonzero pairs is at
    most ``exact_max_pairs``. Larger inputs use seeded Monte Carlo draws and an
    add-one p-value correction.
    """

    first_values = _numbers(first, "first")
    second_values = _numbers(second, "second")
    if len(first_values) != len(second_values):
        raise ValueError("paired inputs must have equal lengths")
    if not first_values:
        raise ValueError("at least one pair is required")
    if alternative not in {"two-sided", "greater", "less"}:
        raise ValueError("alternative must be two-sided, greater, or less")
    if isinstance(exact_max_pairs, bool) or not isinstance(exact_max_pairs, int):
        raise TypeError("exact_max_pairs must be an integer")
    if exact_max_pairs < 0:
        raise ValueError("exact_max_pairs must not be negative")
    if isinstance(permutations, bool) or not isinstance(permutations, int):
        raise TypeError("permutations must be an integer")
    if permutations < 1:
        raise ValueError("permutations must be at least one")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")

    differences = tuple(left - right for left, right in zip(first_values, second_values))
    nonzero = tuple(value for value in differences if value != 0.0)
    observed_sum = math.fsum(nonzero)
    observed_difference = math.fsum(differences) / len(differences)

    if not nonzero:
        return PermutationTestResult(
            observed_difference=0.0,
            p_value=1.0,
            pair_count=len(differences),
            effective_pair_count=0,
            evaluated_permutations=1,
            exact=True,
            alternative=alternative,
        )

    if len(nonzero) <= exact_max_pairs:
        assignment_count = 1 << len(nonzero)
        extreme_count = 0
        for mask in range(assignment_count):
            permuted_sum = math.fsum(
                value if mask & (1 << index) else -value for index, value in enumerate(nonzero)
            )
            if _is_extreme(permuted_sum, observed_sum, alternative):
                extreme_count += 1
        p_value = extreme_count / assignment_count
        evaluated = assignment_count
        exact = True
    else:
        generator = random.Random(seed)
        extreme_count = 0
        for _ in range(permutations):
            permuted_sum = math.fsum(
                value if generator.getrandbits(1) else -value for value in nonzero
            )
            if _is_extreme(permuted_sum, observed_sum, alternative):
                extreme_count += 1
        p_value = (extreme_count + 1) / (permutations + 1)
        evaluated = permutations
        exact = False

    return PermutationTestResult(
        observed_difference=observed_difference,
        p_value=p_value,
        pair_count=len(differences),
        effective_pair_count=len(nonzero),
        evaluated_permutations=evaluated,
        exact=exact,
        alternative=alternative,
    )
