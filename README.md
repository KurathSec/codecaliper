# codecaliper

[![ci](https://github.com/KurathSec/codecaliper/actions/workflows/ci.yml/badge.svg)](https://github.com/KurathSec/codecaliper/actions/workflows/ci.yml)
[![docs](https://github.com/KurathSec/codecaliper/actions/workflows/docs.yml/badge.svg)](https://kurathsec.github.io/codecaliper/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21312527.svg)](https://doi.org/10.5281/zenodo.21312527)

> A cross-language (Python + Java, more staged) **code-readability + complexity
> measurement instrument** — not another metrics scoreboard.
> Documentation: <https://kurathsec.github.io/codecaliper/>

codecaliper is built as an *instrument*: every number it emits is **traceable**
— to a versioned metric-to-syntax specification, to the exact machine-readable
rulings that fired, to the exact tree-sitter grammar that parsed the source —
and **reproducible** — clock-free, hash-seed-free, order-stable. Where a
scoreboard says "CC = 7", codecaliper says "CC = 7 *under spec 1.1.0, ruling
CC-PY-0003, tree-sitter-python 0.25.0*".

## What it measures

- **Readability (the core):** the first open, tested, cross-language
  implementation of the **Buse–Weimer (2010) 25-feature readability set**,
  computed on tree-sitter (comments and positions preserved). Output is always
  the **raw feature vector** — there is deliberately no "readability score" —
  plus a retraining scaffold. Scalabrino/Dorn feature sets are staged for 1.x.
- **Complexity (a convenience, not the selling point):** cyclomatic,
  **dual-mode cognitive complexity** (whitepaper-faithful by default,
  `--sonar-compat` opt-in, every divergence between the modes is an enumerable
  spec ruling), Halstead (a declared lexical approximation), maintainability
  index (typed as *derived from* CC — never an independent signal), and the
  LOC family.

## Why an instrument

Different tools disagree on the same file because each is a different
*operationalization* of the same construct (radon vs lizard cyclomatic; the
per-language cognitive-complexity ports; every hand-rolled Buse–Weimer
extractor in the literature). codecaliper's answer:

1. a **versioned mapping specification** — machine-readable rulings with
   immutable IDs (`CC-PY-0003`), shipped as package data, stamped into every
   result;
2. a **hand-computed consistency corpus** — every active ruling is exercised by
   a case with human-verified expected values;
3. **differential tests** against radon / lizard / cognitive_complexity with
   a **published known-divergence list** — every disagreement is classified
   against a ruling, in both directions (an unclassified divergence fails CI,
   and so does a stale entry); PMD and rust-code-analysis are staged as
   additional oracles;
4. a **faithfulness reproduction** of the original Buse–Weimer study (100 Java
   snippets, 120 annotators) using this extractor and a retrained model.

## Honesty boundaries

codecaliper guarantees **procedural consistency** (identical rules over
isomorphic syntax across languages), *not* cross-language numerical
comparability. MI contains CC. Halstead absolute values are
implementation-defined. BW output is a feature set, not a score, calibrated on
4–11-line snippets — function/file vectors are labelled extrapolation. Metrics
operate on pre-preprocessing source text. Every one of these is enforced in the
result types, not just stated here.

## Install

```bash
pip install codecaliper          # (not yet on PyPI — install from source for now)
pip install -e .                 # from a checkout
```

## Use

```bash
codecaliper myfile.py --json
codecaliper src/**/*.java --csv -o metrics.csv
codecaliper myfile.py --sonar-compat --explain
codecaliper spec show CC-PY-0003     # read the ruling behind a number
codecaliper env                      # the calibration plate for bug reports/papers
codecaliper cite                     # methods-section template
```

```python
from codecaliper import measure

report = measure(source_code, language="python")
cc = next(m for m in report.file_metrics if m.metric == "cyclomatic")
print(cc.value, cc.rulings, report.provenance.spec_version)

vec = report.readability[0]          # raw BW 25-feature vector — never a score
print(dict(zip(vec.names, vec.values)), vec.extrapolated)
```

## Status

Spec **v1.1.0** (package 0.1.0.dev0 — the spec and package are versioned
independently): Python + Java wired end-to-end; every active ruling is
exercised by a hand-computed corpus case; mypy --strict and the differential
oracle lane (radon/lizard/cognitive_complexity, classified divergence list)
are hard CI gates. The BW faithfulness reproduction ran on the original
100-snippet dataset: 10-fold logistic accuracy 0.820 (bootstrap 95% CI
[0.770, 0.870], overlapping the paper's ~0.80), AUC 0.828, Fig. 9 sign
agreement 21/24 — after a pre-registered arbitration experiment resolved two
feature-definition ambiguities (indentation tab width; lexical fallback on
parse errors) as versioned ruling supersessions (see
`validation/bw_faithfulness/derived/`). The
[docs site](https://kurathsec.github.io/codecaliper/) and the tag-triggered
release pipeline (PyPI trusted publishing + Zenodo archival, `RELEASING.md`)
are in place; next: the first tagged release (v0.1.0 + DOI) and the MSR
Data & Tool Showcase paper (`ARCHITECTURE.md` §16, W8).

## Development

```bash
pip install -e ".[dev]" -c constraints/ci.txt
pytest
ruff check src tests tools
```

See `ARCHITECTURE.md` for the full design (data model, spec mechanism,
validation architecture, grammar-evolution policy) and `CONTRIBUTING.md` for
how rulings, corpus cases, and adapters are added.

## Citing

Citation metadata lives in
[`CITATION.cff`](https://github.com/KurathSec/codecaliper/blob/main/CITATION.cff)
(GitHub's "Cite this repository" box reads it; Zenodo archives releases from
it).
`codecaliper cite` prints a methods-section template stating the package,
spec, and grammar versions your numbers were produced under — report all
three.

## License & provenance

MIT. Some measurement primitives descend from
[Spaghetti Architect](https://doi.org/10.5281/zenodo.21033174) (same author) —
see `NOTICE`.
