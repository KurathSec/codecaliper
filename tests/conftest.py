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
    """Every corpus case: {id, language, input_path, source, expected}."""
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
            cases.append(
                {
                    "id": case_dir.name,
                    "language": expected["case"]["language"],
                    "input_path": inputs[0],
                    "source": inputs[0].read_text(encoding="utf-8"),
                    "expected": expected,
                }
            )
    return cases
