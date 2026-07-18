# Quickstart

## CLI

Here is `demo.py`, four lines, one branch:

```python
def classify(value, limit):
    if value > limit and value < 100:
        return "high"
    return "low"
```

`codecaliper demo.py` measures it and prints a JSON report. The default report
carries every metric family plus the 25-feature readability vector, so it runs
to a few hundred lines. Restricting it to two metrics makes it small enough to
print whole, and nothing below is elided:

```bash
codecaliper demo.py --metrics cyclomatic,cognitive --no-readability
```

```json
{
  "path": "demo.py",
  "parse_ok": true,
  "file_metrics": [
    {
      "metric": "cyclomatic",
      "value": 3,
      "rulings": [
        "CC-ALL-0001",
        "CC-PY-0001",
        "CC-PY-0002",
        "CC-PY-0003",
        "CC-PY-0004",
        "CC-PY-0005",
        "CC-PY-0006",
        "CC-PY-0007",
        "CC-PY-0008"
      ],
      "derived_from": [],
      "trace": [],
      "diagnostics": []
    },
    {
      "metric": "cognitive",
      "value": 2,
      "rulings": [
        "COG-ALL-0001",
        "COG-ALL-0002",
        "COG-ALL-0003",
        "COG-ALL-0004",
        "COG-ALL-0005",
        "COG-PY-0001"
      ],
      "derived_from": [],
      "trace": [],
      "diagnostics": []
    }
  ],
  "functions": [
    {
      "name": "classify",
      "qualified_name": "classify",
      "span": {
        "start_line": 1,
        "start_col": 0,
        "end_line": 4,
        "end_col": 16
      },
      "metrics": [
        {
          "metric": "cyclomatic",
          "value": 3,
          "rulings": [
            "CC-ALL-0001",
            "CC-PY-0001",
            "CC-PY-0002",
            "CC-PY-0003",
            "CC-PY-0004",
            "CC-PY-0005",
            "CC-PY-0006",
            "CC-PY-0007",
            "CC-PY-0008"
          ],
          "derived_from": [],
          "trace": [],
          "diagnostics": []
        },
        {
          "metric": "cognitive",
          "value": 2,
          "rulings": [
            "COG-ALL-0001",
            "COG-ALL-0002",
            "COG-ALL-0003",
            "COG-ALL-0004",
            "COG-ALL-0005",
            "COG-PY-0001"
          ],
          "derived_from": [],
          "trace": [],
          "diagnostics": []
        }
      ]
    }
  ],
  "readability": [],
  "diagnostics": [],
  "provenance": {
    "tool_version": "0.2.0",
    "spec_version": "1.2.0",
    "language": "python",
    "grammar": {
      "language": "python",
      "package": "tree-sitter-python",
      "version": "0.25.0",
      "abi_version": 15,
      "validated": true
    },
    "modes": {
      "cognitive": "whitepaper"
    },
    "rulings_applied": [
      "CC-ALL-0001",
      "CC-PY-0001",
      "CC-PY-0003",
      "COG-ALL-0001",
      "COG-ALL-0003"
    ]
  }
}
```

Cyclomatic is 3 on those four lines, and `rulings_applied` says why: the base
value (CC-ALL-0001), the `if` (CC-PY-0001), and the `and` (CC-PY-0003, "Boolean
short-circuit operators count per operator"). Cognitive is 2, because it treats
the same `and` differently: a boolean *sequence* increments once, not once per
operator (COG-ALL-0003).

The two lists differ on purpose. A metric's `rulings` are the decisions that
govern that metric, whether or not this input triggered them;
`provenance.rulings_applied` is the union of what actually fired here. Keys come
out in a fixed canonical field order, not alphabetically: `path`, `parse_ok`,
`file_metrics`, `functions`, `readability`, `diagnostics`, `provenance`. There
are no timestamps and no hash-order dependence, so the same input under the same
versions gives byte-identical output on a given platform.

Add `--explain` and each metric's `trace` fills with the individual increments,
every one carrying the ruling that made it and the span it fired on. The
cyclomatic trace on `demo.py` holds exactly three:

| ruling | span (line:col) | delta |
|---|---|---|
| CC-ALL-0001 | 1:0 to 4:0 | +1 |
| CC-PY-0001 | 2:4 to 3:21 | +1 |
| CC-PY-0003 | 2:7 to 2:36 | +1 |

Useful flags:

| flag | effect |
|---|---|
| `--bw-granularity {snippet,function,file}` | BW measurement unit. Vectors outside the native snippet granularity are labelled `extrapolated: true` |
| `--sonar-compat` | cognitive complexity in SonarSource-compatible mode (the mode differences are the `COG-*` ruling pairs in the [spec](spec/rulings.md)) |
| `--explain` | per-increment attribution traces on cyclomatic, cognitive and lloc |
| `--strict` | error exit on parse errors instead of measure-and-label |
| `--metrics`, `--no-readability` | restrict what is computed |
| `--csv`, `-o FILE` | wide-format CSV; write to a file |

Every counting decision can be interrogated. `codecaliper spec show
TOK-ALL-0006` prints that ruling's title, its metric family and language, its
status, the spec version it entered in, the corpus cases that pin it, and the
prose that decides the case:

> Indentation features count leading whitespace with a tab as 8 characters and
> a space as 1. Supersedes TOK-ALL-0004 (tab = 1), whose PROVISIONAL marker was
> resolved by the pre-registered 32-cell BW faithfulness arbitration [...]

The whole set is browsable under [Rulings](spec/rulings.md).

`codecaliper env` prints the installed grammar versions against the calibrated
ones, and `codecaliper cite` prints a methods-section template as a single
unwrapped line, ready to paste (scroll it, or pipe it to `fmt`):

```console
$ codecaliper cite
Metrics were computed with codecaliper 0.2.0 under mapping specification 1.2.0 (grammars: tree-sitter-python 0.25.0, tree-sitter-java 0.23.5, tree-sitter-go 0.25.0); cognitive complexity in whitepaper mode unless stated; readability vectors are the raw Buse-Weimer 2010 feature set, with granularity and extrapolation as labelled in the output.
```

## Python API

```python
from codecaliper import measure

report = measure(source_text, language="python")

report.parse_ok                     # False => measured anyway, and labelled
report.provenance.spec_version      # "1.2.0", on every report
for m in report.file_metrics:
    print(m.metric, m.value, m.rulings)

vec = report.readability[0]         # bw2010: the raw 25-feature vector
dict(zip(vec.names, vec.values))    # canonical order, sha-stamped
vec.extrapolated                    # True at file granularity: BW's native
                                    # unit is the snippet, and that is labelled
```

Per-function vectors and metrics:

```python
report = measure(source_text, language="python", granularity="function")
for fn in report.functions:
    print(fn.qualified_name, fn.span, fn.metrics)
```

Java fragments are usually measured exactly as you pass them:

```python
report = measure(java_fragment, language="java", granularity="snippet")
```

tree-sitter-java's `program` rule already accepts a bare statement sequence or
a bare method declaration, so a snippet in that shape parses on its own and no
wrapper is involved. CORE-JAVA-0001 is a narrow fallback for the fragments that
do not: at snippet granularity, an error-bearing bare parse is retried inside
two candidate class scaffolds, and a scaffold is adopted only when it strictly
beats the bare parse on error count. In practice it rescues constructors and
modifier-bearing members that cannot stand alone as a `program`. On the
Buse-Weimer dataset's 100 snippets, 10 end up scaffolded.

When a scaffold is adopted, the emitted numbers are computed over the original
lines only, spans are rebased to the snippet's own coordinates, and the vector
carries a `snippet-scaffolded` diagnostic. Scaffolding lowers the error count;
it does not have to reach zero, and it cannot repair a fragment that was
truncated mid-construct. Most of the Buse-Weimer snippets are truncated that
way. Of the 100: 27 parse cleanly as they stand, 2 more do once scaffolded, 8
are scaffolded and still error-bearing, and 63 are neither. The 71 that keep
`parse_ok: false` are measured under BW-ALL-0007, described below. Measure the
same corpus at file granularity and 73 come back recovered, because the scaffold
never runs there; [Validation](validation.md) reconciles the two counts.

All result types are frozen dataclasses. See the [API reference](api.md).

## Reading a report honestly

`parse_ok`. On a parse error codecaliper still measures, sets `parse_ok: false`
and attaches `parse-error-recovered`. When the recovered ERROR region actually
adds tokens, the BW token-family features fall back to the full lexical stream
under ruling `BW-ALL-0007` and say so (`bw-lexical-fallback`). A MISSING-only
recovery adds no tokens, so it keeps the opaque stream and carries no fallback
label.

`provenance`. Quote `spec_version` and the grammar versions in anything you
publish. They are what make the number reproducible by someone else.

Per-value `diagnostics`. Every MI value carries `mi-contains-cc`; every Halstead
value carries `halstead-approximation`. Neither is a warning you can clear by
fixing your code: both are permanent properties of the metric.
[Honesty invariants](honesty.md) says what each one is protecting you from.
