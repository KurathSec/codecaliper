# Validation

Two generated artifacts back the faithfulness claim; both live in
`validation/bw_faithfulness/derived/` and are **included here verbatim** (the
site cannot drift from them). The dataset itself is not committed here: an
author of the dataset granted redistribution and derived-data publication by
email (2026-07-11), and the pipeline tracks only aggregates and feature vectors
by repo-focus choice.

The loop they close, in one paragraph: ambiguities in the published
Buse–Weimer feature definitions (how wide is a tab? do error fragments
count?) are not resolved by taste. Each candidate interpretation ships as a
`PROVISIONAL` ruling, a **pre-registered experiment** on the paper's original
dataset arbitrates (criteria written down before results were seen), the
winner is adopted by **superseding** the old ruling under a new immutable ID,
the spec MAJOR version is bumped, and the faithfulness reproduction below is
re-run under the adopted rulings.

---

--8<-- "validation/bw_faithfulness/derived/bw_faithfulness_report.md"

---

*Reading the two reports together:* the faithfulness report's headline AUC
(0.828, the final instrument run) and the arbitration report's adopted-cell
AUC (0.827) are the **same configuration** — they differ by one ranked pair
out of 2419 (≈ 0.0004) of feature-serialization precision, as the arbitration
report's reconciliation note details. The arbitration re-runs end-to-end from
pinned inputs (`derived/arbitration_inputs/`, see the validation README).

--8<-- "validation/bw_faithfulness/derived/arbitration_report.md"
