# Breadth: cross-corpus parse anatomy + cross-language demonstration

Real codecaliper measurements over three Java readability corpora and two Python
inputs. Everything here is produced by the shipped public API; nothing is
hand-constructed. The recorded output is `results.txt` (tracked), and re-running
the script must reproduce it byte for byte.

## What the corpora are, and where they come from

| corpus | archive | what it is | what we measure |
|---|---|---|---|
| Buse & Weimer (2010) | `DatasetBW.zip` | 100 Java snippets rated 1–5 by 121 annotator rows | all 100 snippets |
| Scalabrino et al. (2018) | `Dataset.zip` | 200 rated Java **methods** | all 200 snippets |
| Dorn (2012) | `DatasetDorn.zip` | multi-language corpus: 121 Java + 120 CUDA + 119 Python snippets | the **121 Java** snippets only |

Dorn's CUDA and Python snippets are deliberately excluded. Measuring them under
the Java grammar would be a category error, and it was the source of an earlier
wrong 6% / N=360 figure, since corrected.

This script measures all three corpora from the archives, which it reads from the
**gitignored** `validation/bw_faithfulness/cache/`. So `fetch.py --all`, and
therefore the network, is a prerequisite **here**, unlike the faithfulness lane,
which is self-contained and runs from tracked pins. This is a consequence of the
licence posture below: two of the three corpora may not be redistributed, so
their bytes cannot be pinned in the tree.
The archives' URLs, sha256 checksums, internal layout and per-corpus licence status
are recorded in [`../bw_faithfulness/dataset.toml`](../bw_faithfulness/dataset.toml).

## Licence posture (read this before redistributing anything)

One corpus may be redistributed; two may not. The distinction is never blurred.

- **Buse & Weimer (2010)**: an author granted, by email (2026-07-11),
  redistribution of the raw data and publication of derived results. He asked that
  the work be cited as **both** Buse & Weimer, IEEE TSE 36(4):546–558, 2010 **and**
  Buse & Weimer, ISSTA 2008:121–130; this project does so, in `CITATION.cff`, in
  `dataset.toml` and in the faithfulness README. Under that grant its raw snippets
  and annotator scores **are** tracked, in
  [`../bw_faithfulness/derived/arbitration_inputs/`](../bw_faithfulness/derived/arbitration_inputs/),
  and they are the only dataset content in this repository.
- **Scalabrino et al. (2018)** and **Dorn (2012)**: **no permission has been sought
  or granted.** Both are publicly downloadable from the authors' replication pages.
  This project only *uses* them. It fetches them at run time, measures them, and
  publishes aggregate results (the parse rates below). It does not redistribute
  them, not one byte enters the tracked tree, and it makes no claim that it may.

This directory itself tracks no corpus content: only the script, its recorded
output, and two hand-written Python demo files.

## Reproducing the cross-corpus parse anatomy

```bash
pip install -e ".[dev]" -c constraints/ci.txt
python validation/bw_faithfulness/fetch.py --all   # -> cache/ (gitignored), sha256-verified
python validation/breadth/measure_corpora.py       # prints exactly the lines in results.txt
```

For every snippet the script calls `codecaliper.api.measure(src, language="java")`
and emits one line per corpus:

- `N`, snippets measured;
- `clean`, how many parse with no ERROR node (`parse_ok=true`), with the percentage;
- `tabbed`, how many have at least one tab-indented line;
- `fail`, `N - clean`, i.e. snippets whose parse was recovered rather than clean;
- `brace_imbalance`, of those failures, how many have differing `{` and `}` counts
  (the snippet is a truncated fragment of a larger unit, not broken syntax);
- `err_med` / `err_max`, median and maximum ERROR-node count of the recovered parses.

If any archive is missing from `cache/`, the script names the missing files on
stderr, tells you to run `fetch.py --all`, and exits 1 having measured nothing.
It never exits 0 on an absent corpus: a measurement script that reports success
without measuring is the failure mode this repository is built to prevent.

Recorded output (`results.txt`):

```
Buse-Weimer    N=100 clean= 27 (27.0%) tabbed= 32 (32.0%) fail= 73 brace_imbalance= 69 err_med=1 err_max=10
Scalabrino     N=200 clean=190 (95.0%) tabbed=151 (75.5%) fail= 10 brace_imbalance=  0 err_med=2 err_max=3
Dorn           N=121 clean= 19 (15.7%) tabbed=108 (89.3%) fail=102 brace_imbalance= 76 err_med=2 err_max=6
```

These numbers are spec- and grammar-dependent: they hold for the spec version and
grammar pins of this working tree (`codecaliper env` prints both). A change that
moves them is a spec event. Re-run and update `results.txt` deliberately, never
silently.

## Cross-language demonstration (`python-demo/`)

Two tiny hand-written Python inputs, measured with the shipped CLI:

```bash
codecaliper validation/breadth/python-demo/method.py --json
codecaliper validation/breadth/python-demo/fragment.py --json
```

- `method.py`, a tab-indented Python method. `avg_indentation` is 18.0 under the
  ruled tab width of 8 (TOK-ALL-0006) versus 2.25 if a tab counted as one column:
  the same tab-semantics question the Java arbitration settled, reappearing in
  another language. cyclomatic 4, cognitive 7.
- `fragment.py`, the same code truncated mid-call. It does not parse
  (`parse_ok=false`) and is measured anyway, with diagnostics, under CORE-ALL-0002
  (error subtrees opaque) plus BW-ALL-0007 (BW token-family features over the full
  lexical stream). cyclomatic 3, cognitive 3.

Both files are original to this repository; neither contains corpus content.
