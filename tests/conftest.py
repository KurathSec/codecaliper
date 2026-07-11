"""Shared corpus loading for the test suite."""

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

TESTS_DIR = Path(__file__).parent
CORPUS_DIR = TESTS_DIR / "corpus"
SNAPSHOT_PATH = TESTS_DIR / "snapshots" / "corpus_values.json"


def corpus_cases() -> list[dict]:
    """Every corpus case: {id, language, input_path, source, source_bytes, expected}.

    `source` is decoded from the raw bytes (UTF-8, replacement) WITHOUT
    universal-newline translation, so CRLF/BOM fixtures survive as written
    (read_text would silently rewrite \\r\\n to \\n and hide TOK-* behaviour).
    """
    cases = []
    for lang_dir in sorted(CORPUS_DIR.iterdir()):
        if not lang_dir.is_dir():
            continue
        for case_dir in sorted(lang_dir.iterdir()):
            expected_path = case_dir / "expected.toml"
            inputs = [p for p in case_dir.iterdir() if p.name.startswith("input.")]
            assert expected_path.exists(), f"{case_dir} has no expected.toml"
            assert len(inputs) == 1, f"{case_dir} must have exactly one input.* file"
            with expected_path.open("rb") as f:
                expected = tomllib.load(f)
            assert expected["case"]["id"] == case_dir.name, (
                f"{case_dir.name}: [case].id must equal the directory name"
            )
            raw = inputs[0].read_bytes()
            cases.append(
                {
                    "id": case_dir.name,
                    "language": expected["case"]["language"],
                    "input_path": inputs[0],
                    "source": raw.decode("utf-8", errors="replace"),
                    "source_bytes": raw,
                    "expected": expected,
                }
            )
    return cases


def case_source(case: dict) -> str | bytes:
    """The measurement input: raw bytes when the case pins byte-level policy
    ([case].input = "bytes", e.g. TOK-ALL-0001 undecodable-byte fixtures)."""
    if case["expected"]["case"].get("input") == "bytes":
        return case["source_bytes"]
    return case["source"]


def case_measure_kwargs(case: dict) -> dict:
    """Per-case measure() options declared in expected.toml ([case].granularity)."""
    kwargs: dict = {}
    gran = case["expected"]["case"].get("granularity")
    if gran is not None:
        kwargs["granularity"] = gran
    return kwargs


def is_reference_comparable(case: dict) -> bool:
    """Whether the stdlib reference lanes (bw_stdlib / py_ast_lane) can be run
    on this case: they need clean, decodable, default-granularity input —
    normalization edge cases and parse errors are OUR policy surface, not the
    reference's."""
    c = case["expected"]["case"]
    return (
        c.get("parse_ok", True)
        and c.get("input") != "bytes"
        and c.get("granularity") is None
        # a case may opt out when it exercises a construct an external oracle
        # cannot parse at all (e.g. lizard sees no functions in a single-line
        # `...`-body stub) — the mismatch is the oracle's limit, not a value
        # divergence, and the case's own hand-computed expectations still gate it
        and c.get("reference_comparable", True)
    )
