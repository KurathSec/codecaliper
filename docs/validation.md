# Validation

Two generated reports back the faithfulness claim. Both live in
`validation/bw_faithfulness/derived/` and are included on this page verbatim,
by transclusion, so the site cannot drift from the artifacts it describes.

## What reruns offline, and what does not

**The Buse-Weimer lane is self-contained.** Its raw inputs are tracked in
[`validation/bw_faithfulness/derived/arbitration_inputs/`](https://github.com/KurathSec/codecaliper/tree/main/validation/bw_faithfulness/derived/arbitration_inputs):
the 100 rated Java snippets, `oracle.csv` (the raw 121-row annotator matrix),
and `scores.csv` (the per-snippet means derived from it). `extract.py`,
`train.py`, `arbitrate.py` and `report.py` read those pins as their primary
source, so with no network and no `cache/` directory they regenerate every
number quoted below. A missing tracked input is a hard error and exit 1; there
is no skip-and-pass path anywhere in the lane. When the original archive happens
to be present in the gitignored `cache/`, the scripts cross-check every pin
against it byte for byte, and any difference is a hard error rather than a
silent re-pin. `pinned.py` is the input contract; `fetch.py` is not on this
lane's path at all.

Those inputs can be tracked because an author of the dataset gave written
permission to redistribute the snippets and annotator scores and to publish
data derived from them. What was asked, what was answered, and how the message
can be checked are in
[`PERMISSIONS.md`](https://github.com/KurathSec/codecaliper/blob/main/PERMISSIONS.md).

**The cross-corpus lane is not self-contained and never will be.** The
Scalabrino et al. (2018) and Dorn (2012) corpora carry no permission of any
kind, so not one byte of either is tracked, now or later. They are fetched at run
time into the gitignored `cache/`, measured there, and only aggregates are
published. Reproducing
[`validation/breadth/`](https://github.com/KurathSec/codecaliper/tree/main/validation/breadth)
therefore needs a network fetch (`fetch.py --all`), even though the Buse-Weimer
lane never does. Nothing on this page should be read as "the whole project
regenerates from the git tree alone".

## The arbitration loop

Ambiguities in the published Buse-Weimer feature definitions (how wide is a tab?
do error fragments count?) are not resolved by taste. Each candidate
interpretation ships as a `PROVISIONAL` ruling. A pre-registered experiment on
the paper's original dataset arbitrates it, with the decision criteria written
down before any result was seen. The winner is adopted by *superseding* the old
ruling under a new immutable ID, the spec MAJOR version is bumped, and the
faithfulness reproduction is re-run under the adopted rulings. Both reports
below are the output of that loop.

To rerun it:

```bash
pip install -e ".[retrain]" -c constraints/ci.txt -c constraints/retrain.txt
python validation/bw_faithfulness/extract.py     # -> derived/features.csv
python validation/bw_faithfulness/train.py       # -> derived/train_results.json
python validation/bw_faithfulness/report.py      # -> derived/bw_faithfulness_report.{json,md}
python validation/bw_faithfulness/arbitrate.py   # -> derived/arbitration_report.{json,md}
```

---

--8<-- "validation/bw_faithfulness/derived/bw_faithfulness_report.md"

---

*Reading the two reports together:* the faithfulness report's headline AUC
(0.828, the final instrument run) and the arbitration report's adopted-cell AUC
(0.827) are the same configuration. They differ by one ranked pair out of 2419
(about 0.0004), a matter of feature-serialization precision, as the arbitration
report's reconciliation note details. 0.828 is the instrument's number.

--8<-- "validation/bw_faithfulness/derived/arbitration_report.md"

---

## Cross-corpus parse anatomy

The breadth lane measures three Java corpora with the shipped public API and
reports what the parser met. It is the reason the BW lane is careful about
error recovery: most snippets in the readability corpora are truncated
fragments of larger units, not broken code.

| corpus | N | clean parse | at least one tab | recovered | of those, brace-imbalanced |
|---|---|---|---|---|---|
| Buse-Weimer (2010) | 100 | 27 (27.0%) | 32 | 73 | 69 |
| Scalabrino et al. (2018) | 200 | 190 (95.0%) | 151 | 10 | 0 |
| Dorn (2012), Java only | 121 | 19 (15.7%) | 108 | 102 | 76 |

These aggregates are spec- and grammar-dependent: they hold for the versions
`codecaliper env` prints in this tree, and a change that moves them is a spec
event. Reproducing them needs the archives, hence a network fetch. See
[`validation/breadth/README.md`](https://github.com/KurathSec/codecaliper/blob/main/validation/breadth/README.md).

### Why this page says 73 and the Quickstart says 71

Both counts are of the same 100 Buse-Weimer snippets under the same grammar, and
they differ because the two lanes measure at different granularities.

The breadth lane calls `measure(src, language="java")` and takes the default
`granularity="file"`. The CORE-JAVA-0001 snippet scaffold is gated on
`granularity == "snippet"` (`api._measure`), so at file granularity it cannot
fire: a snippet either parses as a bare `program` or it does not. 27 do, 73 are
recovered, and that is the row above.

The faithfulness lane calls `measure(src, language="java",
granularity="snippet")` (`validation/bw_faithfulness/extract.py`), where the
scaffold does fire. It is adopted on 10 of the 100 snippets, and on 2 of those 10
the scaffolded parse is clean. So 29 snippets reach `parse_ok: true` and 71 keep
`parse_ok: false`, which is the number the
[Quickstart](quickstart.md#python-api) breaks down. The two-snippet gap between
the pages is the scaffold, and nothing else.
