"""Shared corpus-value computation for the drift gate and tools/update_snapshot.py."""

from __future__ import annotations

from conftest import corpus_cases

from codecaliper import measure
from codecaliper.canonical import qfloat


def compute_corpus_values() -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for case in corpus_cases():
        values: dict[str, object] = {}
        for mode in ("whitepaper", "sonar-compat"):
            rep = measure(case["source"], language=case["language"], cognitive_mode=mode)
            for mv in rep.file_metrics:
                key = f"{mv.metric}.{mode}" if mv.metric == "cognitive" else mv.metric
                values[key] = qfloat(mv.value) if isinstance(mv.value, float) else mv.value
            for fn in rep.functions:
                for mv in fn.metrics:
                    if mv.metric == "cognitive":
                        values[f"fn.{fn.qualified_name}.cognitive.{mode}"] = mv.value
                    elif mode == "whitepaper":
                        values[f"fn.{fn.qualified_name}.{mv.metric}"] = mv.value
            if mode == "whitepaper":
                for vec in rep.readability:
                    for name, val in zip(vec.names, vec.values, strict=True):
                        values[f"bw.{name}"] = qfloat(val)
        out[case["id"]] = values
    return out
