"""TEST-ONLY internal oracle: the stdlib Buse-Weimer feature reference.

Verbatim port of ``bw_readability_features`` (and its helpers) from Spaghetti
Architect ``bench/anchor.py`` (MIT, same author — see NOTICE; cite DOI
10.5281/zenodo.21033174). It is the per-PR differential witness for the
tree-sitter BW port (tests/test_bw_port_fidelity.py) and must never be imported
from src/ (anti-salami boundary, ARCHITECTURE.md §1 invariant 3).

Known, ruled divergences from the tree-sitter lane (do not "fix" them here):
- TOK-PY-0001: on CPython 3.12+ tokenize (PEP 701) f-string interpolation
  contents are tokenized; the tree-sitter lane consumes strings atomically.
  Fidelity tests therefore avoid f-strings with interpolations.
- BW-PY-0001: soft keywords (match/case) are NAME tokens here and identifiers
  in both lanes — consistent; avoid match statements anyway for clarity.
"""

from __future__ import annotations

import io
import keyword
import tokenize

_PY_KEYWORDS = frozenset(keyword.kwlist)
_ARITH_OPS = frozenset(["+", "-", "*", "/", "//", "%", "**", "@"])
_COMPARE_OPS = frozenset(["==", "!=", "<", ">", "<=", ">=", "<>"])
_ASSIGN_OPS = frozenset(["=", "+=", "-=", "*=", "/=", "//=", "%=", "**=",
                         "&=", "|=", "^=", ">>=", "<<=", "@=", ":="])
_BRANCH_KW = frozenset(["if", "elif"])
_LOOP_KW = frozenset(["for", "while"])

_BW_FEATURE_NAMES = (
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


def _bw_tokens_by_line(src: str) -> dict[int, list]:
    out: dict[int, list] = {}
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
        return out
    _skip = {tokenize.ENCODING, tokenize.ENDMARKER, tokenize.NEWLINE,
             tokenize.NL, tokenize.INDENT, tokenize.DEDENT}
    for tok in toks:
        if tok.type in _skip:
            continue
        out.setdefault(tok.start[0], []).append((tok.type, tok.string))
    return out


def bw_readability_features(src: str) -> dict[str, float]:
    """The 25 Buse-Weimer (2010) Fig. 6 readability features (stdlib only)."""
    lines = src.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    n_lines = max(1, len(lines))
    by_line = _bw_tokens_by_line(src)

    line_len: list[int] = []
    indent: list[int] = []
    ident_per_line: list[int] = []
    ident_len_per_line: list[int] = []
    kw_per_line: list[int] = []
    num_per_line: list[int] = []
    comments = periods = commas = spaces = parens = 0
    arith = compare = assign = branch = loop = blank = 0
    char_freq: dict[str, int] = {}
    ident_freq: dict[str, int] = {}

    for i, line in enumerate(lines, start=1):
        line_len.append(len(line))
        stripped = line.lstrip()
        indent.append(len(line) - len(stripped))
        spaces += line.count(" ")
        if stripped == "":
            blank += 1
        for ch in line:
            char_freq[ch] = char_freq.get(ch, 0) + 1

        ids_here = 0
        id_lens_here = [0]
        kw_here = num_here = 0
        for ttype, tstr in by_line.get(i, ()):
            if ttype == tokenize.NAME:
                if tstr in _PY_KEYWORDS:
                    kw_here += 1
                    if tstr in _BRANCH_KW:
                        branch += 1
                    elif tstr in _LOOP_KW:
                        loop += 1
                else:
                    ids_here += 1
                    id_lens_here.append(len(tstr))
                    ident_freq[tstr] = ident_freq.get(tstr, 0) + 1
            elif ttype == tokenize.NUMBER:
                num_here += 1
            elif ttype == tokenize.COMMENT:
                comments += 1
            elif ttype == tokenize.OP:
                if tstr == ",":
                    commas += 1
                elif tstr == ".":
                    periods += 1
                elif tstr in ("(", ")"):
                    parens += 1
                if tstr in _ASSIGN_OPS:
                    assign += 1
                elif tstr in _COMPARE_OPS:
                    compare += 1
                elif tstr in _ARITH_OPS:
                    arith += 1
        ident_per_line.append(ids_here)
        ident_len_per_line.append(max(id_lens_here))
        kw_per_line.append(kw_here)
        num_per_line.append(num_here)

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
