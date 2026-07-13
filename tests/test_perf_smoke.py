"""Performance smoke (ARCHITECTURE.md §8.4): a generous throughput floor that
catches the easy regression class (per-call spec reloads, per-call parser
construction) without CI flakiness. The declared audience measures 10^5-10^6
snippets.
"""

from __future__ import annotations

import time

from conftest import corpus_cases

from codecaliper import Session
from codecaliper.languages import get_adapter


def test_session_reuses_adapter_and_parser() -> None:
    a1 = get_adapter("python")
    a2 = get_adapter("python")
    assert a1 is a2, "adapters must be cached (parser reuse)"
    a1._ensure_loaded()
    p1 = a1._parser
    a2._ensure_loaded()
    assert a2._parser is p1


def test_throughput_floor() -> None:
    session = Session()
    cases = corpus_cases()
    n = 0
    start = time.perf_counter()
    for _ in range(20):
        for case in cases:
            session.measure(case["source"], language=case["language"])
            n += 1
    elapsed = time.perf_counter() - start
    rate = n / elapsed
    assert rate > 50, (
        f"measured {rate:.0f} snippets/s, below the 50/s smoke floor; "
        "check for per-call spec reloads or parser construction"
    )
