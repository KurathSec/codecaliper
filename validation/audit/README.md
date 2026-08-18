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

## The original extractor, run end to end (`original_extractor_results.txt`)

`original_extractor_rerun.py` runs the recovered original extractor over the
same 100 tracked snippets, through its own detector suite, and reports what
the tool itself computes. Three results, in increasing order of consequence.

**1. Five of the original's own 25 features never reach its classifier.**
`MaxLineValueDetector.featureName()` returns `"max " + fd.featureNames()`,
concatenating the ARRAY OBJECT instead of its first element, and
`featureNames()` calls `featureName()` again, minting a fresh array each time.
The name a max feature is stored under therefore never equals the name the
suite advertises, and `TrainableAdapter.getInstance` substitutes a
`StandardValueFeature(..., 0)` on a lookup miss. So maximum line length,
maximum identifiers, maximum keywords, maximum numbers and maximum
indentation enter every training and scoring instance as the constant zero.
The tool computes all five correctly; nothing downstream can see them.

Confirmed on the tool's own scoring path, black box: two inputs whose only
difference is the distribution of an identical number of leading tabs (so
average indentation, line lengths, space counts and character frequencies are
all unchanged, and only maximum indentation differs, 8 against 16) score
identically to the last digit, 0.8587440848350525 both, while doubling the
AVERAGE indentation instead moves the score to 0.8770732283592224.

**2. Per-feature agreement with this instrument.** Spearman correlations
between the original's values and ours run from +0.36 to +1.00 over the 100
snippets (full table in the recorded output). The lowest agreements are
exactly the features whose counting semantics the source audit above shows to
differ: `max_char_occurrences` (+0.356), `avg_arithmetic_ops` (+0.399),
`max_identifiers` (+0.554), `avg_identifier_length` (+0.574). Exact-value
agreement is high where the definitions coincide (`avg_blank_lines` 99/100,
`avg_numbers` 95/100, `avg_commas` 95/100) and low where they cannot
(`avg_parentheses` 5/100: the original counts `(` and `{`, we count `(` and
`)`; `avg_line_length` 0/100: the original trims each line first).

**3. What the original's own vectors yield under our protocol.** Feeding the
original's 25 columns to this project's reproduction protocol (logistic
regression, stratified ten-fold, seed 0) gives **23 of 24** Figure 9 sign
agreements and ten-fold accuracy **0.790**, AUC 0.788, against our 21 of 24
and 0.820. Two consequences:

- Two of this project's three residual sign divergences are ours, not the
  definition's: `avg_arithmetic_ops` and `max_char_occurrences` agree with
  Figure 9 under the original's character-level counting and disagree under
  our token-level counting.
- The third does not survive even the original: `avg_spaces` reads +0.041
  under the tool's own extractor against Figure 9's negative direction, close
  to our +0.039. That published direction is not reproducible from the
  original artifact on the original corpus.

The accuracy is the corroboration: the original's own features land at 0.790,
inside the "between 75% and 80%" band its paper reports for its best
classifiers, while our reimplementation lands slightly above it at 0.820.

## End-to-end policy-corner re-run (`policy_corner_results.txt`)

The findings above establish that tools occupy divergent policy points. This
lane's last experiment closes the remaining step: it runs a published tool end
to end on a published corpus and measures how far its **own output** moves
between two points of a policy space no publication states.

`policy_corner_rerun.py` scores the 200 rated Java methods of Scalabrino et
al.'s own dataset with `rsm.jar` under two corners that differ in one
convention and nothing else: as distributed (151 of the 200 are tab-indented)
and with every leading tab expanded to eight spaces. The code is semantically
identical under both. Both corners are wrapped in a byte-identical, unindented
class declaration, because the units are bare methods and the CLI returns NaN
without a compilation unit; the wrapper cancels out of the contrast. The
corpus is fetched at run time and never redistributed; only these aggregates
are published.

```
score changes when leading tabs are expanded to eight spaces: 174 of 200 methods
  delta score (expanded minus as-distributed): mean -0.0235, median +0.0000, min -0.4577, max +0.2057
  binary classification at cut 0.4: 21 of 200 methods change class (9 to readable, 12 to unreadable)
  binary classification at cut 0.5: 11 of 200 methods change class (4 to readable, 7 to unreadable)
  binary classification at cut 0.6: 14 of 200 methods change class (3 to readable, 11 to unreadable)
```

So the whitespace convention is not only a within-instrument sensitivity: on a
published model, on the corpus its own authors published, it moves 174 of 200
readability scores and flips the readable/unreadable verdict for 11 methods at
the conventional cut (21 and 14 at the neighbouring cuts). A study consuming
this tool's score as a variable inherits that movement, and no publication of
the tool states which convention its features assume.

## Reproducing

```bash
python validation/audit/fetch.py                  # artifacts into cache/ (gitignored), sha256-verified
python validation/audit/run_audit.py              # needs a JRE (recorded under Temurin 21.0.11)
python validation/audit/divergence_diagnosis.py   # pure stdlib, tracked pins only
python validation/bw_faithfulness/fetch.py --all # the Scalabrino corpus into its gitignored cache
python validation/audit/original_extractor_rerun.py # needs a JDK; runs the 2010 tool itself
python validation/audit/policy_corner_rerun.py   # needs a JRE; ~10 JVM launches
```

The source-audit findings are checkable by unzipping `cache/readability-applet.jar`
(`unzip readability-applet.jar '*.java'`) and reading the named classes.
