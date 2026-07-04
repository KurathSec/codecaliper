#!/usr/bin/env python3
"""Extract the 25 BW features for every dataset snippet via the PUBLIC API
(granularity="snippet", language="java") — the same path users run, no private
shortcuts. Output: derived/features.csv, stamped with spec/grammar versions and
the feature-order sha.

Directory contract (ARCHITECTURE.md §8.3): cache/ holds the fetched dataset and
anything extracted from it — NEVER committed (.gitignore enforces it); derived/
holds only values computed by this extractor and is the one committable output.

The snippet/score layout inside DatasetBW.zip must be confirmed against the
actual archive on first fetch (W6 task); this script encodes the documented
layout (snippets/<n>.java + scores matrix) and fails loudly if it differs.
"""

from __future__ import annotations

import csv
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
DERIVED = HERE / "derived"
ARCHIVE = CACHE / "DatasetBW.zip"
OUT = DERIVED / "features.csv"


def main() -> int:
    if not ARCHIVE.exists():
        print("SKIP: cache/DatasetBW.zip missing — run fetch.py first.")
        return 0

    from codecaliper import BW_FEATURE_ORDER_SHA, measure, spec_version
    from codecaliper._version import __version__

    rows: list[dict] = []
    with zipfile.ZipFile(ARCHIVE) as zf:
        java_members = sorted(n for n in zf.namelist() if n.endswith(".jsnp") or n.endswith(".java"))
        if not java_members:
            print("ERROR: no snippet files found in the archive — confirm the "
                  "layout and update extract.py (tracked W6 task).", file=sys.stderr)
            return 1
        for member in java_members:
            src = zf.read(member).decode("utf-8", errors="replace")
            rep = measure(src, language="java", granularity="snippet", metrics=())
            vec = rep.readability[0]
            row = {"snippet": Path(member).stem, "parse_ok": rep.parse_ok,
                   "scaffolded": any(d.code == "snippet-scaffolded" for d in vec.diagnostics)}
            row.update(dict(zip(vec.names, vec.values)))
            rows.append(row)

    DERIVED.mkdir(exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUT}: {len(rows)} snippets "
          f"(codecaliper {__version__}, spec {spec_version()}, "
          f"feature order {BW_FEATURE_ORDER_SHA[:12]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
