"""The tree-sitter quarantine — the ONLY module that imports ``tree_sitter``.

py-tree-sitter breaks its API across 0.x minors (0.22 removed
``Language(path, name)``; 0.23 removed the Parser setters; 0.24/0.25 moved
query execution to ``QueryCursor`` and deprecated ``Language.version`` for
``abi_version``). Confining the import here bounds every future breakage to one
file (ARCHITECTURE.md §4). The MVP deliberately avoids the Query API entirely —
cursor walks suffice.
"""

from __future__ import annotations

import importlib
import importlib.metadata
from collections.abc import Iterator
from typing import Any

from tree_sitter import Language, Node, Parser, Tree

from codecaliper.errors import GrammarLoadError

__all__ = ["Language", "Node", "Parser", "Tree", "load_language", "make_parser",
           "walk", "leaves", "node_kinds", "count_error_nodes"]


def load_language(grammar_module: str) -> tuple[Language, str, int]:
    """Import a grammar wheel and wrap its PyCapsule.

    Returns ``(language, installed_version, abi_version)``.
    """
    try:
        mod = importlib.import_module(grammar_module)
        lang = Language(mod.language())
    except Exception as exc:  # noqa: BLE001 — surface as our typed error
        raise GrammarLoadError(f"cannot load grammar module {grammar_module!r}: {exc}") from exc
    dist = grammar_module.replace("_", "-")
    try:
        version = importlib.metadata.version(dist)
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    # version -> abi_version shim (abi_version since py-tree-sitter 0.25)
    abi: int | None = getattr(lang, "abi_version", None)
    if abi is None:  # pragma: no cover - older binding shim
        abi = int(getattr(lang, "version", 0))
    return lang, version, int(abi)


def make_parser(language: Language) -> Parser:
    return Parser(language)


def walk(tree: Tree) -> Iterator[tuple[Node, int]]:
    """Cursor-based preorder ``(node, depth)`` — O(1) memory, no recursion limit,
    deterministic order."""
    cursor = tree.walk()
    depth = 0
    while True:
        node = cursor.node
        assert node is not None  # a fresh walk cursor always sits on a node
        yield node, depth
        if cursor.goto_first_child():
            depth += 1
            continue
        while True:
            if cursor.goto_next_sibling():
                break
            if not cursor.goto_parent():
                return
            depth -= 1


def is_opaque(node: Node) -> bool:
    """ERROR/MISSING subtrees are opaque to all measurement (CORE-ALL-0002)."""
    return node.type == "ERROR" or node.is_missing


def leaves(tree: Tree, atomic_types: frozenset[str]) -> Iterator[Node]:
    """Terminal-token stream: descend to leaves, but consume node types in
    ``atomic_types`` (e.g. Python ``string`` with its start/content/end
    children) as single opaque tokens (TOK-PY-0002 / TOK-JAVA-0001).

    ERROR/MISSING subtrees yield nothing and are not descended into
    (CORE-ALL-0002): their tokens must not feed Halstead/LOC or (on clean
    parses) BW. On parse errors, BW token-family features instead use
    :func:`leaves_lexical`, which descends into ERROR subtrees (BW-ALL-0007).
    """
    cursor = tree.walk()
    while True:
        node = cursor.node
        assert node is not None  # a fresh walk cursor always sits on a node
        descend = False
        if not is_opaque(node):
            if node.child_count == 0 or node.type in atomic_types:
                yield node
            else:
                descend = True
        if descend and cursor.goto_first_child():
            continue
        while True:
            if cursor.goto_next_sibling():
                break
            if not cursor.goto_parent():
                return


def leaves_lexical(tree: Tree, atomic_types: frozenset[str]) -> Iterator[Node]:
    """Full lexical leaf stream: like :func:`leaves`, but DESCENDS into ERROR
    subtrees, yielding the tokens tree-sitter recovered inside them — the BW
    construct is lexical and must see fragment tokens (BW-ALL-0007). MISSING
    nodes are zero-width fabrications and still yield nothing; a childless
    ERROR node (raw untokenized bytes) also yields nothing."""
    cursor = tree.walk()
    while True:
        node = cursor.node
        assert node is not None  # a fresh walk cursor always sits on a node
        descend = False
        if not node.is_missing:
            if node.type == "ERROR":
                descend = node.child_count > 0
            elif node.child_count == 0 or node.type in atomic_types:
                yield node
            else:
                descend = True
        if descend and cursor.goto_first_child():
            continue
        while True:
            if cursor.goto_next_sibling():
                break
            if not cursor.goto_parent():
                return


def node_kinds(language: Language) -> frozenset[str]:
    """Grammar introspection: every node-kind string of the COMPILED grammar.

    Used by tests/test_grammar_integrity.py to validate adapter tables and
    ruling node_types against the actually-installed grammar, so a grammar node
    rename fails loudly instead of silently zeroing metrics.
    """
    count: int = language.node_kind_count
    kinds = set()
    for i in range(count):
        kind = language.node_kind_for_id(i)
        if kind is not None:
            kinds.add(kind)
    return frozenset(kinds)


def count_error_nodes(tree: Tree) -> int:
    """Number of ERROR/MISSING nodes (parse-error policy CORE-ALL-0002)."""
    n = 0
    for node, _ in walk(tree):
        if node.type == "ERROR" or node.is_missing:
            n += 1
    return n


def node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def field_name_of(node: Node) -> str | None:
    """The field name this node occupies in its parent, if any."""
    parent = node.parent
    if parent is None:
        return None
    # tree-sitter exposes this via the parent's field iteration; the portable
    # way across binding versions is child_by_field_name comparison.
    for field in ("alternative", "consequence", "condition", "operator", "body", "name"):
        try:
            if parent.child_by_field_name(field) == node:
                return field
        except Exception:  # pragma: no cover - defensive against binding churn
            return None
    return None


def language_of_parser(parser: Parser) -> Any:  # pragma: no cover - debugging aid
    return parser.language
