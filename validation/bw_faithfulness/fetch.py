#!/usr/bin/env python3
"""Fetch the readability corpora recorded in dataset.toml into the gitignored cache/.

Nothing here is required to reproduce the Buse-Weimer faithfulness result or the
arbitration. That lane runs from the tracked pins in derived/arbitration_inputs/
(pinned.py), offline; fetching `bw2010` only adds an optional cross-check of
those pins against the archive. validation/breadth/ is the opposite case: the
Scalabrino 2018 and Dorn 2012 corpora are not tracked and never will be, so the
cross-corpus parse rates genuinely require this fetch and a network.

Licence posture is per corpus and recorded in dataset.toml. An author granted
redistribution of the Buse-Weimer data (email 2026-07-11). NO permission has been
sought or granted for the Scalabrino and Dorn corpora, so those are fetched at
run time and only aggregate/derived results are ever published. Nothing fetched
here is ever committed: every download lands inside cache/ (gitignored), and the
destination is checked to be inside cache/ before anything is written.

Each archive is verified against the sha256 in dataset.toml (trust on first use:
an empty sha256 prints the observed value to record, instead of failing). An
unreachable corpus SKIPs rather than failing: this script is a convenience, and
the pipelines that truly need a corpus say so themselves.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
PRIMARY = "bw2010"


def _load() -> dict[str, dict[str, Any]]:
    with (HERE / "dataset.toml").open("rb") as f:
        return dict(tomllib.load(f)["datasets"])


def _dest(archive: str) -> Path:
    """cache/<archive>, refusing any name that escapes cache/ (path-traversal guard)."""
    dest = (CACHE / archive).resolve()
    if dest.parent != CACHE.resolve():
        raise SystemExit(
            f"ERROR: dataset.toml archive name {archive!r} would write outside "
            f"{CACHE}. Refusing."
        )
    return dest


def fetch_one(key: str, meta: dict[str, Any]) -> int:
    url = meta["url"]
    want_sha = meta["sha256"]
    dest = _dest(meta["archive"])
    lic = meta["license"]

    if not dest.exists():
        print(f"fetching {url} ...")
        try:
            urllib.request.urlretrieve(url, dest)  # noqa: S310 (pinned research URL)
        except (urllib.error.URLError, OSError) as exc:
            print(f"SKIP: {key} unreachable ({exc}); the pipelines that need it "
                  "cannot run, but absence never fails a build.")
            return 0

    got_sha = hashlib.sha256(dest.read_bytes()).hexdigest()
    if not want_sha:
        print(f"NOTE: dataset.toml sha256 for {key} is empty (trust-on-first-use); "
              f"record this value: {got_sha}")
    elif got_sha != want_sha:
        print(f"ERROR: {key} checksum mismatch: expected {want_sha}, got {got_sha}",
              file=sys.stderr)
        return 1
    print(f"ok: {dest} ({dest.stat().st_size} bytes); licence {lic['status']}, "
          f"redistributable={lic['redistributable']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    datasets = _load()
    ap = argparse.ArgumentParser(description="Fetch readability corpora into cache/.")
    ap.add_argument("ids", nargs="*", choices=list(datasets), default=[],
                    help=f"dataset ids to fetch (default: {PRIMARY})")
    ap.add_argument("--all", action="store_true",
                    help="fetch every corpus recorded in dataset.toml")
    args = ap.parse_args(argv)

    keys: list[str] = list(datasets) if args.all else (list(args.ids) or [PRIMARY])
    CACHE.mkdir(exist_ok=True)
    rc = 0
    for key in keys:
        rc |= fetch_one(key, datasets[key])
    print("NOTE: cache/ is gitignored; nothing fetched here is ever committed. "
          "Buse-Weimer: an author granted redistribution and derived publication "
          "(email 2026-07-11). Scalabrino 2018 / Dorn 2012: no permission sought or "
          "granted, so run-time fetch, aggregate/derived results only, never "
          "redistributed (dataset.toml).")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
