"""Structural sanity of divergences.toml and freshness of the generated doc.

These tests need no oracle installed: the table itself must always be
well-formed (real rulings, real inputs, actual divergences, no duplicates)
and docs/spec/divergences.md must be exactly what tools/gen_divergences.py
renders from it.
"""

from __future__ import annotations

import importlib.util

from codecaliper.spec import require
from differential import _harness as h


def test_table_is_well_formed() -> None:
    entries = h.load_table()
    fingerprints = [e.fingerprint for e in entries]
    assert len(fingerprints) == len(set(fingerprints)), "duplicate divergence entries"
    known = h.all_labels()
    for e in entries:
        assert e.oracle in h.ORACLES, f"unknown oracle {e.oracle!r}"
        assert e.metric in h.METRICS, f"unknown metric {e.metric!r}"
        assert e.ours != e.theirs, f"{e.fingerprint}: not a divergence (ours == theirs)"
        assert e.case in known, f"{e.case!r} is neither a corpus case nor a snippet label"
        assert e.reason.strip(), f"{e.fingerprint}: empty reason"
        require(e.ruling)  # phantom ruling ID -> SpecError, same gate as src/


def _load_generator() -> object:
    path = h.REPO_ROOT / "tools" / "gen_divergences.py"
    spec = importlib.util.spec_from_file_location("gen_divergences", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_generated_divergence_doc_is_fresh() -> None:
    gen = _load_generator()
    committed = (h.REPO_ROOT / "docs" / "spec" / "divergences.md").read_text(encoding="utf-8")
    assert committed == gen.render(), (
        "docs/spec/divergences.md is stale — run: python tools/gen_divergences.py"
    )
