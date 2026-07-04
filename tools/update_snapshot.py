#!/usr/bin/env python3
"""Regenerate tests/snapshots/corpus_values.json (the spec-drift gate).

Refuses to change existing numeric values unless --confirm-spec-bump is given —
a numeric change under an unchanged spec MAJOR is exactly what the gate exists
to catch (ARCHITECTURE.md §3.2).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

from conftest import SNAPSHOT_PATH  # noqa: E402
from tools_snapshot import compute_corpus_values  # noqa: E402

from codecaliper._version import __version__  # noqa: E402
from codecaliper.spec import spec_version  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-spec-bump", action="store_true",
                        help="allow existing values to change (requires a spec MAJOR bump)")
    args = parser.parse_args()

    live = compute_corpus_values()
    if SNAPSHOT_PATH.exists():
        old = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        changed = [
            f"{case}::{key}: {vals[key]} -> {live[case][key]}"
            for case, vals in old["values"].items()
            if case in live
            for key in vals
            if key in live[case] and live[case][key] != vals[key]
        ]
        if changed and not args.confirm_spec_bump:
            print("REFUSING: existing corpus values would change:", file=sys.stderr)
            for line in changed:
                print(f"  {line}", file=sys.stderr)
            print("A numeric change requires a spec MAJOR bump; re-run with "
                  "--confirm-spec-bump after bumping rulings/index.toml.", file=sys.stderr)
            return 1
        if changed and args.confirm_spec_bump:
            old_major = str(old["spec_version"]).split(".")[0]
            new_major = spec_version().split(".")[0]
            if old_major == new_major:
                print(f"REFUSING --confirm-spec-bump: values changed but the spec "
                      f"major is still {new_major} (snapshot was {old['spec_version']}, "
                      f"current is {spec_version()}). Bump the MAJOR in "
                      "rulings/index.toml first — the flag confirms a bump, it does "
                      "not replace one.", file=sys.stderr)
                return 1

    from codecaliper.languages import available_languages, get_adapter

    snapshot = {
        "spec_version": spec_version(),
        "tool_version": __version__,
        "grammars": {
            lang: get_adapter(lang).grammar_info().version
            for lang in available_languages()
        },
        "values": live,
    }
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {SNAPSHOT_PATH} ({len(live)} cases, spec {spec_version()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
