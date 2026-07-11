"""CLI contract tests: subcommand output content, flag behavior, exit codes,
and error paths — asserted against independent expectations, never against the
program's own output (ARCHITECTURE.md §9).
"""

from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from codecaliper._version import __version__
from codecaliper.readability.bw2010 import BW_FEATURE_ORDER_SHA
from codecaliper.readability.retrain import ModelArtifact, new_artifact_metadata
from codecaliper.spec import spec_version

REPO = Path(__file__).resolve().parent.parent


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "codecaliper.cli", *args],
        capture_output=True, text=True, check=False,
    )


@pytest.fixture
def sample(tmp_path: Path) -> Path:
    f = tmp_path / "sample.py"
    f.write_text("def f(a):\n    if a:\n        return 1\n    return 0\n")
    return f


def test_json_output_content(sample: Path) -> None:
    r = run_cli(str(sample), "--json")
    assert r.returncode == 0
    rep = json.loads(r.stdout)
    assert rep["parse_ok"] is True
    fm = {m["metric"]: m["value"] for m in rep["file_metrics"]}
    assert fm["cyclomatic"] == 2  # 1 + if — independent hand expectation
    assert rep["provenance"]["spec_version"] == spec_version()
    assert rep["provenance"]["language"] == "python"
    assert rep["provenance"]["grammar"]["validated"] is True


def test_csv_output_content(sample: Path) -> None:
    r = run_cli(str(sample), "--csv")
    assert r.returncode == 0
    rows = list(csv.DictReader(io.StringIO(r.stdout)))
    file_rows = [row for row in rows if row["scope"] == "file"]
    assert len(file_rows) == 1
    assert float(file_rows[0]["cyclomatic"]) == 2.0
    assert file_rows[0]["spec_version"] == spec_version()
    assert file_rows[0]["cognitive_mode"] == "whitepaper"


def test_json_csv_mutually_exclusive(sample: Path) -> None:
    r = run_cli(str(sample), "--json", "--csv")
    assert r.returncode == 1
    assert "not allowed with" in r.stderr


def test_missing_file_is_clean_error() -> None:
    r = run_cli("/nonexistent/x.py")
    assert r.returncode == 1
    assert "Traceback" not in r.stderr
    assert "error" in r.stderr


def test_unwritable_output_is_clean_error(sample: Path) -> None:
    r = run_cli(str(sample), "-o", "/nonexistent-dir/out.json")
    assert r.returncode == 1
    assert "Traceback" not in r.stderr
    assert "error" in r.stderr


def test_output_file_written(sample: Path, tmp_path: Path) -> None:
    """The happy path of -o: exit 0, nothing on stdout, and the file holds the
    same report the terminal would have shown."""
    out = tmp_path / "out.json"
    r = run_cli(str(sample), "--json", "-o", str(out))
    assert r.returncode == 0
    assert r.stdout == ""
    rep = json.loads(out.read_text())
    assert rep["parse_ok"] is True
    fm = {m["metric"]: m["value"] for m in rep["file_metrics"]}
    assert fm["cyclomatic"] == 2


def test_strict_exit_code(sample: Path, tmp_path: Path) -> None:
    broken = tmp_path / "broken.py"
    broken.write_text("def broken(:\n    pass\n")
    assert run_cli(str(broken)).returncode == 0  # measured-and-labelled
    assert run_cli(str(broken), "--strict").returncode == 2


def test_sonar_compat_flag_changes_mode_and_value(tmp_path: Path) -> None:
    rec = tmp_path / "rec.py"
    rec.write_text("def walk(n):\n    if n <= 0:\n        return 0\n    return walk(n - 1)\n")
    wp = json.loads(run_cli(str(rec), "--json").stdout)
    sc = json.loads(run_cli(str(rec), "--json", "--sonar-compat").stdout)
    wp_cog = next(m["value"] for m in wp["file_metrics"] if m["metric"] == "cognitive")
    sc_cog = next(m["value"] for m in sc["file_metrics"] if m["metric"] == "cognitive")
    assert (wp_cog, sc_cog) == (2, 1)  # recursion +1 is whitepaper-only
    assert sc["provenance"]["modes"]["cognitive"] == "sonar-compat"


def test_spec_subcommands() -> None:
    assert run_cli("spec", "version").stdout.strip() == spec_version()
    show = run_cli("spec", "show", "CC-PY-0003")
    assert show.returncode == 0
    assert "CC-PY-0003" in show.stdout and "boolean" in show.stdout.lower()
    superseded = run_cli("spec", "show", "TOK-ALL-0004").stdout
    assert "superseded by: TOK-ALL-0006" in superseded
    phantom = run_cli("spec", "show", "CC-PY-9999")
    assert phantom.returncode == 1
    listed = run_cli("spec", "list", "--metric", "cyclomatic", "--lang", "java").stdout
    assert "CC-JAVA-0001" in listed and "CC-PY-0001" not in listed


def test_env_and_cite_content() -> None:
    env = run_cli("env").stdout
    assert f"codecaliper {__version__}" in env
    assert f"spec {spec_version()}" in env
    cite = run_cli("cite").stdout
    assert __version__ in cite and spec_version() in cite


def test_model_artifact_roundtrip_and_refusal(tmp_path: Path) -> None:
    """The feature-order-sha refusal is an honesty invariant: a model trained
    against a different canonical order must refuse to predict."""
    meta = new_artifact_metadata(
        trained_granularity="snippet", trained_language="java",
        dataset_id="test-dataset", protocol="test-protocol", seed=7,
    )
    art = ModelArtifact(coefficients=(0.1,) * 25, intercept=-0.5, **meta)  # type: ignore[arg-type]
    p = tmp_path / "model.json"
    art.save(str(p))
    loaded = ModelArtifact.load(str(p))
    assert loaded == art
    assert loaded.feature_order_sha == BW_FEATURE_ORDER_SHA
    assert loaded.spec_version == spec_version()

    data = json.loads(p.read_text())
    data["feature_order_sha"] = "0" * 64
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(data))
    from codecaliper.errors import SpecError

    with pytest.raises(SpecError, match="feature order"):
        ModelArtifact.load(str(bad))
