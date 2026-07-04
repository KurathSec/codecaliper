"""Canonical, deterministic serialization (CORE-ALL-0004).

No timestamps, no hash-order dependence; floats are quantized to 12 significant
digits (round-half-even via repr of the formatted value). Byte-identical output
is a per-platform guarantee — tests/test_determinism.py enforces it.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import fields, is_dataclass
from typing import Any

from codecaliper.model import FileReport


def qfloat(x: float) -> float:
    """Quantize to 12 significant digits (CORE-ALL-0004)."""
    return float(f"{x:.12g}")


def _plain(obj: Any) -> Any:
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _plain(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, tuple) and obj and isinstance(obj[0], tuple) and len(obj[0]) == 2:
        # mode pairs -> object
        try:
            return {k: _plain(v) for k, v in obj}
        except (TypeError, ValueError):
            return [_plain(v) for v in obj]
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, float):
        return qfloat(obj)
    return obj


def to_dict(report: FileReport) -> dict[str, Any]:
    return _plain(report)


def to_json(report: FileReport) -> str:
    return json.dumps(to_dict(report), ensure_ascii=False, indent=2) + "\n"


#: Wide-format CSV: one row per scope, flat metric + BW columns, plus MANDATORY
#: provenance columns — a pasted CSV row still names its spec (ARCHITECTURE.md §9).
_PROVENANCE_COLUMNS = (
    "spec_version", "tool_version", "language", "grammar_package", "grammar_version",
    "grammar_validated", "cognitive_mode", "parse_ok",
)


def to_csv(reports: list[FileReport]) -> str:
    metric_names: list[str] = []
    bw_names: list[str] = []
    for rep in reports:
        for mv in rep.file_metrics:
            if mv.metric not in metric_names:
                metric_names.append(mv.metric)
        for vec in rep.readability:
            for n in vec.names:
                if n not in bw_names:
                    bw_names.append(n)
    header = (
        ["path", "scope", "name", "start_line", "end_line"]
        + metric_names
        + [f"bw_{n}" for n in bw_names]
        + ["bw_granularity", "bw_extrapolated"]
        + list(_PROVENANCE_COLUMNS)
    )
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for rep in reports:
        prov = rep.provenance
        assert prov is not None
        prov_cells = [
            prov.spec_version, prov.tool_version, prov.language, prov.grammar.package,
            prov.grammar.version, prov.grammar.validated, dict(prov.modes)["cognitive"],
            rep.parse_ok,
        ]
        file_vec = next(
            (v for v in rep.readability if v.granularity in ("file", "snippet")), None
        )
        file_metrics = {mv.metric: mv.value for mv in rep.file_metrics}
        row: list[Any] = [rep.path or "", "file", "", "", ""]
        row += [_cell(file_metrics.get(m)) for m in metric_names]
        if file_vec is not None:
            fv = dict(zip(file_vec.names, file_vec.values, strict=True))
            row += [_cell(fv.get(n)) for n in bw_names]
            row += [file_vec.granularity, file_vec.extrapolated]
        else:
            row += ["" for _ in bw_names] + ["", ""]
        row += prov_cells
        w.writerow(row)
        fn_vecs = {v.unit_name: v for v in rep.readability if v.granularity == "function"}
        for fn in rep.functions:
            fm = {mv.metric: mv.value for mv in fn.metrics}
            row = [rep.path or "", "function", fn.qualified_name,
                   fn.span.start_line, fn.span.end_line]
            row += [_cell(fm.get(m)) for m in metric_names]
            vec = fn_vecs.get(fn.qualified_name)
            if vec is not None:
                fv = dict(zip(vec.names, vec.values, strict=True))
                row += [_cell(fv.get(n)) for n in bw_names]
                row += [vec.granularity, vec.extrapolated]
            else:
                row += ["" for _ in bw_names] + ["", ""]
            row += prov_cells
            w.writerow(row)
    return buf.getvalue()


def _cell(v: Any) -> Any:
    if v is None:
        return ""
    if isinstance(v, float):
        return qfloat(v)
    return v
