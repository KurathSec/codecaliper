"""Shared corpus-value computation for the drift gate and tools/update_snapshot.py."""

from __future__ import annotations

from conftest import case_measure_kwargs, case_source, corpus_cases

from codecaliper import measure
from codecaliper.canonical import qfloat


def _duplicates(names: list[str]) -> set[str]:
    seen: set[str] = set()
    dups: set[str] = set()
    for n in names:
        (dups if n in seen else seen).add(n)
    return dups


def compute_corpus_values() -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for case in corpus_cases():
        values: dict[str, object] = {}
        for mode in ("whitepaper", "sonar-compat"):
            rep = measure(case_source(case), language=case["language"],
                          cognitive_mode=mode, **case_measure_kwargs(case))
            for mv in rep.file_metrics:
                key = f"{mv.metric}.{mode}" if mv.metric == "cognitive" else mv.metric
                values[key] = qfloat(mv.value) if isinstance(mv.value, float) else mv.value
            # Disambiguate by span ONLY when a name/vector could collide (Java
            # overloads or a >=2-unit function-granularity case), so the drift
            # gate never silently drops a distinct value — and single-unit,
            # single-vector cases keep their plain keys (no snapshot churn).
            dup_names = _duplicates([fn.qualified_name for fn in rep.functions])
            for fn in rep.functions:
                # start_line:start_col — two overloads can share a line, never a
                # start position, so distinct values never collide to one key
                tag = (f"@{fn.span.start_line}:{fn.span.start_col}"
                       if fn.qualified_name in dup_names else "")
                for mv in fn.metrics:
                    if mv.metric == "cognitive":
                        values[f"fn.{fn.qualified_name}{tag}.cognitive.{mode}"] = mv.value
                    elif mode == "whitepaper":
                        values[f"fn.{fn.qualified_name}{tag}.{mv.metric}"] = mv.value
            if mode == "whitepaper":
                multi = len(rep.readability) > 1
                for vec in rep.readability:
                    vtag = (f"{vec.span.start_line}:{vec.span.start_col}."
                            if multi and vec.span else "")
                    for name, val in zip(vec.names, vec.values, strict=True):
                        values[f"bw.{vtag}{name}"] = qfloat(val)
        out[case["id"]] = values
    return out
