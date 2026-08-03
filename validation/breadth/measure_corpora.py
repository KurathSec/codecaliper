#!/usr/bin/env python3
"""Cross-corpus parse anatomy: run codecaliper over the reused readability corpora.

Measures the Buse-Weimer (2010) and Scalabrino et al. (2018) corpora and the
Java and Python subsets of the Dorn (2012) corpus through the PUBLIC API
(`codecaliper.api.measure`), each subset under its own grammar, and reports,
per corpus row: how many snippets parse cleanly, how many are tab-indented,
and, for the failures, how many have unbalanced braces plus the median/max
ERROR-node count of the recovered parse. The brace-imbalance column is the
mid-block-truncation signature for the brace languages; it is computed
literally for every row and is a meaningful failure signature only for Java.

This script reads all three corpora from their ARCHIVES, which live in the
gitignored `validation/bw_faithfulness/cache/` and are fetched at run time by
`validation/bw_faithfulness/fetch.py --all` (URLs, checksums and per-corpus
licence status: `validation/bw_faithfulness/dataset.toml`). So `fetch.py --all` is
a prerequisite HERE, unlike the faithfulness lane, whose raw inputs are tracked
pins and which therefore needs no network.

No corpus content is committed by THIS lane. Repository-wide, the only tracked
dataset content is the Buse-Weimer raw input under
`validation/bw_faithfulness/derived/arbitration_inputs/`, redistributed under an
author's explicit grant (PERMISSIONS.md). The Scalabrino 2018 and Dorn 2012
corpora carry no permission of any kind: they are measured here and never
redistributed, and only the aggregate rates in `results.txt` are published.

The corpus rows are measured together or not at all: the reported rates are a
statement about all of them, so a missing archive is a hard error (stderr, exit 1),
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

CORPORA: dict[str, tuple[str, Callable[[str], bool], str]] = {
    "Buse-Weimer": (
        "DatasetBW.zip",
        lambda n: n.startswith("snippets/") and n.endswith(".jsnp"),
        "java",
    ),
    "Scalabrino": (
        "Dataset.zip",
        lambda n: n.startswith("Dataset/Snippets/") and n.endswith(".jsnp"),
        "java",
    ),
    # Dorn ships Java, CUDA and Python snippets (121/120/119). The Java and
    # Python subsets are measured, each under its own grammar (measuring a
    # snippet under another language's grammar would be a category error);
    # CUDA has no grammar in the instrument and is not measured.
    "Dorn-Java": (
        "DatasetDorn.zip",
        lambda n: n.startswith("dataset/snippets/java/") and n.endswith(".jsnp"),
        "java",
    ),
    "Dorn-Python": (
        "DatasetDorn.zip",
        lambda n: n.startswith("dataset/snippets/python/") and n.endswith(".jsnp"),
        "python",
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
    missing = sorted({zf for zf, _, _ in CORPORA.values() if not (CACHE / zf).exists()})
    if missing:
        print(f"error: {', '.join(missing)} missing from {CACHE}; run "
              "`python validation/bw_faithfulness/fetch.py --all` first; nothing measured.",
              file=sys.stderr)
        return 1

    from codecaliper.api import measure

    for name, (zf, sel, lang) in CORPORA.items():
        z = zipfile.ZipFile(CACHE / zf)
        files = [n for n in z.namelist() if sel(n)]
        total = clean = tabbed = brace_fail = 0
        errs: list[int] = []
        for n in sorted(files):
            src = z.read(n).decode("utf-8", "replace")
            total += 1
            if any(ln.startswith("\t") for ln in src.splitlines()):
                tabbed += 1
            rep = measure(src, language=lang)
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
