"""Go adapter: tables + contextual hooks, every increment-bearing row citing a ruling.

Verified against tree-sitter-go 0.25.0 node kinds. Like Java, Go's `else` is an
anonymous token and an else-if chain lives in the if_statement's `alternative`
field, so both are handled by hooks here. Go has no ternary and no exceptions
(errors are values); its only loop is `for_statement` in all its forms, and
`select` is a Go-specific branching construct measured like a switch. The
predeclared identifiers `true`/`false`/`nil`/`iota` are IDENTIFIER tokens, not
keywords (BW-GO-0001): the Go spec reserves exactly 25 words, none of them these.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from codecaliper.languages.base import Classified, LanguageAdapter, NodeClass
from codecaliper.spec import require

if TYPE_CHECKING:  # pragma: no cover
    from codecaliper.syntax._treesitter import Node

R_CC_IF = require("CC-GO-0001")
R_CC_LOOP = require("CC-GO-0002")
R_CC_BOOLOP = require("CC-GO-0003")
R_CC_CASE = require("CC-GO-0004")
R_CC_COMM = require("CC-GO-0005")
R_COG_STRUCT = require("COG-ALL-0001")
R_COG_HYBRID = require("COG-ALL-0002")
R_COG_BOOLSEQ = require("COG-ALL-0003")
R_COG_NESTING = require("COG-ALL-0004")
R_COG_JUMP = require("COG-GO-0001")
R_NESTED_UNITS = require("CORE-ALL-0003")

# The Go spec's 25 reserved words. true/false/nil/iota are predeclared
# IDENTIFIERS (universe block, shadowable), not keywords, so they are absent
# here and classified as identifiers via identifier_types (BW-GO-0001).
_GO_KEYWORDS = frozenset(
    """break case chan const continue default defer else fallthrough for func
    go goto if import interface map package range return select struct switch
    type var""".split()
)

_NODE_CLASS_MAP: dict[str, tuple[NodeClass, tuple[str, ...]]] = {
    "for_statement": (NodeClass.LOOP, (R_CC_LOOP, R_COG_STRUCT)),
    "expression_switch_statement": (NodeClass.SWITCH, (R_COG_STRUCT,)),
    "type_switch_statement": (NodeClass.SWITCH, (R_COG_STRUCT,)),
    "select_statement": (NodeClass.SWITCH, (R_COG_STRUCT,)),
    # switch/type-switch value cases count for CC; select comm cases too, under
    # a distinct ruling; the `default` case (default_case) never counts.
    "expression_case": (NodeClass.CASE_LABEL, (R_CC_CASE,)),
    "type_case": (NodeClass.CASE_LABEL, (R_CC_CASE,)),
    "communication_case": (NodeClass.CASE_LABEL, (R_CC_COMM,)),
    "func_literal": (NodeClass.LAMBDA, (R_COG_NESTING,)),
    "function_declaration": (NodeClass.FUNCTION_DEF, (R_NESTED_UNITS, R_COG_NESTING)),
    "method_declaration": (NodeClass.FUNCTION_DEF, (R_NESTED_UNITS, R_COG_NESTING)),
}


class GoAdapter(LanguageAdapter):
    def __init__(self) -> None:
        super().__init__(
            name="go",
            file_extensions=(".go",),
            grammar_module="tree_sitter_go",
            keywords=_GO_KEYWORDS,
            # true/false/nil/iota are named leaves; the Go spec makes them
            # predeclared identifiers, so they lex as IDENTIFIER (BW-GO-0001).
            # The blank identifier `_` is a plain `identifier` and needs no
            # special row (unlike Java's underscore_pattern).
            identifier_types=frozenset(
                {
                    "identifier", "type_identifier", "field_identifier",
                    "package_identifier", "label_name",
                    "true", "false", "nil", "iota",
                }
            ),
            number_types=frozenset(
                {"int_literal", "float_literal", "imaginary_literal"}
            ),
            # rune literals are integer-valued but written like character
            # literals; they are consumed whole, like Java `char` (TOK-GO-0001).
            string_types=frozenset(
                {"interpreted_string_literal", "raw_string_literal", "rune_literal"}
            ),
            comment_types=frozenset({"comment"}),  # one node type for // and /* */
            atomic_types=frozenset(  # TOK-GO-0001
                {"interpreted_string_literal", "raw_string_literal", "rune_literal"}
            ),
            arithmetic_ops=frozenset({"+", "-", "*", "/", "%"}),
            comparison_ops=frozenset({"==", "!=", "<", ">", "<=", ">="}),
            assignment_ops=frozenset(
                {"=", ":=", "+=", "-=", "*=", "/=", "%=",
                 "&=", "|=", "^=", "<<=", ">>=", "&^="}
            ),
            branch_keywords=frozenset({"if"}),  # BW-GO-0002
            loop_keywords=frozenset({"for"}),  # BW-GO-0002
            node_class_map=dict(_NODE_CLASS_MAP),
            statement_types=frozenset(
                {
                    "if_statement", "for_statement", "expression_switch_statement",
                    "type_switch_statement", "select_statement", "return_statement",
                    "break_statement", "continue_statement", "goto_statement",
                    "fallthrough_statement", "defer_statement", "go_statement",
                    "labeled_statement", "expression_statement", "send_statement",
                    "inc_statement", "dec_statement", "assignment_statement",
                    "short_var_declaration",
                    # declarations (LOC-ALL-0004 covers declarations too)
                    "package_clause", "import_declaration", "const_declaration",
                    "var_declaration", "type_declaration", "function_declaration",
                    "method_declaration",
                }
            ),
            function_def_types=frozenset(
                {"function_declaration", "method_declaration"}
            ),
            # Go has no class scope that encloses its methods: a method is a
            # package-level func with a receiver, so there is no CLASS_DEF unit.
            class_def_types=frozenset(),
        )

    def classify(self, node: Node) -> Classified | None:
        t = node.type
        if t == "if_statement":
            # CC-GO-0001 + COG-ALL-0002: an if that is the `alternative` of
            # another if is an else-if arm, chain-flattened for cognitive.
            parent = node.parent
            if (
                parent is not None
                and parent.type == "if_statement"
                and parent.child_by_field_name("alternative") == node
            ):
                return Classified(NodeClass.ELIF_CONTINUATION, (R_CC_IF, R_COG_HYBRID))
            return Classified(NodeClass.BRANCH, (R_CC_IF, R_COG_STRUCT))
        if t == "else":
            # Anonymous `else` token: hybrid +1 unless it introduces an else-if
            # (then the nested if_statement counts instead, so no double count).
            parent = node.parent
            if parent is not None and parent.type == "if_statement":
                alt = parent.child_by_field_name("alternative")
                if alt is not None and alt.type != "if_statement":
                    return Classified(NodeClass.ELSE_CLAUSE, (R_COG_HYBRID,))
            return None
        if t == "binary_expression":
            op = node.child_by_field_name("operator")
            op_type = op.type if op is not None else ""
            if op_type not in ("&&", "||"):
                return None
            parent = node.parent
            same_as_parent = False
            if parent is not None and parent.type == "binary_expression":
                pop = parent.child_by_field_name("operator")
                same_as_parent = pop is not None and pop.type == op_type
            return Classified(
                NodeClass.BOOL_OP, (R_CC_BOOLOP, R_COG_BOOLSEQ), new_sequence=not same_as_parent
            )
        if t in ("break_statement", "continue_statement"):
            # COG-GO-0001: only LABELED break/continue increment (break LABEL /
            # continue LABEL); a bare break/continue contributes nothing.
            if any(child.type == "label_name" for child in node.children):
                return Classified(NodeClass.JUMP_LABEL, (R_COG_JUMP,))
            return None
        if t == "goto_statement":
            # COG-GO-0001: goto always targets a label, so it is always a
            # fundamental increment.
            return Classified(NodeClass.JUMP_LABEL, (R_COG_JUMP,))
        return super().classify(node)

    def call_name(self, node: Node) -> str | None:
        """COG-ALL-0005 receiver rule: a bare same-package call `f(...)` is the
        recursion candidate. A method/qualified call `x.f(...)` has a
        selector_expression function and is not treated as recursion."""
        if node.type != "call_expression":
            return None
        fn = node.child_by_field_name("function")
        if fn is None or fn.type != "identifier":
            return None
        return (fn.text or b"").decode("utf-8", errors="replace")
