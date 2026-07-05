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
    assert {t.ruling_id for t in cc.trace} == {"CC-PY-0001", "CC-PY-0003"}
    rep_default = measure("if x and y:\n    pass\n", language="python")
    assert not metric_map(rep_default.file_metrics)["cyclomatic"].trace
