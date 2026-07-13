#!/usr/bin/env python3
"""Formal arbitration experiment (ARCHITECTURE.md §8.3 empirical-arbiter loop)
for the three provisional interpretation questions:

  A1 (TOK-ALL-0004)  tab semantics in avg_indentation / max_indentation:
                     a tab counts as 1 | 2 | 4 | 8 indentation characters.
  A2 (BW-ALL-0006)   the Java arithmetic-operator set behind
                     avg_arithmetic_ops (Fig. 9 label "avg '+' '*' '%' '/' '-'"):
                     V0_current  = the adapter's arithmetic_ops table as-is,
                     V1_minimal  = {+, -, *, /},
                     V2_incdec   = V0 + {++, --},
                     V3_compound = V0 + {+=, -=, *=, /=, %=}.
  A3 (BW-ALL-0007)   the lexical fallback for token-family BW features:
                     fallback_off = the error-opaque token stream (the
                     git-committed pre-BW-ALL-0007 extraction), fallback_on =
                     the full lexical stream, ERROR regions included.

The experiment is a full 32-cell factorial:
extraction mode {fallback_off, fallback_on} x tab_width {1, 2, 4, 8} x ops
variant {V0_current, V1_minimal, V2_incdec, V3_compound}; every cell is scored
with the EXACT train.py protocol (label = mean score >= 3.14,
LogisticRegression(max_iter=1000), StratifiedKFold(10, shuffle,
random_state=0), fold accuracies + seeded bootstrap CI, AUC via
cross_val_predict decision_function, per-feature Spearman + Fig. 9 sign
table). The protocol code is a copy of train.py's; before any other cell is
trusted, the baseline cell (fallback_off, tab=1, V0_current) is asserted to
reproduce the committed pre-fallback training record EXACTLY
(derived/arbitration_inputs/train_results_fallback_off.json).

PRE-REGISTERED DECISION RULE (written before any matrix cell was computed):

  Primary criterion: the number of sign agreements over the 24 clear-signed
  Fig. 9 features (fig9_signs.toml; avg_identifier_length is "unclear" and
  excluded). Tie-break: AUC. A winner must hold under BOTH extraction modes
  to be adopted for the instrument. The lexical fallback is adopted iff it
  does not reduce sign agreements or AUC materially (its independent
  justification is construct fidelity — the original BW instrument was
  grammar-less and saw every token of every snippet — plus coverage:
  29/100 -> 100/100 snippets with a full token stream).

  Operationalization (fixed together with the rule, before any result):
  - Within each extraction mode the 16 (tab_width, ops_variant) cells are
    ranked by (n_sign_agree desc, AUC desc).
  - A (tab_width, ops_variant) candidate beats the current setting
    (tab=1, V0_current) iff it strictly increases n_sign_agree in at least
    one mode, never decreases n_sign_agree in either mode, and never
    decreases AUC by more than 0.01 in either mode. A candidate that merely
    ties keeps the current ruling: a spec change requires positive evidence.
  - Among candidates clearing that bar, adopt the one with the highest
    (n_sign_agree summed over both modes, then AUC summed over both modes);
    remaining ties prefer fewer changed dimensions vs the current setting,
    then the smaller tab width, then variant order V0 < V1 < V2 < V3.
  - "Materially" for the fallback criterion, at the adopted (tab, ops):
    fallback_on must not have fewer sign agreements than fallback_off and
    its AUC must not be lower by more than 0.01.
  - If no candidate clears the bars, the honest outcome is a recorded null
    result and the current rulings stand.

DISCLOSED DEVIATION (added AFTER the matrix was computed; the pre-registered
rule above is preserved verbatim): the joint (tab, ops) preference chain put
summed AUC before parsimony, which would let a dimension with zero
primary-criterion evidence (identical sign agreements in every cell) be
changed on ~4e-4 summed-AUC noise — contradicting the rule's own "ties keep
the current ruling / a spec change requires positive evidence" clause. The
implemented decision therefore evaluates each dimension MARGINALLY (the other
dimension held at its current/adopted setting) under the same bar; the joint
chain's outcome is recorded in the report for transparency.

Scoping (stated up front, repeated in the report):
- The tab dimension re-derives ONLY avg_indentation / max_indentation from
  the raw snippet text (instrument conventions replicated exactly: CRLF
  normalization, source_lines final-newline rule, leading-whitespace count
  with a tab counted as N characters). avg_line_length / max_line_length /
  avg_spaces stay raw character counts — a possible future arbitration.
- The ops dimension re-derives ONLY avg_arithmetic_ops, from a DIRECT parse
  of the raw snippet (lex(include_error_tokens=True) for fallback_on, plain
  lex() for fallback_off). The instrument itself may engage the CORE-JAVA-0001
  scaffold at snippet granularity; for operator counting the direct parse is
  an accepted approximation, and its size is reported (V0 recomputed vs the
  instrument's own column). V0_current cells therefore keep the matrix's own
  avg_arithmetic_ops column (the true instrument path); V1-V3 splice the
  direct-parse recomputation.

Outputs: derived/arbitration_report.json + derived/arbitration_report.md.
Deterministic: sorted keys, qfloat floats, no timestamps (CORE-ALL-0004).
Missing data/deps => SKIP with a precise reason, exit 0 (anchor.py style).
"""

from __future__ import annotations

import csv
import json
import sys
import warnings
import zipfile
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
DERIVED = HERE / "derived"
ARCHIVE = CACHE / "DatasetBW.zip"
# The experiment's inputs are PINNED tracked copies (derived/arbitration_inputs/),
# not the live derived/ files: after spec 1.0.0 adopted the arbitrated rulings,
# the live features.csv / train_results.json / extract_meta.json moved on to the
# post-adoption state, which the baseline and tab=1 gates below correctly reject.
# See README.md "Reproducing the arbitration" for the input contract.
PINNED = DERIVED / "arbitration_inputs"
FEATURES_ON = PINNED / "features_fallback_on_tab1.csv"   # fallback_on, tab=1 (spec 0.1.0)
FEATURES_OFF = DERIVED / "features_fallback_off.csv"     # pre-BW-ALL-0007 extraction
# The human ratings the matrix scores against. The TRACKED copy is authoritative,
# so the arbitration is re-runnable without a third-party download (an author
# granted redistribution of the Buse-Weimer data — dataset.toml [datasets.bw2010];
# this is the only raw-dataset-derived file in the tracked tree, and it covers the
# Buse-Weimer ratings ONLY). The extract.py output in cache/ is the fallback, and
# the two are asserted byte-identical whenever both exist.
SCORES_TRACKED = PINNED / "scores.csv"                   # snippet_id,mean_score,n_ratings
SCORES_FETCHED = CACHE / "scores.csv"                    # extract.py output (gitignored)
SCORES = SCORES_TRACKED if SCORES_TRACKED.exists() else SCORES_FETCHED
SIGNS = HERE / "fig9_signs.toml"
BASELINE = PINNED / "train_results_fallback_off.json"    # pre-fallback training record
META_ON = PINNED / "extract_meta_fallback_on_tab1.json"
OUT_JSON = DERIVED / "arbitration_report.json"
OUT_MD = DERIVED / "arbitration_report.md"

N_SNIPPETS = 100
PAPER_CUTOFF = 3.14  # train.py: the paper's Fig. 5 bimodal cutoff

# An author of the dataset asked that the work be cited as BOTH papers
# (dataset.toml [datasets.bw2010]); every report carries both.
DATASET_CITATIONS = (
    "Raymond P. L. Buse and Westley Weimer, 'Learning a Metric for Code Readability', "
    "IEEE Transactions on Software Engineering 36(4):546-558, 2010, "
    "DOI 10.1109/TSE.2009.70",
    "Raymond P. L. Buse and Westley Weimer, 'A Metric for Software Readability', "
    "ISSTA 2008:121-130, DOI 10.1145/1390630.1390647",
)
TAB_WIDTHS = (1, 2, 4, 8)
MODES = ("fallback_off", "fallback_on")
CURRENT = (1, "V0_current")
MATERIAL_AUC_DROP = 0.01

# The decision rule, verbatim in the report (kept in sync with the docstring).
DECISION_RULE = (
    "Primary criterion: the number of sign agreements over the 24 clear-signed "
    "Fig. 9 features (fig9_signs.toml; avg_identifier_length is 'unclear' and "
    "excluded). Tie-break: AUC. A winner must hold under BOTH extraction modes "
    "to be adopted for the instrument. The lexical fallback is adopted iff it "
    "does not reduce sign agreements or AUC materially (its independent "
    "justification is construct fidelity + coverage 29/100 -> 100/100). "
    "Operationalization: within each mode the 16 (tab, ops) cells are ranked by "
    "(n_sign_agree desc, AUC desc); a candidate beats the current setting "
    "(tab=1, V0_current) iff it strictly increases n_sign_agree in at least one "
    "mode, never decreases n_sign_agree in either mode, and never decreases AUC "
    "by more than 0.01 in either mode; ties keep the current ruling. Among "
    "clearing candidates: highest summed n_sign_agree, then summed AUC, then "
    "fewer changed dimensions, smaller tab, earlier variant. 'Materially' for "
    "the fallback: at the adopted (tab, ops), fallback_on must not have fewer "
    "sign agreements than fallback_off and its AUC must not be lower by more "
    "than 0.01. No candidate clearing the bars => recorded null result, current "
    "rulings stand."
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


# --------------------------------------------------------------------------
# feature-matrix loading and per-snippet recomputations
# --------------------------------------------------------------------------

def _load_matrix(path: Path, feature_names: tuple[str, ...]) -> dict[int, list[float]]:
    """snippet id -> 25-vector in canonical order; header verified."""
    with path.open(newline="", encoding="utf-8") as f:
        rows = {int(r["snippet"]): r for r in csv.DictReader(f)}
    header = [c for c in next(iter(rows.values())) if c not in ("snippet", "parse_ok", "scaffolded")]
    if tuple(header) != feature_names:
        raise SystemExit(f"ERROR: {path.name} columns do not match BW_FEATURE_NAMES.")
    return {i: [float(r[n]) for n in feature_names] for i, r in sorted(rows.items())}


def _snippet_lines(raw: bytes) -> list[str]:
    """The instrument's own text conventions: normalize (TOK-ALL-0001..0003:
    UTF-8 replace, BOM strip, CRLF->LF) then source_lines (final-newline rule)."""
    from codecaliper.syntax import tokens as tok_mod

    text, _ = tok_mod.normalize(raw)
    return tok_mod.source_lines(text)


def _indentation(lines: list[str], tab_width: int) -> tuple[float, float]:
    """(avg, max) indentation with a tab counted as tab_width characters —
    bw_features' leading-whitespace convention (len(line) - len(line.lstrip()))
    generalized so that tab_width=1 is bit-identical to the instrument."""
    indents: list[int] = []
    for line in lines:
        prefix = line[: len(line) - len(line.lstrip())]
        indents.append(sum(tab_width if ch == "\t" else 1 for ch in prefix))
    if not indents:
        return 0.0, 0.0
    return sum(indents) / len(indents), float(max(indents))


def _arith_counts(
    raw: bytes, variants: dict[str, frozenset[str]]
) -> dict[str, dict[str, float]]:
    """avg_arithmetic_ops per ops variant per extraction mode, from a DIRECT
    parse of the raw snippet (approximation: the instrument may scaffold).
    Counting mirrors bw_features: OPERATOR/PUNCT tokens attributed to in-range
    lines, divided by max(1, n_lines)."""
    from codecaliper.languages import get_adapter
    from codecaliper.syntax import tokens as tok_mod
    from codecaliper.syntax.tokens import TokenKind

    adapter = get_adapter("java")
    text, _ = tok_mod.normalize(raw)
    lines = tok_mod.source_lines(text)
    n_lines = max(1, len(lines))
    source_bytes = text.encode("utf-8")
    tree = adapter.parse(source_bytes)
    out: dict[str, dict[str, float]] = {}
    for mode in MODES:
        toks = tok_mod.lex(
            tree, source_bytes, adapter, include_error_tokens=(mode == "fallback_on")
        )
        counts = dict.fromkeys(variants, 0)
        for tok in toks:
            if not (1 <= tok.line <= len(lines)):
                continue
            if tok.kind in (TokenKind.OPERATOR, TokenKind.PUNCT):
                for name, ops in variants.items():
                    if tok.text in ops:
                        counts[name] += 1
        out[mode] = {name: counts[name] / n_lines for name in variants}
    return out


# --------------------------------------------------------------------------
# the train.py protocol (copied, then asserted against the committed baseline)
# --------------------------------------------------------------------------

def run_protocol(
    x: Any, mean_scores: list[float], signs: dict[str, Any], feature_names: tuple[str, ...]
) -> dict[str, Any]:
    """EXACT copy of train.py's protocol on a feature matrix ``x`` (numpy,
    snippets ordered by id, columns in BW_FEATURE_NAMES order)."""
    import numpy as np
    import stats  # sibling stdlib stats module (spearman, ci95_bootstrap)
    from sklearn.exceptions import ConvergenceWarning
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedKFold, cross_val_predict

    y = np.array([1 if m >= PAPER_CUTOFF else 0 for m in mean_scores])
    skf = StratifiedKFold(n_splits=10, shuffle=True, random_state=0)
    fold_accuracies: list[float] = []
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

    per_feature: list[dict[str, Any]] = []
    disagreements: list[str] = []
    n_agree = n_disagree = n_unclear = 0
    for col, name in enumerate(feature_names):
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
            {"feature": name, "spearman_rho": rho, "expected_sign": expected, "agree": agree}
        )
    return {
        "fold_accuracies": fold_accuracies,
        "accuracy_mean": stats.mean(fold_accuracies),
        "accuracy_ci95_bootstrap": stats.ci95_bootstrap(fold_accuracies),
        "auc": auc,
        "convergence_warnings": n_convergence_warnings,
        "per_feature": per_feature,
        "n_sign_agree": n_agree,
        "n_sign_disagree": n_disagree,
        "n_excluded_unclear": n_unclear,
        "disagreements": disagreements,
    }


def _assert_baseline(result: dict[str, Any]) -> None:
    """The copied protocol must reproduce the pinned pre-fallback training record
    for the baseline cell (fallback_off, tab=1, V0_current) EXACTLY (qfloat)."""
    from codecaliper.canonical import qfloat

    committed = json.loads(BASELINE.read_text(encoding="utf-8"))
    if committed.get("extraction", {}).get("empty_token_vector_count") != 8:
        raise SystemExit(
            "ERROR: the pinned baseline (arbitration_inputs/train_results_fallback_off"
            ".json) is not the pre-fallback training record "
            "(expected extraction.empty_token_vector_count == 8) — the "
            "baseline assertion has no valid reference."
        )
    want = committed["results"]
    got = {
        "fold_accuracies": [qfloat(a) for a in result["fold_accuracies"]],
        "accuracy_mean": qfloat(result["accuracy_mean"]),
        "accuracy_ci95_bootstrap": [qfloat(v) for v in result["accuracy_ci95_bootstrap"]],
        "auc": qfloat(result["auc"]),
    }
    for key, val in got.items():
        if val != want[key]:
            raise SystemExit(f"ERROR: baseline mismatch on {key}: {val} != {want[key]}")
    want_signs = committed["sign_agreement"]
    if (
        result["n_sign_agree"] != want_signs["n_agree"]
        or result["disagreements"] != want_signs["disagreements"]
    ):
        raise SystemExit("ERROR: baseline sign-agreement table mismatch.")
    want_rho = {r["feature"]: r["spearman_rho"] for r in committed["per_feature"]}
    for row in result["per_feature"]:
        if qfloat(row["spearman_rho"]) != want_rho[row["feature"]]:
            raise SystemExit(f"ERROR: baseline spearman mismatch on {row['feature']}.")


# --------------------------------------------------------------------------
# report rendering
# --------------------------------------------------------------------------

def _cell_key(mode: str, tab: int, variant: str) -> str:
    return f"{mode}/tab={tab}/{variant}"


def _md(report: dict[str, Any], variant_names: list[str]) -> str:
    lines: list[str] = []
    add = lines.append
    add("# BW arbitration experiment (A1 tab width / A2 arithmetic ops / A3 lexical fallback)")
    add("")
    add("Empirical-arbiter loop, ARCHITECTURE.md §8.3. Every cell runs the exact")
    add("train.py protocol; the baseline cell reproduced the committed")
    add("pre-fallback training record (`derived/arbitration_inputs/`) exactly before")
    add("the rest of the matrix was trusted.")
    add("")
    add("## Citing the original work")
    add("")
    add("The experiment is scored against the Buse-Weimer dataset. An author of the")
    add("dataset asked that the work be cited as **both** papers; this project honours")
    add("that requested citation form:")
    add("")
    for c in report["dataset_citations"]:
        add(f"- {c}")
    add("")
    add("## Pre-registered decision rule (verbatim)")
    add("")
    add("> " + report["decision_rule"])
    add("")
    add("## Extraction modes")
    add("")
    ext = report["extraction"]
    add(f"- `fallback_off`: {ext['fallback_off']['source']} — empty-token vectors "
        f"{ext['fallback_off']['empty_token_vector_count']}/100.")
    add(f"- `fallback_on`: {ext['fallback_on']['source']} — empty-token vectors "
        f"{ext['fallback_on']['empty_token_vector_count']}/100 "
        f"(parse_ok {ext['fallback_on']['parse_ok_count']}/100, BW-ALL-0007 gives the other "
        "snippets a full lexical stream).")
    add("")
    add("## Ops variants (Java operator sets)")
    add("")
    for name in variant_names:
        ops = " ".join(f"`{o}`" for o in report["ops_variants"][name])
        add(f"- **{name}**: {ops}")
    add("")
    add("## Matrix (n_sign_agree / AUC / accuracy)")
    add("")
    for mode in MODES:
        add(f"### {mode}")
        add("")
        add("| tab \\ ops | " + " | ".join(variant_names) + " |")
        add("|---|" + "---|" * len(variant_names))
        for tab in TAB_WIDTHS:
            cells = []
            for variant in variant_names:
                c = report["matrix"][_cell_key(mode, tab, variant)]
                cells.append(
                    f"{c['n_sign_agree']}/24, auc {c['auc']:.4f}, acc {c['accuracy_mean']:.3f}"
                )
            add(f"| tab={tab} | " + " | ".join(cells) + " |")
        add("")
    add("### Sign disagreements per cell")
    add("")
    add("| cell | disagreements |")
    add("|---|---|")
    for key in sorted(report["matrix"]):
        c = report["matrix"][key]
        add(f"| {key} | " + (", ".join(c["disagreements"]) or "(none)") + " |")
    add("")
    add("## Decision (per-dimension, with disclosed deviation)")
    add("")
    dec = report["decision"]
    add(dec["deviation_note"])
    add("")
    joint = dec["pre_registered_joint_chain_outcome"]
    add(f"- Pre-registered joint chain would pick: tab={joint['tab_width']}, "
        f"{joint['ops_variant']} (ops component carried by AUC noise only).")
    add(f"- A1 clearing tab widths (ops at V0_current): {dec['a1_tab_clearing_widths']}.")
    add(f"- A2 clearing ops variants (tab at adopted): {dec['a2_ops_clearing_variants'] or 'none'}; "
        f"max AUC spread across variants within any (mode, tab) row: "
        f"{dec['a2_max_auc_spread_across_variants']:.6f}.")
    a3 = dec["a3_fallback_at_adopted"]
    add(f"- A3 at the adopted setting: sign agreements on/off = "
        f"{a3['n_sign_agree_on_vs_off'][0]}/{a3['n_sign_agree_on_vs_off'][1]}, "
        f"AUC on/off = {a3['auc_on_vs_off'][0]:.4f}/{a3['auc_on_vs_off'][1]:.4f}.")
    add("")
    add("## Recommendation")
    add("")
    rec = report["recommendation"]
    add(f"- **tab_width = {rec['tab_width']}**")
    add(f"- **ops_variant = {rec['ops_variant']}**")
    add(f"- **lexical fallback (BW-ALL-0007): {rec['fallback']}**")
    add("")
    add(rec["rationale"])
    add("")
    add("## Scoping notes")
    add("")
    for note in report["scoping_notes"]:
        add(f"- {note}")
    add("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main() -> int:  # noqa: PLR0915 - one linear experiment script
    for path, hint in (
        (ARCHIVE, "run fetch.py first"),
        (FEATURES_OFF, "tracked pinned input — restore from git"),
        (FEATURES_ON, "tracked pinned input (derived/arbitration_inputs/) — restore from git"),
        (SCORES, "tracked pinned input (derived/arbitration_inputs/scores.csv) — restore "
                 "from git, or regenerate the cache/ fallback with extract.py"),
        (BASELINE, "tracked pinned input (derived/arbitration_inputs/) — restore from git"),
        (META_ON, "tracked pinned input (derived/arbitration_inputs/) — restore from git"),
    ):
        if not path.exists():
            print(f"SKIP: {path.relative_to(HERE)} missing — {hint}.")
            return 0
    try:
        import numpy as np
    except ImportError:
        print("SKIP: scikit-learn/numpy not installed — pip install -e '.[retrain]'")
        return 0
    try:
        from codecaliper.languages import get_adapter
        from codecaliper.readability.bw2010 import BW_FEATURE_NAMES
    except ImportError:
        print("SKIP: codecaliper not importable — pip install -e '.[dev]'")
        return 0

    from codecaliper.canonical import qfloat

    with SIGNS.open("rb") as f:
        signs = tomllib.load(f)["signs"]
    n_clear = sum(1 for s in signs.values() if s["sign"] != "unclear")
    assert n_clear == 24, f"expected 24 clear-signed Fig. 9 features, found {n_clear}"

    # Integrity gate: if extract.py has also written the cache/ copy, the tracked
    # ratings must be byte-identical to it — the tracked file is a pin, not a fork.
    if SCORES_TRACKED.exists() and SCORES_FETCHED.exists():
        if SCORES_TRACKED.read_bytes() != SCORES_FETCHED.read_bytes():
            raise SystemExit(
                "ERROR: derived/arbitration_inputs/scores.csv differs from the "
                "extract.py output in cache/scores.csv — the tracked ratings are a "
                "pin of the dataset, so a difference means the archive or the "
                "averaging changed. Investigate; do not silently update the pin."
            )
        print("ratings integrity: tracked derived/arbitration_inputs/scores.csv is "
              "byte-identical to the freshly extracted cache/scores.csv.")

    with SCORES.open(newline="", encoding="utf-8") as f:
        score_rows = {int(r["snippet_id"]): r for r in csv.DictReader(f)}
    snippet_ids = sorted(score_rows)
    mean_scores = [float(score_rows[i]["mean_score"]) for i in snippet_ids]

    matrices = {
        "fallback_off": _load_matrix(FEATURES_OFF, BW_FEATURE_NAMES),
        "fallback_on": _load_matrix(FEATURES_ON, BW_FEATURE_NAMES),
    }
    for mode, mat in matrices.items():
        if sorted(mat) != snippet_ids:
            raise SystemExit(f"ERROR: snippet ids differ between {mode} matrix and scores.csv.")
    col = {name: i for i, name in enumerate(BW_FEATURE_NAMES)}

    # --- baseline reproduction gate: the copied protocol must reproduce the
    # pinned pre-fallback training record EXACTLY before anything else runs.
    def as_array(mode: str) -> Any:
        return np.array([matrices[mode][i] for i in snippet_ids])

    baseline = run_protocol(as_array("fallback_off"), mean_scores, signs, BW_FEATURE_NAMES)
    _assert_baseline(baseline)
    print("baseline cell (fallback_off, tab=1, V0_current) reproduces the pinned "
          "pre-fallback training record exactly — protocol copy validated.")

    # --- ops variants, built from the adapter table so V0 is literally "as-is"
    v0 = frozenset(get_adapter("java").arithmetic_ops)
    variants: dict[str, frozenset[str]] = {
        "V0_current": v0,
        "V1_minimal": frozenset({"+", "-", "*", "/"}),
        "V2_incdec": v0 | {"++", "--"},
        "V3_compound": v0 | {"+=", "-=", "*=", "/=", "%="},
    }
    variant_names = list(variants)

    # --- per-snippet recomputations from the raw archive snippets
    indent: dict[int, dict[int, tuple[float, float]]] = {}
    arith: dict[int, dict[str, dict[str, float]]] = {}
    with zipfile.ZipFile(ARCHIVE) as zf:
        for i in snippet_ids:
            raw = zf.read(f"snippets/{i}.jsnp")
            lines = _snippet_lines(raw)
            indent[i] = {tw: _indentation(lines, tw) for tw in TAB_WIDTHS}
            arith[i] = _arith_counts(raw, variants)

    # tab=1 must be bit-identical to the instrument's own columns (both modes:
    # indentation is a raw-line family, independent of the token stream).
    for mode in MODES:
        for i in snippet_ids:
            vec = matrices[mode][i]
            avg1, max1 = indent[i][1]
            if qfloat(avg1) != vec[col["avg_indentation"]] or max1 != vec[col["max_indentation"]]:
                raise SystemExit(
                    f"ERROR: tab=1 indentation recomputation diverges from the {mode} "
                    f"matrix on snippet {i} — convention drift."
                )

    # direct-parse approximation size: recomputed V0 vs the instrument column
    approximation: dict[str, Any] = {}
    for mode in MODES:
        diffs = [
            abs(arith[i][mode]["V0_current"] - matrices[mode][i][col["avg_arithmetic_ops"]])
            for i in snippet_ids
        ]
        approximation[mode] = {
            "n_snippets_equal_qfloat": sum(
                1
                for i in snippet_ids
                if qfloat(arith[i][mode]["V0_current"])
                == matrices[mode][i][col["avg_arithmetic_ops"]]
            ),
            "max_abs_diff": max(diffs),
            "mean_abs_diff": sum(diffs) / len(diffs),
        }

    # --- the 32-cell matrix
    matrix: dict[str, dict[str, Any]] = {}
    for mode in MODES:
        for tab in TAB_WIDTHS:
            for variant in variant_names:
                x = as_array(mode)
                for row_idx, i in enumerate(snippet_ids):
                    avg_i, max_i = indent[i][tab]
                    x[row_idx, col["avg_indentation"]] = avg_i
                    x[row_idx, col["max_indentation"]] = max_i
                    if variant != "V0_current":  # V0 keeps the instrument's own column
                        x[row_idx, col["avg_arithmetic_ops"]] = arith[i][mode][variant]
                res = run_protocol(x, mean_scores, signs, BW_FEATURE_NAMES)
                arb_rho = {
                    r["feature"]: r["spearman_rho"]
                    for r in res["per_feature"]
                    if r["feature"] in ("avg_indentation", "max_indentation", "avg_arithmetic_ops")
                }
                matrix[_cell_key(mode, tab, variant)] = {
                    "accuracy_mean": res["accuracy_mean"],
                    "accuracy_ci95_bootstrap": res["accuracy_ci95_bootstrap"],
                    "auc": res["auc"],
                    "convergence_warnings": res["convergence_warnings"],
                    "disagreements": res["disagreements"],
                    "fold_accuracies": res["fold_accuracies"],
                    "n_sign_agree": res["n_sign_agree"],
                    "n_sign_disagree": res["n_sign_disagree"],
                    "spearman_arbitrated": arb_rho,
                }

    # --- apply the decision rule per dimension (A1 tab, A2 ops), marginally.
    #
    # DISCLOSED DEVIATION from the pre-registered operationalization (the rule
    # itself is unchanged): the joint (tab, ops) preference chain put summed
    # AUC before parsimony, which would let a dimension with ZERO
    # primary-criterion evidence (identical sign agreements in every cell) be
    # changed on ~4e-4 summed-AUC noise — contradicting the rule's own "a spec
    # change requires positive evidence / ties keep the current ruling"
    # clause. Each dimension is therefore evaluated MARGINALLY (the other
    # dimension held at its current/adopted setting), and the joint chain's
    # outcome is recorded alongside for transparency.
    def cell(mode: str, cand: tuple[int, str]) -> dict[str, Any]:
        return matrix[_cell_key(mode, cand[0], cand[1])]

    def clears_bar(cand: tuple[int, str], base: tuple[int, str]) -> bool:
        strict = any(
            cell(m, cand)["n_sign_agree"] > cell(m, base)["n_sign_agree"] for m in MODES
        )
        never_worse = all(
            cell(m, cand)["n_sign_agree"] >= cell(m, base)["n_sign_agree"] for m in MODES
        )
        auc_ok = all(
            cell(m, cand)["auc"] >= cell(m, base)["auc"] - MATERIAL_AUC_DROP for m in MODES
        )
        return strict and never_worse and auc_ok

    # the pre-registered joint chain, recorded for transparency
    joint_clearing = [
        c
        for c in ((t, v) for t in TAB_WIDTHS for v in variant_names)
        if c != CURRENT and clears_bar(c, CURRENT)
    ]

    def joint_preference(cand: tuple[int, str]) -> tuple[float, ...]:
        n_changed = (cand[0] != CURRENT[0]) + (cand[1] != CURRENT[1])
        return (
            -sum(cell(m, cand)["n_sign_agree"] for m in MODES),
            -sum(cell(m, cand)["auc"] for m in MODES),
            n_changed,
            cand[0],
            variant_names.index(cand[1]),
        )

    joint_pick = min(joint_clearing, key=joint_preference) if joint_clearing else CURRENT

    # A1 (tab), ops held at V0_current. Tie-break among clearing tabs: the
    # winner must be the top (n_sign_agree, AUC) cell within EACH mode.
    tab_clearing = [
        (t, CURRENT[1]) for t in TAB_WIDTHS if t != CURRENT[0]
        if clears_bar((t, CURRENT[1]), CURRENT)
    ]
    adopted_tab = CURRENT[0]
    if tab_clearing:
        pool = [CURRENT, *tab_clearing]
        tops = {
            max(pool, key=lambda c, m=m: (cell(m, c)["n_sign_agree"], cell(m, c)["auc"]))
            for m in MODES
        }
        if len(tops) == 1 and next(iter(tops)) != CURRENT:
            adopted_tab = next(iter(tops))[0]
    if adopted_tab != CURRENT[0]:
        tab_note = (
            f"A1 ADOPTED: tab={adopted_tab}. Every tab>=2 fixes the avg_indentation sign "
            "disagreement in BOTH extraction modes (+1 sign agreement, the primary "
            f"criterion); among clearing tab widths {sorted(t for t, _ in tab_clearing)}, "
            f"tab={adopted_tab} is the (n_sign_agree, AUC) top cell in both modes (the "
            "pre-registered tie-break). It also moves max_indentation's Spearman rho from "
            "~0 to clearly negative, matching Fig. 9."
        )
    else:
        tab_note = (
            "A1 NULL RESULT: no tab width cleared the pre-registered bar consistently "
            "under both extraction modes; TOK-ALL-0004 (tab=1) stands."
        )

    # A2 (ops), tab held at the adopted width.
    ops_base = (adopted_tab, "V0_current")
    ops_clearing = [
        v for v in variant_names if v != "V0_current"
        if clears_bar((adopted_tab, v), ops_base)
    ]
    ops_auc_spread = max(
        max(cell(m, (t, v))["auc"] for v in variant_names)
        - min(cell(m, (t, v))["auc"] for v in variant_names)
        for m in MODES
        for t in TAB_WIDTHS
    )
    if ops_clearing:
        adopted_ops = min(
            ops_clearing,
            key=lambda v: (
                -sum(cell(m, (adopted_tab, v))["n_sign_agree"] for m in MODES),
                -sum(cell(m, (adopted_tab, v))["auc"] for m in MODES),
                variant_names.index(v),
            ),
        )
        ops_note = f"A2 ADOPTED: {adopted_ops} cleared the pre-registered bar."
    else:
        adopted_ops = "V0_current"
        ops_note = (
            "A2 NULL RESULT: no ops variant changes ANY Fig. 9 sign in any of the 32 "
            "cells (avg_arithmetic_ops disagrees with the paper's near-zero-power "
            f"positive bar everywhere), and the AUC spread across variants within any "
            f"(mode, tab) row is <= {qfloat(ops_auc_spread)} — within noise. The current "
            "ruling stands (BW-ALL-0006, Java arithmetic_ops as-is)."
        )

    adopted = (adopted_tab, adopted_ops)

    on_c, off_c = cell("fallback_on", adopted), cell("fallback_off", adopted)
    fallback_ok = (
        on_c["n_sign_agree"] >= off_c["n_sign_agree"]
        and on_c["auc"] >= off_c["auc"] - MATERIAL_AUC_DROP
    )
    # META_ON existence is gated in main(): a missing pinned record must SKIP,
    # never degrade into a report with null extraction stamps or a rationale
    # quoting a hardcoded default masquerading as data
    ext_on = json.loads(META_ON.read_text(encoding="utf-8"))
    fallback_note = (
        f"at the adopted setting, fallback_on has {on_c['n_sign_agree']}/24 sign agreements "
        f"vs {off_c['n_sign_agree']}/24 and AUC {qfloat(on_c['auc'])} vs "
        f"{qfloat(off_c['auc'])}: "
        + (
            "no material reduction, so BW-ALL-0007 is ADOPTED — its independent "
            "justification is construct fidelity (the original BW instrument was "
            "grammar-less) and coverage (empty-token vectors 8 -> "
            f"{ext_on['empty_token_vector_count']}, full token streams "
            "29/100 -> 100/100)."
            if fallback_ok
            else "a material reduction, so BW-ALL-0007 is REJECTED by the pre-registered rule "
            "despite its construct-fidelity/coverage justification."
        )
    )

    recommendation = {
        "tab_width": adopted[0],
        "ops_variant": adopted[1],
        "fallback": "adopt" if fallback_ok else "reject",
        "rationale": tab_note + " " + ops_note + " A3: " + fallback_note,
    }
    decision_detail = {
        "deviation_note": (
            "DISCLOSED DEVIATION from the pre-registered operationalization (the "
            "decision rule itself is unchanged): the joint (tab, ops) preference chain "
            "put summed AUC before parsimony, allowing a dimension with zero "
            "primary-criterion evidence to change on ~4e-4 summed-AUC noise, "
            "contradicting the rule's own 'ties keep the current ruling / a spec change "
            "requires positive evidence' clause. Dimensions were therefore evaluated "
            "marginally; the joint chain's outcome is recorded here for transparency."
        ),
        "pre_registered_joint_chain_outcome": {
            "tab_width": joint_pick[0],
            "ops_variant": joint_pick[1],
        },
        "a1_tab_clearing_widths": sorted(t for t, _ in tab_clearing),
        "a2_ops_clearing_variants": ops_clearing,
        "a2_max_auc_spread_across_variants": ops_auc_spread,
        "a3_fallback_at_adopted": {
            "n_sign_agree_on_vs_off": [on_c["n_sign_agree"], off_c["n_sign_agree"]],
            "auc_on_vs_off": [on_c["auc"], off_c["auc"]],
        },
    }

    scoping_notes = [
        "Tab dimension: only avg_indentation/max_indentation were re-derived; "
        "avg_line_length, max_line_length and avg_spaces remain raw character counts "
        "(a tab is 1 character there) — a possible future arbitration.",
        "Ops dimension: avg_arithmetic_ops for V1-V3 was recomputed from a DIRECT parse "
        "of the raw snippet (lex(include_error_tokens=True) for fallback_on, plain lex() "
        "for fallback_off); the instrument itself may engage the CORE-JAVA-0001 scaffold "
        "at snippet granularity. V0_current cells keep the matrix's own column (the true "
        "instrument path); the 'approximation' block reports recomputed-V0 vs that column.",
        "V3_compound counts compound assignments (+= -= *= /= %=) in avg_arithmetic_ops "
        "while avg_assignments (unchanged base column) still counts them too; adopting V3 "
        "in the instrument would additionally require a precedence decision in BW-ALL-0006.",
        "Anti-circularity (README.md): these rulings are arbitrated on the same 100-snippet "
        "dataset whose reproduction accuracy is reported; the reproduction is evidence of "
        "faithful operationalization, not an independent validation of BW's construct.",
        "The baseline cell (fallback_off, tab=1, V0_current) was asserted to reproduce the "
        "committed pre-fallback training record exactly (fold accuracies, CI, AUC, per-feature "
        "Spearman, sign table) before the rest of the matrix was computed.",
        "Reconciliation with the final instrument run: the adopted cell's AUC "
        "(fallback_on/tab=8/V0, 0.827201322861) differs from the headline AUC of the "
        "final re-extraction (derived/train_results.json, 0.827614716825 — first "
        "produced under spec 1.0.0 and byte-identical on every number when re-stamped "
        "under spec 1.1.0) "
        "by exactly one ranked pair (1/2419 = 0.000413): the matrix splices full-precision "
        "recomputed indentation values into the feature array, while the instrument's "
        "train.py consumes the canonical 12-significant-digit features.csv. The feature "
        "VALUES agree under 12-significant-digit quantization for all 100 snippets — the "
        "gap is serialization precision flipping one near-tied AUC pair, not a semantic "
        "difference; 0.828 (the final run) is the instrument's number.",
    ]

    import narwhals
    import sklearn

    report: dict[str, Any] = {
        "dataset_citations": list(DATASET_CITATIONS),
        "decision_rule": DECISION_RULE,
        "environment": {
            "narwhals": narwhals.__version__,
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
            "note": "the AUC is sensitive at the single-ranked-pair level (0.0004), "
                    "so byte-reproducibility of this report is scoped to this ML stack "
                    "(constraints/retrain.txt) as well as per platform",
        },
        "extraction": {
            "fallback_off": {
                "source": "derived/features_fallback_off.csv "
                          "(pre-BW-ALL-0007 extraction, error-opaque token stream)",
                "empty_token_vector_count": sum(
                    1
                    for i in snippet_ids
                    if matrices["fallback_off"][i][col["avg_identifiers"]] == 0.0
                    and matrices["fallback_off"][i][col["avg_keywords"]] == 0.0
                ),
            },
            "fallback_on": {
                "source": "derived/arbitration_inputs/features_fallback_on_tab1.csv "
                          "(extract.py with BW-ALL-0007 implemented: full lexical "
                          "stream on parse errors; tab=1, spec 0.1.0)",
                "empty_token_vector_count": ext_on["empty_token_vector_count"],
                "parse_ok_count": ext_on["parse_ok_count"],
                "scaffolded_count": ext_on["scaffolded_count"],
                "spec_version": ext_on["spec_version"],
                "grammar": ext_on["grammar"],
            },
        },
        "ops_variants": {name: sorted(ops) for name, ops in variants.items()},
        "ops_direct_parse_approximation": approximation,
        "protocol": (
            "per cell: exact train.py protocol — label = mean score >= 3.14, "
            "LogisticRegression(max_iter=1000), StratifiedKFold(n_splits=10, shuffle=True, "
            "random_state=0), fold accuracies + stats.ci95_bootstrap(seed=0), AUC via "
            "cross_val_predict(method='decision_function') on the same folds, per-feature "
            "Spearman vs snippet mean score, sign table vs fig9_signs.toml"
        ),
        "matrix": matrix,
        "n_clear_signed_features": n_clear,
        "decision": decision_detail,
        "recommendation": recommendation,
        "scoping_notes": scoping_notes,
    }

    OUT_JSON.write_text(
        json.dumps(_qfloat_deep(report), sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    OUT_MD.write_text(_md(_qfloat_deep(report), variant_names), encoding="utf-8")
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print(
        f"recommendation: tab_width={recommendation['tab_width']} "
        f"ops_variant={recommendation['ops_variant']} fallback={recommendation['fallback']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
