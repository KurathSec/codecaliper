"""PMD vs codecaliper: per-method cyclomatic AND cognitive complexity, Java.

This is the lane's only Java witness besides lizard, and the only external
witness Java cognitive complexity has at all (ARCHITECTURE.md §8.2). It is worth
its JVM because it is independent all the way down: PMD parses Java with its own
JavaCC grammar, not tree-sitter, and computes both metrics with its own
visitors, so agreement here is not two wrappers around one parser agreeing with
themselves.

One caveat, stated because it would otherwise be an overclaim: on the ONE axis
where our two cognitive modes disagree, the recursion increment, PMD takes the
whitepaper's +1 (`snippet:diff-java-recursion`). Comparisons run in sonar-compat
mode, so that axis shows up as a classified divergence, and what PMD witnesses
there is our *whitepaper* mode. Java's sonar-compat recursion behaviour still
has no external witness.

Every method's value comes out of one PMD run; see `_harness.pmd_values` for how
a linter is made to report metrics, and for the guard on the one inference it
takes.
"""

from __future__ import annotations

import pytest

from differential import _harness as h

_SKIP_REASON = h.probe_pmd()
pytestmark = pytest.mark.skipif(
    _SKIP_REASON is not None, reason=_SKIP_REASON or "pmd is present"
)

LABELS = sorted(h.inputs("java"))


@pytest.mark.parametrize("label", LABELS)
def test_every_divergence_is_classified(label: str) -> None:
    h.assert_classified(h.comparisons("pmd", label))


def test_every_table_entry_is_still_observed() -> None:
    comps = [c for label in LABELS for c in h.comparisons("pmd", label)]
    h.assert_no_stale("pmd", comps)
