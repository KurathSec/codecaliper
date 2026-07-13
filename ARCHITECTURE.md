# codecaliper: Architecture

> **What this document is.** The authoritative requirements record: why codecaliper is built the
> way it is, what was decided, and what was rejected. When it disagrees with any other prose in
> the repo, it wins. When it disagrees with the code, the code wins and this file has a bug.
>
> **What it is not.** It is not a user guide (that is `README.md`) and not a set of operating
> instructions for an agent working in the tree (that is `CLAUDE.md`). Neither of those files
> repeats the rationale below; this one does not repeat their content.
>
> **Design thesis.** Every number codecaliper emits is *traceable* and *reproducible*: traceable to
> a spec version, to the exact rulings that fired, and to the exact grammar that parsed the source;
> reproducible because it is clock-free, hash-seed-free and order-stable. Where a scoreboard says
> "CC = 7", this instrument says "CC = 7 *under spec 1.1.0, ruling CC-PY-0003, tree-sitter-python
> 0.25.0*". That sentence is the data model.
>
> This document synthesizes a three-way architecture study (instrument-purist, API/extensibility,
> validation-first lenses) judged against the project charter. The charter itself is deliberately
> not in the repo, so this file replaced it. Charter section references (§5 design, §6 validation,
> §7 publication checklist, §8 risks) appear throughout; §0 restates every fixed decision they
> pinned, and §14 records what was chosen over what.

## 0. Fixed decisions (from the charter; do not relitigate)

- **MVP languages: Python + Java.** Java is the Buse-Weimer (BW) native language, which is what
  makes the §6.3 faithfulness reproduction possible. That reproduction is the project's main piece
  of external evidence that the extractor implements what the paper describes.
- **tree-sitter is the unified syntactic base.** Metrics operate on the **pre-preprocessing
  source text**, declared honestly: the C-family preprocessor makes any syntactic tool an
  approximation.
- **Cognitive complexity is dual-mode**: default *whitepaper-faithful*, `--sonar-compat` opt-in.
  Every inter-mode divergence is an enumerable, mode-tagged ruling.
- **1.0 readability scope: faithful BW features only.** Scalabrino and Dorn slot into the same
  `FeatureSet` seam in 1.x without model changes.
- **BW feature extraction is decoupled from any trained model.** The API returns raw 25-feature
  vectors. There is deliberately **no** `bw_score` anywhere. A retraining scaffold ships instead
  of weights.
- **External tools are differential-test oracles only** (radon, lizard, cognitive_complexity, PMD,
  rust-code-analysis), never runtime backends. A missing oracle is an honest SKIP.
- The old Spaghetti-Architect regex lane is **demoted**: its per-language ruling knowledge is
  mined into the spec, and its proven implementations survive only as *test-only internal
  oracles*.
- **Procedural consistency, not numerical comparability.** The tool guarantees identical rules
  over isomorphic syntactic structures across languages. It does *not* claim CC numbers are
  directly comparable across languages. Saying so out loud is a feature (§13).

## 1. Package / module tree (src layout)

```
codecaliper/
├── pyproject.toml               # hatchling; requires-python >=3.10
├── LICENSE                      # MIT
├── NOTICE                       # primitives descend from Spaghetti Architect (DOI 10.5281/zenodo.21033174);
│                                #   data attribution for the redistributed Buse-Weimer corpus
├── PERMISSIONS.md               # ★ the terms of all three corpora, in prose (dataset.toml is the machine form)
├── CITATION.cff  README.md  ARCHITECTURE.md  CLAUDE.md  CHANGELOG.md
├── CONTRIBUTING.md  CODE_OF_CONDUCT.md  RELEASING.md  SECURITY.md
├── mkdocs.yml                   # site config; the nav is §11
├── constraints/                 # ★ pin files: ci.txt (exact grammar + oracle pins for CI/releases),
│                                #   build.txt (PEP 517 closure), docs.txt, retrain.txt (ML stack)
├── src/codecaliper/
│   ├── __init__.py              # public API re-exports; __version__
│   ├── py.typed
│   ├── _version.py
│   ├── api.py                   # typed façade: measure(), measure_file(), Session
│   ├── cli.py                   # argparse: measure (default) | spec | env | cite
│   ├── canonical.py             # deterministic JSON/CSV serialization (float policy CORE-ALL-0004)
│   ├── errors.py                # CodecaliperError tree
│   ├── model.py                 # frozen result dataclasses (§2)
│   ├── spec/
│   │   ├── __init__.py          # spec_version(), require(), ruling(), iter_rulings(), Ruling
│   │   ├── registry.py          # loads rulings TOML; require(id) fails at import on phantom IDs
│   │   ├── rulings/             # ★ the versioned metric-to-syntax mapping spec (TOML package data)
│   │   │   ├── index.toml       # spec version, changelog
│   │   │   ├── core.toml        # CORE-*: parse policy, error nodes, nested-unit attribution,
│   │   │   │                    #         snippet scaffolding, float emission policy
│   │   │   ├── tokenization.toml# TOK-*: encoding, BOM, CRLF, tabs, atomic tokens
│   │   │   ├── cyclomatic.toml  # CC-ALL-*, CC-PY-*, CC-JAVA-*
│   │   │   ├── cognitive.toml   # COG-* (mode-tagged where the two modes diverge)
│   │   │   ├── halstead.toml    # HAL-*
│   │   │   ├── mi.toml          # MI-*
│   │   │   ├── loc.toml         # LOC-*
│   │   │   └── bw.toml          # BW-*: the 25 features' delimitation rulings
│   │   └── validated_grammars.toml  # grammar versions this release is calibrated against
│   │   # (classified divergences live TEST-side in tests/differential/divergences.toml;
│   │   #  the published artifact is the generated docs/spec/divergences.md)
│   ├── syntax/
│   │   ├── _treesitter.py       # ★ the ONLY module importing tree_sitter: load/parse/walk/leaves
│   │   │                        #   + version shims + Language.node_kind introspection
│   │   ├── grammars.py          # GrammarInfo capture; validated flag (never refuses, always labels)
│   │   └── tokens.py            # normalize() + the unified per-line LexicalToken stream
│   │                            #   and TokenKind enum (leaf walk + atomic tokens)
│   ├── languages/
│   │   ├── __init__.py          # plain dict registry; detect_language() for --lang auto
│   │   ├── base.py              # LanguageAdapter protocol; NodeClass enum; Classified (TokenKind
│   │   │                        #   lives with the lexer, in syntax/tokens.py)
│   │   ├── python.py            # classification dicts + named hook methods, every row cites rulings
│   │   └── java.py
│   ├── metrics/
│   │   ├── base.py              # MetricContext.count(ruling, node, delta): the trace/audit seam
│   │   ├── cyclomatic.py        # decision points over NodeClass
│   │   ├── cognitive.py         # ONE walker, two frozen CognitiveRules tables (whitepaper/sonar)
│   │   ├── halstead.py          # LEXICAL Halstead over the token stream (declared approximation)
│   │   ├── mi.py                # derived_from=("halstead.volume","cyclomatic","sloc")
│   │   └── loc.py               # physical/blank/comment/sloc/lloc
│   └── readability/
│       ├── base.py              # FeatureSet protocol + registry (bw2010 now; scalabrino/dorn later)
│       ├── bw2010.py            # the 25 Fig.6 features; BW_FEATURE_NAMES canonical order + sha
│       ├── granularity.py       # snippet/function/file segmentation; extrapolation labelling
│       └── retrain.py           # scaffold: JSON model artifacts, never pickle, never bundled weights
├── tests/
│   ├── conftest.py              # corpus loading shared by every gate
│   ├── corpus/                  # ★ §6.1 consistency corpus: <lang>/<case-id>/{input.*, expected.toml}
│   │                            #   26 cases today: 16 python, 10 java
│   ├── snapshots/corpus_values.json   # ★ spec-drift snapshot (spec+grammar stamped)
│   ├── tools_snapshot.py        # the corpus-value computation the drift gate and
│   │                            #   tools/update_snapshot.py share, so they cannot disagree
│   ├── _reference/              # test-only verbatim ports (NOTICE-credited):
│   │   ├── bw_stdlib.py         #   anchor.py::bw_readability_features (stdlib tokenize)
│   │   └── py_ast_lane.py       #   eval/metrics.py cyclomatic/cognitive/halstead/MI (stdlib ast)
│   ├── differential/            # external-oracle lane: divergences.toml, _harness.py, and
│   │                            #   test_radon / test_lizard / test_cognitive / test_table
│   ├── test_consistency_corpus.py
│   ├── test_spec_coverage.py    # rulings ⇄ code ⇄ corpus bidirectional coverage
│   ├── test_spec_drift.py       # numbers may not change without a spec MAJOR bump
│   ├── test_grammar_integrity.py# adapter tables validated against the COMPILED grammar
│   ├── test_bw_port_fidelity.py # tree-sitter BW vs stdlib reference, per feature
│   ├── test_python_lane_crosscheck.py  # tree-sitter Python metrics vs ported AST lane
│   ├── test_measure_behavior.py # the policies a value assertion cannot carry: error recovery,
│   │                            #   granularity labelling, the Java scaffold, provenance completeness
│   ├── test_cli.py              # subcommand output, flags, exit codes, error paths (§9)
│   ├── test_determinism.py      # two runs, different PYTHONHASHSEED, byte-identical output
│   └── test_perf_smoke.py       # throughput floor; parser/spec-registry reuse assertions
├── validation/bw_faithfulness/  # ★ §6.3 pipeline (repo-only, never in the wheel)
│   ├── dataset.toml             # per-corpus URL + sha256 + permission status
│   ├── pinned.py                # ★ the INPUT CONTRACT: tracked pins are primary, cache/ is a cross-check
│   ├── pin_inputs.py            # how the pins were produced (NOT on the reproduction path)
│   ├── fig9_signs.toml          # the paper's Fig. 9 directionality, keyed by BW_FEATURE_NAMES
│   ├── stats.py                 # spearman / ci95_bootstrap, pure stdlib (from bench/grade.py)
│   ├── fetch.py  extract.py  train.py  report.py  arbitrate.py  README.md
│   └── derived/                 # ★ TRACKED: the pinned raw inputs (§8.3) + every derived artifact
│       ├── arbitration_inputs/  #   snippets/1..100.jsnp, oracle.csv, scores.csv (the raw pins),
│       │                        #   plus arbitrate.py's pinned pre-arbitration matrix, its meta,
│       │                        #   and the pre-fallback training record it compares against
│       ├── features.csv  features_fallback_off.csv  extract_meta.json  train_results.json
│       ├── bw_faithfulness_report.{md,json}
│       └── arbitration_report.{md,json}
├── validation/breadth/          # cross-corpus parse anatomy (3 corpora) + Python demo.
│   └── measure_corpora.py  results.txt  README.md  python-demo/  # NEEDS A NETWORK FETCH (§8.3)
├── tools/
│   ├── gen_spec_docs.py         # ruling TOMLs → docs/spec/rulings.md (generated, staleness-checked)
│   ├── gen_divergences.py       # classification TOMLs → docs/spec/divergences.md
│   └── update_snapshot.py       # refuses numeric changes without --confirm-spec-bump
├── docs/                        # index, quickstart, honesty, validation, api + the generated spec/
└── .github/workflows/           # ci.yml (test / typecheck / spec-docs / differential jobs),
                                 #   docs.yml, grammar-bump.yml, release.yml
```

Three structural invariants:

1. `tree_sitter` is imported **only** in `syntax/_treesitter.py`. Gated by ruff
   (`banned-module-level-imports`, with one sanctioned per-file ignore).
2. `metrics/` and `readability/` never mention a concrete tree-sitter node-type string. They
   consume `NodeClass` and `TokenKind`, and where an engine does touch `node.type` it compares
   against an adapter-supplied table rather than a literal (`loc.py` against
   `adapter.statement_types`). This one is upheld by the seam and by review; no lint enforces it.
3. Oracles and the legacy reference ports live **only** under `tests/`, and cannot be imported
   from `src/`. `test_spec_coverage.py::test_src_never_imports_test_oracles` reads every file under
   `src/` and fails on any of the banned names, so the anti-salami boundary is a red build rather
   than a promise.

## 2. Core data model (`model.py`)

All frozen `@dataclass(frozen=True, slots=True)`; no timestamps anywhere; canonical field order.

```python
Granularity = Literal["snippet", "function", "file"]

@dataclass(frozen=True, slots=True)
class GrammarInfo:
    language: str            # "python"
    package: str             # "tree-sitter-python"
    version: str             # actually-installed version (importlib.metadata)
    abi_version: int         # Language.abi_version
    validated: bool          # matches spec/validated_grammars.toml? (never refuse; label)

@dataclass(frozen=True, slots=True)
class Provenance:
    tool_version: str
    spec_version: str        # ★ on every report
    language: str
    grammar: GrammarInfo
    modes: tuple[tuple[str, str], ...]  # (("cognitive", "whitepaper"),) hashable, JSON-objectified
    rulings_applied: tuple[str, ...]   # sorted, deduped IDs governing the emitted values
                                       # (conditional rulings fire per-occurrence; structural/
                                       #  convention rulings are cited whenever they govern)

@dataclass(frozen=True, slots=True)
class Diagnostic:
    severity: Literal["info", "warning", "error"]
    code: str    # closed set: parse-error-recovered | unvalidated-grammar | granularity-extrapolated
                 #             | snippet-out-of-calibrated-range | mi-contains-cc
                 #             | halstead-approximation | encoding-replaced | snippet-scaffolded
                 #             | bom-stripped | bw-lexical-fallback
                 # (authoritative: DIAGNOSTIC_CODES in model.py; membership is
                 # enforced across the corpus by test_diagnostic_codes_are_a_closed_set)
    message: str
    span: Span | None = None
    ruling: str | None = None

@dataclass(frozen=True, slots=True)
class RulingTrace:           # populated only with explain=True; zero cost on the default path
    ruling_id: str
    span: Span
    delta: float

@dataclass(frozen=True, slots=True)
class MetricValue:
    metric: str                          # "cyclomatic", "halstead.volume", ...
    value: int | float
    rulings: tuple[str, ...]             # ruling IDs governing this metric+language
    derived_from: tuple[str, ...] = ()   # MI: ("halstead.volume","cyclomatic","sloc"); §13 honesty, typed
    trace: tuple[RulingTrace, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()

@dataclass(frozen=True, slots=True)
class FeatureVectorResult:
    feature_set: str                     # "bw2010"
    granularity: Granularity
    native_granularity: Granularity      # "snippet" for bw2010
    extrapolated: bool                   # granularity != native_granularity
    names: tuple[str, ...]               # canonical Fig.6 order (= anchor.py _BW_FEATURE_NAMES)
    values: tuple[float, ...]
    rulings: tuple[str, ...]
    diagnostics: tuple[Diagnostic, ...]
    unit_name: str | None = None         # function name when granularity == "function"
    span: Span | None = None

@dataclass(frozen=True, slots=True)
class FunctionReport:
    name: str; qualified_name: str; span: Span
    metrics: tuple[MetricValue, ...]

@dataclass(frozen=True, slots=True)
class FileReport:
    path: str | None
    parse_ok: bool                       # False if ERROR/MISSING nodes present
    file_metrics: tuple[MetricValue, ...]
    functions: tuple[FunctionReport, ...]
    readability: tuple[FeatureVectorResult, ...]   # plural: Scalabrino/Dorn add entries, not model breaks
    diagnostics: tuple[Diagnostic, ...]
    provenance: Provenance | None        # None only for hand-built reports; measure() always sets it
```

Metric collections are order-stable tuples rather than mappings. `model.metric_map(values)` is the
keyed convenience view (`metric_map(report.file_metrics)["cyclomatic"]`).

Honesty is encoded in the types, not in the docs: MI always carries `mi-contains-cc` and a typed
`derived_from`; Halstead always carries `halstead-approximation`; `extrapolated` is a field that
flows into JSON and CSV. There is no score field to launder.

## 3. The spec mechanism

### 3.1 Rulings: machine-readable TOML with immutable IDs

One ruling is one decision about how a metric maps onto syntax. This is the shipped stanza for
CC-PY-0003, verbatim from `spec/rulings/cyclomatic.toml`:

```toml
[[ruling]]
id = "CC-PY-0003"
metric = "cyclomatic"
language = "python"
title = "Boolean short-circuit operators count per operator"
statement = """
Each `boolean_operator` node contributes one decision point. An N-operand chain
is (N-1) nested nodes, so `a and b or c` contributes 2 — each short-circuit is a
distinct execution path. Agrees with radon; diverges from tools that count a
whole chain as one.
"""
node_types = ["boolean_operator"]
examples = ["py-cc-boolop-001"]
```

The statement is normative, and it is a claim about *nodes*, not about a chain's arity: the engine
adds 1 per `boolean_operator` node it walks (§3.3, §6). `node_types` is validated against the
compiled grammar (§6.4 of the charter, `test_grammar_integrity.py`), and `examples` names the
corpus case that pins the value. Four further fields exist and are defaulted in `registry.py` when
a stanza omits them, which most do: `status` (`active`, or `superseded` alongside a
`superseded_by` ID), `since_spec`, and `mode`, which is set only where the two cognitive modes
diverge. `codecaliper spec show CC-PY-0003` renders the loaded record, which is the copy that
governs.

ID grammar: `{METRIC}-{LANG}-{NNNN}`, `METRIC ∈ {CORE, TOK, CC, COG, HAL, MI, LOC, BW}`,
`LANG ∈ {ALL, PY, JAVA, …}`. IDs are **immutable forever**. A changed decision *supersedes* the
old ruling under a new ID, so the audit trail survives.

### 3.2 Spec versioning (independent of the package version)

The spec version (semver) lives in `rulings/index.toml` as `[spec] version`, next to the spec's own
changelog, and reaches the API through `spec_version()`. **patch** = editorial; **minor** = new
rulings, no existing number changes; **major** = any change that alters any number for any
existing corpus case, *including a grammar pin bump that does so*.

Enforcement is mechanical. `test_spec_drift.py` recomputes every metric over the whole corpus and
compares against `tests/snapshots/corpus_values.json` (stamped with the spec and grammar
versions). Any drift without a major bump is a red build, and the snapshot is refreshed only via
`tools/update_snapshot.py --confirm-spec-bump`.

### 3.3 How code references rulings

Every ruling ID enters the code through `require()` at import time, so a phantom ID is an import
error rather than a wrong number. A node-bound ruling enters in the adapter that binds it, next to
the node type it governs (`languages/python.py`); an engine-level one, like the CC-ALL-0001 base
path, enters in the engine.

```python
R_CC_BOOLOP = require("CC-PY-0003")          # SpecError at import if the ID is phantom
...
return Classified(NodeClass.BOOL_OP, (R_CC_BOOLOP, R_COG_BOOLSEQ), new_sequence=not same_as_parent)
```

The engine never names the ruling or the node type. It sees a `NodeClass` in its decision set and
counts the first CC-prefixed ID the adapter attached, one increment per node
(`metrics/cyclomatic.py`):

```python
if c.node_class in _DECISION_CLASSES and ctx.in_range(node):
    for r in c.rulings:
        if r.startswith("CC-"):
            total += int(ctx.count(r, node, 1, metric="cyclomatic"))
            break
```

`MetricContext.count()` returns the delta, records the fired ID for provenance, and under
`explain=True` appends a `RulingTrace(ruling, span, delta)`; the engine does the accumulating.
`codecaliper FILE --explain` therefore gives per-increment attribution, which is what divergence
triage and downstream audit actually need. On `if a and b and c:` it prints two CC-PY-0003 lines,
one per `boolean_operator` node, each with delta 1 and its own span, next to the CC-ALL-0001 base
increment and the CC-PY-0001 `if`. Total 4.

`test_spec_coverage.py` asserts bidirectional coverage: every active ruling is referenced by
code **and** exercised by at least one corpus case, and every corpus citation and every non-empty
adapter table-row citation points at a real ruling covering that node type. Deleting a ruling
breaks an import; adding one without a corpus case fails the gate.

### 3.4 The known-divergence list is generated, complete by construction

Classified divergences are TOML records in `tests/differential/divergences.toml`. This is a shipped
record, verbatim:

```toml
[[divergence]]
oracle = "cognitive_complexity"
case = "py-nested-function-001"
unit = "outer"
metric = "cognitive"
ours = 3
theirs = 5
ruling = "CORE-ALL-0003"
reason = "cognitive_complexity scores a function including its nested defs (inner's `if` lands at nesting 2); CORE-ALL-0003 excludes nested named units, which get their own FunctionReports."
```

`case` is a corpus case ID or `snippet:<probe-name>`; `unit` is the codecaliper qualified function
name; `ours` is the value the cited `ruling` pins, and `theirs` is what the installed oracle
produced.

The differential harness fails CI on any **unclassified** divergence (the failure prints a
ready-to-paste stanza) and on any **stale** entry no longer observed, so the table is complete by
construction in both directions. Oracle versions are pinned in `constraints/ci.txt`, and a pin bump
re-runs the whole lane, re-surfacing every entry for re-triage. The published
`docs/spec/divergences.md` (generated by `tools/gen_divergences.py`, staleness-checked) is the
complete scholarly artifact the charter promises.

## 4. tree-sitter integration (`syntax/`)

`_treesitter.py` is the quarantine, the only importer of `tree_sitter`. It provides:

- `load_language(module_name) -> (Language, GrammarInfo)`. Wraps the grammar wheel's PyCapsule via
  `Language(mod.language())`; captures the version via `importlib.metadata` and the ABI via
  `abi_version` (with the `version → abi_version` deprecation shim); checks
  `spec/validated_grammars.toml` to set `GrammarInfo.validated`. **Deviation never refuses to
  run.** It stamps `validated=false` plus an `unvalidated-grammar` diagnostic on every report.
- `walk(tree)`. Cursor-based preorder `(node, depth)` iteration: O(1) memory, no recursion limit,
  deterministic order.
- `leaves(tree, atomic_types)`. The terminal-token stream for the lexer. Node types declared
  *atomic* (Python `string`, which has `string_start`/`content`/`end` children; Java
  `string_literal`) are consumed as **one token** (ruling TOK-\*).
- `node_kinds(language)`. Grammar introspection (`node_kind_count`, `node_kind_for_id`) used by
  `test_grammar_integrity.py` to validate every adapter-table entry and every ruling's
  `node_types` against the **actually compiled grammar**. A grammar node rename (the real
  tree-sitter-java `comment` → `line_comment`/`block_comment` case) fails loudly and specifically
  instead of silently zeroing metrics. No vendored `node-types.json` needed.

Verified environment shape (2026-07): binding `tree-sitter 0.26.0` (`Language(capsule)`,
`Parser(lang)`, ABI 15, min 13), grammar wheels `tree-sitter-python 0.25.0` and
`tree-sitter-java 0.23.5`. The grammar wheels enforce no runtime-compat constraint themselves
(their `core` extra is optional), so we pin both sides ourselves (§11). The MVP deliberately avoids
the Query API entirely, since cursor walks suffice; that sidesteps the 0.24/0.25
`Query → QueryCursor` churn. If queries are ever needed, the shim lives here.

Input normalization is itself ruled (TOK-ALL-\*): decode UTF-8 with replacement plus a diagnostic;
strip a UTF-8 BOM (diagnostic); CRLF to LF before measurement; a tab counts as 8 indentation
characters (TOK-ALL-0006, adopted by the pre-registered arbitration at spec 1.0.0, superseding
TOK-ALL-0004's provisional tab = 1; see §8.3 and §14). These change emitted numbers, so they are
spec, not implementation detail.

## 5. Language adapters (`languages/`)

Metric engines never see node-type strings, only this taxonomy:

```python
class NodeClass(Enum):
    BRANCH; ELIF_CONTINUATION; ELSE_CLAUSE; TERNARY; SWITCH; CASE_LABEL
    LOOP; CATCH; BOOL_OP; COMPREHENSION_GUARD; LAMBDA
    JUMP_LABEL  # labeled break/continue, COG-JAVA-0001
    FUNCTION_DEF; CLASS_DEF; NESTING_ONLY

class TokenKind(Enum):
    IDENTIFIER; KEYWORD; NUMBER; STRING; COMMENT; OPERATOR; PUNCT; OTHER
```

An adapter provides `node_class_map: dict[str, tuple[NodeClass, tuple[ruling_id, ...]]]` as plain
Python dicts. There is **no predicate DSL**: the three-way study showed that a `when.*`
mini-language costs an interpreter and hits expressiveness walls immediately. Alongside the map, an
adapter provides a small set of **named hook functions** for the contextual cases a table cannot
express (Python elif detection via the parent `if_statement`'s `alternative` field, for instance),
each hook citing a ruling; the token-classification frozensets (identifier, number, string,
comment, keyword-leaf and operator-leaf node-type sets); `atomic_types`; the operator-class tables
(arithmetic, comparison, assignment) which serve the BW-ALL-0006 operator-class features only,
Halstead classifying by `TokenKind` rather than by these tables; `conditional_token_rulings`;
`function_units()`; and the keyword list. `PythonAdapter` and `JavaAdapter` are thin. The behaviour
lives in the tables, every increment-bearing row cites a ruling (nesting-only rows carry an empty
tuple by design: no increment, nothing to cite), and the node-type strings are validated by the
grammar-integrity gate.

**Adding language #3** is a checklist in `CONTRIBUTING.md` ("Adding a language"), gated by the
existing meta-tests: new adapter module and tables, new `*-GO-*` rulings, corpus cases, an oracle
probe, a grammar pin.

The seam holds where it claims to: `metrics/`, `readability/` and `model.py` need no edit, because
they are written against `NodeClass` and `TokenKind` and never against a node-type string. `api.py`
needs none either, though it is not language-neutral: its snippet-scaffold fallback is guarded by
`adapter.name == "java"` (CORE-JAVA-0001), so a new language simply gets no scaffolding until a
ruling gives it one.

Three files outside `languages/` do have to change, and a contributor who is told otherwise walks
into them:

| file | what is hardcoded | symptom if skipped |
|---|---|---|
| `languages/__init__.py` | `_BUILTIN` tuple; `get_adapter()`'s if-chain | `UnsupportedLanguageError` |
| `syntax/grammars.py` | `_GRAMMAR_MODULES`, an unguarded dict lookup | bare `KeyError` from `load()` |
| `cli.py` | `--lang` `choices=["auto", "python", "java"]` | argparse rejects the language, exit 1 |

Only the first is registration in any meaningful sense; the other two are unparameterized lookups
that a fourth language would hit again. Making them one table is a 1.x cleanup, not a blocker. The
registry is a plain dict, and entry-point plugin discovery is deferred until a third party actually
exists.

## 6. Metric engines (`metrics/`)

All engines are pure functions of `(tree, adapter, MetricContext)`, and every increment routes
through `ctx.count(ruling, node, delta)`. Each computes file-level and per-function values.

- **cyclomatic**: `1 + Σ decision points`. Eight `NodeClass`es are decision classes (BRANCH,
  ELIF_CONTINUATION, LOOP, CATCH, CASE_LABEL, TERNARY, COMPREHENSION_GUARD, BOOL_OP) and each
  matching node adds exactly 1. The base 1 is itself an increment, routed through
  `ctx.count(CC-ALL-0001, root)` so that it appears in provenance and in `--explain` like any
  other. BOOL_OP is not a special case: tree-sitter parses a boolean chain as nested binary
  `boolean_operator` nodes, so `a and b or c` is two nodes and contributes 2, which is where
  CC-PY-0003's "(N-1) nested nodes" comes from (§3.1). A Python-AST tool reaches the same number by
  a different route, one `BoolOp` per operator run counted as operands minus one; the ported AST
  reference lane does exactly that, and `test_python_lane_crosscheck.py` holds the two lanes to
  equality on boolean chains.
- **cognitive (dual mode)**: **one** recursive walker parameterized by two frozen `CognitiveRules`
  tables (whitepaper default, sonar-compat). Elif chains are flattened in both modes; the walk is
  ported from the proven `eval/metrics.py::_traverse` and cross-checked against it in
  `test_python_lane_crosscheck.py`. Every field where the tables differ is a mode-tagged ruling,
  and corpus cases assert **both** mode values whenever they diverge. The spec table *is* the
  whitepaper-versus-Sonar diff.
- **halstead**: **lexical** Halstead (HAL-ALL-0001). Operators are OPERATOR + KEYWORD + PUNCT tokens
  per the adapter tables; operands are IDENTIFIER + NUMBER + STRING. Chosen over AST-harvesting for
  cross-language uniformity and lexer reuse. The divergence against radon and against the ported
  AST reference is *declared*, not classified, because no Halstead differential lane runs, and
  every value carries `halstead-approximation`: absolute values are implementation-defined, and
  only trends and ratios are stable.
- **mi**: `clamp₀₋₁₀₀((171 − 5.2·ln V − 0.23·CC − 16.2·ln SLOC)·100/171)`. MI-ALL-0001 pins the
  variant (no comment term). Typed `derived_from` plus a standing `mi-contains-cc` diagnostic.
- **loc**: physical, blank, comment (a block comment counts every line it spans, LOC-ALL-\*), sloc,
  and lloc (counted over the adapter's `statement_types` node-type table, LOC-ALL-0004). The corpus
  contains multi-line-string cases that the old regex lane provably gets wrong, which is the reason
  tree-sitter won.

**Nested-unit attribution is explicitly ruled** (CORE-ALL-\*), a gap all three designs missed and a
classic radon-versus-lizard divergence axis. A nested function, lambda or inner-class body counts
toward the *enclosing* function's file-level walk, but per-function values are computed on each
function's own subtree **excluding** nested `FUNCTION_DEF`, `LAMBDA` and `CLASS_DEF` subtrees, which
get their own `FunctionReport`s. File-level values come from one whole-file walk, and are *not* the
sum of the functions. Corpus cases pin this per language.

**Parse-error policy** (CORE-ALL-0002): tree-sitter always returns a tree. ERROR and MISSING
subtrees are skipped as opaque by every walker (`is_opaque`, never descended into), `parse_ok` goes
False, and a warning diagnostic is attached. `--strict` upgrades that to an error exit. No number is
fabricated silently.

## 7. Buse-Weimer readability (`readability/`)

### 7.1 Tokenization on tree-sitter

Two feature families, mirroring the proven `anchor.py` structure:

- **Raw-line facts** (line length in code points, indentation, spaces, blanks,
  `max_char_occurrences`) come from the normalized decoded text directly.
- **Token facts** (identifiers, keywords, numbers, comments, operator classes, periods, commas,
  parentheses, `max_identifier_occurrences`) come from the unified per-line `LexicalToken` stream
  (leaf walk plus atomic tokens), each token attributed to the physical line of its start point.

Every ambiguity the paper leaves open is a numbered BW-\* or TOK-\* ruling. Does a block comment
count on each line it spans (BW-ALL-\*)? Do string contents feed punctuation counts (by default no:
token-level features count OPERATOR and PUNCT tokens, while character-level features always use raw
text)? Is the `.` in a qualified name a "period"? **Ambiguous rulings are resolved empirically by
the §8.3 faithfulness pipeline**: the interpretation that best reproduces the paper is frozen into
the spec, with the experiment recorded in the ruling.

*Anti-circularity note*, stated in the spec and in the paper: these rulings are selected on the same
100-snippet dataset whose reproduction accuracy we then report. The reproduction is evidence of
faithful operationalization, not an independent validation of BW's construct.

### 7.2 Output shape and granularity

Output is always the raw 25-vector in canonical Fig. 6 order, inherited verbatim from
`anchor.py::_BW_FEATURE_NAMES`, plus `BW_FEATURE_ORDER_SHA` (sha256 of the joined names) stamped
into any trained-model artifact as a feature-order integrity gate. `granularity ∈ {snippet,
function, file}` and `extrapolated = granularity != "snippet"` (a typed field plus a diagnostic).
Even at snippet granularity, a `snippet-out-of-calibrated-range` diagnostic fires outside the
paper's 4-to-11-line regime.

### 7.3 Bare-snippet parsing (CORE-JAVA-0001, critical-path ruling for §8.3)

The 100 BW Java snippets are mostly statement sequences or bare members rather than compilation
units. The early design assumed tree-sitter-java would choke on that shape and always wrap it. It
does not: the grammar's `program` rule accepts both bare statement sequences and bare method
declarations, so snippet *shape* on its own does not break a parse. Scaffolding is therefore a
**fallback**, not the default path, and CORE-JAVA-0001 pins it as one:

1. Parse the raw snippet and count ERROR/MISSING nodes.
2. Only if that count is non-zero, and only at `granularity="snippet"` in Java, re-parse the text
   inside **two** candidate scaffolds: class-body-only `class __CC__ { … }`, which rescues
   constructors and modifier-bearing members that a method body cannot legally contain, and
   `class __CC__ { void __cc__() { … } }` for statement fragments.
3. Adopt the strict error-count minimizer, and adopt it **only if it strictly beats the bare
   parse**. A scaffold that does not reduce the error count is discarded, so the wrapper can never
   make a snippet's parse worse.

When a scaffold is adopted, features are computed **only over the original snippet's line range**
(scaffold lines excluded, indentation unshifted), function units living on scaffold lines are
dropped, emitted spans and `--explain` traces are rebased to snippet coordinates so no `__CC__`
artifact leaks into output, and a `snippet-scaffolded` diagnostic is attached.

The measured effect on the dataset says what the scaffold is and is not doing. **10 of the 100
snippets are scaffolded** (4, 7, 8, 13, 19, 32, 33, 35, 43, 48), and 71 still carry parse errors
afterwards. That is not a scaffold failure: the snippets are short excerpts (4 to 13 lines) lifted
out of larger methods, so most of them end mid-construct with unbalanced braces, and no wrapper can
close a brace the source never opened. What keeps those 71 measurable is BW-ALL-0007, the lexical
fallback (§14), under which the
token-family features read the full lexical stream, ERROR regions included. Metrics stay
error-opaque (CORE-ALL-0002) regardless. The extractor is tested on real snippet-shaped input before
the faithfulness pipeline runs.

### 7.4 Retraining scaffold (`retrain.py`, extra `[retrain]`)

`train_bw_model(vectors, labels, *, protocol="bw2010-logistic-10fold", seed=0)` returns a
`TrainedReadabilityModel` serialized as **JSON coefficients**, never pickle, carrying `feature_set`,
`feature_order_sha`, `spec_version`, `trained_granularity`, `trained_language` and `dataset_id`.
Predicting on a mismatched language, granularity or spec is *possible but labelled*: applying
Java-snippet weights elsewhere is a construct-validity decision the user makes with eyes open.
codecaliper ships **no trained weights**.

### 7.5 Scalabrino and Dorn (1.x)

`FeatureSet` registry entries (`dorn2012`: visual and spatial, natural on tree-sitter positions;
`scalabrino2018`: textual, needing wordlists, an optional extra). New ruling prefixes, corpus cases,
and their own faithfulness pipelines. `FileReport.readability` is already plural, so nothing breaks.

## 8. Validation architecture (validation decides everything)

### 8.1 Consistency corpus (§6.1 of the charter)

`tests/corpus/<lang>/<case-id>/{input.<ext>, expected.toml}`, with hand-computed expected values and
the working shown. Integers assert exactly; floats carry explicit tolerances; dual-mode cognitive
cases assert both values whenever they differ; any subset of the 25 BW features may appear per case
(depth over breadth). Case IDs are globally unique and cross-referenced from rulings and divergence
records. One pytest node per (case, metric[, mode]); a failure prints the rulings in dispute and the
`--explain` trace diff.

### 8.2 Differential harness (§6.2)

The probe/SKIP pattern is inherited from `bench/anchor.py`. Honesty runs two ways:

- **Locally**, a missing oracle is a `SKIP` with a precise reason. A contributor's build never fails
  for a tool they do not have.
- **In CI** (the `differential` job in `ci.yml`), the three wired oracles are installed at
  `constraints/ci.txt` pins, with a hard-import step (`python -c "import radon.complexity, lizard,
  cognitive_complexity.api"`) before pytest. An oracle that installs but cannot import fails the job
  outright, so a silent SKIP can never mask a regression.

Oracle set. **Per-PR, zero-install**: the two `tests/_reference/` ports (the stdlib BW extractor and
the Python-AST lane) run on every PR as free differential witnesses. **Differential CI job**: radon,
lizard and cognitive_complexity from pip, with `cognitive_complexity` specifically witnessing
`--sonar-compat`. **Staged, not yet wired** (§15 items 2 and 4; the README says the same): PMD, the
serious second Java cyclomatic witness, without which Java cyclomatic is witnessed by lizard alone
and Java cognitive complexity has no external oracle at all, only the corpus and the spec, as the
divergence-list preamble states; rust-code-analysis, whose last release was 2023, making it a
scheduled-job candidate rather than per-PR infrastructure; and a pinned wild-file input set.
**SonarQube is excluded as an automated oracle** because of its server architecture. Its whitepaper
is a *spec source*, with cognitive_complexity as the Sonar-lineage witness. The inputs today are the
whole corpus plus inline probe snippets in the per-oracle tests.

### 8.3 BW faithfulness reproduction (§6.3, the make-or-break)

`validation/bw_faithfulness/` is reviewer-rerunnable, and it is **self-contained**: it runs offline,
from the git tree alone.

That is possible because an author of the dataset (W. Weimer) granted redistribution by e-mail on
2026-07-11 (PERMISSIONS.md records the message's date, its DKIM result and the sha256 of the
retained original; `dataset.toml` carries the same facts in machine-readable form). Under that
grant, every raw input the lane consumes is tracked in the repository as a pin under
`derived/arbitration_inputs/`: the 100 Java snippets (`snippets/1.jsnp` … `100.jsnp`), `oracle.csv`
(the 121-row per-annotator score matrix) and `scores.csv` (the per-snippet means derived from it).
102 files, 57,168 bytes.

`pinned.py` is the input contract, and it enforces two rules. A missing tracked input is a **hard
error, exit 1, never a SKIP**, because a SKIP exits 0: the lane would report success on a run that
measured nothing, and the failure would surface only when someone tried to reproduce the numbers.
And when `cache/DatasetBW.zip` happens to be present, every pin is cross-checked byte-for-byte
against it, with any difference a hard error rather than a silent re-pin. Re-pinning is a deliberate
act (`pin_inputs.py --force`), and `pin_inputs.py` is not on the reproduction path.

The pipeline:

1. **fetch** (`fetch.py`, *optional*): downloads the archives and sha256-verifies them against
   `dataset.toml`. For the BW lane this is a provenance and cross-check tool, not a prerequisite;
   the lane never needs it. It remains mandatory for `validation/breadth/` (below).
2. **extract**: the *public API path* (`granularity="snippet"`, Java) over all 100 tracked snippets,
   producing `features.csv` stamped with the spec, grammar and feature-order sha.
3. **train**: the shipped scaffold (dogfooding). Binarize per the paper's protocol (the exact
   binarization and classifier-battery choice is documented, and any deviation from the paper is
   stated), then 10-fold CV logistic regression with a fixed seed.
4. **report**: accuracy **with a bootstrap CI** (n=100 implies roughly ±8pp of sampling noise, so a
   bare ≥0.75 threshold can pass or fail by chance; the gate is "the CI overlaps the paper's ≈80%",
   plus the trend), AUC, and the **per-feature table**: the Spearman correlation of each feature
   against the annotator means, sign-compared to the paper's Fig. 9 directionality. That last table
   localizes a failure to a specific BW-\* or TOK-\* ruling instead of one opaque number. The
   expected signs are a data file, `fig9_signs.toml`, keyed by the canonical feature names. The
   statistics are `spearman` and `ci95_bootstrap` in `stats.py`, pure stdlib, ported from
   Spaghetti's `bench/grade.py` (NOTICE-credited).
5. **arbitrate**: the pre-registered 32-cell experiment that settled the two open BW ambiguities at
   spec 1.0.0 (§14). It reads the same pins.

The grant covers the Buse-Weimer corpus and nothing else, and that has an architectural
consequence. `validation/breadth/`, the cross-corpus parse anatomy, also measures the Scalabrino et
al. (2018) and Dorn (2012) corpora, which carry no permission, are never tracked, and are fetched at
run time into the gitignored `cache/`. **That lane requires a network fetch and always will.** So the
headline reproduction runs from a clone and the breadth numbers do not, and the repository states
the split wherever either is described. PERMISSIONS.md holds the terms of all three corpora.

The pipeline is **local and manual only, and never runs in CI** (§11, RELEASING.md). The derived
artifacts are tracked too (`derived/`: per-snippet feature vectors, training and arbitration
results, and the generated reports), which makes the extraction step diffable after the fact. There
is no automated per-PR guard over them: an extractor change that would invalidate them shows up in
the corpus and fidelity gates, and re-running the pipeline against a refreshed spec is a deliberate,
documented act. Those reports stamp the package version that generated them, which constrains the
release order (RELEASING.md).

### 8.4 Determinism and performance

- `test_determinism.py` runs the CLI twice over the corpus under different `PYTHONHASHSEED`s and
  byte-compares the JSON and CSV. The **float policy** (CORE-ALL-0004) rounds floats to 12
  significant digits (round-half-even) at serialization; corpus float assertions always carry
  tolerances. The byte-identity claim is scoped **per platform**, because libm's `ln()` may differ
  across OS and architecture. Documented, not hidden.
- `test_perf_smoke.py` sets a throughput floor over the corpus, catching the easy regression class
  (re-loading the spec TOMLs on every call, say), and asserts that `Session` reuses parsers and that
  the ruling registry loads once. The declared audience (pretraining-data filtering, corpus-scale
  MSR) measures 10⁵ to 10⁶ files, and `Session` is the corpus-scale entry point: it caches, and its
  order is deterministic and sequential. Parallelism is a 1.x concern.

## 9. Public API + CLI

```python
def measure(source: str | bytes, *, language: str,
            metrics: Collection[str] | None = None,          # None = all registered
            readability: Collection[str] = ("bw2010",),      # () disables
            granularity: Granularity = "file",
            cognitive_mode: Literal["whitepaper", "sonar-compat"] = "whitepaper",
            explain: bool = False) -> FileReport
def measure_file(path, *, language: str | None = None, **kw) -> FileReport   # None ⇒ detect
class Session: ...          # caches Language/Parser/tables; measure()/measure_file()
def spec_version() -> str
def ruling(ruling_id: str) -> Ruling
def iter_rulings(metric=None, language=None) -> Iterator[Ruling]
```

`py.typed`; mypy `--strict` in CI. Errors: `CodecaliperError` → `UnsupportedLanguageError`,
`GrammarLoadError`, `SpecError`, `StrictParseError`.

```
codecaliper FILE... [--lang auto|python|java] [--json|--csv] [--metrics …] [--sonar-compat]
            [--no-readability] [--bw-granularity snippet|function|file] [--explain] [--strict] [-o OUT]
codecaliper spec version | list [--metric --lang] | show CC-PY-0003
codecaliper env            # calibration plate: tool/spec/binding/grammar/ABI/Python versions
codecaliper cite [--format text|bibtex]         # methods-section template incl. spec version,
                                                # modes, grammar versions
```

JSON always embeds the full provenance block. **CSV is wide-format** (one row per file or function
scope; flat metric and BW columns) **plus mandatory provenance columns** (`spec_version`,
`grammar_version`, `cognitive_mode`, `extrapolated`), so a CSV row pasted into someone's paper still
names its spec. `--lang auto` uses the extension map, and an ambiguity is an explicit error rather
than a guess. Diagnostics go to stderr, data to stdout; exit codes 0/1/2.

## 10. Grammar-evolution policy (the top long-term risk)

- Install metadata uses **compatible ranges** (`tree-sitter>=0.25,<0.27`,
  `tree-sitter-python>=0.25,<0.26`, `tree-sitter-java>=0.23.5,<0.24`) so that pip can resolve in
  shared environments. `constraints/ci.txt` pins **exact** versions for CI and releases;
  `spec/validated_grammars.toml` records the calibrated set; provenance records the
  **actually-installed** versions and stamps `validated=false` plus a diagnostic on deviation. Run
  and label: never refuse, never trust silently.
- **Fixed upgrade procedure.** Bump the pin on a branch, run the consistency and differential
  suites, and let the result decide the version: any changed number forces a spec **major** plus a
  changelog entry, and no change is a spec patch. The `grammar-bump.yml` weekly job runs the corpus
  against the *latest* grammars and opens an issue with the per-case diff on drift. It never
  auto-merges. Grammar evolution becomes a reviewed calibration event.

## 11. Packaging and CI

- hatchling, src layout, `requires-python = ">=3.10"`, `tomli; python_version < "3.11"`. Runtime
  dependencies: the tree-sitter binding, two grammar wheels, nothing else.
- Extras: `[retrain]` (scikit-learn), `[oracles]` (radon, lizard, cognitive_complexity, all
  test-time only), `[dev]`, `[docs]` (mkdocs-material and mkdocstrings; `docs.yml` installs it
  under `constraints/docs.txt`).
- CI as built, with the original plan de-scoped per §15 items 3 and 4. `ci.yml` has four jobs, all
  on `ubuntu-latest`: **test** (Python 3.10, 3.12 and 3.14; ruff, then the whole pytest suite:
  consistency, spec-coverage, spec-drift, grammar-integrity, BW port fidelity, AST-lane crosscheck,
  CLI, behaviour, determinism, perf smoke); **typecheck** (mypy `--strict`, a hard gate, on 3.12);
  **spec-docs** (regenerate and `git diff --exit-code docs/`, so a stale generated page is red); and
  **differential** (oracles at `constraints/ci.txt` pins, a hard-import step so that a SKIP cannot
  mask an absence, zero unclassified divergences, stale entries fail). `docs.yml`: `mkdocs build
  --strict` and the Pages deploy. `grammar-bump.yml`: the weekly early warning (Mondays 06:00 UTC).
  `release.yml`: gate and build in parallel, then PyPI trusted publishing, then the GitHub Release,
  which fires the Zenodo webhook (RELEASING.md).
- There is deliberately **no bw-faithfulness workflow**. The lane is self-contained and needs no
  network, so that is not the reason; re-running it pulls the whole `[retrain]` ML stack, and it
  stays a deliberate local action by repo-focus choice (RELEASING.md, "What deliberately does NOT
  happen here").
- Docs (mkdocs-material). The nav is home, quickstart, the honesty invariants, the **generated**
  spec pages (rulings and known divergences), a validation page that verbatim-includes the derived
  faithfulness and arbitration reports via snippet includes, an mkdocstrings API reference, and a
  contributor page. That last one is not a second copy of anything: `docs/contributing.md` is a
  snippet transclusion of the repository's `CONTRIBUTING.md`, so how to add a ruling, a corpus case
  or a language is hosted on the site without a checklist existing in two versions. `ARCHITECTURE.md`
  is the file that is linked rather than re-hosted, because it is written for someone with the tree
  in front of them. Paper sources live in a local, gitignored `paper/` directory: submission material
  stays out of the public repo until publication.

## 12. Reuse from Spaghetti Architect (NOTICE-credited, DOI 10.5281/zenodo.21033174)

| Origin | Destination | Role |
|---|---|---|
| `bench/anchor.py::bw_readability_features` + `_BW_FEATURE_NAMES` | `tests/_reference/bw_stdlib.py` (verbatim) + canonical order in `readability/bw2010.py` | Reference extractor; per-PR differential oracle for the tree-sitter BW port |
| `eval/metrics.py::cyclomatic/_traverse/halstead/maintainability_index` | `tests/_reference/py_ast_lane.py` (verbatim) + algorithm basis of `metrics/cognitive.py` | Python-AST oracle; the proven elif-flattening walk |
| `bench/anchor.py` probe/SKIP pattern (`_PROBES`, `_SKIP_REASON`) | `tests/differential/` | Honest-SKIP oracle harness |
| `bench/grade.py::spearman/mean/ci95_bootstrap` | `validation/bw_faithfulness/stats.py` | Faithfulness statistics (pure stdlib) |
| `eval/metrics.py` regex-lane ruling knowledge (comment prefixes, branch keywords) | `spec/rulings/*.toml` | Ruling raw material only; the lane itself is not shipped |

Not ported (the anti-salami boundary): SPAGH markers, the IR and anti-optimization machinery, the
validity study. codecaliper measures arbitrary user source, and the only overlap with the DMLR
artifact is general-purpose measurement primitives.

## 13. Honesty boundaries (verbatim commitments, on the docs honesty page and in diagnostics)

1. Procedural consistency is not cross-language numerical comparability.
2. MI contains CC. Never treat them as independent signals (typed `derived_from`).
3. Halstead absolute values are implementation-defined; only trends and ratios are stable.
4. BW output is a feature set, not a score. No score field exists.
5. Function-level and file-level readability vectors are labelled extrapolation. The calibrated
   regime is 4-to-11-line snippets.
6. Metrics operate on pre-preprocessing source text.
7. Byte-identical output is a per-platform claim (the float/libm caveat is documented).
8. The BW-ambiguity rulings are arbitrated on the same dataset the reproduction reports. That is
   evidence of faithful operationalization, not independent construct validation.
9. One of the three measured corpora may be redistributed, and two may not. The repository never
   elides the difference (§8.3, PERMISSIONS.md).

## 14. Decision log (what was chosen over what)

| Decision | Rejected alternative | Why |
|---|---|---|
| Validation-first skeleton, lean core | Gate-maximalist instrument design | Unbuildable solo in 8 weeks; per-value provenance objects and tamper checks are speculative bloat |
| Plain dict tables + named hooks in adapters | `when.*` predicate DSL in nodemap.toml | A DSL needs an interpreter and tests, and hits expressiveness walls immediately |
| Plain dict registry | setuptools entry-point plugins | Speculative until a third-party adapter exists |
| Lexical Halstead | AST-harvest Halstead | Cross-language uniformity; lexer reuse; the divergence is declared via halstead-approximation (no Halstead differential lane is wired) |
| Range pins + CI lockfile + validated flag | Exact `==` grammar pins in install metadata | `==` fights pip resolution in shared envs; the flag keeps honesty without breaking installs |
| Run-and-label on unvalidated grammars | Refuse to run | Provenance already records the truth; refusal punishes legitimate environments |
| Ship with the three pip-installable oracles wired per-PR (radon, lizard, cognitive_complexity); leave PMD and rust-code-analysis staged | Wire all five before 1.0 | The three are pinned in `constraints/ci.txt` (radon 6.0.1, lizard 1.23.0, cognitive-complexity 1.3.0) and gate every PR. PMD is a JVM tool outside that pip closure and was the §15 item-4 cut, which leaves Java cyclomatic witnessed by lizard alone and Java cognitive with no external witness at all. That gap is stated (§8.2, the divergence-list preamble), not silent. RCA's last release was 2023 |
| ctx.count() + opt-in `--explain` traces | rulings-applied lists only | Divergence triage needs *where and how much*, not just *which* |
| 12-sig-digit float quantization + per-platform byte claim | Cross-OS byte-identity claim | libm differences make the stronger claim false, and honesty is the brand |
| Indentation tab = 8 (TOK-ALL-0006, superseding TOK-ALL-0004's tab = 1) | tab = 1 / tab = 4 | Pre-registered 32-cell arbitration: tab=1 zeroes the Fig. 9 indentation correlation; any tab>=2 fixes the sign, and 8 won the pre-registered AUC tie-break (8-vs-4 is a stated convention pick within noise) |
| BW token features see ERROR-region tokens (BW-ALL-0007) | Error-opaque BW (CORE-ALL-0002 everywhere) | The BW construct is lexical (the original tool was grammar-less); opacity zeroed 8 of the 100 original snippets and depressed AUC 0.798 -> fallback 0.827 (the matrix cell; the final re-run's headline is 0.828, the same configuration differing by one ranked pair of serialization precision, see the arbitration report). Metrics stay opaque |
| Java arithmetic-op class unchanged after arbitration (null result) | Adding ++/--/compound assignment | No variant changed any Fig. 9 sign across 32 cells, and an AUC spread <= 0.00125 is noise. A ruling is not changed on noise |
| Track the BW raw inputs; keep Scalabrino and Dorn out of the tree forever | Fetch everything at run time (the pre-permission status quo) | An author granted redistribution of the BW data (PERMISSIONS.md), so the headline reproduction runs from the git tree with no download step that can rot, 404 or change under it. No such grant exists for the other two corpora, so the asymmetry is permanent and stated (§8.3) |

## 15. De-scoping ladder: which rungs were taken

This was written before W6 as a cut order, cheapest first, for the case where the schedule ran out.
W6 and W8 shipped (§16), so it is now a record of what 0.1.0 actually gave up. Rungs 1 and 5 were
never taken; 2, 3 and 4 were. Each cut still stands as the honest description of a gap, and each
is reversible without touching the core.

1. `--explain` traces move to 1.1 (the `ctx.count` seam stays; only the CLI surface slips).
   **Not cut.** `--explain` ships and is the per-increment attribution shown in §3.3.
2. Wild-corpus differential inputs become corpus-only differential. **Cut.** The differential lane's
   inputs are the consistency corpus plus inline probe snippets in the per-oracle tests. Nothing
   scraped from the wild has been run past the oracles.
3. macOS and Windows CI jobs drop to ubuntu-only. **Cut.** Every `ci.yml` job runs on
   `ubuntu-latest`, across Python 3.10, 3.12 and 3.14. The determinism claim was already
   per-platform (§8.4), so this narrows the evidence for that claim rather than contradicting it:
   nothing in CI exercises the libm difference the claim is scoped around.
4. The PMD oracle drops to lizard-only Java witnessing for 1.0. **Cut.** Java cyclomatic has one
   external witness and Java cognitive has none (§8.2, §14).
5. `Session` caching drops to plain `measure()`. **Not cut.** `Session` ships, and
   `test_perf_smoke.py` asserts both the parser reuse and the throughput floor.
6. Never cut: the consistency corpus, the spec-drift gate, the BW faithfulness pipeline, the
   honest-SKIP differential harness. These are the paper's evidence base, and all four are in the
   tree.

## 16. Milestones (from the charter, sharpened)

- **W1-3**: skeleton; tree-sitter wired (Python and Java); BW ported onto tree-sitter with the
  stdlib reference as a per-PR oracle; first consistency cases; spec registry and seed rulings.
- **W4-5**: dual-mode cognitive; AST-lane crosscheck green; spec table v0.1 complete; drift gate on.
- **W6**: the **BW faithfulness reproduction** (snippet-scaffold ruling first), the differential lane
  and the divergence list.
- **W7**: CLI complete (`env`, `cite`), docs, community files.
- **W8**: **done.** v0.1.0 was tagged on 2026-07-12, PyPI serves `codecaliper 0.1.0`, the GitHub
  Release is published, and the Zenodo concept DOI 10.5281/zenodo.21312527 resolves (the v0.1.0
  version DOI is 10.5281/zenodo.21312528).
  Remaining: the tool-showcase paper (acmart sigconf, 4+1 pages) for the MSR Data and Tool Showcase.
  There is no screencast, because the MSR Data and Tool Showcase CFP has no video or
  demo-recording requirement. That is an ICPC Tool-Demo convention, not this venue's.
