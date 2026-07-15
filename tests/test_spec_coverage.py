"""Bidirectional rulings ⇄ code ⇄ corpus coverage (ARCHITECTURE.md §3.3).

- every ruling ID cited anywhere (corpus, ruling examples, src/ code) exists;
- every ruling's `examples` case exists AND cites the ruling back in its
  [case].rulings (self-attested examples that assert nothing are rejected);
- every ACTIVE ruling is cited by >= 1 corpus case, except the explicit
  UNCOVERED allowlist below, which must SHRINK to empty before 1.0 and may
  never grow (a new ruling without a case is a red build);
- src/ never imports the test-only reference oracles (anti-salami boundary).
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import corpus_cases

from codecaliper.spec import iter_rulings, ruling

CASES = corpus_cases()
CASE_IDS = {c["id"] for c in CASES}
SRC = Path(__file__).parent.parent / "src" / "codecaliper"

#: Rulings not yet exercised by a corpus case. SHRINK-ONLY: adding to this list
#: is a review-visible act of debt. The 1.0 gate is an empty list, reached
#: 2026-07-05 (W4-5). It must stay empty: a new ruling ships with its case.
UNCOVERED: frozenset[str] = frozenset()

_RULING_ID_RE = re.compile(r"\b(?:CORE|TOK|CC|COG|HAL|MI|LOC|BW)-(?:ALL|PY|JAVA|GO)-\d{4}\b")


def test_corpus_citations_exist() -> None:
    for case in CASES:
        for rid in case["expected"]["case"].get("rulings", []):
            ruling(rid)  # raises SpecError on a phantom citation


def test_ruling_examples_exist_and_cite_back() -> None:
    by_case = {
        c["id"]: set(c["expected"]["case"].get("rulings", [])) for c in CASES
    }
    for r in iter_rulings():
        for example in r.examples:
            assert example in CASE_IDS, (
                f"{r.id} names normative case {example!r} which does not exist"
            )
            assert r.id in by_case[example], (
                f"{r.id} claims {example} as a normative example, but that case "
                f"does not cite {r.id} in its [case].rulings; self-attested "
                "examples are vacuous"
            )


def test_active_rulings_are_covered() -> None:
    cited: set[str] = set()
    for case in CASES:
        cited.update(case["expected"]["case"].get("rulings", []))
    uncovered_now = {
        r.id for r in iter_rulings() if r.status == "active" and r.id not in cited
    }
    new_debt = uncovered_now - UNCOVERED
    assert not new_debt, (
        f"new active rulings without corpus coverage: {sorted(new_debt)}. "
        "add a corpus case or (visibly) extend UNCOVERED"
    )
    paid_off = UNCOVERED - uncovered_now
    assert not paid_off, (
        f"rulings now covered but still allowlisted: {sorted(paid_off)}. "
        "remove them from UNCOVERED (shrink-only)"
    )


def test_all_ruling_ids_in_src_resolve() -> None:
    """Any ruling-ID-shaped string anywhere in src/ must exist in the registry,
    docstrings and comments included, so no citation can go phantom."""
    for py in SRC.rglob("*.py"):
        for rid in _RULING_ID_RE.findall(py.read_text(encoding="utf-8")):
            ruling(rid)


def test_supersession_chain_is_consistent() -> None:
    """A superseded ruling must name a resolvable, ACTIVE successor, and a
    superseded_by pointer may only appear on superseded rulings. The chain is
    registry data the CLI and generated docs surface, so it may not dangle."""
    for r in iter_rulings():
        if r.status == "superseded":
            assert r.superseded_by, f"{r.id} is superseded but names no successor"
            successor = ruling(r.superseded_by)  # raises SpecError if phantom
            assert successor.status == "active", (
                f"{r.id} is superseded by {successor.id}, which is not active"
            )
        else:
            assert not r.superseded_by, (
                f"{r.id} has superseded_by={r.superseded_by!r} but status={r.status!r}"
            )


def test_src_never_imports_test_oracles() -> None:
    """Anti-salami boundary (ARCHITECTURE.md §1 invariant 3)."""
    banned = ("tests._reference", "_reference.bw_stdlib", "_reference.py_ast_lane",
              "import radon", "import lizard", "import cognitive_complexity")
    for py in SRC.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for pattern in banned:
            assert pattern not in text, f"{py} references banned test-only code: {pattern}"
