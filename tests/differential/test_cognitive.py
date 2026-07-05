"""cognitive_complexity (pip) vs codecaliper: per-function Python cognitive
complexity in OUR sonar-compat mode.

cognitive_complexity is the Sonar-lineage witness (ARCHITECTURE.md §8.2); the
comparison deliberately runs codecaliper with ``cognitive_mode="sonar-compat"``
so the classified residue is the true us-vs-Sonar-lineage diff.
"""

from __future__ import annotations

import pytest

from differential import _harness as h

_SKIP_REASON = h.probe_oracle("cognitive_complexity.api", "cognitive_complexity")
pytestmark = pytest.mark.skipif(
    _SKIP_REASON is not None, reason=_SKIP_REASON or "cognitive_complexity is installed"
)

LABELS = sorted(h.inputs("python"))


@pytest.mark.parametrize("label", LABELS)
def test_every_divergence_is_classified(label: str) -> None:
    h.assert_classified(h.comparisons("cognitive_complexity", label))


def test_every_table_entry_is_still_observed() -> None:
    comps = [c for label in LABELS for c in h.comparisons("cognitive_complexity", label)]
    h.assert_no_stale("cognitive_complexity", comps)
