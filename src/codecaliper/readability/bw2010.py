"""The 25 Buse-Weimer (2010, Fig. 6) readability features on tree-sitter.

Canonical feature names and order are inherited verbatim from the reference
implementation (Spaghetti Architect bench/anchor.py::_BW_FEATURE_NAMES,
NOTICE-credited); tests/test_bw_port_fidelity.py holds this port to the stdlib
reference per feature. Output is always the raw vector; there is no score
(BW-ALL-0001).

Two feature families (BW-ALL-0004):
- raw-line facts (length, indentation, spaces, blanks, char frequency) from the
  normalized text of every line, strings included;
- token facts (identifiers, keywords, numbers, comments, operator classes,
  punctuation) from the unified LexicalToken stream, so string/comment contents
  are invisible to them.
"""

from __future__ import annotations

import hashlib

from codecaliper.languages.base import LanguageAdapter
from codecaliper.spec import require
from codecaliper.syntax.tokens import LexicalToken, TokenKind

R_FEATURES = require("BW-ALL-0001")
R_GRANULARITY = require("BW-ALL-0002")
R_COMMENT_ONCE = require("BW-ALL-0003")
R_TOKEN_LEVEL = require("BW-ALL-0004")
R_ID_LENGTH = require("BW-ALL-0005")
R_OP_CLASSES = require("BW-ALL-0006")

#: Fig. 6 order, verbatim from the reference implementation.
BW_FEATURE_NAMES: tuple[str, ...] = (
    "avg_line_length", "max_line_length",
    "avg_identifiers", "max_identifiers",
    "avg_identifier_length", "max_identifier_length",
    "avg_indentation", "max_indentation",
    "avg_keywords", "max_keywords",
    "avg_numbers", "max_numbers",
    "avg_comments", "avg_periods", "avg_commas", "avg_spaces",
    "avg_parentheses", "avg_arithmetic_ops", "avg_comparison_ops",
    "avg_assignments", "avg_branches", "avg_loops", "avg_blank_lines",
    "max_char_occurrences", "max_identifier_occurrences",
)

#: Feature-order integrity stamp for trained-model artifacts (ARCHITECTURE.md §7.2).
BW_FEATURE_ORDER_SHA: str = hashlib.sha256(",".join(BW_FEATURE_NAMES).encode()).hexdigest()

#: The rulings in force for every bw2010 vector.
BW_RULINGS: tuple[str, ...] = (
    R_FEATURES, R_GRANULARITY, R_COMMENT_ONCE, R_TOKEN_LEVEL, R_ID_LENGTH, R_OP_CLASSES,
)

#: This tool's calibrated-regime diagnostic window (BW-ALL-0002; the paper
#: states no line range — see the ruling's 1.2.1 editorial note).
CALIBRATED_LINE_RANGE = (4, 11)


def bw_features(
    lines: list[str], tokens: list[LexicalToken], adapter: LanguageAdapter
) -> dict[str, float]:
    """Compute the 25 features. ``tokens`` line numbers must be 1-based relative
    to ``lines`` (granularity slicing rebases them)."""
    n_lines = max(1, len(lines))

    line_len: list[int] = []
    indent: list[int] = []
    spaces = 0
    blank = 0
    char_freq: dict[str, int] = {}
    for line in lines:
        line_len.append(len(line))
        stripped = line.lstrip()
        # TOK-ALL-0006 (supersedes TOK-ALL-0004): a tab counts as 8 indentation
        # characters, arbitrated by the BW faithfulness experiment. Line length
        # above stays a raw character count.
        leading = line[: len(line) - len(stripped)]
        indent.append(sum(8 if ch == "\t" else 1 for ch in leading))
        spaces += line.count(" ")
        if stripped == "":
            blank += 1
        for ch in line:
            char_freq[ch] = char_freq.get(ch, 0) + 1

    ident_per_line = [0] * len(lines)
    ident_len_per_line = [0] * len(lines)  # per-line max identifier length (BW-ALL-0005)
    kw_per_line = [0] * len(lines)
    num_per_line = [0] * len(lines)
    comments = periods = commas = parens = 0
    arith = compare = assign = branch = loop = 0
    ident_freq: dict[str, int] = {}

    for tok in tokens:
        i = tok.line - 1
        if not (0 <= i < len(lines)):
            continue
        if tok.kind is TokenKind.IDENTIFIER:
            ident_per_line[i] += 1
            ident_len_per_line[i] = max(ident_len_per_line[i], len(tok.text))
            ident_freq[tok.text] = ident_freq.get(tok.text, 0) + 1
        elif tok.kind is TokenKind.KEYWORD:
            kw_per_line[i] += 1
            if tok.text in adapter.branch_keywords:
                branch += 1
            elif tok.text in adapter.loop_keywords:
                loop += 1
        elif tok.kind is TokenKind.NUMBER:
            num_per_line[i] += 1
        elif tok.kind is TokenKind.COMMENT:
            comments += 1  # once per token (BW-ALL-0003, provisional)
        elif tok.kind in (TokenKind.OPERATOR, TokenKind.PUNCT):
            if tok.text == ",":
                commas += 1
            elif tok.text == ".":
                periods += 1
            elif tok.text in ("(", ")"):
                parens += 1
            if tok.text in adapter.assignment_ops:
                assign += 1
            elif tok.text in adapter.comparison_ops:
                compare += 1
            elif tok.text in adapter.arithmetic_ops:
                arith += 1

    def _avg(xs: list[int]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    def _max(xs: list[int]) -> float:
        return float(max(xs)) if xs else 0.0

    return {
        "avg_line_length": _avg(line_len),
        "max_line_length": _max(line_len),
        "avg_identifiers": _avg(ident_per_line),
        "max_identifiers": _max(ident_per_line),
        "avg_identifier_length": _avg(ident_len_per_line),
        "max_identifier_length": _max(ident_len_per_line),
        "avg_indentation": _avg(indent),
        "max_indentation": _max(indent),
        "avg_keywords": _avg(kw_per_line),
        "max_keywords": _max(kw_per_line),
        "avg_numbers": _avg(num_per_line),
        "max_numbers": _max(num_per_line),
        "avg_comments": comments / n_lines,
        "avg_periods": periods / n_lines,
        "avg_commas": commas / n_lines,
        "avg_spaces": spaces / n_lines,
        "avg_parentheses": parens / n_lines,
        "avg_arithmetic_ops": arith / n_lines,
        "avg_comparison_ops": compare / n_lines,
        "avg_assignments": assign / n_lines,
        "avg_branches": branch / n_lines,
        "avg_loops": loop / n_lines,
        "avg_blank_lines": blank / n_lines,
        "max_char_occurrences": float(max(char_freq.values(), default=0)),
        "max_identifier_occurrences": float(max(ident_freq.values(), default=0)),
    }
