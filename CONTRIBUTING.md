# Contributing to codecaliper

Thanks for your interest! codecaliper is a *measurement instrument*: the bar
for changes is traceability, not just green tests.

## Setup

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]" -c constraints/ci.txt   # exact calibrated grammar pins
pytest
ruff check src tests tools
```

## The three rules

1. **No number changes silently.** If your change alters any value for any
   consistency-corpus case, the spec-drift gate (`tests/test_spec_drift.py`)
   will fail. That is intentional: bump the spec MAJOR in
   `src/codecaliper/spec/rulings/index.toml`, describe the change in its
   changelog, and regenerate the snapshot with
   `python tools/update_snapshot.py --confirm-spec-bump`.
2. **Every counting decision is a ruling.** New behaviour needs a ruling in
   `src/codecaliper/spec/rulings/*.toml` (immutable ID — supersede, never
   mutate), a corpus case exercising it (`tests/corpus/<lang>/<case-id>/`),
   and code that cites it via `spec.require()`. The coverage meta-test
   (`tests/test_spec_coverage.py`) enforces this; its `UNCOVERED` allowlist is
   shrink-only.
3. **Hand-compute corpus expectations.** `expected.toml` values are computed by
   a human, with the working shown in `notes`. Integers assert exactly; floats
   always carry tolerances.

## Adding a language (the afternoon tutorial)

1. Pin the grammar wheel (compatible range in `pyproject.toml`, exact pin in
   `constraints/ci.txt`, calibrated version in
   `src/codecaliper/spec/validated_grammars.toml`).
2. Write `src/codecaliper/languages/<lang>.py`: token tables, node-class map,
   hooks — every row citing a ruling. `tests/test_grammar_integrity.py` will
   hold your tables to the compiled grammar.
3. Add `*-<LANG>-*` rulings for every language-specific decision.
4. Add corpus cases with hand-computed expectations.
5. Register the adapter in `src/codecaliper/languages/__init__.py`.
6. Bump the spec MINOR (additive) and regenerate the snapshot — the drift test
   proves existing languages' numbers did not move.

## What not to do

- Do not add external metric tools as runtime dependencies — radon, lizard,
  etc. are differential-test **oracles** only (`[oracles]` extra).
- Do not add a "readability score". BW output is a feature vector by design
  (ARCHITECTURE.md §13).
- Do not import `tree_sitter` outside `src/codecaliper/syntax/_treesitter.py`.
- Do not import anything from `tests/_reference/` in `src/`.

## Releases

Tagged releases build via trusted publishing and archive to Zenodo. Release
notes state the spec version and the exact calibrated grammar versions.
