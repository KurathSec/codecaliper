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

import os
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


def _java() -> str:
    java_home = os.environ.get("JAVA_HOME")
    if java_home and (Path(java_home) / "bin" / "java").exists():
        return str(Path(java_home) / "bin" / "java")
    found = shutil.which("java")
    if not found:
        print("ERROR: java not found on PATH and JAVA_HOME unset.", file=sys.stderr)
        raise SystemExit(1)
    return found


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
               "tabs_expanded_8": CACHE / "corner_spaces"}
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
            expanded = "\n".join(
                ln[:len(ln) - len(ln.lstrip("\t"))].replace("\t", " " * 8)
                + ln.lstrip("\t")
                for ln in src.splitlines())
            # The corpus units are bare METHODS; rsm.jar's CLI needs a
            # compilation unit and returns NaN without one. Both corners get
            # the byte-identical unindented wrapper, so it cancels out of the
            # contrast while leaving every body line's own indentation intact.
            for corner, text in (("as_distributed", src),
                                 ("tabs_expanded_8", expanded)):
                (corners[corner] / f"S{stem}.java").write_text(
                    f"class S{stem} {{\n{text}\n}}\n", encoding="utf-8")
    if n_files == 0:
        print(f"ERROR: no snippets found under {MEMBER} in {CORPUS_ZIP.name}.",
              file=sys.stderr)
        return 1

    a = score_dir(java, corners["as_distributed"])
    b = score_dir(java, corners["tabs_expanded_8"])
    common = sorted(set(a) & set(b))
    scored = [f for f in common if a[f] == a[f] and b[f] == b[f]]  # drop NaN

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
    for cut in CUTS:
        flips = [f for f in scored if (a[f] >= cut) != (b[f] >= cut)]
        up = sum(1 for f in flips if b[f] >= cut)
        print(f"  binary classification at cut {cut}: {len(flips)} of "
              f"{len(scored)} methods change class "
              f"({up} to readable, {len(flips) - up} to unreadable)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
