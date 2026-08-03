#!/usr/bin/env python3
"""Adaptive brace-balancing repair: the obvious alternative the scaffold is not.

The fixed class/method scaffold (CORE-JAVA-0001) cannot close a brace the
fragment never contained, and 69 of the 73 clean-parse failures of the
Buse-Weimer snippets are brace-imbalanced. This probe measures the obvious
adaptive alternative: balance each snippet's braces (append the missing '}',
prepend the missing '{') and re-measure. It reports the clean-parse rate as
written, after brace balancing alone (granularity="file", so the instrument's
scaffold never engages), and after brace balancing with the snippet scaffold
allowed on top (granularity="snippet").

Measurement caveat the numbers carry: unlike the scaffold, whose synthetic
lines are excluded from every feature range (CORE-JAVA-0001 line_range), the
appended brace characters BECOME PART of the measured text, so this repair
changes feature values as a side effect of enabling the parse. The probe
quantifies parse rates only.

TRACKED inputs only (derived/arbitration_inputs/snippets/); no network. A
missing tracked input is a hard error, never a SKIP.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNIPPETS = HERE / "derived" / "arbitration_inputs" / "snippets"


def balance(src: str) -> tuple[str, int]:
    """Balance braces: append missing '}', prepend missing '{'. Returns the
    repaired text and the (signed) imbalance that was repaired."""
    k = src.count("{") - src.count("}")
    if k > 0:
        return src + ("\n" + "}\n" * k), k
    if k < 0:
        return ("{\n" * (-k)) + src, k
    return src, 0


def main() -> int:
    if not SNIPPETS.is_dir():
        print(f"ERROR: tracked input {SNIPPETS} is missing; nothing measured.",
              file=sys.stderr)
        return 1
    try:
        from codecaliper.api import measure
    except ImportError as exc:
        print(f"ERROR: codecaliper not importable ({exc}).", file=sys.stderr)
        return 1

    files = sorted(SNIPPETS.glob("*.jsnp"), key=lambda p: int(p.stem))
    n = len(files)
    as_written = balanced = balanced_scaffold = 0
    pos = neg = zero = 0
    for f in files:
        src = f.read_text(encoding="utf-8")
        rep, k = balance(src)
        pos += 1 if k > 0 else 0
        neg += 1 if k < 0 else 0
        zero += 1 if k == 0 else 0
        if measure(src, language="java").parse_ok:
            as_written += 1
        if measure(rep, language="java").parse_ok:
            balanced += 1
        if measure(rep, language="java", granularity="snippet").parse_ok:
            balanced_scaffold += 1

    print(f"snippets: {n}; brace imbalance: {pos} missing '}}', {neg} missing "
          f"'{{', {zero} balanced")
    print(f"clean parse as written (no scaffold):            {as_written}/{n}")
    print(f"clean parse after brace balancing (no scaffold): {balanced}/{n}")
    print(f"clean parse after brace balancing + scaffold:    {balanced_scaffold}/{n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
