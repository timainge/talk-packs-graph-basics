"""graphtools — the live recipe-demo mechanics for the talk.

Notebooks stay thin; the work lives here. Every public name maps to a beat:

    extract.py   [HOW] Act I   — recipe v1 (text -> typed records)
    graph.py     [HOW] Act I   — records -> NetworkX graph
    resolve.py   [HOW] Act II  — entity resolution + hybrid lookup
    drift.py     [---] Act II  — the drift visualisation (sidequest; build last)
    algos.py     [HOW] Act III — ppr / authority / explain_path / match_subgraph
    bench.py     [MONEY]       — load committed judgements benchmark files (no private code)
    replay.py    infra         — record/replay cache so live LLM demos are deterministic
"""

from .graph import build_graph, build_naive_graph
from .algos import ppr, authority, explain_path, match_subgraph

__all__ = ["build_graph", "build_naive_graph", "ppr", "authority", "explain_path", "match_subgraph"]
