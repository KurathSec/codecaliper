# codecaliper

> A cross-language (Python + Java, more staged) **code-readability + complexity
> measurement instrument** — not another metrics scoreboard.

codecaliper is built as an *instrument*: every number it emits is **traceable**
— to a versioned metric-to-syntax specification, to the exact machine-readable
rulings that fired, to the exact tree-sitter grammar that parsed the source —
and **reproducible** — clock-free, hash-seed-free, order-stable. Where a
scoreboard says "CC = 7", codecaliper says "CC = 7 *under spec 0.1.0, ruling
CC-PY-0003, tree-sitter-python 0.25.0, whitepaper mode*".

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
2. a **hand-computed consistency corpus** — every ruling is exercised by a case
   with human-verified expected values;
3. **differential tests** against radon / lizard / cognitive_complexity / PMD /
   rust-code-analysis with a **published known-divergence list** — every
   disagreement is classified against a ruling or an upstream bug, or CI fails
   (this lane lands pre-1.0; see Status);
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

Pre-1.0 scaffold (spec v0.1.0): Python + Java wired end-to-end; seed ruling set
and consistency corpus; the differential lane and the BW faithfulness
reproduction are the next milestones (see `ARCHITECTURE.md` §16).

## Development

```bash
pip install -e ".[dev]" -c constraints/ci.txt
pytest
ruff check src tests tools
```

See `ARCHITECTURE.md` for the full design (data model, spec mechanism,
validation architecture, grammar-evolution policy) and `CONTRIBUTING.md` for
how rulings, corpus cases, and adapters are added.

## License & provenance

MIT. Some measurement primitives descend from
[Spaghetti Architect](https://doi.org/10.5281/zenodo.21033174) (same author) —
see `NOTICE`.
