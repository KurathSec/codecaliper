#!/usr/bin/env python3
"""Black-box audit of two first-party readability tools' de facto policies.

Places two real, publicly downloadable pipelines into the policy space the
paper measures (the source-level findings live in README.md; this script
records the RUNNABLE observations):

1. rsm.jar (Scalabrino et al.): per-feature extraction via
   `it.unimol.readability.metric.runnable.ExtractMetrics`, on three variants
   of probes/TabProbe.java that differ only in leading whitespace (tabs,
   8 spaces per tab, 1 space per tab). For every emitted BW feature the
   verdict is mechanical: value(tabs) == value(sp8) and != value(sp1) means
   the tool expands a tab to eight columns for that feature; == value(sp1)
   means one column. Then the same extractor on the truncated Buse-Weimer
   snippet 8 (TRACKED pin) records its parse policy at feature level, and the
   scoring mode records what a fragment gets end to end.
2. readability-original.jar (Buse-Weimer 2010): a smoke run on stdin proves
   the recovered tool still runs and scores; its policies are read from its
   own source (the applet jar), not inferred from scores, because a score is
   a confound of all 25 features.

Prerequisites: fetch.py (once) and a JRE on PATH or JAVA_HOME (recorded
results were produced under Temurin 21.0.11). Recorded output: results.txt
(regenerate, never edit).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
RSM = CACHE / "rsm.jar"
ORIGINAL = CACHE / "readability-original.jar"
TABPROBE = HERE / "probes" / "TabProbe.java"
SNIPPET8 = (HERE.parent / "bw_faithfulness" / "derived" / "arbitration_inputs"
            / "snippets" / "8.jsnp")


def _java() -> str:
    java_home = os.environ.get("JAVA_HOME")
    if java_home and (Path(java_home) / "bin" / "java").exists():
        return str(Path(java_home) / "bin" / "java")
    found = shutil.which("java")
    if not found:
        print("ERROR: java not found on PATH and JAVA_HOME unset.", file=sys.stderr)
        raise SystemExit(1)
    return found


def extract_bw(java: str, file: Path) -> dict[str, float]:
    proc = subprocess.run(
        [java, "-cp", str(RSM), "it.unimol.readability.metric.runnable.ExtractMetrics",
         str(file)],
        capture_output=True, text=True, check=False, cwd=CACHE)
    out: dict[str, float] = {}
    for line in proc.stdout.splitlines():
        m = re.match(r"(BW[^:]*):\s*(.+)", line.strip())
        if m:
            try:
                out[m.group(1).strip()] = float(m.group(2))
            except ValueError:
                out[m.group(1).strip()] = float("nan")
    if proc.returncode != 0 and not out:
        print(f"ERROR: ExtractMetrics failed on {file.name}:\n{proc.stderr[:500]}",
              file=sys.stderr)
        raise SystemExit(1)
    return out


def main() -> int:
    for p in (RSM, ORIGINAL, SNIPPET8, TABPROBE):
        if not p.exists():
            print(f"ERROR: {p} missing (run fetch.py first?).", file=sys.stderr)
            return 1
    java = _java()
    version = subprocess.run([java, "-version"], capture_output=True, text=True,
                             check=False).stderr.splitlines()[0]
    print(f"runtime: {version}")

    # --- rsm.jar tab policy, feature level
    master = TABPROBE.read_text(encoding="utf-8")
    variants = {
        "tabs": master,
        "sp8": master.replace("\t", " " * 8),
        "sp1": master.replace("\t", " " * 1),
    }
    vals: dict[str, dict[str, float]] = {}
    vdir = CACHE / "tabprobe"
    vdir.mkdir(exist_ok=True)
    for name, text in variants.items():
        f = vdir / f"TabProbe_{name}.java"
        f.write_text(text, encoding="utf-8")
        vals[name] = extract_bw(java, f)
    features = sorted(vals["tabs"])
    print(f"rsm.jar ExtractMetrics: {len(features)} BW features emitted")
    tab8 = tab1 = tab0 = neither = 0
    for feat in features:
        t, s8, s1 = vals["tabs"][feat], vals["sp8"][feat], vals["sp1"][feat]
        if s8 == s1:
            continue  # feature blind to the whitespace difference
        if t == s8:
            tab8 += 1
            verdict = "expands tab to 8"
        elif t == s1:
            tab1 += 1
            verdict = "counts tab as 1"
        elif t == 0.0 and s1 > 0:
            tab0 += 1
            verdict = "tab contributes zero (ignored)"
        else:
            neither += 1
            verdict = "tab contributes less than one column"
        print(f"  {feat}: tabs={t:g} sp8={s8:g} sp1={s1:g} -> {verdict}")
    print(f"rsm.jar tab policy over whitespace-sensitive BW features: "
          f"{tab8} expand-to-8, {tab1} count-as-1, {tab0} ignored, "
          f"{neither} below-one-column")
    def score_of(out: str) -> str:
        # keep only "<basename>\t<score>": recorded output must carry no
        # machine-specific absolute path
        if not out.strip():
            return "(no output)"
        parts = out.strip().splitlines()[-1].split("\t")
        return f"{Path(parts[0]).name}\t{parts[-1]}" if len(parts) > 1 else parts[-1]

    well = subprocess.run([java, "-jar", str(RSM), str(vdir / 'TabProbe_tabs.java')],
                          capture_output=True, text=True, check=False, cwd=CACHE)
    print(f"rsm.jar scoring mode on the well-formed tab probe: {score_of(well.stdout)}")

    # --- rsm.jar on a truncated fragment (tracked snippet 8)
    frag = vdir / "Fragment8.java"
    frag.write_text(SNIPPET8.read_text(encoding="utf-8"), encoding="utf-8")
    fvals = extract_bw(java, frag)
    n_nan = sum(1 for v in fvals.values() if v != v)
    n_zero = sum(1 for v in fvals.values() if v == 0.0)
    print(f"rsm.jar ExtractMetrics on truncated snippet 8: {len(fvals)} BW "
          f"features emitted, {n_nan} NaN, {n_zero} zero")
    score = subprocess.run([java, "-jar", str(RSM), str(frag)],
                           capture_output=True, text=True, check=False, cwd=CACHE)
    print(f"rsm.jar scoring mode on the fragment: {score_of(score.stdout)}")

    # --- original 2010 jar smoke run
    smoke = subprocess.run([java, "-jar", str(ORIGINAL)],
                           input=master + "\n###\n", capture_output=True,
                           text=True, check=False, cwd=CACHE)
    scores = [ln for ln in smoke.stdout.splitlines()
              if re.fullmatch(r"-?\d+\.\d+(E-?\d+)?", ln.strip())]
    print(f"readability-original.jar (stdin, ### separator): runs, "
          f"{len(scores)} score line(s), first: {scores[0] if scores else 'NONE'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
