"""Cyclomatic complexity: 1 + decision points over NodeClass (CC-* rulings)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from codecaliper.languages.base import LanguageAdapter, NodeClass
from codecaliper.metrics.base import MetricContext
from codecaliper.spec import require

if TYPE_CHECKING:  # pragma: no cover
    from codecaliper.syntax._treesitter import Node

R_BASE = require("CC-ALL-0001")

_DECISION_CLASSES = frozenset(
    {
        NodeClass.BRANCH,
        NodeClass.ELIF_CONTINUATION,
        NodeClass.LOOP,
        NodeClass.CATCH,
        NodeClass.CASE_LABEL,
        NodeClass.TERNARY,
        NodeClass.COMPREHENSION_GUARD,
        NodeClass.BOOL_OP,
    }
)


def cyclomatic(
    root: Node,
    adapter: LanguageAdapter,
    ctx: MetricContext,
    *,
    exclude_nested_units: bool = False,
) -> int:
    """Decision points in ``root``'s subtree (root itself excluded from unit
    exclusion so a function node can be measured as a unit, CORE-ALL-0003)."""
    from codecaliper.syntax._treesitter import is_opaque

    total = 1
    stack = list(reversed(root.children))
    while stack:
        node = stack.pop()
        if is_opaque(node):
            continue  # CORE-ALL-0002: ERROR/MISSING subtrees are opaque
        c = adapter.classify(node)
        if c is not None:
            if exclude_nested_units and c.node_class in (
                NodeClass.FUNCTION_DEF,
                NodeClass.CLASS_DEF,
            ):
                continue  # nested units get their own reports (CORE-ALL-0003)
            if c.node_class in _DECISION_CLASSES and ctx.in_range(node):
                for r in c.rulings:
                    if r.startswith("CC-"):
                        total += int(ctx.count(r, node, 1, metric="cyclomatic"))
                        break
        stack.extend(reversed(node.children))
    return total
