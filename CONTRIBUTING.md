# Contributing to codecaliper

Thanks for your interest! codecaliper is a *measurement instrument*: the bar
for changes is traceability, not just green tests.

## Setup

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]" -c constraints/ci.txt   # exact calibrated grammar pins
pytest
ruff check src tests tools
mypy                                            # --strict; config in pyproject.toml
```

All three are hard CI gates. `mypy` takes no arguments on purpose: `[tool.mypy]` in
`pyproject.toml` sets `strict = true` and `files = ["src/codecaliper"]`, and the `typecheck` job in
`ci.yml` runs exactly `mypy`, so passing your own paths can check something CI does not.

### The differential oracles (one of them is not a pip package)

The oracle lane (`tests/differential/`) checks our numbers against external tools. Four are wired,
and they install two different ways:

```bash
pip install -e ".[dev,oracles]" -c constraints/ci.txt  # radon, lizard, cognitive_complexity
python tools/fetch_pmd.py                              # PMD: the Java oracle (cyclomatic + cognitive)
```

The `[oracles]` extra is **not** the whole oracle set. PMD is a JVM tool, not a pip package, so it
is outside the pip closure `constraints/ci.txt` pins: it needs `java` on PATH, its own pin lives in
`tests/differential/pmd.toml`, and `tools/fetch_pmd.py` downloads that exact release (~73 MB) into
the gitignored `.oracles/`, sha256-verifying the archive before it unpacks anything.

Without a JVM, or with nothing fetched, the PMD tests SKIP with a reason that tells you which of the
two is missing. That is fine locally: a missing oracle never fails a contributor's build. It is not
fine in CI, so the `differential` job in `ci.yml` installs a JDK, runs `tools/fetch_pmd.py` (cached
on the pinned sha256) and proves `pmd --version` answers *before* pytest starts. A SKIP there would
let the job pass while testing nothing, which is also why the three pip oracles are hard-imported in
the same job.

## The three rules

1. **No number changes silently.** If your change alters any value for any
   consistency-corpus case, the spec-drift gate (`tests/test_spec_drift.py`)
   will fail. That is intentional: bump the spec MAJOR in
   `src/codecaliper/spec/rulings/index.toml`, describe the change in its
   changelog, and regenerate the snapshot with
   `python tools/update_snapshot.py --confirm-spec-bump`.
2. **Every counting decision is a ruling.** New behaviour needs a ruling in
   `src/codecaliper/spec/rulings/*.toml` (the ID is immutable: supersede, never
   mutate), a corpus case exercising it (`tests/corpus/<lang>/<case-id>/`),
   and code that cites it via `spec.require()`. The coverage meta-test
   (`tests/test_spec_coverage.py`) enforces this; its `UNCOVERED` allowlist is
   shrink-only. Then regenerate the docs the ruling feeds (see below), or CI
   will fail on a stale generated file even though your tests pass locally.
3. **Hand-compute corpus expectations.** `expected.toml` values are computed by
   a human, with the working shown in `notes`. Integers assert exactly; floats
   always carry tolerances.

## Superseding a ruling

"Supersede, never mutate" is rule 2, and it is a concrete edit, not an attitude.
A ruling ID is immutable forever: changing what an existing ID *means* silently
rewrites the history of every number ever published under it. Instead you retire
the old stanza in place and write a new one.

Two shipped supersessions show the whole mechanism. TOK-ALL-0004 (tab = 1) was
superseded by TOK-ALL-0006 (tab = 8), and TOK-PY-0001 by TOK-PY-0002.

**On the old stanza**, add exactly two fields and change nothing else. Its
`statement`, `title`, `node_types` and ID stay as they were: that text is the
audit trail for numbers already in the world, and editing it is the thing this
rule exists to prevent.

```toml
status = "superseded"          # default is "active"
superseded_by = "TOK-ALL-0006" # the successor's ID
```

You do not have to give the old stanza a corpus case, and neither TOK-ALL-0004
nor TOK-PY-0001 has one. Coverage is enforced from the corpus side:
`test_active_rulings_are_covered` requires every **active** ruling to be cited in
some case's `[case].rulings`, and a superseded ruling is exempt by that filter.

**The new stanza** is an ordinary ruling with a fresh ID, plus `since_spec` set
to the spec version that introduces it, and a `statement` that names what it
supersedes and why. TOK-ALL-0006 carries `since_spec = "1.0.0"` and
`examples = ["py-tok-normalize-001"]`; TOK-PY-0002 carries `since_spec = "1.1.0"`
and two examples. It is the successor that now needs a corpus case citing it. If
you name that case in `examples`, the case must cite the ruling back in its
`[case].rulings`, because `test_ruling_examples_exist_and_cite_back` rejects a
self-attested example as vacuous.

A meta-test holds the chain together: a superseded ruling must name a successor
that resolves and is itself `active`, and `superseded_by` may not appear on a
ruling that is not superseded. A dangling or circular supersession is a red
build, not a stale comment.

**The spec level is not decided by the supersession.** It is decided by the
drift gate, and the two examples land on opposite sides:

| supersession | did an existing corpus value move? | spec level |
|---|---|---|
| TOK-ALL-0004 → TOK-ALL-0006 (tab 1 → 8) | yes | **MAJOR**, spec 1.0.0 |
| TOK-PY-0001 → TOK-PY-0002 (`concatenated_string` descended) | no | **MINOR**, spec 1.1.0 |

So: write the new ruling, run the suite, and let `tests/test_spec_drift.py` tell
you which bump you are making. If it stays green, you are additive (MINOR). If it
goes red, you changed a calibrated number, and that is a MAJOR plus
`tools/update_snapshot.py --confirm-spec-bump` (rule 1). Record the change in the
`[[changelog]]` block in `index.toml` either way.

## Generated files you have to regenerate

Two files under `docs/` are rendered from data elsewhere in the tree and are
committed. Editing them by hand is pointless; forgetting to regenerate them is a
red CI on a change that is otherwise fine.

| you touched | run | who fails if you do not |
|---|---|---|
| `src/codecaliper/spec/rulings/*.toml` | `python tools/gen_spec_docs.py` (writes `docs/spec/rulings.md`) | the `spec-docs` job in `ci.yml` (and the release gate): it regenerates and runs `git diff --exit-code docs/` |
| `tests/differential/divergences.toml` | `python tools/gen_divergences.py` (writes `docs/spec/divergences.md`) | `tests/differential/test_table.py::test_generated_divergence_doc_is_fresh`, which needs no oracle installed and so runs in the plain `pytest` job too |

Snapshots are the third case, and the one with teeth: `tools/update_snapshot.py`
refreshes `tests/snapshots/corpus_values.json` and **refuses** to record a
changed number unless you pass `--confirm-spec-bump` (rule 1).

## Adding a language (the afternoon tutorial)

Most of the work is in one new file, and a new language is confined to the
`languages/` package. The metric engines, the readability extractors,
`model.py`, `api.py`, the CLI and the grammar loader need no edit at all: the
first four are written against the `NodeClass` and `TokenKind` enums and never
against a node-type string, `cli.py` derives `--lang`'s choices from the
registry, and `syntax/grammars.py` takes the tree-sitter package name from your
adapter. Your tables are the only thing that teaches the tool your language.

1. Pin the grammar wheel (compatible range in `pyproject.toml`, exact pin in
   `constraints/ci.txt`, calibrated version in
   `src/codecaliper/spec/validated_grammars.toml`).
2. Write `src/codecaliper/languages/<lang>.py`: token tables, node-class map,
   hooks, and `grammar_module="tree_sitter_<lang>"` (the package name the
   grammar loader will import; it lives on the adapter, next to
   `file_extensions`). Every increment-bearing row cites a ruling (nesting-only
   rows carry an empty tuple). `tests/test_grammar_integrity.py` will hold your
   tables to the compiled grammar.
3. Add `*-<LANG>-*` rulings for every language-specific decision.
4. Add corpus cases with hand-computed expectations.
5. Register the adapter in `src/codecaliper/languages/__init__.py`, the one
   place in the runtime package outside your new file that you touch: add the
   name to the `_BUILTIN` tuple *and* a branch to `get_adapter()`. Miss this and
   you get `UnsupportedLanguageError`; `_BUILTIN` alone also drives
   `detect_language()` (so an unregistered language cannot be auto-detected) and
   `cli.py`'s `--lang` choices (so the CLI rejects it with an argparse error
   until it is registered).
6. Extend the language alternation in `_RULING_ID_RE` in
   `tests/test_spec_coverage.py` (e.g. `(?:ALL|PY|JAVA|GO)` gained `GO`).
   Until you do, the phantom-citation sweep cannot see your `*-<LANG>-*` IDs in
   src/ comments and docstrings.
7. Wire the language into the differential lane: a probe dict in
   `tests/differential/_harness.py` (Go added `GO_PROBES`), branches in
   `inputs()`/`comparisons()`, and the language's inputs in the relevant oracle
   test (`test_lizard.py` covers cyclomatic for all three languages). Classify
   any divergence in `tests/differential/divergences.toml`; a lizard-vs-us
   disagreement fails the lane until it is classified.
8. Bump the spec MINOR (additive) and regenerate the snapshot. The drift test
   proves existing languages' numbers did not move.
9. Regenerate `docs/spec/rulings.md` with `python tools/gen_spec_docs.py` and
   commit it (see the table above). If you also classified a new oracle
   divergence, regenerate `docs/spec/divergences.md` too.

The registry in step 5 is the only hand-maintained spot in the *runtime*
package: keep `_BUILTIN` and the `get_adapter()` branch in step with each other.
The lazy imports there are deliberate, so no adapter (and no grammar) loads
until it is asked for. `docs/adding-a-language.md` narrates this whole
checklist with Go as the worked example.

One thing you get for free and should not fight: `api.py` guards the Java
snippet-scaffold fallback with `adapter.name == "java"` (CORE-JAVA-0001), so a
new language gets no scaffolding. If yours needs it, that is a ruling, not an
`if`.

## What not to do

- Do not add external metric tools as runtime dependencies. radon, lizard and
  cognitive_complexity (the `[oracles]` extra) and PMD (a JVM tool, fetched by
  `tools/fetch_pmd.py`) are differential-test **oracles** only.
- Do not add a "readability score". BW output is a feature vector by design
  (ARCHITECTURE.md §13).
- Do not import `tree_sitter` outside `src/codecaliper/syntax/_treesitter.py`.
- Do not import anything from `tests/_reference/` in `src/`.
- Do not track corpus data. The Buse-Weimer snippets under
  `validation/bw_faithfulness/derived/arbitration_inputs/` are the sole
  exception, permitted by a grant from an author of that dataset; every other
  corpus is fetched into the gitignored `cache/` at run time. The terms, per
  corpus, are in
  [`PERMISSIONS.md`](https://github.com/KurathSec/codecaliper/blob/main/PERMISSIONS.md).
  Read it before you add a byte of data to the tree.

## Releases

A release is a calibration event, not a version bump. The tag is what mints the
citable artifact, so it has to name what was calibrated: every release states
three versions (package, spec, and the exact grammar pins the numbers were
produced under), and the CHANGELOG section for the version becomes the GitHub
Release notes verbatim.

The pipeline is `.github/workflows/release.yml`: a tag triggers the gate and the
build in parallel, then PyPI trusted publishing, then the GitHub Release, whose
publication fires the Zenodo archival webhook. The procedure, the ordering
constraint on the validation reports, and the one-time account setup are in
[`RELEASING.md`](https://github.com/KurathSec/codecaliper/blob/main/RELEASING.md).
Follow it rather than improvising: several steps are not idempotent.
