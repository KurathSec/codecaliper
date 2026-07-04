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

- package 0.1.0.dev0 · spec 0.1.0 · grammars: tree-sitter-python 0.25.0,
  tree-sitter-java 0.23.5 (binding tree-sitter 0.26.0)
- Initial scaffold: unified tree-sitter measurement base (Python + Java),
  Buse–Weimer 25-feature extractor (fidelity-tested against the reference
  implementation), cyclomatic complexity, dual-mode cognitive complexity
  (whitepaper / `--sonar-compat`), lexical Halstead, maintainability index,
  LOC family.
- Versioned ruling registry with immutable IDs, hand-computed consistency
  corpus, and the three mechanical gates (spec drift, ruling coverage,
  grammar integrity).
- CLI: `measure` (default), `spec show`, `env`, `cite`.
