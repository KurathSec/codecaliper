#!/usr/bin/env python3
"""(Re)create the TRACKED PINNED RAW INPUTS of the Buse-Weimer lane from the
fetched archive: the provenance record of how derived/arbitration_inputs/
came to hold dataset content.

This script is NOT part of the reproduction path: the lane reads the pins, never
the archive (pinned.py). It exists so the pins are demonstrably a mechanical
byte-for-byte copy out of the sha256-verified archive rather than something
assembled by hand, and so a future maintainer can re-derive them.

    python validation/bw_faithfulness/fetch.py       # cache/DatasetBW.zip (sha-verified)
    python validation/bw_faithfulness/pin_inputs.py  # -> derived/arbitration_inputs/

Writes, verbatim from cache/DatasetBW.zip:

  derived/arbitration_inputs/snippets/1.jsnp .. 100.jsnp   the 100 Java snippets
  derived/arbitration_inputs/oracle.csv                    the per-annotator score matrix
                                                           (121 rows: id, cohort, 100 scores)

and re-derives, from the tracked oracle.csv:

  derived/arbitration_inputs/scores.csv                    snippet_id,mean_score,n_ratings

Licence: an author of the dataset (W. Weimer) granted redistribution of the raw
snippets and the annotator scores, and publication of derived data, by email on
2026-07-11 (PERMISSIONS.md; dataset.toml [datasets.bw2010.license]). These are
the ONLY dataset files in the tracked tree. The Scalabrino 2018 and Dorn 2012
corpora carry NO permission of any kind and may never be tracked, so this script
refuses to touch anything but DatasetBW.zip.

By default an existing pin is only REPORTED as differing, never overwritten:
the pins are the authoritative inputs of a published result, so re-pinning is a
deliberate act (--force) that must be justified in the changelog.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path

import pinned


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true",
                    help="overwrite pins that differ from the archive (deliberate re-pin)")
    args = ap.parse_args(argv)

    if not pinned.ARCHIVE.exists():
        print(f"ERROR: {pinned.ARCHIVE} missing. Run fetch.py first (this script is the "
              "only step that needs the archive; the lane itself runs from the pins).",
              file=sys.stderr)
        return 1
    sha = hashlib.sha256(pinned.ARCHIVE.read_bytes()).hexdigest()
    print(f"archive {pinned.ARCHIVE.name} sha256 {sha}")

    pinned.SNIPPETS_DIR.mkdir(parents=True, exist_ok=True)
    created: list[str] = []   # pin absent -> written (first pinning; not a re-pin)
    differing: list[str] = []  # pin present AND different -> the dangerous case

    def place(dest: Path, want: bytes) -> None:
        rel = str(dest.relative_to(pinned.HERE))
        if not dest.exists():
            dest.write_bytes(want)
            created.append(rel)
        elif dest.read_bytes() != want:
            differing.append(rel)
            if args.force:
                dest.write_bytes(want)

    with zipfile.ZipFile(pinned.ARCHIVE) as zf:
        names = set(zf.namelist())
        missing = [n for n in pinned.archive_members() if n not in names]
        if missing:
            print(f"ERROR: archive layout differs from dataset.toml (missing: {missing[:3]}"
                  f"{'...' if len(missing) > 3 else ''}). Confirm the layout first.",
                  file=sys.stderr)
            return 1
        for member, dest in pinned.pin_map().items():
            place(dest, zf.read(member))

    # scores.csv is DERIVED from the tracked oracle.csv, not copied from the archive.
    place(pinned.SCORES, pinned.scores_csv_text(pinned.ORACLE.read_bytes()).encode("utf-8"))

    if created:
        print(f"pinned {len(created)} file(s) that were absent: "
              + ", ".join(created[:3]) + ("..." if len(created) > 3 else ""))
    if differing and not args.force:
        print("ERROR: these existing pins DIFFER from the archive and were NOT overwritten "
              "(re-pinning a published input is deliberate: re-run with --force and "
              "justify it in CHANGELOG.md):\n  " + "\n  ".join(differing), file=sys.stderr)
        return 1
    if differing:
        print("re-pinned (--force):\n  " + "\n  ".join(differing))
    if not created and not differing:
        print("pins already byte-identical to the archive; nothing to do.")
    total = sum(p.stat().st_size for p in pinned.tracked_inputs())
    print(f"tracked pinned raw inputs: {len(pinned.tracked_inputs())} files, {total} bytes "
          f"under {pinned.PINNED.relative_to(pinned.HERE)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
