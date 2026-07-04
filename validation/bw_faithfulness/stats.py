"""Pure-stdlib statistics for the faithfulness report.

Ported from Spaghetti Architect bench/grade.py (MIT, same author — NOTICE;
DOI 10.5281/zenodo.21033174). Deterministic: the bootstrap is seeded.
"""

from __future__ import annotations

import random


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def stdev(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5


def ci95_bootstrap(xs: list[float], iters: int = 2000, seed: int = 0) -> list[float]:
    """Deterministic percentile bootstrap 95% CI of the mean."""
    if len(xs) < 2 or stdev(xs) == 0.0:
        return [mean(xs), mean(xs)]
    rng = random.Random(seed)
    means = sorted(
        mean([xs[rng.randrange(len(xs))] for _ in range(len(xs))]) for _ in range(iters)
    )
    return [means[int(0.025 * iters)], means[int(0.975 * iters)]]


def _ranks(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = r
        i = j + 1
    return ranks


def spearman(x: list[float], y: list[float]) -> float:
    """Spearman rank correlation (ties share mean rank); 0.0 on degenerate input."""
    if len(x) != len(y) or len(x) < 2:
        return 0.0
    rx, ry = _ranks(x), _ranks(y)
    mx, my = mean(rx), mean(ry)
    sx = (sum((a - mx) ** 2 for a in rx)) ** 0.5
    sy = (sum((b - my) ** 2 for b in ry)) ** 0.5
    if sx == 0 or sy == 0:
        return 0.0
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / (sx * sy)
