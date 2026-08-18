#!/usr/bin/env python3
"""Does the arbitration's winner survive feature standardization?

The reproduction fits L2-penalised logistic regression at a fixed C on RAW,
unscaled feature vectors. The tab-width factor under study rescales the
indentation features, so it also rescales their effective penalty: the AUC
tie-break therefore confounds information content with regularization scale.
The primary criterion is Spearman-based and hence scale-invariant, so the
confound is confined to the tie-break, but that is an argument, not a check.

This probe is the check. It recomputes every cell of the 32-cell matrix with
the features standardized inside each fold (mean zero, unit variance, fitted
on the training split only, so no leakage), and reports whether the adopted
cell still wins under the same lexicographic rule, plus the AUC ordering.

TRACKED pins only, deterministic, no network. Recorded output:
standardization_results.txt (regenerate, never edit).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any

import tomllib

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import arbitrate  # noqa: E402
import pinned  # noqa: E402
import stats  # noqa: E402

FEATURES_ON_TAB1 = HERE / "derived" / "arbitration_inputs" / "features_fallback_on_tab1.csv"
FEATURES_OFF = HERE / "derived" / "features_fallback_off.csv"
SIGNS = HERE / "fig9_signs.toml"
PAPER_CUTOFF = 3.14
TAB_WIDTHS = (1, 2, 4, 8)
MODES = ("fallback_off", "fallback_on")


def main() -> int:
    pinned.require_inputs()
    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import roc_auc_score
        from sklearn.model_selection import StratifiedKFold, cross_val_predict
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        print(f"ERROR: scikit-learn/numpy not importable ({exc}).", file=sys.stderr)
        return 1
    from codecaliper.languages import get_adapter
    from codecaliper.readability.bw2010 import BW_FEATURE_NAMES

    with pinned.SCORES.open(newline="", encoding="utf-8") as f:
        rows = {int(r["snippet_id"]): r for r in csv.DictReader(f)}
    ids = sorted(rows)
    means = [float(rows[i]["mean_score"]) for i in ids]
    with SIGNS.open("rb") as f:
        signs = tomllib.load(f)["signs"]

    matrices = {
        "fallback_off": arbitrate._load_matrix(FEATURES_OFF, BW_FEATURE_NAMES),
        "fallback_on": arbitrate._load_matrix(FEATURES_ON_TAB1, BW_FEATURE_NAMES),
    }
    col = {name: i for i, name in enumerate(BW_FEATURE_NAMES)}
    snippets = {i: (HERE / "derived" / "arbitration_inputs" / "snippets"
                    / f"{i}.jsnp").read_bytes() for i in ids}
    indent = {i: {tw: arbitrate._indentation(arbitrate._snippet_lines(snippets[i]), tw)
                  for tw in TAB_WIDTHS} for i in ids}
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

    def matrix(mode: str, tab: int, variant: str) -> Any:
        out = []
        for i in ids:
            vec = list(matrices[mode][i])
            avg, mx = indent[i][tab]
            vec[col["avg_indentation"]] = avg
            vec[col["max_indentation"]] = mx
            if variant != "V0_current":
                vec[col["avg_arithmetic_ops"]] = arith[i][mode][variant]
            out.append(vec)
        return np.array(out)

    def cell(mode: str, tab: int, variant: str, scale: bool) -> tuple[int, float]:
        x = matrix(mode, tab, variant)
        n_agree = 0
        for c, name in enumerate(BW_FEATURE_NAMES):
            expected = signs[name]["sign"]
            if expected == "unclear":
                continue
            rho = stats.spearman(list(x[:, c]), means)
            if (rho > 0) if expected == "+" else (rho < 0):
                n_agree += 1
        est: Any = (make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
                    if scale else LogisticRegression(max_iter=1000))
        dec = cross_val_predict(est, x, y, cv=skf, method="decision_function")
        return n_agree, float(roc_auc_score(y, dec))

    for scale in (False, True):
        label = "standardized in-fold" if scale else "raw (as adopted)"
        res = {(m, t, v): cell(m, t, v, scale)
               for m in MODES for t in TAB_WIDTHS for v in variants}
        base = {m: res[(m, 1, "V0_current")] for m in MODES}

        def clears(t: int, v: str, res: Any = res, base: Any = base) -> bool:
            gain = False
            for m in MODES:
                a, auc = res[(m, t, v)]
                if a < base[m][0] or auc < base[m][1] - 0.01:
                    return False
                gain = gain or a > base[m][0]
            return gain

        cands = [(t, v) for t in TAB_WIDTHS for v in variants if clears(t, v)]

        def rank(c: tuple[int, str], res: Any = res) -> tuple[float, ...]:
            t, v = c
            return (-sum(res[(m, t, v)][0] for m in MODES),
                    -sum(res[(m, t, v)][1] for m in MODES),
                    (1 if t != 1 else 0) + (1 if v != "V0_current" else 0),
                    t, list(variants).index(v))

        win = min(cands, key=rank) if cands else (1, "V0_current")
        aucs = {t: res[("fallback_on", t, "V0_current")][1] for t in TAB_WIDTHS}
        print(f"{label}: winner tab={win[0]} ops={win[1]}; clearing candidates "
              f"{len(cands)}/16; full-stream AUC by tab "
              + ", ".join(f"{t}:{aucs[t]:.4f}" for t in TAB_WIDTHS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
