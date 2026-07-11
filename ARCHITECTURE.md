# codecaliper — Architecture

> **Design thesis.** Every number codecaliper emits is *traceable* — to a spec version, to the
> exact rulings that fired, to the exact grammar that parsed the source — and *reproducible* —
> clock-free, hash-seed-free, order-stable. Where a scoreboard says "CC = 7", this instrument says
> "CC = 7 *under spec 1.1.0, ruling CC-PY-0003, tree-sitter-python 0.25.0*".
> That sentence is the data model.
>
> This document is the synthesis of a three-way architecture study (instrument-purist,
> API/extensibility, validation-first lenses) judged against the project charter, and is now the
> authoritative requirements record (the charter itself is deliberately not in the repo). Charter
> section references (§5 design, §6 validation, §7 publication checklist, §8 risks) appear throughout;
> §0 below restates every fixed decision they pinned. The decision log in §14 records what was
> chosen over what.

## 0. Fixed decisions (from the charter — do not relitigate)

- **MVP languages: Python + Java.** Java is the Buse–Weimer (BW) native language, enabling the
  §6.3 faithfulness reproduction — the project's single strongest credibility asset.
- **tree-sitter is the unified syntactic base.** Metrics operate on the **pre-preprocessing
  source text** (declared honestly; the C-family preprocessor makes any syntactic tool an
  approximation).
- **Cognitive complexity is dual-mode**: default *whitepaper-faithful*, `--sonar-compat` opt-in.
  Every inter-mode divergence is an enumerable, mode-tagged ruling.
- **1.0 readability scope: faithful BW features only.** Scalabrino/Dorn slot into the same
  `FeatureSet` seam in 1.x without model changes.
- **BW feature extraction is decoupled from any trained model.** The API returns raw 25-feature
  vectors; there is deliberately **no** `bw_score` anywhere. A retraining scaffold ships instead
  of weights.
- **External tools are differential-test oracles only** (radon / lizard / cognitive_complexity /
  PMD / rust-code-analysis), never runtime backends. Missing oracle ⇒ honest SKIP.
- The old Spaghetti-Architect regex lane is **demoted**: its per-language ruling knowledge is
  mined into the spec; its proven implementations survive only as *test-only internal oracles*.
- **Procedural consistency, not numerical comparability.** The tool guarantees identical rules
  over isomorphic syntactic structures across languages; it does *not* claim CC numbers are
  directly comparable across languages. Stating this is a feature (§13).

## 1. Package / module tree (src layout)

```
codecaliper/
├── pyproject.toml               # hatchling; requires-python >=3.10
├── LICENSE                      # MIT
├── NOTICE                       # primitives descend from Spaghetti Architect (DOI 10.5281/zenodo.21033174)
├── CITATION.cff  README.md  ARCHITECTURE.md  CLAUDE.md
├── CONTRIBUTING.md  CODE_OF_CONDUCT.md
├── constraints/                 # ★ pin files: ci.txt (exact grammar pins for CI/releases),
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
│   │   ├── __init__.py          # SPEC_VERSION, ruling(), iter_rulings()
│   │   ├── registry.py          # loads rulings TOML; require(id) fails at import on phantom IDs
│   │   ├── rulings/             # ★ the versioned metric-to-syntax mapping spec (TOML package data)
│   │   │   ├── index.toml       # spec_version, changelog
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
│   │   └── tokens.py            # unified per-line LexicalToken stream + TokenKind enum (leaf walk + atomic tokens)
│   ├── languages/
│   │   ├── __init__.py          # plain dict registry; detect_language() for --lang auto
│   │   ├── base.py              # LanguageAdapter protocol; NodeClass enum
│   │   ├── python.py            # classification dicts + named hook functions, every row cites rulings
│   │   └── java.py
│   ├── metrics/
│   │   ├── base.py              # MetricContext.count(ruling, node, delta) — the trace/audit seam
│   │   ├── cyclomatic.py        # decision points over NodeClass
│   │   ├── cognitive.py         # ONE walker, two frozen CognitiveRules tables (whitepaper/sonar)
│   │   ├── halstead.py          # LEXICAL Halstead over the token stream (declared approximation)
│   │   ├── mi.py                # derived_from=("halstead.volume","cyclomatic","sloc")
│   │   └── loc.py               # physical/blank/comment/sloc/lloc
│   └── readability/
│       ├── base.py              # FeatureSet protocol + registry (bw2010 now; scalabrino/dorn later)
│       ├── bw2010.py            # the 25 Fig.6 features; canonical order from anchor.py
│       ├── granularity.py       # snippet/function/file segmentation; extrapolation labelling
│       └── retrain.py           # scaffold: JSON model artifacts, never pickle, never bundled weights
├── tests/
│   ├── corpus/                  # ★ §6.1 consistency corpus: <lang>/<case-id>/{input.*, expected.toml}
│   ├── snapshots/corpus_values.json   # ★ spec-drift snapshot (spec+grammar stamped)
│   ├── _reference/              # test-only verbatim ports (NOTICE-credited):
│   │   ├── bw_stdlib.py         #   anchor.py::bw_readability_features (stdlib tokenize)
│   │   └── py_ast_lane.py       #   eval/metrics.py cyclomatic/cognitive/halstead/MI (stdlib ast)
│   ├── differential/            # external-oracle lane: divergences.toml + per-oracle tests
│   ├── test_consistency_corpus.py
│   ├── test_spec_coverage.py    # rulings ⇄ code ⇄ corpus bidirectional coverage
│   ├── test_spec_drift.py       # numbers may not change without a spec MAJOR bump
│   ├── test_grammar_integrity.py# adapter tables validated against the COMPILED grammar
│   ├── test_bw_port_fidelity.py # tree-sitter BW vs stdlib reference, per feature
│   ├── test_python_lane_crosscheck.py  # tree-sitter Python metrics vs ported AST lane
│   ├── test_determinism.py      # two runs, different PYTHONHASHSEED, byte-identical output
│   └── test_perf_smoke.py       # throughput floor; parser/spec-registry reuse assertions
├── validation/bw_faithfulness/  # ★ §6.3 pipeline (repo-only, never in the wheel)
│   ├── dataset.toml             # URL + sha256 + license note; data NEVER committed
│   ├── fetch.py  extract.py  train.py  report.py  README.md
├── tools/
│   ├── gen_spec_docs.py         # ruling TOMLs → docs/spec/*.md (generated, staleness-checked)
│   ├── gen_divergences.py       # classification TOMLs → docs/spec/divergences.md
│   └── update_snapshot.py       # refuses numeric changes without --confirm-spec-bump
├── docs/
└── .github/workflows/           # ci.yml (incl. differential job), docs.yml, grammar-bump.yml, release.yml
```

Three structural invariants, mechanically enforced:

1. `tree_sitter` is imported **only** in `syntax/_treesitter.py` (lint gate).
2. `metrics/` and `readability/` never mention a concrete tree-sitter node-type string — they
   consume `NodeClass`/`TokenKind` only.
3. Oracles and the legacy reference ports live **only** under `tests/` — they cannot be imported
   from `src/` (the anti-salami boundary is a build failure, not a promise).

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
    validated: bool          # matches spec/validated_grammars.toml? (never refuse — label)

@dataclass(frozen=True, slots=True)
class Provenance:
    tool_version: str
    spec_version: str        # ★ on every report
    language: str
    grammar: GrammarInfo
    modes: tuple[tuple[str, str], ...]  # (("cognitive", "whitepaper"),) — hashable, JSON-objectified
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
                 # (authoritative: DIAGNOSTIC_CODES in model.py — membership is
                 # enforced across the corpus by test_diagnostic_codes_are_a_closed_set)
    message: str
    span: Span | None = None
    ruling: str | None = None

@dataclass(frozen=True, slots=True)
class RulingTrace:           # populated only with explain=True — zero cost on the default path
    ruling_id: str
    span: Span
    delta: float

@dataclass(frozen=True, slots=True)
class MetricValue:
    metric: str                          # "cyclomatic", "halstead.volume", ...
    value: int | float
    rulings: tuple[str, ...]             # ruling IDs governing this metric+language
    derived_from: tuple[str, ...] = ()   # MI: ("halstead.volume","cyclomatic","sloc") — §5.6 honesty, typed
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

Metric collections are order-stable tuples, not mappings — `model.metric_map(values)`
is the keyed convenience view (`metric_map(report.file_metrics)["cyclomatic"]`).

Honesty is encoded in types, not docs: MI always carries `mi-contains-cc` + typed `derived_from`;
Halstead always carries `halstead-approximation`; `extrapolated` is a field that flows into
JSON/CSV; there is no score field to launder.

## 3. The spec mechanism

### 3.1 Rulings: machine-readable TOML with immutable IDs

One ruling = one decision about how a metric maps onto syntax.

```toml
[[ruling]]
id = "CC-PY-0003"
metric = "cyclomatic"
language = "python"                # or "all"
title = "Boolean short-circuit operands count as decision points"
status = "active"                  # active | superseded (superseded_by = "…")
since_spec = "0.1.0"
mode = ""                          # cognitive only: "whitepaper" | "sonar-compat" | "" (both)
node_types = ["boolean_operator"]  # CI-validated against the compiled grammar (§6.4)
statement = """Each boolean operator chain contributes (operands − 1) decision points…"""
examples = ["py-cc-boolop-001"]    # normative corpus case IDs
```

ID grammar: `{METRIC}-{LANG}-{NNNN}`, `METRIC ∈ {CORE, TOK, CC, COG, HAL, MI, LOC, BW}`,
`LANG ∈ {ALL, PY, JAVA, …}`. IDs are **immutable forever**: a changed decision *supersedes* the
old ruling under a new ID — the audit trail survives.

### 3.2 Spec versioning (independent of the package version)

`SPEC_VERSION` (semver) lives in `rulings/index.toml`. **patch** = editorial; **minor** = new
rulings, no existing number changes; **major** = any change that alters any number for any
existing corpus case — *including a grammar pin bump that does so*.

Enforcement is mechanical: `test_spec_drift.py` recomputes every metric over the whole corpus and
compares against `tests/snapshots/corpus_values.json` (stamped with spec + grammar versions). Any
drift without a major bump is a red build; the snapshot is refreshed only via
`tools/update_snapshot.py --confirm-spec-bump`.

### 3.3 How code references rulings

```python
R_BOOLOP = spec.require("CC-PY-0003")        # KeyError at import if the ID is phantom
...
ctx.count(R_BOOLOP, node, delta=len(operands) - 1)
```

`MetricContext.count()` accumulates the value, records the fired ID for provenance, and — when
`explain=True` — appends a `RulingTrace(ruling, span, delta)`. `codecaliper FILE --explain` thus
gives per-increment attribution, which is what divergence triage and downstream audit actually
need. `test_spec_coverage.py` asserts bidirectional coverage: every active ruling is referenced
by code **and** exercised by ≥1 corpus case; every corpus citation and every non-empty adapter
table-row citation points at a real ruling covering that node type. The spec, the code, and the corpus are one mutually
verifying artifact.

### 3.4 The known-divergence list is generated, complete by construction

Classified divergences are TOML records in `tests/differential/divergences.toml` (a real one):

```toml
[[divergence]]
oracle = "cognitive_complexity"
case = "py-nested-function-001"     # corpus case ID or "snippet:<probe-name>"
unit = "outer"                      # codecaliper qualified function name
metric = "cognitive"
ours = 3                            # the value pinned by `ruling`
theirs = 5                          # the installed oracle's value
ruling = "CORE-ALL-0003"
reason = "cognitive_complexity scores a function including its nested defs; CORE-ALL-0003 excludes nested named units, which get their own FunctionReports."
```

The differential harness fails CI on any **unclassified** divergence (the failure prints a
ready-to-paste stanza) and on any **stale** entry no longer observed — the table is complete by
construction, in both directions. Oracle versions are pinned in `constraints/ci.txt` (a pin bump
re-runs the whole lane, re-surfacing every entry for re-triage), and the published
`docs/spec/divergences.md` (generated by `tools/gen_divergences.py`, staleness-checked) is the
complete scholarly artifact the charter promises.

## 4. tree-sitter integration (`syntax/`)

`_treesitter.py` is the quarantine — the only importer of `tree_sitter`, providing:

- `load_language(module_name) -> (Language, GrammarInfo)` — wraps the grammar wheel's PyCapsule
  via `Language(mod.language())`; captures version via `importlib.metadata`, ABI via
  `abi_version` (with the `version → abi_version` deprecation shim); checks
  `spec/validated_grammars.toml` → `GrammarInfo.validated`. **Deviation never refuses to run** —
  it stamps `validated=false` plus an `unvalidated-grammar` diagnostic on every report.
- `walk(tree)` — cursor-based preorder `(node, depth)` iteration; O(1) memory, no recursion
  limit, deterministic order.
- `leaves(tree, atomic_types)` — terminal-token stream for the lexer; node types declared
  *atomic* (e.g. Python `string`, which has `string_start/content/end` children; Java
  `string_literal`) are consumed as **one token** (ruling TOK-\*).
- `node_kinds(language)` — grammar introspection (`node_kind_count`/`node_kind_for_id`) used by
  `test_grammar_integrity.py` to validate every adapter-table entry and every ruling's
  `node_types` against the **actually compiled grammar**. A grammar node rename (the real
  tree-sitter-java `comment` → `line_comment`/`block_comment` case) fails loudly and specifically
  instead of silently zeroing metrics. No vendored `node-types.json` needed.

Verified environment shape (2026-07): binding `tree-sitter 0.26.0` (`Language(capsule)`,
`Parser(lang)`, ABI 15/min 13), grammar wheels `tree-sitter-python 0.25.0`,
`tree-sitter-java 0.23.5`. Grammar wheels enforce **no** runtime-compat constraint themselves
(their `core` extra is optional) — we pin both sides ourselves (§11). The MVP deliberately avoids
the Query API entirely (cursor walks suffice), sidestepping the 0.24/0.25 `Query → QueryCursor`
churn; if queries are ever needed, the shim lives here.

Input normalization is itself ruled (TOK-ALL-\*): decode UTF-8 with replacement + diagnostic;
strip a UTF-8 BOM (diagnostic); CRLF→LF before measurement; tab = 8 indentation characters
(TOK-ALL-0006, adopted by the pre-registered arbitration at spec 1.0.0, superseding
TOK-ALL-0004's provisional tab = 1 — §8.3/§14). These change emitted
numbers, so they are spec, not implementation detail.

## 5. Language adapters (`languages/`)

Metric engines never see node-type strings — only this taxonomy:

```python
class NodeClass(Enum):
    BRANCH; ELIF_CONTINUATION; ELSE_CLAUSE; TERNARY; SWITCH; CASE_LABEL
    LOOP; CATCH; BOOL_OP; COMPREHENSION_GUARD; LAMBDA
    JUMP_LABEL  # labeled break/continue, COG-JAVA-0001
    FUNCTION_DEF; CLASS_DEF; NESTING_ONLY

class TokenKind(Enum):
    IDENTIFIER; KEYWORD; NUMBER; STRING; COMMENT; OPERATOR; PUNCT; OTHER
```

An adapter provides: `node_class_map: dict[str, tuple[NodeClass, tuple[ruling_id, ...]]]` (plain
Python dicts — **no predicate DSL**; the three-way study showed a `when.*` mini-language costs an
interpreter and hits expressiveness walls immediately), a small set of **named hook functions**
for the contextual cases a table can't express (e.g. Python elif detection via the parent
`if_statement`'s `alternative` field), each hook citing a ruling; the token-classification frozensets (identifier / number / string /
comment / keyword-leaf / operator-leaf node-type sets) + `atomic_types` + the operator-class tables
(arithmetic/comparison/assignment — the BW-ALL-0006 operator-class features only; Halstead
classifies by `TokenKind`, not these tables); `conditional_token_rulings`; `function_units()`;
keyword list. `PythonAdapter`/`JavaAdapter` are thin; the behaviour is
in the tables, and every increment-bearing row cites a ruling (the nesting-only rows carry an
empty tuple by design — no increment, nothing to cite) — node-type strings validated by the
grammar-integrity gate.

**Adding language #3** (documented checklist, gated by existing meta-tests): new adapter module +
tables, new `*-GO-*` rulings, corpus cases, oracle probe, grammar pin. Zero edits to `metrics/`,
`readability/`, `model.py`, `api.py`, `cli.py`. Registry is a plain dict — entry-point plugin
discovery is deliberately deferred until a third party actually exists.

## 6. Metric engines (`metrics/`)

All engines are pure functions of `(tree, adapter, MetricContext)`; every increment routes
through `ctx.count(ruling, node, delta)`. Each computes file-level and per-function values.

- **cyclomatic** — `1 + Σ decision points`: BRANCH, ELIF_CONTINUATION, LOOP, CATCH, CASE_LABEL,
  TERNARY, COMPREHENSION_GUARD each +1; BOOL_OP +(operands−1).
- **cognitive (dual mode)** — **one** recursive walker parameterized by two frozen
  `CognitiveRules` tables (whitepaper default / sonar-compat). Elif chains are flattened in both
  modes (ported from the proven `eval/metrics.py::_traverse` and cross-checked against it in
  `test_python_lane_crosscheck.py`). Every field where the tables differ is a mode-tagged ruling;
  corpus cases assert **both** mode values whenever they diverge. The spec table *is* the
  whitepaper-vs-Sonar diff.
- **halstead** — **lexical** Halstead (HAL-ALL-0001): operators = OPERATOR + KEYWORD + PUNCT
  tokens per the adapter tables; operands = IDENTIFIER + NUMBER + STRING. Chosen over AST-harvesting for
  cross-language uniformity and lexer reuse; the divergence vs radon and vs the ported AST
  reference is *declared* (no Halstead differential lane runs), and every value carries `halstead-approximation`
  (absolute values are implementation-defined; only trends/ratios are stable).
- **mi** — `clamp₀₋₁₀₀((171 − 5.2·ln V − 0.23·CC − 16.2·ln SLOC)·100/171)` (MI-ALL-0001 pins the
  variant: no comment term). Typed `derived_from` + standing `mi-contains-cc` diagnostic.
- **loc** — physical / blank / comment (block comments count every spanned line, LOC-ALL-\*) /
  sloc / lloc (counted over the adapter's `statement_types` node-type table, LOC-ALL-0004). The
  corpus contains multi-line-string cases that the
  old regex lane provably gets wrong — the reason tree-sitter won.

**Nested-unit attribution is explicitly ruled** (CORE-ALL-\*, a gap all three designs missed and
a classic radon-vs-lizard divergence axis): a nested function/lambda/inner-class body counts
toward the *enclosing* function's file-level walk, but per-function values are computed on each
function's own subtree **excluding** nested `FUNCTION_DEF`/`LAMBDA`/`CLASS_DEF` subtrees, which
get their own `FunctionReport`s; file-level values are one whole-file walk, *not* the sum of
functions. Corpus cases pin this per language.

**Parse-error policy** (CORE-ALL-0002): tree-sitter always returns a tree; ERROR/MISSING subtrees
are skipped as opaque by every walker (`is_opaque`, not descended into), `parse_ok=False`, warning
diagnostic. `--strict`
upgrades to an error exit. No number is fabricated silently.

## 7. Buse–Weimer readability (`readability/`)

### 7.1 Tokenization on tree-sitter

Two feature families, mirroring the proven `anchor.py` structure:

- **Raw-line facts** (line length in code points, indentation, spaces, blanks,
  `max_char_occurrences`) — from the normalized decoded text directly.
- **Token facts** (identifiers, keywords, numbers, comments, operator classes, periods, commas,
  parentheses, `max_identifier_occurrences`) — from the unified per-line `LexicalToken` stream
  (leaf walk + atomic tokens), each token attributed to the physical line of its start point.

Every ambiguity the paper leaves open is a numbered BW-\*/TOK-\* ruling: does a block comment
count on each spanned line (BW-ALL-\*)? do string contents feed punctuation counts (default no —
token-level features count OPERATOR/PUNCT tokens; character-level features always use raw text)?
is the `.` in a qualified name a "period"? **Ambiguous rulings are resolved empirically by the
§8.3 faithfulness pipeline** — the interpretation that best reproduces the paper is frozen into
the spec with the experiment recorded in the ruling. *Anti-circularity note (stated in the spec
and the paper): these rulings are selected on the same 100-snippet dataset whose reproduction
accuracy we then report; the reproduction is evidence of faithful operationalization, not an
independent validation of BW's construct.*

### 7.2 Output shape and granularity

Output is always the raw 25-vector in canonical Fig. 6 order (inherited verbatim from
`anchor.py::_BW_FEATURE_NAMES`), plus `BW_FEATURE_ORDER_SHA` (sha256 of the joined names) stamped
into any trained-model artifact as a feature-order integrity gate. `granularity ∈
{snippet, function, file}`; `extrapolated = granularity != "snippet"` (typed field + diagnostic);
even at snippet granularity, a `snippet-out-of-calibrated-range` diagnostic fires outside the
paper's 4–11-line regime.

### 7.3 Bare-snippet parsing (critical-path ruling for §8.3)

The 100 BW Java snippets are mostly statement sequences, not valid compilation units —
tree-sitter-java yields ERROR-dense trees on them (a gap every initial design missed; it sits on
the make-or-break W6 milestone). Ruling CORE-JAVA-\* pins the strategy: parse the raw snippet;
if the tree is error-dense (threshold ruled), re-parse wrapped in a synthetic
`class __CC__ { void __cc__() { … } }` scaffold, compute features **only over the original
snippet's line range** (scaffold lines excluded, indentation unshifted), and attach a
`snippet-scaffolded` diagnostic. The extractor is tested on actual snippet-shaped input *before*
the faithfulness pipeline runs.

### 7.4 Retraining scaffold (`retrain.py`, extra `[retrain]`)

`train_bw_model(vectors, labels, *, protocol="bw2010-logistic-10fold", seed=0)` →
`TrainedReadabilityModel` serialized as **JSON coefficients** (never pickle) carrying
`feature_set`, `feature_order_sha`, `spec_version`, `trained_granularity`, `trained_language`,
`dataset_id`. Predicting on mismatched language/granularity/spec is *possible but labelled* —
applying Java-snippet weights elsewhere is a construct-validity decision the user makes with eyes
open. codecaliper ships **no trained weights**.

### 7.5 Scalabrino/Dorn (1.x)

`FeatureSet` registry entries (`dorn2012`: visual/spatial — natural on tree-sitter positions;
`scalabrino2018`: textual — needs wordlists, optional extra). New ruling prefixes, corpus cases,
own faithfulness pipelines. `FileReport.readability` is already plural; nothing breaks.

## 8. Validation architecture (validation decides everything)

### 8.1 Consistency corpus (§6.1 of the charter)

`tests/corpus/<lang>/<case-id>/{input.<ext>, expected.toml}` — hand-computed expected values with
working shown; integers assert exactly, floats carry explicit tolerances; dual-mode cognitive
cases assert both values whenever they differ; any subset of the 25 BW features per case (depth
over breadth). Case IDs are globally unique and cross-referenced from rulings and divergence
records. One pytest node per (case, metric[, mode]); failures print the rulings in dispute and
the `--explain` trace diff.

### 8.2 Differential harness (§6.2)

Probe/SKIP pattern inherited from `bench/anchor.py`. Two-sided honesty:

- **Locally**: missing oracle ⇒ `SKIP` with a precise reason; a contributor's build never fails
  for a missing tool.
- **In CI** (the `differential` job in `ci.yml`): all oracles installed at `constraints/ci.txt`
  pins, with a hard-import step (`python -c "import radon.complexity, lizard,
  cognitive_complexity.api"`) before pytest — a missing oracle fails the job outright, so a
  silent SKIP can never mask a regression.

Oracle set: **per-PR, zero-install** — the two `tests/_reference/` ports (stdlib BW extractor;
Python-AST lane) run on every PR as free differential witnesses. **Differential CI job** — radon,
lizard, cognitive_complexity (pip; `cognitive_complexity` specifically witnesses
`--sonar-compat`). **Staged, not yet wired** (§15 items 2 and 4, and README says the same): PMD (the
serious second Java cyclomatic witness — until then Java cyclomatic is witnessed by lizard only,
and Java cognitive complexity has NO external oracle, only the corpus and the spec, as the
divergence-list preamble states), rust-code-analysis (last release 2023; a scheduled-job candidate,
not per-PR infrastructure), and a pinned wild-file input set. **SonarQube is excluded as an
automated oracle** (server architecture); its whitepaper is a *spec source*, with
cognitive_complexity as the Sonar-lineage witness. Inputs today: the whole corpus + inline probe
snippets in the per-oracle tests.

### 8.3 BW faithfulness reproduction (§6.3 — the make-or-break)

`validation/bw_faithfulness/`, reviewer-rerunnable:

1. **fetch** — Scalabrino replication package
   (`https://dibt-research.unimol.it/report/readability/files/DatasetBW.zip`), checksum-verified,
   cached, **never committed** (license is *unstated* — verified 2026-07; contacting the authors
   is a tracked pre-1.0 task). Unavailable ⇒ honest SKIP, anchor.py style.
2. **extract** — the *public API path* (`granularity="snippet"`, Java) over all 100 snippets →
   `features.csv` stamped with spec/grammar/feature-order-sha.
3. **train** — the shipped scaffold (dogfooding): binarize per the paper's protocol (the exact
   binarization and classifier battery choice is documented, with any deviation from the paper
   stated), 10-fold CV logistic regression, fixed seed.
4. **report** — accuracy **with bootstrap CI** (n=100 ⇒ ±8pp sampling noise; a bare ≥0.75
   threshold can pass or fail by chance, so the gate is "CI overlaps the paper's ≈80%" plus
   trend), AUC, and the **per-feature table**: Spearman of each feature vs annotator means,
   sign-compared to the paper's Fig. 9 directionality — this localizes a failure to a specific
   BW-\*/TOK-\* ruling instead of one opaque number. Stats use the portable stdlib
   `spearman`/`ci95_bootstrap` from Spaghetti's `bench/grade.py` (NOTICE-credited).

The pipeline is **local and manual only — it never runs in CI** (§11, RELEASING.md): an author
granted redistribution by email (2026-07-12, dataset.toml), but fetching stays a deliberate local
action and only aggregates are tracked, by repo-focus choice. What IS tracked
are the derived artifacts (`derived/`: per-snippet feature vectors + aggregate reports), which
make the extraction step diffable after the fact; there is no automated per-PR guard over them —
an extractor change that would invalidate them shows up in the corpus/fidelity gates, and
re-running the pipeline against a refreshed spec is a deliberate, documented act.

### 8.4 Determinism & performance

- `test_determinism.py`: run the CLI twice on the corpus under different `PYTHONHASHSEED`s;
  byte-compare JSON and CSV. **Float policy** (CORE-ALL-0004): canonical output rounds floats to
  12 significant digits (round-half-even) at serialization; corpus float assertions always carry
  tolerances; the byte-identity claim is scoped **per platform** (libm `ln()` may differ across
  OS/arch — documented, not hidden).
- `test_perf_smoke.py`: a throughput floor over the corpus (catching the easy regression class —
  e.g. re-loading spec TOMLs per call) plus assertions that `Session` reuses parsers and the
  ruling registry loads once. The declared audience (pretraining-data filtering, corpus-scale
  MSR) measures 10⁵–10⁶ files; `Session` is the corpus-scale entry point (caching; deterministic
  sequential order — parallelism is 1.x).

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

JSON always embeds the full provenance block. **CSV is wide-format** (one row per file/function
scope; flat metric + BW columns) **plus mandatory provenance columns**
(`spec_version, grammar_version, cognitive_mode, extrapolated`) — a pasted CSV row in someone's
paper still names its spec. `--lang auto` = extension map; ambiguity is an explicit error, never
a guess. Diagnostics → stderr, data → stdout; exit codes 0/1/2.

## 10. Grammar-evolution policy (the top long-term risk)

- Install metadata uses **compatible ranges** (`tree-sitter>=0.25,<0.27`,
  `tree-sitter-python>=0.25,<0.26`, `tree-sitter-java>=0.23.5,<0.24`) so pip can resolve in
  shared environments; `constraints/ci.txt` pins **exact** versions for CI and releases;
  `spec/validated_grammars.toml` records the calibrated set; provenance records the
  **actually-installed** versions and stamps `validated=false` + diagnostic on deviation. Run and
  label — never refuse, never trust silently.
- **Fixed upgrade procedure**: bump pin on a branch → run consistency + differential suites → any
  changed number forces a spec **major** + changelog entry; no change = spec patch. The
  `grammar-bump.yml` weekly job runs the corpus against the *latest* grammars and opens an issue
  with the per-case diff on drift (never auto-merges). Grammar evolution becomes a reviewed
  calibration event.

## 11. Packaging & CI

- hatchling, src layout, `requires-python = ">=3.10"`, `tomli; python_version < "3.11"`.
  Runtime deps: the tree-sitter binding + two grammar wheels + nothing else.
- Extras: `[retrain]` (scikit-learn), `[oracles]` (radon, lizard, cognitive_complexity —
  test-time only), `[dev]`.
- CI, as built (original plan de-scoped per §15 items 3–4): `ci.yml` (ubuntu × 3.10/3.12/3.14:
  ruff, mypy --strict as a hard gate, unit, consistency, spec-coverage, spec-drift,
  grammar-integrity, BW port fidelity, AST-lane crosscheck, determinism; plus a `differential`
  job — oracles at `constraints/ci.txt` pins, hard-import step so SKIP cannot mask absence,
  zero unclassified divergences, stale entries fail; plus a spec-docs staleness job);
  `docs.yml` (mkdocs build --strict, Pages deploy); `grammar-bump.yml` (weekly early warning);
  `release.yml` (gate + build in parallel → PyPI trusted publishing → GitHub Release → Zenodo
  webhook; RELEASING.md). Deliberately NO bw-faithfulness workflow: fetching the dataset stays a
  local action by repo-focus choice (RELEASING.md "What deliberately does NOT
  happen here").
- Docs (mkdocs-material): quickstart, typed API, **generated** spec tables + divergence list, the
  honesty page, adding-a-language. Paper sources (ACM format, MSR tool track) live in a local,
  gitignored `paper/` directory — submission material stays out of the public repo until
  publication.

## 12. Reuse from Spaghetti Architect (NOTICE-credited, DOI 10.5281/zenodo.21033174)

| Origin | Destination | Role |
|---|---|---|
| `bench/anchor.py::bw_readability_features` + `_BW_FEATURE_NAMES` | `tests/_reference/bw_stdlib.py` (verbatim) + canonical order in `readability/bw2010.py` | Reference extractor; per-PR differential oracle for the tree-sitter BW port |
| `eval/metrics.py::cyclomatic/_traverse/halstead/maintainability_index` | `tests/_reference/py_ast_lane.py` (verbatim) + algorithm basis of `metrics/cognitive.py` | Python-AST oracle; the proven elif-flattening walk |
| `bench/anchor.py` probe/SKIP pattern (`_PROBES`, `_SKIP_REASON`) | `tests/differential/` | Honest-SKIP oracle harness |
| `bench/grade.py::spearman/mean/ci95_bootstrap` | `validation/bw_faithfulness/` | Faithfulness statistics (pure stdlib) |
| `eval/metrics.py` regex-lane ruling knowledge (comment prefixes, branch keywords) | `spec/rulings/*.toml` | Ruling raw material only — the lane itself is not shipped |

Not ported (anti-salami boundary): SPAGH markers, IR/anti-optimization machinery, the validity
study. codecaliper measures arbitrary user source; the only overlap with the DMLR artifact is
general-purpose measurement primitives.

## 13. Honesty boundaries (verbatim commitments, on the docs honesty page and in diagnostics)

1. Procedural consistency ≠ cross-language numerical comparability.
2. MI contains CC — never treat them as independent signals (typed `derived_from`).
3. Halstead absolute values are implementation-defined; only trends/ratios are stable.
4. BW output is a feature set, not a score; no score field exists.
5. Function/file readability vectors are labelled extrapolation; the calibrated regime is
   4–11-line snippets.
6. Metrics operate on pre-preprocessing source text.
7. Byte-identical output is a per-platform claim (float/libm caveat documented).
8. The BW-ambiguity rulings are arbitrated on the same dataset the reproduction reports —
   evidence of faithful operationalization, not independent construct validation.

## 14. Decision log (what was chosen over what)

| Decision | Rejected alternative | Why |
|---|---|---|
| Validation-first skeleton, lean core | Gate-maximalist instrument design | Unbuildable solo in 8 weeks; per-value provenance objects & tamper checks are speculative bloat |
| Plain dict tables + named hooks in adapters | `when.*` predicate DSL in nodemap.toml | A DSL needs an interpreter, tests, and hits expressiveness walls immediately |
| Plain dict registry | setuptools entry-point plugins | Speculative until a third-party adapter exists |
| Lexical Halstead | AST-harvest Halstead | Cross-language uniformity; lexer reuse; the divergence is declared via halstead-approximation (no Halstead differential lane wired) |
| Range pins + CI lockfile + validated flag | Exact `==` grammar pins in install metadata | `==` fights pip resolution in shared envs; the flag keeps honesty without breaking installs |
| Run-and-label on unvalidated grammars | Refuse to run | Provenance already records the truth; refusal punishes legitimate environments |
| PMD in CI, rust-code-analysis scheduled-only | All oracles per-PR | PMD is the only serious Java witness; RCA is stale (2023) — witness value without treadmill |
| ctx.count() + opt-in `--explain` traces | rulings-applied lists only | Divergence triage needs *where and how much*, not just *which* |
| 12-sig-digit float quantization + per-platform byte claim | Cross-OS byte-identity claim | libm differences make the stronger claim false; honesty is the brand |
| Indentation tab = 8 (TOK-ALL-0006, supersedes TOK-ALL-0004's tab = 1) | tab = 1 / tab = 4 | Pre-registered 32-cell arbitration: tab=1 zeroes the Fig. 9 indentation correlation; any tab>=2 fixes the sign, 8 won the pre-registered AUC tie-break (8-vs-4 is a stated convention pick within noise) |
| BW token features see ERROR-region tokens (BW-ALL-0007) | Error-opaque BW (CORE-ALL-0002 everywhere) | The BW construct is lexical (the original tool was grammar-less); opacity zeroed 8/100 original snippets and depressed AUC 0.798 -> fallback 0.827 (matrix cell; the final re-run's headline is 0.828 — same configuration, one ranked pair of serialization-precision difference, see the arbitration report); metrics stay opaque |
| Java arithmetic-op class unchanged after arbitration (null result) | Adding ++/--/compound assignment | No variant changed any Fig. 9 sign in 32 cells; AUC spread <= 0.00125 is noise — a ruling is not changed on noise |

## 15. De-scoping ladder (cut order when — not if — W6 slips)

1. `--explain` traces → 1.1 (the `ctx.count` seam stays; only the CLI surface slips).
2. Wild-corpus differential inputs → corpus-only differential.
3. macOS/Windows CI jobs → ubuntu-only (determinism claim already per-platform).
4. PMD oracle → lizard-only Java witnessing for 1.0 (divergence list notes the gap).
5. `Session` caching → plain `measure()` (perf smoke gate relaxes).
6. Never cut: the consistency corpus, the spec-drift gate, the BW faithfulness pipeline, the
   honest-SKIP differential harness. These are the paper's evidence base.

## 16. Milestones (unchanged from the charter, sharpened)

- **W1–3**: skeleton; tree-sitter wired (Python+Java); BW ported onto tree-sitter with the
  stdlib reference as per-PR oracle; first consistency cases; spec registry + seed rulings.
- **W4–5**: dual-mode cognitive; AST-lane crosscheck green; spec table v0.1 complete; drift gate on.
- **W6**: **BW faithfulness reproduction** (snippet-scaffold ruling first!); differential lane +
  divergence list.
- **W7**: CLI complete (`env`, `cite`), docs, community files.
- **W8**: tool-showcase paper (ACM format, 4+1 pages) + screencast video; tag + Zenodo archival
  DOI; submit to the MSR Data & Tool Showcase (tool track).
