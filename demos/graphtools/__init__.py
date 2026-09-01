"""graphtools — the recipe-demo mechanics for the talk.

Notebooks stay thin; the work lives here. Every module maps to a part of the talk:

    extract.py   Act I   — text -> typed records (naive triples, then schema v1 and v2)
    graph.py     Act I   — records -> NetworkX graph
    resolve.py   Act II  — entity matching (synonym table + fuzzy) and hybrid vector lookup
    focus.py     Act II  — the legible before/after projection for entity matching
    algos.py     Act III — ppr / explain_path / match_subgraph
    bench.py     Act III — load the committed real-world result files (artifacts/)
    replay.py    infra   — record/replay cache so the LLM extractions run offline
    viz.py       infra   — matplotlib rendering for the notebooks
"""

from .graph import build_graph, build_naive_graph
from .algos import ppr, explain_path, match_subgraph

__all__ = ["build_graph", "build_naive_graph", "ppr", "explain_path", "match_subgraph"]
