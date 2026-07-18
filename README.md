# codecaliper

[![ci](https://github.com/KurathSec/codecaliper/actions/workflows/ci.yml/badge.svg)](https://github.com/KurathSec/codecaliper/actions/workflows/ci.yml)
[![docs](https://github.com/KurathSec/codecaliper/actions/workflows/docs.yml/badge.svg)](https://kurathsec.github.io/codecaliper/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21312527.svg)](https://doi.org/10.5281/zenodo.21312527)

A code-readability and complexity **measurement instrument** for Python, Java, and Go,
built on tree-sitter. Documentation: <https://kurathsec.github.io/codecaliper/>

Every number codecaliper emits is *traceable* and *reproducible*: traceable to a
versioned metric-to-syntax specification, to the exact rulings that fired, and to
the exact grammar that parsed the source; reproducible because it is clock-free,
hash-seed-free and order-stable. Where a scoreboard says "CC = 7", codecaliper
says "CC = 7 under spec 1.2.0, ruling CC-PY-0003, tree-sitter-python 0.25.0".

This README says what the tool is and how to use it. The design rationale, the
requirements record and the decision log are in
[`ARCHITECTURE.md`](ARCHITECTURE.md); how to add a ruling, a corpus case or a
language is in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## What it measures

**Readability** is the point of the tool. codecaliper is an open, tested,
cross-language implementation of the Buse-Weimer (2010) 25-feature readability
set. The features come from the paper; what the tool adds is that every one of
them is pinned. Figure 6 does not settle the questions an implementer actually
has to answer (does a block comment count on every line it spans? is the dot in
a qualified name a "period"?), so each answer here is a numbered ruling, and
every number the tool emits cites the rulings that produced it. Two of those
answers were not guessed: they were arbitrated on the original dataset by a
pre-registered experiment, and the spec then moved to record what the experiment
decided. One replaced an earlier ruling (`TOK-ALL-0006` supersedes `TOK-ALL-0004`,
tab width 1 to 8, a spec MAJOR because it moved corpus values); the other added a
ruling that had not existed (`BW-ALL-0007`, lexical fallback). See [Status](#status).

Output is always the raw feature vector, computed on tree-sitter with comments
and positions preserved. There is no "readability score" anywhere in the API, by
design; a retraining scaffold ships instead of weights. The Scalabrino and Dorn
feature sets slot into the same seam in 1.x.

**Complexity** is the convenience half: cyclomatic; cognitive in two modes
(whitepaper-faithful by default, `--sonar-compat` opt-in, with every divergence
between the modes written down as a spec ruling); Halstead, declared as a
lexical approximation; the maintainability index, typed as *derived from* CC so
nobody mistakes it for an independent signal; and the LOC family.

## Why an instrument

Start with what an unwritten lexer convention costs. Buse and Weimer's Figure 9
reports indentation as negatively correlated with readability: the more you
indent, the less readable people judge the code. The paper never says how wide a
tab is. Read a tab as one column and, on the paper's own 100 snippets,
`avg_indentation` correlates with the human scores at Spearman rho **+0.0007**
and `max_indentation` at **-0.007**. That is no signal at all, and the first one
sits on the wrong side of zero. Read a tab as eight columns, same extractor, same
data, and the two features give **-0.230** and **-0.254**, the direction the paper
reports; agreement with its 24 clear-signed features goes from 20 to 21. One
undocumented lexer choice decides whether you reproduce a published finding or
quietly null it out.

So tab width is not a convention here. It is ruling TOK-ALL-0006, adopted over
the tab-as-1 ruling it supersedes because a pre-registered experiment on the
original dataset said so, and cited by every vector that depends on it. Any
readability extractor makes dozens of decisions of that shape. Writing each one
down under an ID a reader can look up is what lets someone else tell your
implementation of a construct apart from the construct itself.

The four rho values above are in
`validation/bw_faithfulness/derived/arbitration_report.json`, under
`matrix."fallback_on/tab=1/V0_current"` and `matrix."fallback_on/tab=8/V0_current"`
(key `spearman_arbitrated`), which is also where the 20-to-21 sign counts come
from (`n_sign_agree`). The adopted tab=8 pair is reported again, rounded, in the
per-feature table of
`validation/bw_faithfulness/derived/bw_faithfulness_report.md`. The prose verdict
and the tie-break are in `arbitration_report.md`, which carries the reasoning but
not the correlations.

Tools disagree about the same file because each one is a different
operationalization of the same construct. radon and lizard do not compute the
same cyclomatic number. Neither do two hand-rolled Buse-Weimer extractors.
codecaliper's response is to make its own operationalization inspectable:

- a **versioned mapping specification**, machine-readable rulings with immutable
  IDs (`CC-PY-0003`), shipped as package data and stamped into every result;
- a **hand-computed consistency corpus**, where every active ruling is exercised
  by a case whose expected values a human worked out and wrote down;
- **differential tests** against radon, lizard, cognitive_complexity and PMD,
  with a published known-divergence list. Every disagreement is classified
  against a ruling; an unclassified divergence fails CI, and so does a stale
  entry. The first three are pip oracles; PMD is a JVM tool, outside that pip
  closure, so it carries its own pin (`tests/differential/pmd.toml`), needs
  `java` on PATH, and is an honest SKIP locally when absent.
  rust-code-analysis is staged, not yet wired;
- a **faithfulness reproduction** of the original Buse-Weimer study, using this
  extractor and a retrained model.

## Honesty boundaries

codecaliper guarantees procedural consistency: identical rules over isomorphic
syntax across languages. It does not guarantee that a Python CC and a Java CC
are numerically comparable. MI contains CC. Halstead absolute values are
implementation-defined. The BW vector is calibrated on short snippets (a
diagnostic fires outside the tool's 4-to-11-line window), so function-level and
file-level vectors are labelled extrapolation. Metrics run on
pre-preprocessing source text. None of this lives only in this README: it is
enforced in the result types and emitted as diagnostics (ARCHITECTURE.md §13).

## Install

```bash
pip install codecaliper          # PyPI: https://pypi.org/project/codecaliper/
pip install -e .                 # from a checkout
```

For research use, pin the calibrated grammars as well. A grammar version other
than the calibrated one still parses and still measures, but the numbers are no
longer the numbers the spec was calibrated against, so every report produced
under it is stamped `grammar.validated: false` and carries an
`unvalidated-grammar` diagnostic:

```bash
pip install codecaliper -c https://raw.githubusercontent.com/KurathSec/codecaliper/main/constraints/ci.txt
pip install -e . -c constraints/ci.txt   # from a checkout
```

The calibrated versions are listed in
`src/codecaliper/spec/validated_grammars.toml` (currently tree-sitter-python
0.25.0, tree-sitter-java 0.23.5, tree-sitter-go 0.25.0). To see what you are actually running, and
whether it is calibrated:

```console
$ codecaliper env
codecaliper 0.2.0
spec 1.2.0
python 3.14.6 (Linux x86_64)
tree-sitter 0.26.0 (binding)
tree-sitter-python 0.25.0 (ABI 15, calibrated)
tree-sitter-java 0.23.5 (ABI 14, calibrated)
tree-sitter-go 0.25.0 (ABI 15, calibrated)
```

An uncalibrated grammar prints `UNVALIDATED` on its line. That plate belongs in
your bug report and in your methods section.

## Use

```bash
codecaliper myfile.py --json
codecaliper src/**/*.java --csv -o metrics.csv
codecaliper myfile.py --sonar-compat --explain
codecaliper spec show CC-PY-0003     # read the ruling behind a number
codecaliper env                      # the calibration plate for bug reports and papers
codecaliper cite                     # methods-section template
```

```python
from codecaliper import measure

report = measure(source_code, language="python")
cc = next(m for m in report.file_metrics if m.metric == "cyclomatic")
print(cc.value, cc.rulings, report.provenance.spec_version)

vec = report.readability[0]          # the raw BW 25-feature vector, never a score
print(dict(zip(vec.names, vec.values)), vec.extrapolated)
```

## Status

Package **0.2.0** is released: on
[PyPI](https://pypi.org/project/codecaliper/), tagged
[v0.2.0](https://github.com/KurathSec/codecaliper/releases/tag/v0.2.0), archived
at Zenodo. The badge above is the concept DOI, which always resolves to the
latest version; every released version also has its own DOI, listed on that
Zenodo record. It ships spec **1.2.0**: the spec and the package are versioned
independently, and 0.2.0 shows the split working in the other direction from
0.1.1 — a third language (Go) arrived as new rulings and new corpus cases, a
spec MINOR, while every previously emitted number stayed where it was.
See [`CHANGELOG.md`](CHANGELOG.md).

Python, Java and Go are wired end-to-end. Every active ruling is exercised by a
hand-computed corpus case. `mypy --strict` and the differential oracle lane are
hard CI gates.

PMD 7.26.0 is now wired into that lane: the first external witness this project
has had for Java cognitive complexity, and the second for Java cyclomatic
(lizard was the only one). It is independent of tree-sitter all the way down,
with its own Java grammar and its own metric visitors, so agreement with it is
not two wrappers around one parser agreeing with themselves. Over 16 Java
inputs and 2 metrics, 28 of the 32 per-method comparisons agree; the other 4
are classified divergences (`docs/spec/divergences.md`). One gap survives:
recursion is the single axis on which the two cognitive modes differ, and PMD
takes the whitepaper's increment, so it witnesses whitepaper mode there. Java's
sonar-compat recursion behaviour still has no external witness, and rests on
the hand-computed corpus and the spec alone.

The Buse-Weimer faithfulness reproduction ran on the original 100-snippet
dataset: 10-fold logistic accuracy 0.820 (bootstrap 95% CI [0.770, 0.870],
overlapping the paper's ~0.80), AUC 0.828, Fig. 9 sign agreement 21/24. Two
feature-definition ambiguities (indentation tab width, and lexical fallback on
parse errors) were resolved beforehand by a pre-registered arbitration
experiment, and the spec records each outcome: tab width as a supersession
(`TOK-ALL-0006` replacing `TOK-ALL-0004`), lexical fallback as a new ruling
(`BW-ALL-0007`). Reports: `validation/bw_faithfulness/derived/`.

That lane is self-contained: an author of the dataset granted redistribution, so
its raw inputs (the 100 snippets, the annotator matrix and the per-snippet
means, 102 files and 57,168 bytes) are tracked here, and the reproduction
re-runs from the git tree with no network. `oracle.csv` as distributed holds
**121** annotator rows, where the paper says 120. The archive is measured as it
is, the extra row is not reconciled away, and every number here is computed from
all 121. The two other corpora codecaliper
measures carry no such permission and no byte of either is tracked, so the
cross-corpus breadth lane (`validation/breadth/`) needs a network fetch and
always will. The terms, per corpus, are in
[`PERMISSIONS.md`](PERMISSIONS.md).

Next: the MSR Data and Tool Showcase paper (ARCHITECTURE.md §16).

## Development

```bash
pip install -e ".[dev]" -c constraints/ci.txt
pytest
ruff check src tests tools
mypy                 # --strict, configured in pyproject.toml; a hard CI gate
```

All three gate every pull request. `mypy` is run with no arguments, exactly as
`ci.yml` runs it: `[tool.mypy]` already sets `strict = true` and the files to
check. [`CONTRIBUTING.md`](CONTRIBUTING.md) has the rest, including how to add a
ruling, supersede one, or add a language.

## Citing

Citation metadata lives in
[`CITATION.cff`](https://github.com/KurathSec/codecaliper/blob/main/CITATION.cff),
which is what GitHub's "Cite this repository" box and Zenodo both read.
`codecaliper cite` prints a methods-section template naming the package
version, the spec version and the grammar versions your numbers were produced
under. Report all three.

If you use the Buse-Weimer corpus through this repository, cite the two original
papers as its authors asked (`PERMISSIONS.md`).

## License and provenance

MIT. Some measurement primitives descend from
[Spaghetti Architect](https://doi.org/10.5281/zenodo.21033174), by the same
author; see [`NOTICE`](NOTICE), which also carries the data attribution for the
Buse-Weimer corpus.
