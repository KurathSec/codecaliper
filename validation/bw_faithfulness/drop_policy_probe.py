#!/usr/bin/env python3
"""What a drop policy costs downstream, not just in corpus size.

The parse-anatomy finding establishes that the repair-and-drop policy sets the
measured corpus anywhere between 27 and 100 snippets. It does not, on its own,
show that anything MEASURED changes: that is the half a reviewer asks for.
This probe supplies it, by re-running the reproduction on each corpus a drop
policy would actually leave behind, under the adopted operationalization:

  full            all 100 snippets (measure-anyway, what this project adopts)
  as_written      the 27 that parse cleanly with no repair attempted
  scaffold        the 29 that parse cleanly once the CORE-JAVA-0001 scaffold
                  is allowed
  brace balanced  the snippets that parse cleanly after adaptive brace
                  balancing (brace_repair_probe.balance)

For each it reports the class split, the Figure 9 sign agreement, and the
cross-validated accuracy and AUC. Read the small-corpus rows with the obvious
caveat: at n = 27 part of any movement is a power artifact, which is itself
part of the finding, since a study that drops is left with exactly that.

The fold count is min(10, size of the smaller class), reported per row,
because a 27-snippet corpus cannot support ten stratified folds.

TRACKED pins only, deterministic, no network.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import tomllib

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pinned  # noqa: E402
import stats  # noqa: E402
from brace_repair_probe import balance  # noqa: E402

AI = HERE / "derived" / "arbitration_inputs"
FEATURES = HERE / "derived" / "features.csv"
SIGNS = HERE / "fig9_signs.toml"
PAPER_CUTOFF = 3.14


def main() -> int:
    pinned.require_inputs()
    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import roc_auc_score
        from sklearn.model_selection import StratifiedKFold, cross_val_predict
    except ImportError as exc:
        print(f"ERROR: scikit-learn/numpy not importable ({exc}).", file=sys.stderr)
        return 1
    from codecaliper.api import measure
    from codecaliper.readability.bw2010 import BW_FEATURE_NAMES

    with FEATURES.open(newline="", encoding="utf-8") as f:
        rows = {int(r["snippet"]): r for r in csv.DictReader(f)}
    with pinned.SCORES.open(newline="", encoding="utf-8") as f:
        means = {int(r["snippet_id"]): float(r["mean_score"])
                 for r in csv.DictReader(f)}
    with SIGNS.open("rb") as f:
        signs = tomllib.load(f)["signs"]
    ids = sorted(rows)

    as_written = [i for i in ids
                  if rows[i]["parse_ok"] == "True" and rows[i]["scaffolded"] == "False"]
    scaffold = [i for i in ids if rows[i]["parse_ok"] == "True"]
    balanced = []
    for i in ids:
        src = (AI / "snippets" / f"{i}.jsnp").read_text(encoding="utf-8")
        if measure(balance(src)[0], language="java").parse_ok:
            balanced.append(i)

    def report(label: str, subset: list[int]) -> None:
        y = np.array([1 if means[i] >= PAPER_CUTOFF else 0 for i in subset])
        n_hi, n_lo = int(y.sum()), int(len(y) - y.sum())
        n_agree = n_eval = 0
        disagree: list[str] = []
        for name in BW_FEATURE_NAMES:
            expected = signs[name]["sign"]
            if expected == "unclear":
                continue
            n_eval += 1
            rho = stats.spearman([float(rows[i][name]) for i in subset],
                                 [means[i] for i in subset])
            if (rho > 0) if expected == "+" else (rho < 0):
                n_agree += 1
            else:
                disagree.append(name)
        folds = min(10, n_hi, n_lo)
        x = np.array([[float(rows[i][name]) for name in BW_FEATURE_NAMES]
                      for i in subset])
        skf = StratifiedKFold(n_splits=folds, shuffle=True, random_state=0)
        accs = []
        for tr, te in skf.split(x, y):
            clf = LogisticRegression(max_iter=1000)
            clf.fit(x[tr], y[tr])
            accs.append(float(clf.score(x[te], y[te])))
        dec = cross_val_predict(LogisticRegression(max_iter=1000), x, y, cv=skf,
                                method="decision_function")
        print(f"  {label:22s} n={len(subset):3d} ({n_hi:2d} high /{n_lo:3d} low)  "
              f"signs {n_agree}/{n_eval}  {folds:2d}-fold acc "
              f"{stats.mean(accs):.3f}  AUC {float(roc_auc_score(y, dec)):.3f}")
        if disagree:
            print(f"      diverging: {', '.join(sorted(disagree))}")

    print("reproduction under each corpus a drop policy would leave behind "
          "(adopted operationalization, tab=8, full lexical stream):")
    for label, subset in (("full (measure anyway)", ids),
                          ("as written", as_written),
                          ("scaffold allowed", scaffold),
                          ("brace balanced", balanced)):
        report(label, subset)

    # --- power control: is the small-corpus accuracy drop about WHICH
    # snippets survive, or only about how few there are? Draw random
    # subsamples of the same size from the full 100 and compare.
    import random

    y_all = np.array([1 if means[i] >= PAPER_CUTOFF else 0 for i in ids])
    x_all = np.array([[float(rows[i][name]) for name in BW_FEATURE_NAMES]
                      for i in ids])

    def signs_of(idx: list[int]) -> int:
        sub = [ids[j] for j in idx]
        n_ok = 0
        for name in BW_FEATURE_NAMES:
            expected = signs[name]["sign"]
            if expected == "unclear":
                continue
            rho = stats.spearman([float(rows[i][name]) for i in sub],
                                 [means[i] for i in sub])
            if (rho > 0) if expected == "+" else (rho < 0):
                n_ok += 1
        return n_ok

    def acc_of(idx: list[int]) -> float | None:
        y = y_all[idx]
        n_hi, n_lo = int(y.sum()), int(len(y) - y.sum())
        folds = min(10, n_hi, n_lo)
        if folds < 2:
            return None
        x = x_all[idx]
        skf = StratifiedKFold(n_splits=folds, shuffle=True, random_state=0)
        accs = []
        for tr, te in skf.split(x, y):
            clf = LogisticRegression(max_iter=1000)
            clf.fit(x[tr], y[tr])
            accs.append(float(clf.score(x[te], y[te])))
        return stats.mean(accs)

    rng = random.Random(0)
    for size, observed, label in ((len(as_written), 0.717, "as written"),
                                  (len(scaffold), 0.733, "scaffold allowed")):
        draws = []
        sign_draws = []
        while len(draws) < 200:
            idx = rng.sample(range(len(ids)), size)
            a = acc_of(idx)
            if a is not None:
                draws.append(a)
                sign_draws.append(signs_of(idx))
        draws.sort()
        below = sum(1 for a in draws if a <= observed)
        lost = sum(1 for v in sign_draws if v < 21)
        sign_draws.sort()
        print(f"  power control, random {size}-snippet subsamples of the full "
              f"100 (200 draws): accuracy median {draws[len(draws) // 2]:.3f}, "
              f"5th-95th [{draws[10]:.3f}, {draws[189]:.3f}]; the observed "
              f"{label} value {observed:.3f} sits at the {100 * below / len(draws):.0f}th "
              "percentile of that distribution")
        print(f"      sign agreement over the same draws: median "
              f"{sign_draws[len(sign_draws) // 2]}/24, range "
              f"{sign_draws[0]}-{sign_draws[-1]}; below 21 in "
              f"{100 * lost / len(sign_draws):.0f}% of draws")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
