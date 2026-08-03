#!/usr/bin/env python3
"""Fetch the audited third-party readability tools into cache/ (gitignored).

Three artifacts, each verified against the sha256 recorded below
(TOFU-anchored 2026-08-03); a mismatching download is refused and deleted.
None is ever committed: no artifact states a license, so this lane fetches at
run time and publishes only audit observations, the same posture the corpus
lanes take for unlicensed data.

- readability-original.jar: the ORIGINAL Buse-Weimer CLI tool ("Readability
  Metric 0.2010.12", classes only, Weka bundled). Its canonical home
  (arrestedcomputing.com/readability) is gone; the URL below is a GitHub
  mirror that is byte-identical (same sha256) to the Wayback Machine capture
  of the original Google-Sites download and to a second independent mirror
  (raw.githubusercontent.com/ishtiaque05/JMetricShovel/master/libs/
  readability/read-tse/1.0.0/read-tse-1.0.0.jar).
- readability-applet.jar: from the original author's live page
  (web.eecs.umich.edu/~weimerw/data/readability/); contains the full .java
  SOURCE of the original feature detectors, which is what the source audit
  reads. The host serves an incomplete TLS chain; integrity rests on the
  sha256 pin, so a certificate failure falls back to an unverified fetch and
  the pin decides.
- readability.zip: Scalabrino et al.'s tool from the official replication
  page (rsm.jar + readability.classifier + README).
"""

from __future__ import annotations

import hashlib
import ssl
import sys
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

ARTIFACTS = {
    "readability-original.jar": (
        "https://raw.githubusercontent.com/roncoleman125/Pretty/master/Pretty/readability.jar",
        "a8eae863520f9b9378a342564f327a34e4610f9c7f9017ccb1dbed2bc0f0d847",
    ),
    "readability-applet.jar": (
        "https://web.eecs.umich.edu/~weimerw/data/readability/readability-applet.jar",
        "2532ae3002b29c95fc15bf7841b2dea1051e4a53c9dd0840a608f4a04b0e7ed1",
    ),
    "readability.zip": (
        "https://dibt-research.unimol.it/report/readability/files/readability.zip",
        "e556b9b05ed14ed76c122170bd7d43fbc39cf80b8acac2930caebe96ac284329",
    ),
}


def _get(url: str) -> bytes:
    try:
        with urllib.request.urlopen(url) as r:  # noqa: S310 - pinned https URL
            return r.read()
    except ssl.SSLError:
        # Incomplete server chain (weimerw host): integrity rests on the
        # sha256 pin below, which the caller verifies before keeping the file.
        ctx = ssl._create_unverified_context()  # noqa: S323
        with urllib.request.urlopen(url, context=ctx) as r:  # noqa: S310
            return r.read()


def main() -> int:
    CACHE.mkdir(exist_ok=True)
    for name, (url, sha) in ARTIFACTS.items():
        dest = CACHE / name
        if not dest.exists():
            print(f"fetching {url}")
            dest.write_bytes(_get(url))
        digest = hashlib.sha256(dest.read_bytes()).hexdigest()
        if digest != sha:
            dest.unlink()
            print(f"ERROR: sha256 mismatch for {name}: got {digest}, expected "
                  f"{sha}; deleted the download.", file=sys.stderr)
            return 1
        print(f"{name}: sha256 verified ({dest.stat().st_size} bytes)")
    with zipfile.ZipFile(CACHE / "readability.zip") as z:
        z.extract("rsm.jar", CACHE)
        z.extract("readability.classifier", CACHE)
    print("rsm.jar + readability.classifier extracted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
