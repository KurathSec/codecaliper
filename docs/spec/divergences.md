# Known divergences from external oracles (spec v1.0.0)

> Generated from `tests/differential/divergences.toml` by
> `tools/gen_divergences.py` — do not edit by hand. The differential
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

Calibrated against the oracle versions pinned in `constraints/ci.txt`:
`radon==6.0.1`, `lizard==1.23.0`, `cognitive-complexity==1.3.0`.

## cognitive_complexity

| case | unit | metric | ours | theirs | ruling | why |
| --- | --- | --- | ---: | ---: | --- | --- |
| `py-match-001` | `dispatch` | cognitive | 1 | 0 | `COG-ALL-0001` | the cognitive_complexity package has no handler for ast.Match, so match statements contribute nothing; COG-ALL-0001 gives match one structural increment (Sonar's own spec counts match). |
| `py-match-001` | `label` | cognitive | 1 | 0 | `COG-ALL-0001` | the cognitive_complexity package has no handler for ast.Match, so match statements contribute nothing; COG-ALL-0001 gives match one structural increment (Sonar's own spec counts match). |
| `py-nested-function-001` | `outer` | cognitive | 3 | 5 | `CORE-ALL-0003` | cognitive_complexity scores a function including its nested defs (inner's `if` lands at nesting 2); CORE-ALL-0003 excludes nested named units, which get their own FunctionReports. |
| `py-recursion-001` | `fact` | cognitive | 1 | 2 | `COG-ALL-0006` | cognitive_complexity 1.3 implements the whitepaper's +1-per-recursive-call increment; our sonar-compat mode omits recursion per COG-ALL-0006 (whitepaper mode agrees with the oracle here). |
| `snippet:diff-match-in-func` | `dispatch` | cognitive | 1 | 0 | `COG-ALL-0001` | match/case is a switch-like structural increment for us (COG-ALL-0001); cognitive_complexity 1.3 has no ast.Match handling and scores the whole statement zero. |
| `snippet:diff-while-else` | `scan` | cognitive | 1 | 2 | `COG-ALL-0002` | cognitive_complexity gives a loop's `else` clause a +1 hybrid increment; COG-ALL-0002 rules only if-attached else arms count — loop/try completion clauses contribute nothing. |

## lizard

| case | unit | metric | ours | theirs | ruling | why |
| --- | --- | --- | ---: | ---: | --- | --- |
| `py-match-001` | `dispatch` | cyclomatic | 4 | 5 | `CC-PY-0004` | lizard counts a case guard's `if` token in addition to the case itself; CC-PY-0004 never double-counts a guard whose case_clause already counts under CC-PY-0008. |
| `py-match-001` | `label` | cyclomatic | 2 | 3 | `CC-PY-0008` | lizard counts every `case` token including the bare wildcard; CC-PY-0008 excludes an unguarded `case _:` as the fall-through path (mirror of Java default, CC-JAVA-0006). |
| `snippet:diff-comp-guard` | `evens` | cyclomatic | 2 | 3 | `CC-PY-0004` | lizard's token-based CCN counts the comprehension `for` keyword as a loop; CC-PY-0004 rules the iteration clause is not a decision point (only the guard counts). |
| `snippet:diff-match-in-func` | `dispatch` | cyclomatic | 3 | 4 | `CC-PY-0008` | lizard counts every `case` token including the bare wildcard arm; CC-PY-0008 rules `case _:` with no guard is the fall-through path and does not count (mirror of Java `default:`). |

## radon

| case | unit | metric | ours | theirs | ruling | why |
| --- | --- | --- | ---: | ---: | --- | --- |
| `py-match-001` | `dispatch` | cyclomatic | 4 | 3 | `CC-PY-0008` | radon never counts a wildcard case; CC-PY-0008 counts a GUARDED `case _ if p:` (only the unguarded wildcard is the fall-through path). |
| `snippet:diff-comp-guard` | `evens` | cyclomatic | 2 | 3 | `CC-PY-0004` | radon counts each comprehension generator as a decision point in addition to its guards; CC-PY-0004 counts only guard `if_clause`s, never the iteration clause. |
| `snippet:diff-while-else` | `scan` | cyclomatic | 2 | 3 | `CC-PY-0005` | radon counts a loop's `else` clause as a decision point; under CC-PY-0005 a loop contributes exactly one, and its completion `else` is not a branch. |
