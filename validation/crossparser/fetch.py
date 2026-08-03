#!/usr/bin/env python3
"""Fetch the second-parser dependency (JavaParser) into cache/ (gitignored).

The cross-parser lane needs one third-party artifact: javaparser-core, an
independently implemented Java parser widely used in SE research pipelines.
It is fetched from Maven Central and verified against the sha256 recorded
below (TOFU-anchored 2026-08-03); a mismatching download is refused and
deleted. The jar is never committed. The other second parser, javac, ships
with the JDK and needs no fetch.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

JAR = "javaparser-core-3.26.2.jar"
URL = ("https://repo1.maven.org/maven2/com/github/javaparser/javaparser-core/"
       "3.26.2/" + JAR)
SHA256 = "3e3e0c65d57d12797dbead3df1ebb28e7583737d0cd1f2a898dba6febd50ab88"
SIZE = 1440274


def main() -> int:
    CACHE.mkdir(exist_ok=True)
    dest = CACHE / JAR
    if not dest.exists():
        print(f"fetching {URL}")
        with urllib.request.urlopen(URL) as r:  # noqa: S310 - pinned https URL
            dest.write_bytes(r.read())
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    if digest != SHA256:
        dest.unlink()
        print(f"ERROR: sha256 mismatch for {JAR}: got {digest}, expected "
              f"{SHA256}; deleted the download.", file=sys.stderr)
        return 1
    print(f"{JAR}: sha256 verified ({dest.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
