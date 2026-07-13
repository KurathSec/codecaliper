# BW arbitration experiment (A1 tab width / A2 arithmetic ops / A3 lexical fallback)

Empirical-arbiter loop, ARCHITECTURE.md §8.3. Every cell runs the exact
train.py protocol; the baseline cell reproduced the committed
pre-fallback training record (`derived/arbitration_inputs/`) exactly before
the rest of the matrix was trusted.

## Citing the original work

The experiment is scored against the Buse-Weimer dataset. An author of the
dataset asked that the work be cited as **both** papers; this project honours
that requested citation form:

- Raymond P. L. Buse and Westley Weimer, 'Learning a Metric for Code Readability', IEEE Transactions on Software Engineering 36(4):546-558, 2010, DOI 10.1109/TSE.2009.70
- Raymond P. L. Buse and Westley Weimer, 'A Metric for Software Readability', ISSTA 2008:121-130, DOI 10.1145/1390630.1390647

## Pre-registered decision rule (verbatim)

> Primary criterion: the number of sign agreements over the 24 clear-signed Fig. 9 features (fig9_signs.toml; avg_identifier_length is 'unclear' and excluded). Tie-break: AUC. A winner must hold under BOTH extraction modes to be adopted for the instrument. The lexical fallback is adopted iff it does not reduce sign agreements or AUC materially (its independent justification is construct fidelity + coverage 29/100 -> 100/100). Operationalization: within each mode the 16 (tab, ops) cells are ranked by (n_sign_agree desc, AUC desc); a candidate beats the current setting (tab=1, V0_current) iff it strictly increases n_sign_agree in at least one mode, never decreases n_sign_agree in either mode, and never decreases AUC by more than 0.01 in either mode; ties keep the current ruling. Among clearing candidates: highest summed n_sign_agree, then summed AUC, then fewer changed dimensions, smaller tab, earlier variant. 'Materially' for the fallback: at the adopted (tab, ops), fallback_on must not have fewer sign agreements than fallback_off and its AUC must not be lower by more than 0.01. No candidate clearing the bars => recorded null result, current rulings stand.

## Extraction modes

- `fallback_off`: derived/features_fallback_off.csv (pre-BW-ALL-0007 extraction, error-opaque token stream) — empty-token vectors 8/100.
- `fallback_on`: derived/arbitration_inputs/features_fallback_on_tab1.csv (extract.py with BW-ALL-0007 implemented: full lexical stream on parse errors; tab=1, spec 0.1.0) — empty-token vectors 0/100 (parse_ok 29/100, BW-ALL-0007 gives the other snippets a full lexical stream).

## Ops variants (Java operator sets)

- **V0_current**: `%` `*` `+` `-` `/`
- **V1_minimal**: `*` `+` `-` `/`
- **V2_incdec**: `%` `*` `+` `++` `-` `--` `/`
- **V3_compound**: `%` `%=` `*` `*=` `+` `+=` `-` `-=` `/` `/=`

## Matrix (n_sign_agree / AUC / accuracy)

### fallback_off

| tab \ ops | V0_current | V1_minimal | V2_incdec | V3_compound |
|---|---|---|---|---|
| tab=1 | 20/24, auc 0.7834, acc 0.720 | 20/24, auc 0.7830, acc 0.720 | 20/24, auc 0.7830, acc 0.720 | 20/24, auc 0.7830, acc 0.720 |
| tab=2 | 21/24, auc 0.7854, acc 0.720 | 21/24, auc 0.7859, acc 0.720 | 21/24, auc 0.7859, acc 0.720 | 21/24, auc 0.7859, acc 0.720 |
| tab=4 | 21/24, auc 0.7929, acc 0.770 | 21/24, auc 0.7929, acc 0.770 | 21/24, auc 0.7929, acc 0.770 | 21/24, auc 0.7929, acc 0.770 |
| tab=8 | 21/24, auc 0.7983, acc 0.770 | 21/24, auc 0.7974, acc 0.770 | 21/24, auc 0.7987, acc 0.770 | 21/24, auc 0.7979, acc 0.770 |

### fallback_on

| tab \ ops | V0_current | V1_minimal | V2_incdec | V3_compound |
|---|---|---|---|---|
| tab=1 | 20/24, auc 0.8297, acc 0.790 | 20/24, auc 0.8297, acc 0.790 | 20/24, auc 0.8305, acc 0.790 | 20/24, auc 0.8297, acc 0.790 |
| tab=2 | 21/24, auc 0.8260, acc 0.800 | 21/24, auc 0.8260, acc 0.800 | 21/24, auc 0.8251, acc 0.800 | 21/24, auc 0.8260, acc 0.800 |
| tab=4 | 21/24, auc 0.8210, acc 0.800 | 21/24, auc 0.8214, acc 0.800 | 21/24, auc 0.8210, acc 0.800 | 21/24, auc 0.8210, acc 0.800 |
| tab=8 | 21/24, auc 0.8272, acc 0.820 | 21/24, auc 0.8280, acc 0.820 | 21/24, auc 0.8272, acc 0.820 | 21/24, auc 0.8276, acc 0.820 |

### Sign disagreements per cell

| cell | disagreements |
|---|---|
| fallback_off/tab=1/V0_current | avg_indentation, avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_off/tab=1/V1_minimal | avg_indentation, avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_off/tab=1/V2_incdec | avg_indentation, avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_off/tab=1/V3_compound | avg_indentation, avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_off/tab=2/V0_current | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_off/tab=2/V1_minimal | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_off/tab=2/V2_incdec | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_off/tab=2/V3_compound | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_off/tab=4/V0_current | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_off/tab=4/V1_minimal | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_off/tab=4/V2_incdec | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_off/tab=4/V3_compound | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_off/tab=8/V0_current | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_off/tab=8/V1_minimal | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_off/tab=8/V2_incdec | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_off/tab=8/V3_compound | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_on/tab=1/V0_current | avg_indentation, avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_on/tab=1/V1_minimal | avg_indentation, avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_on/tab=1/V2_incdec | avg_indentation, avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_on/tab=1/V3_compound | avg_indentation, avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_on/tab=2/V0_current | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_on/tab=2/V1_minimal | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_on/tab=2/V2_incdec | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_on/tab=2/V3_compound | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_on/tab=4/V0_current | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_on/tab=4/V1_minimal | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_on/tab=4/V2_incdec | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_on/tab=4/V3_compound | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_on/tab=8/V0_current | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_on/tab=8/V1_minimal | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_on/tab=8/V2_incdec | avg_spaces, avg_arithmetic_ops, max_char_occurrences |
| fallback_on/tab=8/V3_compound | avg_spaces, avg_arithmetic_ops, max_char_occurrences |

## Decision (per-dimension, with disclosed deviation)

DISCLOSED DEVIATION from the pre-registered operationalization (the decision rule itself is unchanged): the joint (tab, ops) preference chain put summed AUC before parsimony, allowing a dimension with zero primary-criterion evidence to change on ~4e-4 summed-AUC noise, contradicting the rule's own 'ties keep the current ruling / a spec change requires positive evidence' clause. Dimensions were therefore evaluated marginally; the joint chain's outcome is recorded here for transparency.

- Pre-registered joint chain would pick: tab=8, V2_incdec (ops component carried by AUC noise only).
- A1 clearing tab widths (ops at V0_current): [2, 4, 8].
- A2 clearing ops variants (tab at adopted): none; max AUC spread across variants within any (mode, tab) row: 0.001240.
- A3 at the adopted setting: sign agreements on/off = 21/21, AUC on/off = 0.8272/0.7983.

## Recommendation

- **tab_width = 8**
- **ops_variant = V0_current**
- **lexical fallback (BW-ALL-0007): adopt**

A1 ADOPTED: tab=8. Every tab>=2 fixes the avg_indentation sign disagreement in BOTH extraction modes (+1 sign agreement, the primary criterion); among clearing tab widths [2, 4, 8], tab=8 is the (n_sign_agree, AUC) top cell in both modes (the pre-registered tie-break). It also moves max_indentation's Spearman rho from ~0 to clearly negative, matching Fig. 9. A2 NULL RESULT: no ops variant changes ANY Fig. 9 sign in any of the 32 cells (avg_arithmetic_ops disagrees with the paper's near-zero-power positive bar everywhere), and the AUC spread across variants within any (mode, tab) row is <= 0.00124018189334 — within noise. The current ruling stands (BW-ALL-0006, Java arithmetic_ops as-is). A3: at the adopted setting, fallback_on has 21/24 sign agreements vs 21/24 and AUC 0.827201322861 vs 0.798263745349: no material reduction, so BW-ALL-0007 is ADOPTED — its independent justification is construct fidelity (the original BW instrument was grammar-less) and coverage (empty-token vectors 8 -> 0, full token streams 29/100 -> 100/100).

## Scoping notes

- Tab dimension: only avg_indentation/max_indentation were re-derived; avg_line_length, max_line_length and avg_spaces remain raw character counts (a tab is 1 character there) — a possible future arbitration.
- Ops dimension: avg_arithmetic_ops for V1-V3 was recomputed from a DIRECT parse of the raw snippet (lex(include_error_tokens=True) for fallback_on, plain lex() for fallback_off); the instrument itself may engage the CORE-JAVA-0001 scaffold at snippet granularity. V0_current cells keep the matrix's own column (the true instrument path); the 'approximation' block reports recomputed-V0 vs that column.
- V3_compound counts compound assignments (+= -= *= /= %=) in avg_arithmetic_ops while avg_assignments (unchanged base column) still counts them too; adopting V3 in the instrument would additionally require a precedence decision in BW-ALL-0006.
- Anti-circularity (README.md): these rulings are arbitrated on the same 100-snippet dataset whose reproduction accuracy is reported; the reproduction is evidence of faithful operationalization, not an independent validation of BW's construct.
- The baseline cell (fallback_off, tab=1, V0_current) was asserted to reproduce the committed pre-fallback training record exactly (fold accuracies, CI, AUC, per-feature Spearman, sign table) before the rest of the matrix was computed.
- Reconciliation with the final instrument run: the adopted cell's AUC (fallback_on/tab=8/V0, 0.827201322861) differs from the headline AUC of the final re-extraction (derived/train_results.json, 0.827614716825 — first produced under spec 1.0.0 and byte-identical on every number when re-stamped under spec 1.1.0) by exactly one ranked pair (1/2419 = 0.000413): the matrix splices full-precision recomputed indentation values into the feature array, while the instrument's train.py consumes the canonical 12-significant-digit features.csv. The feature VALUES agree under 12-significant-digit quantization for all 100 snippets — the gap is serialization precision flipping one near-tied AUC pair, not a semantic difference; 0.828 (the final run) is the instrument's number.
