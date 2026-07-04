"""Lexical Halstead over the unified token stream (HAL-ALL-0001).

Deliberately uniform cross-language: operators are OPERATOR/KEYWORD/PUNCT
tokens, operands are IDENTIFIER/NUMBER/STRING tokens. Absolute values are
implementation-defined (only trends/ratios are stable); every emitted value
carries the halstead-approximation diagnostic. The divergence vs AST-harvest
implementations (radon, the stdlib reference lane) is classified.
"""

from __future__ import annotations

import math

from codecaliper.model import Diagnostic
from codecaliper.spec import require
from codecaliper.syntax.tokens import LexicalToken, TokenKind

R_LEXICAL = require("HAL-ALL-0001")

APPROX_DIAGNOSTIC = Diagnostic(
    severity="info",
    code="halstead-approximation",
    message="Halstead values are a lexical approximation; absolute values are "
    "implementation-defined, only trends/ratios are stable (HAL-ALL-0001).",
    ruling=R_LEXICAL,
)

_OPERATOR_KINDS = frozenset({TokenKind.OPERATOR, TokenKind.KEYWORD, TokenKind.PUNCT})
_OPERAND_KINDS = frozenset({TokenKind.IDENTIFIER, TokenKind.NUMBER, TokenKind.STRING})


def halstead(tokens: list[LexicalToken]) -> dict[str, float]:
    operators: list[str] = []
    operands: list[str] = []
    for tok in tokens:
        if tok.kind in _OPERATOR_KINDS:
            operators.append(tok.text)
        elif tok.kind in _OPERAND_KINDS:
            operands.append(tok.text)
    n1, big_n1 = len(set(operators)), len(operators)
    n2, big_n2 = len(set(operands)), len(operands)
    n, big_n = n1 + n2, big_n1 + big_n2
    volume = big_n * math.log2(n) if n > 0 else 0.0
    difficulty = (n1 / 2) * (big_n2 / n2) if n2 > 0 else 0.0
    effort = difficulty * volume
    return {
        "halstead.n1": float(n1),
        "halstead.N1": float(big_n1),
        "halstead.n2": float(n2),
        "halstead.N2": float(big_n2),
        "halstead.volume": volume,
        "halstead.difficulty": difficulty,
        "halstead.effort": effort,
    }
