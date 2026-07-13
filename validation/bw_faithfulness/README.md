# BW faithfulness reproduction (ARCHITECTURE.md §8.3, the make-or-break)

> **Citing the dataset.** An author of the dataset asked that the work be cited
> as **both** papers, and this project honours that requested citation form
> (it is also encoded in `CITATION.cff` and in `dataset.toml`):
>
> - Raymond P. L. Buse and Westley Weimer. *Learning a Metric for Code
>   Readability.* IEEE Transactions on Software Engineering 36(4):546–558, 2010.
>   [doi:10.1109/TSE.2009.70](https://doi.org/10.1109/TSE.2009.70)
> - Raymond P. L. Buse and Westley Weimer. *A Metric for Software Readability.*
>   ISSTA 2008, 121–130.
>   [doi:10.1145/1390630.1390647](https://doi.org/10.1145/1390630.1390647)

Reproduces the original Buse–Weimer 2010 study with **this** feature extractor.
Read the 100 rated Java snippets, extract the 25 features through codecaliper's
*public API* at snippet granularity, retrain a logistic model under the paper's
protocol, then compare accuracy (paper ≈ 80%) **with a bootstrap CI**, plus a
per-feature Spearman sign-agreement table against the paper's Fig. 9
directionality.

The per-feature table is the sharp instrument. A sign disagreement localizes a
tokenization error to a specific `BW-*`/`TOK-*` ruling, which is then resolved
by the **empirical-arbiter loop**: choose the interpretation that best
reproduces the paper, freeze it as a superseding ruling, cite the experiment.

> **Anti-circularity note (stated in the paper too):** ambiguity rulings are
> arbitrated on the same 100-snippet dataset whose reproduction accuracy we
> report. The reproduction is evidence of *faithful operationalization* of the
> published feature definitions, not an independent validation of BW's
> construct (ARCHITECTURE.md §8.3).

## Run: no network, no `cache/`, no download

Every number this lane reports regenerates from **tracked pinned inputs**:

```bash
pip install -e ".[retrain]" -c constraints/ci.txt -c constraints/retrain.txt
python validation/bw_faithfulness/extract.py     # -> derived/features.csv + derived/extract_meta.json
python validation/bw_faithfulness/train.py       # -> derived/train_results.json (10-fold CV
                                                 #    logistic, fixed seed; re-runs extract if
                                                 #    its outputs are missing)
python validation/bw_faithfulness/report.py      # -> derived/bw_faithfulness_report.{json,md}
python validation/bw_faithfulness/arbitrate.py   # -> derived/arbitration_report.{json,md}
```

That is the whole reproduction. `fetch.py` is **not** a prerequisite for any of
it. It downloads the archive into `cache/` (gitignored) purely as an optional
cross-check, and `pin_inputs.py` is the provenance script that extracted the
pins from that archive in the first place.

**Input contract** (`pinned.py`): the primary source is
`derived/arbitration_inputs/`.

| pinned input | what it is |
|---|---|
| `snippets/1.jsnp … 100.jsnp` | the 100 rated Java snippets, verbatim from the archive |
| `oracle.csv` | the per-annotator score matrix (121 rows: id, cohort, 100 scores in snippet order) |
| `scores.csv` | `snippet_id,mean_score,n_ratings`, derived from `oracle.csv` and pinned because the arbitration scores against it |
| `features_fallback_on_tab1.csv`, `features_fallback_off.csv` (in `derived/`), `train_results_fallback_off.json`, `extract_meta_fallback_on_tab1.json` | the arbitration's pinned matrices and baseline record (codecaliper-derived, see below) |

The 102 raw input files (57,168 bytes) are tracked under the Buse–Weimer
author's redistribution grant, and they are the **only** dataset content in this
repository. No Scalabrino or Dorn byte is ever tracked. Two rules, enforced in
`pinned.py`:

1. **A missing tracked input is a HARD ERROR** (stderr, exit 1), never a SKIP.
   A lane that silently declines to reproduce its own headline number is the
   failure this instrument exists to expose.
2. **When `cache/DatasetBW.zip` is present it is an optional cross-check.**
   Every pin must be byte-identical to what the archive yields, and any
   difference is a hard error rather than a silent re-pin. `scores.csv` is
   additionally re-derived from the tracked `oracle.csv` on every run and
   asserted byte-identical. Re-pinning is deliberate: `pin_inputs.py --force`.

`derived/` holds the values computed by codecaliper (feature vectors, extraction
stamps and stats, training metrics, the reports). It is tracked, and it is the
committable scholarly artifact. `cache/` is gitignored and never committed.

Dataset layout (confirmed 2026-07-04, recorded in `dataset.toml`):
`snippets/1.jsnp .. snippets/100.jsnp` + `oracle.csv` with **121** annotator
rows against the paper's "120 annotators". That gap is reported as-is and never
reconciled silently.

Expected per-feature directionality lives in `fig9_signs.toml`, keyed by our
canonical feature names (`BW_FEATURE_NAMES`) and sourced from the paper's
Fig. 9 (bar colors pixel-verified against the figure legend); features whose
direction the paper never states carry `sign = "unclear"` and are excluded
from the sign-agreement gate (the excluded count is reported).

**Licence status** (prose record: `PERMISSIONS.md`; machine-readable: `dataset.toml`):
an author of the dataset (W. Weimer) granted, by email on 2026-07-11, both
redistribution of the raw data and publication of derived results. Under that
grant the raw inputs the pipeline consumes (the 100 snippets, `oracle.csv`,
`scores.csv`) are tracked under `derived/arbitration_inputs/`, which is what makes
the reproduction runnable offline from the git tree alone.
`dataset.toml` also records the two corpora measured by
`validation/breadth/` (Scalabrino 2018, Dorn 2012), for which **no permission has
been sought or granted**. Those are fetched at run time (`fetch.py --all`), only
their aggregate parse rates are published, and not a byte of them enters this
repository. `validation/breadth/` therefore always needs the network; this lane
never does.

## Reproducing the arbitration (spec 1.0.0's evidence)

`arbitrate.py` is the pre-registered 32-cell experiment
(mode × tab-width × ops-variant) whose report
(`derived/arbitration_report.{json,md}`) justified TOK-ALL-0006 and
BW-ALL-0007. Its inputs are **pinned tracked copies** under
`derived/arbitration_inputs/`. They have to be: once spec 1.0.0 adopted the
arbitrated rulings, the live `features.csv` and `train_results.json` moved on to
the post-adoption state, which the script's baseline and tab=1 integrity gates
correctly reject.

- `features_fallback_on_tab1.csv`, the fallback-on/tab=1 extraction the matrix
  consumed. Reconstructed from the spec-1.0.0 `features.csv` by recomputing the
  two indentation columns at tab=1. Indentation is a raw-line family, so this is
  exact, and the reconstruction matches `features_fallback_off.csv`'s
  indentation columns bit-for-bit.
- `train_results_fallback_off.json`, the pre-BW-ALL-0007 training record: the
  baseline-reproduction gate's reference (`git show efb6853:...`).
- `extract_meta_fallback_on_tab1.json`, the arbitration-time extraction stamps
  (spec 0.1.0).
- `snippets/{1..100}.jsnp`, `oracle.csv` and `scores.csv`, the raw dataset inputs
  (see the input contract above). The tab dimension re-derives the indentation
  columns and the ops dimension re-parses the operators **from these tracked
  snippets**, so the experiment needs no download. `arbitrate.py` cross-checks
  them against `cache/DatasetBW.zip` only when that archive happens to exist.

```bash
pip install -e ".[retrain]" -c constraints/ci.txt -c constraints/retrain.txt
python validation/bw_faithfulness/arbitrate.py   # -> derived/arbitration_report.{json,md}
```

The re-run reproduces every matrix cell, the decision trace, and the
recommendation exactly. `constraints/retrain.txt` pins the ML stack the
committed artifacts were produced under. The AUC is sensitive at the
single-ranked-pair level (~4e-4), so byte-reproducibility is scoped to that
stack as well as per platform; the reports stamp the versions used.

## Statistical gate

10-fold accuracy on n=100 carries ≈±8pp sampling noise, so the gate is not a
bare threshold. Report accuracy with a bootstrap 95% CI and require (a) the CI
to overlap the paper's ≈0.80, and (b) sign agreement on the paper's
top-weighted features. Stats use the stdlib `spearman`/`ci95_bootstrap`
descended from Spaghetti Architect `bench/grade.py` (see NOTICE).
