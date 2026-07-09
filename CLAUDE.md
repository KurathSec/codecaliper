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

Spec v1.0.0 (first calibrated evolution: TOK-ALL-0006 tab=8 supersedes TOK-ALL-0004,
BW-ALL-0007 lexical fallback added, ops arbitration null — all via the pre-registered
experiment in `validation/bw_faithfulness/derived/arbitration_report.md`), W1–6 done:
skeleton + tree-sitter + BW port (W1–3); UNCOVERED list EMPTY — every
active ruling has a corpus case — and mypy --strict is a hard CI gate (W4–5); BW faithfulness
reproduction ran end-to-end (W6, paper's Fig. 5 cutoff 3.14; under spec 1.0.0's arbitrated
rulings: 10-fold logistic accuracy 0.820, bootstrap 95% CI [0.770, 0.870] overlapping the
paper's ~0.80, AUC 0.828, sign agreement 21/24; deviations documented in the report — see
`validation/bw_faithfulness/derived/bw_faithfulness_report.md`; dataset license is UNVERIFIED,
dataset content stays in gitignored `cache/`, only aggregates/feature vectors live in tracked
`derived/`), plus the external-oracle differential lane (`tests/differential/` vs
radon/lizard/cognitive_complexity; every divergence classified against a ruling in
`divergences.toml`, docs generated by `tools/gen_divergences.py`). W7 done: mkdocs-material
docs site (`mkdocs.yml`, deployed by `docs.yml`; validation page verbatim-includes the derived
reports via snippets — `mkdocs build --strict` is the check; toolchain pinned in
`constraints/docs.txt`). Release pipeline ready (`release.yml`: gate + build in parallel → PyPI trusted
publishing → GitHub Release → Zenodo webhook; `RELEASING.md` documents the remaining one-time
setup before tagging v0.1.0: the PyPI pending publisher + `pypi` environment; Pages enablement
done 2026-07-10). Paper sources in `paper/` — LOCAL ONLY, gitignored: submission material stays
out of the public repo until publication (prose draft + references.bib + checklist; numbers
regenerate from derived/, never edited). Next (ARCHITECTURE.md §16, W8): tag v0.1.0 + first DOI,
screencast, acmart conversion, MSR Data & Tool Showcase submission (~Dec 2026 CFP).
