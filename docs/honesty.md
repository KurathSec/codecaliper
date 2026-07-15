# Honesty invariants

This page lists what codecaliper's numbers will not claim. Every invariant here
is encoded in a type or enforced by a test, so you can check the prose against
the code that implements it. ARCHITECTURE.md §13 is the authoritative record.

## There is no readability score

The bw2010 output is the raw 25-feature vector, in a canonical order whose
SHA-256 is exported as `BW_FEATURE_ORDER_SHA` and stamped into every model
artifact. codecaliper ships no trained weights at all.

The original Buse-Weimer classifier was fitted to 2010-era annotator judgments
about 100 Java snippets. Shipping its score as though it were a constant of
nature would be construct-validity theater. If you need a score, train one on
your own population (`[retrain]` extra): the vector, the granularity and the
`extrapolated` flag give you what you need to do that honestly. Model artifacts
are JSON, never pickle, and `ModelArtifact.load()` raises `SpecError` if the
artifact's feature order does not match this build's canonical order, so a
model trained under one feature layout can never quietly predict under another.

## Derived metrics say so

- **Maintainability index** always carries
  `derived_from = ("halstead.volume", "cyclomatic", "sloc")` and a standing
  `mi-contains-cc` diagnostic. MI and CC are not independent signals, and a
  study that correlates them should be able to learn that from the data
  structure itself.
- **Halstead** is a lexical approximation: operators and operands are
  classified from the token stream, not from a language-semantic analysis. Every
  Halstead value carries `halstead-approximation`. Absolute Halstead values are
  implementation-defined across the literature: only trends and ratios survive a
  change of tool, so those are the only things worth reading off them.

## Procedural consistency is not cross-language comparability

Python, Java and Go run through the same engines under the same rulings. That
makes the *procedure* consistent. It does not make the *numbers* comparable: a
Java cyclomatic 7 and a Python cyclomatic 7 are not the same quantity, because
the languages express control flow differently. Compare within-language
distributions, not raw values across languages.

## What text is measured

Metrics operate on the source as written, before any preprocessing or
build-time transformation. The only normalization is the TOK-* layer. BOM
stripping (TOK-ALL-0002) and undecodable-byte replacement (TOK-ALL-0001) each
attach a diagnostic when they fire (`bom-stripped`, `encoding-replaced`).
Line-ending normalization to LF (TOK-ALL-0003) is unconditional and attaches no
diagnostic, but when a CR was actually present the ruling is recorded in
`provenance.rulings_applied`, so the normalization is never invisible in the
output.

## Parse errors are measured, never hidden

On a parse error codecaliper measures anyway, sets `parse_ok: false` and
attaches `parse-error-recovered`. `--strict` opts into refusal instead. Two
rulings govern what the numbers then mean:

- **CORE-ALL-0002**: ERROR and MISSING subtrees are opaque to every *metric*.
  Cyclomatic, cognitive, Halstead and LOC never count fragments of unparseable
  code.
- **BW-ALL-0007**: when the recovered ERROR region actually adds tokens, the BW
  *token-family features* use the full lexical stream, ERROR regions included,
  labelled `bw-lexical-fallback` and cited in `rulings_applied`. A MISSING-only
  recovery that adds no tokens keeps the opaque stream, and at function
  granularity only units whose own span gained tokens are labelled. The BW
  construct is lexical (the original extractor never parsed at all), so
  error-opacity would misrepresent it. The pre-registered arbitration settled
  this. See [Validation](validation.md).

## Granularity is labelled, extrapolation is declared

bw2010 is calibrated on snippets, the paper's unit. A function-level or
file-level vector is an extrapolation, and the result says so:
`native_granularity: "snippet"`, `extrapolated: true`, plus a
`granularity-extrapolated` diagnostic. A snippet outside the calibrated line
range gets `snippet-out-of-calibrated-range`.

## Unvalidated grammars run, but are labelled

The spec is calibrated against exact grammar versions (packaged as
`spec/validated_grammars.toml`). A deviating installed grammar still runs;
refusing to measure would be the worse failure. But the report then carries
`grammar.validated: false` and an `unvalidated-grammar` diagnostic, so a
reviewer can spot it in the artifact without knowing what was installed on your
laptop.

## Outputs are clock-free and order-stable

No timestamps, no hash-order dependence, no environment leakage; enforced by
`test_determinism.py`. JSON keys are emitted in a fixed canonical field order,
not sorted alphabetically. Byte-identical output for identical input and
versions is a per-platform claim: floating-point and libm differences across
platforms are the documented caveat.

## The faithfulness result is not independent validation

The Buse-Weimer reproduction on [Validation](validation.md) is evidence that
codecaliper faithfully operationalizes the published feature definitions, and
evidence of nothing else. The ambiguity rulings were arbitrated on the same
100-snippet dataset whose reproduction accuracy is reported, so the result
cannot also serve as independent validation of the readability construct. The
generated report carries this anti-circularity note itself. That page is also
where the corpora-permission asymmetry is stated: one of the three corpora may
be redistributed, two may not, and the difference decides what you can rerun
without a network.

## The spec evolves loudly, never silently

If a change alters any value for any corpus case, CI stays red until the spec
MAJOR version is bumped and the change is described. Rulings are never edited
into new meanings; they are superseded by new immutable IDs, and the old text
stays, marked `superseded`.
Divergences from other tools are published and differentially tested in
[both directions](spec/divergences.md).
