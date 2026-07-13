"""Java adapter: tables + contextual hooks, every row citing a ruling.

Verified against tree-sitter-java 0.23.5 node kinds. Java has no else_clause
node: an `else` is an anonymous token, and the else-if chain lives in the
if_statement's `alternative` field, so both are handled by hooks here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from codecaliper.languages.base import Classified, LanguageAdapter, NodeClass
from codecaliper.spec import require

if TYPE_CHECKING:  # pragma: no cover
    from codecaliper.syntax._treesitter import Node

R_CC_IF = require("CC-JAVA-0001")
R_CC_TERNARY = require("CC-JAVA-0002")
R_CC_BOOLOP = require("CC-JAVA-0003")
R_CC_LOOP = require("CC-JAVA-0004")
R_CC_CATCH = require("CC-JAVA-0005")
R_CC_CASE = require("CC-JAVA-0006")
R_COG_STRUCT = require("COG-ALL-0001")
R_COG_HYBRID = require("COG-ALL-0002")
R_COG_BOOLSEQ = require("COG-ALL-0003")
R_COG_NESTING = require("COG-ALL-0004")
R_COG_JUMP = require("COG-JAVA-0001")
R_NESTED_UNITS = require("CORE-ALL-0003")
R_TOK_UNDERSCORE = require("TOK-JAVA-0002")

# The JLS reserved words except `_`, which is ruled an identifier token
# (TOK-JAVA-0002, mirroring Python's `_`); true/false/null arrive via
# keyword_leaf_types (BW-JAVA-0001). Contextual keywords (record, sealed,
# yield, ...) are identifiers, like every other non-reserved word token
# (TOK-ALL-0007).
_JAVA_KEYWORDS = frozenset(
    """abstract assert boolean break byte case catch char class const continue
    default do double else enum extends final finally float for goto if
    implements import instanceof int interface long native new package private
    protected public return short static strictfp super switch synchronized
    this throw throws transient try void volatile while""".split()
)

_NODE_CLASS_MAP: dict[str, tuple[NodeClass, tuple[str, ...]]] = {
    "ternary_expression": (NodeClass.TERNARY, (R_CC_TERNARY, R_COG_STRUCT)),
    "for_statement": (NodeClass.LOOP, (R_CC_LOOP, R_COG_STRUCT)),
    "enhanced_for_statement": (NodeClass.LOOP, (R_CC_LOOP, R_COG_STRUCT)),
    "while_statement": (NodeClass.LOOP, (R_CC_LOOP, R_COG_STRUCT)),
    "do_statement": (NodeClass.LOOP, (R_CC_LOOP, R_COG_STRUCT)),
    "catch_clause": (NodeClass.CATCH, (R_CC_CATCH, R_COG_STRUCT)),
    "switch_expression": (NodeClass.SWITCH, (R_COG_STRUCT,)),
    "lambda_expression": (NodeClass.LAMBDA, (R_COG_NESTING,)),
    "method_declaration": (NodeClass.FUNCTION_DEF, (R_NESTED_UNITS, R_COG_NESTING)),
    "constructor_declaration": (NodeClass.FUNCTION_DEF, (R_NESTED_UNITS, R_COG_NESTING)),
    "compact_constructor_declaration": (NodeClass.FUNCTION_DEF, (R_NESTED_UNITS, R_COG_NESTING)),
    "class_declaration": (NodeClass.CLASS_DEF, (R_NESTED_UNITS,)),
    "interface_declaration": (NodeClass.CLASS_DEF, (R_NESTED_UNITS,)),
    "enum_declaration": (NodeClass.CLASS_DEF, (R_NESTED_UNITS,)),
    "record_declaration": (NodeClass.CLASS_DEF, (R_NESTED_UNITS,)),
    "try_statement": (NodeClass.NESTING_ONLY, ()),
    "try_with_resources_statement": (NodeClass.NESTING_ONLY, ()),
    "synchronized_statement": (NodeClass.NESTING_ONLY, ()),
}


class JavaAdapter(LanguageAdapter):
    def __init__(self) -> None:
        super().__init__(
            name="java",
            file_extensions=(".java",),
            keywords=_JAVA_KEYWORDS,
            keyword_leaf_types=frozenset({"true", "false", "null_literal"}),
            # underscore_pattern: `_` as an unnamed variable declarator is the
            # same identifier token as `_` in pattern/lambda positions
            # (TOK-JAVA-0002)
            identifier_types=frozenset(
                {"identifier", "type_identifier", "underscore_pattern"}
            ),
            # TOK-JAVA-0002 governs only when an underscore_pattern actually
            # lexes; cited per-occurrence, not statically (unlike TOK-JAVA-0001)
            conditional_token_rulings={"underscore_pattern": R_TOK_UNDERSCORE},
            number_types=frozenset(
                {
                    "decimal_integer_literal", "hex_integer_literal",
                    "octal_integer_literal", "binary_integer_literal",
                    "decimal_floating_point_literal", "hex_floating_point_literal",
                }
            ),
            string_types=frozenset({"string_literal", "character_literal"}),
            comment_types=frozenset({"line_comment", "block_comment"}),
            atomic_types=frozenset({"string_literal", "character_literal"}),  # TOK-JAVA-0001
            arithmetic_ops=frozenset({"+", "-", "*", "/", "%"}),
            comparison_ops=frozenset({"==", "!=", "<", ">", "<=", ">="}),
            assignment_ops=frozenset(
                {"=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>=", ">>>="}
            ),
            branch_keywords=frozenset({"if"}),  # BW-JAVA-0002
            loop_keywords=frozenset({"for", "while", "do"}),  # BW-JAVA-0002
            node_class_map=dict(_NODE_CLASS_MAP),
            statement_types=frozenset(
                {
                    "local_variable_declaration", "expression_statement", "return_statement",
                    "if_statement", "for_statement", "enhanced_for_statement",
                    "while_statement", "do_statement", "try_statement",
                    "try_with_resources_statement", "switch_expression", "break_statement",
                    "continue_statement", "throw_statement", "method_declaration",
                    "constructor_declaration", "class_declaration", "field_declaration",
                    "assert_statement", "yield_statement", "labeled_statement",
                    "synchronized_statement",
                    # declarations (LOC-ALL-0004 covers declarations too)
                    "package_declaration", "import_declaration", "interface_declaration",
                    "enum_declaration", "record_declaration", "annotation_type_declaration",
                    "annotation_type_element_declaration", "constant_declaration",
                    "static_initializer", "compact_constructor_declaration",
                    "explicit_constructor_invocation", "module_declaration",
                    "requires_module_directive", "exports_module_directive",
                    "opens_module_directive", "uses_module_directive",
                    "provides_module_directive",
                }
            ),
            function_def_types=frozenset(
                {"method_declaration", "constructor_declaration",
                 "compact_constructor_declaration"}
            ),
            class_def_types=frozenset(
                {"class_declaration", "interface_declaration", "enum_declaration",
                 "record_declaration"}
            ),
        )

    def classify(self, node: Node) -> Classified | None:
        t = node.type
        if t == "if_statement":
            # CC-JAVA-0001 + COG-ALL-0002: an if that is the `alternative` of
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
        if t == "switch_label":
            # CC-JAVA-0006: `case` labels count; `default` does not.
            first = node.children[0] if node.children else None
            if first is not None and first.type == "case":
                return Classified(NodeClass.CASE_LABEL, (R_CC_CASE,))
            return None
        if t in ("break_statement", "continue_statement"):
            # COG-JAVA-0001: only LABELED jumps increment (break LABEL /
            # continue LABEL); a bare break/continue contributes nothing.
            if any(child.type == "identifier" for child in node.children):
                return Classified(NodeClass.JUMP_LABEL, (R_COG_JUMP,))
            return None
        return super().classify(node)

    def call_name(self, node: Node) -> str | None:
        """COG-ALL-0005 receiver rule: bare calls plus this-receiver calls only.
        A same-named call on another receiver is not recursion."""
        if node.type != "method_invocation":
            return None
        obj = node.child_by_field_name("object")
        if obj is not None and obj.type != "this":
            return None
        name = node.child_by_field_name("name")
        if name is not None:
            return (name.text or b"").decode("utf-8", errors="replace")
        return None
