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
pip install -e ".[retrain]"
python validation/bw_faithfulness/fetch.py     # downloads to cache/ (never committed)
python validation/bw_faithfulness/extract.py   # -> derived/features.csv (public API path)
python validation/bw_faithfulness/train.py     # 10-fold CV logistic, fixed seed
python validation/bw_faithfulness/report.py    # -> derived/bw_faithfulness_report.{json,md}
```

Directory contract: `cache/` holds the fetched archive and anything extracted
from it (snippets, annotator scores) — ignored by git, never committed;
`derived/` holds only values computed by codecaliper (feature vectors, training
metrics, the report) and is tracked — it is the committable scholarly artifact.

Missing dataset ⇒ each step SKIPs with a precise reason (anchor.py style) and
exit code 0 — absence must never fail a build. The **license status is
UNVERIFIED** (see dataset.toml): data is fetched for local research use only,
never redistributed; only derived feature vectors are ever committed.

## Statistical gate

10-fold accuracy on n=100 carries ≈±8pp sampling noise, so the gate is NOT a
bare threshold: report accuracy with a bootstrap 95% CI and require (a) the CI
to overlap the paper's ≈0.80, and (b) sign agreement on the paper's
top-weighted features. Stats use the stdlib `spearman`/`ci95_bootstrap`
descended from Spaghetti Architect `bench/grade.py` (see NOTICE).
