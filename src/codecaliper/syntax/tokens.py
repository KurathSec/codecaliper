"""The unified lexical token stream (TOK-* rulings).

Derived from the tree-sitter leaf walk (with atomic-token subtrees) and
classified by the adapter's token tables. This one stream feeds the BW
readability features, lexical Halstead, and the LOC coverage counts — one
tokenizer, three consumers, zero drift.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from codecaliper.model import Diagnostic
from codecaliper.spec import iter_rulings, require

if TYPE_CHECKING:  # pragma: no cover
    from codecaliper.languages.base import LanguageAdapter
    from codecaliper.syntax._treesitter import Tree

R_ANON_WORD = require("TOK-ALL-0007")  # anonymous word tokens are identifiers


class TokenKind(Enum):
    IDENTIFIER = "identifier"
    KEYWORD = "keyword"
    NUMBER = "number"
    STRING = "string"
    COMMENT = "comment"
    OPERATOR = "operator"
    PUNCT = "punct"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class LexicalToken:
    kind: TokenKind
    text: str
    line: int  # 1-based physical line of the token start (TOK-ALL-0005)
    end_line: int  # 1-based line of the token end (span coverage for sloc/cloc)


_PUNCT = frozenset({"(", ")", "[", "]", "{", "}", ",", ".", ";", ":"})

# Word-shaped anonymous tokens (TOK-ALL-0007): identifier-shaped, with internal
# hyphens allowed for Java's hyphenated contextual keyword (`non-sealed`).
_WORD_RE = re.compile(r"[^\W\d]\w*(?:-\w+)*", re.UNICODE)


def normalize(source: str | bytes) -> tuple[str, tuple[Diagnostic, ...]]:
    """Input normalization per TOK-ALL-0001..0003."""
    diags: list[Diagnostic] = []
    if isinstance(source, bytes):
        # the diagnostic fires only when replacement actually happened — valid
        # UTF-8 that legitimately contains U+FFFD is not flagged
        try:
            text = source.decode("utf-8")
        except UnicodeDecodeError:
            text = source.decode("utf-8", errors="replace")
            diags.append(
                Diagnostic("warning", "encoding-replaced",
                           "undecodable bytes replaced with U+FFFD", ruling="TOK-ALL-0001")
            )
    else:
        text = source
    if text.startswith("﻿"):
        text = text[1:]
        diags.append(
            Diagnostic("info", "bom-stripped", "leading UTF-8 BOM stripped", ruling="TOK-ALL-0002")
        )
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text, tuple(diags)


def source_lines(text: str) -> list[str]:
    """Physical lines; a trailing final newline does not create an extra empty
    line (LOC-ALL-0001, and the BW reference's convention)."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return lines


def lang_tokenization_rulings(adapter: LanguageAdapter) -> tuple[str, ...]:
    """The language's STATIC tokenization rulings: the atomic-string rules
    (TOK-PY-0002 / TOK-JAVA-0001) that unconditionally govern how the stream is
    cut, so every token-derived value cites them. Construct-specific
    classification rulings (``adapter.conditional_token_rulings``, e.g.
    TOK-JAVA-0002) are excluded — they are cited per-occurrence, like the
    language-neutral TOK-ALL-0007, not statically."""
    conditional = set(adapter.conditional_token_rulings.values())
    return tuple(sorted(
        r.id
        for r in iter_rulings(metric="tokenization", language=adapter.name)
        if r.language == adapter.name and r.status == "active"
        and r.id not in conditional
    ))


def lex(
    tree: Tree,
    source_bytes: bytes,
    adapter: LanguageAdapter,
    *,
    include_error_tokens: bool = False,
    cond_lines: dict[str, set[int]] | None = None,
) -> list[LexicalToken]:
    """Classify the leaf stream via the adapter's token tables.

    ``include_error_tokens=True`` descends into ERROR subtrees (BW-ALL-0007:
    the BW construct is lexical); the default stream is error-opaque
    (CORE-ALL-0002) and feeds every metric. ``cond_lines``, when given, records
    for each conditional tokenization ruling the physical lines where it
    engaged (TOK-ALL-0007 anonymous words; the adapter's
    ``conditional_token_rulings``, e.g. TOK-JAVA-0002 `_`), so provenance can
    cite it per-occurrence and per-unit rather than file-globally.
    """
    from codecaliper.syntax._treesitter import leaves, leaves_lexical, node_text

    iterator = leaves_lexical if include_error_tokens else leaves
    out: list[LexicalToken] = []
    for node in iterator(tree, adapter.atomic_types):
        ttype = node.type
        if ttype in ("ERROR",) or node.is_missing:
            continue
        text = node_text(node, source_bytes)
        if not text:
            continue
        line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        if ttype in adapter.comment_types:
            kind = TokenKind.COMMENT
        elif ttype in adapter.string_types:
            kind = TokenKind.STRING
        elif ttype in adapter.number_types:
            kind = TokenKind.NUMBER
        elif ttype in adapter.keyword_leaf_types or text in adapter.keywords:
            kind = TokenKind.KEYWORD
        elif ttype in adapter.identifier_types:
            kind = TokenKind.IDENTIFIER
        elif ttype in adapter.operator_leaf_types:
            # named leaves that are operator tokens (Python `...`, TOK-PY-0003),
            # so they are not swallowed by the is_named -> OTHER fallthrough
            kind = TokenKind.OPERATOR
        elif not node.is_named and text in adapter.soft_keywords:
            kind = TokenKind.IDENTIFIER  # soft keywords are identifiers (BW-PY-0001)
        elif not node.is_named and _WORD_RE.fullmatch(text) is not None:
            # TOK-ALL-0007: anonymous word tokens outside the keyword table are
            # identifiers (Python `__future__`, Java contextual keywords) —
            # matching the reference tokenizers, which yield NAME for them.
            kind = TokenKind.IDENTIFIER
            if cond_lines is not None:
                cond_lines.setdefault(R_ANON_WORD, set()).add(line)
        elif node.is_named:
            kind = TokenKind.OTHER
        elif text in _PUNCT:
            kind = TokenKind.PUNCT
        else:
            kind = TokenKind.OPERATOR
        if cond_lines is not None and ttype in adapter.conditional_token_rulings:
            cond_lines.setdefault(adapter.conditional_token_rulings[ttype], set()).add(line)
        out.append(LexicalToken(kind, text, line, end_line))
    return out
