#!/usr/bin/env python3
"""End-to-end re-run of a published readability tool under two policy corners.

Every other lane here shows that the operationalization space exists and that
tools occupy divergent points of it. This one closes the remaining step: it
takes a published, downloadable readability model, runs it end to end on a
published corpus, and measures how much its OWN OUTPUT moves between two
points of a policy space no paper states.

Tool: rsm.jar, the model of Scalabrino et al. (JSEP 2018), which run_audit.py
shows values a tab at zero columns in its visual features. It emits one
readability score in [0, 1] per file; the model is a binary classifier, so
0.5 is the readable/unreadable cut, and this script also reports the movement
at neighbouring cuts so no conclusion rests on that single choice.

Corpus: the 200 rated Java methods of the same authors' own dataset, which
carry NO redistribution permission and are therefore fetched at run time by
`validation/bw_faithfulness/fetch.py --all` into the gitignored cache and
never redistributed. Only the aggregates below are published.

The two corners differ in ONE convention and nothing else:

  A. as distributed (151 of the 200 methods are tab-indented)
  B. every leading tab expanded to eight spaces
  C. every leading tab expanded to four columns, the convention the original
     extractor's own source uses

Both corners are wrapped in a byte-identical, unindented class declaration,
because the corpus units are bare methods and the tool's CLI returns NaN
without a compilation unit; the wrapper cancels out of the contrast.

The code is semantically identical under both; only the whitespace convention
differs, and no publication of this model states which one its features
assume. Any movement between A and B is therefore movement a reader of the
published model cannot see, in the published tool's own output.

Prerequisites: `validation/audit/fetch.py` (rsm.jar), `validation/
bw_faithfulness/fetch.py --all` (the corpus archive), and a JRE. Recorded
output: policy_corner_results.txt (regenerate, never edit).
"""

from __future__ import annotations

import csv
import io
import os
import random
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
RSM = CACHE / "rsm.jar"
CORPUS_ZIP = HERE.parent / "bw_faithfulness" / "cache" / "Dataset.zip"
MEMBER = "Dataset/Snippets/"
CUTS = (0.4, 0.5, 0.6)
RATINGS = "Dataset/scores.csv"
BOOT_ITERS = 2000
BOOT_SEED = 0

# The Spearman implementation is the faithfulness lane's, not a second copy:
# the two lanes must not be able to disagree about what a rank correlation is.
sys.path.insert(0, str(HERE.parent / "bw_faithfulness"))
import stats  # noqa: E402


def _java() -> str:
    java_home = os.environ.get("JAVA_HOME")
    if java_home and (Path(java_home) / "bin" / "java").exists():
        return str(Path(java_home) / "bin" / "java")
    found = shutil.which("java")
    if not found:
        print("ERROR: java not found on PATH and JAVA_HOME unset.", file=sys.stderr)
        raise SystemExit(1)
    return found


def _mean_ratings() -> dict[int, float]:
    """{snippet number: mean human readability rating} from the archive.

    scores.csv is one row per evaluator and one column per snippet, rated 1 to
    5; the mean over the evaluator rows is the per-snippet rating the dataset's
    own papers use.
    """
    with zipfile.ZipFile(CORPUS_ZIP) as z:
        text = z.read(RATINGS).decode("utf-8", "replace")
    rows = list(csv.reader(io.StringIO(text)))
    header = rows[0]
    out: dict[int, float] = {}
    for col, name in enumerate(header):
        if not name.startswith("Snippet"):
            continue
        vals = [float(r[col]) for r in rows[1:] if r and r[col].strip()]
        if vals:
            out[int(name[len("Snippet"):])] = sum(vals) / len(vals)
    return out


def score_dir(java: str, directory: Path) -> dict[str, float]:
    """Score every .java file in a directory; returns {basename: score}."""
    files = sorted(directory.glob("*.java"))
    out: dict[str, float] = {}
    # rsm.jar loads its classifier from the working directory, so run in CACHE
    batch = 40  # keep the argument list well inside any platform limit
    for i in range(0, len(files), batch):
        chunk = [str(f) for f in files[i:i + batch]]
        proc = subprocess.run([java, "-jar", str(RSM), *chunk],
                              capture_output=True, text=True, check=False, cwd=CACHE)
        for line in proc.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) != 2 or parts[0] == "file":
                continue
            try:
                out[Path(parts[0]).name] = float(parts[1])
            except ValueError:
                continue
        if proc.returncode != 0 and not out:
            print(f"ERROR: rsm.jar failed:\n{proc.stderr[:500]}", file=sys.stderr)
            raise SystemExit(1)
    return out


def main() -> int:
    if not RSM.exists():
        print(f"ERROR: {RSM} missing; run validation/audit/fetch.py first.",
              file=sys.stderr)
        return 1
    if not CORPUS_ZIP.exists():
        print(f"ERROR: {CORPUS_ZIP} missing; run "
              "`python validation/bw_faithfulness/fetch.py --all` first "
              "(the corpus is fetched, never redistributed).", file=sys.stderr)
        return 1
    java = _java()

    # --- materialize the two corners into the gitignored cache
    corners = {"as_distributed": CACHE / "corner_tabs",
               "tabs_expanded_8": CACHE / "corner_spaces",
               "tabs_expanded_4": CACHE / "corner_spaces4"}
    for d in corners.values():
        d.mkdir(parents=True, exist_ok=True)
    n_files = n_tabbed = 0
    with zipfile.ZipFile(CORPUS_ZIP) as z:
        names = sorted(n for n in z.namelist()
                       if n.startswith(MEMBER) and n.endswith(".jsnp"))
        for n in names:
            src = z.read(n).decode("utf-8", "replace")
            n_files += 1
            if any(ln.startswith("\t") for ln in src.splitlines()):
                n_tabbed += 1
            stem = Path(n).stem
            def expand(text: str, cols: int) -> str:
                return "\n".join(
                    ln[:len(ln) - len(ln.lstrip("\t"))].replace("\t", " " * cols)
                    + ln.lstrip("\t")
                    for ln in text.splitlines())

            # expand() rebuilds the text through splitlines(), which also
            # normalises CRLF to LF. 24 of the 200 snippets carry CRLF, so
            # leaving the baseline as raw bytes would put a line-ending change
            # inside the contrast alongside the tab change. Normalise all three
            # corners identically, so the only difference is the tab column.
            baseline = "\n".join(src.splitlines())
            expanded = expand(src, 8)
            expanded4 = expand(src, 4)
            # The corpus units are bare METHODS; rsm.jar's CLI needs a
            # compilation unit and returns NaN without one. Both corners get
            # the byte-identical unindented wrapper, so it cancels out of the
            # contrast while leaving every body line's own indentation intact.
            for corner, text in (("as_distributed", baseline),
                                 ("tabs_expanded_8", expanded),
                                 ("tabs_expanded_4", expanded4)):
                (corners[corner] / f"S{stem}.java").write_text(
                    f"class S{stem} {{\n{text}\n}}\n", encoding="utf-8")
    if n_files == 0:
        print(f"ERROR: no snippets found under {MEMBER} in {CORPUS_ZIP.name}.",
              file=sys.stderr)
        return 1

    a = score_dir(java, corners["as_distributed"])
    b = score_dir(java, corners["tabs_expanded_8"])
    b4 = score_dir(java, corners["tabs_expanded_4"])
    common = sorted(set(a) & set(b) & set(b4))
    scored = [f for f in common
              if a[f] == a[f] and b[f] == b[f] and b4[f] == b4[f]]  # drop NaN

    print("tool: rsm.jar (Scalabrino et al., JSEP 2018), classifier from "
          "readability.classifier")
    print(f"corpus: {n_files} methods, {n_tabbed} tab-indented "
          f"({100 * n_tabbed / n_files:.1f}%); scored under both corners: "
          f"{len(scored)}")
    moved = [f for f in scored if a[f] != b[f]]
    deltas = sorted(b[f] - a[f] for f in scored)
    print(f"score changes when leading tabs are expanded to eight spaces: "
          f"{len(moved)} of {len(scored)} methods")
    if deltas:
        mean_d = sum(deltas) / len(deltas)
        mid = len(deltas) // 2
        median_d = deltas[mid] if len(deltas) % 2 else (deltas[mid - 1] + deltas[mid]) / 2
        print(f"  delta score (expanded minus as-distributed): mean {mean_d:+.4f}, "
              f"median {median_d:+.4f}, min {deltas[0]:+.4f}, max {deltas[-1]:+.4f}")
    for label, other in (("eight columns", b), ("four columns", b4)):
        for cut in CUTS:
            flips = [f for f in scored if (a[f] >= cut) != (other[f] >= cut)]
            up = sum(1 for f in flips if other[f] >= cut)
            print(f"  {label}, cut {cut}: {len(flips)} of {len(scored)} methods "
                  f"change class ({up} to readable, "
                  f"{len(flips) - up} to unreadable)")

    # Does the convention reach the tool's agreement with its own corpus's human
    # ratings, or only its output? The archive ships the per-evaluator ratings
    # alongside the snippets, so the association is measurable at each corner.
    ratings = _mean_ratings()
    paired = [(f, ratings[int(Path(f).stem[1:])]) for f in scored
              if int(Path(f).stem[1:]) in ratings]
    if len(paired) != len(scored):
        print(f"NOTE: {len(scored) - len(paired)} scored methods have no rating "
              f"row and are excluded from the correlations.")
    human = [r for _, r in paired]
    print(f"score against mean human rating, {len(paired)} methods "
          f"({RATINGS}, mean of the evaluator rows):")
    corner_rho = {}
    for label, table in (("as distributed (tabs count nothing)", a),
                         ("tabs expanded to eight columns", b),
                         ("tabs expanded to four columns", b4)):
        rho = stats.spearman([table[f] for f, _ in paired], human)
        corner_rho[label] = rho
        print(f"  {label:38s} Spearman {rho:+.4f}")

    # The corners share every snippet, so the contrast is paired: resample
    # methods, recompute both correlations on the same resample, difference them.
    rng = random.Random(BOOT_SEED)
    n = len(paired)
    deltas_b = []
    for _ in range(BOOT_ITERS):
        idx = [rng.randrange(n) for _ in range(n)]
        hs = [human[j] for j in idx]
        deltas_b.append(stats.spearman([b[paired[j][0]] for j in idx], hs)
                        - stats.spearman([a[paired[j][0]] for j in idx], hs))
    deltas_b.sort()
    lo = deltas_b[int(0.025 * BOOT_ITERS)]
    hi = deltas_b[int(0.975 * BOOT_ITERS)]
    d = (corner_rho["tabs expanded to eight columns"]
         - corner_rho["as distributed (tabs count nothing)"])
    print(f"  paired difference (eight columns minus as distributed): {d:+.4f}, "
          f"95% interval [{lo:+.4f}, {hi:+.4f}] "
          f"({BOOT_ITERS} resamples, seed {BOOT_SEED})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
