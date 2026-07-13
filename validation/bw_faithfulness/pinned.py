"""The lane's INPUT CONTRACT: tracked pinned raw inputs are the primary source;
the fetched archive is an optional cross-check.

Every number this lane reports (the faithfulness reproduction AND the 32-cell
arbitration) is regenerable from files that live in the git tree, with no
network and no cache/ directory. The raw inputs are:

  derived/arbitration_inputs/snippets/1.jsnp .. 100.jsnp   the 100 Java snippets
  derived/arbitration_inputs/oracle.csv                    per-annotator score matrix
                                                           (121 rows: id, cohort, 100 scores)
  derived/arbitration_inputs/scores.csv                    snippet_id,mean_score,n_ratings
                                                           (derived from oracle.csv; pinned
                                                           because the arbitration scores
                                                           against it)

tracked under the Buse-Weimer author's explicit grant (W. Weimer, email
2026-07-11: redistribution of the raw snippets and the annotator scores, plus
publication of derived data; see PERMISSIONS.md, dataset.toml). This is the ONLY
dataset content in the tracked tree. The Scalabrino 2018 and Dorn 2012 corpora
have NO permission of any kind: they stay in the gitignored cache/, aggregates
only, forever.

Two rules, both enforced here:

1. A missing TRACKED input is a HARD ERROR (stderr, exit 1), never a SKIP. A
   measurement instrument that silently declines to reproduce its own headline
   result is the failure this project exists to expose.
2. When cache/DatasetBW.zip IS present, every pin is verified byte-identical to
   what the archive yields, and any difference is a HARD ERROR, never a silent
   re-pin. Re-pinning is a deliberate act (pin_inputs.py --force).

The archive itself is still sha256-verified on download by fetch.py
(trust-on-first-use against dataset.toml); pin_inputs.py extracts the pins from
that verified archive.
"""

from __future__ import annotations

import csv
import io
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"                      # gitignored: fetched archives, never committed
DERIVED = HERE / "derived"                  # tracked: the committable scholarly artifact
PINNED = DERIVED / "arbitration_inputs"     # tracked: the pinned inputs (this module's subject)

ARCHIVE = CACHE / "DatasetBW.zip"           # OPTIONAL cross-check source
SNIPPETS_DIR = PINNED / "snippets"
ORACLE = PINNED / "oracle.csv"
SCORES = PINNED / "scores.csv"

N_SNIPPETS = 100
VALID_SCORES = frozenset({"1", "2", "3", "4", "5"})

_RESTORE = "restore it from git (tracked pinned input) or re-create it with pin_inputs.py"


def snippet_path(i: int) -> Path:
    return SNIPPETS_DIR / f"{i}.jsnp"


def archive_members() -> list[str]:
    """The archive members the lane pins (dataset.toml layout, confirmed 2026-07-04)."""
    return [f"snippets/{i}.jsnp" for i in range(1, N_SNIPPETS + 1)] + ["oracle.csv"]


def pin_map() -> dict[str, Path]:
    """archive member -> tracked pin path (verbatim byte copies)."""
    m: dict[str, Path] = {f"snippets/{i}.jsnp": snippet_path(i) for i in range(1, N_SNIPPETS + 1)}
    m["oracle.csv"] = ORACLE
    return m


def tracked_inputs() -> list[Path]:
    """Every tracked raw input of the lane, in a stable order."""
    return [snippet_path(i) for i in range(1, N_SNIPPETS + 1)] + [ORACLE, SCORES]


def _die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def require_inputs() -> None:
    """Hard-fail (exit 1) unless every tracked raw input is present. Never SKIPs."""
    missing = [str(p.relative_to(HERE)) for p in tracked_inputs() if not p.exists()]
    if missing:
        shown = missing if len(missing) <= 5 else [*missing[:5], f"... (+{len(missing) - 5} more)"]
        _die(
            "tracked pinned raw input(s) missing:\n  " + "\n  ".join(shown)
            + f"\n{_RESTORE}. The lane runs from the pins, NOT from cache/. A missing "
              "pin means the reproduction cannot run, which is a failure, not a SKIP."
        )


def load_snippets() -> dict[int, bytes]:
    """The 100 raw snippets, read from the TRACKED pins (primary source)."""
    require_inputs()
    return {i: snippet_path(i).read_bytes() for i in range(1, N_SNIPPETS + 1)}


def load_oracle() -> bytes:
    """The raw per-annotator score matrix, read from the TRACKED pin."""
    require_inputs()
    return ORACLE.read_bytes()


def scores_csv_text(oracle_raw: bytes) -> str:
    """snippet_id,mean_score,n_ratings, derived from the per-annotator matrix.

    The float text is the instrument's own 12-significant-digit policy
    (CORE-ALL-0004, via codecaliper.canonical.qfloat), so the derivation is
    byte-stable across platforms.
    """
    from codecaliper.canonical import qfloat

    rows = list(csv.reader(io.StringIO(oracle_raw.decode("utf-8"))))
    for row in rows:
        if len(row) != 2 + N_SNIPPETS:
            _die(
                f"oracle.csv row for annotator {row[0]!r} has {len(row)} fields, expected "
                f"{2 + N_SNIPPETS} (id, cohort, {N_SNIPPETS} scores). Layout drift."
            )
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["snippet_id", "mean_score", "n_ratings"])
    for snip in range(1, N_SNIPPETS + 1):
        cells = [row[1 + snip] for row in rows]
        ratings = [int(c) for c in cells if c.strip() in VALID_SCORES]
        if len(ratings) != len(cells):
            _die(
                f"snippet {snip} has {len(cells) - len(ratings)} non-1..5 score cells. "
                "Layout drift, update pinned.py."
            )
        writer.writerow([snip, repr(qfloat(sum(ratings) / len(ratings))), len(ratings)])
    return buf.getvalue()


def n_annotators(oracle_raw: bytes) -> int:
    """Annotator rows in the pinned matrix (121; the paper says 120, reported as-is)."""
    return len(list(csv.reader(io.StringIO(oracle_raw.decode("utf-8")))))


def verify_scores_pin(oracle_raw: bytes) -> None:
    """The tracked scores.csv must be exactly what the tracked oracle.csv derives to.

    A difference is a HARD ERROR: scores.csv is a pin of a published input, not a
    cache to be refreshed.
    """
    require_inputs()
    want = scores_csv_text(oracle_raw)
    if SCORES.read_text(encoding="utf-8") != want:
        _die(
            f"{SCORES.relative_to(HERE)} is NOT the per-snippet mean of "
            f"{ORACLE.relative_to(HERE)}: the ratings pin and the annotator matrix "
            "disagree. Investigate; do not silently re-pin (pin_inputs.py --force is "
            "the deliberate path)."
        )


def crosscheck_archive() -> bool:
    """If cache/DatasetBW.zip exists, assert every pin is byte-identical to it.

    Returns True if the cross-check ran, False if the archive is absent (which is
    the normal, fully supported case: the lane never needs it). Any difference is a
    HARD ERROR, never a silent re-pin.
    """
    if not ARCHIVE.exists():
        print("cross-check: cache/DatasetBW.zip absent; running from the tracked pins "
              "alone (the supported path; fetch.py only adds the optional cross-check).")
        return False
    with zipfile.ZipFile(ARCHIVE) as zf:
        names = set(zf.namelist())
        missing = [n for n in archive_members() if n not in names]
        if missing:
            _die(
                f"cache/DatasetBW.zip layout differs from dataset.toml (missing: "
                f"{missing[:3]}{'...' if len(missing) > 3 else ''}). Confirm the layout."
            )
        differing = [
            member for member, dest in pin_map().items() if dest.read_bytes() != zf.read(member)
        ]
    if differing:
        shown = differing if len(differing) <= 5 else [
            *differing[:5], f"... (+{len(differing) - 5} more)"
        ]
        _die(
            "the tracked pins differ from cache/DatasetBW.zip:\n  " + "\n  ".join(shown)
            + "\nThe pins are a byte-for-byte copy of the sha256-verified archive, so a "
              "difference means the archive changed (or a pin was edited). Investigate; "
              "do NOT silently re-pin (pin_inputs.py --force is the deliberate path)."
        )
    print(f"cross-check: all {len(pin_map())} tracked pins are byte-identical to "
          "cache/DatasetBW.zip.")
    return True
