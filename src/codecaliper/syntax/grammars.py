"""Grammar loading and the calibration check (ARCHITECTURE.md §10).

A deviating installed grammar version never refuses to run. It is stamped
``GrammarInfo.validated=False`` and every report carries an
``unvalidated-grammar`` diagnostic. Run and label it; never refuse, and never
silently trust.
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

@lru_cache(maxsize=1)
def validated_versions() -> dict[str, str]:
    ref = resources.files("codecaliper.spec") / "validated_grammars.toml"
    with ref.open("rb") as f:
        return dict(tomllib.load(f)["grammars"])


@cache
def load(language_name: str, module: str) -> tuple[ts.Language, ts.Parser, GrammarInfo]:
    """Load a pinned grammar. ``module`` is the tree-sitter package name, which
    the adapter owns (``LanguageAdapter.grammar_module``): the set of languages
    lives only in the ``languages/`` registry and is not duplicated here."""
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
