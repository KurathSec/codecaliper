"""Adapter tables and ruling node bindings validated against the COMPILED
grammar via Language introspection (ARCHITECTURE.md §4). A grammar node rename
(the real tree-sitter-java comment -> line_comment/block_comment case) fails
loudly and specifically here instead of silently zeroing metrics.
"""

from __future__ import annotations

import pytest

from codecaliper.languages import available_languages, get_adapter
from codecaliper.spec import iter_rulings
from codecaliper.syntax._treesitter import node_kinds


@pytest.mark.parametrize("lang", available_languages())
def test_adapter_tables_match_grammar(lang: str) -> None:
    adapter = get_adapter(lang)
    kinds = node_kinds(adapter.grammar())
    tables = {
        "node_class_map": set(adapter.node_class_map),
        "statement_types": set(adapter.statement_types),
        "atomic_types": set(adapter.atomic_types),
        "comment_types": set(adapter.comment_types),
        "string_types": set(adapter.string_types),
        "number_types": set(adapter.number_types),
        "identifier_types": set(adapter.identifier_types),
        "keyword_leaf_types": set(adapter.keyword_leaf_types),
        "function_def_types": set(adapter.function_def_types),
        "class_def_types": set(adapter.class_def_types),
    }
    for table, entries in tables.items():
        unknown = entries - kinds
        assert not unknown, (
            f"{lang}.{table} names node types absent from the compiled grammar: "
            f"{sorted(unknown)} (grammar drift?)"
        )


@pytest.mark.parametrize("lang", available_languages())
def test_ruling_node_bindings_match_grammar(lang: str) -> None:
    adapter = get_adapter(lang)
    kinds = node_kinds(adapter.grammar())
    for r in iter_rulings(language=lang):
        if r.language != lang:
            continue  # 'all' rulings carry no per-grammar node bindings
        unknown = set(r.node_types) - kinds
        assert not unknown, (
            f"ruling {r.id} binds node types absent from the {lang} grammar: "
            f"{sorted(unknown)}"
        )


@pytest.mark.parametrize("lang", available_languages())
def test_grammar_is_calibrated(lang: str) -> None:
    """The dev/CI environment must run the release-calibrated grammar
    (constraints/ci.txt); user environments may deviate and get labelled."""
    info = get_adapter(lang).grammar_info()
    assert info.validated, (
        f"{info.package} {info.version} != validated_grammars.toml: "
        "either fix the environment or follow the grammar-upgrade procedure "
        "(ARCHITECTURE.md §10)"
    )
