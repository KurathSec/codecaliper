"""Typed error taxonomy. Nothing else escapes the public facade."""

from __future__ import annotations


class CodecaliperError(Exception):
    """Base class for all codecaliper errors."""


class UnsupportedLanguageError(CodecaliperError):
    """The requested language has no registered adapter."""


class LanguageDetectionError(CodecaliperError):
    """--lang auto could not map the file extension; never guess (spec CORE-ALL-0005)."""


class GrammarLoadError(CodecaliperError):
    """A tree-sitter grammar wheel could not be imported or wrapped."""


class SpecError(CodecaliperError):
    """The ruling registry is unreadable, or code cited a phantom ruling ID."""


class StrictParseError(CodecaliperError):
    """--strict was set and the parse tree contains ERROR/MISSING nodes (CORE-ALL-0002)."""
