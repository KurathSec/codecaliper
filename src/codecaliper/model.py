"""Result data model.

All result types are frozen, slotted dataclasses: immutable, clock-free (no
timestamps anywhere, so outputs are byte-reproducible per platform,
CORE-ALL-0004), with a stable field order that canonical.py serializes
deterministically.

Honesty is encoded in the types themselves: MI carries a typed ``derived_from`` and a
standing ``mi-contains-cc`` diagnostic; every Halstead value carries
``halstead-approximation``; readability results carry ``extrapolated`` as a field;
there is deliberately no score field anywhere (ARCHITECTURE.md §13).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Granularity = Literal["snippet", "function", "file"]
Severity = Literal["info", "warning", "error"]

#: Closed set of diagnostic codes (ARCHITECTURE.md §2).
DIAGNOSTIC_CODES = frozenset(
    {
        "parse-error-recovered",
        "unvalidated-grammar",
        "granularity-extrapolated",
        "snippet-out-of-calibrated-range",
        "snippet-scaffolded",
        "bw-lexical-fallback",
        "mi-contains-cc",
        "halstead-approximation",
        "encoding-replaced",
        "bom-stripped",
    }
)


@dataclass(frozen=True, slots=True)
class Span:
    """1-based line numbers, 0-based columns (editor convention)."""

    start_line: int
    start_col: int
    end_line: int
    end_col: int


@dataclass(frozen=True, slots=True)
class GrammarInfo:
    language: str  # "python"
    package: str  # "tree-sitter-python"
    version: str  # actually-installed version (importlib.metadata)
    abi_version: int  # tree-sitter Language ABI
    validated: bool  # matches spec/validated_grammars.toml? Run and label, never refuse.


@dataclass(frozen=True, slots=True)
class Provenance:
    tool_version: str
    spec_version: str  # on EVERY report: the instrument's calibration stamp
    language: str
    grammar: GrammarInfo
    modes: tuple[tuple[str, str], ...]  # (("cognitive", "whitepaper"),); sorted, hashable
    rulings_applied: tuple[str, ...]  # sorted, deduped IDs governing the emitted values


@dataclass(frozen=True, slots=True)
class Diagnostic:
    severity: Severity
    code: str  # member of DIAGNOSTIC_CODES
    message: str
    span: Span | None = None
    ruling: str | None = None  # the ruling governing this behaviour, if any


@dataclass(frozen=True, slots=True)
class RulingTrace:
    """Per-increment attribution, populated only with explain=True (zero default cost)."""

    ruling_id: str
    span: Span
    delta: float


@dataclass(frozen=True, slots=True)
class MetricValue:
    metric: str  # "cyclomatic", "halstead.volume", ...
    value: int | float
    rulings: tuple[str, ...] = ()  # ruling IDs governing this metric for this language
    derived_from: tuple[str, ...] = ()  # MI: ("halstead.volume", "cyclomatic", "sloc")
    trace: tuple[RulingTrace, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True, slots=True)
class FeatureVectorResult:
    """A raw feature vector, never a score (ARCHITECTURE.md §7/§13)."""

    feature_set: str  # "bw2010"
    granularity: Granularity
    native_granularity: Granularity  # "snippet" for bw2010
    extrapolated: bool  # granularity != native_granularity
    names: tuple[str, ...]  # canonical order (bw2010: Fig. 6 order from the reference)
    values: tuple[float, ...]
    rulings: tuple[str, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    unit_name: str | None = None  # function name when granularity == "function"
    span: Span | None = None


@dataclass(frozen=True, slots=True)
class FunctionReport:
    name: str
    qualified_name: str
    span: Span
    metrics: tuple[MetricValue, ...] = ()


@dataclass(frozen=True, slots=True)
class FileReport:
    path: str | None  # None for in-memory measure()
    parse_ok: bool  # False if the tree contains ERROR/MISSING nodes (CORE-ALL-0002)
    file_metrics: tuple[MetricValue, ...] = ()
    functions: tuple[FunctionReport, ...] = ()
    readability: tuple[FeatureVectorResult, ...] = ()  # plural: feature SETS, not scores
    diagnostics: tuple[Diagnostic, ...] = ()
    provenance: Provenance | None = None


def metric_map(values: tuple[MetricValue, ...]) -> dict[str, MetricValue]:
    """Convenience view keyed by metric name (stable insertion order preserved)."""
    return {v.metric: v for v in values}
