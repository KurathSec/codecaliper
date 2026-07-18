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
PMD_PIN = ROOT / "tests" / "differential" / "pmd.toml"
_ORACLES = ("radon", "lizard", "cognitive-complexity")


def _oracle_pins_line() -> str:
    """The pinned oracle versions, read from constraints/ci.txt and (for PMD,
    which is a JVM tool and so outside the pip closure) tests/differential/pmd.toml,
    so the doc can never drift from the calibration sources of truth."""
    pins = []
    for line in CONSTRAINTS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        name = line.split("==")[0].strip().lower()
        if "==" in line and not line.startswith("#") and name in _ORACLES:
            pins.append(f"`{line}`")
    with PMD_PIN.open("rb") as f:
        pins.append(f"`pmd=={tomllib.load(f)['pmd']['version']}`")
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
        "Calibrated against the oracle versions pinned in `constraints/ci.txt`",
        "and, for PMD (a JVM tool, so outside the pip closure),",
        "`tests/differential/pmd.toml`:",
        _oracle_pins_line(),
        "",
        "**What is witnessed, and where the witnessing runs out**",
        "(ARCHITECTURE.md §8.2/§15). Java is witnessed by lizard (cyclomatic)",
        "and by PMD (cyclomatic and cognitive). PMD is independent of",
        "tree-sitter all the way down, with its own Java grammar and its own",
        "metric visitors, so agreement with it is not two wrappers around one",
        "parser agreeing with themselves. One gap survives: on the single axis",
        "where the two cognitive modes differ, the recursion increment, PMD",
        "takes the whitepaper's +1, so on `snippet:diff-java-recursion` it",
        "witnesses *whitepaper* mode rather than the `sonar-compat` mode these",
        "comparisons run in. Java's sonar-compat recursion behaviour therefore",
        "has no external witness, and rests on the hand-computed corpus and the",
        "spec alone. Go is witnessed by lizard (cyclomatic), which concurs on",
        "every Go input, which is why no Go entry appears in the tables below;",
        "Go cognitive has no external witness at all and rests on the",
        "hand-computed corpus and the spec. rust-code-analysis remains staged,",
        "not wired.",
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
