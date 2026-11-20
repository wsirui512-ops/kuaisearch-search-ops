"""Small statistics helpers, kept dependency-free so the pipeline stays reproducible."""

from __future__ import annotations

import math


def wilson_interval(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion."""
    if trials <= 0:
        return (0.0, 0.0)
    p = successes / trials
    denominator = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denominator
    margin = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def two_sided_p_value(z_score: float) -> float:
    """Normal-approximation p-value."""
    return math.erfc(abs(z_score) / math.sqrt(2))


def compare_rate(observed: int, trials: int, expected_rate: float) -> float:
    """Two-sided p-value for a binomial count against an expected rate.

    The expected rate is treated as fixed (estimated on the train split), which makes
    the test slightly optimistic; it is used for triage, not for causal claims.
    """
    if trials <= 0 or not 0 < expected_rate < 1:
        return 1.0
    observed_rate = observed / trials
    standard_error = math.sqrt(expected_rate * (1 - expected_rate) / trials)
    if standard_error == 0:
        return 1.0
    return two_sided_p_value((observed_rate - expected_rate) / standard_error)


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    """q-values controlling the false discovery rate; input order is preserved."""
    total = len(p_values)
    if total == 0:
        return []
    ranked = sorted(range(total), key=lambda index: p_values[index])
    q_values = [1.0] * total
    running = 1.0
    for rank, index in enumerate(reversed(ranked), start=1):
        position = total - rank + 1
        running = min(running, p_values[index] * total / position)
        q_values[index] = min(1.0, running)
    return q_values
