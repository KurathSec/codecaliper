# codecaliper mapping specification v0.1.0

> Generated from `src/codecaliper/spec/rulings/*.toml` by `tools/gen_spec_docs.py` — do not edit by hand.

## bw2010

### BW-ALL-0001 — The 25 features, canonical order, raw vector only

*language: all · status: active · since spec 0.1.0*

The feature set is the 25 features of Buse & Weimer 2010 Fig. 6, emitted in the
canonical order inherited from the reference implementation
(avg_line_length ... max_identifier_occurrences). Output is always the raw
feature vector; no scalar readability score exists anywhere in this tool
(ARCHITECTURE.md §13). Average features divide by the number of lines; max features
take the maximum.

Normative cases: `py-cc-boolop-001`

### BW-ALL-0002 — Granularity labelling and the calibrated regime

*language: all · status: active · since spec 0.1.0*

granularity is one of snippet | function | file; anything other than snippet is
extrapolation beyond the model's native unit and is labelled with
extrapolated=true plus a diagnostic. Even at snippet granularity, a diagnostic
warns when the unit falls outside the paper's 4-11 line calibrated regime.

### BW-ALL-0003 — A comment token counts once (PROVISIONAL)

*language: all · status: active · since spec 0.1.0*

avg_comments counts comment TOKENS divided by lines; a multi-line block comment
counts once (on its start line), mirroring the stdlib-tokenize reference
behaviour for line comments. PROVISIONAL: per-spanned-line counting is the
alternative; the faithfulness pipeline will arbitrate.

Normative cases: `java-block-comment-001`

### BW-ALL-0004 — Token-level features exclude string contents; character features use raw text

*language: all · status: active · since spec 0.1.0*

Punctuation/operator features (periods, commas, parentheses, arithmetic,
comparisons, assignments) count TOKENS, so punctuation inside string literals
and comments is invisible to them. Character-level features (line length,
indentation, spaces, max_char_occurrences) always use the raw normalized text
of every line, strings included.

Normative cases: `py-multiline-string-001`

### BW-ALL-0005 — Identifier-length feature is the mean of per-line maxima

*language: all · status: active · since spec 0.1.0*

avg_identifier_length = mean over all lines of (the longest identifier on that
line, 0 for lines without identifiers); max_identifier_length is the global
maximum. Faithful to the reference implementation's reading of Fig. 6
('average/maximum value per line').

### BW-ALL-0006 — Operator classes are adapter tables

*language: all · status: active · since spec 0.1.0*

Which operator spellings count as arithmetic / comparison / assignment is a
per-language adapter table, part of the spec surface. Short-circuit operators
(and/or, &&/||) are NOT in these classes: Python's are keywords (counted by
avg_keywords), Java's are uncategorized operators.

Normative cases: `py-comprehension-001`

### BW-JAVA-0001 — Java keyword set

*language: java · status: active · since spec 0.1.0*

Keywords are the JLS reserved words plus the literals true/false/null —
procedurally consistent with Python, whose kwlist includes True/False/None.

### BW-JAVA-0002 — Java branch/loop keyword features

*language: java · status: active · since spec 0.1.0*

avg_branches counts `if` keyword tokens (an else-if contributes via its `if`);
avg_loops counts for/while/do keyword tokens.

Normative cases: `java-elseif-001`

### BW-PY-0001 — Python keyword set

*language: python · status: active · since spec 0.1.0*

Keywords are keyword.kwlist of the reference CPython (True/False/None
included). Soft keywords (match/case/type/_) count as identifiers, matching the
stdlib tokenize reference.

### BW-PY-0002 — Python branch/loop keyword features

*language: python · status: active · since spec 0.1.0*

avg_branches counts if/elif keyword tokens; avg_loops counts for/while keyword
tokens (including comprehension for/if keywords, which are lexically identical
- faithful to the reference's lexical reading).

Normative cases: `py-elif-chain-001`

## cognitive

### COG-ALL-0001 — Structural increments: +1 plus the current nesting level

*language: all · status: active · since spec 0.1.0*

if / loops / catch / switch / ternary each contribute (1 + nesting level at
their position). Both modes.

Normative cases: `py-cc-boolop-001`, `java-boolop-catch-001`, `py-nested-function-001`

### COG-ALL-0002 — elif/else-if and else are hybrid increments: +1, no nesting penalty

*language: all · status: active · since spec 0.1.0*

An elif/else-if continuation and an if-attached else clause each contribute a
flat +1 regardless of nesting depth, and an elif does not deepen nesting
relative to its chain head (chain flattening — Sonar's own rule). Both modes.
In Java an `else` directly followed by an if_statement is the chain
continuation and is not additionally counted as an else. ONLY an else attached
to an if/elif chain is a hybrid increment: Python's for/while/try `else`
clauses contribute nothing (they are completion handlers, not branch arms).

Normative cases: `py-elif-chain-001`, `java-elseif-001`

### COG-ALL-0003 — Boolean operator sequences: +1 per sequence of like operators

*language: all · status: active · since spec 0.1.0*

A run of the same short-circuit operator contributes +1 total; each operator
change starts a new sequence (`a and b or c` = 2; `a && b && c` = 1).
Parentheses delimit sequences. Both modes.

Normative cases: `py-cc-boolop-001`, `java-boolop-catch-001`

### COG-ALL-0004 — What deepens nesting

*language: all · status: active · since spec 0.1.0*

Nesting increases inside: if (and its else/elif bodies), loops, catch, switch,
ternary, and function-like units that are themselves nested inside another
function (nested functions, lambdas). Nesting does NOT increase inside: try
bodies, with/synchronized blocks, class bodies, or top-level function bodies.
Both modes.

Normative cases: `py-nested-function-001`

### COG-ALL-0005 — Direct recursion counts +1 per recursive call (whitepaper mode) *(mode: whitepaper)*

*language: all · status: active · since spec 0.1.0*

Each call whose callee name equals the enclosing function's name contributes +1
(the whitepaper lists recursion as a fundamental increment). Receiver rule,
applied symmetrically across languages: bare calls count (`f(...)`), and
self-receiver calls count (Python `self.f(...)`/`cls.f(...)`, Java
`this.f(...)`); a same-named call on any other receiver does NOT count. Name
matching is a declared syntactic heuristic: it does not resolve overloads or
mutual recursion.

Normative cases: `py-recursion-001`

### COG-ALL-0006 — No recursion increment (sonar-compat mode) *(mode: sonar-compat)*

*language: all · status: active · since spec 0.1.0*

The deployed Sonar-lineage implementations (cognitive_complexity for Python,
and SonarQube's own analyzers in common configurations) do not implement the
whitepaper's recursion increment; sonar-compat mode therefore omits it.

Normative cases: `py-recursion-001`

### COG-PY-0001 — Comprehension clauses contribute no cognitive increment

*language: python · status: active · since spec 0.1.0*

Binds node types: `if_clause`, `for_in_clause`

Comprehension `for_in_clause` and `if_clause` (guard) contribute no cognitive
increment and do not deepen nesting: a comprehension reads as a single
declarative expression (consistent with SonarPython's treatment). Contrast
with cyclomatic, where the guard IS a decision point (CC-PY-0004).

Normative cases: `py-comprehension-001`

## core

### CORE-ALL-0001 — Metrics operate on pre-preprocessing source text

*language: all · status: active · since spec 0.1.0*

All measurements are functions of the source text as written, before any
preprocessing (relevant to C-family languages later; declared now, ARCHITECTURE.md §0).
A purely syntactic tool is an approximation for preprocessed languages, and this
instrument says so instead of hiding it.

### CORE-ALL-0002 — Parse-error recovery: measure, label, never fabricate

*language: all · status: active · since spec 0.1.0*

tree-sitter always returns a tree. ERROR and MISSING subtrees are classified as
opaque (not descended into for metric counting), the report carries
parse_ok=false and a parse-error-recovered diagnostic. --strict upgrades this
to an error exit. No number is silently fabricated from broken syntax.

### CORE-ALL-0003 — Nested-unit attribution

*language: all · status: active · since spec 0.1.0*

Per-function values are computed on the function's own subtree EXCLUDING nested
named function/method/constructor definitions and nested class declarations,
which receive their own FunctionReports (lambdas remain part of the enclosing
unit). File-level values are ONE whole-file walk (top-level code plus all
units), not the sum of per-function values. This is a classic radon-vs-lizard
divergence axis, ruled explicitly.

Normative cases: `py-nested-function-001`

### CORE-ALL-0004 — Float emission and determinism scope

*language: all · status: active · since spec 0.1.0*

Canonical JSON/CSV output rounds floating-point values to 12 significant digits
(round-half-even). Outputs contain no timestamps and no hash-order dependence;
byte-identical output is guaranteed PER PLATFORM (libm differences across
OS/arch may flip the last ULP of ln(); this is documented, not hidden).
Consistency-corpus float assertions always carry explicit tolerances.

### CORE-ALL-0005 — Language detection is an extension map — never a guess

*language: all · status: active · since spec 0.1.0*

--lang auto maps file extensions to adapters; an unmapped or ambiguous
extension is an explicit error. Content sniffing is out of scope for 1.0.

### CORE-JAVA-0001 — Bare-snippet scaffolding at snippet granularity

*language: java · status: active · since spec 0.1.0*

The Buse-Weimer dataset snippets are mostly statement sequences or bare
methods, not compilation units. VERIFIED (tree-sitter-java 0.23.5): the
grammar's `program` rule accepts both bare statement sequences and bare method
declarations, so BW-shaped snippets parse cleanly WITHOUT scaffolding. As a
fallback, at granularity="snippet", if the bare parse yields an error-bearing
tree, the text is re-parsed inside TWO candidate scaffolds — class-body-only
`class __CC__ { ... }` (rescues constructors and modifier-bearing members) and
`class __CC__ { void __cc__() { ... } }` — and the strict error-count
minimizer is adopted only when it beats the bare parse. All features are
computed ONLY over the original snippet's line range (scaffold lines excluded,
original indentation unshifted), scaffold-line function units are dropped, all
emitted spans and traces are rebased to original snippet coordinates, and a
snippet-scaffolded diagnostic is attached.

## cyclomatic

### CC-ALL-0001 — Base value and decision-point summation

*language: all · status: active · since spec 0.1.0*

cyclomatic = 1 + the number of decision points in the measured unit. What
counts as a decision point is pinned by the per-language rulings below.

Normative cases: `py-cc-boolop-001`, `java-elseif-001`

### CC-JAVA-0001 — if statements count +1 (else-if chains count each if)

*language: java · status: active · since spec 0.1.0*

Binds node types: `if_statement`

Each `if_statement` contributes one decision point, including an if_statement
that is the `alternative` of another (an else-if arm is a branch).

Normative cases: `java-elseif-001`

### CC-JAVA-0002 — Ternary expressions count +1

*language: java · status: active · since spec 0.1.0*

Binds node types: `ternary_expression`

Each `ternary_expression` contributes one decision point.

### CC-JAVA-0003 — Short-circuit operators count per operator

*language: java · status: active · since spec 0.1.0*

Binds node types: `binary_expression`

Each `binary_expression` whose operator is `&&` or `||` contributes one
decision point; `a && b && c` contributes 2.

Normative cases: `java-boolop-catch-001`

### CC-JAVA-0004 — Loops count +1

*language: java · status: active · since spec 0.1.0*

Binds node types: `for_statement`, `enhanced_for_statement`, `while_statement`, `do_statement`

Each `for_statement` / `enhanced_for_statement` / `while_statement` / `do_statement` contributes one decision point.

### CC-JAVA-0005 — catch clauses count +1 each

*language: java · status: active · since spec 0.1.0*

Binds node types: `catch_clause`

Each `catch_clause` contributes one decision point.

Normative cases: `java-boolop-catch-001`

### CC-JAVA-0006 — case labels count +1 each; default does not

*language: java · status: active · since spec 0.1.0*

Binds node types: `switch_label`

Each `switch_label` beginning with `case` contributes one decision point; a
`default` label does not (it is the fall-through path, like an else).

### CC-PY-0001 — if statements count +1

*language: python · status: active · since spec 0.1.0*

Binds node types: `if_statement`

Each `if_statement` contributes one decision point.

Normative cases: `py-cc-boolop-001`, `py-elif-chain-001`

### CC-PY-0002 — elif clauses count +1 each

*language: python · status: active · since spec 0.1.0*

Binds node types: `elif_clause`

Each `elif_clause` contributes one decision point (each arm is a branch).

Normative cases: `py-elif-chain-001`

### CC-PY-0003 — Boolean short-circuit operators count per operator

*language: python · status: active · since spec 0.1.0*

Binds node types: `boolean_operator`

Each `boolean_operator` node contributes one decision point. An N-operand chain
is (N-1) nested nodes, so `a and b or c` contributes 2 — each short-circuit is a
distinct execution path. Agrees with radon; diverges from tools that count a
whole chain as one.

Normative cases: `py-cc-boolop-001`

### CC-PY-0004 — Comprehension guards count +1; comprehension for-clauses do not

*language: python · status: active · since spec 0.1.0*

Binds node types: `if_clause`

Each `if_clause` inside a comprehension/generator contributes one decision
point (a guard is a branch). The `for_in_clause` itself does not (it is
iteration syntax, not a decision). A case-clause guard `if_clause` is NOT
separately counted — the guarded case_clause already counts under CC-PY-0008,
and counting both would double-count one branch. Diverges from lizard
(ignores comprehension guards).

Normative cases: `py-comprehension-001`

### CC-PY-0005 — Loops count +1

*language: python · status: active · since spec 0.1.0*

Binds node types: `for_statement`, `while_statement`

Each `for_statement` / `while_statement` contributes one decision point (async included: the async modifier does not change counting).

Normative cases: `py-nested-function-001`

### CC-PY-0006 — except clauses count +1 each

*language: python · status: active · since spec 0.1.0*

Binds node types: `except_clause`

Each `except_clause` contributes one decision point.

### CC-PY-0007 — Conditional expressions (ternaries) count +1

*language: python · status: active · since spec 0.1.0*

Binds node types: `conditional_expression`

Each `conditional_expression` contributes one decision point. Diverges from the
stdlib-ast reference lane (which does not count IfExp); the divergence is
classified.

### CC-PY-0008 — match case clauses count +1 each; the match statement and bare wildcard do not

*language: python · status: active · since spec 0.1.0*

Binds node types: `case_clause`

Each `case_clause` contributes one decision point, EXCEPT a bare-wildcard
`case _:` with no guard, which is the fall-through path and does not count —
the exact mirror of Java `default:` (CC-JAVA-0006).

## halstead

### HAL-ALL-0001 — Lexical Halstead: token-class harvesting (a declared approximation)

*language: all · status: active · since spec 0.1.0*

Operators are OPERATOR, KEYWORD, and PUNCT tokens; operands are IDENTIFIER,
NUMBER, and STRING tokens, from the unified lexical stream. n1/n2 are distinct
counts, N1/N2 total counts; V = N*log2(n); D = (n1/2)*(N2/n2); E = D*V.
Absolute Halstead values are implementation-defined across all tools — only
trends and ratios are stable — and every emitted value carries the
halstead-approximation diagnostic (ARCHITECTURE.md §13). This lexical convention is
deliberately uniform cross-language; its divergence from AST-harvest
implementations (radon, the stdlib reference lane) is classified.

Normative cases: `py-cc-boolop-001`

## loc

### LOC-ALL-0001 — Physical and blank lines

*language: all · status: active · since spec 0.1.0*

physical_lines = number of lines of the normalized text (a trailing final
newline does not create an extra empty line). blank_lines = lines whose content
strips to empty.

Normative cases: `py-multiline-string-001`

### LOC-ALL-0002 — sloc: lines covered by at least one code token

*language: all · status: active · since spec 0.1.0*

sloc counts lines covered by the span of at least one non-comment token. A
multi-line string is code: every line it spans counts. (This is where the old
regex lane provably fails — ARCHITECTURE.md §6.)

Normative cases: `py-multiline-string-001`

### LOC-ALL-0003 — comment_lines: lines covered by at least one comment token

*language: all · status: active · since spec 0.1.0*

comment_lines counts lines covered by the span of at least one comment token;
a multi-line block comment counts on EVERY line it spans. A line containing
both code and a trailing comment counts toward both sloc and comment_lines
(the two are coverage measures, not a partition).

Normative cases: `java-block-comment-001`, `py-multiline-string-001`

### LOC-ALL-0004 — lloc: statement-classified nodes

*language: all · status: active · since spec 0.1.0*

lloc counts nodes in the adapter's statement table (simple statements plus
compound-statement headers plus declarations). The table is part of the spec
surface and validated against the grammar.

Normative cases: `py-cc-boolop-001`, `java-elseif-001`

## maintainability_index

### MI-ALL-0001 — MI variant: no comment term, clamped to 0-100

*language: all · status: active · since spec 0.1.0*

MI = clamp_0_100((171 - 5.2*ln(V) - 0.23*CC - 16.2*ln(SLOC)) * 100/171), the
Visual Studio / radon convention without the comment term. MI is DERIVED from
Halstead volume, cyclomatic complexity and SLOC — it is not independent of CC
(ARCHITECTURE.md §13); every MI value carries a typed derived_from and a standing
mi-contains-cc diagnostic.

Normative cases: `py-cc-boolop-001`

## tokenization

### TOK-ALL-0001 — Input is decoded as UTF-8 with replacement

*language: all · status: active · since spec 0.1.0*

Byte input is decoded as UTF-8; undecodable bytes are replaced (U+FFFD) and an
encoding-replaced diagnostic is attached. str input is used as-is.

### TOK-ALL-0002 — A leading UTF-8 BOM is stripped

*language: all · status: active · since spec 0.1.0*

A leading U+FEFF is stripped before measurement (with a bom-stripped
diagnostic); otherwise it would pollute line-1 character and length features.

### TOK-ALL-0003 — Line endings are normalized to LF

*language: all · status: active · since spec 0.1.0*

CRLF and lone CR are normalized to LF before measurement, so character-level
features are platform-stable.

### TOK-ALL-0004 — A tab counts as one indentation character (provisional)

*language: all · status: active · since spec 0.1.0*

Indentation is measured as the count of leading whitespace characters; a tab
counts as 1. PROVISIONAL: the BW faithfulness pipeline (§6.3) will arbitrate
tab semantics empirically; any change supersedes this ruling.

### TOK-ALL-0005 — Token line attribution

*language: all · status: active · since spec 0.1.0*

Every lexical token is attributed to the physical line of its start position.
A multi-line token (string, block comment) is ONE token on its start line for
token-count features; line-coverage features (sloc, comment lines) use its full
span instead.

### TOK-JAVA-0001 — Java atomic tokens: string and character literals

*language: java · status: active · since spec 0.1.0*

Binds node types: `string_literal`, `character_literal`

`string_literal` and `character_literal` subtrees are consumed as single STRING
tokens (text blocks included).

### TOK-PY-0001 — Python atomic tokens: strings are consumed whole

*language: python · status: active · since spec 0.1.0*

Binds node types: `string`, `concatenated_string`

`string` and `concatenated_string` subtrees are consumed as single STRING
tokens. F-string interpolation contents therefore do NOT contribute token-level
features (identifiers/operators inside interpolations are invisible). This
diverges from CPython 3.12+ tokenize (PEP 701), which tokenizes interpolation
contents; the divergence vs the stdlib reference extractor is classified, and
uniformity with Java strings is preferred.
