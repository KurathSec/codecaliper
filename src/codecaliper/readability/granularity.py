"""Granularity segmentation and extrapolation labelling (BW-ALL-0002), plus the
Java bare-snippet scaffold (CORE-JAVA-0001)."""

from __future__ import annotations

from codecaliper.languages.base import FunctionUnit, LanguageAdapter
from codecaliper.model import Diagnostic, FeatureVectorResult, Granularity, Span
from codecaliper.readability.bw2010 import (
    BW_FEATURE_NAMES,
    BW_RULINGS,
    CALIBRATED_LINE_RANGE,
    bw_features,
)
from codecaliper.syntax.tokens import LexicalToken

JAVA_SNIPPET_PREFIX = "class __CC__ {\nvoid __cc__() {\n"
JAVA_SNIPPET_SUFFIX = "\n}\n}\n"
JAVA_SNIPPET_LINE_OFFSET = 2  # lines prepended by the class+method scaffold

# Class-body-only scaffold: rescues member-level snippets (constructors,
# modifier-bearing methods) that a method body cannot contain (CORE-JAVA-0001).
JAVA_CLASS_PREFIX = "class __CC__ {\n"
JAVA_CLASS_SUFFIX = "\n}\n"
JAVA_CLASS_LINE_OFFSET = 1


def rebase_unit(unit: FunctionUnit, line_offset: int, n_lines: int) -> FunctionUnit:
    """Shift a FunctionUnit's span from scaffold to original snippet coordinates,
    and strip the synthetic scaffold qualifiers from qualified_name — scaffold
    artifacts must never leak into emitted output (CORE-JAVA-0001). Longest
    prefix first: the class+method scaffold nests units under __CC__.__cc__."""
    qualified = unit.qualified_name
    for scaffold_prefix in ("__CC__.__cc__.", "__CC__."):
        if qualified.startswith(scaffold_prefix):
            qualified = qualified[len(scaffold_prefix):]
            break
    s = unit.span
    return FunctionUnit(
        unit.name,
        qualified,
        unit.node,
        Span(
            start_line=s.start_line - line_offset,
            start_col=s.start_col,
            end_line=min(s.end_line - line_offset, n_lines),
            end_col=s.end_col,
        ),
    )


def rebase_tokens(
    tokens: list[LexicalToken], start_line: int, end_line: int
) -> list[LexicalToken]:
    """Tokens whose start lies in [start_line, end_line], rebased to 1-based."""
    offset = start_line - 1
    return [
        LexicalToken(t.kind, t.text, t.line - offset, min(t.end_line, end_line) - offset)
        for t in tokens
        if start_line <= t.line <= end_line
    ]


def vector(
    lines: list[str],
    tokens: list[LexicalToken],
    adapter: LanguageAdapter,
    granularity: Granularity,
    *,
    unit_name: str | None = None,
    span: Span | None = None,
    scaffolded: bool = False,
) -> FeatureVectorResult:
    features = bw_features(lines, tokens, adapter)
    diags: list[Diagnostic] = []
    extrapolated = granularity != "snippet"
    if extrapolated:
        diags.append(
            Diagnostic(
                "warning", "granularity-extrapolated",
                f"bw2010 is calibrated on snippets; {granularity}-level vectors are "
                "extrapolation beyond the model's native unit (BW-ALL-0002)",
                ruling="BW-ALL-0002",
            )
        )
    lo, hi = CALIBRATED_LINE_RANGE
    if granularity == "snippet" and not (lo <= len(lines) <= hi):
        diags.append(
            Diagnostic(
                "info", "snippet-out-of-calibrated-range",
                f"snippet is {len(lines)} lines; the bw2010 calibrated regime is "
                f"{lo}-{hi} lines (BW-ALL-0002)",
                ruling="BW-ALL-0002",
            )
        )
    if scaffolded:
        diags.append(
            Diagnostic(
                "info", "snippet-scaffolded",
                "bare Java snippet was parsed inside a synthetic class/method "
                "scaffold; features computed over the original lines only "
                "(CORE-JAVA-0001)",
                ruling="CORE-JAVA-0001",
            )
        )
    return FeatureVectorResult(
        feature_set="bw2010",
        granularity=granularity,
        native_granularity="snippet",
        extrapolated=extrapolated,
        names=BW_FEATURE_NAMES,
        values=tuple(features[n] for n in BW_FEATURE_NAMES),
        rulings=BW_RULINGS,
        diagnostics=tuple(diags),
        unit_name=unit_name,
        span=span,
    )


def function_vectors(
    lines: list[str],
    tokens: list[LexicalToken],
    adapter: LanguageAdapter,
    units: list[FunctionUnit],
) -> list[FeatureVectorResult]:
    out = []
    for unit in units:
        s, e = unit.span.start_line, unit.span.end_line
        out.append(
            vector(
                lines[s - 1 : e],
                rebase_tokens(tokens, s, e),
                adapter,
                "function",
                unit_name=unit.qualified_name,
                span=unit.span,
            )
        )
    return out
