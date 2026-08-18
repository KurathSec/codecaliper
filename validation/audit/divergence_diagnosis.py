#!/usr/bin/env python3
"""Diagnose the avg_arithmetic_ops sign divergence with the original's own
counting semantics.

The instrument counts arithmetic OPERATOR TOKENS (BW-ALL-0006) and measures
Spearman -0.2297 against the human scores, disagreeing with Figure 9's
positive bar. The original tool's source (the applet jar's
CharCountDetector, wired as AvgLineValueDetector(CharCountDetector('+', '*',
'%', '/', '-'))) counts those five CHARACTERS per raw line, comments and
strings included, and averages over lines. This probe recomputes the feature
under exactly that character semantics on the 100 TRACKED snippets and
reports its Spearman correlation with the tracked mean scores, plus a
decomposition: the same character count restricted to comment-free text
(approximated by stripping // and /* */ regions lexically).

If the character-semantics correlation is positive, the published positive
direction is a property of the counting semantics (comment asterisks and
hyphens included), not of arithmetic density, and the divergence is
diagnosed rather than open. Pure stdlib, tracked inputs only.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BW = HERE.parent / "bw_faithfulness"
sys.path.insert(0, str(BW))

import stats  # noqa: E402

AI = BW / "derived" / "arbitration_inputs"
CHARS = "+*%/-"


def strip_comments(src: str) -> str:
    """Lexical comment strip: remove // to end of line and /* */ regions
    (string literals are not protected; good enough for a decomposition)."""
    src = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)),
                 src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


def avg_char_count(src: str) -> float:
    lines = src.splitlines() or [""]
    return sum(sum(1 for ch in ln if ch in CHARS) for ln in lines) / len(lines)


def main() -> int:
    snippets_dir = AI / "snippets"
    if not snippets_dir.is_dir():
        print(f"ERROR: tracked input {snippets_dir} is missing.", file=sys.stderr)
        return 1
    with (AI / "scores.csv").open(newline="", encoding="utf-8") as f:
        recorded = {int(r["snippet_id"]): float(r["mean_score"])
                    for r in csv.DictReader(f)}
    ids = sorted(recorded)
    means = [recorded[i] for i in ids]
    srcs = {i: (snippets_dir / f"{i}.jsnp").read_text(encoding="utf-8") for i in ids}

    raw = [avg_char_count(srcs[i]) for i in ids]
    nocomment = [avg_char_count(strip_comments(srcs[i])) for i in ids]
    rho_raw = stats.spearman(raw, means)
    rho_nc = stats.spearman(nocomment, means)
    print("avg arithmetic feature, original character semantics "
          f"(chars {CHARS!r} per raw line, comments included): "
          f"Spearman {rho_raw:+.4f}")
    print("same count with comments stripped:                    "
          f"Spearman {rho_nc:+.4f}")
    print("instrument, operator-token semantics (BW-ALL-0006):   "
          "Spearman -0.2297 (derived/train_results.json, avg_arithmetic_ops)")

    # The second feature the original wins is NOT on the comment/string axis.
    # Both implementations count characters over raw text; the original's
    # CharCounter.count(String) skips ' ' and '\t' before tallying
    # (raykernel/util/CharCounter.java in the applet build, called from
    # MaxOccurencesOfSingleChar.runDetector), and BW-ALL-0004 does not. On most
    # snippets the most frequent character IS a space, so the two features are
    # measuring different quantities.
    def max_char(src: str, skip_ws: bool) -> float:
        freq: dict[str, int] = {}
        for line in src.splitlines():
            for ch in line:
                if skip_ws and ch in (" ", "\t"):
                    continue
                freq[ch] = freq.get(ch, 0) + 1
        return float(max(freq.values())) if freq else 0.0

    ours = [max_char(srcs[i], skip_ws=False) for i in ids]
    theirs = [max_char(srcs[i], skip_ws=True) for i in ids]
    rho_ours = stats.spearman(ours, means)
    rho_theirs = stats.spearman(theirs, means)
    exact = sum(1 for a, b in zip(ours, theirs, strict=True) if a == b)
    print("max char occurrences, instrument rule (every character, "
          f"BW-ALL-0004):   Spearman {rho_ours:+.4f}")
    print("same feature under the original's rule (space and tab skipped): "
          f"     Spearman {rho_theirs:+.4f}")
    print(f"  snippets where the two rules give the same value: {exact} of {len(ids)}; "
          f"Figure 9 signs this feature negative, so the original's rule "
          f"{'agrees' if rho_theirs < 0 else 'disagrees'} and ours "
          f"{'agrees' if rho_ours < 0 else 'disagrees'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
