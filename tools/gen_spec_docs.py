#!/usr/bin/env python3
"""Render the ruling TOMLs into docs/spec/rulings.md.

The TOMLs are the single source of truth; the rendered table is a build
artifact. CI regenerates and diffs it so the published spec can never lag the
shipped one (ARCHITECTURE.md §11, the spec-docs job).
"""

from __future__ import annotations

from pathlib import Path

from codecaliper.spec import iter_rulings, spec_version

OUT = Path(__file__).resolve().parent.parent / "docs" / "spec" / "rulings.md"


def main() -> int:
    lines = [
        f"# codecaliper mapping specification v{spec_version()}",
        "",
        "> Generated from `src/codecaliper/spec/rulings/*.toml` by "
        "`tools/gen_spec_docs.py`. Do not edit by hand.",
        "",
    ]
    by_metric: dict[str, list] = {}
    for r in iter_rulings():
        by_metric.setdefault(r.metric, []).append(r)
    for metric in sorted(by_metric):
        lines += [f"## {metric}", ""]
        for r in sorted(by_metric[metric], key=lambda r: r.id):
            mode = f" *(mode: {r.mode})*" if r.mode else ""
            lines += [f"### {r.id} — {r.title}{mode}", ""]
            status = r.status + (
                f" (superseded by {r.superseded_by})" if r.superseded_by else ""
            )
            lines += [f"*language: {r.language} · status: {status} · "
                      f"since spec {r.since_spec}*", ""]
            if r.node_types:
                lines += [f"Binds node types: `{'`, `'.join(r.node_types)}`", ""]
            lines += [r.statement, ""]
            if r.examples:
                lines += [f"Normative cases: {', '.join(f'`{e}`' for e in r.examples)}", ""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
