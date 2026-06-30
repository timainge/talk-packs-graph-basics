"""[VIZ · review] POC fixtures for the deck scale/legibility pass.

Each builder here addresses a `demos.md` comment about a graph that's "too zoomed
out", "can't see the benefit", or "needs a more real-world example". They are
CANDIDATES, surfaced on review slides at the end of the deck (a "Graph review
appendix"); the winners get promoted into the main flow + `viz_export._FIXTURES`.

All offline: recipe builders replay from `data/cache/`; the code-graph builders
read the committed `artifacts/code-graph/eshop-code-graph.graphml`; the fraud ring
is hand-authored static data (the Act III spoken anchor, no private data).

Run: ``uv run python -c "from graphtools.poc_fixtures import write_pocs; write_pocs()"``
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import networkx as nx

from .viz_export import to_graph_json

_DEMOS_DIR = Path(__file__).resolve().parent.parent
_CODE_GRAPHML = _DEMOS_DIR / "artifacts" / "code-graph" / "eshop-code-graph.graphml"
_PFX = "Microsoft.eShopWeb."  # node-id prefix in the code graph


# ---------------------------------------------------------------------------
# #2 — the v0 "mess": is it the source or the params? Two candidates.
# ---------------------------------------------------------------------------

def _poc_naive_single() -> dict:
    """SMALLER SOURCE: free-form triples from ONE short recipe (Pancakes).

    The full naive-v0 (51 nodes off the first hero recipe) is unreadable. A single
    short recipe gives ~15-25 untyped nodes — you can actually READ the inconsistent
    predicate vocabulary and the duplicate/near-duplicate entities that are the point.
    """
    from .data import load_hero_texts
    from .extract import extract_freeform
    from .graph import build_naive_graph

    title, text = next(t for t in load_hero_texts() if t[0] == "Pancakes")
    g = build_naive_graph(extract_freeform(text))
    return to_graph_json(
        g,
        title=f"v0 mess — single small recipe ({title}): untyped nodes + inconsistent predicates, but READABLE",
    )


def _poc_naive_curated() -> dict:
    """CURATED static mess — the v0 failures, legibly dense.

    Real free-form extraction fragments into disconnected pairs (see -single /
    -tuned), so the 'mess' reads as sparse scatter, not a tangle. This hand-built
    12-ish-node graph instead makes the actual v0 defects unmissable: ONE thing
    under many names (Pancakes / pancake recipe / the batter; Flour / plain flour /
    flour; Egg / eggs; Milk / milk) and a different predicate every time."""
    from .graph import build_naive_graph

    triples = [
        {"subject": "Pancakes", "predicate": "needs", "object": "Flour"},
        {"subject": "pancake recipe", "predicate": "requires", "object": "plain flour"},
        {"subject": "the batter", "predicate": "made with", "object": "flour"},
        {"subject": "Pancakes", "predicate": "has ingredient", "object": "eggs"},
        {"subject": "the batter", "predicate": "uses", "object": "Egg"},
        {"subject": "Pancakes", "predicate": "contains", "object": "Milk"},
        {"subject": "pancake recipe", "predicate": "needs", "object": "milk"},
        {"subject": "Flour", "predicate": "mixed with", "object": "Egg"},
        {"subject": "plain flour", "predicate": "combined with", "object": "Milk"},
        {"subject": "the batter", "predicate": "cooked on", "object": "a pan"},
        {"subject": "pancake recipe", "predicate": "serves", "object": "4 people"},
        {"subject": "Pancakes", "predicate": "is a", "object": "breakfast"},
    ]
    g = build_naive_graph(triples)
    data = to_graph_json(
        g,
        title="v0 mess — CURATED: one thing under many names (Pancakes/the batter; Flour/plain flour/flour) + a different predicate every time",
    )
    data["params"] = {
        "labels": {"nodeFontSize": 15, "edgeFontSize": 12},
        "nodes": {"radiusScale": 1.15},
        "layout": {"spread": 0.85},
    }
    return data


def _poc_naive_tuned() -> dict:
    """PARAMS ONLY: the same full naive-v0, re-skinned to claw back legibility.

    Same messy source as the live slide, but with bigger labels, more spread and
    edge labels OFF — tests whether presentation params alone rescue it (vs needing
    a smaller source). Compare side-by-side with `poc-naive-single`.
    """
    from .data import load_hero_texts
    from .extract import extract_freeform
    from .graph import build_naive_graph

    _title, text = load_hero_texts()[0]
    g = build_naive_graph(extract_freeform(text))
    data = to_graph_json(
        g, title="v0 mess — full source, params-tuned (bigger labels, more spread, no edge chips)"
    )
    data["params"] = {
        "labels": {"nodeFontSize": 15, "showEdges": False},
        "nodes": {"radiusScale": 1.2},
        "layout": {"spread": 1.5},
    }
    return data


# ---------------------------------------------------------------------------
# #5 — "a shape isn't an ontology": the v2 win is per-attribute, invisible in
# topology. Show it on ONE recipe with the UNITS ON THE EDGES.
# ---------------------------------------------------------------------------

def _recipe_unit_focus(recipe, normalise_v2: bool):
    """Project ONE recipe to recipe + ingredient nodes, with each CONTAINS edge
    RELABELLED to its quantity+unit so the canonicalisation is visible on the edge.

    `normalise_v2=False` → v1 (verbatim units like '2 cup', Title-Case names);
    `normalise_v2=True`  → v2 (canonical 'ml'/'g', clean lowercase names)."""
    from .extract import extract_recipe, extract_recipe_v2  # noqa: F401
    from .graph import nid

    g = nx.MultiDiGraph()
    rid = nid("recipe", recipe.title)
    g.add_node(rid, kind="recipe", label=recipe.title)
    for ing in recipe.ingredients:
        iid = nid("ingredient", ing.name)
        if iid not in g:
            g.add_node(iid, kind="ingredient", label=ing.name.strip())
        qty = ing.quantity
        qty_str = ("" if qty is None else (f"{qty:g}")).strip()
        unit = (ing.unit or "").strip()
        chip = (f"{qty_str} {unit}").strip() or "—"
        g.add_edge(rid, iid, key=f"C{iid}", rel=chip, qty=qty, unit=ing.unit)
    return g


def _poc_v2_single(normalise_v2: bool) -> dict:
    from .data import load_hero_texts
    from .extract import extract_recipe, extract_recipe_v2
    from .graph import nid

    title, text = next(t for t in load_hero_texts() if t[0] == "Beef Lo Mein")
    recipe = extract_recipe_v2(text) if normalise_v2 else extract_recipe(text)
    g = _recipe_unit_focus(recipe, normalise_v2)

    # pin the recipe at centre so v1/v2 share a frame; ingredients fan out (free).
    layout = {nid("recipe", recipe.title): (0.0, 0.0)}
    tag = "v2 (schema-first)" if normalise_v2 else "v1 (naive)"
    detail = (
        "canonical units (g/ml) + clean lowercase names"
        if normalise_v2
        else "verbatim cooking units (cups/tbsp/lb) + Title-Case names"
    )
    data = to_graph_json(g, layout=layout, title=f"'A shape isn't an ontology' — {title} {tag}: {detail}")
    # units live on the edge chips here, so make them legible and keep node labels.
    data["params"] = {
        "labels": {"nodeFontSize": 15, "edgeFontSize": 13, "showEdges": True},
        "nodes": {"radiusScale": 1.1},
        "layout": {"spread": 1.25},
        "density": {"edgeLabelLimit": 200},
    }
    return data


# ---------------------------------------------------------------------------
# #9 / #9a — shortest path. Real-world REPLACEMENT: the eShop code graph.
# "why does editing Basket..ctor break checkout" — a 4-hop calls chain.
# ---------------------------------------------------------------------------

def _short_label(node_id: str) -> str:
    """Human label for a code node: last 2 dotted segments (Type.Member)."""
    parts = node_id.split(".")
    if parts[-1] == "":  # ".ctor" splits oddly
        parts = parts[:-1]
    return ".".join(parts[-2:]) if len(parts) >= 2 else parts[-1]


def _code_kind(attrs: dict) -> str:
    t = (attrs.get("type") or "").lower()
    k = (attrs.get("kind") or "").lower()
    if t == "type":
        return "interface" if k == "interface" or attrs.get("name", "").startswith("I") else "class"
    if t == "member":
        return "method"
    return "class"


def _poc_codepath() -> dict:
    g = nx.read_graphml(_CODE_GRAPHML)
    chain = [
        _PFX + s for s in [
            "Web.Pages.Basket.CheckoutModel.OnPost",
            "Web.Pages.Basket.CheckoutModel.SetBasketModelAsync",
            "Web.Services.BasketViewModelService.GetOrCreateBasketForUser",
            "Web.Services.BasketViewModelService.CreateBasketForUser",
            "ApplicationCore.Entities.BasketAggregate.Basket..ctor",
        ]
    ]
    h = nx.MultiDiGraph()

    def add(nid_: str):
        if nid_ not in h:
            a = g.nodes[nid_]
            h.add_node(nid_, kind=_code_kind(a), label=_short_label(nid_))

    for nid_ in chain:
        add(nid_)
    # the path edges
    for u, v in zip(chain, chain[1:]):
        h.add_edge(u, v, key="calls", rel="calls")
    # a little 1-hop context off each path node (callers/callees) so it's not a bare line
    for nid_ in chain:
        for _u, ctx in list(g.out_edges(nid_))[:2]:
            if ctx not in chain:
                add(ctx)
                h.add_edge(nid_, ctx, key="calls", rel="calls")

    # staged reveal: walk the 4 hops
    reveal = [{"label": "seed", "nodes": [chain[0]], "edges": []}]
    for u, v in zip(chain, chain[1:]):
        reveal.append({"label": "hop", "nodes": [v], "edges": [[u, v, "calls"]]})

    data = to_graph_json(
        h,
        reveal=reveal,
        title="Shortest path (REAL code graph) — why editing Basket..ctor breaks checkout: a 4-hop calls chain",
    )
    data["params"] = {"labels": {"nodeFontSize": 14}, "layout": {"spread": 1.2}}
    return data


# ---------------------------------------------------------------------------
# #10 — exact subgraph match. Two real-world candidates: the code-graph
# Decorator motif, and the AML fraud ring (the Act III spoken anchor).
# ---------------------------------------------------------------------------

def _poc_decorator() -> dict:
    g = nx.read_graphml(_CODE_GRAPHML)
    deco = _PFX + "Web.Services.CachedCatalogViewModelService"
    wrapped = _PFX + "Web.Services.CatalogViewModelService"
    iface = _PFX + "Web.Services.ICatalogViewModelService"

    h = nx.MultiDiGraph()
    h.add_node(deco, kind="class", label="CachedCatalogViewModelService")
    h.add_node(wrapped, kind="class", label="CatalogViewModelService")
    h.add_node(iface, kind="interface", label="ICatalogViewModelService")
    # the Decorator motif: both implement the interface; the cache wraps the real one.
    h.add_edge(deco, iface, key="implements", rel="implements")
    h.add_edge(wrapped, iface, key="implements", rel="implements")
    h.add_edge(deco, wrapped, key="wraps", rel="wraps (calls)")

    reveal = [
        {"label": "interface", "nodes": [iface], "edges": []},
        {"label": "both implement", "nodes": [deco, wrapped],
         "edges": [[deco, iface, "implements"], [wrapped, iface, "implements"]]},
        {"label": "wraps", "nodes": [deco, wrapped], "edges": [[deco, wrapped, "wraps"]]},
    ]
    data = to_graph_json(
        h,
        reveal=reveal,
        title="Exact subgraph match (REAL code graph) — the Decorator motif, found all-and-only (P=R=1.0)",
    )
    # bolder arrowheads so direction (who wraps/implements whom) reads on a sparse graph.
    data["params"] = {
        "labels": {"nodeFontSize": 15},
        "nodes": {"radiusScale": 1.15},
        "layout": {"spread": 1.3},
        "edges": {"arrowScale": 2.0, "endGap": 4},
    }
    return data


def _poc_decorator_query() -> dict:
    """Abstract build-up twin of `_poc_decorator`, for the 'subgraph query' slide.

    SAME node ids / edge order / params as `_poc_decorator` so the two fixtures
    share an identical frozen layout — the slide can v-if swap from this (abstract
    pattern variables) to `poc-decorator` (concrete matched symbols) with no jump.
    Only the labels and the reveal differ: labels are the query variables
    (cache/impl/iface) and the reveal lights edges in the order the query declares
    them — wraps first, then the two implements edges."""
    deco = _PFX + "Web.Services.CachedCatalogViewModelService"
    wrapped = _PFX + "Web.Services.CatalogViewModelService"
    iface = _PFX + "Web.Services.ICatalogViewModelService"

    h = nx.MultiDiGraph()
    # node + edge order identical to _poc_decorator → identical layout.
    h.add_node(deco, kind="class", label="cache")
    h.add_node(wrapped, kind="class", label="impl")
    h.add_node(iface, kind="interface", label="iface")
    h.add_edge(deco, iface, key="implements", rel="implements")
    h.add_edge(wrapped, iface, key="implements", rel="implements")
    h.add_edge(deco, wrapped, key="wraps", rel="wraps")

    # reveal in QUERY order. Step 0 is intentionally EMPTY so the slide opens
    # "dark" (whole pattern dimmed), then each click lights — and focuses — the
    # next edge condition: (cache)-[:WRAPS]->(impl), then the two IMPLEMENTS edges.
    reveal = [
        {"label": "dark", "nodes": [], "edges": []},
        {"label": "wraps", "nodes": [deco, wrapped], "edges": [[deco, wrapped, "wraps"]]},
        {"label": "cache implements iface", "nodes": [iface],
         "edges": [[deco, iface, "implements"]]},
        {"label": "impl implements iface", "nodes": [wrapped],
         "edges": [[wrapped, iface, "implements"]]},
    ]
    data = to_graph_json(
        h,
        reveal=reveal,
        title="Subgraph query (abstract) — the Decorator pattern built edge-by-edge in query order",
    )
    # MUST match _poc_decorator's params (incl. arrowScale) so the swap doesn't jump.
    data["params"] = {
        "labels": {"nodeFontSize": 15},
        "nodes": {"radiusScale": 1.15},
        "layout": {"spread": 1.3},
        "edges": {"arrowScale": 2.0, "endGap": 4},
    }
    return data


def _poc_landscape() -> dict:
    """Wrap-up 'there's more' map — the classes of graph problem as a hub-and-spoke.
    Three toured beats (green) on the left, next-steps (violet) on the right with the
    AI/KG-weighted teaser, out-of-scope set apart at the bottom. Node positions are
    PINNED (x/y) so each category's members sit adjacent — d3-force freezes any node
    that arrives with finite coords. Static (no reveal); undirected (no arrowheads)."""
    h = nx.MultiDiGraph()
    hub = "class:graph-problems"
    h.add_node(hub, kind="maphub", label="graph problems", x=0, y=0)
    # (label, status-kind, x, y) — left column = toured, right column = next steps.
    classes = [
        ("Ranking", "toured", -250, -130),
        ("Paths", "toured", -250, 0),
        ("Patterns", "toured", -250, 130),
        ("Prediction", "frontier", 250, -130),
        ("Similarity", "frontier", 250, 0),
        ("Clustering", "frontier", 250, 130),
        ("Flow & cost", "scope", 0, 215),
    ]
    for label, kind, x, y in classes:
        nid = f"class:{label.lower()}"
        h.add_node(nid, kind=kind, label=label, x=x, y=y)
        h.add_edge(hub, nid, key="is", rel="", directed=False)
    data = to_graph_json(
        h,
        title="Graph problem classes — three toured (green), next steps ahead (violet)",
    )
    data["params"] = {
        "labels": {"nodeFontSize": 16},
        "legend": {"show": False},
    }
    return data


def _poc_fraud_ring() -> dict:
    """STATIC curated AML 'ring' — the Act III spoken anchor, made visual.

    A money cycle A->B->C->A (invisible in SQL, obvious as a shape), fed by mule
    accounts and cashing out at a merchant. Hand-authored illustrative data."""
    h = nx.MultiDiGraph()
    ring = ["acct:A", "acct:B", "acct:C"]
    for a in ring:
        h.add_node(a, kind="account", label=a.split(":")[1])
    # the cycle
    cyc = [("acct:A", "acct:B"), ("acct:B", "acct:C"), ("acct:C", "acct:A")]
    for u, v in cyc:
        h.add_edge(u, v, key="pays", rel="$")
    # mules feeding the ring
    mules = ["mule:m1", "mule:m2", "mule:m3"]
    for i, m in enumerate(mules):
        h.add_node(m, kind="mule", label="mule")
        h.add_edge(m, ring[i % 3], key="pays", rel="$")
    # cash-out merchant + some innocent traffic for context
    h.add_node("merch:shop", kind="merchant", label="Merchant")
    h.add_edge("acct:C", "merch:shop", key="pays", rel="$")
    for i, name in enumerate(["acct:X", "acct:Y", "acct:Z"]):
        h.add_node(name, kind="account", label=name.split(":")[1])
        h.add_edge(name, "merch:shop", key="pays", rel="$")

    reveal = [
        {"label": "haystack", "nodes": [], "edges": []},
        {"label": "the ring", "nodes": ring,
         "edges": [[u, v, "pays"] for u, v in cyc]},
    ]
    data = to_graph_json(
        h,
        reveal=reveal,
        title="Exact subgraph match (illustrative) — the A→B→C→A money-laundering ring: invisible in SQL, obvious as a shape",
    )
    data["params"] = {"labels": {"nodeFontSize": 14}, "nodes": {"radiusScale": 1.15}, "layout": {"spread": 1.2}}
    return data


def _poc_subgraph_cumin() -> dict:
    """LEGIBLE recipe version: the cumin shared-ingredient star, projected small.

    Just cumin + the recipes that contain it + their other SHARED ingredients —
    drops steps/techniques and singleton ingredients so the 'star' shape reads."""
    from .data import load_hero_texts
    from .extract import extract_recipe
    from .graph import build_graph

    recipes = [extract_recipe(t) for _ti, t in load_hero_texts()]
    g = build_graph(recipes, normalise=True)
    shared = "ingredient:cumin"
    star = [r for r in g.predecessors(shared) if g.nodes[r].get("kind") == "recipe"]

    h = nx.MultiDiGraph()
    h.add_node(shared, kind="ingredient", label="cumin")
    for r in star:
        h.add_node(r, **g.nodes[r])
        h.add_edge(r, shared, key="CONTAINS", rel="CONTAINS")
    # add other ingredients shared by >=2 of the star recipes (context, keeps it a graph)
    from collections import Counter
    ing_count: Counter = Counter()
    for r in star:
        for _u, ing in g.out_edges(r):
            if g.nodes[ing].get("kind") == "ingredient" and ing != shared:
                ing_count[ing] += 1
    for ing, c in ing_count.items():
        if c >= 2:
            h.add_node(ing, **g.nodes[ing])
            for r in star:
                if g.has_edge(r, ing):
                    h.add_edge(r, ing, key="CONTAINS", rel="CONTAINS")

    reveal = [
        {"label": "pattern", "nodes": [shared], "edges": []},
        {"label": "matches", "nodes": star, "edges": [[r, shared, "CONTAINS"] for r in star]},
    ]
    data = to_graph_json(
        h, reveal=reveal,
        title="Exact subgraph match (recipe, projected) — recipes sharing cumin, as a legible star",
    )
    data["params"] = {"labels": {"nodeFontSize": 14}, "nodes": {"radiusScale": 1.1}, "layout": {"spread": 1.25}}
    return data


# ---------------------------------------------------------------------------
# #9 / #12 — substitution path, LEGIBLE recipe version (projected, not the
# 259-node hairball with a camera zoom).
# ---------------------------------------------------------------------------

def _poc_path_recipe() -> dict:
    from .data import load_hero_texts
    from .extract import extract_recipe
    from .graph import build_graph_v3
    from .algos import explain_path

    recipes = [extract_recipe(t) for _ti, t in load_hero_texts()]
    g = build_graph_v3(recipes, with_substitutions=True)
    src, tgt = "ingredient:yoghurt", "ingredient:milk"
    path = explain_path(g, src, tgt)

    h = nx.MultiDiGraph()
    for n in path:
        h.add_node(n, **g.nodes[n])
    for u, v in zip(path, path[1:]):
        key = next(iter(g[u][v]))
        attrs = {k: val for k, val in g.edges[u, v, key].items() if k not in ("rel", "key")}
        h.add_edge(u, v, key="SUBSTITUTES_FOR", rel="SUBSTITUTES_FOR", **attrs)
    # 1-hop context: a couple of recipes that contain the path endpoints
    for endpoint in (src, tgt):
        cnt = 0
        for r in g.predecessors(endpoint):
            if g.nodes[r].get("kind") == "recipe" and cnt < 2:
                h.add_node(r, **g.nodes[r]); h.add_edge(r, endpoint, key="CONTAINS", rel="CONTAINS"); cnt += 1

    reveal = [{"label": "seed", "nodes": [path[0]], "edges": []}]
    for u, v in zip(path, path[1:]):
        reveal.append({"label": "hop", "nodes": [v], "edges": [[u, v, "SUBSTITUTES_FOR"]]})
    data = to_graph_json(
        h, reveal=reveal,
        title="Shortest path (recipe, projected) — yoghurt → buttermilk → milk, the substitution chain, legible",
    )
    data["params"] = {"labels": {"nodeFontSize": 15}, "nodes": {"radiusScale": 1.1}, "layout": {"spread": 1.3}}
    return data


# ---------------------------------------------------------------------------
# #13 — projection: a query seed → its retrieved ego-graph "context".
# ---------------------------------------------------------------------------

def _poc_projection_ego() -> dict:
    """The bookend's missing 'Project' beat: seed a query, project the relevant
    neighbourhood (a 1-hop ego-graph) — that compact subgraph IS the context you
    hand to the model, instead of the whole corpus."""
    from .data import load_hero_texts
    from .extract import extract_recipe
    from .graph import build_graph

    recipes = [extract_recipe(t) for _ti, t in load_hero_texts()]
    g = build_graph(recipes, normalise=True)
    seed = "ingredient:garlic"
    neigh = [r for r in g.predecessors(seed) if g.nodes[r].get("kind") == "recipe"][:5]

    h = nx.MultiDiGraph()
    h.add_node(seed, kind="query", label="garlic?")
    ctx_nodes: list[str] = []
    ctx_edges: list[list] = []
    for r in neigh:
        h.add_node(r, **g.nodes[r])
        h.add_edge(r, seed, key="CONTAINS", rel="CONTAINS")
        # one extra shared ingredient per recipe as projected context
        for _u, ing in list(g.out_edges(r)):
            if g.nodes[ing].get("kind") == "ingredient" and ing != seed and g.in_degree(ing) >= 3:
                h.add_node(ing, **g.nodes[ing]); h.add_edge(r, ing, key="CONTAINS", rel="CONTAINS")
                if ing not in ctx_nodes:
                    ctx_nodes.append(ing)
                ctx_edges.append([r, ing, "CONTAINS"])
                break

    # 3-step reveal: ask the question → the recipes that match → the surrounding
    # neighbourhood (the projected subgraph you'd hand to a model as context).
    reveal = [
        {"label": "query", "nodes": [seed], "edges": []},
        {"label": "recipes with garlic", "nodes": neigh, "edges": [[r, seed, "CONTAINS"] for r in neigh]},
        {"label": "+ projected context", "nodes": ctx_nodes, "edges": ctx_edges},
    ]
    data = to_graph_json(
        h, reveal=reveal,
        title="Projection (POC) — a query seed → its ego-graph: the compact context you retrieve, not the whole corpus",
    )
    data["params"] = {"labels": {"nodeFontSize": 14}, "nodes": {"radiusScale": 1.1}, "layout": {"spread": 1.25}}
    return data


def _poc_projection_ego_full() -> dict:
    """Variant of `_poc_projection_ego` that keeps EVERY ingredient of each matched
    recipe (not just one context node), so the projected subgraph looks like a real
    corpus slice. Shared staples (oil / onion / tomato / cumin) become hubs that
    cross-link the recipes — the realism is in that connective tissue."""
    from .data import load_hero_texts
    from .extract import extract_recipe
    from .graph import build_graph

    recipes = [extract_recipe(t) for _ti, t in load_hero_texts()]
    g = build_graph(recipes, normalise=True)
    seed = "ingredient:garlic"
    neigh = [r for r in g.predecessors(seed) if g.nodes[r].get("kind") == "recipe"][:5]

    h = nx.MultiDiGraph()
    h.add_node(seed, kind="query", label="garlic?")
    ctx_nodes: list[str] = []
    ctx_edges: list[list] = []
    for r in neigh:
        h.add_node(r, **g.nodes[r])
        h.add_edge(r, seed, key="CONTAINS", rel="CONTAINS")
        for _u, ing in list(g.out_edges(r)):
            if g.nodes[ing].get("kind") != "ingredient" or ing == seed:
                continue
            if ing not in h:
                h.add_node(ing, **g.nodes[ing])
            h.add_edge(r, ing, key="CONTAINS", rel="CONTAINS")
            if ing not in ctx_nodes:
                ctx_nodes.append(ing)
            ctx_edges.append([r, ing, "CONTAINS"])

    reveal = [
        {"label": "query", "nodes": [seed], "edges": []},
        {"label": "recipes with garlic", "nodes": neigh, "edges": [[r, seed, "CONTAINS"] for r in neigh]},
        {"label": "+ full ingredient context", "nodes": ctx_nodes, "edges": ctx_edges},
    ]
    data = to_graph_json(
        h, reveal=reveal,
        title="Projection (POC, full) — query seed → ego-graph keeping every ingredient; shared staples cross-link the recipes",
    )
    # smaller labels + more spread to stay legible at ~55 nodes
    data["params"] = {"labels": {"nodeFontSize": 11}, "nodes": {"radiusScale": 0.9}, "layout": {"spread": 1.5}}
    return data


# name -> builder
_POCS = {
    "poc-naive-curated": _poc_naive_curated,
    "poc-naive-single": _poc_naive_single,
    "poc-naive-tuned": _poc_naive_tuned,
    "poc-v2-single-before": lambda: _poc_v2_single(normalise_v2=False),
    "poc-v2-single-after": lambda: _poc_v2_single(normalise_v2=True),
    "poc-codepath": _poc_codepath,
    "poc-decorator": _poc_decorator,
    "poc-decorator-query": _poc_decorator_query,
    "poc-landscape": _poc_landscape,
    "poc-fraud-ring": _poc_fraud_ring,
    "poc-subgraph-cumin": _poc_subgraph_cumin,
    "poc-path-recipe": _poc_path_recipe,
    "poc-projection-ego": _poc_projection_ego,
    "poc-projection-ego-full": _poc_projection_ego_full,
}


def write_pocs(out_dir="demos/viz/fixtures") -> list[str]:
    out = Path(out_dir)
    if not out.is_absolute():
        out = _DEMOS_DIR.parent / out_dir
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, build in _POCS.items():
        data = build()
        p = out / f"{name}.json"
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        paths.append(str(p))
    return paths
