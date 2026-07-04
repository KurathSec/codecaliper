"""The spec-drift gate (ARCHITECTURE.md §3.2): every metric value over the
whole corpus is snapshotted with its spec + grammar versions; ANY numeric drift
while the snapshot's spec MAJOR matches the current one is a red build. Refresh
only via tools/update_snapshot.py --confirm-spec-bump.
"""

from __future__ import annotations

import json
import math

import pytest
from conftest import SNAPSHOT_PATH
from tools_snapshot import compute_corpus_values  # tests/tools_snapshot.py

from codecaliper.spec import spec_version


def test_snapshot_exists() -> None:
    assert SNAPSHOT_PATH.exists(), (
        "tests/snapshots/corpus_values.json missing — run tools/update_snapshot.py"
    )


def test_no_silent_numeric_drift() -> None:
    if not SNAPSHOT_PATH.exists():
        pytest.skip("no snapshot yet")
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    current_major = spec_version().split(".")[0]
    snap_major = str(snapshot["spec_version"]).split(".")[0]
    if snap_major != current_major:
        pytest.skip("spec major bumped; regenerate the snapshot deliberately")
    live = compute_corpus_values()
    for case_id, values in snapshot["values"].items():
        assert case_id in live, f"corpus case {case_id} disappeared"
        for key, expected in values.items():
            actual = live[case_id][key]
            if isinstance(expected, float):
                ok = math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9)
            else:
                ok = actual == expected
            assert ok, (
                f"SPEC DRIFT: {case_id}::{key} changed {expected} -> {actual} under "
                f"spec {spec_version()} — a numeric change requires a spec MAJOR "
                "bump (tools/update_snapshot.py --confirm-spec-bump)"
            )
