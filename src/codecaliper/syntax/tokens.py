"""The unified lexical token stream (TOK-* rulings).

Derived from the tree-sitter leaf walk (with atomic-token subtrees) and
classified by the adapter's token tables. This one stream feeds the BW
readability features, lexical Halstead, and the LOC coverage counts — one
tokenizer, three consumers, zero drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from codecaliper.model import Diagnostic

if TYPE_CHECKING:  # pragma: no cover
    from codecaliper.languages.base import LanguageAdapter
    from codecaliper.syntax._treesitter import Tree


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


def normalize(source: str | bytes) -> tuple[str, tuple[Diagnostic, ...]]:
    """Input normalization per TOK-ALL-0001..0003."""
    diags: list[Diagnostic] = []
    if isinstance(source, bytes):
        text = source.decode("utf-8", errors="replace")
        if "�" in text:
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


def lex(
    tree: Tree,
    source_bytes: bytes,
    adapter: LanguageAdapter,
    *,
    include_error_tokens: bool = False,
) -> list[LexicalToken]:
    """Classify the leaf stream via the adapter's token tables.

    ``include_error_tokens=True`` descends into ERROR subtrees (BW-ALL-0007:
    the BW construct is lexical); the default stream is error-opaque
    (CORE-ALL-0002) and feeds every metric.
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
        elif not node.is_named and text in adapter.soft_keywords:
            kind = TokenKind.IDENTIFIER  # soft keywords are identifiers (BW-PY-0001)
        elif node.is_named:
            kind = TokenKind.OTHER
        elif text in _PUNCT:
            kind = TokenKind.PUNCT
        else:
            kind = TokenKind.OPERATOR
        out.append(LexicalToken(kind, text, line, end_line))
    return out
