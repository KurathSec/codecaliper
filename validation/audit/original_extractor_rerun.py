#!/usr/bin/env python3
"""Run the ORIGINAL Buse-Weimer extractor end to end and compare it to ours.

The audit lane's other probes read the original tool's source and probe a
reimplementation's outputs. This one closes the loop the reviewers of a
readability reproduction always ask for: it runs the recovered original
extractor over the same 100 tracked snippets, recovers the 25 values IT
computes, and reports

1. a defect in the recovered artifact: five of its own 25 features are stored
   under a name its suite cannot reproduce, so its instance builder silently
   substitutes zero for them (see probes/OriginalExtractor.java for the
   mechanism, and the black-box confirmation printed below);
2. a per-feature comparison against this instrument's vectors, so that a
   disagreement can be attributed to an ambiguous definition rather than to
   either implementation;
3. what the original's own vectors yield under this project's reproduction
   protocol: Figure 9 sign agreement and ten-fold accuracy.

Prerequisites: `validation/audit/fetch.py` (the jar) and a JDK (javac/java;
recorded under Temurin 21.0.11). TRACKED snippet and score pins only.
Recorded output: original_extractor_results.txt (regenerate, never edit).
"""

from __future__ import annotations

import csv
import os
import shutil
import subprocess
import sys
from pathlib import Path

import tomllib

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
CLASSES = CACHE / "classes"
JAR = CACHE / "readability-original.jar"
BW = HERE.parent / "bw_faithfulness"
SNIPPETS = BW / "derived" / "arbitration_inputs" / "snippets"
SCORES = BW / "derived" / "arbitration_inputs" / "scores.csv"
OURS = BW / "derived" / "features.csv"
SIGNS = BW / "fig9_signs.toml"
PAPER_CUTOFF = 3.14

sys.path.insert(0, str(BW))

# Position in the original suite -> this project's canonical BW name. The
# suite's own advertised names are unusable for five entries (the defect
# above), so the mapping is positional, read off the suite's construction
# order in ReadabilityDetectorSuite.getDefaultSuite().
ORDER = [
    "avg_line_length", "avg_identifiers", "avg_keywords", "avg_numbers",
    "avg_indentation", "avg_identifier_length", "avg_comments",
    "avg_blank_lines", "max_line_length", "max_identifiers", "max_keywords",
    "max_numbers", "max_indentation", "max_identifier_length", "avg_periods",
    "avg_commas", "avg_parentheses", "avg_spaces", "avg_arithmetic_ops",
    "avg_assignments", "avg_comparison_ops", "avg_branches", "avg_loops",
    "max_char_occurrences", "max_identifier_occurrences",
]
# Features the original's own pipeline cannot retrieve (positions 9-13).
UNRETRIEVABLE = set(ORDER[8:13])

# Pair of inputs identical in every feature except maximum indentation: the
# same four code lines, the same total number of leading tabs, redistributed.
PAIR_A = "\t\tint a = 1;\n\t\tint b = 2;\n\t\tint c = 3;\n\t\tint d = 4;\n"
PAIR_B = "\tint a = 1;\n\tint b = 2;\n\t\tint c = 3;\n\t\t\t\tint d = 4;\n"
PAIR_C = "\t\t\t\tint a = 1;\n\t\t\t\tint b = 2;\n\t\t\t\tint c = 3;\n\t\t\t\tint d = 4;\n"


def _tool(name: str) -> str:
    java_home = os.environ.get("JAVA_HOME")
    if java_home and (Path(java_home) / "bin" / name).exists():
        return str(Path(java_home) / "bin" / name)
    found = shutil.which(name)
    if not found:
        print(f"ERROR: {name} not found on PATH and JAVA_HOME unset.", file=sys.stderr)
        raise SystemExit(1)
    return found


def main() -> int:
    if not JAR.exists():
        print(f"ERROR: {JAR} missing; run validation/audit/fetch.py first.",
              file=sys.stderr)
        return 1
    for p in (SNIPPETS, SCORES, OURS, SIGNS):
        if not p.exists():
            print(f"ERROR: tracked input {p} is missing.", file=sys.stderr)
            return 1
    javac, java = _tool("javac"), _tool("java")
    import stats

    CLASSES.mkdir(parents=True, exist_ok=True)
    cp = f"{CLASSES}{os.pathsep}{JAR}"
    r = subprocess.run([javac, "-nowarn", "-cp", str(JAR), "-d", str(CLASSES),
                        str(HERE / "probes" / "OriginalExtractor.java")],
                       capture_output=True, text=True, check=False)
    if r.returncode != 0:
        print(f"ERROR: javac failed:\n{r.stderr[:600]}", file=sys.stderr)
        return 1
    r = subprocess.run([java, "-cp", cp, "OriginalExtractor", str(SNIPPETS), "*.jsnp"],
                       capture_output=True, text=True, check=False)
    if r.returncode != 0:
        print(f"ERROR: OriginalExtractor failed:\n{r.stderr[:600]}", file=sys.stderr)
        return 1
    rows = [ln.split("\t") for ln in r.stdout.strip().splitlines()]
    header, body = rows[0], rows[1:]
    if len(header) != len(ORDER) + 1:
        print(f"ERROR: expected {len(ORDER)} features, got {len(header) - 1}.",
              file=sys.stderr)
        return 1
    orig = {int(row[0]): {ORDER[i]: float(v) for i, v in enumerate(row[1:])}
            for row in body}

    with SCORES.open(newline="", encoding="utf-8") as f:
        means_by_id = {int(x["snippet_id"]): float(x["mean_score"])
                       for x in csv.DictReader(f)}
    with OURS.open(newline="", encoding="utf-8") as f:
        ours = {int(x["snippet"]): x for x in csv.DictReader(f)}
    ids = sorted(means_by_id)
    means = [means_by_id[i] for i in ids]
    with SIGNS.open("rb") as f:
        signs = tomllib.load(f)["signs"]

    print(f"original extractor: {len(orig)} snippets x {len(ORDER)} features, "
          "computed by its own detector suite")
    print(f"features its own pipeline cannot retrieve by name "
          f"(silently zeroed): {len(UNRETRIEVABLE)} of {len(ORDER)} "
          f"({', '.join(sorted(UNRETRIEVABLE))})")

    # --- black-box confirmation on the scoring path
    proc = subprocess.run([java, "-jar", str(JAR)],
                          input=f"{PAIR_A}###\n{PAIR_B}###\n{PAIR_C}###\n",
                          capture_output=True, text=True, check=False, cwd=CACHE)
    scores = [ln.strip() for ln in proc.stdout.splitlines()
              if ln.strip().replace(".", "", 1).replace("-", "", 1).isdigit()]
    if len(scores) == 3:
        same = "IDENTICAL" if scores[0] == scores[1] else "different"
        moved = "moves" if scores[0] != scores[2] else "unchanged"
        print(f"black-box check on the tool's own scoring path: doubling MAX "
              f"indentation at constant average leaves the score {same} "
              f"({scores[0]} vs {scores[1]}); doubling AVERAGE indentation "
              f"{moved} it ({scores[0]} vs {scores[2]})")
    else:
        print(f"black-box check: unexpected output ({len(scores)} scores)")

    # --- per-feature comparison against this instrument
    print("per-feature agreement, original vs this instrument "
          "(Spearman over the 100 snippets, and exact-value matches):")
    for name in ORDER:
        a = [orig[i][name] for i in ids]
        b = [float(ours[i][name]) for i in ids]
        rho = stats.spearman(a, b)
        exact = sum(1 for x, y in zip(a, b, strict=True) if abs(x - y) < 1e-6)
        flag = "  (zeroed in the original's own pipeline)" if name in UNRETRIEVABLE else ""
        print(f"  {name:28s} rho {rho:+.4f}  exact {exact:3d}/100{flag}")

    # --- what the original's own vectors yield under our protocol
    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import roc_auc_score
        from sklearn.model_selection import StratifiedKFold, cross_val_predict
    except ImportError as exc:
        print(f"(scikit-learn unavailable: {exc}; skipping the protocol run)")
        return 0

    n_agree = n_eval = 0
    disagree: list[str] = []
    for name in ORDER:
        expected = signs[name]["sign"]
        if expected == "unclear":
            continue
        n_eval += 1
        rho = stats.spearman([orig[i][name] for i in ids], means)
        if (rho > 0) if expected == "+" else (rho < 0):
            n_agree += 1
        else:
            disagree.append(f"{name} ({rho:+.3f})")
    y = np.array([1 if m >= PAPER_CUTOFF else 0 for m in means])
    x = np.array([[orig[i][name] for name in ORDER] for i in ids])
    skf = StratifiedKFold(n_splits=10, shuffle=True, random_state=0)
    accs = []
    for tr, te in skf.split(x, y):
        clf = LogisticRegression(max_iter=1000)
        clf.fit(x[tr], y[tr])
        accs.append(float(clf.score(x[te], y[te])))
    dec = cross_val_predict(LogisticRegression(max_iter=1000), x, y, cv=skf,
                            method="decision_function")
    print("the original's OWN vectors under this project's reproduction "
          "protocol (logistic regression, stratified ten-fold, seed 0):")
    print(f"  Figure 9 sign agreement: {n_agree} of {n_eval}")
    print(f"  features whose sign still disagrees: "
          f"{', '.join(disagree) if disagree else 'none'}")
    print("  (this instrument's three: avg_spaces, avg_arithmetic_ops, "
          "max_char_occurrences)")
    print(f"  ten-fold accuracy {stats.mean(accs):.3f}, "
          f"AUC {float(roc_auc_score(y, dec)):.3f}")
    print("  (this instrument, adopted operationalization: 21 of 24, "
          "accuracy 0.820, AUC 0.828; the original paper reports its best "
          "classifiers at between 75% and 80%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
