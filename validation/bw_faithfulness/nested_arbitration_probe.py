#!/usr/bin/env python3
"""Selection-aware (nested) estimate of the reproduction accuracy.

The arbitration selected the adopted cell as the best of 32 on the full
dataset, and the headline 0.820 accuracy is then reported on that same data,
so the selection is not priced into the estimate. This probe nests the
selection inside the cross-validation: for each of the same ten outer folds
(StratifiedKFold, shuffle, seed 0), the pre-specified decision rule is applied
using ONLY the fold's training snippets (sign agreements on the training
subset; AUC tie-break from an inner 10-fold on the training subset), the
selected cell's classifier is trained on the training subset, and accuracy is
measured on the held-out fold. The mean over folds is the selection-aware
accuracy.

The per-fold rule mirrors arbitrate.py's pre-specified rule: a (tab, ops)
candidate beats the incumbent (tab=1, V0_current) iff it strictly increases
sign agreement in at least one extraction mode, never decreases it in either,
and never lowers AUC by more than 0.01 in either; among clearing candidates,
highest summed sign agreement, then summed AUC, then fewer changed dimensions,
smaller tab, earlier variant; ties keep the incumbent. The lexical fallback is
then adopted iff, at the chosen (tab, ops), it does not reduce sign agreement
and does not lower AUC by more than 0.01.

TRACKED pins only, deterministic, no network. Cell feature matrices are built
the way arbitrate.py builds them (tab: indentation columns recomputed from the
raw snippets; ops: V0 keeps the instrument's own column, V1-V3 use the
direct-parse recomputation).
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
AUC_DROP = 0.01


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
    from codecaliper.languages import get_adapter
    from codecaliper.readability.bw2010 import BW_FEATURE_NAMES

    with pinned.SCORES.open(newline="", encoding="utf-8") as f:
        score_rows = {int(r["snippet_id"]): r for r in csv.DictReader(f)}
    ids = sorted(score_rows)
    means = [float(score_rows[i]["mean_score"]) for i in ids]
    with SIGNS.open("rb") as f:
        signs = tomllib.load(f)["signs"]

    matrices = {
        "fallback_off": arbitrate._load_matrix(FEATURES_OFF, BW_FEATURE_NAMES),
        "fallback_on": arbitrate._load_matrix(FEATURES_ON_TAB1, BW_FEATURE_NAMES),
    }
    col = {name: i for i, name in enumerate(BW_FEATURE_NAMES)}
    snippets = {i: (HERE / "derived" / "arbitration_inputs" / "snippets" / f"{i}.jsnp"
                    ).read_bytes() for i in ids}
    indent = {i: {tw: arbitrate._indentation(arbitrate._snippet_lines(snippets[i]), tw)
                  for tw in TAB_WIDTHS} for i in ids}
    v0 = frozenset(get_adapter("java").arithmetic_ops)
    variants: dict[str, frozenset[str]] = {
        "V0_current": v0,
        "V1_minimal": frozenset({"+", "-", "*", "/"}),
        "V2_incdec": v0 | {"++", "--"},
        "V3_compound": v0 | {"+=", "-=", "*=", "/=", "%="},
    }
    variant_names = list(variants)
    arith = {i: arbitrate._arith_counts(snippets[i], variants) for i in ids}

    def cell_matrix(mode: str, tab: int, variant: str) -> Any:
        rows = []
        for i in ids:
            vec = list(matrices[mode][i])
            avg, mx = indent[i][tab]
            vec[col["avg_indentation"]] = avg
            vec[col["max_indentation"]] = mx
            if variant != "V0_current":
                vec[col["avg_arithmetic_ops"]] = arith[i][mode][variant]
            rows.append(vec)
        return np.array(rows)

    cells = {(m, t, v): cell_matrix(m, t, v)
             for m in MODES for t in TAB_WIDTHS for v in variant_names}
    y = np.array([1 if m >= PAPER_CUTOFF else 0 for m in means])
    means_arr = np.array(means)
    outer = StratifiedKFold(n_splits=10, shuffle=True, random_state=0)
    inner = StratifiedKFold(n_splits=10, shuffle=True, random_state=0)

    def train_metrics(x_tr: Any, y_tr: Any, m_tr: Any) -> tuple[int, float]:
        n_agree = 0
        for c, name in enumerate(BW_FEATURE_NAMES):
            expected = signs[name]["sign"]
            if expected == "unclear":
                continue
            rho = stats.spearman(list(x_tr[:, c]), list(m_tr))
            if (rho > 0) if expected == "+" else (rho < 0):
                n_agree += 1
        decision = cross_val_predict(LogisticRegression(max_iter=1000), x_tr, y_tr,
                                     cv=inner, method="decision_function")
        return n_agree, float(roc_auc_score(y_tr, decision))

    accs: list[float] = []
    picks: list[str] = []
    for tr_idx, te_idx in outer.split(np.zeros(len(ids)), y):
        y_tr, m_tr = y[tr_idx], means_arr[tr_idx]
        metric: dict[tuple[str, int, str], tuple[int, float]] = {}
        for key, x in cells.items():
            metric[key] = train_metrics(x[tr_idx], y_tr, m_tr)

        base = {m: metric[(m, 1, "V0_current")] for m in MODES}

        def clears(tab: int, var: str, metric: Any = metric, base: Any = base) -> bool:
            gain = False
            for m in MODES:
                a, auc = metric[(m, tab, var)]
                if a < base[m][0] or auc < base[m][1] - AUC_DROP:
                    return False
                gain = gain or a > base[m][0]
            return gain

        cands = [(t, v) for t in TAB_WIDTHS for v in variant_names if clears(t, v)]
        if cands:
            def rank(c: tuple[int, str], metric: Any = metric) -> tuple[float, ...]:
                t, v = c
                sum_a = sum(metric[(m, t, v)][0] for m in MODES)
                sum_auc = sum(metric[(m, t, v)][1] for m in MODES)
                changed = (1 if t != 1 else 0) + (1 if v != "V0_current" else 0)
                return (-sum_a, -sum_auc, changed, t, variant_names.index(v))
            tab, var = min(cands, key=rank)
        else:
            tab, var = 1, "V0_current"
        on_a, on_auc = metric[("fallback_on", tab, var)]
        off_a, off_auc = metric[("fallback_off", tab, var)]
        mode = "fallback_on" if on_a >= off_a and on_auc >= off_auc - AUC_DROP \
            else "fallback_off"
        picks.append(f"{mode}/tab={tab}/{var}")

        x = cells[(mode, tab, var)]
        clf = LogisticRegression(max_iter=1000)
        clf.fit(x[tr_idx], y_tr)
        accs.append(float(clf.score(x[te_idx], y[te_idx])))

    mean_acc = stats.mean(accs)
    ci = stats.ci95_bootstrap(accs)
    print("nested selection-aware protocol (selection re-run inside each outer fold):")
    for p, a in zip(picks, accs, strict=True):
        print(f"  picked {p:34s} fold accuracy {a:.2f}")
    print(f"nested accuracy mean {mean_acc:.3f}, ci95 bootstrap over fold "
          f"accuracies [{ci[0]:.3f}, {ci[1]:.3f}]")
    print("(reference: the non-nested reproduction reports 0.820 [0.770, 0.870])")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
