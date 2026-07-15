"""Python adapter: tables + contextual hooks, every row citing a ruling.

Verified against tree-sitter-python 0.25.0 node kinds (test_grammar_integrity
holds these tables to the compiled grammar).
"""

from __future__ import annotations

import keyword
from typing import TYPE_CHECKING

from codecaliper.languages.base import Classified, LanguageAdapter, NodeClass
from codecaliper.spec import require

if TYPE_CHECKING:  # pragma: no cover
    from codecaliper.syntax._treesitter import Node

R_CC_IF = require("CC-PY-0001")
R_CC_ELIF = require("CC-PY-0002")
R_CC_BOOLOP = require("CC-PY-0003")
R_CC_COMP_GUARD = require("CC-PY-0004")
R_CC_LOOP = require("CC-PY-0005")
R_CC_EXCEPT = require("CC-PY-0006")
R_CC_TERNARY = require("CC-PY-0007")
R_CC_CASE = require("CC-PY-0008")
R_COG_STRUCT = require("COG-ALL-0001")
R_COG_HYBRID = require("COG-ALL-0002")
R_COG_BOOLSEQ = require("COG-ALL-0003")
R_COG_NESTING = require("COG-ALL-0004")
R_COG_COMPREHENSION = require("COG-PY-0001")
R_NESTED_UNITS = require("CORE-ALL-0003")
R_TOK_ELLIPSIS = require("TOK-PY-0003")

# BW-PY-0001's enumerated soft-keyword set (match/case/type/_), pinned so
# classification is identical across the supported interpreters; asserted at
# import time to be a superset of the running interpreter's softkwlist so a
# future CPython addition can't drift silently past this table.
_SOFT_KEYWORDS = frozenset({"_", "case", "match", "type"})
assert _SOFT_KEYWORDS >= frozenset(keyword.softkwlist), (
    f"host softkwlist {keyword.softkwlist} exceeds the pinned BW-PY-0001 set "
    f"{sorted(_SOFT_KEYWORDS)}; reconcile the ruling before shipping"
)

_NODE_CLASS_MAP: dict[str, tuple[NodeClass, tuple[str, ...]]] = {
    "if_statement": (NodeClass.BRANCH, (R_CC_IF, R_COG_STRUCT)),
    "elif_clause": (NodeClass.ELIF_CONTINUATION, (R_CC_ELIF, R_COG_HYBRID)),
    "conditional_expression": (NodeClass.TERNARY, (R_CC_TERNARY, R_COG_STRUCT)),
    "for_statement": (NodeClass.LOOP, (R_CC_LOOP, R_COG_STRUCT)),
    "while_statement": (NodeClass.LOOP, (R_CC_LOOP, R_COG_STRUCT)),
    "except_clause": (NodeClass.CATCH, (R_CC_EXCEPT, R_COG_STRUCT)),
    "match_statement": (NodeClass.SWITCH, (R_COG_STRUCT,)),
    "case_clause": (NodeClass.CASE_LABEL, (R_CC_CASE,)),
    "if_clause": (NodeClass.COMPREHENSION_GUARD, (R_CC_COMP_GUARD, R_COG_COMPREHENSION)),
    "lambda": (NodeClass.LAMBDA, (R_COG_NESTING,)),
    "function_definition": (NodeClass.FUNCTION_DEF, (R_NESTED_UNITS, R_COG_NESTING)),
    "class_definition": (NodeClass.CLASS_DEF, (R_NESTED_UNITS,)),
    "try_statement": (NodeClass.NESTING_ONLY, ()),
    "with_statement": (NodeClass.NESTING_ONLY, ()),
}


class PythonAdapter(LanguageAdapter):
    def __init__(self) -> None:
        super().__init__(
            name="python",
            file_extensions=(".py", ".pyi"),
            grammar_module="tree_sitter_python",
            # BW-PY-0001: kwlist (True/False/None included; soft keywords are identifiers)
            keywords=frozenset(keyword.kwlist),
            # BW-PY-0001: soft keywords are identifiers, matching tokenize NAME.
            # PINNED to the spec's enumerated set rather than the running
            # interpreter's keyword.softkwlist: `type` (PEP 695) is absent from
            # softkwlist before 3.12, which would make provenance for a `type`
            # alias differ across the supported 3.10-3.14 interpreters.
            soft_keywords=_SOFT_KEYWORDS,
            keyword_leaf_types=frozenset({"true", "false", "none"}),
            identifier_types=frozenset({"identifier"}),
            # TOK-PY-0003: `...` (named `ellipsis` leaf) is an OPERATOR token,
            # matching CPython tokenize's OP and Java's varargs `...`; otherwise
            # it falls through to OTHER and vanishes from Halstead
            operator_leaf_types=frozenset({"ellipsis"}),
            number_types=frozenset({"integer", "float"}),
            string_types=frozenset({"string"}),
            comment_types=frozenset({"comment"}),
            # TOK-PY-0002: `string` is atomic; `concatenated_string` is
            # descended so interleaved comments lex as COMMENT tokens
            atomic_types=frozenset({"string"}),
            # BW-ALL-0006 operator classes (spellings mirror the reference extractor)
            arithmetic_ops=frozenset({"+", "-", "*", "/", "//", "%", "**", "@"}),
            comparison_ops=frozenset({"==", "!=", "<", ">", "<=", ">=", "<>"}),
            assignment_ops=frozenset(
                {"=", "+=", "-=", "*=", "/=", "//=", "%=", "**=",
                 "&=", "|=", "^=", ">>=", "<<=", "@=", ":="}
            ),
            branch_keywords=frozenset({"if", "elif"}),  # BW-PY-0002
            loop_keywords=frozenset({"for", "while"}),  # BW-PY-0002
            node_class_map=dict(_NODE_CLASS_MAP),
            statement_types=frozenset(
                {
                    "expression_statement", "return_statement", "pass_statement",
                    "break_statement", "continue_statement", "import_statement",
                    "import_from_statement", "future_import_statement",
                    "raise_statement", "assert_statement",
                    "delete_statement", "global_statement", "nonlocal_statement",
                    "if_statement", "for_statement", "while_statement", "try_statement",
                    "with_statement", "function_definition", "class_definition",
                    "match_statement", "type_alias_statement",
                    # legacy py2 syntax the grammar still recognizes
                    "print_statement", "exec_statement",
                }
            ),
            function_def_types=frozenset({"function_definition"}),
            class_def_types=frozenset({"class_definition"}),
            # TOK-PY-0003 governs only when an `...` actually lexes; cited
            # per-occurrence, not statically
            conditional_token_rulings={"ellipsis": R_TOK_ELLIPSIS},
        )

    def classify(self, node: Node) -> Classified | None:
        t = node.type
        if t == "if_clause":
            # CC-PY-0004 scopes to comprehension guards. A case-clause guard is
            # not separately counted: the guarded case_clause already counts
            # (CC-PY-0008), and counting the guard too would double-count.
            parent = node.parent
            if parent is not None and parent.type == "case_clause":
                return None
            return super().classify(node)
        if t == "case_clause":
            # CC-PY-0008: a bare-wildcard `case _:` with no guard is the
            # fall-through path, mirroring Java `default:` (CC-JAVA-0006).
            patterns = [c for c in node.children if c.type == "case_pattern"]
            has_guard = node.child_by_field_name("guard") is not None
            if (
                len(patterns) == 1
                and (patterns[0].text or b"") == b"_"
                and not has_guard
            ):
                return None
            return super().classify(node)
        if t == "else_clause":
            # COG-ALL-0002: hybrid +1 only for an if-attached else; for/while/try
            # else clauses are not branch arms.
            parent = node.parent
            if parent is not None and parent.type == "if_statement":
                return Classified(NodeClass.ELSE_CLAUSE, (R_COG_HYBRID,))
            return None
        if t == "boolean_operator":
            op = node.child_by_field_name("operator")
            op_type = op.type if op is not None else ""
            parent = node.parent
            same_as_parent = False
            if parent is not None and parent.type == "boolean_operator":
                pop = parent.child_by_field_name("operator")
                same_as_parent = pop is not None and pop.type == op_type
            return Classified(
                NodeClass.BOOL_OP, (R_CC_BOOLOP, R_COG_BOOLSEQ), new_sequence=not same_as_parent
            )
        return super().classify(node)

    def call_name(self, node: Node) -> str | None:
        """COG-ALL-0005 receiver rule: bare calls plus self./cls. method calls."""
        if node.type != "call":
            return None
        fn = node.child_by_field_name("function")
        if fn is None:
            return None
        if fn.type == "identifier":
            return (fn.text or b"").decode("utf-8", errors="replace")
        if fn.type == "attribute":
            obj = fn.child_by_field_name("object")
            attr = fn.child_by_field_name("attribute")
            if (
                obj is not None
                and obj.type == "identifier"
                and (obj.text or b"") in (b"self", b"cls")
                and attr is not None
            ):
                return (attr.text or b"").decode("utf-8", errors="replace")
        return None
