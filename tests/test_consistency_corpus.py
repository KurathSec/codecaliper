"""§6.1 consistency corpus: hand-computed expected values, asserted per metric,
per BW feature, and per cognitive mode (ARCHITECTURE.md §8.1).

Integers assert exactly; floats always via explicit tolerance (CORE-ALL-0004).
A failure names the case, the metric, and the rulings in dispute.
"""

from __future__ import annotations

import math

import pytest
from conftest import case_measure_kwargs, case_source, corpus_cases

from codecaliper import measure
from codecaliper.languages import detect_language
from codecaliper.model import DIAGNOSTIC_CODES, metric_map

CASES = corpus_cases()


def _assert_value(case_id: str, name: str, actual: float, expected: object) -> None:
    if isinstance(expected, dict):  # {value = ..., abs_tol = ...}
        assert math.isclose(
            actual, float(expected["value"]), abs_tol=float(expected.get("abs_tol", 1e-9))
        ), f"{case_id}::{name}: {actual} != {expected['value']}"
    elif isinstance(expected, float):
        assert math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), (
            f"{case_id}::{name}: {actual} != {expected}"
        )
    else:
        assert actual == expected, f"{case_id}::{name}: {actual} != {expected}"


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_case(case: dict) -> None:
    expected = case["expected"]
    rulings = expected["case"].get("rulings", [])
    header = f"[{case['id']}] rulings in dispute: {', '.join(rulings)}"

    src = case_source(case)
    kwargs = case_measure_kwargs(case)
    reports = {
        "whitepaper": measure(src, language=case["language"],
                              cognitive_mode="whitepaper", **kwargs),
    }

    if "CORE-ALL-0005" in rulings:
        # the cited case doubles as the extension-map witness
        assert detect_language(str(case["input_path"])) == case["language"]

    file_expect = dict(expected.get("expect", {}).get("file", {}))
    cog_expect = file_expect.pop("cognitive", None)
    fm = metric_map(reports["whitepaper"].file_metrics)

    for name, exp in file_expect.items():
        assert name in fm, f"{header}: metric {name!r} missing from report"
        _assert_value(case["id"], name, fm[name].value, exp)

    def _sonar_report():
        if "sonar-compat" not in reports:
            reports["sonar-compat"] = measure(
                src, language=case["language"], cognitive_mode="sonar-compat", **kwargs
            )
        return reports["sonar-compat"]

    if cog_expect is not None:
        _assert_value(case["id"], "cognitive.whitepaper", fm["cognitive"].value,
                      cog_expect["whitepaper"])
        fm_sonar = metric_map(_sonar_report().file_metrics)
        _assert_value(case["id"], "cognitive.sonar_compat", fm_sonar["cognitive"].value,
                      cog_expect["sonar_compat"])

    def _fn_metrics(report, fn_name):
        matches = [f for f in report.functions if f.name == fn_name]
        assert matches, f"{header}: no function named {fn_name!r} in report"
        return metric_map(matches[0].metrics)

    for fn_name, fn_expect in expected.get("expect", {}).get("functions", {}).items():
        for name, exp in fn_expect.items():
            if isinstance(exp, dict) and "whitepaper" in exp:
                # dual-mode per-function assertion (e.g. cognitive tables)
                _assert_value(case["id"], f"functions.{fn_name}.{name}.whitepaper",
                              _fn_metrics(reports["whitepaper"], fn_name)[name].value,
                              exp["whitepaper"])
                _assert_value(case["id"], f"functions.{fn_name}.{name}.sonar_compat",
                              _fn_metrics(_sonar_report(), fn_name)[name].value,
                              exp["sonar_compat"])
            else:
                _assert_value(case["id"], f"functions.{fn_name}.{name}",
                              _fn_metrics(reports["whitepaper"], fn_name)[name].value, exp)

    bw_expect = expected.get("expect", {}).get("bw", {})
    if bw_expect:
        vec = reports["whitepaper"].readability[0]
        features = dict(zip(vec.names, vec.values, strict=True))
        for name, exp in bw_expect.items():
            _assert_value(case["id"], f"bw.{name}", features[name], exp)

    # scaffold artifacts must never leak into emitted output (CORE-JAVA-0001)
    for fn in reports["whitepaper"].functions:
        assert "__CC__" not in fn.qualified_name and "__cc__" not in fn.qualified_name, (
            f"{header}: scaffold identifier leaked into {fn.qualified_name!r}"
        )

    report_expect = expected.get("expect", {}).get("report", {})
    for code in report_expect.get("diagnostics_include", []):
        assert any(d.code == code for d in reports["whitepaper"].diagnostics), (
            f"{header}: report diagnostics missing {code!r}"
        )

    vec_expect = expected.get("expect", {}).get("vector", {})
    if vec_expect:
        vec = reports["whitepaper"].readability[0]
        for field in ("granularity", "native_granularity", "extrapolated"):
            if field in vec_expect:
                assert getattr(vec, field) == vec_expect[field], (
                    f"{header}: vector.{field} = {getattr(vec, field)!r}, "
                    f"expected {vec_expect[field]!r}"
                )
        for code in vec_expect.get("diagnostics_include", []):
            assert any(d.code == code for d in vec.diagnostics), (
                f"{header}: vector diagnostics missing {code!r}"
            )


def test_diagnostic_codes_are_a_closed_set() -> None:
    """Every diagnostic code emitted anywhere across the corpus is a member of
    DIAGNOSTIC_CODES — the set stays closed by enforcement, not by comment
    (ARCHITECTURE.md §2). A new code lands by extending the set, never ad hoc."""
    for case in CASES:
        rep = measure(case_source(case), language=case["language"],
                      **case_measure_kwargs(case))
        seen = {d.code for d in rep.diagnostics}
        seen.update(d.code for m in rep.file_metrics for d in m.diagnostics)
        seen.update(d.code for v in rep.readability for d in v.diagnostics)
        for fn in rep.functions:
            seen.update(d.code for m in fn.metrics for d in m.diagnostics)
        unknown = seen - DIAGNOSTIC_CODES
        assert not unknown, f"{case['id']}: diagnostic codes outside the closed set: {unknown}"


def test_parse_ok_matches_declaration() -> None:
    """Corpus inputs parse cleanly unless the case EXPLICITLY declares
    parse_ok = false (error-opacity fixtures, CORE-ALL-0002)."""
    for case in CASES:
        rep = measure(case_source(case), language=case["language"],
                      **case_measure_kwargs(case))
        declared = case["expected"]["case"].get("parse_ok", True)
        assert rep.parse_ok == declared, (
            f"{case['id']}: parse_ok={rep.parse_ok}, declared {declared}"
        )
