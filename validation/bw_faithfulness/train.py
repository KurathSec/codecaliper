#!/usr/bin/env python3
"""Retrain under the paper's protocol: binarize mean annotator score at the
overall mean, 10-fold cross-validated logistic regression, fixed seed
(requires the [retrain] extra). Any deviation from the paper's exact classifier
battery/binarization is documented in the report — a methodology reviewer will
check (ARCHITECTURE.md §8.3).

Blocked on: the per-snippet annotator scores' layout inside DatasetBW.zip
(confirm on first fetch, W6). This script encodes the protocol so the gate and
report format are fixed before the data arrives.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"       # dataset-derived raw material — never committed
DERIVED = HERE / "derived"   # extractor outputs / results — the committable dir


def main() -> int:
    features = DERIVED / "features.csv"
    scores = CACHE / "scores.csv"  # annotator scores ARE dataset content -> cache/
    if not features.exists():
        print("SKIP: derived/features.csv missing — run extract.py first.")
        return 0
    if not scores.exists():
        print("SKIP: cache/scores.csv missing — the annotator-score extraction "
              "from DatasetBW.zip is the tracked W6 task (confirm archive "
              "layout, then extend extract.py).")
        return 0
    try:
        import numpy  # noqa: F401
        import sklearn  # noqa: F401
    except ImportError:
        print("SKIP: scikit-learn not installed — pip install -e '.[retrain]'")
        return 0
    # Protocol (fixed here, executed in W6):
    #  1. label = 1 if snippet mean score >= overall mean else 0 (paper's split)
    #  2. LogisticRegression(max_iter=1000), StratifiedKFold(10, shuffle, seed=0)
    #  3. metrics: accuracy + bootstrap CI (stats.ci95_bootstrap over fold
    #     accuracies), AUC; per-feature Spearman vs mean score + Fig. 9 signs
    print("NOT IMPLEMENTED YET: waiting on scores.csv (W6).", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
