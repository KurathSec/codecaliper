# Quickstart

## CLI

The default command measures a file and prints a deterministic JSON report
(sorted, clock-free — byte-identical for identical input):

```bash
codecaliper path/to/file.py
```

```json
{
  "path": "demo.py",
  "parse_ok": true,
  "file_metrics": [
    {
      "metric": "cyclomatic",
      "value": 3,
      "rulings": ["CC-ALL-0001", "CC-PY-0001", "CC-PY-0002", "..."],
      "derived_from": [],
      "trace": [],
      "diagnostics": []
    },
    "..."
  ],
  "functions": ["..."],
  "readability": ["..."],
  "diagnostics": [],
  "provenance": {
    "tool_version": "0.1.0.dev0",
    "spec_version": "1.0.0",
    "language": "python",
    "grammar": {
      "language": "python",
      "package": "tree-sitter-python",
      "version": "0.25.0",
      "abi_version": 15,
      "validated": true
    },
    "modes": { "cognitive": "whitepaper" },
    "rulings_applied": ["BW-ALL-0001", "...", "MI-ALL-0001"]
  }
}
```

Useful flags:

| flag | effect |
|---|---|
| `--bw-granularity {snippet,function,file}` | BW measurement unit; vectors outside the native snippet granularity are labelled `extrapolated: true` |
| `--sonar-compat` | cognitive complexity in SonarSource-compatible mode (the mode differences are the `COG-*` ruling pairs in the [spec](spec/rulings.md)) |
| `--explain` | per-increment attribution traces on cyclomatic/cognitive |
| `--strict` | error exit on parse errors instead of measure-and-label |
| `--csv`, `-o FILE` | wide-format CSV, output file |

Every counting decision can be interrogated:

```console
$ codecaliper spec show TOK-ALL-0006
TOK-ALL-0006 — A tab counts as 8 indentation characters (arbitrated)
metric: tokenization   language: all   status: active
since spec: 1.0.0
normative cases: py-tok-normalize-001

Indentation features count leading whitespace with a tab as 8 characters and a
space as 1. Supersedes TOK-ALL-0004 (tab = 1), whose PROVISIONAL marker was
resolved by the pre-registered 32-cell BW faithfulness arbitration ...
```

And `codecaliper env` prints the installed grammar versions against the
calibrated ones; `codecaliper cite` prints a methods-section template:

```console
$ codecaliper cite
Metrics were computed with codecaliper 0.1.0.dev0 under mapping specification
1.0.0 (grammars: tree-sitter-python 0.25.0, tree-sitter-java 0.23.5);
cognitive complexity in whitepaper mode unless stated; readability vectors are
the raw Buse-Weimer 2010 feature set, with granularity and extrapolation as
labelled in the output.
```

## Python API

```python
from codecaliper import measure

report = measure(source_text, language="python")

report.parse_ok                     # False => measured anyway, labelled
report.provenance.spec_version      # "1.0.0" — on every report
for m in report.file_metrics:
    print(m.metric, m.value, m.rulings)

vec = report.readability[0]         # bw2010: the raw 25-feature vector
dict(zip(vec.names, vec.values))    # canonical order, sha-stamped
vec.extrapolated                    # True at file granularity — BW's native
                                    # unit is the snippet, and that is labelled
```

Per-function vectors and metrics:

```python
report = measure(source_text, language="python", granularity="function")
for fn in report.functions:
    print(fn.qualified_name, fn.span, fn.metrics)
```

Bare Java snippets (the Buse–Weimer dataset shape) that do not parse on their
own are retried inside a synthetic scaffold (CORE-JAVA-0001) — invisibly to
the emitted numbers, and labelled `snippet-scaffolded`; fragments that parse
as-is are measured directly, with no scaffold and no label:

```python
report = measure(java_fragment, language="java", granularity="snippet")
```

All result types are frozen dataclasses — see the [API reference](api.md).

## Reading a report honestly

Three fields matter more than the numbers:

- `parse_ok` — on parse errors codecaliper still measures, attaches
  `parse-error-recovered`, and (for BW token-family features) falls back to
  the full lexical stream under ruling `BW-ALL-0007`;
- `provenance` — quote `spec_version` + grammar versions in anything you
  publish;
- per-value `diagnostics` — e.g. every MI value carries `mi-contains-cc`,
  every Halstead value carries `halstead-approximation`. They are not
  warnings to silence; they are the instrument's honesty labels — see
  [Honesty invariants](honesty.md).
