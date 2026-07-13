"""Cross-check the tree-sitter Python cyclomatic path against the ported
stdlib-ast reference lane (ARCHITECTURE.md §8.2).

The two lanes agree on if/elif/loops/except/boolops/comprehension-guards; they
RULEDLY diverge on ternaries (CC-PY-0007: we count, the reference does not) and
match/case (CC-PY-0008). Inputs here avoid the divergent constructs; a
divergence case asserts the divergence itself so it can never go stale
silently.
"""

from __future__ import annotations

import pytest
from _reference import py_ast_lane
from conftest import corpus_cases, is_reference_comparable

from codecaliper import measure
from codecaliper.model import metric_map

PY_CASES = [c for c in corpus_cases()
            if c["language"] == "python" and is_reference_comparable(c)]

AGREEING_SNIPPETS = {
    "plain": "x = 1\n",
    "if-elif-else": (
        "def f(x):\n    if x > 2:\n        return 1\n    elif x > 1:\n"
        "        return 2\n    else:\n        return 3\n"
    ),
    "loops-and-except": (
        "for i in range(3):\n    while i:\n        i -= 1\n"
        "try:\n    pass\nexcept ValueError:\n    pass\nexcept KeyError:\n    pass\n"
    ),
    "boolops": "flag = a and b and c or d\n",
    "comprehension": "ys = [i for i in xs if i > 0 if i < 9]\n",
}


def _our_cc(src: str) -> int:
    rep = measure(src, language="python", metrics=("cyclomatic",), readability=())
    return int(metric_map(rep.file_metrics)["cyclomatic"].value)


# Rulings where the tree-sitter lane KNOWINGLY diverges from the stdlib-ast
# reference (ternaries, match/case). The divergences are asserted EXACTLY by
# the dedicated tests below, so corpus cases citing them are excluded from the
# equality sweep, so an accidental "fix" of either lane still surfaces.
DIVERGENT_RULINGS = {"CC-PY-0007", "CC-PY-0008"}
AGREEING_CASES = [
    c for c in PY_CASES
    if not DIVERGENT_RULINGS & set(c["expected"]["case"].get("rulings", []))
]


@pytest.mark.parametrize("case", AGREEING_CASES, ids=[c["id"] for c in AGREEING_CASES])
def test_corpus_cc_matches_reference(case: dict) -> None:
    assert _our_cc(case["source"]) == py_ast_lane.cyclomatic(case["source"])


@pytest.mark.parametrize("name", sorted(AGREEING_SNIPPETS), ids=sorted(AGREEING_SNIPPETS))
def test_snippet_cc_matches_reference(name: str) -> None:
    src = AGREEING_SNIPPETS[name]
    assert _our_cc(src) == py_ast_lane.cyclomatic(src)


def test_ternary_divergence_is_ruled() -> None:
    """CC-PY-0007: we count conditional expressions; the reference lane does
    not. Assert the divergence EXACTLY so an accidental 'fix' of either lane
    surfaces here and forces a spec decision."""
    src = "y = 1 if x else 2\n"
    ours = _our_cc(src)
    theirs = py_ast_lane.cyclomatic(src)
    assert ours == 2 and theirs == 1, (
        f"ternary divergence drifted: ours={ours} (expect 2, CC-PY-0007), "
        f"reference={theirs} (expect 1)"
    )


def test_match_case_divergence_is_ruled() -> None:
    """CC-PY-0008: non-wildcard case clauses count +1 each (the bare-wildcard
    `case _:` mirrors Java default and does not); the reference lane counts
    match statements not at all. Asserted exactly, like the ternary case."""
    src = (
        "match x:\n"
        "    case 1:\n"
        "        y = 1\n"
        "    case 2:\n"
        "        y = 2\n"
        "    case _:\n"
        "        y = 0\n"
    )
    ours = _our_cc(src)
    theirs = py_ast_lane.cyclomatic(src)
    assert ours == 3 and theirs == 1, (
        f"match/case divergence drifted: ours={ours} (expect 3 = 1 + two "
        f"non-wildcard cases, CC-PY-0008), reference={theirs} (expect 1)"
    )
