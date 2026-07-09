# Honesty invariants

codecaliper's design bets that a measurement tool earns trust by what it
*refuses to claim*. These invariants are encoded in types and enforced by
tests — they are not documentation aspirations (ARCHITECTURE.md §13 is the
authoritative record).

## There is no readability score

The bw2010 output is the **raw 25-feature vector**, in a canonical order
whose SHA-256 is stamped into model artifacts. The original Buse–Weimer
classifier was trained on 2010-era annotator data; shipping its score as if
it were a universal constant would be construct-validity theater. If you need
a score, retrain on your own population (`[retrain]` extra) — the vector, the
granularity, and the `extrapolated` flag give you everything needed to do
that honestly.

## Derived metrics say so

- **Maintainability index** always carries
  `derived_from = ("halstead.volume", "cyclomatic", "sloc")` and a standing
  `mi-contains-cc` diagnostic: MI and CC are **not** independent signals, and
  a paper that correlates them should know that from the data structure
  itself.
- **Halstead** is a **lexical approximation** (operator/operand
  classification from the token stream, not a language-semantic analysis) and
  every Halstead value carries `halstead-approximation`. Its absolute values
  are implementation-defined across the literature — only trends and ratios
  are stable, and that is all they should be used for.

## Procedural consistency is not cross-language comparability

Python and Java are measured by the same engines under the same rulings —
that makes the *procedure* consistent, not the *numbers* comparable: a Java
cyclomatic 7 and a Python cyclomatic 7 are not the same quantity, because the
languages express control flow differently. Cross-language claims should
compare within-language distributions, not raw values.

## What text is measured

Metrics operate on the source text as written — before any preprocessing or
build-time transformation. The only normalization applied is the TOK-*
layer: BOM stripping and undecodable-byte replacement each attach a
diagnostic when they fire (`bom-stripped`, `encoding-replaced`);
line-ending normalization to LF (TOK-ALL-0003) is unconditional and silent.

## Parse errors are measured, never hidden

On a parse error codecaliper measures anyway, sets `parse_ok = false`, and
attaches `parse-error-recovered` (`--strict` opts into refusal). Two rulings
govern what the numbers then mean:

- **CORE-ALL-0002** — ERROR/MISSING subtrees are opaque to every *metric*:
  cyclomatic, cognitive, Halstead, LOC never count fragments of unparseable
  code.
- **BW-ALL-0007** — BW **token-family features** instead use the full
  lexical stream, ERROR regions included, labelled `bw-lexical-fallback`.
  The BW construct is lexical (the original extractor never parsed), so
  error-opacity would misrepresent it — this was adopted by the
  pre-registered arbitration, not by taste (see [Validation](validation.md)).

## Granularity is labelled, extrapolation is declared

bw2010 is calibrated on snippets (the paper's unit). A function- or
file-level vector is an **extrapolation** and its result says so:
`native_granularity: "snippet"`, `extrapolated: true`, plus a
`granularity-extrapolated` diagnostic. Snippets far outside the calibrated
line range get `snippet-out-of-calibrated-range`.

## Unvalidated grammars run, but are labelled

The spec is calibrated against exact grammar versions (the packaged
`src/codecaliper/spec/validated_grammars.toml`). A deviating installed grammar still runs —
refusing would be worse — but every report carries
`grammar.validated: false` plus an `unvalidated-grammar` diagnostic, so a
reviewer can spot it in the artifact.

## Outputs are clock-free and order-stable

No timestamps, no hash-order dependence, no environment leakage — enforced by
`test_determinism.py`. Byte-identical output for identical input and versions
is a **per-platform** claim (floating-point/libm differences across platforms
are the documented caveat); that is what makes "as labelled in the output" a
checkable claim rather than a promise.

## The faithfulness result is not independent validation

The Buse–Weimer reproduction on [Validation](validation.md) is evidence that
codecaliper *faithfully operationalizes the published feature definitions* —
nothing more. The ambiguity rulings were arbitrated on the same 100-snippet
dataset whose reproduction accuracy is reported, so the result cannot also
serve as independent validation of the readability construct; the report
carries this anti-circularity note itself.

## The spec evolves loudly, never silently

If any change alters any value for any corpus case, CI is red until the spec
MAJOR version is bumped and the change is described — the spec-drift gate
makes silent recalibration mechanically impossible. Rulings are never edited
into new meanings; they are superseded by new immutable IDs (the old text
stays, marked `superseded`). Known divergences from other tools are published
and differentially tested in [both directions](spec/divergences.md).
