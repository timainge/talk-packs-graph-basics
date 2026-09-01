"""[HOW · Act III] The talk's graph algorithms, as thin NetworkX wrappers.

Personalised PageRank (ranking), shortest path (paths) and exact subgraph matching
(patterns) — the three the talk tours. The recipe graph carries the intuition; the
committed artifacts (see bench.py) carry the real-world results.

These are demo helpers: they return empty results rather than raising on the
ordinary "no answer" / tiny-graph cases, so a live cell never throws a traceback.
"""

from __future__ import annotations

import random

import networkx as nx


def random_walk_with_restart(
    g: nx.Graph,
    seeds: list[str],
    *,
    steps: int = 60,
    restart_prob: float = 0.15,
    rng_seed: int = 0,
) -> tuple[list[str], list[int]]:
    """Trace ONE random-walk-with-restart over ``g``, personalised to ``seeds``.

    This is the *sampling* view of Personalised PageRank. :func:`ppr` computes the
    stationary distribution analytically (``nx.pagerank``); this instead traces a
    single walker step by step so the walk can be **animated**. The mechanism is
    exactly PPR's: from the current node, with probability ``restart_prob`` teleport
    back to a (random) seed, otherwise step to a random neighbour. Over many steps
    the fraction of time spent on each node converges to its PPR score.

    Runs on the **undirected** view for the same reason as :func:`ppr` (recipe edges
    point recipe→ingredient, so a directed walk from an ingredient seed dead-ends).

    Deterministic for a given ``rng_seed``.

    Returns ``(visits, restarts)`` where ``visits`` is the ordered list of visited
    node ids (length ``steps + 1``, including the start) and ``restarts`` is the list
    of indices in ``visits`` that were reached by a teleport back to a seed.
    """
    ug = g.to_undirected() if g.is_directed() else g
    present = [s for s in seeds if s in ug]
    if not present:
        raise ValueError("no seed nodes present in graph")
    rnd = random.Random(rng_seed)
    cur = rnd.choice(present)
    visits = [cur]
    restarts: list[int] = []
    for _ in range(steps):
        nbrs = list(ug.neighbors(cur))
        if not nbrs or rnd.random() < restart_prob:
            cur = rnd.choice(present)
            restarts.append(len(visits))
        else:
            cur = rnd.choice(nbrs)
        visits.append(cur)
    return visits, restarts


def ppr(g: nx.Graph, seeds: list[str], top: int = 10) -> list[tuple[str, float]]:
    """Personalised PageRank — "given this seed, what's most relevant?" (smarter).

    seeds: node ids to personalise toward (e.g. one ingredient or recipe).

    Runs on the **undirected** view: the recipe graph's edges point recipe→ingredient
    and step→ingredient, so on the *directed* graph an ingredient seed has almost no
    out-edges and PPR collapses onto a lone sink. Undirected PPR walks back out to the
    recipes/steps that actually use the seed — the intended "what's related" answer.
    """
    seeds = [s for s in seeds if s in g]
    if not seeds:
        return []
    ug = g.to_undirected() if g.is_directed() else g
    personalization = {n: (1.0 if n in seeds else 0.0) for n in ug.nodes}
    scores = nx.pagerank(ug, personalization=personalization)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [(n, s) for n, s in ranked if n not in seeds][:top]


def authority(g: nx.Graph, top: int = 10) -> list[tuple[str, float]]:
    """HITS authority scores — "which nodes does everything else point at?"

    Not part of the spoken talk (kept for the citation-graph experiments). On a
    citation graph the landmark cases surface. Returns [] for an edgeless graph
    (HITS is undefined there) rather than raising.
    """
    if g.number_of_edges() == 0:
        return []
    _hubs, auth = nx.hits(g, max_iter=1000, normalized=True)
    return sorted(auth.items(), key=lambda kv: kv[1], reverse=True)[:top]


def explain_path(g: nx.Graph, source: str, target: str) -> list[str]:
    """Shortest path — "how does A relate to B, and through what?" (more reliable).

    The auditable answer vector search cannot give. Returns the node-id path, or
    [] when there is no path / a node is absent (so a live cell never throws).
    """
    try:
        return nx.shortest_path(g, source=source, target=target)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []


def match_subgraph(g: nx.Graph, pattern: nx.Graph, node_match=None, edge_match=None) -> list[dict]:
    """Exact subgraph matching (VF2) — "find this shape, not this keyword".

    Returns each match as a ``{pattern_node: graph_node}`` mapping. ``node_match`` /
    ``edge_match`` are the usual NetworkX callables ``(graph_attrs, pattern_attrs) -> bool``
    for typed matching (e.g. only match a ``class`` to a ``class``). Fuzzy / learned
    matching is reading-list material (see FURTHER-READING.md), not a demo.

    Note: NetworkX's matcher yields ``{graph_node: pattern_node}``; we invert it so
    the returned dict honours the documented ``{pattern_node: graph_node}`` contract.
    """
    matcher = nx.algorithms.isomorphism.DiGraphMatcher(
        g, pattern, node_match=node_match, edge_match=edge_match
    )
    return [{p: gnode for gnode, p in m.items()} for m in matcher.subgraph_monomorphisms_iter()]
