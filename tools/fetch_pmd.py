#!/usr/bin/env python3
"""Fetch the pinned PMD distribution into the gitignored .oracles/.

PMD is the Java differential oracle (ARCHITECTURE.md §8.2). It is a JVM tool,
so it cannot ride along in `pip install -e '.[oracles]'` with radon, lizard and
cognitive_complexity, and this script is the Java half of that install step.

The pin lives in tests/differential/pmd.toml, and it is enforced twice: the
archive is sha256-verified here before anything is unpacked, and the harness
asserts at run time that the PMD which actually answered reports the pinned
version. Neither check is skippable, because PMD's counting can move between
releases: an unnoticed upgrade would silently re-baseline the divergence table.

The download is idempotent. A present, correctly-hashed archive is reused, and
an already-unpacked distribution is left alone unless --force is given.

Nothing fetched here is ever committed: .oracles/ is gitignored, and the
destination is checked to be inside .oracles/ before anything is written.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import stat
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

ROOT = Path(__file__).resolve().parent.parent
PIN = ROOT / "tests" / "differential" / "pmd.toml"
ORACLES = ROOT / ".oracles"


def load_pin() -> dict[str, Any]:
    with PIN.open("rb") as f:
        return dict(tomllib.load(f)["pmd"])


def _dest(name: str) -> Path:
    """.oracles/<name>, refusing any name that escapes .oracles/."""
    dest = (ORACLES / name).resolve()
    if dest.parent != ORACLES.resolve():
        raise SystemExit(f"ERROR: {name!r} would write outside {ORACLES}. Refusing.")
    return dest


def _make_executable(path: Path) -> None:
    """zipfile does not preserve the executable bit, and nor does every cache."""
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fetch the pinned PMD into .oracles/.")
    ap.add_argument("--force", action="store_true",
                    help="re-download and re-unpack even if already present")
    args = ap.parse_args(argv)

    pin = load_pin()
    version, url, want_sha = pin["version"], pin["url"], pin["sha256"]
    home = _dest(pin["unpacks_to"])
    binary = home / "bin" / "pmd"

    if binary.is_file() and not args.force:
        # Also on this path: a cache restore that dropped the mode bits would
        # otherwise surface as a bare "permission denied" from the launcher.
        _make_executable(binary)
        print(f"ok: PMD {version} already present at {binary}")
        return 0

    ORACLES.mkdir(exist_ok=True)
    archive = _dest(Path(url).name)

    if archive.is_file() and not args.force and _digest(archive) == want_sha:
        print(f"reusing verified archive {archive}")
    else:
        print(f"fetching {url} ({pin['size_bytes']} bytes) ...")
        try:
            urllib.request.urlretrieve(url, archive)  # noqa: S310 (pinned release URL)
        except (urllib.error.URLError, OSError) as exc:
            print(f"ERROR: cannot fetch PMD {version}: {exc}", file=sys.stderr)
            return 1

    got_sha = _digest(archive)
    if got_sha != want_sha:
        archive.unlink(missing_ok=True)
        print(
            f"ERROR: PMD {version} checksum mismatch.\n"
            f"  expected {want_sha}\n"
            f"  got      {got_sha}\n"
            "The archive was deleted. A release asset that changed under a fixed "
            "tag is not something to work around: verify the upstream release "
            "before touching tests/differential/pmd.toml.",
            file=sys.stderr,
        )
        return 1

    if home.exists():
        shutil.rmtree(home)
    with zipfile.ZipFile(archive) as z:
        # The archive is sha256-pinned, so its member names are known-good; the
        # guard is here so that a future pin bump cannot quietly gain a member
        # that unpacks outside .oracles/.
        for member in z.namelist():
            resolved = (ORACLES / member).resolve()
            if not resolved.is_relative_to(ORACLES.resolve()):
                raise SystemExit(f"ERROR: archive member {member!r} escapes {ORACLES}.")
        z.extractall(ORACLES)

    if not binary.is_file():
        print(f"ERROR: {archive.name} did not unpack to {binary} "
              f"(tests/differential/pmd.toml says unpacks_to = {pin['unpacks_to']!r})",
              file=sys.stderr)
        return 1
    _make_executable(binary)

    print(f"ok: PMD {version} unpacked to {home}")
    print("NOTE: .oracles/ is gitignored; nothing fetched here is ever committed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
