# Known divergences from external oracles (spec v1.2.0)

> Generated from `tests/differential/divergences.toml` by
> `tools/gen_divergences.py`. Do not edit by hand. The differential
> lane (`tests/differential/`) keeps this list complete in both
> directions: an unclassified divergence fails CI, and so does a
> stale entry that is no longer observed (ARCHITECTURE.md §3.4).

Values are per named function; `unit` is the codecaliper qualified
name. `ours` is the codecaliper value pinned by the cited ruling;
`theirs` is the installed oracle's value. Cognitive comparisons run
codecaliper in `sonar-compat` mode. `snippet:*` inputs are defined in
`tests/test_bw_port_fidelity.py` (EXTRA_SNIPPETS) and
`tests/differential/_harness.py` (divergence-axis probes); all other
inputs are consistency-corpus cases.

Calibrated against the oracle versions pinned in `constraints/ci.txt`
and, for PMD (a JVM tool, so outside the pip closure),
`tests/differential/pmd.toml`:
`radon==6.0.1`, `lizard==1.23.0`, `cognitive-complexity==1.3.0`, `pmd==7.26.0`.

**What is witnessed, and where the witnessing runs out**
(ARCHITECTURE.md §8.2/§15). Java is witnessed by lizard (cyclomatic)
and by PMD (cyclomatic and cognitive). PMD is independent of
tree-sitter all the way down, with its own Java grammar and its own
metric visitors, so agreement with it is not two wrappers around one
parser agreeing with themselves. One gap survives: on the single axis
where the two cognitive modes differ, the recursion increment, PMD
takes the whitepaper's +1, so on `snippet:diff-java-recursion` it
witnesses *whitepaper* mode rather than the `sonar-compat` mode these
comparisons run in. Java's sonar-compat recursion behaviour therefore
has no external witness, and rests on the hand-computed corpus and the
spec alone. Go is witnessed by lizard (cyclomatic), which concurs on
every Go input, which is why no Go entry appears in the tables below;
Go cognitive has no external witness at all and rests on the
hand-computed corpus and the spec. rust-code-analysis remains staged,
not wired.

## cognitive_complexity

| case | unit | metric | ours | theirs | ruling | why |
| --- | --- | --- | ---: | ---: | --- | --- |
| `py-match-001` | `dispatch` | cognitive | 1 | 0 | `COG-ALL-0001` | the cognitive_complexity package has no handler for ast.Match, so match statements contribute nothing; COG-ALL-0001 gives match one structural increment (Sonar's own spec counts match). |
| `py-match-001` | `label` | cognitive | 1 | 0 | `COG-ALL-0001` | the cognitive_complexity package has no handler for ast.Match, so match statements contribute nothing; COG-ALL-0001 gives match one structural increment (Sonar's own spec counts match). |
| `py-nested-function-001` | `outer` | cognitive | 3 | 5 | `CORE-ALL-0003` | cognitive_complexity scores a function including its nested defs (inner's `if` lands at nesting 2); CORE-ALL-0003 excludes nested named units, which get their own FunctionReports. |
| `py-recursion-001` | `fact` | cognitive | 1 | 2 | `COG-ALL-0006` | cognitive_complexity 1.3 implements the whitepaper's +1-per-recursive-call increment; our sonar-compat mode omits recursion per COG-ALL-0006 (whitepaper mode agrees with the oracle here). |
| `snippet:diff-match-in-func` | `dispatch` | cognitive | 1 | 0 | `COG-ALL-0001` | match/case is a switch-like structural increment for us (COG-ALL-0001); cognitive_complexity 1.3 has no ast.Match handling and scores the whole statement zero. |
| `snippet:diff-while-else` | `scan` | cognitive | 1 | 2 | `COG-ALL-0002` | cognitive_complexity gives a loop's `else` clause a +1 hybrid increment; COG-ALL-0002 rules only if-attached else arms count, so loop/try completion clauses contribute nothing. |

## lizard

| case | unit | metric | ours | theirs | ruling | why |
| --- | --- | --- | ---: | ---: | --- | --- |
| `py-match-001` | `dispatch` | cyclomatic | 4 | 5 | `CC-PY-0004` | lizard counts a case guard's `if` token in addition to the case itself; CC-PY-0004 never double-counts a guard whose case_clause already counts under CC-PY-0008. |
| `py-match-001` | `label` | cyclomatic | 2 | 3 | `CC-PY-0008` | lizard counts every `case` token including the bare wildcard; CC-PY-0008 excludes an unguarded `case _:` as the fall-through path (mirror of Java default, CC-JAVA-0006). |
| `snippet:diff-comp-guard` | `evens` | cyclomatic | 2 | 3 | `CC-PY-0004` | lizard's token-based CCN counts the comprehension `for` keyword as a loop; CC-PY-0004 rules the iteration clause is not a decision point (only the guard counts). |
| `snippet:diff-match-in-func` | `dispatch` | cyclomatic | 3 | 4 | `CC-PY-0008` | lizard counts every `case` token including the bare wildcard arm; CC-PY-0008 rules `case _:` with no guard is the fall-through path and does not count (mirror of Java `default:`). |

## pmd

| case | unit | metric | ours | theirs | ruling | why |
| --- | --- | --- | ---: | ---: | --- | --- |
| `java-contextual-001` | `Point.quadrant` | cognitive | 1 | 0 | `COG-ALL-0001` | COG-ALL-0001 gives a switch its structural +1 whether it is a statement or an expression, and this record's body is a switch expression; PMD 7.26's CognitiveComplexity rule scores a switch expression zero. Measured on all four forms: PMD counts arrow-form and colon-form switch STATEMENTS (agreeing with us) and zeroes both forms of switch EXPRESSION, while its own CyclomaticComplexity rule counts all four. The gap is expression-vs-statement, and it is specific to PMD's cognitive rule. |
| `snippet:diff-java-lambda` | `L.make` | cyclomatic | 2 | 1 | `CORE-ALL-0003` | CORE-ALL-0003 keeps a lambda body inside the enclosing unit, so the lambda's `if` counts toward make. PMD's CyclomaticComplexity rule neither descends into the lambda nor reports it as a unit of its own, so that `if` is counted nowhere and the method reads as 1. Two witnesses put PMD alone here: lizard scores make 2, and PMD's OWN CognitiveComplexity rule does descend into the lambda (cognitive 2, agreeing with us), so PMD's two rules disagree with each other about lambda bodies. |
| `snippet:diff-java-recursion` | `R.fact` | cognitive | 1 | 2 | `COG-ALL-0006` | PMD implements the whitepaper's +1-per-recursive-call increment; our sonar-compat mode omits it per COG-ALL-0006, and comparisons run in sonar-compat mode. Recursion is the ONE axis on which our two cognitive modes differ, so on this row PMD witnesses our WHITEPAPER mode, which scores 2 and agrees with it exactly. Java's sonar-compat recursion behaviour therefore has no external witness. The Python oracle cognitive_complexity 1.3 takes the same side (see py-recursion-001), so both independent implementations follow the whitepaper here. |
| `snippet:diff-java-switch-expr` | `SwExpr.grade` | cognitive | 1 | 0 | `COG-ALL-0001` | The minimal probe for the same PMD gap that java-contextual-001 hits: a bare `return switch (x) { ... };` and nothing else. Ours is the switch increment of COG-ALL-0001 (+1 at nesting 0); PMD's CognitiveComplexity rule does not visit switch expressions and reports nothing, which the harness reads as 0. |

## radon

| case | unit | metric | ours | theirs | ruling | why |
| --- | --- | --- | ---: | ---: | --- | --- |
| `py-match-001` | `dispatch` | cyclomatic | 4 | 3 | `CC-PY-0008` | radon never counts a wildcard case; CC-PY-0008 counts a GUARDED `case _ if p:` (only the unguarded wildcard is the fall-through path). |
| `snippet:diff-comp-guard` | `evens` | cyclomatic | 2 | 3 | `CC-PY-0004` | radon counts each comprehension generator as a decision point in addition to its guards; CC-PY-0004 counts only guard `if_clause`s, never the iteration clause. |
| `snippet:diff-while-else` | `scan` | cyclomatic | 2 | 3 | `CC-PY-0005` | radon counts a loop's `else` clause as a decision point; under CC-PY-0005 a loop contributes exactly one, and its completion `else` is not a branch. |
