"""Determinism is a tested contract, not a sentence (CORE-ALL-0004): the CLI is
run twice on the whole corpus under DIFFERENT hash seeds and the outputs must
be byte-identical. (The claim is per-platform; cross-OS byte-identity is
explicitly not claimed.)
"""

from __future__ import annotations

import os
import subprocess
import sys

from conftest import corpus_cases


def _run(hash_seed: str, fmt: str) -> bytes:
    files = [str(c["input_path"]) for c in corpus_cases()]
    langs = {c["language"] for c in corpus_cases()}
    out = b""
    for lang in sorted(langs):
        lang_files = [str(c["input_path"]) for c in corpus_cases() if c["language"] == lang]
        env = dict(os.environ, PYTHONHASHSEED=hash_seed)
        proc = subprocess.run(
            [sys.executable, "-m", "codecaliper.cli", *lang_files, "--lang", lang, fmt],
            capture_output=True, check=True, env=env,
        )
        out += proc.stdout
    assert files
    return out


def test_json_byte_stable_across_hash_seeds() -> None:
    assert _run("0", "--json") == _run("1", "--json")


def test_csv_byte_stable_across_hash_seeds() -> None:
    assert _run("0", "--csv") == _run("1", "--csv")
