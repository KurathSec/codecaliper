#!/usr/bin/env python3
"""Extract the 25 BW features for every dataset snippet via the PUBLIC API
(granularity="snippet", language="java") — the same path users run, no private
shortcuts.

Outputs (directory contract, ARCHITECTURE.md §8.3):

- derived/features.csv      — the 25-feature vector per snippet (committable).
- derived/extract_meta.json — spec/grammar/tool stamps + extraction stats
  (no dataset content; committable; deterministic, no timestamps).
- cache/scores.csv          — snippet_id,mean_score,n_ratings. Dataset-DERIVED
  content, so it lives in cache/ and is NEVER committed.
- cache/oracle.csv          — verbatim pass-through of the per-annotator score
  matrix from the archive (one row per annotator: id, cohort, 100 scores in
  snippet order 1..100), so train.py and future analyses can read it without
  re-opening the zip. Dataset content — cache/ only, NEVER committed.

Archive layout (confirmed 2026-07-04, recorded in dataset.toml):
snippets/1.jsnp .. snippets/100.jsnp + oracle.csv with 121 annotator rows —
the paper says 120 annotators; the discrepancy is reported as-is, never
reconciled silently. This script fails loudly if the layout differs.
"""

from __future__ import annotations

import csv
import io
import json
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
DERIVED = HERE / "derived"
ARCHIVE = CACHE / "DatasetBW.zip"
FEATURES_OUT = DERIVED / "features.csv"
META_OUT = DERIVED / "extract_meta.json"
SCORES_OUT = CACHE / "scores.csv"
ORACLE_OUT = CACHE / "oracle.csv"

N_SNIPPETS = 100
VALID_SCORES = frozenset({"1", "2", "3", "4", "5"})


def _fmt(x: float) -> str:
    """12-significant-digit float text (the CORE-ALL-0004 policy, via qfloat)."""
    from codecaliper.canonical import qfloat

    return repr(qfloat(x))


def _extract_scores(zf: zipfile.ZipFile) -> int:
    """cache/oracle.csv (verbatim matrix) + cache/scores.csv (per-snippet mean).

    Returns the annotator-row count so the caller can report the 121-vs-120
    discrepancy without reconciling it.
    """
    raw = zf.read("oracle.csv")
    ORACLE_OUT.write_bytes(raw)

    rows = list(csv.reader(io.StringIO(raw.decode("utf-8"))))
    for row in rows:
        if len(row) != 2 + N_SNIPPETS:
            raise SystemExit(
                f"ERROR: oracle.csv row for annotator {row[0]!r} has {len(row)} fields, "
                f"expected {2 + N_SNIPPETS} (id, cohort, {N_SNIPPETS} scores) — layout drift."
            )
    with SCORES_OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["snippet_id", "mean_score", "n_ratings"])
        for snip in range(1, N_SNIPPETS + 1):
            cells = [row[1 + snip] for row in rows]
            ratings = [int(c) for c in cells if c.strip() in VALID_SCORES]
            if len(ratings) != len(cells):
                raise SystemExit(
                    f"ERROR: snippet {snip} has {len(cells) - len(ratings)} non-1..5 "
                    "score cells — layout drift, update extract.py."
                )
            writer.writerow([snip, _fmt(sum(ratings) / len(ratings)), len(ratings)])
    return len(rows)


def main() -> int:
    if not ARCHIVE.exists():
        print("SKIP: cache/DatasetBW.zip missing — run fetch.py first.")
        return 0

    from codecaliper import BW_FEATURE_ORDER_SHA, measure, spec_version
    from codecaliper._version import __version__
    from codecaliper.readability.bw2010 import BW_FEATURE_NAMES

    grammar: dict[str, object] = {}
    rows: list[dict[str, object]] = []
    with zipfile.ZipFile(ARCHIVE) as zf:
        names = set(zf.namelist())
        missing = [f"snippets/{i}.jsnp" for i in range(1, N_SNIPPETS + 1)
                   if f"snippets/{i}.jsnp" not in names]
        if missing or "oracle.csv" not in names:
            print("ERROR: archive layout differs from dataset.toml "
                  f"(missing: {missing[:3]}{'...' if len(missing) > 3 else ''}"
                  f"{' oracle.csv' if 'oracle.csv' not in names else ''}) — "
                  "confirm the layout and update extract.py.", file=sys.stderr)
            return 1

        n_annotators = _extract_scores(zf)

        for i in range(1, N_SNIPPETS + 1):
            src = zf.read(f"snippets/{i}.jsnp").decode("utf-8", errors="replace")
            rep = measure(src, language="java", granularity="snippet", metrics=())
            vec = rep.readability[0]
            row: dict[str, object] = {
                "snippet": i,
                "parse_ok": rep.parse_ok,
                "scaffolded": any(d.code == "snippet-scaffolded" for d in vec.diagnostics),
            }
            row.update({n: _fmt(v) for n, v in zip(vec.names, vec.values, strict=True)})
            rows.append(row)
            if not grammar:
                g = rep.provenance.grammar
                grammar = {"abi_version": g.abi_version, "language": g.language,
                           "package": g.package, "validated": g.validated,
                           "version": g.version}

    DERIVED.mkdir(exist_ok=True)
    with FEATURES_OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    # Extraction-quality stats the report must carry (honesty, not tuning):
    # an all-ERROR tree lexes to zero tokens (CORE-ALL-0002 error-opaque), which
    # zeroes every token-family feature while raw-line features survive.
    parse_ok_count = sum(1 for r in rows if r["parse_ok"])
    scaffolded_count = sum(1 for r in rows if r["scaffolded"])
    empty_token = sum(
        1 for r in rows
        if float(str(r["avg_identifiers"])) == 0.0 and float(str(r["avg_keywords"])) == 0.0
    )
    meta = {
        "dataset_id": "bw2010-original-100java",
        "empty_token_vector_count": empty_token,
        "feature_names": list(BW_FEATURE_NAMES),
        "feature_order_sha256": BW_FEATURE_ORDER_SHA,
        "grammar": grammar,
        "n_annotators_in_archive": n_annotators,
        "n_snippets": len(rows),
        "parse_ok_count": parse_ok_count,
        "scaffolded_count": scaffolded_count,
        "spec_version": spec_version(),
        "tool_version": __version__,
    }
    META_OUT.write_text(
        json.dumps(meta, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"wrote {FEATURES_OUT}: {len(rows)} snippets "
          f"(parse_ok {parse_ok_count}/{len(rows)}, scaffolded {scaffolded_count}, "
          f"empty-token {empty_token})")
    print(f"wrote {META_OUT} (codecaliper {__version__}, spec {spec_version()}, "
          f"feature order {BW_FEATURE_ORDER_SHA[:12]})")
    print(f"wrote {SCORES_OUT} + {ORACLE_OUT} (dataset content — cache/ only, "
          f"{n_annotators} annotator rows; the paper says 120 — reported as-is)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
