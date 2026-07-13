#!/usr/bin/env python3
"""Cross-corpus parse anatomy: run codecaliper over three Java readability corpora.

Measures every Java snippet of the Buse-Weimer (2010), Scalabrino et al. (2018)
and Dorn (2012) corpora through the PUBLIC API (`codecaliper.api.measure`,
language="java") and reports, per corpus: how many snippets parse cleanly, how
many are tab-indented, and — for the failures — how many have unbalanced braces
plus the median/max ERROR-node count of the recovered parse.

The archives live in the gitignored `validation/bw_faithfulness/cache/` and are
fetched at run time by `validation/bw_faithfulness/fetch.py --all` (URLs,
checksums and per-corpus licence status: `validation/bw_faithfulness/dataset.toml`).
No corpus content is ever committed; the recorded output of this script is
`results.txt`, which is.

The three corpora are measured together or not at all: the reported rates are a
statement about all three, so a missing archive is a hard error (stderr, exit 1),
never a silent success. A measurement script must not exit 0 having measured nothing.
"""

from __future__ import annotations

import re
import statistics
import sys
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CACHE = HERE.parent / "bw_faithfulness" / "cache"

CORPORA: dict[str, tuple[str, Callable[[str], bool]]] = {
    "Buse-Weimer": (
        "DatasetBW.zip",
        lambda n: n.startswith("snippets/") and n.endswith(".jsnp"),
    ),
    "Scalabrino": (
        "Dataset.zip",
        lambda n: n.startswith("Dataset/Snippets/") and n.endswith(".jsnp"),
    ),
    # Dorn ships Java, CUDA and Python snippets; only the 121 Java ones are
    # measured, under the Java grammar (measuring the others as Java would be a
    # category error).
    "Dorn": (
        "DatasetDorn.zip",
        lambda n: n.startswith("dataset/snippets/java/") and n.endswith(".jsnp"),
    ),
}


def errcount(rep: Any) -> int:
    """ERROR-node count of a recovered parse, read off the diagnostic message."""
    for d in rep.diagnostics:
        m = re.search(r"contains (\d+) ERROR", d.message)
        if m:
            return int(m.group(1))
    return 0


def main() -> int:
    missing = [zf for zf, _ in CORPORA.values() if not (CACHE / zf).exists()]
    if missing:
        print(f"error: {', '.join(missing)} missing from {CACHE} — run "
              "`python validation/bw_faithfulness/fetch.py --all` first; nothing measured.",
              file=sys.stderr)
        return 1

    from codecaliper.api import measure

    for name, (zf, sel) in CORPORA.items():
        z = zipfile.ZipFile(CACHE / zf)
        files = [n for n in z.namelist() if sel(n)]
        total = clean = tabbed = brace_fail = 0
        errs: list[int] = []
        for n in sorted(files):
            src = z.read(n).decode("utf-8", "replace")
            total += 1
            if any(ln.startswith("\t") for ln in src.splitlines()):
                tabbed += 1
            rep = measure(src, language="java")
            if rep.parse_ok:
                clean += 1
            else:
                errs.append(errcount(rep))
                if src.count("{") != src.count("}"):
                    brace_fail += 1
        med = statistics.median(errs) if errs else 0
        mx = max(errs) if errs else 0
        print(f"{name:14s} N={total:3d} clean={clean:3d} ({100*clean/total:4.1f}%) "
              f"tabbed={tabbed:3d} ({100*tabbed/total:4.1f}%) fail={total-clean:3d} "
              f"brace_imbalance={brace_fail:3d} err_med={med:g} err_max={mx}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
