"""The LanguageAdapter contract.

Metric engines never see tree-sitter node-type strings — only :class:`NodeClass`
and :class:`~codecaliper.syntax.tokens.TokenKind`. Per-language differences live
entirely in the adapters' tables and a few named hook methods, every one citing
a ruling ID; the grammar-integrity and spec-coverage tests hold the tables to
the compiled grammar and the spec (ARCHITECTURE.md §5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from codecaliper.model import GrammarInfo, Span

if TYPE_CHECKING:  # pragma: no cover
    from codecaliper.syntax._treesitter import Node, Tree


class NodeClass(Enum):
    BRANCH = "branch"                     # if heads
    ELIF_CONTINUATION = "elif"            # elif / else-if arms (chain-flattened)
    ELSE_CLAUSE = "else"                  # if-attached else
    TERNARY = "ternary"
    SWITCH = "switch"                     # match / switch head
    CASE_LABEL = "case"
    LOOP = "loop"
    CATCH = "catch"
    BOOL_OP = "boolop"
    COMPREHENSION_GUARD = "comp-guard"
    LAMBDA = "lambda"
    FUNCTION_DEF = "function"
    CLASS_DEF = "class"
    NESTING_ONLY = "nesting-only"         # try / with — no increment, no cognitive nesting


@dataclass(frozen=True, slots=True)
class Classified:
    node_class: NodeClass
    rulings: tuple[str, ...]
    new_sequence: bool = True  # BOOL_OP only: starts a new like-operator sequence (COG-ALL-0003)


@dataclass(frozen=True, slots=True)
class FunctionUnit:
    name: str
    qualified_name: str
    node: Node
    span: Span


def span_of(node: Node) -> Span:
    return Span(
        start_line=node.start_point[0] + 1,
        start_col=node.start_point[1],
        end_line=node.end_point[0] + 1,
        end_col=node.end_point[1],
    )


@dataclass
class LanguageAdapter:
    """Base adapter: concrete adapters supply tables and small hooks."""

    name: str = ""
    file_extensions: tuple[str, ...] = ()

    # --- token tables (BW + Halstead + LOC share them; BW-ALL-0006) ---
    keywords: frozenset[str] = frozenset()
    soft_keywords: frozenset[str] = frozenset()  # classify as IDENTIFIER (BW-PY-0001)
    keyword_leaf_types: frozenset[str] = frozenset()
    identifier_types: frozenset[str] = frozenset()
    number_types: frozenset[str] = frozenset()
    string_types: frozenset[str] = frozenset()
    comment_types: frozenset[str] = frozenset()
    atomic_types: frozenset[str] = frozenset()
    arithmetic_ops: frozenset[str] = frozenset()
    comparison_ops: frozenset[str] = frozenset()
    assignment_ops: frozenset[str] = frozenset()
    branch_keywords: frozenset[str] = frozenset()
    loop_keywords: frozenset[str] = frozenset()

    # --- structural tables ---
    node_class_map: dict[str, tuple[NodeClass, tuple[str, ...]]] = field(default_factory=dict)
    statement_types: frozenset[str] = frozenset()
    function_def_types: frozenset[str] = frozenset()
    class_def_types: frozenset[str] = frozenset()

    _grammar: object = None
    _parser: object = None
    _grammar_info: GrammarInfo | None = None

    # --- parsing ---
    def _ensure_loaded(self) -> None:
        if self._parser is None:
            from codecaliper.syntax import grammars

            self._grammar, self._parser, self._grammar_info = grammars.load(self.name)

    def parse(self, source: bytes) -> Tree:
        self._ensure_loaded()
        return self._parser.parse(source)  # type: ignore[union-attr]

    def grammar_info(self) -> GrammarInfo:
        self._ensure_loaded()
        assert self._grammar_info is not None
        return self._grammar_info

    def grammar(self) -> object:
        self._ensure_loaded()
        return self._grammar

    # --- classification (table lookup; hooks in subclasses for context cases) ---
    def classify(self, node: Node) -> Classified | None:
        entry = self.node_class_map.get(node.type)
        if entry is None:
            return None
        return Classified(entry[0], entry[1])

    # --- hooks ---
    def function_name(self, node: Node) -> str:
        name = node.child_by_field_name("name")
        if name is None:
            return ""
        return (name.text or b"").decode("utf-8", errors="replace")

    def call_name(self, node: Node) -> str | None:
        """Simple callee name for the recursion heuristic (COG-ALL-0005), or None."""
        return None

    def function_units(self, tree: Tree) -> list[FunctionUnit]:
        from codecaliper.syntax._treesitter import is_opaque, walk

        units: list[FunctionUnit] = []
        # enclosing-name stack for qualified names, driven by node spans
        stack: list[tuple[int, str]] = []  # (end_byte, name)
        opaque_until = -1  # skip everything inside an ERROR subtree (CORE-ALL-0002)
        for node, _depth in walk(tree):
            if node.start_byte < opaque_until:
                continue
            if is_opaque(node):
                opaque_until = node.end_byte
                continue
            while stack and node.start_byte >= stack[-1][0]:
                stack.pop()
            if node.type in self.function_def_types or node.type in self.class_def_types:
                name = self.function_name(node)
                if node.type in self.function_def_types:
                    qual = ".".join([n for _, n in stack] + [name])
                    units.append(FunctionUnit(name, qual, node, span_of(node)))
                stack.append((node.end_byte, name))
        return units
