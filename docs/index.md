# codecaliper

codecaliper measures code readability (the raw Buse-Weimer 2010 feature set)
and complexity (cyclomatic, dual-mode cognitive, Halstead, maintainability
index, LOC) for Python, Java, and Go, and it tells you where every number came from.

A metrics scoreboard says *"CC = 7"*. codecaliper says *"CC = 7 under spec
1.1.0, on tree-sitter-python 0.25.0, and here are the seven increments, each one
with the ruling that made it and the span it fired on"*. Every value it emits
is:

- **traceable**: to a versioned metric-to-syntax specification, to the exact
  machine-readable [rulings](spec/rulings.md) that fired, and to the exact
  tree-sitter grammar that parsed the source;
- **reproducible**: clock-free, hash-seed-free, order-stable. Identical input
  under identical versions gives byte-identical output on a given platform.

## What it measures

| family | what you get |
|---|---|
| **Readability** (the core) | the raw **Buse-Weimer (2010) 25-feature vector** at snippet, function or file granularity, every vector labelled with its unit. There is deliberately [no readability score](honesty.md) |
| Cyclomatic complexity | one number per function and per file; every counting decision is a ruling |
| Cognitive complexity | **dual-mode**: whitepaper-faithful by default, `--sonar-compat` on request. The two modes differ by an enumerable table of ruling pairs, which the spec publishes |
| Halstead | a declared lexical approximation, labelled on every value |
| Maintainability index | typed as *derived from* Halstead volume, cyclomatic and SLOC, so it cannot be mistaken for an independent signal |
| LOC family | physical, blank, source, comment, logical |

## Why an instrument

Two tools disagree about the same file because each one is a different
*operationalization* of the same construct. radon and lizard count cyclomatic
differently. The cognitive-complexity ports disagree with each other and with
the whitepaper. Every hand-rolled Buse-Weimer extractor in the literature made
its own undocumented calls about what counts as a token. That disagreement is
inherent and will not go away. What can go away is its being unrecorded, which is
what leaves a reader downstream unable to tell which operationalization produced
the number in front of them.

codecaliper records it, with four mechanisms:

1. a **versioned mapping specification**: rulings with immutable IDs, shipped
   as package data, stamped into every result;
2. a **hand-computed consistency corpus**, where every active ruling is
   exercised by a case whose expected values a human worked out, with the
   working shown;
3. **differential tests** against radon, lizard and cognitive_complexity with a
   published [known-divergence list](spec/divergences.md), each divergence
   classified against a ruling, in both directions;
4. a **faithfulness reproduction** of the original Buse-Weimer experiment on
   the paper's own dataset, with the ambiguous feature definitions settled by a
   pre-registered arbitration. See [Validation](validation.md).

## Install

```bash
pip install codecaliper   # https://pypi.org/project/codecaliper/
```

For research use, add the exact calibrated grammar pins. A deviating grammar
still runs, but then every report it produces is labelled `validated: false`:

```bash
pip install codecaliper -c https://raw.githubusercontent.com/KurathSec/codecaliper/main/constraints/ci.txt
```

Then head to the [Quickstart](quickstart.md). What the numbers refuse to claim
is on [Honesty invariants](honesty.md), and how to add a language or a ruling is
on [Contributing](contributing.md).

## Citing

`codecaliper cite` prints a methods-section template naming the package, spec
and grammar versions your numbers were produced under. Report all three: a
package version alone does not pin a value. Citation metadata lives in
[`CITATION.cff`](https://github.com/KurathSec/codecaliper/blob/main/CITATION.cff).
