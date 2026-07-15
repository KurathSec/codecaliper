# Adding a language

This is the end-to-end procedure for adding a language to codecaliper, worked
through with **Go**, the third language and the one added after the extension
seam was tightened. Read `CONTRIBUTING.md` for the terse checklist; this page is
the narrated version.

## Two layers, and only one is expensive

Adding a language is two separable jobs:

- **A. Make the tool run** on the language: write the adapter, pin the grammar,
  register it. This is genuinely small, and it is confined to the `languages/`
  package. The metric engines, readability extractors, `model.py`, `api.py`,
  the CLI and the grammar loader need no edit.
- **B. Make the numbers traceable**: a ruling for every language-specific
  counting decision, and a hand-computed corpus case for every ruling. This is
  the work, and it is not optional. codecaliper's whole reason to exist is that
  every number it stamps is backed by a verified rule. A language with an
  adapter but no corpus would ship numbers nobody checked, wearing a provenance
  stamp that claims otherwise. Do not do that.

The steps below interleave A and B.

## 0. Pin the grammar

A language is a pinned, calibrated tree-sitter grammar. Three edits, all
mechanical:

- `pyproject.toml` dependencies: a compatible range, e.g. `tree-sitter-go>=0.25,<0.26`.
- `constraints/ci.txt`: the exact pin, e.g. `tree-sitter-go==0.25.0`.
- `src/codecaliper/spec/validated_grammars.toml`: the calibrated version,
  e.g. `go = "0.25.0"`.

Install it (`pip install -e ".[dev]" -c constraints/ci.txt`) and confirm it
loads under the pinned binding. `test_grammar_integrity.py` will hold every
node-type string you write to this exact compiled grammar.

## 1. Write the adapter

`languages/<lang>.py` is a `LanguageAdapter`: plain dict tables plus a few named
hooks. See `languages/go.py`. It is the *only* file the metric engines never
see through, because they read `NodeClass` and `TokenKind`, never a node-type
string. Introspect the grammar first (parse representative source, dump node
kinds) so your tables name real nodes.

Key fields (all in `languages/base.py`):

- `grammar_module` (the tree-sitter package name, e.g. `"tree_sitter_go"`),
  `file_extensions`, `keywords`.
- Token tables: `identifier_types`, `number_types`, `string_types`,
  `comment_types`, `atomic_types`, the operator-class sets. `syntax/tokens.lex`
  classifies each leaf against these. A worked subtlety from Go: `true`, `false`,
  `nil` and `iota` are *named* leaves, and the Go spec makes them predeclared
  identifiers, not keywords, so they go in `identifier_types`, not the keyword
  table (BW-GO-0001) — a deliberate, spec-faithful divergence from Java.
- `node_class_map`: node type -> `(NodeClass, rulings)`. Every increment-bearing
  row cites a ruling ID via `require(...)`, which fails at import on a phantom ID.
- Hooks: override `classify()` for context-dependent decisions (Go's else-if
  chain flattening, boolean-operator sequences, labeled jumps) and `call_name()`
  for the recursion heuristic.

Register it in `languages/__init__.py`: add the name to `_BUILTIN` and a lazy
branch to `get_adapter()`. That is the one hand-maintained spot; keep the two in
step. Nothing else outside `languages/` changes — the CLI derives its `--lang`
choices from the registry, and the grammar loader reads `grammar_module` off the
adapter.

## 2. Author the rulings

Reuse every `-ALL-` ruling (structural/hybrid cognitive increments, nesting,
recursion, Halstead, LOC, MI, the token-normalization rules). Write a new
`*-<LANG>-*` ruling only for a genuinely language-specific counting decision,
in the matching `spec/rulings/*.toml`, tagged `since_spec = "<new version>"`.

Go added nine: `CC-GO-0001..0005` (if; the single `for` loop; short-circuit
operators; switch/type-switch cases; select communication cases), `COG-GO-0001`
(labeled jumps and `goto`), `TOK-GO-0001` (atomic string/rune literals),
`BW-GO-0001`/`BW-GO-0002` (the keyword set and branch/loop features). A ruling
is immutable once shipped: supersede with a new ID, never edit its meaning.

## 3. Hand-compute the corpus

`tests/corpus/<lang>/<case-id>/{input.<ext>, expected.toml}`. Every ruling needs
at least one case that cites it in `[case].rulings`; the coverage gate
(`test_spec_coverage.py`) enforces it both ways. **Expected values are computed
by a human**, with the arithmetic shown in `notes` — integers assert exactly,
floats carry an `abs_tol`, dual-mode cognitive cases assert both modes. Read the
metric engines (`metrics/cyclomatic.py`, `metrics/cognitive.py`) so your
by-hand count matches how the engine treats each `NodeClass`, then run the tool
as a cross-check: hand and tool must agree, and the note records the derivation,
not the tool output. Go shipped eight cases; `go-features-001` is the Halstead +
BW + MI + LOC witness, with the full token harvest written out.

## 4. Wire the differential oracle

An external oracle is the independent witness. lizard covers Go cyclomatic
complexity, so Go joins the lizard lane in `tests/differential/`: a few probes
in `GO_PROBES`, a `go` branch in `inputs()`/`comparisons()`, and Go's inputs
added to `test_lizard.py`. lizard concurs with us on every Go probe, so nothing
lands in `divergences.toml` — but when an oracle disagrees, the divergence must
be classified there (the lane fails on an unclassified difference and on a stale
entry alike). Regenerate `docs/spec/divergences.md` with
`tools/gen_divergences.py`.

## 5. Bump the spec and regenerate

Adding rulings is a spec **MINOR** (new rulings, no existing number moves). Bump
`spec/rulings/index.toml` and add a `[[changelog]]` entry. Then:

- `python tools/update_snapshot.py` — refreshes the spec-drift snapshot. It
  refuses a *changed* existing value without `--confirm-spec-bump`; new cases
  are additive and need no flag.
- `python tools/gen_spec_docs.py` — regenerates `docs/spec/rulings.md`.

If any *existing* corpus value moved, you did not add a language — you changed a
number, which is a spec MAJOR, and the drift gate will say so.

## 6. Verify the gates

```bash
.venv/bin/ruff check src tests tools
.venv/bin/mypy
.venv/bin/pytest
```

Green means: the three mechanical gates pass (spec-drift with the new snapshot,
ruling coverage for the new rulings, grammar integrity for every new node-type
string), the differential lane agrees or has the divergence classified, and
every hand-computed corpus value matches the engine. That is what "the number is
traceable" means for the new language, and it is the bar every language is held
to.

## What you also touch (and what you do not)

Outside `languages/` and the spec/corpus data, a language touches a small,
honest set of shared registries: the ruling-ID pattern in
`test_spec_coverage.py` (so `*-<LANG>-*` citations are checked), the language
lists in the prose docs, and the differential harness. It does **not** touch any
metric engine, the readability extractors, `model.py`, `api.py`, the CLI or the
grammar loader. That seam is the point, and it is real.
