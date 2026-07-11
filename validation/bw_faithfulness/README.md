# BW faithfulness reproduction (ARCHITECTURE.md §8.3 — the make-or-break)

Reproduces the original Buse–Weimer 2010 study with **this** feature extractor:
fetch the original dataset (100 Java snippets, 120 annotators), extract the 25
features via codecaliper's *public API* at snippet granularity, retrain a
logistic model under the paper's protocol, and compare accuracy (paper ≈ 80%)
**with a bootstrap CI** plus a per-feature Spearman sign-agreement table
against the paper's Fig. 9 directionality.

The per-feature table is the sharp instrument: a sign disagreement localizes a
tokenization error to a specific `BW-*`/`TOK-*` ruling, which is then resolved
by the **empirical-arbiter loop** — choose the interpretation that best
reproduces the paper, freeze it as a superseding ruling with the experiment
cited.

> **Anti-circularity note (stated in the paper too):** ambiguity rulings are
> arbitrated on the same 100-snippet dataset whose reproduction accuracy we
> report. The reproduction is evidence of *faithful operationalization* of the
> published feature definitions — not an independent validation of BW's
> construct (ARCHITECTURE.md §8.3).

## Run

```bash
pip install -e ".[retrain]" -c constraints/ci.txt -c constraints/retrain.txt
python validation/bw_faithfulness/fetch.py     # downloads to cache/ (never committed; idempotent)
python validation/bw_faithfulness/extract.py   # -> derived/features.csv + derived/extract_meta.json
                                               #    + cache/scores.csv + cache/oracle.csv
python validation/bw_faithfulness/train.py     # -> derived/train_results.json (10-fold CV
                                               #    logistic, fixed seed; re-runs extract if
                                               #    its outputs are missing)
python validation/bw_faithfulness/report.py    # -> derived/bw_faithfulness_report.{json,md}
```

Directory contract: `cache/` holds the fetched archive and anything extracted
from it — the snippets, the verbatim per-annotator matrix (`cache/oracle.csv`,
one row per annotator: id, cohort, 100 scores in snippet order 1..100) and the
per-snippet means (`cache/scores.csv`: `snippet_id,mean_score,n_ratings`) —
ignored by git, never committed; `derived/` holds only values computed by
codecaliper (feature vectors, extraction stamps/stats, training metrics, the
report) and is tracked — it is the committable scholarly artifact.

Archive layout (confirmed 2026-07-04, recorded in `dataset.toml`):
`snippets/1.jsnp .. snippets/100.jsnp` + `oracle.csv` with **121** annotator
rows vs the paper's "120 annotators" — reported as-is, never reconciled
silently.

Expected per-feature directionality lives in `fig9_signs.toml`, keyed by our
canonical feature names (`BW_FEATURE_NAMES`) and sourced from the paper's
Fig. 9 (bar colors pixel-verified against the figure legend); features whose
direction the paper never states carry `sign = "unclear"` and are excluded
from the sign-agreement gate (the excluded count is reported).

Missing dataset ⇒ each step SKIPs with a precise reason (anchor.py style) and
exit code 0 — absence must never fail a build. The **license status is
UNVERIFIED** (see dataset.toml): data is fetched for local research use only,
never redistributed; only derived feature vectors are ever committed.

## Reproducing the arbitration (spec 1.0.0's evidence)

`arbitrate.py` is the pre-registered 32-cell experiment
(mode × tab-width × ops-variant) whose report
(`derived/arbitration_report.{json,md}`) justified TOK-ALL-0006 and
BW-ALL-0007. Its inputs are **pinned tracked copies** under
`derived/arbitration_inputs/` — after spec 1.0.0 adopted the arbitrated
rulings, the live `features.csv`/`train_results.json` moved on to the
post-adoption state, which the script's baseline and tab=1 integrity gates
correctly reject:

- `features_fallback_on_tab1.csv` — the fallback-on/tab=1 extraction the
  matrix consumed (reconstructed from the spec-1.0.0 `features.csv` by
  recomputing the two indentation columns at tab=1; indentation is a raw-line
  family, so this is exact — the reconstruction matches
  `features_fallback_off.csv`'s indentation columns bit-for-bit);
- `train_results_fallback_off.json` — the pre-BW-ALL-0007 training record
  (the baseline-reproduction gate's reference; `git show efb6853:...`);
- `extract_meta_fallback_on_tab1.json` — the arbitration-time extraction
  stamps (spec 0.1.0).

```bash
pip install -e ".[retrain]" -c constraints/ci.txt -c constraints/retrain.txt
python validation/bw_faithfulness/fetch.py       # the raw snippets are still needed (cache/)
python validation/bw_faithfulness/extract.py     # produces cache/scores.csv, which the matrix
                                                 # consumes (also re-derives features.csv —
                                                 # byte-identical under the current spec)
python validation/bw_faithfulness/arbitrate.py   # -> derived/arbitration_report.{json,md}
```

The re-run reproduces every matrix cell, the decision trace, and the
recommendation exactly. `constraints/retrain.txt` pins the ML stack the
committed artifacts were produced under: the AUC is sensitive at the
single-ranked-pair level (~4e-4), so byte-reproducibility is scoped to that
stack as well as per platform (the reports stamp the versions used).

## Statistical gate

10-fold accuracy on n=100 carries ≈±8pp sampling noise, so the gate is NOT a
bare threshold: report accuracy with a bootstrap 95% CI and require (a) the CI
to overlap the paper's ≈0.80, and (b) sign agreement on the paper's
top-weighted features. Stats use the stdlib `spearman`/`ci95_bootstrap`
descended from Spaghetti Architect `bench/grade.py` (see NOTICE).
