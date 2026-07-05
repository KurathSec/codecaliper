"""Shared engine for the differential oracle lane.

Inputs are (a) every consistency-corpus case the reference lanes can compare
(``conftest.is_reference_comparable`` — normalization edge cases and parse
errors are OUR policy surface, not the oracles'), (b) the BW-fidelity EXTRA
snippets, and (c) the divergence-axis probe snippets below, which exercise the
counting decisions where our rulings knowingly differ from at least one
oracle.

Two-sided honesty (ARCHITECTURE.md §3.4):

- an observed divergence with no ``divergences.toml`` entry FAILS, printing a
  ready-to-paste TOML stanza;
- a table entry that is no longer observed FAILS as stale;
- a missing oracle SKIPs with a precise reason (probe pattern inherited from
  Spaghetti Architect's ``bench/anchor.py``), never fails a local build. SKIP
  alone cannot mask a regression in CI: the ``differential`` job installs the
  ``oracles`` extra AND hard-imports every oracle module before pytest runs,
  so an oracle that installs-but-cannot-import fails the job instead of
  silently skipping every comparison.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import cache, lru_cache
from pathlib import Path

import pytest
from conftest import case_source, corpus_cases, is_reference_comparable
from test_bw_port_fidelity import EXTRA_SNIPPETS

from codecaliper import measure
from codecaliper.model import metric_map

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
TABLE_PATH = HERE / "divergences.toml"

ORACLES = ("radon", "lizard", "cognitive_complexity")
METRICS = ("cyclomatic", "cognitive")

# --- divergence-axis probe snippets -----------------------------------------
# Minimal named functions around the ruled counting decisions. Agreement is as
# valuable a witness as divergence: a probe with no table entry asserts the
# oracle CONCURS (e.g. radon and lizard both count ternaries, CC-PY-0007).
PY_PROBES = {
    "diff-ternary": "def pick(a, b, flag):\n    return a if flag else b\n",
    # CC-PY-0004: guards count, iteration clauses do not.
    "diff-comp-guard": "def evens(xs):\n    return [x for x in xs if x % 2 == 0]\n",
    # CC-PY-0003 / COG-ALL-0003: per-operator vs per-sequence boolop counting.
    "diff-boolop-chain": (
        "def allow(a, b, c, d):\n"
        "    if a and b and c or d:\n"
        "        return 1\n"
        "    return 0\n"
    ),
    # CC-PY-0008 / COG-ALL-0001: case arms count, the bare wildcard does not.
    "diff-match-in-func": (
        "def dispatch(cmd):\n"
        "    match cmd:\n"
        "        case 'go':\n"
        "            return 1\n"
        "        case 'stop':\n"
        "            return 2\n"
        "        case _:\n"
        "            return 0\n"
    ),
    # CC-PY-0005 / COG-ALL-0002: a loop's completion `else` is not a branch.
    "diff-while-else": (
        "def scan(xs):\n"
        "    while xs:\n"
        "        xs.pop()\n"
        "    else:\n"
        "        return -1\n"
        "    return 0\n"
    ),
    # CORE-ALL-0003: lambdas stay part of the enclosing unit (both lanes agree).
    "diff-lambda-ternary": "def make(flag):\n    return lambda v: v if flag else -v\n",
}
JAVA_PROBES = {
    # CC-JAVA-0006: case labels count, `default` does not (lizard concurs).
    "diff-java-switch": (
        "class Sw {\n"
        "    int pick(int x) {\n"
        "        switch (x) {\n"
        "            case 1: return 10;\n"
        "            case 2: return 20;\n"
        "            default: return 0;\n"
        "        }\n"
        "    }\n"
        "}\n"
    ),
    # CC-JAVA-0002 ternary; CC-JAVA-0004 do-while.
    "diff-java-ternary": "class T {\n    int sign(int a) { return a > 0 ? 1 : -1; }\n}\n",
    "diff-java-do-while": (
        "class D {\n"
        "    int spin(int n) {\n"
        "        do { n--; } while (n > 0);\n"
        "        return n;\n"
        "    }\n"
        "}\n"
    ),
}


def probe_oracle(module_name: str, dist_name: str) -> str | None:
    """Return a skip reason when the oracle is unavailable, else None
    (honest-SKIP probe, anchor.py style — absence never fails locally)."""
    try:
        importlib.import_module(module_name)
    except ImportError as exc:
        return (
            f"differential oracle {dist_name!r} is not installed ({exc}); "
            f"install it with: pip install -e '.[oracles]'"
        )
    return None


@cache
def inputs(language: str) -> dict[str, str]:
    """label -> source. Corpus labels are case IDs; snippets are 'snippet:<name>'."""
    out: dict[str, str] = {}
    for case in corpus_cases():
        if case["language"] != language or not is_reference_comparable(case):
            continue
        src = case_source(case)
        assert isinstance(src, str)  # byte-policy cases are not reference-comparable
        out[case["id"]] = src
    snippets = dict(EXTRA_SNIPPETS, **PY_PROBES) if language == "python" else JAVA_PROBES
    for name, src in snippets.items():
        out[f"snippet:{name}"] = src
    return out


def all_labels() -> set[str]:
    return set(inputs("python")) | set(inputs("java"))


# --- comparison records -------------------------------------------------------


@dataclass(frozen=True)
class Comparison:
    oracle: str
    case: str  # corpus case ID or 'snippet:<name>'
    unit: str  # OUR qualified function name
    metric: str
    ours: int
    theirs: int

    @property
    def diverges(self) -> bool:
        return self.ours != self.theirs

    @property
    def fingerprint(self) -> tuple[str, str, str, str, int, int]:
        return (self.oracle, self.case, self.unit, self.metric, self.ours, self.theirs)


@dataclass(frozen=True)
class TableEntry:
    oracle: str
    case: str
    unit: str
    metric: str
    ours: int
    theirs: int
    ruling: str
    reason: str

    @property
    def fingerprint(self) -> tuple[str, str, str, str, int, int]:
        return (self.oracle, self.case, self.unit, self.metric, self.ours, self.theirs)


@lru_cache(maxsize=1)
def load_table() -> tuple[TableEntry, ...]:
    with TABLE_PATH.open("rb") as f:
        data = tomllib.load(f)
    return tuple(
        TableEntry(
            oracle=raw["oracle"],
            case=raw["case"],
            unit=raw["unit"],
            metric=raw["metric"],
            ours=int(raw["ours"]),
            theirs=int(raw["theirs"]),
            ruling=raw["ruling"],
            reason=raw["reason"],
        )
        for raw in data.get("divergence", [])
    )


# --- our side -----------------------------------------------------------------


def our_functions(source: str, language: str, metric: str) -> dict[str, tuple[str, int]]:
    """simple name -> (qualified name, per-function value).

    Cognitive values run in sonar-compat mode — the oracle under comparison
    (cognitive_complexity) is a Sonar-lineage implementation.
    """
    rep = measure(
        source,
        language=language,
        metrics=(metric,),
        readability=(),
        cognitive_mode="sonar-compat",
    )
    out: dict[str, tuple[str, int]] = {}
    for fn in rep.functions:
        if fn.name in out:
            raise AssertionError(
                f"duplicate function name {fn.name!r} in a differential input; "
                "name-based unit matching requires unique names per input"
            )
        out[fn.name] = (fn.qualified_name, int(metric_map(fn.metrics)[metric].value))
    return out


# --- oracle sides (lazy imports; callers sit behind a probe skip) --------------


def radon_functions(source: str) -> list[tuple[str, int]]:
    """(name, cyclomatic) for every named function radon reports.

    radon lists methods both at top level and under their Class block, so
    blocks are deduped by (name, lineno); closures are recursed.
    """
    from radon.complexity import cc_visit
    from radon.visitors import Class, Function

    out: list[tuple[str, int]] = []
    seen: set[tuple[str, int]] = set()

    def visit(blocks: Iterable[object]) -> None:
        for b in blocks:
            if isinstance(b, Function):
                key = (b.name, b.lineno)
                if key in seen:
                    continue
                seen.add(key)
                out.append((b.name, int(b.complexity)))
                visit(b.closures)
            elif isinstance(b, Class):
                visit(b.methods)

    visit(cc_visit(source))
    return out


def lizard_functions(source: str, ext: str) -> list[tuple[str, int]]:
    """(name, CCN) per function; 'Cls::m' (java) / 'outer.inner' (python)
    are reduced to the simple name for cross-oracle unit matching."""
    import lizard

    info = lizard.analyze_file.analyze_source_code(f"input.{ext}", source)
    return [
        (f.name.replace("::", ".").rsplit(".", 1)[-1], int(f.cyclomatic_complexity))
        for f in info.function_list
    ]


def cognitive_complexity_functions(source: str) -> list[tuple[str, int]]:
    """(name, cognitive) per (async) def, via the oracle's public API."""
    import ast

    from cognitive_complexity.api import get_cognitive_complexity

    return [
        (node.name, int(get_cognitive_complexity(node)))
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


# --- pairing and collection -----------------------------------------------------


def pair(
    oracle: str,
    label: str,
    metric: str,
    ours: dict[str, tuple[str, int]],
    theirs: Sequence[tuple[str, int]],
) -> tuple[Comparison, ...]:
    theirs_map: dict[str, int] = {}
    for name, value in theirs:
        if name in theirs_map:
            raise AssertionError(
                f"{oracle} on {label}: duplicate function name {name!r} from the oracle; "
                "name-based unit matching requires unique names per input"
            )
        theirs_map[name] = value
    if set(ours) != set(theirs_map):
        raise AssertionError(
            f"{oracle} on {label}: function unit sets differ — "
            f"only ours: {sorted(set(ours) - set(theirs_map))}, "
            f"only oracle: {sorted(set(theirs_map) - set(ours))} "
            "(a unit-scope mismatch is a harness or scope bug, not a value divergence)"
        )
    return tuple(
        Comparison(oracle, label, ours[name][0], metric, ours[name][1], theirs_map[name])
        for name in sorted(ours)
    )


@cache
def comparisons(oracle: str, label: str) -> tuple[Comparison, ...]:
    """All per-function comparisons for one oracle on one input."""
    if oracle == "radon":
        src = inputs("python")[label]
        return pair(oracle, label, "cyclomatic",
                    our_functions(src, "python", "cyclomatic"), radon_functions(src))
    if oracle == "cognitive_complexity":
        src = inputs("python")[label]
        return pair(oracle, label, "cognitive",
                    our_functions(src, "python", "cognitive"),
                    cognitive_complexity_functions(src))
    if oracle == "lizard":
        language = "python" if label in inputs("python") else "java"
        src = inputs(language)[label]
        ext = "py" if language == "python" else "java"
        return pair(oracle, label, "cyclomatic",
                    our_functions(src, language, "cyclomatic"),
                    lizard_functions(src, ext))
    raise ValueError(f"unknown oracle {oracle!r}")


# --- assertions (both directions of table completeness) --------------------------


def toml_stanza(c: Comparison) -> str:
    return (
        "[[divergence]]\n"
        f'oracle = "{c.oracle}"\n'
        f'case = "{c.case}"\n'
        f'unit = "{c.unit}"\n'
        f'metric = "{c.metric}"\n'
        f"ours = {c.ours}\n"
        f"theirs = {c.theirs}\n"
        'ruling = ""  # the codecaliper ruling ID that pins our behaviour\n'
        'reason = ""  # one sentence: why the oracle counts differently\n'
    )


def assert_classified(comps: Iterable[Comparison]) -> None:
    table = {e.fingerprint for e in load_table()}
    unclassified = [c for c in comps if c.diverges and c.fingerprint not in table]
    if unclassified:
        stanzas = "\n".join(toml_stanza(c) for c in unclassified)
        pytest.fail(
            "UNCLASSIFIED divergence(s) from an external oracle. Either fix the "
            "bug, or classify each one against a real ruling by appending to "
            "tests/differential/divergences.toml and regenerating the docs "
            "(python tools/gen_divergences.py):\n\n" + stanzas
        )


def assert_no_stale(oracle: str, comps: Iterable[Comparison]) -> None:
    observed = {c.fingerprint for c in comps if c.diverges}
    stale = [e for e in load_table() if e.oracle == oracle and e.fingerprint not in observed]
    if stale:
        listing = "\n".join(
            f"  {e.oracle} / {e.case} / {e.unit} / {e.metric}: ours={e.ours} theirs={e.theirs}"
            for e in stale
        )
        pytest.fail(
            "STALE entr(y|ies) in tests/differential/divergences.toml — no longer "
            "observed against the installed oracle (values changed, or the input "
            "disappeared); remove or re-triage, then regenerate the docs:\n" + listing
        )
