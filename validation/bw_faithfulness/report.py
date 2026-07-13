#!/usr/bin/env python3
"""Assemble derived/bw_faithfulness_report.{json,md} from train_results.json:
accuracy with bootstrap CI vs the paper's ~0.80, AUC, and the per-feature
Spearman sign-agreement table against BW Fig. 9 directionality. That table is
the sharp instrument: a sign disagreement localizes a tokenization error to a
specific BW-*/TOK-* ruling and is an EMPIRICAL-ARBITER INPUT, not a failure to
hide.

The report contains no dataset content (aggregates only), so it lives in the
tracked derived/ directory and is committed as part of the scholarly artifact.
Deterministic: sorted JSON keys, no timestamps (CORE-ALL-0004 float policy is
already applied by train.py).

A missing train_results.json is a HARD ERROR (stderr, exit 1), never a SKIP:
the lane regenerates it from the tracked pinned inputs (pinned.py) with no
network and no cache/, so absence means the pipeline was not run, not that the
data is unavailable.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

DERIVED = Path(__file__).resolve().parent / "derived"
RESULTS = DERIVED / "train_results.json"
OUT_JSON = DERIVED / "bw_faithfulness_report.json"
OUT_MD = DERIVED / "bw_faithfulness_report.md"

PAPER_ACCURACY = 0.80
CITATION = (
    "Raymond P. L. Buse and Westley Weimer, 'Learning a Metric for Code "
    "Readability', IEEE Transactions on Software Engineering 36(4):546-558, "
    "2010, DOI 10.1109/TSE.2009.70"
)
# An author of the dataset asked that the work be cited as BOTH papers
# (dataset.toml [datasets.bw2010]); every report carries both.
CITATION_ISSTA = (
    "Raymond P. L. Buse and Westley Weimer, 'A Metric for Software Readability', "
    "ISSTA 2008:121-130, DOI 10.1145/1390630.1390647"
)
CITATIONS = (CITATION, CITATION_ISSTA)
# Verbatim from README.md (anti-circularity note); keep the wording in sync.
ANTI_CIRCULARITY = (
    "Anti-circularity note (stated in the paper too): ambiguity rulings are "
    "arbitrated on the same 100-snippet dataset whose reproduction accuracy we "
    "report. The reproduction is evidence of faithful operationalization of the "
    "published feature definitions, not an independent validation of BW's "
    "construct (ARCHITECTURE.md §8.3)."
)


def _md_table(per_feature: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| feature | Spearman rho | expected sign (Fig. 9) | rel. power | agree |",
        "|---|---:|:---:|---:|:---:|",
    ]
    for row in per_feature:
        agree = row["agree"]
        mark = "excluded (unclear)" if agree is None else ("yes" if agree else "**NO**")
        lines.append(
            f"| {row['feature']} | {row['spearman_rho']:+.3f} | {row['expected_sign']} "
            f"| {row['relative_power_fig9']:.2f} | {mark} |"
        )
    return lines


def main() -> int:
    if not RESULTS.exists():
        print("ERROR: derived/train_results.json missing. Run train.py first "
              "(it regenerates from the tracked pinned inputs; see README.md).",
              file=sys.stderr)
        return 1

    tr = json.loads(RESULTS.read_text(encoding="utf-8"))
    res = tr["results"]
    sign = tr["sign_agreement"]
    extraction = tr.get("extraction", {})
    ci = res["accuracy_ci95_bootstrap"]
    ci_overlaps = ci[0] <= PAPER_ACCURACY <= ci[1]

    report = {
        "title": "BW 2010 faithfulness reproduction (ARCHITECTURE.md §8.3)",
        "paper": {
            "citation": CITATION,
            "citations_requested_by_author": list(CITATIONS),
            "reference_accuracy": PAPER_ACCURACY,
        },
        "gate": {
            "rule": (
                "bootstrap 95% CI of the 10-fold accuracy must overlap the paper's "
                "~0.80, plus sign agreement on the paper's top-weighted features "
                "(a bare threshold on n=100 can pass or fail by chance)"
            ),
            "ci_overlaps_paper_accuracy": ci_overlaps,
            "sign_disagreements": sign["disagreements"],
        },
        "results": res,
        "sign_agreement": sign,
        "per_feature": tr["per_feature"],
        "labels": tr["labels"],
        "protocol": tr["protocol"],
        "dataset": tr["dataset"],
        "stamps": {
            "tool_version": extraction.get("tool_version"),
            "spec_version": extraction.get("spec_version"),
            "grammar": extraction.get("grammar"),
            "feature_order_sha256": extraction.get("feature_order_sha256"),
        },
        "notes": {
            "anti_circularity": ANTI_CIRCULARITY,
            "annotator_count": tr["dataset"]["annotator_count_note"],
            "deviation_from_paper": tr["protocol"]["deviation_from_paper"],
            "extraction_quality": (
                f"parse_ok {extraction.get('parse_ok_count')}/{extraction.get('n_snippets')} "
                f"snippets, {extraction.get('scaffolded_count')} scaffolded "
                f"(CORE-JAVA-0001), {extraction.get('empty_token_vector_count')} with an "
                "EMPTY token vector. On parse errors BW token-family features are "
                "computed over the full lexical stream, ERROR subtrees included "
                "(BW-ALL-0007, bw-lexical-fallback diagnostic), which is why this "
                "count is zero; metrics remain error-opaque per CORE-ALL-0002. "
                "This is measured extractor behaviour on bare snippets, an "
                "arbitration outcome (see arbitration_report.md), never tuned away."
            ),
            "sign_disagreements_are_arbitration_inputs": (
                "each sign disagreement localizes a candidate tokenization/feature "
                "divergence to a specific BW-*/TOK-* ruling; resolution goes through "
                "the empirical-arbiter loop (supersede with a new ruling ID, "
                "experiment cited), never through silent refitting"
            ),
        },
    }
    OUT_JSON.write_text(
        json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    grammar = extraction.get("grammar") or {}
    fold_accs = ", ".join(f"{a:.2f}" for a in res["fold_accuracies"])
    md: list[str] = [
        "# BW 2010 faithfulness reproduction",
        "",
        "Reproduction of the Buse-Weimer readability study with codecaliper's public "
        "snippet-granularity extractor (ARCHITECTURE.md §8.3).",
        "",
        "## Citing the original work",
        "",
        "An author of the dataset asked that the work be cited as **both** papers; "
        "this project honours that requested citation form:",
        "",
        *(f"- {c}" for c in CITATIONS),
        "",
        "## Headline numbers",
        "",
        f"- **10-fold accuracy**: {res['accuracy_mean']:.3f} "
        f"(bootstrap 95% CI [{ci[0]:.3f}, {ci[1]:.3f}]) vs the paper's ~{PAPER_ACCURACY:.2f}; "
        f"CI {'OVERLAPS' if ci_overlaps else 'DOES NOT overlap'} the paper's figure",
        f"- **AUC**: {res['auc']:.3f}",
        f"- fold accuracies: {fold_accs}",
        f"- convergence warnings during fitting: {res['convergence_warnings']}",
        f"- **sign agreement vs Fig. 9**: {sign['n_agree']}/{sign['n_evaluated']} agree, "
        f"{sign['n_disagree']} disagree, {sign['n_excluded_unclear']} excluded "
        "(direction unclear in the paper)",
        "",
        "## Protocol",
        "",
        f"- labels: {tr['labels']['rule']} "
        f"(paper Fig. 5 cutoff {tr['labels']['threshold_paper_fig5']:.2f}; "
        f"{tr['labels']['n_high']} high / {tr['labels']['n_low']} low)",
        f"- classifier: {tr['protocol']['classifier']}; CV: {tr['protocol']['cv']}",
        f"- AUC: {tr['protocol']['auc_method']}",
        f"- **Deviation from the paper**: {tr['protocol']['deviation_from_paper']}",
        "",
        "## Per-feature Spearman vs Fig. 9 directionality",
        "",
        "Spearman rho of each feature against the snippet mean score; expected sign "
        "is the Fig. 9 direction of correlation with HIGH readability. A disagreement "
        "localizes a candidate divergence to a specific BW-*/TOK-* ruling. It is an "
        "empirical-arbiter input (ARCHITECTURE.md §8.3), not a failure to hide.",
        "",
        *_md_table(tr["per_feature"]),
        "",
        "## Extraction quality (reported, not tuned away)",
        "",
        f"- {report['notes']['extraction_quality']}",
        "",
        "## Dataset",
        "",
        f"- {tr['dataset']['n_snippets']} snippets; "
        f"{tr['dataset']['n_annotators_in_archive']} annotator rows in the archive vs "
        f"{tr['dataset']['n_annotators_in_paper']} in the paper, "
        "reported as-is, never reconciled silently.",
        "- Permission (a grant, not a licence): an author of the dataset (W. Weimer) "
        "granted redistribution and derived-data publication by email 2026-07-11 "
        "(PERMISSIONS.md, dataset.toml). Under that grant the repository tracks the raw "
        "inputs this lane consumes: the 100 snippets, the per-annotator score matrix "
        "(oracle.csv) and the per-snippet mean ratings (scores.csv), all under "
        "derived/arbitration_inputs/. Every number reported here therefore regenerates "
        "from pinned tracked inputs with no network and no cache/. Re-downloading the "
        "archive is an optional byte-for-byte cross-check, never a prerequisite. This "
        "grant covers the Buse-Weimer corpus alone; the other readability corpora this "
        "project measures carry no permission and are never redistributed.",
        "",
        "## Anti-circularity",
        "",
        f"> {ANTI_CIRCULARITY}",
        "",
        "## Provenance",
        "",
        f"- codecaliper {extraction.get('tool_version')}, "
        f"spec {extraction.get('spec_version')}",
        f"- grammar: {grammar.get('package')} {grammar.get('version')} "
        f"(ABI {grammar.get('abi_version')}, validated={grammar.get('validated')})",
        f"- BW feature-order sha256: {extraction.get('feature_order_sha256')}",
        "",
    ]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
