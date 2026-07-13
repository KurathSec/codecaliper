"""radon vs codecaliper: per-function Python cyclomatic complexity.

radon is per-function by construction (`radon.complexity.cc_visit`), so the
comparison is per named function; file-level totals are not a radon concept.
"""

from __future__ import annotations

import pytest

from differential import _harness as h

_SKIP_REASON = h.probe_oracle("radon.complexity", "radon")
pytestmark = pytest.mark.skipif(
    _SKIP_REASON is not None, reason=_SKIP_REASON or "radon is installed"
)

LABELS = sorted(h.inputs("python"))


@pytest.mark.parametrize("label", LABELS)
def test_every_divergence_is_classified(label: str) -> None:
    h.assert_classified(h.comparisons("radon", label))


def test_every_table_entry_is_still_observed() -> None:
    comps = [c for label in LABELS for c in h.comparisons("radon", label)]
    h.assert_no_stale("radon", comps)
