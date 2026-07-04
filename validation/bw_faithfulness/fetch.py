#!/usr/bin/env python3
"""Fetch the original BW dataset (never committed; license UNVERIFIED — local
research use only). Honest SKIP on unavailability, anchor.py style."""

from __future__ import annotations

import hashlib
import sys
import urllib.error
import urllib.request
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"


def main() -> int:
    with (HERE / "dataset.toml").open("rb") as f:
        meta = tomllib.load(f)
    url = meta["dataset"]["url"]
    want_sha = meta["dataset"]["sha256"]
    CACHE.mkdir(exist_ok=True)
    dest = CACHE / "DatasetBW.zip"

    if not dest.exists():
        print(f"fetching {url} ...")
        try:
            urllib.request.urlretrieve(url, dest)  # noqa: S310 — pinned research URL
        except (urllib.error.URLError, OSError) as exc:
            print(f"SKIP: dataset unreachable ({exc}); the faithfulness pipeline "
                  "cannot run without it, but absence never fails a build.")
            return 0

    got_sha = hashlib.sha256(dest.read_bytes()).hexdigest()
    if not want_sha:
        print(f"NOTE: dataset.toml sha256 is empty (trust-on-first-use); "
              f"record this value: {got_sha}")
    elif got_sha != want_sha:
        print(f"ERROR: checksum mismatch: expected {want_sha}, got {got_sha}",
              file=sys.stderr)
        return 1
    print(f"ok: {dest} ({dest.stat().st_size} bytes)")
    print("REMINDER: license status is UNVERIFIED (dataset.toml) — local research "
          "use only; never commit or redistribute the data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
