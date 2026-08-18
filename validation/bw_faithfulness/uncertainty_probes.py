#!/usr/bin/env python3
"""Uncertainty probes for the reproduction: per-feature CIs, the paired
tab-width contrast, and score stability across the arbitration matrix.

Three questions a reviewer of the faithfulness lane asks, answered from the
TRACKED pins only (no network, hard error on a missing input):

1. Per-feature bootstrap 95% CIs of the Spearman correlations in the adopted
   configuration (snippet-level resampling, 2000 replicates, percentile,
   seed 0) -- so the sign-agreement table can show which correlations are
   individually distinguishable from zero.
2. A paired bootstrap 95% CI for the tab-width contrast on avg_indentation:
   delta = rho(tab=8) - rho(tab=1), both correlations computed on the same
   resample (full-lexical-stream mode), 2000 replicates, percentile, seed 0.
3. Label stability across the 32 arbitration cells: for every cell, the
   out-of-fold predicted labels under the exact train.py protocol, counted
   against the adopted cell (fallback_on, tab=8, V0_current). Cell feature
   matrices are built the way arbitrate.py builds them (tab: indentation
   columns recomputed from the raw snippets at full precision; ops: V0 keeps
   the instrument's own column, V1-V3 use the direct-parse recomputation).
"""

from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import arbitrate  # noqa: E402  (sibling module; reuses its cell machinery)
import pinned  # noqa: E402
import stats  # noqa: E402

FEATURES_ON_TAB1 = HERE / "derived" / "arbitration_inputs" / "features_fallback_on_tab1.csv"
FEATURES_OFF = HERE / "derived" / "features_fallback_off.csv"
PAPER_CUTOFF = 3.14
ITERS = 2000
SEED = 0
TAB_WIDTHS = (0, 1, 2, 4, 8)
MODES = ("fallback_off", "fallback_on")


def boot_ci(values_fn: Any, n: int, iters: int = ITERS, seed: int = SEED) -> list[float]:
    rng = random.Random(seed)
    out = sorted(values_fn([rng.randrange(n) for _ in range(n)]) for _ in range(iters))
    return [out[int(0.025 * iters)], out[int(0.975 * iters)]]


def main() -> int:
    pinned.require_inputs()
    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import StratifiedKFold, cross_val_predict
    except ImportError as exc:
        print(f"ERROR: scikit-learn/numpy not importable ({exc}).", file=sys.stderr)
        return 1
    import csv

    from codecaliper.readability.bw2010 import BW_FEATURE_NAMES

    with pinned.SCORES.open(newline="", encoding="utf-8") as f:
        score_rows = {int(r["snippet_id"]): r for r in csv.DictReader(f)}
    ids = sorted(score_rows)
    n = len(ids)
    means = [float(score_rows[i]["mean_score"]) for i in ids]

    feats = arbitrate._load_matrix(HERE / "derived" / "features.csv", BW_FEATURE_NAMES)
    col = {name: i for i, name in enumerate(BW_FEATURE_NAMES)}

    # --- 1. per-feature bootstrap CIs (adopted configuration)
    print("per-feature Spearman rho with bootstrap 95% CI "
          f"(snippet resampling, {ITERS} replicates, seed {SEED}):")
    for name in BW_FEATURE_NAMES:
        xs = [feats[i][col[name]] for i in ids]
        rho = stats.spearman(xs, means)

        def d(idx: list[int], xs: list[float] = xs) -> float:
            return stats.spearman([xs[j] for j in idx], [means[j] for j in idx])

        lo, hi = boot_ci(d, n)
        star = " *" if lo > 0 or hi < 0 else ""
        print(f"  {name:28s} {rho:+.3f}  [{lo:+.3f}, {hi:+.3f}]{star}")

    # --- 2. paired tab contrast on avg_indentation (fallback_on mode)
    snippets = {i: (HERE / "derived" / "arbitration_inputs" / "snippets" / f"{i}.jsnp"
                    ).read_bytes() for i in ids}
    indent = {
        i: {tw: arbitrate._indentation(arbitrate._snippet_lines(snippets[i]), tw)
            for tw in TAB_WIDTHS}
        for i in ids
    }
    with (HERE / "fig9_signs.toml").open("rb") as f:
        import tomllib
        signs = tomllib.load(f)["signs"]

    def agreement_at(tw: int) -> int:
        n_ok = 0
        for name in BW_FEATURE_NAMES:
            expected = signs[name]["sign"]
            if expected == "unclear":
                continue
            if name == "avg_indentation":
                rho = stats.spearman([indent[i][tw][0] for i in ids], means)
            elif name == "max_indentation":
                rho = stats.spearman([indent[i][tw][1] for i in ids], means)
            else:
                rho = stats.spearman([feats[i][col[name]] for i in ids], means)
            if (rho > 0) if expected == "+" else (rho < 0):
                n_ok += 1
        return n_ok

    for tw in TAB_WIDTHS:
        a = [indent[i][tw][0] for i in ids]
        rho = stats.spearman(a, means)

        def d(idx: list[int], a: list[float] = a) -> float:
            return stats.spearman([a[j] for j in idx], [means[j] for j in idx])

        lo_t, hi_t = boot_ci(d, n)
        print(f"avg_indentation rho at tab={tw}: {rho:+.4f} "
              f"95% CI [{lo_t:+.4f}, {hi_t:+.4f}]  "
              f"Figure 9 agreement {agreement_at(tw)}/24")
    a8 = [indent[i][8][0] for i in ids]
    a1 = [indent[i][1][0] for i in ids]

    def delta(idx: list[int]) -> float:
        return (stats.spearman([a8[j] for j in idx], [means[j] for j in idx])
                - stats.spearman([a1[j] for j in idx], [means[j] for j in idx]))

    d_full = stats.spearman(a8, means) - stats.spearman(a1, means)
    lo, hi = boot_ci(delta, n)
    print(f"paired tab contrast, avg_indentation, fallback_on: "
          f"delta rho (tab8 - tab1) = {d_full:+.4f}, 95% CI [{lo:+.4f}, {hi:+.4f}]")

    # --- 3. label stability across the 32 cells vs the adopted cell
    matrices = {
        "fallback_off": arbitrate._load_matrix(FEATURES_OFF, BW_FEATURE_NAMES),
        "fallback_on": arbitrate._load_matrix(FEATURES_ON_TAB1, BW_FEATURE_NAMES),
    }
    from codecaliper.languages import get_adapter
    v0 = frozenset(get_adapter("java").arithmetic_ops)
    variants: dict[str, frozenset[str]] = {
        "V0_current": v0,
        "V1_minimal": frozenset({"+", "-", "*", "/"}),
        "V2_incdec": v0 | {"++", "--"},
        "V3_compound": v0 | {"+=", "-=", "*=", "/=", "%="},
    }
    arith = {i: arbitrate._arith_counts(snippets[i], variants) for i in ids}

    y = np.array([1 if m >= PAPER_CUTOFF else 0 for m in means])
    skf = StratifiedKFold(n_splits=10, shuffle=True, random_state=0)

    def cell_labels(mode: str, tab: int, variant: str) -> Any:
        rows = []
        for i in ids:
            vec = list(matrices[mode][i])
            avg, mx = indent[i][tab]
            vec[col["avg_indentation"]] = avg
            vec[col["max_indentation"]] = mx
            if variant != "V0_current":
                vec[col["avg_arithmetic_ops"]] = arith[i][mode][variant]
            rows.append(vec)
        x = np.array(rows)
        return cross_val_predict(LogisticRegression(max_iter=1000), x, y, cv=skf,
                                 method="predict")

    adopted = cell_labels("fallback_on", 8, "V0_current")
    flips: dict[str, int] = {}
    for mode in MODES:
        for tab in TAB_WIDTHS:
            for variant in variants:
                lab = cell_labels(mode, tab, variant)
                flips[f"{mode}/tab={tab}/{variant}"] = int((lab != adopted).sum())
    nonzero = {k: v for k, v in flips.items() if v}
    print(f"label flips vs adopted cell over 32 cells: max = {max(flips.values())}, "
          f"cells with any flip = {len(nonzero)}/32")
    for k, v in sorted(nonzero.items(), key=lambda kv: -kv[1]):
        print(f"  {k:38s} {v}")

    # --- 4. is the AUC gap between the adopted cell and the maximum-AUC cell
    # resolvable? Paired bootstrap over snippets on fixed out-of-fold scores.
    from sklearn.metrics import roc_auc_score

    def cell_scores(mode: str, tab: int, variant: str) -> Any:
        rows = []
        for i in ids:
            vec = list(matrices[mode][i])
            avg, mx = indent[i][tab]
            vec[col["avg_indentation"]] = avg
            vec[col["max_indentation"]] = mx
            if variant != "V0_current":
                vec[col["avg_arithmetic_ops"]] = arith[i][mode][variant]
            rows.append(vec)
        return cross_val_predict(LogisticRegression(max_iter=1000), np.array(rows),
                                 y, cv=skf, method="decision_function")

    adopted_s = cell_scores("fallback_on", 8, "V0_current")
    maxauc_s = cell_scores("fallback_on", 1, "V0_current")
    auc_a = float(roc_auc_score(y, adopted_s))
    auc_m = float(roc_auc_score(y, maxauc_s))

    def paired_auc_delta(idx: list[int]) -> float:
        yy = y[idx]
        if yy.min() == yy.max():
            return 0.0
        return float(roc_auc_score(yy, maxauc_s[idx])
                     - roc_auc_score(yy, adopted_s[idx]))

    lo, hi = boot_ci(paired_auc_delta, n)

    def auc_ci(scores: Any) -> list[float]:
        def f(idx: list[int]) -> float:
            yy = y[idx]
            return (float(roc_auc_score(yy, scores[idx]))
                    if yy.min() != yy.max() else 0.5)
        return boot_ci(f, n)

    ca, cm = auc_ci(adopted_s), auc_ci(maxauc_s)
    print(f"AUC of the adopted cell (tab=8, full stream): {auc_a:.4f} "
          f"95% CI [{ca[0]:.4f}, {ca[1]:.4f}]")
    print(f"AUC of the maximum-AUC cell (tab=1, full stream): {auc_m:.4f} "
          f"95% CI [{cm[0]:.4f}, {cm[1]:.4f}]")
    print(f"paired difference (max minus adopted): {auc_m - auc_a:+.4f}, "
          f"95% CI [{lo:+.4f}, {hi:+.4f}]")

    # --- 5. counterfactual: extend the tab convention to the space count
    def avg_spaces(i: int, tab_cols: int) -> float:
        lines = arbitrate._snippet_lines(snippets[i])
        if not lines:
            return 0.0
        return sum(ln.count(" ") + tab_cols * ln.count("\t")
                   for ln in lines) / len(lines)

    for tw in (0, 1, 8):
        a = [avg_spaces(i, tw) for i in ids]
        rho = stats.spearman(a, means)
        label = {0: "as shipped, a tab counts nothing",
                 1: "a tab counts as one space",
                 8: "a tab counts as eight spaces"}[tw]
        print(f"avg_spaces counterfactual, {label:34s} rho {rho:+.4f} "
              f"({'agrees' if rho < 0 else 'disagrees'} with Figure 9's negative)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
