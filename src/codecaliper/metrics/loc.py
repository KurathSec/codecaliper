"""Line counting (LOC-* rulings) — coverage measures over the token stream.

sloc counts lines covered by code-token spans, so multi-line strings count on
every line they span; this is exactly where the demoted regex lane provably
fails (ARCHITECTURE.md §6) and the corpus proves it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from codecaliper.languages.base import LanguageAdapter
from codecaliper.metrics.base import MetricContext
from codecaliper.spec import require
from codecaliper.syntax.tokens import LexicalToken, TokenKind

if TYPE_CHECKING:  # pragma: no cover
    from codecaliper.syntax._treesitter import Node

R_PHYSICAL = require("LOC-ALL-0001")
R_SLOC = require("LOC-ALL-0002")
R_CLOC = require("LOC-ALL-0003")
R_LLOC = require("LOC-ALL-0004")


def loc_metrics(
    lines: list[str],
    tokens: list[LexicalToken],
    root: Node,
    adapter: LanguageAdapter,
    ctx: MetricContext,
) -> dict[str, int]:
    physical = len(lines)
    blank = sum(1 for ln in lines if not ln.strip())

    code_lines: set[int] = set()
    comment_lines: set[int] = set()
    for tok in tokens:
        target = comment_lines if tok.kind is TokenKind.COMMENT else code_lines
        for line in range(tok.line, tok.end_line + 1):
            target.add(line)

    from codecaliper.syntax._treesitter import is_opaque

    lloc = 0
    stack = [root]
    while stack:
        node = stack.pop()
        if is_opaque(node):
            continue  # CORE-ALL-0002: ERROR/MISSING subtrees are opaque
        if node.type in adapter.statement_types and ctx.in_range(node):
            lloc += int(ctx.count(R_LLOC, node, 1, metric="lloc"))
        stack.extend(reversed(node.children))

    return {
        "physical_lines": physical,
        "blank_lines": blank,
        "sloc": len(code_lines),
        "comment_lines": len(comment_lines),
        "lloc": lloc,
    }
