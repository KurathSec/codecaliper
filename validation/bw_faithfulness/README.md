# BW faithfulness reproduction (ARCHITECTURE.md §8.3 — the make-or-break)

> **Citing the dataset.** An author of the dataset asked that the work be cited
> as **both** papers, and this project honours that requested citation form:
>
> - Raymond P. L. Buse and Westley Weimer. *Learning a Metric for Code
>   Readability.* IEEE Transactions on Software Engineering 36(4):546–558, 2010.
>   [doi:10.1109/TSE.2009.70](https://doi.org/10.1109/TSE.2009.70)
> - Raymond P. L. Buse and Westley Weimer. *A Metric for Software Readability.*
>   ISSTA 2008, 121–130.
>   [doi:10.1145/1390630.1390647](https://doi.org/10.1145/1390630.1390647)

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
ignored by git, never committed; `derived/` holds the values computed by
codecaliper (feature vectors, extraction stamps/stats, training metrics, the
reports) and is tracked — it is the committable scholarly artifact. The single
exception is `derived/arbitration_inputs/scores.csv`, a pinned copy of the
per-snippet mean ratings, tracked under the author's grant so the arbitration
re-runs without a download (see below).

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
exit code 0 — absence must never fail a build.

**Licence status** (full record in `dataset.toml`): an author of the dataset
(W. Weimer) granted, by email on 2026-07-12, both redistribution of the raw data
and publication of derived results. The pipeline nonetheless keeps fetching the
snippet archive at run time and tracks only derived artifacts plus the
per-snippet mean ratings (`derived/arbitration_inputs/scores.csv`, the one input
the arbitration cannot recompute) — a repo-focus choice, no longer a licence
constraint. `dataset.toml` also records the two corpora measured by
`validation/breadth/` (Scalabrino 2018, Dorn 2012), for which **no permission has
been sought or granted**: those are fetched at run time (`fetch.py --all`) and
only aggregate results are published; not a byte of them enters this repository.

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
  stamps (spec 0.1.0);
- `scores.csv` — the per-snippet **mean human ratings**
  (`snippet_id,mean_score,n_ratings`) the matrix scores against. This is the one
  pinned input that is dataset-derived rather than codecaliper-derived, and it is
  tracked under the author's redistribution grant so the arbitration is
  re-runnable without a third-party download. `arbitrate.py` reads this tracked
  copy and falls back to `cache/scores.csv`; when both exist it asserts they are
  byte-identical (the tracked file is a *pin*, never a fork). It is the **only**
  raw-dataset content in the tracked tree, and it covers the Buse-Weimer ratings
  only — no Scalabrino or Dorn content is ever tracked.

```bash
pip install -e ".[retrain]" -c constraints/ci.txt -c constraints/retrain.txt
python validation/bw_faithfulness/fetch.py       # the raw snippets are still needed for the
                                                 # V1-V3 operator recount (cache/)
python validation/bw_faithfulness/arbitrate.py   # -> derived/arbitration_report.{json,md}
                                                 # (ratings come from the tracked pin; run
                                                 # extract.py first if you want the cache/
                                                 # fallback cross-checked as well)
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
