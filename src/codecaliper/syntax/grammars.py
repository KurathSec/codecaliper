"""Grammar loading and the calibration check (ARCHITECTURE.md §10).

A deviating installed grammar version never refuses to run — it is stamped
``GrammarInfo.validated=False`` and every report carries an
``unvalidated-grammar`` diagnostic. Run and label, never refuse, never silently
trust.
"""

from __future__ import annotations

import sys
from functools import cache, lru_cache
from importlib import resources

from codecaliper.model import GrammarInfo
from codecaliper.syntax import _treesitter as ts

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - py3.10 fallback
    import tomli as tomllib

_GRAMMAR_MODULES = {"python": "tree_sitter_python", "java": "tree_sitter_java"}


@lru_cache(maxsize=1)
def validated_versions() -> dict[str, str]:
    ref = resources.files("codecaliper.spec") / "validated_grammars.toml"
    with ref.open("rb") as f:
        return dict(tomllib.load(f)["grammars"])


@cache
def load(language_name: str) -> tuple[ts.Language, ts.Parser, GrammarInfo]:
    module = _GRAMMAR_MODULES[language_name]
    lang, version, abi = ts.load_language(module)
    parser = ts.make_parser(lang)
    info = GrammarInfo(
        language=language_name,
        package=module.replace("_", "-"),
        version=version,
        abi_version=abi,
        validated=(validated_versions().get(language_name) == version),
    )
    return lang, parser, info
