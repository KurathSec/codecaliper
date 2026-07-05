#!/usr/bin/env python3
"""Retrain under the paper's protocol and write derived/train_results.json.

Fixed protocol (ARCHITECTURE.md §8.3; deviations documented in the output):

1. label = 1 iff snippet mean score >= 3.14 — the paper's own cutoff: "We
   designate snippets that received an average score below 3.14 to be 'less
   readable' based on the natural cutoff from the bimodal distribution in
   Figure 5" (TSE 2010, section 4.1).
2. LogisticRegression(max_iter=1000) on the raw (unscaled) 25-feature vectors
   from derived/features.csv, StratifiedKFold(n_splits=10, shuffle=True,
   random_state=0).
3. Metrics: per-fold accuracies + mean, ci95_bootstrap over fold accuracies
   (stats.py, seeded), AUC via cross_val_predict decision_function over the
   same folds (deterministic), per-feature Spearman (stats.py) of each feature
   vs snippet mean score, and sign agreement vs fig9_signs.toml (features with
   sign="unclear" are excluded and counted).

DEVIATIONS FROM THE PAPER (stated here and in the report):
- Buse & Weimer ran a battery of classifiers (Bayesian, logistic, MLP, ...);
  the ~80% figure summarizes that setting. We run logistic regression ONLY.
- The paper repeats the entire 10-fold validation 10 times over fresh random
  partitionings and averages across runs; this reproduction uses ONE
  fixed-seed partitioning (random_state=0) per ARCHITECTURE.md section 8.3's
  determinism requirement.

Output is deterministic: sorted keys, floats quantized to 12 significant
digits (codecaliper.canonical.qfloat), no timestamps. Byte-identity is scoped
per platform (CORE-ALL-0004).

Missing data/deps => SKIP with a precise reason, exit 0 (anchor.py style).
"""

from __future__ import annotations

import csv
import json
import sys
import warnings
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"       # dataset-derived raw material — never committed
DERIVED = HERE / "derived"   # extractor outputs / results — the committable dir
FEATURES = DERIVED / "features.csv"
META = DERIVED / "extract_meta.json"
SCORES = CACHE / "scores.csv"  # annotator scores ARE dataset content -> cache/
SIGNS = HERE / "fig9_signs.toml"
OUT = DERIVED / "train_results.json"

PAPER_CUTOFF = 3.14  # TSE 2010 section 4.1: the bimodal-distribution cutoff (Fig. 5)
LABEL_RULE = (
    "label = 1 iff snippet mean score >= 3.14 (the paper's Figure 5 bimodal "
    "cutoff; scores below 3.14 are 'less readable')"
)
DEVIATION = (
    "(1) The paper evaluated a battery of classifiers (Bayesian classifier, "
    "logistic regression, multilayer perceptron, ...) under 10-fold "
    "cross-validation; its ~0.80 accuracy summarizes that setting. This "
    "reproduction runs logistic regression ONLY (LogisticRegression(max_iter=1000), "
    "raw unscaled features). (2) The paper repeats the entire 10-fold validation "
    "10 times over fresh random partitionings and averages across runs; this "
    "reproduction uses ONE fixed-seed partitioning (random_state=0) for "
    "byte-reproducibility (ARCHITECTURE.md section 8.3)."
)


def _qfloat_deep(obj: Any) -> Any:
    from codecaliper.canonical import qfloat

    if isinstance(obj, float):
        return qfloat(obj)
    if isinstance(obj, dict):
        return {k: _qfloat_deep(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_qfloat_deep(v) for v in obj]
    return obj


def main() -> int:
    if not FEATURES.exists() or not SCORES.exists():
        import extract  # sibling module; regenerates both outputs

        rc = extract.main()
        if rc != 0:
            print(f"SKIP: extract.py failed (exit {rc}) — cannot train.")
            return 0
        if not FEATURES.exists() or not SCORES.exists():
            print("SKIP: features/scores still missing after extract.py "
                  "(dataset not fetched?) — run fetch.py first.")
            return 0
    try:
        import numpy as np
        from sklearn.exceptions import ConvergenceWarning
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import roc_auc_score
        from sklearn.model_selection import StratifiedKFold, cross_val_predict
    except ImportError:
        print("SKIP: scikit-learn not installed — pip install -e '.[retrain]'")
        return 0
    try:
        from codecaliper.readability.bw2010 import BW_FEATURE_NAMES, BW_FEATURE_ORDER_SHA
    except ImportError:
        print("SKIP: codecaliper not importable — pip install -e '.[dev]'")
        return 0

    import stats  # sibling stdlib stats module (spearman, ci95_bootstrap)

    # --- load features (ordered by snippet id) and verify the feature order sha
    with FEATURES.open(newline="", encoding="utf-8") as f:
        feat_rows = {int(r["snippet"]): r for r in csv.DictReader(f)}
    header_features = [c for c in next(iter(feat_rows.values()))
                       if c not in ("snippet", "parse_ok", "scaffolded")]
    if tuple(header_features) != BW_FEATURE_NAMES:
        print("ERROR: derived/features.csv columns do not match BW_FEATURE_NAMES "
              f"(sha {BW_FEATURE_ORDER_SHA[:12]}) — re-run extract.py.", file=sys.stderr)
        return 1

    with SCORES.open(newline="", encoding="utf-8") as f:
        score_rows = {int(r["snippet_id"]): r for r in csv.DictReader(f)}
    snippet_ids = sorted(score_rows)
    if snippet_ids != sorted(feat_rows):
        print("ERROR: snippet ids differ between features.csv and scores.csv.",
              file=sys.stderr)
        return 1

    mean_scores = [float(score_rows[i]["mean_score"]) for i in snippet_ids]
    x = np.array(
        [[float(feat_rows[i][name]) for name in BW_FEATURE_NAMES] for i in snippet_ids]
    )
    y = np.array([1 if m >= PAPER_CUTOFF else 0 for m in mean_scores])

    # --- 10-fold CV logistic regression (fixed seed) + AUC over the same folds
    skf = StratifiedKFold(n_splits=10, shuffle=True, random_state=0)
    fold_accuracies: list[float] = []
    n_convergence_warnings = 0
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for train_idx, test_idx in skf.split(x, y):
            clf = LogisticRegression(max_iter=1000)
            clf.fit(x[train_idx], y[train_idx])
            fold_accuracies.append(float(clf.score(x[test_idx], y[test_idx])))
        decision = cross_val_predict(
            LogisticRegression(max_iter=1000), x, y, cv=skf, method="decision_function"
        )
        n_convergence_warnings = sum(
            1 for w in caught if issubclass(w.category, ConvergenceWarning)
        )
    auc = float(roc_auc_score(y, decision))
    accuracy_mean = stats.mean(fold_accuracies)
    ci95 = stats.ci95_bootstrap(fold_accuracies)

    # --- per-feature Spearman vs snippet mean score + Fig. 9 sign agreement
    with SIGNS.open("rb") as f:
        signs = tomllib.load(f)["signs"]
    per_feature: list[dict[str, Any]] = []
    disagreements: list[str] = []
    n_agree = n_disagree = n_unclear = 0
    for col, name in enumerate(BW_FEATURE_NAMES):
        rho = stats.spearman([row[col] for row in x.tolist()], mean_scores)
        expected = signs[name]["sign"]
        agree: bool | None
        if expected == "unclear":
            agree = None
            n_unclear += 1
        else:
            agree = (rho > 0) if expected == "+" else (rho < 0)
            if agree:
                n_agree += 1
            else:
                n_disagree += 1
                disagreements.append(name)
        per_feature.append(
            {"feature": name, "spearman_rho": rho, "expected_sign": expected,
             "relative_power_fig9": float(signs[name]["relative_power"]), "agree": agree}
        )

    extraction = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
    extraction.pop("feature_names", None)  # redundant with the sha; keeps the report lean

    results: dict[str, Any] = {
        "dataset": {
            "id": "bw2010-original-100java",
            "n_snippets": len(snippet_ids),
            "n_annotators_in_archive": extraction.get("n_annotators_in_archive"),
            "n_annotators_in_paper": 120,
            "annotator_count_note": (
                "the archive's oracle.csv holds 121 annotator rows, not the paper's "
                "120 — reported as-is, never reconciled silently"
            ),
        },
        "extraction": extraction,
        "labels": {
            "rule": LABEL_RULE,
            "threshold_paper_fig5": PAPER_CUTOFF,
            "n_high": int(y.sum()),
            "n_low": int(len(y) - y.sum()),
        },
        "protocol": {
            "classifier": "LogisticRegression(max_iter=1000)",
            "cv": "StratifiedKFold(n_splits=10, shuffle=True, random_state=0)",
            "auc_method": (
                "roc_auc_score over cross_val_predict(method='decision_function') "
                "on the same folds"
            ),
            "features": "raw (unscaled) 25-feature vectors from derived/features.csv",
            "bootstrap": "stats.ci95_bootstrap over the 10 fold accuracies (seed=0)",
            "deviation_from_paper": DEVIATION,
        },
        "results": {
            "fold_accuracies": fold_accuracies,
            "accuracy_mean": accuracy_mean,
            "accuracy_ci95_bootstrap": ci95,
            "auc": auc,
            "convergence_warnings": n_convergence_warnings,
        },
        "per_feature": per_feature,
        "sign_agreement": {
            "n_evaluated": n_agree + n_disagree,
            "n_agree": n_agree,
            "n_disagree": n_disagree,
            "n_excluded_unclear": n_unclear,
            "disagreements": disagreements,
        },
    }
    OUT.write_text(
        json.dumps(_qfloat_deep(results), sort_keys=True, indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT}")
    print(f"accuracy mean {accuracy_mean:.3f} ci95 [{ci95[0]:.3f}, {ci95[1]:.3f}] "
          f"auc {auc:.3f} | signs: {n_agree} agree / {n_disagree} disagree "
          f"/ {n_unclear} excluded(unclear)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
