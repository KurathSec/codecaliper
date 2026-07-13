#!/usr/bin/env python3
"""Render tests/differential/divergences.toml into docs/spec/divergences.md.

The TOML classification table is the single source of truth; the differential
lane (tests/differential/) keeps it complete in both directions. An
unclassified divergence fails, and so does a stale entry no longer observed, so
this rendered list is the complete known-divergence artifact
(ARCHITECTURE.md §3.4). CI diffs the output like docs/spec/rulings.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

from codecaliper.spec import require, spec_version

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "tests" / "differential" / "divergences.toml"
OUT = ROOT / "docs" / "spec" / "divergences.md"
CONSTRAINTS = ROOT / "constraints" / "ci.txt"
_ORACLES = ("radon", "lizard", "cognitive-complexity")


def _oracle_pins_line() -> str:
    """The pinned oracle versions, read from constraints/ci.txt so the doc can
    never drift from the calibration source of truth."""
    pins = []
    for line in CONSTRAINTS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        name = line.split("==")[0].strip().lower()
        if "==" in line and not line.startswith("#") and name in _ORACLES:
            pins.append(f"`{line}`")
    return ", ".join(pins) + "."


def render() -> str:
    with TABLE.open("rb") as f:
        entries = tomllib.load(f).get("divergence", [])
    for e in entries:
        require(e["ruling"])  # a phantom ruling must not reach the published doc
    lines = [
        f"# Known divergences from external oracles (spec v{spec_version()})",
        "",
        "> Generated from `tests/differential/divergences.toml` by",
        "> `tools/gen_divergences.py`. Do not edit by hand. The differential",
        "> lane (`tests/differential/`) keeps this list complete in both",
        "> directions: an unclassified divergence fails CI, and so does a",
        "> stale entry that is no longer observed (ARCHITECTURE.md §3.4).",
        "",
        "Values are per named function; `unit` is the codecaliper qualified",
        "name. `ours` is the codecaliper value pinned by the cited ruling;",
        "`theirs` is the installed oracle's value. Cognitive comparisons run",
        "codecaliper in `sonar-compat` mode. `snippet:*` inputs are defined in",
        "`tests/test_bw_port_fidelity.py` (EXTRA_SNIPPETS) and",
        "`tests/differential/_harness.py` (divergence-axis probes); all other",
        "inputs are consistency-corpus cases.",
        "",
        "Calibrated against the oracle versions pinned in `constraints/ci.txt`:",
        _oracle_pins_line(),
        "",
        "**Known witnessing gap** (ARCHITECTURE.md §8.2/§15): Java cyclomatic",
        "is witnessed by lizard only, and Java cognitive complexity has NO",
        "external oracle. PMD and rust-code-analysis are staged, not yet",
        "wired. Until then, Java counting rests on the hand-computed corpus",
        "and the spec alone.",
        "",
    ]
    by_oracle: dict[str, list[dict]] = {}
    for e in entries:
        by_oracle.setdefault(e["oracle"], []).append(e)
    for oracle in sorted(by_oracle):
        lines += [
            f"## {oracle}",
            "",
            "| case | unit | metric | ours | theirs | ruling | why |",
            "| --- | --- | --- | ---: | ---: | --- | --- |",
        ]
        for e in sorted(by_oracle[oracle], key=lambda e: (e["case"], e["unit"], e["metric"])):
            lines.append(
                f"| `{e['case']}` | `{e['unit']}` | {e['metric']} | {e['ours']} | "
                f"{e['theirs']} | `{e['ruling']}` | {e['reason']} |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
