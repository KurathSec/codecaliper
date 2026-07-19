# Permissions

This project measures three third-party readability corpora. None of them ships with an
explicit data licence, so their terms differ and are recorded here. The machine-readable
form of the same facts, which `fetch.py` enforces, is
[`validation/bw_faithfulness/dataset.toml`](validation/bw_faithfulness/dataset.toml).

The short version: the Buse-Weimer corpus may be redistributed and derived from, because an
author of it said so. The Scalabrino and Dorn corpora may not, because nobody has asked.

## Buse-Weimer (2010), 100 Java snippets: redistribution and derived publication GRANTED

Granted by **Westley Weimer** (University of Michigan), an author of the dataset and of both
papers below, by e-mail in reply to a licence inquiry.

| | |
|---|---|
| Sender | Westley Weimer, `umich.edu` |
| Message date | `Sat, 11 Jul 2026 13:25:42 -0400` (the message's own `Date:` header) |
| Message-ID | `<CALR632iRxDUAnk-bdV3RWrr_3H6Z7_XKDxuYsWGSVzVYMe0J6A@mail.gmail.com>` |
| Authentication | `dkim=pass header.i=@umich.edu`, `spf=pass`, `arc=pass` |
| Original retained | `.eml` with full headers, sha256 below, held by the maintainer |
| sha256 of the original | `20f0a900bcceca58f5138193b1649a6cd7bb5edb83c6cb6e5d832150850c8896` |

**What was asked, and what was answered.** The inquiry asked three questions; the reply
answered each one:

1. *May I redistribute the raw snippets and the annotator scores as part of an archived
   research artifact?* **Yes.**
2. *May I publish data derived from the snippets, such as per-snippet feature vectors and
   aggregate statistics?* **Yes.**
3. *How would you like the dataset and the original work cited?* He asked, if possible, for
   **both** of these papers to be cited:
   - Raymond P. L. Buse and Westley Weimer. Learning a Metric for Code Readability.
     *IEEE Transactions on Software Engineering* 36(4):546-558, 2010.
     [10.1109/TSE.2009.70](https://doi.org/10.1109/TSE.2009.70)
   - Raymond P. L. Buse and Westley Weimer. A Metric for Software Readability.
     *ISSTA* 2008:121-130.
     [10.1145/1390630.1390647](https://doi.org/10.1145/1390630.1390647)

This project honours that requested citation form: both papers are cited wherever the corpus
is used, in this file, in `NOTICE`, in `dataset.toml`, in the generated reports under
`validation/bw_faithfulness/derived/`, and in the papers that report the reproduction.

**What the grant is, and is not.** It is a permission, not a licence: no licence text was
issued, and the citation request is a request, not a condition. It covers the original
Buse-Weimer data only.

**What this repository actually ships under it.** Every raw input the Buse-Weimer lane consumes,
tracked under `validation/bw_faithfulness/derived/arbitration_inputs/`:

| tracked path | what it is | size |
|---|---|---|
| `snippets/1.jsnp` … `snippets/100.jsnp` | the 100 rated Java snippets, byte-for-byte as they appear in `DatasetBW.zip` | 27,898 B |
| `oracle.csv` | the raw per-annotator score matrix (121 rows: id, cohort, 100 scores) | 27,162 B |
| `scores.csv` | the 100 per-snippet mean ratings, re-derived from `oracle.csv` | 2,108 B |

That is 102 files and 57,168 bytes, and it is the **only** dataset content in the tracked tree. It
is tracked because the grant permits it and because tracking it removes the download from the
reproduction path: the faithfulness reproduction and the pre-registered arbitration both re-run from
the git tree alone, offline, with no `cache/`, so neither can be broken by a dead URL or a silently
re-uploaded archive. Re-fetching `DatasetBW.zip` is an optional byte-for-byte cross-check of the
pins, never a prerequisite.

Derived material is published alongside them under `validation/bw_faithfulness/derived/`:
per-snippet feature vectors, training and arbitration results, and the generated reports. That is
covered by the second answer of the grant.

**Why the original is not in this repository.** It is a third party's private e-mail. The
sha256 above binds this public record to the retained original: anyone who receives the `.eml`
can confirm it is the message this record describes, and its DKIM signature can be verified
against `umich.edu` independently of anything asserted here. The original is available on
request.

## Scalabrino et al. (2018) and Dorn (2012): NO permission sought

Two further corpora are measured by `validation/breadth/`: the Scalabrino et al. 200 Java methods
and the Dorn 121 Java snippets. Neither publishes an explicit data licence, and no permission has
been sought or granted for either. Both are publicly downloadable from the Scalabrino et al. replication
page (`dibt-research.unimol.it/report/readability`, which republishes Dorn's data alongside its
own), and this project treats them accordingly:

- fetched at run time into the gitignored `cache/`, never committed, never redistributed. Not one
  byte of either corpus enters the tracked tree;
- only aggregate and derived results are published, specifically the cross-corpus parse rates
  recorded in [`validation/breadth/results.txt`](validation/breadth/results.txt);
- nothing here should be read as a claim that either corpus may be redistributed.

That is why `validation/breadth/` needs a network fetch and always will, while the Buse-Weimer lane
does not. Any prose implying that this project as a whole reproduces offline is wrong.

Their citations:

- Simone Scalabrino, Mario Linares-Vasquez, Rocco Oliveto and Denys Poshyvanyk. A
  comprehensive model for code readability. *Journal of Software: Evolution and Process*
  30(6):e1958, 2018. [10.1002/smr.1958](https://doi.org/10.1002/smr.1958)
- Jonathan Dorn. A General Software Readability Model. MSc thesis, University of Virginia,
  2012.
