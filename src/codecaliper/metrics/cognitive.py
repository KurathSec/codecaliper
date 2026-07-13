"""Cognitive complexity: ONE walker, dual mode (COG-* rulings).

Default mode is whitepaper-faithful; sonar-compat matches the deployed
Sonar-lineage implementations where they diverge from the paper text. The only
seed divergence is the recursion increment (COG-ALL-0005 whitepaper /
COG-ALL-0006 sonar-compat); every future divergence must arrive as a new
mode-tagged ruling pair, keeping the spec table the authoritative mode diff.

The chain-flattening walk generalizes the proven ``_traverse`` walker from
Spaghetti Architect's eval/metrics.py onto tree-sitter (NOTICE-credited).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from codecaliper.languages.base import LanguageAdapter, NodeClass
from codecaliper.metrics.base import MetricContext
from codecaliper.spec import require

if TYPE_CHECKING:  # pragma: no cover
    from codecaliper.syntax._treesitter import Node

R_STRUCT = require("COG-ALL-0001")
R_HYBRID = require("COG-ALL-0002")
R_BOOLSEQ = require("COG-ALL-0003")
R_NESTING = require("COG-ALL-0004")
R_RECURSION_WP = require("COG-ALL-0005")
R_NO_RECURSION_SONAR = require("COG-ALL-0006")

_STRUCTURAL = frozenset(
    {NodeClass.BRANCH, NodeClass.LOOP, NodeClass.CATCH, NodeClass.SWITCH, NodeClass.TERNARY}
)
_HYBRID = frozenset({NodeClass.ELIF_CONTINUATION, NodeClass.ELSE_CLAUSE})


def cognitive(
    root: Node,
    adapter: LanguageAdapter,
    ctx: MetricContext,
    *,
    exclude_nested_units: bool = False,
    initial_function_names: tuple[str, ...] = (),
) -> int:
    """Cognitive complexity of ``root``'s subtree.

    ``initial_function_names`` seeds the enclosing-function name stack when the
    root itself is a function unit (recursion heuristic, COG-ALL-0005).
    """
    total = 0
    whitepaper = ctx.cognitive_mode == "whitepaper"
    fdepth0 = 1 if initial_function_names else 0
    # stack entries: (node, nesting, function_depth, enclosing_function_names)
    stack: list[tuple[Node, int, int, tuple[str, ...]]] = [
        (child, 0, fdepth0, initial_function_names) for child in reversed(root.children)
    ]
    from codecaliper.syntax._treesitter import is_opaque

    while stack:
        node, nesting, fdepth, names = stack.pop()
        if is_opaque(node):
            continue  # CORE-ALL-0002: ERROR/MISSING subtrees are opaque
        child_nesting, child_fdepth, child_names = nesting, fdepth, names
        c = adapter.classify(node)
        if c is not None:
            k = c.node_class
            if k in _STRUCTURAL:
                if ctx.in_range(node):
                    total += int(ctx.count(R_STRUCT, node, 1 + nesting, metric="cognitive"))
                    if nesting > 0:
                        ctx.fired.add(R_NESTING)  # the nesting penalty rule applied
                child_nesting += 1  # COG-ALL-0004
            elif k in _HYBRID:
                if ctx.in_range(node):
                    total += int(ctx.count(R_HYBRID, node, 1, metric="cognitive"))
                # chain flattening: no extra nesting beyond the chain head's
            elif k is NodeClass.BOOL_OP:
                if c.new_sequence and ctx.in_range(node):
                    total += int(ctx.count(R_BOOLSEQ, node, 1, metric="cognitive"))
            elif k is NodeClass.JUMP_LABEL:
                # labeled jumps: flat +1, both modes, no nesting effect
                # (whitepaper B1 fundamental increment; sonar-java implements it)
                if ctx.in_range(node):
                    for r in c.rulings:
                        if r.startswith("COG-"):
                            total += int(ctx.count(r, node, 1, metric="cognitive"))
                            break
            elif k in (NodeClass.FUNCTION_DEF, NodeClass.LAMBDA):
                if exclude_nested_units and k is NodeClass.FUNCTION_DEF:
                    continue  # CORE-ALL-0003: nested units get their own reports
                if fdepth > 0:
                    child_nesting += 1  # COG-ALL-0004: only NESTED units deepen
                    ctx.fired.add(R_NESTING)
                child_fdepth += 1
                if k is NodeClass.FUNCTION_DEF:
                    child_names = names + (adapter.function_name(node),)
            elif k is NodeClass.CLASS_DEF:
                if exclude_nested_units:
                    continue
                # class bodies do not deepen cognitive nesting (COG-ALL-0004)
        if whitepaper and names:
            callee = adapter.call_name(node)
            if callee is not None and callee == names[-1] and ctx.in_range(node):
                total += int(ctx.count(R_RECURSION_WP, node, 1, metric="cognitive"))
        elif not whitepaper:
            ctx.fired.add(R_NO_RECURSION_SONAR)
        stack.extend(
            (child, child_nesting, child_fdepth, child_names)
            for child in reversed(node.children)
        )
    return total
