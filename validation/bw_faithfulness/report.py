#!/usr/bin/env python3
"""Assemble derived/bw_faithfulness_report.{json,md}: accuracy with bootstrap
CI vs the paper's ~0.80, AUC, and the per-feature Spearman sign-agreement table
against BW Fig. 9 directionality (the sharp instrument — it localizes a
tokenization error to a specific BW-*/TOK-* ruling). The report contains no
dataset content, so it lives in the tracked derived/ directory and is committed
as part of the scholarly artifact.

Honest SKIP until train.py has produced its outputs (W6).
"""

from __future__ import annotations

from pathlib import Path

DERIVED = Path(__file__).resolve().parent / "derived"


def main() -> int:
    results = DERIVED / "train_results.json"
    if not results.exists():
        print("SKIP: derived/train_results.json missing — run train.py first "
              "(blocked on the W6 dataset-layout task; see README.md).")
        return 0
    # W6: render accuracy + ci95_bootstrap (stats.py) + per-feature sign table
    # into derived/bw_faithfulness_report.json / .md, stamped with spec/grammar
    # versions.
    print("NOT IMPLEMENTED YET: report rendering lands with train.py (W6).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
