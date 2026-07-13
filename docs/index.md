# codecaliper

> A cross-language (Python + Java, more staged) **code-readability +
> complexity measurement instrument** — not another metrics scoreboard.

Where a scoreboard says *"CC = 7"*, codecaliper says *"CC = 7 under spec
1.1.0, ruling CC-PY-0003, tree-sitter-python 0.25.0"*. Every
number it emits is:

- **traceable** — to a versioned metric-to-syntax specification, to the exact
  machine-readable [rulings](spec/rulings.md) that fired, and to the exact
  tree-sitter grammar that parsed the source;
- **reproducible** — clock-free, hash-seed-free, order-stable:
  byte-identical output for identical input, per platform.

## What it measures

| family | what you get |
|---|---|
| **Readability** (the core) | the raw **Buse–Weimer (2010) 25-feature vector** — deliberately [no readability score](honesty.md) — at snippet, function, or file granularity, each labelled |
| Cyclomatic complexity | one number per function/file, every counting decision a ruling |
| Cognitive complexity | **dual-mode**: whitepaper-faithful by default, `--sonar-compat` opt-in; the difference between the modes is an enumerable spec table, not folklore |
| Halstead | a **declared lexical approximation** (labelled on every value) |
| Maintainability index | typed as *derived from* Halstead volume + CC + SLOC — never an independent signal |
| LOC family | physical, blank, source, comment, logical |

## Why an instrument

Different tools disagree on the same file because each is a different
*operationalization* of the same construct — radon vs lizard cyclomatic, the
per-language cognitive-complexity ports, every hand-rolled Buse–Weimer
extractor in the literature. codecaliper's answer:

1. a **versioned mapping specification** — rulings with immutable IDs,
   shipped as package data, stamped into every result;
2. a **hand-computed consistency corpus** — every active ruling is exercised by
   a case with human-verified expected values;
3. **differential tests** against radon / lizard / cognitive_complexity with
   a published [known-divergence list](spec/divergences.md) — every
   divergence is classified against a ruling, in both directions;
4. a **faithfulness reproduction** of the original Buse–Weimer experiment on
   the paper's own dataset, with pre-registered arbitration of ambiguous
   definitions — see [Validation](validation.md).

## Install

```bash
pip install codecaliper   # https://pypi.org/project/codecaliper/
```

For byte-reproducible research use, install the exact calibrated grammar
pins; a deviating grammar still runs, but every report is labelled
`validated: false`:

```bash
pip install codecaliper -c https://raw.githubusercontent.com/KurathSec/codecaliper/main/constraints/ci.txt
```

Then head to the [Quickstart](quickstart.md).

## Citing

`codecaliper cite` prints a methods-section template stating the package,
spec, and grammar versions your numbers were produced under — report all
three. Citation metadata lives in
[`CITATION.cff`](https://github.com/KurathSec/codecaliper/blob/main/CITATION.cff).
