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
from codecaliper.spec import require
from codecaliper.syntax.tokens import LexicalToken, lang_tokenization_rulings

R_TOK_LINE = require("TOK-ALL-0005")  # token line attribution
R_TOK_TAB = require("TOK-ALL-0006")   # tab = 8 indentation characters

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


def _bw_vector_rulings(
    adapter: LanguageAdapter, lexical_fallback: bool, cond_rulings: tuple[str, ...]
) -> tuple[str, ...]:
    """The governing set for an emitted BW vector: the six BW-ALL requires,
    the language-specific bw2010 rulings (keyword/branch-keyword delimitation),
    and the tokenization rulings that shape the features (TOK-ALL-0005 line
    attribution, TOK-ALL-0006 tab=8 indentation, the language's static
    atomic-string rulings). ``cond_rulings`` are the construct-specific
    tokenization rulings (TOK-ALL-0007 anonymous words, TOK-JAVA-0002 `_`) that
    actually engaged inside THIS vector's line span; BW-ALL-0007 stays strictly
    conditional on the lexical fallback actually engaging."""
    from codecaliper.spec import iter_rulings

    lang_specific = tuple(sorted(
        r.id
        for r in iter_rulings(metric="bw2010", language=adapter.name)
        if r.id not in BW_RULINGS and r.id != "BW-ALL-0007"
    ))
    return (
        BW_RULINGS
        + lang_specific
        + (R_TOK_LINE, R_TOK_TAB)
        + lang_tokenization_rulings(adapter)
        + tuple(sorted(cond_rulings))
        + (("BW-ALL-0007",) if lexical_fallback else ())
    )


def vector(
    lines: list[str],
    tokens: list[LexicalToken],
    adapter: LanguageAdapter,
    granularity: Granularity,
    *,
    unit_name: str | None = None,
    span: Span | None = None,
    scaffolded: bool = False,
    lexical_fallback: bool = False,
    cond_rulings: tuple[str, ...] = (),
) -> FeatureVectorResult:
    features = bw_features(lines, tokens, adapter)
    diags: list[Diagnostic] = []
    if lexical_fallback:
        diags.append(
            Diagnostic(
                "info", "bw-lexical-fallback",
                "parse errors present; token-family features computed over the "
                "full lexical stream, ERROR regions included — the BW construct "
                "is lexical (BW-ALL-0007). CORE-ALL-0002 still governs every "
                "metric.",
                ruling="BW-ALL-0007",
            )
        )
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
        rulings=_bw_vector_rulings(adapter, lexical_fallback, cond_rulings),
        diagnostics=tuple(diags),
        unit_name=unit_name,
        span=span,
    )


def cond_in_range(cond_lines: dict[str, set[int]], lo: int, hi: int) -> tuple[str, ...]:
    """Conditional tokenization rulings that engaged on a line within [lo, hi]."""
    return tuple(sorted(
        rid for rid, lns in cond_lines.items() if any(lo <= ln <= hi for ln in lns)
    ))


def function_vectors(
    lines: list[str],
    tokens: list[LexicalToken],
    adapter: LanguageAdapter,
    units: list[FunctionUnit],
    opaque_tokens: list[LexicalToken] | None = None,
    cond_opaque: dict[str, set[int]] | None = None,
    cond_full: dict[str, set[int]] | None = None,
) -> list[FeatureVectorResult]:
    """Per-unit vectors. ``opaque_tokens`` is the error-opaque stream, passed
    only when the file-level BW lexical fallback engaged (BW-ALL-0007): a
    unit's vector is flagged only when its OWN span gained ERROR-region tokens
    — the opaque stream is a subsequence of the full one, so equal slice
    lengths imply identical slices. ``cond_opaque``/``cond_full`` map each
    conditional tokenization ruling to the lines it engaged on in the
    respective stream; a unit cites one only when it engaged inside the unit's
    OWN span (in the stream that unit actually used)."""
    out = []
    for unit in units:
        s, e = unit.span.start_line, unit.span.end_line
        unit_tokens = rebase_tokens(tokens, s, e)
        unit_fallback = (
            opaque_tokens is not None
            and len(unit_tokens) != len(rebase_tokens(opaque_tokens, s, e))
        )
        cond_src = cond_full if unit_fallback else cond_opaque
        cond_rulings = cond_in_range(cond_src, s, e) if cond_src is not None else ()
        out.append(
            vector(
                lines[s - 1 : e],
                unit_tokens,
                adapter,
                "function",
                unit_name=unit.qualified_name,
                span=unit.span,
                lexical_fallback=unit_fallback,
                cond_rulings=cond_rulings,
            )
        )
    return out
