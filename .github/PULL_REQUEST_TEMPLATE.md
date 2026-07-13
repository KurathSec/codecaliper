# Summary

<!-- What does this change, and why? -->

## Instrument gates (check what applies)

- [ ] **No corpus value changed**, or this PR bumps the spec MAJOR in
      `src/codecaliper/spec/rulings/index.toml` and regenerates the snapshot
      with `tools/update_snapshot.py --confirm-spec-bump`.
- [ ] Every new counting decision is a **TOML ruling with a new immutable ID**
      (existing rulings are superseded, never edited into new meanings), cited
      from code via `spec.require()`, and exercised by a corpus case with
      hand-computed expected values (working shown in `notes`).
- [ ] Node-type strings appear only in `languages/*.py` tables / ruling
      `node_types` (grammar-integrity test passes); `tree_sitter` is imported
      only in `syntax/_treesitter.py`.
- [ ] Nothing in `src/` imports from `tests/_reference/`; no external metric
      tool became a runtime dependency.
- [ ] `docs/spec/rulings.md` regenerated (`tools/gen_spec_docs.py`) if any
      ruling text changed.

## Test plan

<!-- Commands run and their results, e.g. `.venv/bin/pytest`, `.venv/bin/ruff check src tests tools` -->
