# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

codecaliper is a **measurement instrument** for code readability (Buse–Weimer 2010 feature set)
and complexity (cyclomatic, dual-mode cognitive, Halstead, MI, LOC) on a unified tree-sitter base
(Python + Java). "Instrument" is load-bearing: every emitted number is traceable to a versioned
spec ruling and a grammar version, and reproducible byte-for-byte per platform. The full design
rationale, requirements, honesty boundaries, and decision log live in `ARCHITECTURE.md` — it is
the authoritative requirements record (the original project charter was deliberately removed
from the repo).

## Commands

```bash
.venv/bin/pip install -e ".[dev]" -c constraints/ci.txt   # exact calibrated grammar pins
.venv/bin/pytest                                          # full suite
.venv/bin/pytest tests/test_consistency_corpus.py -k py-cc-boolop-001   # one corpus case
.venv/bin/ruff check src tests tools
.venv/bin/python tools/update_snapshot.py                 # refresh spec-drift snapshot (refuses numeric changes)
.venv/bin/python tools/gen_spec_docs.py                   # regenerate docs/spec/rulings.md (CI diffs it)
.venv/bin/codecaliper FILE --json                         # CLI; also: spec show <ID>, env, cite
```

A project venv exists at `.venv/`. The installed grammar versions must match
`src/codecaliper/spec/validated_grammars.toml` or `test_grammar_integrity.py` fails (that is the
point — see the grammar-upgrade procedure in `ARCHITECTURE.md` §10).

## The three mechanical gates (never work around them)

1. **Spec drift** (`tests/test_spec_drift.py`): if a change alters ANY value for ANY corpus case,
   CI is red until the spec MAJOR is bumped in `src/codecaliper/spec/rulings/index.toml` and the
   snapshot is regenerated with `tools/update_snapshot.py --confirm-spec-bump`. Grammar pin bumps
   that change numbers are also spec majors.
2. **Ruling coverage** (`tests/test_spec_coverage.py`): every counting decision is a TOML ruling
   with an immutable ID (`CC-PY-0003` style) in `src/codecaliper/spec/rulings/`; code cites it via
   `spec.require()` (import-time failure on phantom IDs) and a corpus case exercises it. The
   `UNCOVERED` allowlist in that test is shrink-only. Rulings are never edited into new meanings —
   supersede with a new ID.
3. **Grammar integrity** (`tests/test_grammar_integrity.py`): every node-type string in adapter
   tables and ruling `node_types` is validated against the compiled grammar via
   `Language.node_kind_for_id` introspection.

## Architecture in one pass

Measurement flow: `api._measure()` → `syntax/tokens.normalize()` (TOK-* rulings: BOM/CRLF/UTF-8)
→ adapter parse (tree-sitter) → one unified `LexicalToken` stream (`syntax/tokens.lex`) feeding
BW features, lexical Halstead, and LOC coverage counts → metric engines → frozen dataclasses in
`model.py` with `Provenance` (spec version, fired rulings, grammar version+ABI+validated flag).

Isolation seams (enforced, not conventional):

- `tree_sitter` is imported ONLY in `src/codecaliper/syntax/_treesitter.py` (ruff
  banned-module-level-imports). Binding API churn lands in that one file.
- Metric engines (`metrics/`) and readability (`readability/`) never see tree-sitter node-type
  strings — only the `NodeClass`/`TokenKind` enums. All per-language knowledge lives in
  `languages/python.py` / `languages/java.py` as plain dict tables + small named hook methods,
  every row citing a ruling. Adding a language touches zero core code (checklist in
  CONTRIBUTING.md).
- `tests/_reference/` holds verbatim ports from Spaghetti Architect (the stdlib BW extractor and
  the Python-AST lane) used as per-PR differential oracles. They must NEVER be imported from
  `src/` (anti-salami boundary; NOTICE credits the origin, DOI 10.5281/zenodo.21033174). External
  tools (radon/lizard/…) are test-time oracles only, never runtime dependencies.

Cognitive complexity is ONE walker (`metrics/cognitive.py`) in two modes; the only current mode
divergence is the recursion increment (COG-ALL-0005 whitepaper / COG-ALL-0006 sonar-compat). Any
new mode divergence must arrive as a mode-tagged ruling pair, so the spec table stays the
authoritative whitepaper-vs-Sonar diff.

Known ruled divergences to not "fix": the tree-sitter lane counts ternaries/match-case in CC, the
`tests/_reference` lane does not (`test_python_lane_crosscheck.py` asserts the divergence
exactly); f-string interpolation contents are invisible to token-level BW features (TOK-PY-0001).

## Honesty invariants (encoded in types — keep them that way)

No readability score exists anywhere: BW output is the raw 25-vector (canonical order
`BW_FEATURE_NAMES`, sha-stamped into model artifacts) with `granularity`/`extrapolated` fields.
MI always carries `derived_from=("halstead.volume","cyclomatic","sloc")` and a `mi-contains-cc`
diagnostic; Halstead always carries `halstead-approximation`. Parse errors: measure, set
`parse_ok=False`, attach a diagnostic — never refuse (except `--strict`), never fabricate. An
unvalidated grammar runs but is labelled (`GrammarInfo.validated=False` + diagnostic). Outputs
contain no timestamps; `Date`-like calls and hash-order dependence break
`test_determinism.py`.

## Corpus cases

`tests/corpus/<lang>/<case-id>/{input.*, expected.toml}` — expected values are **hand-computed**
with the working shown in `notes`; integers exact, floats always with tolerances; dual-mode
cognitive cases assert both modes. The case ID equals the directory name and is cross-referenced
from ruling `examples`.

## Current status / next milestones

Spec v0.1.0 scaffold: W1–3 of the plan is done (skeleton, tree-sitter wired, BW ported +
fidelity-tested, seed corpus + gates). Next (ARCHITECTURE.md §16): W4–5 complete the ruling set
and empty the UNCOVERED list; W6 is the BW faithfulness reproduction
(`validation/bw_faithfulness/` — dataset license is UNVERIFIED, data is never committed; only
derived feature vectors may be committed) and the external-oracle differential lane with the
generated known-divergence list.
