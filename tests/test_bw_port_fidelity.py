"""The tree-sitter BW port must equal the proven stdlib reference extractor
per feature (ARCHITECTURE.md §8.2: the per-PR, zero-install differential
witness for the crown jewel).

Inputs avoid the RULED divergence: f-strings with interpolations (TOK-PY-0002
vs PEP 701 tokenize). Match statements ARE comparable, since both lanes classify
the soft keywords as identifiers (BW-PY-0001), and are exercised below.
"""

from __future__ import annotations

import math

import pytest
from _reference.bw_stdlib import bw_readability_features
from conftest import corpus_cases, is_reference_comparable

from codecaliper import measure

PY_CASES = [c for c in corpus_cases()
            if c["language"] == "python" and is_reference_comparable(c)]

EXTRA_SNIPPETS = {
    "empty-ish": "x = 1\n",
    "operators": "y = (a + b) * c ** 2 - d // e % f\nz = y >= 10 != flag\n",
    "augmented": "total = 0\nfor i in range(5):\n    total += i\n",
    "strings-and-comments": (
        "# leading comment\ns = 'single'\nt = \"double\"  # trailing\n"
        "u = '''tri\nple'''\n"
    ),
    "identifiers": "alpha_beta = gamma.delta(epsilon, zeta[1])\nalpha_beta.method()\n",
    "keywords-dense": (
        "import os\n\ndef f(x):\n    with open(x) as fh:\n"
        "        for line in fh:\n            if not line and x is None:\n"
        "                continue\n    return True\n"
    ),
    "class-def": (
        "class Point:\n    def __init__(self, x, y):\n"
        "        self.x = x\n        self.y = y\n"
    ),
    "decorator-and-walrus": "@wraps(fn)\ndef g(xs):\n    if (n := len(xs)) > 3:\n        return n\n",
    "blank-lines": "a = 1\n\n\nb = 2\n",
    "unicode": "名前 = 'テスト'  # コメント\n",
    # soft keywords are identifiers in BOTH lanes (BW-PY-0001): tokenize emits
    # NAME for match/case/_, and the tree-sitter lane classifies the anonymous
    # leaves as IDENTIFIER via the soft-keyword table.
    "match-statement": (
        "match command:\n    case 1:\n        run()\n    case _:\n        stop()\n"
    ),
}


def _assert_features_equal(name: str, src: str) -> None:
    reference = bw_readability_features(src)
    rep = measure(src, language="python", metrics=(), readability=("bw2010",))
    vec = rep.readability[0]
    ours = dict(zip(vec.names, vec.values, strict=True))
    assert set(ours) == set(reference)
    for feat in reference:
        assert math.isclose(ours[feat], reference[feat], rel_tol=1e-12, abs_tol=1e-12), (
            f"{name}: feature {feat}: tree-sitter={ours[feat]} != stdlib={reference[feat]}"
        )


@pytest.mark.parametrize("case", PY_CASES, ids=[c["id"] for c in PY_CASES])
def test_corpus_fidelity(case: dict) -> None:
    _assert_features_equal(case["id"], case["source"])


@pytest.mark.parametrize("name", sorted(EXTRA_SNIPPETS), ids=sorted(EXTRA_SNIPPETS))
def test_snippet_fidelity(name: str) -> None:
    _assert_features_equal(name, EXTRA_SNIPPETS[name])
