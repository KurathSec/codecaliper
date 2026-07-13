"""Language adapter registry: a plain dict, deliberately (ARCHITECTURE.md §14:
entry-point plugin discovery is deferred until a third-party adapter exists)."""

from __future__ import annotations

from functools import cache

from codecaliper.errors import LanguageDetectionError, UnsupportedLanguageError
from codecaliper.languages.base import LanguageAdapter
from codecaliper.spec import require

_BUILTIN = ("python", "java")

R_LANG_AUTO = require("CORE-ALL-0005")  # extension map, never a guess


@cache
def get_adapter(name: str) -> LanguageAdapter:
    if name == "python":
        from codecaliper.languages.python import PythonAdapter

        return PythonAdapter()
    if name == "java":
        from codecaliper.languages.java import JavaAdapter

        return JavaAdapter()
    raise UnsupportedLanguageError(
        f"no adapter for language {name!r}; available: {', '.join(_BUILTIN)}"
    )


def available_languages() -> tuple[str, ...]:
    return _BUILTIN


def detect_language(path: str) -> str:
    """--lang auto: extension map with an explicit error, never a guess."""
    lower = path.lower()
    for name in _BUILTIN:
        if any(lower.endswith(ext) for ext in get_adapter(name).file_extensions):
            return name
    raise LanguageDetectionError(
        f"cannot detect language of {path!r} from its extension; pass --lang explicitly"
    )
