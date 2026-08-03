# Audit: the de facto policies of two first-party readability tools

The papers' central claim is that reimplementations of the Buse-Weimer feature
set carry unreported parse and tokenization policies. This lane stops arguing
that from sensitivity alone: it recovers the two first-party tools, reads or
probes their actual policies, and records where each sits in the policy space
the faithfulness lane measures.

Nothing third party is committed (`cache/` is gitignored; none of the
artifacts states a license). `fetch.py` downloads each artifact and verifies
it against a recorded sha256. Recorded outputs: `results.txt` (runnable
probes, `run_audit.py`) and `diagnosis.txt` (`divergence_diagnosis.py`);
regenerate, never edit.

## Artifacts and provenance

| artifact | what | source | sha256 |
|---|---|---|---|
| `readability-original.jar` | the ORIGINAL Buse-Weimer CLI tool ("Readability Metric 0.2010.12", classes only, Weka bundled, trains at startup from the embedded snippets) | GitHub mirror (`roncoleman125/Pretty`), byte-identical to the Wayback Machine capture of the original arrestedcomputing.com Google-Sites download AND to a second independent mirror (`ishtiaque05/JMetricShovel`) | `a8eae863…f847` |
| `readability-applet.jar` | the original author's applet build, containing the full `.java` SOURCE of the feature detectors (`raykernel/apps/readability/detectors/`) | live author page, `web.eecs.umich.edu/~weimerw/data/readability/` (host serves an incomplete TLS chain; integrity rests on the sha256 pin) | `2532ae30…7ed1` |
| `readability.zip` | Scalabrino et al.'s tool: `rsm.jar` + `readability.classifier` | official replication page, `dibt-research.unimol.it/report/readability/files/readability.zip` (the page that also hosts the corpora `fetch.py --all` downloads) | `e556b9b0…4329` |

Invocation forms (verified): the original jar reads snippets from stdin
separated by `###` lines and prints one score per snippet; `rsm.jar File.java`
prints a TSV score; `java -cp rsm.jar
it.unimol.readability.metric.runnable.ExtractMetrics File.java` prints the
per-feature values, 25 of them prefixed `BW`.

## Source-audit findings: the original tool (from its own `.java` source)

1. **Tab policy: a tab counts as FOUR columns, in the indentation feature
   only.** `IndentDetector.leadingBlanks` adds 4 per leading tab, with the
   in-source comment `//might add more than just 1?` -- the ambiguity was
   seen by the original author and never surfaced in the paper. Every other
   feature leaves tabs unexpanded. The faithfulness arbitration's adopted
   tab width (8) and the original's (4) both sit in the sign-preserving
   class {2, 4, 8} the arbitration identified; the erased-direction cell
   (tab = 1) does not correspond to the original.
2. **The snippet path is purely lexical.** The scoring pipeline is
   `ReadabilityDetectorSuite.getDefaultSuite()` over per-line detectors; no
   parser touches a snippet. The jar does contain an Eclipse JDT `ASTParser`
   import, but only in a function-extraction utility
   (`raykernel.common.code.FunctionExtractor`) used by the whole-file modes,
   outside the suite. The original therefore never confronts the parse
   policy; every grammar-based reimplementation does.
3. **Counting semantics are character- and substring-level with no comment
   or string exclusion.** Line length is `trim().length()` (indentation
   excluded); arithmetic operators are the per-line count of the characters
   `+ * % / -` anywhere in the raw line, comments included; comparisons and
   keywords (`if`, `for`, `while`) are raw `indexOf` substring counts that
   also match inside identifiers; `avg spaces` counts the space character
   only (tabs contribute nothing, same as the instrument); max char
   occurrences counts every character including whitespace (same as the
   instrument).

## Diagnosis: the avg_arithmetic_ops sign divergence (`diagnosis.txt`)

Recomputing the arithmetic feature under the original's character semantics
on the 100 tracked snippets: Spearman **+0.10** with comments included
(matching Figure 9's positive bar) and **-0.245** with comments stripped, in
line with the instrument's token-level **-0.230** (two distinct quantities
that agree in sign and magnitude). The published positive
direction is a property of the counting semantics -- comment asterisks and
hyphens included -- not of arithmetic density. One of the three persistent
sign divergences is thereby diagnosed rather than open.

## Probe findings: rsm.jar (`results.txt`)

- **Tab policy: tabs are ignored.** On three probe variants differing only
  in leading whitespace, the BW indentation features read ZERO under tab
  indentation (`tabs=0`, `sp8=20.57`, `sp1=2.57`), and every other
  whitespace-sensitive BW feature values a tab below one column. Tab-indented
  code -- 32/100 Buse-Weimer snippets, 151/200 Scalabrino units, 108/121
  Dorn Java snippets -- reads as unindented to this tool's BW lane.
- **Fragment policy: features but no score.** On the truncated tracked
  snippet 8, ExtractMetrics emits all 25 BW features (9 zero), but the
  scoring mode returns `NaN` (the well-formed probe scores 0.989), so end to
  end the tool implements a de facto drop policy for fragments.

## Reproducing

```bash
python validation/audit/fetch.py                  # artifacts into cache/ (gitignored), sha256-verified
python validation/audit/run_audit.py              # needs a JRE (recorded under Temurin 21.0.11)
python validation/audit/divergence_diagnosis.py   # pure stdlib, tracked pins only
```

The source-audit findings are checkable by unzipping `cache/readability-applet.jar`
(`unzip readability-applet.jar '*.java'`) and reading the named classes.
