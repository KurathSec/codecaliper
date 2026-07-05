# BW 2010 faithfulness reproduction

Reproduction of Raymond P. L. Buse and Westley Weimer, 'Learning a Metric for Code Readability', IEEE Transactions on Software Engineering 36(4):546-558, 2010, DOI 10.1109/TSE.2009.70 with codecaliper's public snippet-granularity extractor (ARCHITECTURE.md §8.3).

## Headline numbers

- **10-fold accuracy**: 0.720 (bootstrap 95% CI [0.660, 0.790]) vs the paper's ~0.80 — CI DOES NOT overlap the paper's figure
- **AUC**: 0.783
- fold accuracies: 0.90, 0.60, 0.90, 0.70, 0.70, 0.60, 0.70, 0.80, 0.60, 0.70
- convergence warnings during fitting: 0
- **sign agreement vs Fig. 9**: 20/24 agree, 4 disagree, 1 excluded (direction unclear in the paper)

## Protocol

- labels: label = 1 iff snippet mean score >= 3.14 (the paper's Figure 5 bimodal cutoff; scores below 3.14 are 'less readable') (paper Fig. 5 cutoff 3.14; 59 high / 41 low)
- classifier: LogisticRegression(max_iter=1000); CV: StratifiedKFold(n_splits=10, shuffle=True, random_state=0)
- AUC: roc_auc_score over cross_val_predict(method='decision_function') on the same folds
- **Deviation from the paper**: (1) The paper evaluated a battery of classifiers (Bayesian classifier, logistic regression, multilayer perceptron, ...) under 10-fold cross-validation; its ~0.80 accuracy summarizes that setting. This reproduction runs logistic regression ONLY (LogisticRegression(max_iter=1000), raw unscaled features). (2) The paper repeats the entire 10-fold validation 10 times over fresh random partitionings and averages across runs; this reproduction uses ONE fixed-seed partitioning (random_state=0) for byte-reproducibility (ARCHITECTURE.md section 8.3).

## Per-feature Spearman vs Fig. 9 directionality

Spearman rho of each feature against the snippet mean score; expected sign is the Fig. 9 direction of correlation with HIGH readability. A disagreement localizes a candidate divergence to a specific BW-*/TOK-* ruling — it is an empirical-arbiter input (ARCHITECTURE.md §8.3), not a failure to hide.

| feature | Spearman rho | expected sign (Fig. 9) | rel. power | agree |
|---|---:|:---:|---:|:---:|
| avg_line_length | -0.544 | - | 0.96 | yes |
| max_line_length | -0.412 | - | 0.78 | yes |
| avg_identifiers | -0.574 | - | 1.00 | yes |
| max_identifiers | -0.417 | - | 0.64 | yes |
| avg_identifier_length | -0.496 | unclear | 0.00 | excluded (unclear) |
| max_identifier_length | -0.229 | - | 0.40 | yes |
| avg_indentation | +0.001 | - | 0.55 | **NO** |
| max_indentation | -0.007 | - | 0.50 | yes |
| avg_keywords | -0.282 | - | 0.55 | yes |
| max_keywords | -0.166 | - | 0.13 | yes |
| avg_numbers | -0.113 | - | 0.23 | yes |
| max_numbers | -0.080 | - | 0.16 | yes |
| avg_comments | +0.326 | + | 0.33 | yes |
| avg_periods | -0.429 | - | 0.78 | yes |
| avg_commas | -0.413 | - | 0.45 | yes |
| avg_spaces | +0.039 | - | 0.21 | **NO** |
| avg_parentheses | -0.518 | - | 0.93 | yes |
| avg_arithmetic_ops | -0.177 | + | 0.07 | **NO** |
| avg_comparison_ops | -0.292 | - | 0.21 | yes |
| avg_assignments | -0.024 | - | 0.26 | yes |
| avg_branches | -0.207 | - | 0.20 | yes |
| avg_loops | -0.131 | - | 0.19 | yes |
| avg_blank_lines | +0.262 | + | 0.53 | yes |
| max_char_occurrences | +0.090 | - | 0.37 | **NO** |
| max_identifier_occurrences | -0.223 | - | 0.41 | yes |

## Extraction quality (reported, not tuned away)

- parse_ok 29/100 snippets, 10 scaffolded (CORE-JAVA-0001), 8 with an EMPTY token stream (all-ERROR tree; error subtrees are opaque per CORE-ALL-0002, so every token-family feature is zero while raw-line features survive). This is measured extractor behaviour on bare snippets — an arbitration input, not something to tune away.

## Dataset

- 100 snippets; 121 annotator rows in the archive vs 120 in the paper — reported as-is, never reconciled silently.
- License status UNVERIFIED (dataset.toml): data fetched for local research use only, never committed; this report contains aggregates only.

## Anti-circularity

> Anti-circularity note (stated in the paper too): ambiguity rulings are arbitrated on the same 100-snippet dataset whose reproduction accuracy we report. The reproduction is evidence of faithful operationalization of the published feature definitions — not an independent validation of BW's construct (ARCHITECTURE.md §8.3).

## Provenance

- codecaliper 0.1.0.dev0, spec 0.1.0
- grammar: tree-sitter-java 0.23.5 (ABI 14, validated=True)
- BW feature-order sha256: 8adae3992539a4eb2cf8d3b2386558612c77ad8e2e850f5bab940bbf430ad56d
