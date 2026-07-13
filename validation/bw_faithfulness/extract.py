#!/usr/bin/env python3
"""Extract the 25 BW features for every dataset snippet via the PUBLIC API
(granularity="snippet", language="java"): the same path users run, no private
shortcuts.

INPUTS: the TRACKED PINNED raw inputs (pinned.py), derived/arbitration_inputs/
snippets/{1..100}.jsnp and oracle.csv. NOT cache/. The lane therefore regenerates
every number it reports with no network and no cache/ directory; a missing pin is
a HARD ERROR (exit 1), never a SKIP. When cache/DatasetBW.zip happens to be
present it is used as an OPTIONAL cross-check: every pin must be byte-identical
to the archive, and a difference is a hard error, never a silent re-pin.

Outputs (directory contract, ARCHITECTURE.md §8.3):

- derived/features.csv: the 25-feature vector per snippet (committable).
- derived/extract_meta.json: spec/grammar/tool stamps + extraction stats
  (no dataset content; committable; deterministic, no timestamps).

The per-snippet mean ratings (derived/arbitration_inputs/scores.csv:
snippet_id,mean_score,n_ratings) are a PIN, not an output: this script re-derives
them from the tracked oracle.csv and asserts the pin is byte-identical, so the
ratings that training and the arbitration score against are verified on every run.

Dataset layout (confirmed 2026-07-04, recorded in dataset.toml):
snippets/1.jsnp .. snippets/100.jsnp + oracle.csv with 121 annotator rows. The
paper says 120 annotators; the discrepancy is reported as-is, never reconciled
silently. This script fails loudly if the layout differs.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pinned

HERE = Path(__file__).resolve().parent
DERIVED = HERE / "derived"
FEATURES_OUT = DERIVED / "features.csv"
META_OUT = DERIVED / "extract_meta.json"

N_SNIPPETS = pinned.N_SNIPPETS


def _fmt(x: float) -> str:
    """12-significant-digit float text (the CORE-ALL-0004 policy, via qfloat)."""
    from codecaliper.canonical import qfloat

    return repr(qfloat(x))


def main() -> int:
    # The tracked pins are the primary source; a missing one is a hard error (exit 1).
    snippets = pinned.load_snippets()
    oracle_raw = pinned.load_oracle()
    pinned.crosscheck_archive()           # optional: only if cache/DatasetBW.zip exists
    pinned.verify_scores_pin(oracle_raw)  # scores.csv == mean(oracle.csv), byte-for-byte
    n_annotators = pinned.n_annotators(oracle_raw)
    print("ratings integrity: derived/arbitration_inputs/scores.csv is byte-identical to the "
          f"means re-derived from the tracked oracle.csv ({n_annotators} annotator rows).")

    from codecaliper import BW_FEATURE_ORDER_SHA, measure, spec_version
    from codecaliper._version import __version__
    from codecaliper.readability.bw2010 import BW_FEATURE_NAMES

    grammar: dict[str, object] = {}
    rows: list[dict[str, object]] = []
    for i in range(1, N_SNIPPETS + 1):
        src = snippets[i].decode("utf-8", errors="replace")
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

    # Extraction-quality stats the report must carry (honesty, not tuning).
    # With BW-ALL-0007, parse-error snippets still receive a full lexical
    # stream, so a nonzero empty-token count would mean a genuinely token-free
    # snippet or a regression (pre-BW-ALL-0007 runs reported 8 here, caused by
    # CORE-ALL-0002 error-opacity zeroing token-family features).
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
    print(f"inputs: {N_SNIPPETS} tracked snippets + tracked oracle.csv "
          f"({n_annotators} annotator rows; the paper says 120, reported as-is)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
