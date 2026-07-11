"""The typed public facade: measure() / measure_file() / Session."""

from __future__ import annotations

import os
from collections.abc import Collection
from typing import Literal

from codecaliper._version import __version__
from codecaliper.errors import CodecaliperError, StrictParseError
from codecaliper.languages import detect_language, get_adapter
from codecaliper.languages.base import LanguageAdapter
from codecaliper.metrics import cognitive as cog_mod
from codecaliper.metrics import cyclomatic as cc_mod
from codecaliper.metrics import halstead as hal_mod
from codecaliper.metrics import loc as loc_mod
from codecaliper.metrics import mi as mi_mod
from codecaliper.metrics.base import MetricContext
from codecaliper.model import (
    Diagnostic,
    FileReport,
    FunctionReport,
    Granularity,
    MetricValue,
    Provenance,
)
from codecaliper.readability import granularity as gran_mod
from codecaliper.spec import spec_version
from codecaliper.syntax import _treesitter as ts
from codecaliper.syntax import tokens as tok_mod

DEFAULT_METRICS = ("cyclomatic", "cognitive", "halstead", "maintainability_index", "loc")
_FEATURE_SETS = ("bw2010",)
_GRANULARITIES = ("snippet", "function", "file")
_COGNITIVE_MODES = ("whitepaper", "sonar-compat")

CognitiveMode = Literal["whitepaper", "sonar-compat"]


class Session:
    """Caches adapters/parsers — the corpus-scale entry point (deterministic
    sequential order; parallelism is a 1.x item)."""

    def __init__(
        self,
        *,
        metrics: Collection[str] | None = None,
        readability: Collection[str] = ("bw2010",),
        granularity: Granularity = "file",
        cognitive_mode: CognitiveMode = "whitepaper",
        explain: bool = False,
        strict: bool = False,
    ) -> None:
        self.metrics = tuple(metrics) if metrics is not None else DEFAULT_METRICS
        unknown = [m for m in self.metrics if m not in DEFAULT_METRICS]
        if unknown:
            raise CodecaliperError(
                f"unknown metric(s) {unknown!r}; available: {', '.join(DEFAULT_METRICS)}"
            )
        self.readability = tuple(readability)
        unknown_fs = [f for f in self.readability if f not in _FEATURE_SETS]
        if unknown_fs:
            raise CodecaliperError(
                f"unknown readability feature set(s) {unknown_fs!r}; "
                f"available: {', '.join(_FEATURE_SETS)}"
            )
        # Literal types only protect type-checked callers; an invalid mode
        # would otherwise silently measure as sonar-compat and stamp an
        # internally inconsistent provenance.
        if granularity not in _GRANULARITIES:
            raise CodecaliperError(
                f"unknown granularity {granularity!r}; "
                f"available: {', '.join(_GRANULARITIES)}"
            )
        if cognitive_mode not in _COGNITIVE_MODES:
            raise CodecaliperError(
                f"unknown cognitive mode {cognitive_mode!r}; "
                f"available: {', '.join(_COGNITIVE_MODES)}"
            )
        self.granularity: Granularity = granularity
        self.cognitive_mode: CognitiveMode = cognitive_mode
        self.explain = explain
        self.strict = strict

    def measure(
        self, source: str | bytes, *, language: str, path: str | None = None
    ) -> FileReport:
        return _measure(
            source,
            adapter=get_adapter(language),
            path=path,
            metrics=self.metrics,
            readability=self.readability,
            granularity=self.granularity,
            cognitive_mode=self.cognitive_mode,
            explain=self.explain,
            strict=self.strict,
        )

    def measure_file(self, path: str | os.PathLike[str], *, language: str | None = None) -> FileReport:
        p = os.fspath(path)
        lang = language if language is not None else detect_language(p)
        with open(p, "rb") as f:
            data = f.read()
        return self.measure(data, language=lang, path=p)


def measure(
    source: str | bytes,
    *,
    language: str,
    metrics: Collection[str] | None = None,
    readability: Collection[str] = ("bw2010",),
    granularity: Granularity = "file",
    cognitive_mode: CognitiveMode = "whitepaper",
    explain: bool = False,
    strict: bool = False,
) -> FileReport:
    return Session(
        metrics=metrics,
        readability=readability,
        granularity=granularity,
        cognitive_mode=cognitive_mode,
        explain=explain,
        strict=strict,
    ).measure(source, language=language)


def measure_file(
    path: str | os.PathLike[str], *, language: str | None = None, **kwargs: object
) -> FileReport:
    return Session(**kwargs).measure_file(path, language=language)  # type: ignore[arg-type]


def _measure(
    source: str | bytes,
    *,
    adapter: LanguageAdapter,
    path: str | None,
    metrics: tuple[str, ...],
    readability: tuple[str, ...],
    granularity: Granularity,
    cognitive_mode: CognitiveMode,
    explain: bool,
    strict: bool,
) -> FileReport:
    text, diags = tok_mod.normalize(source)
    diagnostics = list(diags)
    lines = tok_mod.source_lines(text)

    # --- parse (with the Java bare-snippet scaffold when needed, CORE-JAVA-0001)
    scaffolded = False
    line_offset = 0
    line_range: tuple[int, int] | None = None
    source_bytes = text.encode("utf-8")
    tree = adapter.parse(source_bytes)
    n_errors = ts.count_error_nodes(tree)
    if n_errors and granularity == "snippet" and adapter.name == "java":
        # Two candidates: class-body-only (rescues constructors/modifier-bearing
        # members) and class+method (statement fragments). Adopt the strict
        # error-count minimizer (CORE-JAVA-0001).
        best = None
        for prefix, suffix, offset in (
            (gran_mod.JAVA_CLASS_PREFIX, gran_mod.JAVA_CLASS_SUFFIX,
             gran_mod.JAVA_CLASS_LINE_OFFSET),
            (gran_mod.JAVA_SNIPPET_PREFIX, gran_mod.JAVA_SNIPPET_SUFFIX,
             gran_mod.JAVA_SNIPPET_LINE_OFFSET),
        ):
            wrapped_bytes = (prefix + text + suffix).encode("utf-8")
            wrapped_tree = adapter.parse(wrapped_bytes)
            errs = ts.count_error_nodes(wrapped_tree)
            if best is None or errs < best[0]:
                best = (errs, wrapped_bytes, wrapped_tree, offset)
        if best is not None and best[0] < n_errors:
            scaffolded = True
            _, source_bytes, tree, line_offset = best
            n_errors = best[0]
            line_range = (line_offset + 1, line_offset + len(lines))
            # CORE-JAVA-0001 promises a report-level trace: every metric below
            # was computed from the synthetically scaffolded parse, so the
            # diagnostic must survive a metrics-only run (readability=()).
            diagnostics.append(
                Diagnostic(
                    "info", "snippet-scaffolded",
                    "bare Java snippet parsed inside a synthetic scaffold; all "
                    "values computed over the original snippet lines only "
                    "(CORE-JAVA-0001)",
                    ruling="CORE-JAVA-0001",
                )
            )

    parse_ok = n_errors == 0
    if not parse_ok:
        if strict:
            raise StrictParseError(
                f"{path or '<source>'}: parse tree contains {n_errors} ERROR/MISSING node(s)"
            )
        diagnostics.append(
            Diagnostic(
                "warning", "parse-error-recovered",
                f"parse tree contains {n_errors} ERROR/MISSING node(s); measured "
                "anyway with error subtrees opaque (CORE-ALL-0002)",
                ruling="CORE-ALL-0002",
            )
        )

    domain = (1, max(len(lines), 1))  # emitted traces may not point outside it
    ctx = MetricContext(
        cognitive_mode=cognitive_mode, explain=explain,
        line_range=line_range, line_offset=line_offset, domain=domain,
    )
    # TOK-ALL-0003 attaches no diagnostic by design, so its firing is detected
    # from the raw input directly (every diagnostic-cited ruling is harvested
    # into rulings_applied just before Provenance is built).
    had_cr = b"\r" in source if isinstance(source, bytes) else "\r" in source
    if had_cr:
        ctx.fired.add("TOK-ALL-0003")
    # cond_opaque/cond_full record, per conditional tokenization ruling, the
    # physical lines it engaged on in the error-opaque (metrics) stream and the
    # ERROR-inclusive (BW fallback) stream respectively, so each value cites
    # them only over the span it was actually computed on.
    cond_opaque: dict[str, set[int]] = {}
    all_tokens = tok_mod.lex(tree, source_bytes, adapter, cond_lines=cond_opaque)
    if line_range is not None:
        tokens = gran_mod.rebase_tokens(all_tokens, line_range[0], line_range[1])
    else:
        tokens = all_tokens
    # The language's static atomic-string rulings govern every token-derived
    # value; construct-specific classification rulings (TOK-ALL-0007,
    # TOK-JAVA-0002) are cited only over ranges where they actually engaged.
    tok_lang_rulings = tok_mod.lang_tokenization_rulings(adapter)
    measured_lo, measured_hi = line_range if line_range is not None else domain
    file_cond = gran_mod.cond_in_range(cond_opaque, measured_lo, measured_hi)

    # --- file-level metrics. cc/loc are also MI inputs; when their own metric
    # is not requested they are computed under a SCRATCH context so
    # rulings_applied reports only rulings backing EMITTED values.
    file_metrics: list[MetricValue] = []
    root = tree.root_node

    def _scratch() -> MetricContext:
        return MetricContext(cognitive_mode=cognitive_mode, line_range=line_range,
                             line_offset=line_offset, domain=domain)

    need_cc = "cyclomatic" in metrics or "maintainability_index" in metrics
    need_loc = "loc" in metrics or "maintainability_index" in metrics
    cc_value = 0
    if need_cc:
        cc_value = cc_mod.cyclomatic(
            root, adapter, ctx if "cyclomatic" in metrics else _scratch()
        )
    loc_values: dict[str, int] = {}
    if need_loc:
        loc_values = loc_mod.loc_metrics(
            lines, tokens, root, adapter, ctx if "loc" in metrics else _scratch()
        )
    if "cyclomatic" in metrics:
        file_metrics.append(
            MetricValue("cyclomatic", cc_value, rulings=_cc_rulings(adapter),
                        trace=ctx.trace_for("cyclomatic"))
        )
    if "cognitive" in metrics:
        cog_value = cog_mod.cognitive(root, adapter, ctx)
        file_metrics.append(
            MetricValue("cognitive", cog_value,
                        rulings=_cog_rulings(adapter, cognitive_mode),
                        trace=ctx.trace_for("cognitive"))
        )
    hal_values: dict[str, float] = {}
    if "halstead" in metrics or "maintainability_index" in metrics:
        hal_values = hal_mod.halstead(tokens)
    if "halstead" in metrics:
        # atomicity + word-token classification shape the operator/operand split;
        # Halstead is computed over the whole (opaque) file stream, so it cites
        # the conditional rulings that engaged anywhere in the measured range
        hal_rulings = (hal_mod.R_LEXICAL,) + tok_lang_rulings + file_cond
        for r in hal_rulings:
            ctx.fired.add(r)
        for name, value in hal_values.items():
            file_metrics.append(
                MetricValue(name, value, rulings=hal_rulings,
                            diagnostics=(hal_mod.APPROX_DIAGNOSTIC,))
            )
    if "maintainability_index" in metrics:
        mi_value = mi_mod.maintainability_index(
            hal_values["halstead.volume"], cc_value, loc_values["sloc"]
        )
        ctx.fired.add(mi_mod.R_MI)
        file_metrics.append(
            MetricValue(
                "maintainability_index", mi_value, rulings=(mi_mod.R_MI,),
                derived_from=mi_mod.DERIVED_FROM,
                diagnostics=(mi_mod.CONTAINS_CC_DIAGNOSTIC,),
            )
        )
    if "loc" in metrics:
        # TOK-ALL-0005 governs the line attribution sloc/comment_lines count
        # over; the atomic-token rulings govern which spans exist to attribute
        loc_rulings = ((loc_mod.R_PHYSICAL, loc_mod.R_SLOC, loc_mod.R_CLOC,
                        loc_mod.R_LLOC, loc_mod.R_TOK_LINES)
                       + tok_lang_rulings + file_cond)
        for r in loc_rulings:
            ctx.fired.add(r)
        for name, ivalue in loc_values.items():
            file_metrics.append(
                MetricValue(name, ivalue, rulings=loc_rulings,
                            trace=ctx.trace_for("lloc") if name == "lloc" else ())
            )

    # --- per-function metrics (cyclomatic + cognitive; CORE-ALL-0003 exclusion)
    units = adapter.function_units(tree)
    if scaffolded:
        # Drop phantom scaffold units (__CC__/__cc__ live on scaffold lines) and
        # rebase spans back to original snippet coordinates (CORE-JAVA-0001).
        lo, hi = line_range if line_range is not None else (1, len(lines))
        units = [
            gran_mod.rebase_unit(u, line_offset, len(lines))
            for u in units
            if lo <= u.span.start_line <= hi
        ]
    functions: list[FunctionReport] = []
    for unit in units:
        fn_metrics: list[MetricValue] = []
        if "cyclomatic" in metrics:
            fn_cc = cc_mod.cyclomatic(unit.node, adapter, ctx, exclude_nested_units=True)
            fn_metrics.append(MetricValue("cyclomatic", fn_cc, rulings=_cc_rulings(adapter)))
        if "cognitive" in metrics:
            fn_cog = cog_mod.cognitive(
                unit.node, adapter, ctx, exclude_nested_units=True,
                initial_function_names=(unit.name,),
            )
            fn_metrics.append(
                MetricValue("cognitive", fn_cog,
                            rulings=_cog_rulings(adapter, cognitive_mode))
            )
        functions.append(
            FunctionReport(unit.name, unit.qualified_name, unit.span, tuple(fn_metrics))
        )

    # --- readability vectors
    vectors = []
    if "bw2010" in readability:
        # BW-ALL-0007: the BW construct is lexical — on parse errors its
        # token-family features use the full leaf stream, ERROR regions
        # included. Every metric above stays error-opaque (CORE-ALL-0002).
        bw_tokens = tokens
        lexical_fallback = False
        cond_full: dict[str, set[int]] = {}
        if not parse_ok:
            full = tok_mod.lex(tree, source_bytes, adapter,
                               include_error_tokens=True, cond_lines=cond_full)
            if line_range is not None:
                full = gran_mod.rebase_tokens(full, line_range[0], line_range[1])
            lexical_fallback = len(full) != len(tokens)
            if lexical_fallback:
                bw_tokens = full
        if granularity == "function":
            vectors = gran_mod.function_vectors(
                lines, bw_tokens, adapter, units,
                opaque_tokens=tokens if lexical_fallback else None,
                cond_opaque=cond_opaque,
                cond_full=cond_full,
            )
        else:
            # single file/snippet vector over the whole measured range, on
            # whichever stream it used
            vec_cond = gran_mod.cond_in_range(
                cond_full if lexical_fallback else cond_opaque,
                measured_lo, measured_hi,
            )
            vectors = [
                gran_mod.vector(lines, bw_tokens, adapter, granularity,
                                scaffolded=scaffolded, lexical_fallback=lexical_fallback,
                                cond_rulings=vec_cond)
            ]
        for v in vectors:
            ctx.fired.update(v.rulings)
        # The report-level trace appears only when an EMITTED vector actually
        # engaged the fallback: at granularity="function" an ERROR region
        # outside every unit changes no emitted number, so a report-level
        # BW-ALL-0007 claim would be false.
        if any("BW-ALL-0007" in v.rulings for v in vectors):
            diagnostics.append(
                Diagnostic(
                    "info", "bw-lexical-fallback",
                    "parse errors present; bw2010 token-family features were "
                    "computed over the full lexical stream, ERROR regions "
                    "included (BW-ALL-0007)",
                    ruling="BW-ALL-0007",
                )
            )

    # Provenance must not contradict the report's own diagnostics: every
    # diagnostic-cited ruling observably shaped the run (TOK-ALL-0001/0002
    # normalization, CORE-ALL-0002 error opacity, CORE-JAVA-0001 scaffolding,
    # BW-ALL-0007 fallback), so it belongs in rulings_applied.
    for d in diagnostics:
        if d.ruling:
            ctx.fired.add(d.ruling)
    provenance = Provenance(
        tool_version=__version__,
        spec_version=spec_version(),
        language=adapter.name,
        grammar=adapter.grammar_info(),
        modes=(("cognitive", cognitive_mode),),
        rulings_applied=tuple(sorted(ctx.fired)),
    )
    if not provenance.grammar.validated:
        diagnostics.append(
            Diagnostic(
                "warning", "unvalidated-grammar",
                f"installed {provenance.grammar.package} {provenance.grammar.version} is "
                "not the release-calibrated version; results are honest but "
                "uncalibrated (ARCHITECTURE.md §10)",
            )
        )

    return FileReport(
        path=path,
        parse_ok=parse_ok,
        file_metrics=tuple(file_metrics),
        functions=tuple(functions),
        readability=tuple(vectors),
        diagnostics=tuple(diagnostics),
        provenance=provenance,
    )


def _cc_rulings(adapter: LanguageAdapter) -> tuple[str, ...]:
    from codecaliper.spec import iter_rulings

    return tuple(
        sorted(r.id for r in iter_rulings(metric="cyclomatic", language=adapter.name))
    )


def _cog_rulings(adapter: LanguageAdapter, mode: str) -> tuple[str, ...]:
    from codecaliper.spec import iter_rulings

    return tuple(
        sorted(
            r.id
            for r in iter_rulings(metric="cognitive", language=adapter.name)
            if r.mode in ("", mode)
        )
    )
