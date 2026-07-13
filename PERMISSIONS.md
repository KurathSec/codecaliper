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

**What this repository actually ships under it.** One file:
`validation/bw_faithfulness/derived/arbitration_inputs/scores.csv`, the 100 per-snippet mean
ratings that the pre-registered arbitration consumes, tracked so that the arbitration re-runs
from a pinned input rather than a third-party download. The snippet archive itself is still
fetched at run time into the gitignored `cache/`. That is a repository-focus choice, not a
licence constraint: the grant would permit shipping it.

**Why the original is not in this repository.** It is a third party's private e-mail. The
sha256 above binds this public record to the retained original: anyone who receives the `.eml`
can confirm it is the message this record describes, and its DKIM signature can be verified
against `umich.edu` independently of anything asserted here. The original is available on
request.

## Scalabrino et al. (2018), 200 Java methods: NO permission sought

## Dorn (2012), 121 Java snippets: NO permission sought

Neither corpus publishes an explicit data licence, and no permission has been sought or
granted for either. Both are publicly downloadable from their authors' replication page
(`dibt-research.unimol.it/report/readability`), and this project treats them accordingly:

- fetched at run time into the gitignored `cache/`, never committed, never redistributed;
- only aggregate and derived results are published, specifically the cross-corpus parse rates
  recorded in [`validation/breadth/results.txt`](validation/breadth/results.txt);
- nothing here should be read as a claim that either corpus may be redistributed.

Their citations:

- Simone Scalabrino, Mario Linares-Vasquez, Rocco Oliveto and Denys Poshyvanyk. A
  comprehensive model for code readability. *Journal of Software: Evolution and Process*
  30(6):e1958, 2018. [10.1002/smr.1958](https://doi.org/10.1002/smr.1958)
- Jonathan Dorn. A General Software Readability Model. MSc thesis, University of Virginia,
  2012.
