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
import os
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
MAXSTAT_ITERS = 2000     # family-wise correction over the 25 feature tests
# Draws are independent, so they are evaluated in parallel. Determinism is
# preserved by construction: the seeded generator emits a fixed SEQUENCE of
# index sets, both the serial and the parallel form walk that sequence in
# order, and both keep the valid ones in order. Only the evaluation is
# concurrent. The recorded output is byte-identical either way.
SUBSAMPLE_JOBS = max(1, (os.cpu_count() or 2) - 2)
SUBSAMPLE_DRAWS = 2000   # each draw refits the ten-fold model, so this is the
                         # point of diminishing returns: it cuts the Monte Carlo
                         # error on a reported percentile from about 3.5
                         # accuracy points at 200 draws to about 1.1, against a
                         # reported 5th-to-95th span of 31 points


def main() -> int:
    pinned.require_inputs()
    try:
        import numpy as np
        from joblib import Parallel, delayed
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

    # --- power control: how much of the small-corpus movement is just size?
    # Draw random subsamples of the same size from the full 100. This is an
    # MCAR reference: it bounds the size effect, it cannot detect selection
    # along the structural mechanism the check above probes.
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

    # --- selection check: the snippets that parse are not a random subset,
    # they are selected on a structural property, so a random-subsample
    # reference cannot detect selection along that mechanism. Compare the two
    # groups directly instead, on the label and on every feature.
    parse_ids = set(as_written)
    grp_a = [i for i in ids if i in parse_ids]
    grp_b = [i for i in ids if i not in parse_ids]
    hi = {g: sum(1 for i in g if means[i] >= PAPER_CUTOFF) / len(g)
          for g in (tuple(grp_a), tuple(grp_b))}
    print(f"  selection check, the {len(grp_a)} that parse as written against "
          f"the other {len(grp_b)}:")
    print(f"      share labelled high: {hi[tuple(grp_a)]:.3f} against "
          f"{hi[tuple(grp_b)]:.3f}; mean rating "
          f"{stats.mean([means[i] for i in grp_a]):.3f} against "
          f"{stats.mean([means[i] for i in grp_b]):.3f}")

    def perm_p(vals_a: list[float], vals_b: list[float], seed: int = 0,
               iters: int = 2000) -> float:
        obs = abs(stats.mean(vals_a) - stats.mean(vals_b))
        pool = vals_a + vals_b
        k = len(vals_a)
        rg = random.Random(seed)
        hits = 0
        for _ in range(iters):
            rg.shuffle(pool)
            if abs(stats.mean(pool[:k]) - stats.mean(pool[k:])) >= obs:
                hits += 1
        return (hits + 1) / (iters + 1)

    differing = []
    for name in BW_FEATURE_NAMES:
        a = [float(rows[i][name]) for i in grp_a]
        b = [float(rows[i][name]) for i in grp_b]
        if perm_p(a, b) < 0.05:
            differing.append(name)
    print(f"      features whose means differ between the groups at a "
          f"two-sided permutation p < 0.05 (2000 relabelings): "
          f"{len(differing)} of {len(BW_FEATURE_NAMES)}"
          + (f" ({', '.join(differing)})" if differing else ""))

    # Twenty-five uncorrected tests cannot support "measurably different". The
    # max-statistic correction controls the family-wise error rate exactly:
    # one relabeling is applied to every feature at once, and each feature's
    # observed statistic is read against the distribution of the largest
    # statistic anywhere in the family under that same relabeling.
    order = grp_a + grp_b
    k = len(grp_a)
    cols = {n: [float(rows[i][n]) for i in order] for n in BW_FEATURE_NAMES}
    scale = {n: (stats.stdev(cols[n]) or 1.0) for n in BW_FEATURE_NAMES}

    def std_diff(name: str, idx: list[int]) -> float:
        col = cols[name]
        return abs(stats.mean([col[j] for j in idx[:k]])
                   - stats.mean([col[j] for j in idx[k:]])) / scale[name]

    base = list(range(len(order)))
    observed = {n: std_diff(n, base) for n in BW_FEATURE_NAMES}
    rg = random.Random(0)
    max_dist = []
    for _ in range(MAXSTAT_ITERS):
        rg.shuffle(base)
        max_dist.append(max(std_diff(n, base) for n in BW_FEATURE_NAMES))
    survivors = [
        n for n in BW_FEATURE_NAMES
        if (sum(1 for m in max_dist if m >= observed[n]) + 1)
        / (MAXSTAT_ITERS + 1) < 0.05
    ]
    print(f"      the same tests under a max-statistic correction over all "
          f"{len(BW_FEATURE_NAMES)} features ({MAXSTAT_ITERS} relabelings, "
          f"family-wise alpha 0.05): {len(survivors)} survive"
          + (f" ({', '.join(survivors)})" if survivors else ""))
    print(f"      label difference permutation p: "
          f"{perm_p([means[i] for i in grp_a], [means[i] for i in grp_b]):.3f}")

    def evaluate(idx: list[int]) -> tuple[float | None, int]:
        a = acc_of(idx)
        return (a, signs_of(idx) if a is not None else 0)

    rng = random.Random(0)
    for size, observed, label in ((len(as_written), 0.717, "as written"),
                                  (len(scaffold), 0.733, "scaffold allowed")):
        draws = []
        sign_draws = []
        while len(draws) < SUBSAMPLE_DRAWS:
            batch = [rng.sample(range(len(ids)), size)
                     for _ in range(SUBSAMPLE_DRAWS - len(draws))]
            for a, sg in Parallel(n_jobs=SUBSAMPLE_JOBS)(
                    delayed(evaluate)(idx) for idx in batch):
                if a is not None:
                    draws.append(a)
                    sign_draws.append(sg)
        draws.sort()
        below = sum(1 for a in draws if a <= observed)
        lost = sum(1 for v in sign_draws if v < 21)
        sign_draws.sort()
        p05 = draws[int(0.05 * len(draws))]
        p95 = draws[int(0.95 * len(draws)) - 1]
        print(f"  power control, random {size}-snippet subsamples of the full "
              f"100 ({SUBSAMPLE_DRAWS} draws): accuracy median "
              f"{draws[len(draws) // 2]:.3f}, "
              f"5th-95th [{p05:.3f}, {p95:.3f}]; the observed "
              f"{label} value {observed:.3f} sits at the {100 * below / len(draws):.0f}th "
              "percentile of that distribution")
        print(f"      sign agreement over the same draws: median "
              f"{sign_draws[len(sign_draws) // 2]}/24, range "
              f"{sign_draws[0]}-{sign_draws[-1]}; below 21 in "
              f"{100 * lost / len(sign_draws):.0f}% of draws")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
