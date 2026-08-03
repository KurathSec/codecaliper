#!/usr/bin/env python3
"""Second-parser robustness of the Buse-Weimer parse anatomy.

The instrument's parse anatomy (27/100 clean as written, 29 with the scaffold,
84 brace-balanced, 94 balanced+scaffold) is relative to one grammar family
(tree-sitter-java, pinned). This lane re-measures the same 100 TRACKED
snippets, under the same repair variants, with two architecturally different
front ends:

- javac (JavacTask.parse(): the JDK compiler's own parser, syntax only), and
- JavaParser (an independently implemented library parser, fetched by
  fetch.py and sha256-verified).

Variants per snippet, mirroring the instrument's policies byte for byte:
as written; the two CORE-JAVA-0001 scaffolds (class, class+method; a snippet
counts as scaffold-clean if ANY of as-written/class/class+method parses
clean, mirroring the strict error-count minimizer); brace-balanced
(validation/bw_faithfulness/brace_repair_probe.balance); and balanced plus
scaffold. javac and JavaParser's compilation-unit entry accept only
compilation units, so their as-written rates answer the entry-point question
as well as the recovery question; JavaParser's classbody and brace-wrapped
block entries are probed separately for the as-written variant.

Prerequisites: a JDK on PATH or JAVA_HOME (javac/java; recorded results were
produced under Temurin 21.0.11) and `fetch.py` (network, once). TRACKED
snippet inputs only; a missing prerequisite is a hard error, never a SKIP.
Recorded output: results.txt (regenerate, never edit).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
CLASSES = CACHE / "classes"
VARIANTS = CACHE / "variants"
JAR = CACHE / "javaparser-core-3.26.2.jar"
SNIPPETS = HERE.parent / "bw_faithfulness" / "derived" / "arbitration_inputs" / "snippets"

sys.path.insert(0, str(HERE.parent / "bw_faithfulness"))
sys.path.insert(0, str(HERE.parent.parent / "src"))


def _tool(name: str) -> str:
    java_home = os.environ.get("JAVA_HOME")
    if java_home and (Path(java_home) / "bin" / name).exists():
        return str(Path(java_home) / "bin" / name)
    found = shutil.which(name)
    if not found:
        print(f"ERROR: {name} not found on PATH and JAVA_HOME unset; "
              "install a JDK (results recorded under Temurin 21.0.11).",
              file=sys.stderr)
        raise SystemExit(1)
    return found


def _run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        print(f"ERROR: {' '.join(cmd)} failed:\n{proc.stderr}", file=sys.stderr)
        raise SystemExit(1)
    return proc.stdout


def main() -> int:
    from brace_repair_probe import balance

    from codecaliper.readability.granularity import (
        JAVA_CLASS_PREFIX,
        JAVA_CLASS_SUFFIX,
        JAVA_SNIPPET_PREFIX,
        JAVA_SNIPPET_SUFFIX,
    )

    if not SNIPPETS.is_dir():
        print(f"ERROR: tracked input {SNIPPETS} is missing.", file=sys.stderr)
        return 1
    if not JAR.exists():
        print(f"ERROR: {JAR.name} missing; run fetch.py first.", file=sys.stderr)
        return 1
    javac, java = _tool("javac"), _tool("java")

    def scaff_a(src: str) -> str:
        return JAVA_CLASS_PREFIX + src + JAVA_CLASS_SUFFIX

    def scaff_b(src: str) -> str:
        return JAVA_SNIPPET_PREFIX + src + JAVA_SNIPPET_SUFFIX

    variants = {
        "as_written": lambda s: s,
        "scaffold_class": scaff_a,
        "scaffold_class_method": scaff_b,
        "balanced": lambda s: balance(s)[0],
        "balanced_scaffold_class": lambda s: scaff_a(balance(s)[0]),
        "balanced_scaffold_class_method": lambda s: scaff_b(balance(s)[0]),
    }
    files = sorted(SNIPPETS.glob("*.jsnp"), key=lambda p: int(p.stem))
    ids = [int(p.stem) for p in files]
    for name, fn in variants.items():
        d = VARIANTS / name
        d.mkdir(parents=True, exist_ok=True)
        for p in files:
            (d / f"{int(p.stem):03d}.java").write_text(
                fn(p.read_text(encoding="utf-8")), encoding="utf-8")

    CLASSES.mkdir(exist_ok=True)
    _run([javac, "-d", str(CLASSES), str(HERE / "probes" / "JavacProbe.java")])
    _run([javac, "-cp", str(JAR), "-d", str(CLASSES),
          str(HERE / "probes" / "JavaParserProbe.java")])

    def counts(cmd: list[str]) -> dict[int, int]:
        out: dict[int, int] = {}
        for line in _run(cmd).splitlines():
            name, errs = line.split("\t")
            out[int(name.split(".")[0])] = int(errs)
        assert sorted(out) == ids, "probe did not cover all 100 snippets"
        return out

    def clean(errmaps: list[dict[int, int]]) -> int:
        return sum(1 for i in ids if any(m[i] == 0 for m in errmaps))

    sep = ":" if os.name != "nt" else ";"
    results: dict[str, dict[str, dict[int, int]]] = {"javac": {}, "javaparser": {}}
    for name in variants:
        vdir = str(VARIANTS / name)
        results["javac"][name] = counts([java, "-cp", str(CLASSES), "JavacProbe", vdir])
        results["javaparser"][name] = counts(
            [java, "-cp", f"{CLASSES}{sep}{JAR}", "JavaParserProbe", vdir, "cu"])
    jp_classbody = counts([java, "-cp", f"{CLASSES}{sep}{JAR}", "JavaParserProbe",
                           str(VARIANTS / "as_written"), "classbody"])
    jp_block = counts([java, "-cp", f"{CLASSES}{sep}{JAR}", "JavaParserProbe",
                       str(VARIANTS / "as_written"), "block"])

    jdk = _run([javac, "-version"]).strip()
    print(f"front ends: {jdk} (JavacTask.parse) | javaparser-core 3.26.2")
    for parser in ("javac", "javaparser"):
        r = results[parser]
        label = "compilation-unit entry" if parser == "javac" else "ParseStart=COMPILATION_UNIT"
        print(f"{parser} ({label}):")
        print(f"  as written                       clean= {clean([r['as_written']]):3d}/100")
        print(f"  scaffold allowed                 clean= "
              f"{clean([r['as_written'], r['scaffold_class'], r['scaffold_class_method']]):3d}/100")
        print(f"  brace-balanced                   clean= {clean([r['balanced']]):3d}/100")
        print(f"  brace-balanced + scaffold        clean= "
              f"{clean([r['balanced'], r['balanced_scaffold_class'], r['balanced_scaffold_class_method']]):3d}/100")
    print("javaparser, as written, other entry points:")
    print(f"  classbody entry                  clean= {clean([jp_classbody]):3d}/100")
    print(f"  block entry (brace-wrapped)      clean= {clean([jp_block]):3d}/100")
    print(f"  any entry (cu|classbody|block)   clean= "
          f"{clean([results['javaparser']['as_written'], jp_classbody, jp_block]):3d}/100")
    print("reference, tree-sitter-java 0.23.5 (the instrument): as written 27, "
          "scaffold 29, brace-balanced 84, balanced+scaffold 94")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
