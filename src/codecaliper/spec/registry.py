"""The ruling registry: loads the versioned metric-to-syntax mapping spec.

Rulings are machine-readable TOML package data with immutable IDs
(``{METRIC}-{LANG}-{NNNN}``). ``require()`` raises :class:`SpecError` the moment
code cites a phantom ID, so the code and the spec cannot drift apart silently
(ARCHITECTURE.md §3.3).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any

from codecaliper.errors import SpecError

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - py3.10 fallback
    import tomli as tomllib

_RULING_FILES = (
    "core.toml",
    "tokenization.toml",
    "cyclomatic.toml",
    "cognitive.toml",
    "halstead.toml",
    "mi.toml",
    "loc.toml",
    "bw.toml",
)


@dataclass(frozen=True, slots=True)
class Ruling:
    id: str
    metric: str
    language: str  # "all" | "python" | "java" | ...
    title: str
    statement: str
    status: str = "active"  # active | draft | superseded
    since_spec: str = "0.1.0"
    mode: str = ""  # cognitive only: "whitepaper" | "sonar-compat" | "" (both)
    node_types: tuple[str, ...] = ()  # tree-sitter node types this ruling binds to
    examples: tuple[str, ...] = ()  # normative consistency-corpus case IDs
    superseded_by: str = ""


def _load_toml(name: str) -> dict[str, Any]:
    ref = resources.files("codecaliper.spec") / "rulings" / name
    with ref.open("rb") as f:
        data: dict[str, Any] = tomllib.load(f)
    return data


@lru_cache(maxsize=1)
def spec_version() -> str:
    return str(_load_toml("index.toml")["spec"]["version"])


@lru_cache(maxsize=1)
def _registry() -> dict[str, Ruling]:
    rulings: dict[str, Ruling] = {}
    for fname in _RULING_FILES:
        data = _load_toml(fname)
        for raw in data.get("ruling", []):
            r = Ruling(
                id=raw["id"],
                metric=raw["metric"],
                language=raw["language"],
                title=raw["title"],
                statement=raw["statement"].strip(),
                status=raw.get("status", "active"),
                since_spec=raw.get("since_spec", "0.1.0"),
                mode=raw.get("mode", ""),
                node_types=tuple(raw.get("node_types", [])),
                examples=tuple(raw.get("examples", [])),
                superseded_by=raw.get("superseded_by", ""),
            )
            if r.id in rulings:
                raise SpecError(f"duplicate ruling id {r.id!r} in {fname}")
            rulings[r.id] = r
    return rulings


def require(ruling_id: str) -> str:
    """Assert the ruling exists and return its ID (call at module import time)."""
    if ruling_id not in _registry():
        raise SpecError(
            f"code cites phantom ruling {ruling_id!r}; add it to the spec or fix the citation"
        )
    return ruling_id


def ruling(ruling_id: str) -> Ruling:
    try:
        return _registry()[ruling_id]
    except KeyError:
        raise SpecError(f"unknown ruling {ruling_id!r}") from None


def iter_rulings(metric: str | None = None, language: str | None = None) -> tuple[Ruling, ...]:
    out = []
    for r in _registry().values():
        if metric is not None and r.metric != metric:
            continue
        if language is not None and r.language not in (language, "all"):
            continue
        out.append(r)
    return tuple(out)
