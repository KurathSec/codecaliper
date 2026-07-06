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

- package 0.1.0.dev0 · spec 1.0.0 · grammars: tree-sitter-python 0.25.0,
  tree-sitter-java 0.23.5 (binding tree-sitter 0.26.0)
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
- Initial scaffold: unified tree-sitter measurement base (Python + Java),
  Buse–Weimer 25-feature extractor (fidelity-tested against the reference
  implementation), cyclomatic complexity, dual-mode cognitive complexity
  (whitepaper / `--sonar-compat`), lexical Halstead, maintainability index,
  LOC family.
- Versioned ruling registry with immutable IDs, hand-computed consistency
  corpus, and the three mechanical gates (spec drift, ruling coverage,
  grammar integrity).
- CLI: `measure` (default), `spec show`, `env`, `cite`.
