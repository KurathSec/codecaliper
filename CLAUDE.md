# CLAUDE.md

Operating instructions for Claude Code (claude.ai/code) in this repository. What the tool is and
how to use it: `README.md`. Why it is built this way, plus the requirements record and the
decision log: `ARCHITECTURE.md`. What changed and when: `CHANGELOG.md`. This file does not repeat
any of them.

## What you are working on

codecaliper is a measurement instrument for code readability (Buse-Weimer 2010 feature set) and
complexity (cyclomatic, dual-mode cognitive, Halstead, MI, LOC) on a unified tree-sitter base
(Python, Java, Go). "Instrument" is load-bearing: every emitted number is traceable to a versioned
spec ruling and a grammar version, and reproducible byte-for-byte per platform.

Treat `ARCHITECTURE.md` as authoritative when it disagrees with anything else, except code. When
code and prose disagree, the code is right and the prose is a bug.

## Commands

```bash
.venv/bin/pip install -e ".[dev]" -c constraints/ci.txt   # exact calibrated grammar pins
.venv/bin/pytest                                          # full suite
.venv/bin/pytest tests/test_consistency_corpus.py -k py-cc-boolop-001   # one corpus case
.venv/bin/ruff check src tests tools
.venv/bin/mypy                                            # --strict, a hard CI gate
.venv/bin/python tools/update_snapshot.py                 # refresh spec-drift snapshot (refuses numeric changes)
.venv/bin/python tools/gen_spec_docs.py                   # regenerate docs/spec/rulings.md (CI diffs it)
.venv/bin/codecaliper FILE --json                         # CLI; also: spec show <ID>, env, cite
```

A project venv exists at `.venv/`. The installed grammar versions must match
`src/codecaliper/spec/validated_grammars.toml` or `test_grammar_integrity.py` fails. That is the
point; the upgrade procedure is ARCHITECTURE.md §10.

## The three mechanical gates (never work around them)

1. **Spec drift** (`tests/test_spec_drift.py`): if a change alters ANY value for ANY corpus case,
   CI is red until the spec MAJOR is bumped in `src/codecaliper/spec/rulings/index.toml` and the
   snapshot is regenerated with `tools/update_snapshot.py --confirm-spec-bump`. A grammar pin bump
   that changes numbers is also a spec major.
2. **Ruling coverage** (`tests/test_spec_coverage.py`): every counting decision is a TOML ruling
   with an immutable ID (`CC-PY-0003` style) in `src/codecaliper/spec/rulings/`; code cites it via
   `spec.require()`, which fails at import on a phantom ID, and a corpus case exercises it. The
   `UNCOVERED` allowlist in that test is shrink-only and currently empty. Rulings are never edited
   into new meanings: supersede with a new ID.
3. **Grammar integrity** (`tests/test_grammar_integrity.py`): every node-type string in adapter
   tables and in ruling `node_types` is validated against the compiled grammar via
   `Language.node_kind_for_id` introspection.

## Architecture in one pass

Measurement flow: `api._measure()` calls `syntax/tokens.normalize()` (TOK-* rulings: BOM, CRLF,
UTF-8), then the adapter parses with tree-sitter, producing one unified `LexicalToken` stream
(`syntax/tokens.lex`) that feeds BW features, lexical Halstead and the LOC coverage counts. The
metric engines run over it and return frozen dataclasses in `model.py`, each carrying `Provenance`
(spec version, fired rulings, grammar version, ABI, validated flag).

Isolation seams, enforced rather than agreed:

- `tree_sitter` is imported ONLY in `src/codecaliper/syntax/_treesitter.py` (ruff
  banned-module-level-imports). Binding API churn lands in that one file.
- Metric engines (`metrics/`) and readability (`readability/`) never see tree-sitter node-type
  strings, only the `NodeClass` and `TokenKind` enums. Per-language knowledge lives in
  `languages/python.py`, `languages/java.py` and `languages/go.py` as plain dict tables plus small named hooks, every
  increment-bearing row citing a ruling. That seam is real for `metrics/`, `readability/`,
  `model.py`, `api.py`, `cli.py` and `syntax/grammars.py`, which a new language does not touch: the
  CLI derives `--lang` choices from the registry and the grammar loader takes its tree-sitter
  package name from the adapter's `grammar_module`. A new language is confined to the `languages/`
  package: the new adapter module plus one edit to `languages/__init__.py` (`_BUILTIN` and a
  `get_adapter()` branch), which is the registry. That registry is the only hand-maintained spot
  (keep `_BUILTIN` and the if-chain in step; a miss raises `UnsupportedLanguageError`). The full
  checklist is in CONTRIBUTING.md.
- `tests/_reference/` holds verbatim ports from Spaghetti Architect (the stdlib BW extractor, the
  Python-AST lane) used as per-PR differential oracles. They must NEVER be imported from `src/`:
  that is the anti-salami boundary, and NOTICE credits the origin (DOI 10.5281/zenodo.21033174).
  External tools (radon, lizard, and the rest) are test-time oracles, never runtime dependencies.

Cognitive complexity is ONE walker (`metrics/cognitive.py`) run in two modes. The only current
divergence between the modes is the recursion increment (COG-ALL-0005 whitepaper, COG-ALL-0006
sonar-compat). A new mode divergence must arrive as a mode-tagged ruling pair, so that the spec
table stays the authoritative whitepaper-versus-Sonar diff.

## Ruled divergences: do not "fix" these

- The tree-sitter lane counts ternaries and match-case in CC; the `tests/_reference` lane does not.
  `test_python_lane_crosscheck.py` asserts the divergence exactly.
- f-string interpolation contents are invisible to token-level BW features (TOK-PY-0002).

## Honesty invariants (encoded in types, keep them that way)

No readability score exists anywhere. BW output is the raw 25-vector, in the canonical order
`BW_FEATURE_NAMES`, sha-stamped into model artifacts, with `granularity` and `extrapolated` fields.
MI always carries `derived_from=("halstead.volume","cyclomatic","sloc")` and an `mi-contains-cc`
diagnostic. Halstead always carries `halstead-approximation`. On a parse error: measure anyway, set
`parse_ok=False`, attach a diagnostic. Never refuse (except under `--strict`) and never fabricate.
An unvalidated grammar runs, labelled (`GrammarInfo.validated=False` plus a diagnostic). Outputs
contain no timestamps: a `Date`-like call or a hash-order dependence breaks `test_determinism.py`.

## Corpus cases

`tests/corpus/<lang>/<case-id>/{input.*, expected.toml}`. Expected values are **hand-computed**,
with the working shown in `notes`. Integers assert exactly; floats always carry tolerances;
dual-mode cognitive cases assert both modes. The case ID equals the directory name and is
cross-referenced from a ruling's `examples`.

## The validation lanes differ, and the difference is legal

`validation/bw_faithfulness/` is self-contained. Its raw inputs (the 100 Java snippets,
`oracle.csv`, `scores.csv`) are tracked under `derived/arbitration_inputs/` because an author of
the dataset granted redistribution (PERMISSIONS.md). `pinned.py` is the input contract: a missing
tracked input is a hard error, never a SKIP, and a present `cache/DatasetBW.zip` is only a
byte-identity cross-check. So extract, train, report and arbitrate all run with no network.

`validation/breadth/` is not self-contained and never will be. It measures the Scalabrino 2018 and
Dorn 2012 corpora, which carry no permission of any kind, so they are fetched at run time into the
gitignored `cache/` and only aggregates are published. It requires `fetch.py --all`.

Never write a sentence implying the whole project reproduces offline. One corpus of three may be
redistributed; the other two are fetched and never tracked, and prose that blurs the difference
misstates a third party's terms. `PERMISSIONS.md` is the canonical statement: point at it rather
than restating it.

## `paper/` is LOCAL ONLY

`paper/` holds the submission material (prose draft, `references.bib`, per-venue directories). It is
gitignored (`.gitignore`, the `paper/` entry) and has zero tracked files. Keep it that way:
submission material stays out of the public repository until publication. Do not `git add` anything
under it, do not move its content into a tracked path, and do not quote it into a tracked file. It
is in your working tree and it is not part of the repo.

Every number in the draft regenerates from `validation/bw_faithfulness/derived/`. Never hand-edit a
number into the paper: fix the pipeline or the spec, re-run, and let the derived artifact carry it.
