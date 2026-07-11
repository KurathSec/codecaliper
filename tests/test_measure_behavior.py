"""Behavioural tests for the policies that corpus value-assertions can't carry:
parse-error recovery, granularity labelling, the Java snippet scaffold, honesty
diagnostics, and provenance completeness.
"""

from __future__ import annotations

import pytest

from codecaliper import BW_FEATURE_NAMES, StrictParseError, measure
from codecaliper.model import metric_map


def test_parse_error_recovered_and_labelled() -> None:
    rep = measure("def broken(:\n    pass\n", language="python")
    assert not rep.parse_ok
    assert any(d.code == "parse-error-recovered" for d in rep.diagnostics)
    # the diagnostic-cited ruling shaped every emitted number (error opacity),
    # so provenance must report it
    assert "CORE-ALL-0002" in rep.provenance.rulings_applied


def test_error_subtrees_are_opaque() -> None:
    """CORE-ALL-0002: nothing inside an ERROR/MISSING subtree may feed any
    metric — the boolean_operator below sits inside an ERROR region and must
    not count, and its tokens must not feed Halstead/sloc."""
    src = "x = (1 +\nif a and b:\n    pass\n"
    rep = measure(src, language="python")
    assert not rep.parse_ok
    fm = metric_map(rep.file_metrics)
    assert fm["cyclomatic"].value == 1, (
        "decision points inside ERROR subtrees counted — CORE-ALL-0002 violated"
    )
    assert fm["cognitive"].value == 0
    # clean file for comparison: same tokens, no error
    clean = measure("x = (1 + 2)\nif a and b:\n    pass\n", language="python")
    clean_fm = metric_map(clean.file_metrics)
    assert fm["halstead.N1"].value < clean_fm["halstead.N1"].value, (
        "tokens under the ERROR subtree leaked into Halstead"
    )


def test_error_subtree_functions_are_opaque() -> None:
    """A def nested inside an ERROR subtree must not produce a FunctionReport."""
    src = "x = (1 +\ndef inner():\n    pass\n"
    rep = measure(src, language="python")
    assert not rep.parse_ok
    assert rep.functions == ()
    assert metric_map(rep.file_metrics)["cyclomatic"].value == 1


def test_strict_raises_on_parse_error() -> None:
    with pytest.raises(StrictParseError):
        measure("def broken(:\n", language="python", strict=True)


def test_granularity_extrapolation_labelled() -> None:
    rep = measure("x = 1\n" * 20, language="python", granularity="file")
    vec = rep.readability[0]
    assert vec.granularity == "file"
    assert vec.native_granularity == "snippet"
    assert vec.extrapolated is True
    assert any(d.code == "granularity-extrapolated" for d in vec.diagnostics)


def test_snippet_out_of_calibrated_range_warns() -> None:
    rep = measure("x = 1\n", language="python", granularity="snippet")
    vec = rep.readability[0]
    assert vec.extrapolated is False
    assert any(d.code == "snippet-out-of-calibrated-range" for d in vec.diagnostics)


def test_java_bare_snippet_parses_clean() -> None:
    """CORE-JAVA-0001, verified reality: tree-sitter-java's program rule accepts
    bare statement sequences and bare methods, so BW-dataset-shaped snippets
    parse cleanly WITHOUT the scaffold fallback (which stays as a ruled,
    strictly-error-reducing fallback)."""
    snippet = (
        "int total = 0;\n"
        "for (int i = 0; i < n; i++) {\n"
        "    if (values[i] > 0) {\n"
        "        total += values[i];\n"
        "    }\n"
        "}\n"
    )
    rep = measure(snippet, language="java", granularity="snippet")
    assert rep.parse_ok
    vec = rep.readability[0]
    assert not any(d.code == "snippet-scaffolded" for d in vec.diagnostics)
    features = dict(zip(vec.names, vec.values, strict=True))
    assert features["avg_loops"] == pytest.approx(1 / 6)
    assert features["avg_branches"] == pytest.approx(1 / 6)
    assert features["max_indentation"] == 8.0
    fm = metric_map(rep.file_metrics)
    assert fm["cyclomatic"].value == 3  # 1 + for + if (comparisons are not decisions)
    assert fm["physical_lines"].value == 6

    bare_method = (
        "private int count(int[] values) {\n"
        "    if (values == null) {\n"
        "        return 0;\n"
        "    }\n"
        "    return values.length;\n"
        "}\n"
    )
    rep2 = measure(bare_method, language="java", granularity="snippet")
    assert rep2.parse_ok
    assert [f.name for f in rep2.functions] == ["count"]


def test_java_snippet_scaffold_engages_for_constructor() -> None:
    """CORE-JAVA-0001 fallback actually fires: a bare constructor errors bare
    (1 ERROR) but parses cleanly in the class-only scaffold (verified against
    tree-sitter-java 0.23.5). Features/units must be in ORIGINAL coordinates
    with no phantom __CC__ units."""
    snippet = (
        "public Matrix(int rows, int cols) {\n"
        "    if (rows <= 0 || cols <= 0) {\n"
        "        throw new IllegalArgumentException();\n"
        "    }\n"
        "    this.rows = rows;\n"
        "}\n"
    )
    rep = measure(snippet, language="java", granularity="snippet", explain=True)
    assert rep.parse_ok, "class-only scaffold should yield an error-free tree"
    vec = rep.readability[0]
    assert any(d.code == "snippet-scaffolded" for d in vec.diagnostics)
    # the trace must be report-level too (survives readability=()) and carry the ruling
    assert any(
        d.code == "snippet-scaffolded" and d.ruling == "CORE-JAVA-0001"
        for d in rep.diagnostics
    )
    assert "CORE-JAVA-0001" in rep.provenance.rulings_applied
    rep_metrics_only = measure(snippet, language="java", granularity="snippet",
                               readability=())
    assert any(d.code == "snippet-scaffolded" for d in rep_metrics_only.diagnostics)
    features = dict(zip(vec.names, vec.values, strict=True))
    # original 6 lines, not scaffold coordinates
    fm = metric_map(rep.file_metrics)
    assert fm["physical_lines"].value == 6
    assert features["avg_branches"] == pytest.approx(1 / 6)
    assert fm["cyclomatic"].value == 3  # 1 + if + ||
    # no phantom scaffold unit; the constructor's span is rebased to line 1
    names = [f.name for f in rep.functions]
    assert "__cc__" not in names and "__CC__" not in names
    assert [f.name for f in rep.functions] == ["Matrix"]
    assert rep.functions[0].span.start_line == 1
    # explain traces are in original coordinates too (the `if` is on line 2)
    cc = fm["cyclomatic"]
    if_trace = [t for t in cc.trace if t.ruling_id == "CC-JAVA-0001"]
    assert if_trace and if_trace[0].span.start_line == 2
    # EVERY trace span (the root-counted CC-ALL-0001 base included) must lie
    # inside the snippet's own line domain — scaffold coordinates may not leak
    n = int(fm["physical_lines"].value)
    for t in cc.trace:
        assert 1 <= t.span.start_line <= t.span.end_line <= n, (
            f"trace {t.ruling_id} span {t.span} outside the {n}-line snippet"
        )


def test_recursion_receiver_rule_java() -> None:
    """COG-ALL-0005: this-receiver recursion counts; other receivers do not."""
    tmpl = (
        "class T {{\n"
        "    int walk(int n) {{\n"
        "        if (n <= 0) return 0;\n"
        "        return {call};\n"
        "    }}\n"
        "}}\n"
    )
    rec = measure(tmpl.format(call="this.walk(n - 1)"), language="java")
    other = measure(tmpl.format(call="helper.walk(n - 1)"), language="java")
    bare = measure(tmpl.format(call="walk(n - 1)"), language="java")
    def cog(rep):
        return metric_map(rep.file_metrics)["cognitive"].value
    assert cog(rec) == cog(bare) == 2  # if +1, recursion +1 (whitepaper)
    assert cog(other) == 1  # same-named call on another receiver is not recursion


def test_recursion_receiver_rule_python_self() -> None:
    src = (
        "class T:\n"
        "    def walk(self, n):\n"
        "        if n <= 0:\n"
        "            return 0\n"
        "        return self.walk(n - 1)\n"
    )
    rep = measure(src, language="python")
    assert metric_map(rep.file_metrics)["cognitive"].value == 2


def test_match_wildcard_mirrors_default() -> None:
    """CC-PY-0008: `case _:` with no guard does not count; a guarded wildcard does."""
    plain = "match x:\n    case 1:\n        pass\n    case _:\n        pass\n"
    guarded = "match x:\n    case 1:\n        pass\n    case _ if x > 0:\n        pass\n"
    cc_plain = metric_map(measure(plain, language="python").file_metrics)["cyclomatic"].value
    cc_guarded = metric_map(measure(guarded, language="python").file_metrics)["cyclomatic"].value
    assert cc_plain == 2
    assert cc_guarded == 3


def test_mi_declares_derivation() -> None:
    rep = measure("x = 1\n", language="python")
    mi = metric_map(rep.file_metrics)["maintainability_index"]
    assert mi.derived_from == ("halstead.volume", "cyclomatic", "sloc")
    assert any(d.code == "mi-contains-cc" for d in mi.diagnostics)


def test_halstead_declares_approximation() -> None:
    rep = measure("x = 1\n", language="python")
    vol = metric_map(rep.file_metrics)["halstead.volume"]
    assert any(d.code == "halstead-approximation" for d in vol.diagnostics)


def test_provenance_complete() -> None:
    rep = measure("x = 1\n", language="python")
    prov = rep.provenance
    assert prov is not None
    assert prov.spec_version
    assert prov.grammar.version
    assert prov.grammar.abi_version > 0
    assert dict(prov.modes)["cognitive"] == "whitepaper"
    assert prov.rulings_applied == tuple(sorted(prov.rulings_applied))


def test_bw_vector_shape() -> None:
    rep = measure("x = 1\n", language="python")
    vec = rep.readability[0]
    assert vec.names == BW_FEATURE_NAMES
    assert len(vec.values) == 25


def test_explain_traces() -> None:
    rep = measure("if x and y:\n    pass\n", language="python", explain=True)
    cc = metric_map(rep.file_metrics)["cyclomatic"]
    assert cc.trace, "--explain must attach RulingTraces"
    assert {t.ruling_id for t in cc.trace} == {"CC-ALL-0001", "CC-PY-0001", "CC-PY-0003"}
    assert sum(t.delta for t in cc.trace) == cc.value, (
        "--explain increments (base included) must sum to the emitted value"
    )
    # the base is traced against the measured domain, never past the last line
    base = [t for t in cc.trace if t.ruling_id == "CC-ALL-0001"][0]
    assert base.span.start_line == 1 and base.span.end_line == 2
    # lloc increments are traced too, and they sum to the emitted value
    lloc = metric_map(rep.file_metrics)["lloc"]
    assert lloc.trace and sum(t.delta for t in lloc.trace) == lloc.value
    rep_default = measure("if x and y:\n    pass\n", language="python")
    assert not metric_map(rep_default.file_metrics)["cyclomatic"].trace
    assert not metric_map(rep_default.file_metrics)["lloc"].trace


def test_bw_lexical_fallback_scoping() -> None:
    """BW-ALL-0007: on parse errors, BW token features see ERROR-region tokens
    (both diagnostic levels + provenance), while every metric stays error-opaque
    (CORE-ALL-0002) — and a clean parse never carries the fallback."""
    src = "count = 1\nbroken = (count +\nif count and flag:\n    pass\n"
    rep = measure(src, language="python")
    assert not rep.parse_ok
    assert any(
        d.code == "bw-lexical-fallback" and d.ruling == "BW-ALL-0007"
        for d in rep.diagnostics
    )
    vec = rep.readability[0]
    assert any(d.code == "bw-lexical-fallback" for d in vec.diagnostics)
    assert "BW-ALL-0007" in vec.rulings
    assert "BW-ALL-0007" in rep.provenance.rulings_applied
    features = dict(zip(vec.names, vec.values, strict=True))
    assert features["max_identifiers"] == 2.0, "ERROR-region identifiers must count for BW"
    fm = metric_map(rep.file_metrics)
    assert fm["cyclomatic"].value == 1, "metrics must stay error-opaque"
    assert fm["sloc"].value == 1

    clean = measure("count = 1\n", language="python")
    assert not any(d.code == "bw-lexical-fallback" for d in clean.diagnostics)
    assert "BW-ALL-0007" not in clean.provenance.rulings_applied

    # per-unit scoping at granularity="function": only a unit whose own span
    # gained ERROR-region tokens carries the flag; clean units stay unflagged
    src_fn = ("def clean(a):\n    return a\n\n"
              "def dirty(b):\n    y = (b +\n    z = 1\n    return b\n")
    rep_fn = measure(src_fn, language="python", granularity="function")
    flags = {
        v.unit_name: any(d.code == "bw-lexical-fallback" for d in v.diagnostics)
        for v in rep_fn.readability
    }
    assert flags == {"clean": False, "dirty": True}
    by_name = {v.unit_name: v for v in rep_fn.readability}
    assert "BW-ALL-0007" not in by_name["clean"].rulings
    assert "BW-ALL-0007" in by_name["dirty"].rulings
    # a unit DID engage, so the report-level diagnostic + provenance follow
    assert any(d.code == "bw-lexical-fallback" for d in rep_fn.diagnostics)
    assert "BW-ALL-0007" in rep_fn.provenance.rulings_applied

    # at granularity="function", an ERROR region OUTSIDE every unit changes no
    # emitted number: no report-level fallback claim, no fired BW-ALL-0007
    src_out = "def clean(x):\n    return x + 1\n\n@@@ $garbage$ @@@\n"
    rep_out = measure(src_out, language="python", granularity="function")
    assert not rep_out.parse_ok
    assert not any(d.code == "bw-lexical-fallback" for d in rep_out.diagnostics)
    assert "BW-ALL-0007" not in rep_out.provenance.rulings_applied
    assert all("BW-ALL-0007" not in v.rulings for v in rep_out.readability)


def test_csv_vectors_join_by_span_not_name() -> None:
    """Same-qualified-name units (Java overloads, Python redefinitions) must
    each carry their OWN BW vector in CSV output — a name-keyed join silently
    hands every row the last unit's numbers."""
    import csv
    import io

    from codecaliper.canonical import to_csv

    src = (
        "class Over {\n"
        "    int f(int a) {\n"
        "        return a;\n"
        "    }\n"
        "    int f(String s, int b) {\n"
        "        return b + b + b;\n"
        "    }\n"
        "}\n"
    )
    rep = measure(src, language="java", granularity="function")
    rows = list(csv.DictReader(io.StringIO(to_csv([rep]))))
    fn_rows = [r for r in rows if r["scope"] == "function"]
    assert len(fn_rows) == 2 and all(r["name"] == "Over.f" for r in fn_rows)
    by_span = {v.span.start_line: v for v in rep.readability if v.granularity == "function"}
    for row in fn_rows:
        vec = by_span[int(row["start_line"])]
        expect = dict(zip(vec.names, vec.values, strict=True))
        assert float(row["bw_avg_identifiers"]) == pytest.approx(
            expect["avg_identifiers"], abs=1e-9
        ), f"row at line {row['start_line']} carries another unit's vector"
    # the two overloads genuinely differ, so the assertion above is not vacuous
    vals = {float(r["bw_avg_identifiers"]) for r in fn_rows}
    assert len(vals) == 2


def test_ruling_citations_are_language_scoped_and_complete() -> None:
    """Citation metadata honesty: a Java value may not cite a Python-scoped
    ruling; provenance may not contradict the report's own diagnostics; and
    the BW vector names the language-specific and tokenization rulings that
    shaped its numbers (TOK-ALL-0006 was the headline spec-1.0.0 change)."""
    rep_java = measure("class A {\n    void f() {}\n}\n", language="java")
    cog = metric_map(rep_java.file_metrics)["cognitive"]
    assert "COG-PY-0001" not in cog.rulings, "Java value citing a Python ruling"
    assert "COG-JAVA-0001" in cog.rulings

    rep_py = measure("def f():\n    pass\n", language="python")
    cog_py = metric_map(rep_py.file_metrics)["cognitive"]
    assert "COG-JAVA-0001" not in cog_py.rulings
    assert "COG-PY-0001" in cog_py.rulings

    # normalization rulings observably firing must reach rulings_applied
    bom = measure("﻿x = 1\n".encode(), language="python")
    assert any(d.code == "bom-stripped" for d in bom.diagnostics)
    assert "TOK-ALL-0002" in bom.provenance.rulings_applied
    crlf = measure(b"x = 1\r\ny = 2\r\n", language="python")
    assert "TOK-ALL-0003" in crlf.provenance.rulings_applied
    plain = measure("x = 1\n", language="python")
    assert "TOK-ALL-0002" not in plain.provenance.rulings_applied
    assert "TOK-ALL-0003" not in plain.provenance.rulings_applied
    # the base increment backs every emitted cyclomatic value
    assert "CC-ALL-0001" in plain.provenance.rulings_applied

    vec = plain.readability[0]
    for rid in ("BW-PY-0001", "BW-PY-0002", "TOK-ALL-0005", "TOK-ALL-0006", "TOK-PY-0002"):
        assert rid in vec.rulings, f"BW vector missing governing ruling {rid}"
    jvec = rep_java.readability[0]
    assert "BW-JAVA-0001" in jvec.rulings and "BW-PY-0001" not in jvec.rulings
    assert "TOK-JAVA-0001" in jvec.rulings and "TOK-PY-0002" not in jvec.rulings
    # the atomic-token rulings govern every token-derived value
    hal = metric_map(plain.file_metrics)["halstead.volume"]
    assert "TOK-PY-0002" in hal.rulings
    assert "TOK-PY-0002" in metric_map(plain.file_metrics)["sloc"].rulings


def test_tok_all_0007_fires_only_when_engaged() -> None:
    """TOK-ALL-0007 reclassified tokens on its own normative corpus inputs, so
    the reports for those inputs must cite it — and a file without anonymous
    word tokens must not."""
    from conftest import CORPUS_DIR

    fut = (CORPUS_DIR / "python" / "py-future-import-001" / "input.py").read_text()
    rep = measure(fut, language="python")
    assert "TOK-ALL-0007" in rep.provenance.rulings_applied
    assert "TOK-ALL-0007" in rep.readability[0].rulings
    assert "TOK-ALL-0007" in metric_map(rep.file_metrics)["halstead.volume"].rulings

    ctx = (CORPUS_DIR / "java" / "java-contextual-001" / "input.java").read_text()
    rep_j = measure(ctx, language="java")
    assert "TOK-ALL-0007" in rep_j.provenance.rulings_applied
    assert "TOK-ALL-0007" in rep_j.readability[0].rulings

    plain = measure("x = 1\n", language="python")
    assert "TOK-ALL-0007" not in plain.provenance.rulings_applied
    assert "TOK-ALL-0007" not in plain.readability[0].rulings


def test_conditional_token_rulings_are_per_unit() -> None:
    """A construct-specific tokenization ruling (TOK-ALL-0007, TOK-JAVA-0002)
    is cited on a per-function BW vector only when its token lies inside that
    unit's own span — not file-globally."""
    src = "from __future__ import annotations\n\ndef f(x):\n    return x + 1\n"
    rep = measure(src, language="python", granularity="function")
    fvec = next(v for v in rep.readability if (v.unit_name or "").endswith("f"))
    assert "TOK-ALL-0007" not in fvec.rulings, (
        "the __future__ token is outside unit f, so its vector must not cite it"
    )
    # but the file-level Halstead genuinely counted __future__, so provenance does
    assert "TOK-ALL-0007" in rep.provenance.rulings_applied


def test_tok_java_0002_is_conditional_not_static() -> None:
    """TOK-JAVA-0002 (`_`) governs per-occurrence: a Java file with no `_` must
    not cite it anywhere, while TOK-JAVA-0001 (string atomicity) is static."""
    from codecaliper.model import metric_map

    plain = measure("class A {\n    void f() { int x = 1; }\n}\n", language="java")
    assert "TOK-JAVA-0002" not in plain.provenance.rulings_applied
    assert "TOK-JAVA-0002" not in plain.readability[0].rulings
    assert "TOK-JAVA-0001" in plain.provenance.rulings_applied  # static

    us = "class B {\n    void g() { int _ = 1; }\n}\n"
    rep = measure(us, language="java")
    assert "TOK-JAVA-0002" in rep.provenance.rulings_applied
    assert "TOK-JAVA-0002" in rep.readability[0].rulings
    assert "TOK-JAVA-0002" in metric_map(rep.file_metrics)["halstead.volume"].rulings


def test_soft_keyword_table_is_pinned_not_host_dependent() -> None:
    """BW-PY-0001's soft-keyword set is pinned, so `type` (added to CPython's
    softkwlist only in 3.12) classifies identically on every supported
    interpreter — via the soft-keyword branch, never the TOK-ALL-0007
    anonymous-word branch."""
    from codecaliper.languages.python import PythonAdapter

    assert PythonAdapter().soft_keywords == frozenset({"_", "case", "match", "type"})
    rep = measure("type Alias = int\n", language="python")
    assert "TOK-ALL-0007" not in rep.provenance.rulings_applied


def test_session_rejects_invalid_mode_and_granularity() -> None:
    """An invalid cognitive_mode would otherwise silently measure as
    sonar-compat while stamping the bogus string into provenance.modes."""
    from codecaliper import CodecaliperError, Session

    with pytest.raises(CodecaliperError, match="cognitive mode"):
        Session(cognitive_mode="bogus")  # type: ignore[arg-type]
    with pytest.raises(CodecaliperError, match="granularity"):
        Session(granularity="bogus")  # type: ignore[arg-type]


def test_concatenated_string_comment_is_a_comment_token() -> None:
    """TOK-PY-0002: a comment between implicitly concatenated string parts is
    an ordinary COMMENT token — it counts as a comment line, not code, and the
    string parts do not swallow its text."""
    src = 'msg = ("part one "\n       # explains part two\n       "part two")\n'
    rep = measure(src, language="python")
    assert rep.parse_ok
    fm = metric_map(rep.file_metrics)
    assert fm["comment_lines"].value == 1
    assert fm["sloc"].value == 2
    feats = dict(zip(rep.readability[0].names, rep.readability[0].values, strict=True))
    assert feats["avg_comments"] == pytest.approx(1 / 3)
    assert "TOK-PY-0002" in rep.readability[0].rulings


def test_encoding_diagnostic_only_on_actual_replacement() -> None:
    """TOK-ALL-0001: valid UTF-8 that legitimately CONTAINS U+FFFD is not
    'replaced' — the diagnostic fires only when undecodable bytes were hit."""
    legit = 's = "\N{REPLACEMENT CHARACTER}"\n'.encode()
    rep = measure(legit, language="python")
    assert not any(d.code == "encoding-replaced" for d in rep.diagnostics)
    assert "TOK-ALL-0001" not in rep.provenance.rulings_applied

    broken = b's = "\xff\xfe"\n'
    rep2 = measure(broken, language="python")
    assert any(d.code == "encoding-replaced" for d in rep2.diagnostics)
    assert "TOK-ALL-0001" in rep2.provenance.rulings_applied
