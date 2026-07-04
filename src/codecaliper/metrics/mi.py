"""Maintainability index (MI-ALL-0001) — derived, and it says so in the types.

MI contains the CC term; it is NOT independent of cyclomatic complexity
(ARCHITECTURE.md §13). Every value carries derived_from and mi-contains-cc.
"""

from __future__ import annotations

import math

from codecaliper.model import Diagnostic
from codecaliper.spec import require

R_MI = require("MI-ALL-0001")

DERIVED_FROM = ("halstead.volume", "cyclomatic", "sloc")

CONTAINS_CC_DIAGNOSTIC = Diagnostic(
    severity="info",
    code="mi-contains-cc",
    message="MI is derived from Halstead volume, cyclomatic complexity and SLOC; "
    "do not treat MI and CC as independent signals (MI-ALL-0001).",
    ruling=R_MI,
)


def maintainability_index(volume: float, cc: int, sloc: int) -> float:
    v = max(volume, 1e-9)
    s = max(sloc, 1)
    mi = (171.0 - 5.2 * math.log(v) - 0.23 * cc - 16.2 * math.log(s)) * 100.0 / 171.0
    return max(0.0, min(100.0, mi))
