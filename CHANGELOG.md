# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

Because codecaliper is a measurement instrument, every release entry states
three versions, not one:

- **package**: the Python package version (`codecaliper.__version__`),
- **spec**: the metric-to-syntax specification version
  (`src/codecaliper/spec/rulings/index.toml`). A spec MAJOR bump means at least
  one calibrated number changed.
- **grammars**: the exact calibrated tree-sitter grammar versions
  (`src/codecaliper/spec/validated_grammars.toml`).

## [Unreleased]

- package 0.2.1.dev0 · spec 1.2.0 · grammars: tree-sitter-python 0.25.0,
  tree-sitter-java 0.23.5, tree-sitter-go 0.25.0 (binding tree-sitter 0.26.0)

## [0.2.0] - 2026-07-17

- package 0.2.0 · spec 1.2.0 · grammars: tree-sitter-python 0.25.0,
  tree-sitter-java 0.23.5, tree-sitter-go 0.25.0 (binding tree-sitter 0.26.0)
- The package MINOR bump reflects a third language and a new runtime dependency
  (tree-sitter-go); no previously emitted number changed, so the spec bump is a
  MINOR too (1.1.0 -> 1.2.0).

### Go language support (spec 1.2.0)

- Go is the third language, and the first added since the extension seam was
  tightened. It is confined to the `languages/` package: `languages/go.py` plus
  its registry entry, no edit to the metric engines, readability, model, API,
  CLI or grammar loader. Nine new rulings (CC-GO-0001..0005, COG-GO-0001,
  TOK-GO-0001, BW-GO-0001, BW-GO-0002); every other rule is a reused `-ALL-`
  ruling. Spec bumped 1.1.0 -> 1.2.0 (MINOR: additive, no existing corpus value
  changed).
- Notable Go-specific rulings: `for` is the only loop keyword and covers every
  loop form; `select` communication cases are a distinct cyclomatic ruling from
  switch cases; labeled break/continue and `goto` are a fundamental cognitive
  +1 in both modes; `true`/`false`/`nil`/`iota` are predeclared IDENTIFIERS, not
  keywords (a spec-faithful divergence from Java's BW keyword set).
- Cross-checked against lizard (the Go cyclomatic oracle), which concurs on
  every Go probe. Eight hand-computed corpus cases. `docs/adding-a-language.md`
  documents the whole procedure with Go as the worked example.

### A new language is now confined to the `languages/` package

- No emitted number changed: this is a plumbing refactor, and the spec-drift
  gate proves every corpus value is untouched.
- Two duplications of the language set that used to sit outside `languages/`
  were folded back in. `syntax/grammars.py` no longer keeps a `_GRAMMAR_MODULES`
  dict; `load(language_name, module)` takes the tree-sitter package name from
  the adapter, which now carries it as `LanguageAdapter.grammar_module`. `cli.py`
  no longer hardcodes `--lang choices`; it derives them from the registry via
  `available_languages()`. Adding a language therefore touches only a new adapter
  module and the registry in `languages/__init__.py`; the CLI and the grammar
  loader need no edit. (Internal API: `grammars.load` gained a required `module`
  argument.)

## [0.1.1] - 2026-07-14

- package 0.1.1 · spec 1.1.0 · grammars: tree-sitter-python 0.25.0,
  tree-sitter-java 0.23.5 (binding tree-sitter 0.26.0)
- No emitted number changed in this cycle. The spec stays at 1.1.0.

### The Buse-Weimer lane is now self-contained

- **Permission obtained.** Westley Weimer, an author of the Buse-Weimer
  dataset, granted redistribution of the raw snippets and annotator scores and
  publication of derived data, by e-mail on 2026-07-11 (DKIM-verified). New
  `PERMISSIONS.md` records the message date, Message-ID, authentication result
  and the sha256 of the retained original, states exactly what was asked and
  answered, and is explicit that this is a *permission*, not a licence, and
  that the accompanying citation request (cite both the TSE 2010 and the ISSTA
  2008 paper) is a request, not a condition. This project honours it anyway.
- **The raw inputs are now tracked**, under that grant, in
  `validation/bw_faithfulness/derived/arbitration_inputs/`: the 100 Java
  snippets (`snippets/1.jsnp` … `100.jsnp`), `oracle.csv` (the 121-row
  per-annotator matrix) and `scores.csv` (the per-snippet means derived from
  it). 102 files, 57,168 bytes.
- **The lane therefore reproduces offline.** `extract.py`, `train.py`,
  `report.py` and `arbitrate.py` read the tracked pins as their primary source.
  With no network and no `cache/`, they run to completion and regenerate the
  seven artifacts they write, byte-for-byte. (`features_fallback_off.csv` is not
  among them: it is a pinned input, the pre-`BW-ALL-0007` extraction that the
  arbitration compares against, and `arbitrate.py` fails if it is missing.) This
  is what the 0.1.0 changelog claimed prematurely (see the correction under
  [0.1.0] below); it is true now.
- **Two gates enforce the input contract** (new `pinned.py`): a missing tracked
  input is a hard error, exit 1, never a SKIP, so a lane that measured nothing
  can no longer exit 0 and read as a successful run; and when
  `cache/DatasetBW.zip` is present, every pin is cross-checked byte-for-byte
  against it, with any difference a hard error rather than a silent re-pin.
  `pin_inputs.py` records how the pins were produced and is not on the
  reproduction path. Every SKIP-and-exit-0 path is gone from the lane.
- The permission asymmetry between the three corpora has a canonical home:
  `PERMISSIONS.md` in prose, `validation/bw_faithfulness/dataset.toml` in
  machine-readable form, which `fetch.py` enforces. Every other document that
  touches the question states the consequence it needs, which is normally just
  "this lane needs the network and that one does not", and links to those two.
  The Buse-Weimer corpus remains the only dataset content in the tracked tree;
  the Scalabrino et al. (2018) and Dorn (2012) corpora have no permission of any
  kind, and not one byte of either is or will be tracked.

### PMD is wired as the Java differential oracle

- **PMD 7.26.0 witnesses both cyclomatic and cognitive complexity, per method, for
  Java.** It is the first external witness Java cognitive complexity has had in this
  project, and the second for Java cyclomatic (lizard was the only one). It is
  independent of tree-sitter all the way down, its own Java grammar and its own
  metric visitors, so agreement with it is not two wrappers around one parser
  agreeing with themselves. Coverage: 16 Java inputs (9 reference-comparable corpus
  cases plus 7 probes) x 2 metrics = 32 per-method comparisons, of which 28 agree.
- **Four new classified divergences** (`tests/differential/divergences.toml`,
  rendered to `docs/spec/divergences.md`):
  - `java-contextual-001` / `Point.quadrant` and `snippet:diff-java-switch-expr` /
    `SwExpr.grade`, cognitive, ours 1, PMD 0 (COG-ALL-0001). One gap, hit twice:
    PMD's CognitiveComplexity rule scores a switch *expression* zero. Measured on
    all four forms: it counts arrow-form and colon-form switch *statements*,
    agreeing with us, and zeroes both forms of switch expression, while its own
    CyclomaticComplexity rule counts all four. The gap is
    expression-versus-statement, and it is specific to PMD's cognitive rule.
  - `snippet:diff-java-recursion` / `R.fact`, cognitive, ours 1, PMD 2
    (COG-ALL-0006). PMD takes the whitepaper's +1-per-recursive-call increment;
    comparisons run in sonar-compat mode, which omits it. The Python oracle
    `cognitive_complexity` 1.3 takes the same side (`py-recursion-001`).
  - `snippet:diff-java-lambda` / `L.make`, cyclomatic, ours 2, PMD 1
    (CORE-ALL-0003). PMD's CyclomaticComplexity rule neither descends into a lambda
    body nor reports the lambda as a unit of its own, so the lambda's `if` is
    counted nowhere. Two witnesses put PMD alone: lizard scores `make` 2, and PMD's
    own CognitiveComplexity rule *does* descend into the lambda (cognitive 2). PMD's
    two rules disagree with each other.
- **The residual gap, named.** Recursion is the one axis on which the two cognitive
  modes differ, and PMD takes the whitepaper side: on that row it witnesses the
  whitepaper mode, which scores 2 and agrees with it exactly. Java's sonar-compat
  recursion behaviour therefore still has **no external witness**, and rests on the
  hand-computed corpus and the spec alone. The Java witnessing gap is narrowed, not
  closed.
- **No measured value changed.** PMD is a test-time oracle, never a runtime
  dependency, and the spec stays at 1.1.0.
- **Running it.** PMD is a JVM tool, so it is not in the `oracles` pip extra: it
  needs `java` on PATH and `python tools/fetch_pmd.py`, which downloads about 73 MB
  and sha256-verifies it against the pin in `tests/differential/pmd.toml`, into the
  gitignored `.oracles/`. Sitting outside the pip closure that `constraints/ci.txt`
  pins is precisely why PMD was cut at 0.1.0. Without PMD, or without a JVM, the
  lane SKIPs with an actionable reason, exactly like the pip oracles. CI does not get
  that option: the `differential` job in `ci.yml` installs a JVM (temurin 21), runs
  `tools/fetch_pmd.py` and hard-gates on `pmd --version` before pytest, because a
  SKIP there would let the job pass while testing nothing.

### Other

- `validation/breadth/`: the cross-corpus parse-anatomy lane (parse rates over
  the three corpora, plus a Python demo). It **requires a network fetch and
  always will**, because two of its three corpora may not be redistributed.
- `validation/bw_faithfulness/dataset.toml` now carries all three corpora with
  their per-corpus permission status, as the machine-readable form of
  `PERMISSIONS.md`, and `fetch.py` enforces it.
- ORCID recorded for the author in `CITATION.cff`
  (0009-0009-9835-3800).
- Root documentation overhauled: `README.md`, `ARCHITECTURE.md` and `CLAUDE.md`
  had been restating each other. Each now declares what it is for and owns that
  content alone (README: what the tool is and how to use it; ARCHITECTURE: the
  requirements record, rationale and decision log; CLAUDE.md: agent operating
  instructions). Two sections of `ARCHITECTURE.md` were describing code that
  does not exist and have been rewritten against it. §8.3 still said the corpus
  licence was "unstated", that the data was "never committed", and that a
  missing archive produced an honest SKIP; all three had become false. §7.3
  claimed bare Java snippets yield ERROR-dense trees and are always re-parsed
  inside one `class __CC__ { void __cc__() { … } }` wrapper. In fact
  tree-sitter-java's `program` rule accepts bare statement sequences and bare
  method declarations (CORE-JAVA-0001), scaffolding is a fallback with two
  candidate wrappers and a strict error-count minimizer that is adopted only
  when it beats the bare parse, and 10 of the 100 dataset snippets actually take
  it.
- Three false claims in that documentation, all of them written rather than
  checked, are corrected against the code:
  - "Adding a language touches zero core code" (ARCHITECTURE §5, repeated in
    `CLAUDE.md`) was wrong in both files. A third language must also edit
    `languages/__init__.py` (`_BUILTIN`, `get_adapter()`), `syntax/grammars.py`
    (`_GRAMMAR_MODULES`, an unguarded dict lookup that raises a bare `KeyError`)
    and `cli.py` (`--lang choices`, which rejects an unlisted language outright).
    The "Adding a language" checklist in `CONTRIBUTING.md` now names all three
    and says what each one's failure looks like.
  - ARCHITECTURE §11 and an earlier draft of this entry said the docs site has
    deliberately no contributor page. It has had one since W7: `mkdocs.yml`'s nav
    lists it, and `docs/contributing.md` is a snippet transclusion of
    `CONTRIBUTING.md`, so the checklists are hosted on the site without existing
    in two versions. The file that is linked rather than re-hosted is
    `ARCHITECTURE.md`.
  - ARCHITECTURE §3.4 introduced a `divergences.toml` stanza as a real record
    while silently dropping a clause from its `reason` and adding four inline
    comments the file does not contain. It is now quoted exactly, with the field
    glosses moved to prose.
- `CONTRIBUTING.md` gains "Superseding a ruling": which two fields go on the
  retired stanza (`status`, `superseded_by`), what the successor needs
  (`since_spec`, a corpus case citing it), and the fact that the spec level is
  set by the drift gate rather than by the supersession (TOK-ALL-0004 →
  TOK-ALL-0006 moved numbers and was a MAJOR; TOK-PY-0001 → TOK-PY-0002 did not
  and was a MINOR).
- `mypy` is listed as a hard CI gate in `CONTRIBUTING.md`'s setup and README's
  development section. It was in `ci.yml` and in `CLAUDE.md`, so the agent was
  told and the human was not.
- README pointed at `arbitration_report.md` for its tab-width correlations. That
  file carries the verdict, not the numbers: they are in
  `arbitration_report.json` and, for the adopted setting,
  `bw_faithfulness_report.md`'s per-feature table. README also now states the
  annotator count as the tracked `oracle.csv` has it (121 rows, against the
  paper's 120, reported and not reconciled).
- `RELEASING.md` documents the release-order constraint the derived reports
  impose (finalise `_version.py` *before* regenerating them; see [0.1.0]).

## [0.1.0] - 2026-07-12

- package 0.1.0 · spec 1.1.0 · grammars: tree-sitter-python 0.25.0,
  tree-sitter-java 0.23.5 (binding tree-sitter 0.26.0)

> **Correction (recorded after the fact, not rewritten away).** As originally
> published, the entry below claimed that the 32-cell arbitration "now re-runs
> end-to-end from pinned tracked inputs". That overstated what 0.1.0 shipped.
> What was actually tracked at the v0.1.0 tag were *derived intermediates* of
> the experiment: the reconstructed fallback_on/tab=1 feature matrix, the
> pre-fallback baseline training record, and the arbitration-time extraction
> stamps. The **raw** inputs were not tracked: `git ls-tree v0.1.0
> validation/bw_faithfulness/derived/arbitration_inputs/` contains no snippets
> and no `oracle.csv`. Every script in the lane still needed
> `cache/DatasetBW.zip`, which had to be downloaded, and
> `git show v0.1.0:validation/bw_faithfulness/arbitrate.py` shows it printing a
> SKIP and exiting 0 when the archive was absent. So at 0.1.0 the experiment's
> *analysis* was auditable from the tree, but the reproduction was not runnable
> from it. The claim became true only in the [Unreleased] cycle above, once an
> author granted redistribution and the raw inputs were tracked.
>
> A second, smaller defect of the same release: the archived reports under
> `derived/` are stamped "codecaliper 0.1.0.dev0", because they were regenerated
> before `_version.py` was finalised. The numbers are correct; the version
> string on them is the pre-release one. The ordering that prevents this is now
> written down in `RELEASING.md`.

- **Spec 1.1.0** (MINOR: new rulings plus table completions; no existing corpus
  value changed, verified through the drift gate) from a whole-project
  adversarial review:
  - COG-JAVA-0001: labeled `break`/`continue` are a flat +1 in both cognitive
    modes. The whitepaper's fundamental increment was silently missing for
    Java, and invisible to the differential lane, whose only cognitive oracle
    is Python-only.
  - TOK-ALL-0007: anonymous word tokens outside the keyword table are
    identifiers (Python `__future__`, Java contextual keywords, previously
    OPERATOR). Java's keyword table dropped contextual `yield`, matching
    BW-JAVA-0001's stated set.
  - lloc statement tables completed to LOC-ALL-0004's stated scope (Python:
    future/type-alias/legacy print+exec statements; Java: package/import and
    all type declarations, constants, initializers, compact constructors,
    explicit constructor invocations, module declarations/directives).
  - TOK-PY-0002 supersedes TOK-PY-0001: `concatenated_string` (implicit
    concatenation) is descended, so string parts are separate STRING tokens and
    an interleaved comment is an ordinary COMMENT token, matching CPython
    tokenize. The superseded ruling swallowed such comments into one string
    token, undercounting comment lines and counting the comment-only line as
    code.
  - TOK-JAVA-0002: Java `_` is an IDENTIFIER token in every position. The
    grammar's `underscore_pattern` (unnamed variable declarators) previously
    lexed as OTHER, invisible to BW and Halstead, while `_` in pattern and
    lambda positions already lexed as an identifier.
  - TOK-PY-0003: Python `...` (the named `ellipsis` leaf) is an OPERATOR token,
    matching CPython tokenize's OP and Java's varargs `...`, so it is visible to
    Halstead. Before this it fell through to OTHER, systematically undercounting
    `.pyi` stub bodies.
  - COG-ALL-0006's justification corrected editorially (it falsely claimed the
    `cognitive_complexity` package omits the recursion increment); the normative
    content is unchanged. BW-JAVA-0001 gained a disclosed editorial
    clarification (its table omits the JLS-reserved `_`, ruled an identifier by
    TOK-JAVA-0002).
  - Corpus 20 -> 26 cases (`java-labeled-jump-001`, `java-contextual-001`,
    `py-future-import-001`, `py-concat-string-001`, `java-underscore-001`,
    `py-ellipsis-001`), hand-computed as always.
- Correctness fixes (same review): CSV per-function BW vectors join by
  (name, span), where Java overloads and Python redefinitions previously all got
  the last unit's numbers; `encoding-replaced` no longer fires on valid UTF-8
  that legitimately contains U+FFFD; Java cognitive values no longer cite the
  Python-only COG-PY-0001; provenance `rulings_applied` now includes
  observably-fired normalization rulings (TOK-ALL-0001/0002/0003) and the
  cyclomatic base CC-ALL-0001, which now also appears in `--explain` traces, so
  increments sum to the emitted value; BW vectors cite their language-specific
  and tokenization rulings (including TOK-ALL-0006); `spec show` and the
  generated rulings doc surface `superseded_by`; the spec-drift gate can no
  longer disarm itself (any snapshot/spec version mismatch or unsnapshotted case
  is red, enforced alongside a new supersession-chain consistency test);
  `--json` and `--csv` are mutually exclusive; an unwritable `-o` path is a clean
  error.
- Provenance completeness (review round 2): every diagnostic-cited ruling now
  reaches `rulings_applied`, so parse-error runs cite CORE-ALL-0002 and
  scaffolded snippets cite CORE-JAVA-0001, exactly as their diagnostics already
  claimed; TOK-ALL-0007 fires into provenance and the BW/Halstead ruling lists
  whenever an anonymous word token actually lexed; the language's atomic-token
  rulings (TOK-PY-0002, TOK-JAVA-0001) are cited by every token-derived value
  (BW vectors, Halstead, LOC); at `--bw-granularity function`, a parse error
  outside every function no longer produces a report-level `bw-lexical-fallback`
  claim (no emitted number was affected).
- More round-2 fixes: `--explain` trace spans are clamped to the measured line
  domain, so the cyclomatic base trace no longer leaks scaffold coordinates
  (line 0, phantom trailing lines) on scaffolded Java snippets; `lloc` values now
  carry their per-increment `--explain` trace instead of silently dropping it;
  `Session` rejects unknown `cognitive_mode` and `granularity` strings (an
  invalid mode previously measured as sonar-compat while stamping the bogus
  string into provenance); the spec-drift gate also asserts per-case metric
  key-set equality, so a snapshot that lost keys can no longer narrow the gate
  silently, and `update_snapshot.py` refuses to re-adopt such a loss;
  `constraints/retrain.txt` gained the missing `narwhals` pin (the closure claim
  was false) and both validation scripts stamp its version; `arbitrate.py` SKIPs
  when the pinned extraction record is missing instead of writing a report with
  null stamps; and the reconciliation note no longer mislabels the re-stamped
  `train_results.json` as "under spec 1.0.0".
- Provenance precision (review round 3): the construct-specific tokenization
  rulings (TOK-ALL-0007 anonymous words, TOK-JAVA-0002 `_`) are now cited
  per-occurrence and per-unit, so a per-function BW vector no longer inherits a
  file-global TOK-ALL-0007 when the anonymous word lies outside its own span, and
  a Java file without `_` no longer cites TOK-JAVA-0002. Only the static
  atomic-string rulings TOK-PY-0002 and TOK-JAVA-0001 are cited unconditionally.
  Python's soft-keyword table is pinned to BW-PY-0001's enumerated set instead of
  the running interpreter's `keyword.softkwlist`, so a `type` alias classifies
  identically on every supported 3.10-3.14 interpreter (asserted at import time
  to stay a superset of the host).
- More round-3 fixes: `update_snapshot.py` treats a whole corpus case vanishing
  as a change requiring `--confirm-spec-bump` (deletion could previously drop
  coverage silently), and `tools_snapshot.py` disambiguates colliding per-unit
  and per-vector snapshot keys by span, so a future overload or multi-vector case
  cannot silently narrow the drift gate. Several disclosed editorial corrections:
  HAL-ALL-0001 and ARCHITECTURE describe the lexical-versus-AST Halstead
  divergence as *declared*, since there is no Halstead differential lane, rather
  than "classified"; CC-PY-0004's lizard note now states the real divergence;
  ARCHITECTURE §5's adapter description no longer names a nonexistent
  `token_kind_map` or claims Halstead shares the operator-class tables; the
  honesty and quickstart pages describe the BW fallback as conditional; README
  and index say "every *active* ruling"; the arbitration reproduction recipe pins
  the calibrated grammars (`constraints/ci.txt`).
- Arbitration auditability: the 32-cell experiment's derived intermediates are
  tracked under `derived/arbitration_inputs/` (the never-committed fallback_on
  and tab=1 matrix reconstructed exactly, the pre-fallback baseline record, the
  arbitration-time extraction stamps), so its analysis can be re-derived and
  diffed. The regenerated report carries accurate input provenance, an ML-stack
  version stamp, and a reconciliation note for the one-ranked-pair (0.0004) AUC
  gap between the matrix cell (0.827) and the final headline (0.828).
  `constraints/retrain.txt` pins the ML stack, and `train_results.json` now stamps
  the sklearn and numpy versions (numbers unchanged, verified). Running the
  experiment still required downloading `cache/DatasetBW.zip`; see the correction
  above.
- CI: the weekly grammar early-warning probe no longer false-alarms on every
  newer wheel (the pin-equality test is deselected; the drift and node-inventory
  checks remain); `constraints/build.txt` is now the complete PEP 517 closure. New
  `tests/test_cli.py` covers subcommand content, flag behaviour, exit codes, and
  the ModelArtifact feature-order-sha refusal.
- **Spec 1.0.0**: the first calibrated evolution, arbitrated by a pre-registered
  32-cell experiment on the original Buse-Weimer dataset
  (`validation/bw_faithfulness/derived/arbitration_report.md`):
  - TOK-ALL-0006 supersedes TOK-ALL-0004: indentation counts a tab as 8
    characters. Tab = 1 zeroed the paper's indentation/readability correlation,
    and the 8-versus-4 tie-break is a stated convention pick.
  - BW-ALL-0007: BW token-family features use the full lexical stream, ERROR
    regions included, because the construct is lexical. Metrics stay error-opaque
    (CORE-ALL-0002). Coverage on the original dataset: 8 empty-token vectors
    became 0.
  - The operator-class arbitration returned a null result; BW-ALL-0006 unchanged.
  - Faithfulness reproduction under the adopted rulings: 10-fold logistic
    accuracy 0.820 (bootstrap 95% CI [0.770, 0.870], overlapping the paper's
    roughly 0.80), AUC 0.828, Fig. 9 sign agreement 21/24.
- Corpus 19 -> 20 cases (`py-bw-fallback-001`); every active ruling remains
  corpus-covered.
- Release pipeline (`release.yml`): a tag-triggered gate, then build (tag,
  version and changelog guards), then PyPI trusted publishing, then the GitHub
  Release, which fires the Zenodo archival webhook. The procedure and one-time
  setup are in `RELEASING.md`.
- Docs site (mkdocs-material, deployed to GitHub Pages by `docs.yml`):
  quickstart, honesty invariants, generated spec rulings and divergence list, a
  validation page that verbatim-includes the derived faithfulness and arbitration
  reports, and an mkdocstrings API reference. The toolchain is pinned in
  `constraints/docs.txt`, separately from the instrument's calibrated pins.
- `DIAGNOSTIC_CODES` now includes `bw-lexical-fallback`, and the closed set is
  enforced by a corpus sweep test instead of by a comment (no emitted value
  changed).
- `CITATION.cff`: the hand-maintained `version` was removed, since Zenodo and
  GitHub take it from the release itself; the docs URL was added.
- Initial scaffold: the unified tree-sitter measurement base (Python and Java),
  the Buse-Weimer 25-feature extractor (fidelity-tested against the reference
  implementation), cyclomatic complexity, dual-mode cognitive complexity
  (whitepaper and `--sonar-compat`), lexical Halstead, the maintainability index,
  and the LOC family.
- The versioned ruling registry with immutable IDs, the hand-computed consistency
  corpus, and the three mechanical gates (spec drift, ruling coverage, grammar
  integrity).
- CLI: `measure` (default), `spec show`, `env`, `cite`.
