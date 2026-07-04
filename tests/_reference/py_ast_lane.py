"""TEST-ONLY internal oracle: the rigorous Python-AST metric lane.

Verbatim port from Spaghetti Architect ``eval/metrics.py`` (MIT, same author —
see NOTICE; cite DOI 10.5281/zenodo.21033174). Used by
tests/test_python_lane_crosscheck.py as a zero-install differential witness for
the tree-sitter Python path. Never imported from src/.

Known, ruled divergences from the tree-sitter lane (asserted as EXPLAINED, not
fixed): this lane does not count ternaries (CC-PY-0007) or match/case
(CC-PY-0008) in cyclomatic; its cognitive walker gives elif +1+depth and does
not count else/bool-sequences/recursion (COG-ALL-0002/0003/0005).
"""

from __future__ import annotations

import ast
import math

_DECISION = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler)


def cyclomatic(py_src: str) -> int:
    """1 + decision points (If/For/While/ExceptHandler, comprehension ifs, and
    each BoolOp operand beyond the first)."""
    tree = ast.parse(py_src)
    dp = 0
    for node in ast.walk(tree):
        if isinstance(node, _DECISION):
            dp += 1
        elif isinstance(node, ast.comprehension):
            dp += len(node.ifs)
        elif isinstance(node, ast.BoolOp):
            dp += len(node.values) - 1
    return 1 + dp


def _traverse(py_src: str) -> dict:
    """Cognitive complexity and max nesting with elif chains flattened."""
    tree = ast.parse(py_src)
    state = {"cognitive": 0, "max_nesting": 0}

    def at(depth: int) -> None:
        state["max_nesting"] = max(state["max_nesting"], depth)

    def visit(node: ast.AST, depth: int) -> None:
        if isinstance(node, ast.If):
            _visit_if(node, depth)
            return
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            state["cognitive"] += 1 + depth
            for child in node.body:
                at(depth + 1)
                visit(child, depth + 1)
            for child in node.orelse:
                at(depth + 1)
                visit(child, depth + 1)
            _scan_expr(node, depth)
            return
        if isinstance(node, ast.Try):
            for child in node.body:
                at(depth + 1)
                visit(child, depth + 1)
            for handler in node.handlers:
                state["cognitive"] += 1 + depth
                for child in handler.body:
                    at(depth + 1)
                    visit(child, depth + 1)
            for child in node.orelse + node.finalbody:
                at(depth + 1)
                visit(child, depth + 1)
            return
        nests = isinstance(node, (ast.With, ast.AsyncWith, ast.FunctionDef,
                                  ast.AsyncFunctionDef, ast.ClassDef))
        for child in ast.iter_child_nodes(node):
            d = depth + 1 if nests else depth
            if nests and isinstance(child, ast.stmt):
                at(d)
            visit(child, d)

    def _visit_if(node: ast.If, depth: int) -> None:
        state["cognitive"] += 1 + depth
        for child in node.body:
            at(depth + 1)
            visit(child, depth + 1)
        orelse = node.orelse
        while len(orelse) == 1 and isinstance(orelse[0], ast.If):
            elif_node = orelse[0]
            state["cognitive"] += 1 + depth
            for child in elif_node.body:
                at(depth + 1)
                visit(child, depth + 1)
            orelse = elif_node.orelse
        for child in orelse:
            at(depth + 1)
            visit(child, depth + 1)

    def _scan_expr(node: ast.AST, depth: int) -> None:
        for child in ast.iter_child_nodes(node):
            if not isinstance(child, ast.stmt):
                visit(child, depth)

    for stmt in tree.body:
        visit(stmt, 0)
    return state


def cognitive(py_src: str) -> int:
    return _traverse(py_src)["cognitive"]


def max_nesting(py_src: str) -> int:
    return _traverse(py_src)["max_nesting"]


def halstead(py_src: str) -> dict:
    """Halstead from AST-harvested operators/operands (a fixed, identical rule)."""
    tree = ast.parse(py_src)
    operators: list[str] = []
    operands: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp):
            operators.append(type(node.op).__name__)
        elif isinstance(node, ast.UnaryOp):
            operators.append(type(node.op).__name__)
        elif isinstance(node, ast.BoolOp):
            operators.extend([type(node.op).__name__] * (len(node.values) - 1))
        elif isinstance(node, ast.Compare):
            operators.extend(type(o).__name__ for o in node.ops)
        elif isinstance(node, ast.AugAssign):
            operators.append("Aug" + type(node.op).__name__)
        elif isinstance(node, ast.Assign):
            operators.append("=")
        elif isinstance(node, ast.Call):
            operators.append("()")
        elif isinstance(node, ast.Subscript):
            operators.append("[]")
        elif isinstance(node, ast.Attribute):
            operators.append(".")
            operands.append(node.attr)
        elif isinstance(node, ast.If):
            operators.append("if")
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            operators.append("for")
        elif isinstance(node, ast.While):
            operators.append("while")
        elif isinstance(node, ast.Try):
            operators.append("try")
        elif isinstance(node, ast.ExceptHandler):
            operators.append("except")
        elif isinstance(node, ast.Name):
            operands.append(node.id)
        elif isinstance(node, ast.Constant):
            operands.append(repr(node.value))
    n1, big_n1 = len(set(operators)), len(operators)
    n2, big_n2 = len(set(operands)), len(operands)
    n, big_n = n1 + n2, big_n1 + big_n2
    volume = big_n * math.log2(n) if n > 0 else 0.0
    difficulty = (n1 / 2) * (big_n2 / n2) if n2 > 0 else 0.0
    effort = difficulty * volume
    return {"n1": n1, "N1": big_n1, "n2": n2, "N2": big_n2,
            "volume": volume, "difficulty": difficulty, "effort": effort}
