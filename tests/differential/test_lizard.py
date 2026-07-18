"""lizard vs codecaliper: per-function cyclomatic complexity, Python, Java AND Go.

lizard's CCN is token-based, which is exactly why it is a useful witness: it
disagrees with tree-shape counting on ruled axes (comprehension `for` tokens,
bare-wildcard `case _` arms, a case guard's `if` token counted on top of its
case) and agrees everywhere else, including on every Go input.
"""

from __future__ import annotations

import pytest

from differential import _harness as h

_SKIP_REASON = h.probe_oracle("lizard", "lizard")
pytestmark = pytest.mark.skipif(
    _SKIP_REASON is not None, reason=_SKIP_REASON or "lizard is installed"
)

LABELS = sorted(h.inputs("python")) + sorted(h.inputs("java")) + sorted(h.inputs("go"))


@pytest.mark.parametrize("label", LABELS)
def test_every_divergence_is_classified(label: str) -> None:
    h.assert_classified(h.comparisons("lizard", label))


def test_every_table_entry_is_still_observed() -> None:
    comps = [c for label in LABELS for c in h.comparisons("lizard", label)]
    h.assert_no_stale("lizard", comps)
