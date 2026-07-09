# Validation

Two generated artifacts back the faithfulness claim; both live in
`validation/bw_faithfulness/derived/` and are **included here verbatim** (the
site cannot drift from them). The dataset itself is never committed — its
license is unverified, so only aggregates and feature vectors are tracked.

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

--8<-- "validation/bw_faithfulness/derived/arbitration_report.md"
