#!/usr/bin/env python3
"""Bound the 121-vs-120 annotator-row discrepancy: leave-one-row-out labels.

The tracked archive's oracle.csv holds 121 annotator rows where the paper
reports 120 annotators (recorded, never silently reconciled; see train.py's
annotator_count_note). This script bounds the discrepancy's effect on the
reproduction: it recomputes the per-snippet mean ratings with each single
annotator row left out in turn and reports how many labels at the paper's 3.14
cutoff change relative to the full-archive means, whichever row is the surplus
one. Pure stdlib, TRACKED inputs only (arbitration_inputs/oracle.csv and
scores.csv), no network. A missing tracked input is a hard error, never a SKIP.

The same leave-one-row-out sweep is also applied to the per-feature
Fig. 9 sign agreements (features from derived/features.csv, the adopted
configuration; signs from fig9_signs.toml), because the labels can be stable
while a near-zero correlation's sign is not.

Recorded result (regenerate, never edit): with all 121 rows the split is
59 high / 41 low, recomputed means match scores.csv exactly, and leaving out
any single row flips zero labels and leaves the split at 59/41. The Fig. 9
sign-agreement count stays exactly 21 of 24 under every one of the 121
single-row omissions, and no feature's agreement status changes.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import tomllib

HERE = Path(__file__).resolve().parent
AI = HERE / "derived" / "arbitration_inputs"
ORACLE = AI / "oracle.csv"
SCORES = AI / "scores.csv"
FEATURES = HERE / "derived" / "features.csv"
SIGNS = HERE / "fig9_signs.toml"

PAPER_CUTOFF = 3.14  # TSE 2010 section 4.1, the Figure 5 bimodal cutoff


def main() -> int:
    for p in (ORACLE, SCORES):
        if not p.exists():
            print(f"ERROR: tracked input {p} is missing; nothing computed.",
                  file=sys.stderr)
            return 1

    with ORACLE.open(newline="", encoding="utf-8") as f:
        rows = [[int(x) for x in r[2:]] for r in csv.reader(f)]
    n_ann = len(rows)
    n_snip = len(rows[0])
    if any(len(r) != n_snip for r in rows):
        print("ERROR: oracle.csv rows have inconsistent rating counts.",
              file=sys.stderr)
        return 1

    with SCORES.open(newline="", encoding="utf-8") as f:
        recorded = {int(r["snippet_id"]): float(r["mean_score"])
                    for r in csv.DictReader(f)}

    totals = [sum(rows[a][s] for a in range(n_ann)) for s in range(n_snip)]
    means_full = [t / n_ann for t in totals]
    mismatched = [s + 1 for s in range(n_snip)
                  if abs(means_full[s] - recorded[s + 1]) > 1e-9]
    labels_full = [1 if m >= PAPER_CUTOFF else 0 for m in means_full]
    n_high = sum(labels_full)

    worst_flips = 0
    rows_with_flips = 0
    splits = {(n_high, n_snip - n_high)}
    for a in range(n_ann):
        labels = [1 if (totals[s] - rows[a][s]) / (n_ann - 1) >= PAPER_CUTOFF else 0
                  for s in range(n_snip)]
        flips = sum(1 for x, y in zip(labels, labels_full, strict=True) if x != y)
        worst_flips = max(worst_flips, flips)
        rows_with_flips += 1 if flips else 0
        splits.add((sum(labels), n_snip - sum(labels)))

    print(f"annotator rows: {n_ann} (paper reports 120); snippets: {n_snip}")
    print(f"recomputed means match scores.csv: {not mismatched}"
          + (f" (first mismatches: {mismatched[:5]})" if mismatched else ""))
    print(f"full-archive split at {PAPER_CUTOFF}: {n_high} high / "
          f"{n_snip - n_high} low")
    print(f"leave-one-row-out: max label flips over any single omitted row = "
          f"{worst_flips}; rows causing any flip = {rows_with_flips}; "
          f"splits observed = {sorted(splits)}")

    # --- Fig. 9 sign-agreement stability under the same sweep
    sys.path.insert(0, str(HERE))
    import stats  # sibling stdlib module

    with FEATURES.open(newline="", encoding="utf-8") as f:
        feat_rows = {int(r["snippet"]): r for r in csv.DictReader(f)}
    with SIGNS.open("rb") as f:
        signs = tomllib.load(f)["signs"]
    names = [c for c in feat_rows[1] if c not in ("snippet", "parse_ok", "scaffolded")]
    cols = {name: [float(feat_rows[s + 1][name]) for s in range(n_snip)]
            for name in names}

    def agreement(means: list[float]) -> tuple[int, dict[str, bool]]:
        count = 0
        agree: dict[str, bool] = {}
        for name in names:
            expected = signs[name]["sign"]
            if expected == "unclear":
                continue
            rho = stats.spearman(cols[name], means)
            ok = (rho > 0) if expected == "+" else (rho < 0)
            agree[name] = ok
            count += 1 if ok else 0
        return count, agree

    base_count, base_agree = agreement(means_full)
    counts = []
    unstable: set[str] = set()
    for a in range(n_ann):
        means = [(totals[s] - rows[a][s]) / (n_ann - 1) for s in range(n_snip)]
        cnt, agree = agreement(means)
        counts.append(cnt)
        unstable |= {nm for nm, ok in agree.items() if ok != base_agree[nm]}
    print(f"Fig. 9 sign agreement: {base_count} of 24 with all rows; over the "
          f"{n_ann} single-row omissions the count spans "
          f"[{min(counts)}, {max(counts)}]")
    print(f"features whose agreement status changes under any omission: "
          f"{sorted(unstable) if unstable else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
