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
    # The gate may never silently disarm itself: a spec bump (major OR minor)
    # is red until the snapshot is deliberately regenerated at the new version,
    # and every corpus case must be snapshotted — otherwise values could drift
    # freely in the regeneration gap / on uncovered cases.
    assert str(snapshot["spec_version"]) == spec_version(), (
        f"snapshot is stamped spec {snapshot['spec_version']} but the current "
        f"spec is {spec_version()} — regenerate it deliberately via "
        "tools/update_snapshot.py (with --confirm-spec-bump iff values changed)"
    )
    live = compute_corpus_values()
    unsnapshotted = set(live) - set(snapshot["values"])
    assert not unsnapshotted, (
        f"corpus cases missing from the snapshot: {sorted(unsnapshotted)} — "
        "run tools/update_snapshot.py"
    )
    for case_id, values in snapshot["values"].items():
        assert case_id in live, f"corpus case {case_id} disappeared"
        # key-set equality, not subset: a hand-edited/merge-mangled snapshot
        # that lost per-case keys would otherwise silently narrow the gate,
        # and a new live metric would never enter it
        assert set(values) == set(live[case_id]), (
            f"{case_id}: snapshot/live metric key sets differ "
            f"(only in snapshot: {sorted(set(values) - set(live[case_id]))}, "
            f"only live: {sorted(set(live[case_id]) - set(values))}) — "
            "regenerate via tools/update_snapshot.py"
        )
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
