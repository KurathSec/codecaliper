# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

Because codecaliper is a measurement instrument, every release entry states
three versions, not one:

- **package** — the Python package version (`codecaliper.__version__`),
- **spec** — the metric-to-syntax specification version
  (`src/codecaliper/spec/rulings/index.toml`); a spec MAJOR bump means at least
  one calibrated number changed,
- **grammars** — the exact calibrated tree-sitter grammar versions
  (`src/codecaliper/spec/validated_grammars.toml`).

## [Unreleased]

- package 0.1.1.dev0 · spec 1.1.0 · grammars: tree-sitter-python 0.25.0,
  tree-sitter-java 0.23.5 (binding tree-sitter 0.26.0)

## [0.1.0] - 2026-07-12

- package 0.1.0 · spec 1.1.0 · grammars: tree-sitter-python 0.25.0,
  tree-sitter-java 0.23.5 (binding tree-sitter 0.26.0)
- **Spec 1.1.0** (MINOR: new rulings + table completions; no existing corpus
  value changes — verified through the drift gate) from a whole-project
  adversarial review:
  - COG-JAVA-0001: labeled `break`/`continue` are a flat +1 in both cognitive
    modes — the whitepaper's fundamental increment was silently missing for
    Java (and invisible to the differential lane: the only cognitive oracle
    is Python-only).
  - TOK-ALL-0007: anonymous word tokens outside the keyword table are
    identifiers (Python `__future__`, Java contextual keywords — previously
    OPERATOR); Java's keyword table dropped contextual `yield`, matching
    BW-JAVA-0001's stated set.
  - lloc statement tables completed to LOC-ALL-0004's stated scope (Python:
    future/type-alias/legacy print+exec statements; Java: package/import and
    all type declarations, constants, initializers, compact constructors,
    explicit constructor invocations, module declarations/directives).
  - TOK-PY-0002 supersedes TOK-PY-0001: `concatenated_string` (implicit
    concatenation) is descended — string parts are separate STRING tokens and
    an interleaved comment is an ordinary COMMENT token, matching CPython
    tokenize (the superseded ruling swallowed such comments into one string
    token: comment lines undercounted, the comment-only line counted as code).
  - TOK-JAVA-0002: Java `_` is an IDENTIFIER token in every position — the
    grammar's `underscore_pattern` (unnamed variable declarators) previously
    lexed as OTHER, invisible to BW and Halstead, while `_` in pattern/lambda
    positions already lexed as an identifier.
  - TOK-PY-0003: Python `...` (the named `ellipsis` leaf) is an OPERATOR token
    (matching CPython tokenize's OP and Java's varargs `...`), so it is visible
    to Halstead; before this it fell through to OTHER, systematically
    undercounting `.pyi` stub bodies.
  - COG-ALL-0006 justification corrected editorially (it falsely claimed the
    `cognitive_complexity` package omits the recursion increment); the
    normative content is unchanged. BW-JAVA-0001 gained a disclosed editorial
    clarification (its table omits the JLS-reserved `_`, ruled an identifier
    by TOK-JAVA-0002).
  - Corpus 20 -> 26 cases (`java-labeled-jump-001`, `java-contextual-001`,
    `py-future-import-001`, `py-concat-string-001`, `java-underscore-001`,
    `py-ellipsis-001`), hand-computed as always.
- Correctness fixes (same review): CSV per-function BW vectors join by
  (name, span) — Java overloads/Python redefinitions previously all got the
  last unit's numbers; `encoding-replaced` no longer fires on valid UTF-8
  that legitimately contains U+FFFD; Java cognitive values no longer cite the
  Python-only COG-PY-0001; provenance `rulings_applied` now includes
  observably-fired normalization rulings (TOK-ALL-0001/0002/0003) and the
  cyclomatic base CC-ALL-0001 (which now also appears in `--explain` traces,
  so increments sum to the emitted value); BW vectors cite their
  language-specific and tokenization rulings (incl. TOK-ALL-0006);
  `spec show` and the generated rulings doc surface `superseded_by`; the
  spec-drift gate can no longer disarm itself (any snapshot/spec version
  mismatch or unsnapshotted case is red, enforced alongside a new
  supersession-chain consistency test); `--json`/`--csv` are mutually
  exclusive; an unwritable `-o` path is a clean error.
- Provenance completeness (review round 2): every diagnostic-cited ruling now
  reaches `rulings_applied` — parse-error runs cite CORE-ALL-0002 and
  scaffolded snippets cite CORE-JAVA-0001, exactly as their diagnostics
  already claimed; TOK-ALL-0007 fires into provenance and the BW/Halstead
  ruling lists whenever an anonymous word token actually lexed; the
  language's atomic-token rulings (TOK-PY-0002/TOK-JAVA-0001) are cited by
  every token-derived value (BW vectors, Halstead, LOC); at
  `--bw-granularity function`, a parse error outside every function no longer
  produces a report-level `bw-lexical-fallback` claim (no emitted number was
  affected).
- More round-2 fixes: `--explain` trace spans are clamped to the measured
  line domain — the cyclomatic base trace no longer leaks scaffold
  coordinates (line 0 / phantom trailing lines) on scaffolded Java snippets;
  `lloc` values now carry their per-increment `--explain` trace instead of
  silently dropping it; `Session` rejects unknown `cognitive_mode`/
  `granularity` strings (an invalid mode previously measured as sonar-compat
  while stamping the bogus string into provenance); the spec-drift gate also
  asserts per-case metric key-set equality (a snapshot that lost keys can no
  longer narrow the gate silently, and `update_snapshot.py` refuses to
  re-adopt such a loss); `constraints/retrain.txt` gained the missing
  `narwhals` pin (the closure claim was false) and both validation scripts
  stamp its version; `arbitrate.py` SKIPs when the pinned extraction record
  is missing instead of writing a report with null stamps, and the
  reconciliation note no longer mislabels the re-stamped
  `train_results.json` as "under spec 1.0.0".
- Provenance precision (review round 3): the construct-specific tokenization
  rulings (TOK-ALL-0007 anonymous words, TOK-JAVA-0002 `_`) are now cited
  per-occurrence and per-unit — a per-function BW vector no longer inherits a
  file-global TOK-ALL-0007 when the anonymous word lies outside its own span,
  and a Java file without `_` no longer cites TOK-JAVA-0002 (only the static
  atomic-string rulings TOK-PY-0002/TOK-JAVA-0001 are cited unconditionally).
  Python's soft-keyword table is pinned to BW-PY-0001's enumerated set instead
  of the running interpreter's `keyword.softkwlist`, so a `type` alias
  classifies identically on every supported 3.10-3.14 interpreter (asserted at
  import time to stay a superset of the host).
- More round-3 fixes: `update_snapshot.py` treats a whole corpus case
  vanishing as a change requiring `--confirm-spec-bump` (deletion could
  previously drop coverage silently), and `tools_snapshot.py` disambiguates
  colliding per-unit / per-vector snapshot keys by span so a future
  overload/multi-vector case cannot silently narrow the drift gate; several
  disclosed editorial corrections (HAL-ALL-0001 and ARCHITECTURE describe the
  lexical-vs-AST Halstead divergence as *declared* — there is no Halstead
  differential lane — rather than "classified"; CC-PY-0004's lizard note now
  states the real divergence; ARCHITECTURE §5's adapter description no longer
  names a nonexistent `token_kind_map` or claims Halstead shares the
  operator-class tables); honesty/quickstart pages describe the BW fallback as
  conditional; README/index say "every *active* ruling"; the arbitration
  reproduction recipe pins the calibrated grammars (`constraints/ci.txt`).
- Arbitration reproducibility: the 32-cell experiment now re-runs end-to-end
  from pinned tracked inputs (`derived/arbitration_inputs/` — the never-
  committed fallback_on/tab=1 matrix reconstructed exactly, the pre-fallback
  baseline record, the arbitration-time extraction stamps); the regenerated
  report carries accurate input provenance, an ML-stack version stamp, and a
  reconciliation note for the one-ranked-pair (0.0004) AUC gap between the
  matrix cell (0.827) and the final headline (0.828). `constraints/retrain.txt`
  pins the ML stack; `train_results.json` now stamps sklearn/numpy versions
  (numbers unchanged, verified).
- CI: the weekly grammar early-warning probe no longer false-alarms on every
  newer wheel (the pin-equality test is deselected; drift + node-inventory
  checks remain); `constraints/build.txt` is now the complete PEP 517
  closure. New `tests/test_cli.py` covers subcommand content, flag behavior,
  exit codes, and the ModelArtifact feature-order-sha refusal.
- **Spec 1.0.0** — first calibrated evolution, arbitrated by a pre-registered
  32-cell experiment on the original Buse–Weimer dataset
  (`validation/bw_faithfulness/derived/arbitration_report.md`):
  - TOK-ALL-0006 supersedes TOK-ALL-0004: indentation counts a tab as 8
    characters (tab = 1 zeroed the paper's indentation/readability
    correlation; the 8-vs-4 tie-break is a stated convention pick).
  - BW-ALL-0007: BW token-family features use the full lexical stream, ERROR
    regions included — the construct is lexical; metrics stay error-opaque
    (CORE-ALL-0002). Coverage on the original dataset: 8 empty-token vectors
    -> 0.
  - Operator-class arbitration returned a null result; BW-ALL-0006 unchanged.
  - Faithfulness reproduction under the adopted rulings: 10-fold logistic
    accuracy 0.820 (bootstrap 95% CI [0.770, 0.870], overlapping the paper's
    ~0.80), AUC 0.828, Fig. 9 sign agreement 21/24.
- Corpus 19 -> 20 cases (`py-bw-fallback-001`); every active ruling remains
  corpus-covered.
- Release pipeline (`release.yml`): tag-triggered gate -> build (tag/version/
  changelog guards) -> PyPI trusted publishing -> GitHub Release (fires the
  Zenodo archival webhook); procedure and one-time setup in `RELEASING.md`.
- Docs site (mkdocs-material, deployed to GitHub Pages by `docs.yml`):
  quickstart, honesty invariants, generated spec rulings + divergence list,
  a validation page that verbatim-includes the derived faithfulness and
  arbitration reports, mkdocstrings API reference. Toolchain pinned in
  `constraints/docs.txt`, separate from the instrument's calibrated pins.
- `DIAGNOSTIC_CODES` now includes `bw-lexical-fallback`, and the closed set
  is enforced by a corpus sweep test instead of by comment (no emitted value
  changes).
- `CITATION.cff`: hand-maintained `version` removed (Zenodo/GitHub take it
  from the release itself), docs URL added.
- Initial scaffold: unified tree-sitter measurement base (Python + Java),
  Buse–Weimer 25-feature extractor (fidelity-tested against the reference
  implementation), cyclomatic complexity, dual-mode cognitive complexity
  (whitepaper / `--sonar-compat`), lexical Halstead, maintainability index,
  LOC family.
- Versioned ruling registry with immutable IDs, hand-computed consistency
  corpus, and the three mechanical gates (spec drift, ruling coverage,
  grammar integrity).
- CLI: `measure` (default), `spec show`, `env`, `cite`.
