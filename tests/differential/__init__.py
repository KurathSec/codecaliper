"""Differential oracle lane (ARCHITECTURE.md §3.4, §8.2).

codecaliper values are compared per function against installed external
oracles (radon, lizard, cognitive_complexity) over the consistency corpus and
the BW-fidelity snippets. Every observed divergence must be classified in
``divergences.toml`` against the ruling that pins our behaviour, and every
table entry must still be observed — complete by construction, both
directions. A missing oracle SKIPs with a precise reason, never fails.
"""
