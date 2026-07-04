"""MetricContext — the trace/audit seam every increment routes through.

``ctx.count(ruling, node, delta)`` records which rulings actually fired (for
``Provenance.rulings_applied``) and, only when ``explain=True``, a per-increment
:class:`RulingTrace` — zero cost on the default path (ARCHITECTURE.md §3.3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from codecaliper.model import RulingTrace, Span

if TYPE_CHECKING:  # pragma: no cover
    from codecaliper.syntax._treesitter import Node


@dataclass
class MetricContext:
    cognitive_mode: str = "whitepaper"  # "whitepaper" | "sonar-compat"
    explain: bool = False
    line_range: tuple[int, int] | None = None  # CORE-JAVA-0001 scaffold restriction
    line_offset: int = 0  # scaffold lines to subtract so trace spans stay in
    # original snippet coordinates (CORE-JAVA-0001)
    fired: set[str] = field(default_factory=set)
    traces: dict[str, list[RulingTrace]] = field(default_factory=dict)

    def in_range(self, node: Node) -> bool:
        if self.line_range is None:
            return True
        lo, hi = self.line_range
        return lo <= node.start_point[0] + 1 <= hi

    def count(self, ruling_id: str, node: Node, delta: float = 1.0, metric: str = "") -> float:
        self.fired.add(ruling_id)
        if self.explain:
            span = Span(
                node.start_point[0] + 1 - self.line_offset, node.start_point[1],
                node.end_point[0] + 1 - self.line_offset, node.end_point[1],
            )
            self.traces.setdefault(metric, []).append(RulingTrace(ruling_id, span, delta))
        return delta

    def trace_for(self, metric: str) -> tuple[RulingTrace, ...]:
        return tuple(self.traces.get(metric, ()))
