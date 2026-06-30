"""[VIZ] Export graphtools graphs to a JSON "fixture" format for the JS renderer.

Phase 1 of the graph-visualisation toolchain. The browser-side SVG renderer reads
these committed fixtures, so the talk's graphs render with no Python at runtime.

Every fixture is ``networkx.node_link_data(g, edges="links")`` (so the link list is
under the top-level ``"links"`` key, as modern networkx requires) lightly normalised:

  - each node carries ``id`` / ``kind`` / ``label`` (label falls back to id),
  - each link carries ``source`` / ``target`` / ``key`` / ``rel`` (rel falls back to
    key, then "related"), plus whatever extra edge attrs ride along (qty, unit, ...),
  - optional ``layout`` writes ``x`` / ``y`` floats onto nodes (the JS renderer
    normally computes layout itself, so we leave this off),
  - optional ``reveal`` (a list of step dicts) and ``title`` ride at the top level.

A ``reveal`` step is ``{"label", "nodes": [id...], "edges": [[src, tgt, key]...]}`` —
a cumulative "light these up" instruction for the staged walk-through animations.

Everything runs OFFLINE through ``graphtools.replay`` (the committed cache in
``data/cache/``), exactly like the notebooks — no API key, no network. Stdlib +
networkx only.
"""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

# repo root = demos/ (this file lives in demos/graphtools/)
_DEMOS_DIR = Path(__file__).resolve().parent.parent
_JUDGEMENTS_DIR = _DEMOS_DIR / "artifacts" / "judgements"


# --- core export -----------------------------------------------------------

def to_graph_json(g, layout=None, reveal=None, title=None) -> dict:
    """Serialise a networkx graph to the fixture dict (see module docstring).

    Args:
        g: a networkx graph with ``kind``/``label`` node attrs and ``rel`` edge attrs.
        layout: optional ``{node_id: (x, y)}`` — writes ``x``/``y`` floats onto nodes.
        reveal: optional list of step dicts, attached as top-level ``"reveal"``.
        title: optional caption, attached as top-level ``"title"``.

    Returns:
        A JSON-serialisable dict (tuples -> lists, ``None`` stays ``null``) whose
        link list is under the ``"links"`` key.
    """
    # node_link_data(edges="links") puts the edge list under "links" (not "edges"),
    # which is the key the JS renderer expects.
    data = nx.node_link_data(g, edges="links")

    # ensure every node has a usable label (fall back to its id).
    for node in data.get("nodes", []):
        if not node.get("label"):
            node["label"] = node.get("id")
        if layout is not None:
            xy = layout.get(node.get("id"))
            if xy is not None:
                node["x"] = float(xy[0])
                node["y"] = float(xy[1])

    # ensure every link names a relation (rel -> key -> "related").
    for link in data.get("links", []):
        if not link.get("rel"):
            link["rel"] = link.get("key") or "related"

    if reveal is not None:
        data["reveal"] = reveal
    if title is not None:
        data["title"] = title

    # round-trip through json to guarantee serialisability (tuples -> lists, etc.).
    return json.loads(json.dumps(data, default=str))


# --- helpers for the hand-built / reveal fixtures --------------------------

def _case_id(name: str) -> str:
    """Stable node id for a caselaw case, e.g. ``case:miranda v. arizona (1966)``."""
    return f"case:{name.strip().lower()}"


def _reveal_for_path(g, path: str, key: str) -> list[dict]:
    """Build a cumulative reveal for a node-id ``path`` walking edges of ``key``.

    step0 lights the seed node; each later step adds the next node plus the
    ``[u, v, key]`` edge. Skips any hop whose edge isn't actually present.
    """
    if not path:
        return []
    steps = [{"label": "seed", "nodes": [path[0]], "edges": []}]
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edges = []
        if g.has_edge(u, v):
            edges.append([u, v, key])
        steps.append({"label": "path", "nodes": [v], "edges": edges})
    return steps


def _edges_between(g, sources: list[str], target: str) -> list[dict]:
    """The ``[source, target, key]`` triples for each ``source`` that has an edge
    to ``target`` (first parallel key). Used to light a star / hub reveal."""
    edges = []
    for s in sources:
        if g.has_edge(s, target):
            key = next(iter(g[s][target]))  # first parallel-edge key
            edges.append([s, target, key])
    return edges


def _stored_edge(g, u: str, v: str):
    """Resolve the directed, stored ``[src, tgt, key]`` triple for the undirected
    hop ``u``–``v`` (the walk steps on the undirected view, but the renderer needs
    the edge as it is actually stored). Returns ``None`` if no such edge exists."""
    for a, b in ((u, v), (v, u)):
        if g.has_edge(a, b):
            # On a multigraph ``g[a][b]`` maps edge-key -> attrs; take the first
            # parallel key (the same identity the fixture's link list carries).
            key = next(iter(g[a][b]), "related") if g.is_multigraph() else "related"
            return [a, b, key]
    return None


def walk_frames(
    g,
    visits: list[str],
    restarts: list[int],
    *,
    tick_ms: int = 130,
    loop: bool = False,
    seeds: list[str] | None = None,
    decay: float = 1.0,
) -> dict:
    """Turn a traced walk (see ``algos.random_walk_with_restart``) into a GraphView
    ``walk`` block: a sequence of frames the renderer plays on a clock.

    Each frame is::

        {"heads": [node_id],            # the walker's current position (brightest)
         "edges": [[src, tgt, key]],    # the edge just traversed (lit); [] on restart
         "heat":  {node_id: 0..1},      # cumulative visit "heat", normalised so far
         "restart": bool}               # True when this position is a teleport-to-seed

    "Heat" is the running visit count per node, normalised at each frame against the
    busiest node *so far* — so nodes the walk keeps landing on visibly warm up. The
    renderer maps heat to node brightness + size, which is the visual analogue of the
    PPR score accumulating.

    A final frame is appended carrying the **exact** Personalised PageRank scores
    (``algos.ppr`` on the same seeds), normalised to ``max = 1`` — so when playback
    stops it freezes on the resolved ranking, not a noisy mid-walk snapshot.

    ``decay`` < 1 fades older visits (recency-weighted heat); 1.0 = plain cumulative.
    """
    from .algos import ppr

    seeds = seeds or [visits[0]]
    counts: dict[str, float] = {}
    frames: list[dict] = []
    restart_set = set(restarts)

    # `excursion` is the path (ordered edges) since the last restart. We light the
    # WHOLE excursion each frame — a comet-tail rooted at the seed — so an out-and-back
    # step reads as retracing rather than a fresh start somewhere else, and a restart
    # visibly collapses the tail back to the seed. `edges` is oldest→newest; the
    # renderer fades older edges and brightens the newest (the current hop).
    excursion: list[list] = []
    for i, node in enumerate(visits):
        if decay < 1.0:
            for k in list(counts):
                counts[k] *= decay
        counts[node] = counts.get(node, 0.0) + 1.0
        peak = max(counts.values()) or 1.0
        heat = {k: round(v / peak, 4) for k, v in counts.items()}
        is_restart = i in restart_set
        if i == 0 or is_restart:
            excursion = []  # at the seed: no trail yet (teleport collapses it)
        else:
            edge = _stored_edge(g, visits[i - 1], node)
            if edge:
                excursion.append(edge)
        frames.append(
            {
                "heads": [node],
                "edges": [list(e) for e in excursion],
                "heat": heat,
                "restart": is_restart,
            }
        )

    # Resolved payoff frame: the real PPR distribution, normalised to max = 1.
    scores = dict(ppr(g, seeds, top=10_000))
    for s in seeds:
        scores.setdefault(s, max(scores.values(), default=1.0))
    peak = max(scores.values(), default=1.0) or 1.0
    frames.append(
        {
            "heads": list(seeds),
            "edges": [],
            "heat": {k: round(v / peak, 4) for k, v in scores.items()},
            "restart": False,
            "resolved": True,
        }
    )

    return {"tickMs": tick_ms, "loop": loop, "seeds": list(seeds), "frames": frames}


# --- the fixture builders --------------------------------------------------
#
# All offline: the extract.* calls replay from data/cache/ (replay default is ON,
# no env var needed — see replay.caching_enabled()).

def _fixture_naive_v0() -> dict:
    """1. naive-v0 — the messy untyped baseline (free-form triples -> naive graph)."""
    from .data import load_hero_texts
    from .extract import extract_freeform
    from .graph import build_naive_graph

    _title, text = load_hero_texts()[0]  # first hero recipe, mirrors act1/sidequest
    triples = extract_freeform(text)  # v0, offline replay
    g = build_naive_graph(triples)
    return to_graph_json(
        g,
        title="v0: free-form triples — untyped 'entity' nodes, inconsistent relations, no resolution",
    )


def _fixture_recipe_single() -> dict:
    """2. recipe-single — one clean schema-first recipe graph (the 4 kinds)."""
    from .data import load_hero_texts
    from .extract import extract_recipe
    from .graph import build_graph

    title, text = load_hero_texts()[0]
    g = build_graph([extract_recipe(text)])
    return to_graph_json(g, title=f"v1 schema-first: one recipe ({title}) — recipe / ingredient / step / technique")


def _fixture_recipe_multi_drift() -> dict:
    """3. recipe-multi-drift — all recipes, normalise=False (duplicate ingredient nodes)."""
    from .data import load_hero_texts
    from .extract import extract_recipe
    from .graph import build_graph

    recipes = [extract_recipe(text) for _title, text in load_hero_texts()]
    g = build_graph(recipes, normalise=False)
    return to_graph_json(
        g,
        title="v1 at scale (normalise=False): raw ingredient names drift into duplicate nodes",
    )


def _fixture_recipe_v2() -> dict:
    """3b. recipe-v2 — the ontology-in-prompt rung: canonical units + clean names.

    Same recipes as recipe-multi-drift, but extracted with the v2 prompt
    (``extract_recipe_v2``), which standardises units and emits canonical
    ingredient names. Result: fewer near-duplicate ingredient nodes than v1 drift,
    before any explicit entity matching. This is the "a shape isn't an ontology" slide.
    """
    from .data import load_hero_texts
    from .extract import extract_recipe_v2
    from .graph import build_graph

    recipes = [extract_recipe_v2(text) for _title, text in load_hero_texts()]
    g = build_graph(recipes, normalise=False)
    ings = sum(1 for _n, d in g.nodes(data=True) if d.get("kind") == "ingredient")
    return to_graph_json(
        g,
        title=(
            f"v2 ontology-in-prompt: canonical units + clean names — near-duplicate "
            f"ingredient nodes drop to {ings} (from v1 drift's 112), before explicit matching"
        ),
    )


def _fixture_recipe_ppr() -> dict:
    """7. recipe-ppr — Personalised PageRank over the resolved recipe graph.

    Seed a single ingredient (garlic) and run PPR; the staged reveal lights the
    seed, then the recipes PPR ranks most relevant from that viewpoint. The Act III
    "smarter" beat, on recipes (answers the slide's open "can we use recipes?" note).
    """
    from .data import load_hero_texts
    from .extract import extract_recipe
    from .graph import build_graph
    from .algos import ppr

    recipes = [extract_recipe(text) for _title, text in load_hero_texts()]
    g = build_graph(recipes, normalise=True)

    seed = "ingredient:garlic"
    ranked = ppr(g, [seed], top=8)
    top_recipes = [n for n, _s in ranked if g.nodes[n].get("kind") == "recipe"][:5]
    reveal = [
        {"label": "seed", "nodes": [seed], "edges": []},
        # the recipes PPR finds most relevant, plus the direct CONTAINS edges that exist
        # back to the seed (some are relevant via shared ingredients, not a direct edge).
        {"label": "relevant", "nodes": top_recipes, "edges": _edges_between(g, top_recipes, seed)},
    ]
    return to_graph_json(
        g,
        reveal=reveal,
        title="Personalised PageRank: seed 'garlic' -> the recipes most relevant through the graph",
    )


def _fixture_recipe_subgraph() -> dict:
    """8. recipe-subgraph — exact subgraph matching: a "shared ingredient" star.

    Highlights one concrete match of the pattern "N recipes that all CONTAIN the same
    ingredient" — here the cumin star (chicken handi / egyptian fatteh / lamb tagine).
    The Act III "find this shape, not this keyword" beat, mirroring the fraud-ring anchor.
    """
    from .data import load_hero_texts
    from .extract import extract_recipe
    from .graph import build_graph

    recipes = [extract_recipe(text) for _title, text in load_hero_texts()]
    g = build_graph(recipes, normalise=True)

    shared = "ingredient:cumin"
    star = ["recipe:chicken handi", "recipe:egyptian fatteh", "recipe:lamb tagine"]
    star = [r for r in star if g.has_edge(r, shared)]  # keep only present + connected
    reveal = [
        {"label": "pattern", "nodes": [shared], "edges": []},
        {"label": "matches", "nodes": star, "edges": _edges_between(g, star, shared)},
    ]
    return to_graph_json(
        g,
        reveal=reveal,
        title="Exact subgraph match: the 'recipes sharing an ingredient' star around cumin",
    )


def _fixture_recipe_v3_subs() -> dict:
    """4. recipe-v3-subs — enriched graph + a staged shortest-path reveal."""
    from .data import load_hero_texts
    from .extract import extract_recipe
    from .graph import build_graph_v3
    from .algos import explain_path

    recipes = [extract_recipe(text) for _title, text in load_hero_texts()]
    g = build_graph_v3(recipes, with_substitutions=True)

    # The notebook's headline pair (buttermilk -> milk) is a single SUBSTITUTES_FOR
    # hop, which makes a thin two-frame reveal. yoghurt -> milk gives a clean 2-hop
    # chain entirely through SUBSTITUTES_FOR (yoghurt -> buttermilk -> milk), so the
    # staged reveal actually walks. (buttermilk -> milk is the same final edge.)
    src, tgt = "ingredient:yoghurt", "ingredient:milk"
    path = explain_path(g, src, tgt)
    reveal = _reveal_for_path(g, path, "SUBSTITUTES_FOR")
    return to_graph_json(
        g,
        reveal=reveal,
        title="v3 SUBSTITUTES_FOR: shortest path yoghurt -> milk (a richer 2-hop walk than buttermilk -> milk)",
    )


def _fixture_caselaw_landmark() -> dict:
    """5. caselaw-landmark — a small hand-built citation graph (real path + authorities)."""
    ppr = json.loads((_JUDGEMENTS_DIR / "ppr_landmark.json").read_text())
    hits = json.loads((_JUDGEMENTS_DIR / "hits_landmarks.json").read_text())

    citation_path = ppr["citation_path"]  # [Cheever, Estelle, Miranda]
    landmark = ppr["landmark"]            # Miranda v. Arizona (1966)
    # ~6 other HITS authorities (excluding Miranda itself) as surrounding context.
    context = [a["case"] for a in hits["authorities"] if a["case"] != landmark][:6]

    g = nx.MultiDiGraph()

    def add_case(name: str) -> str:
        cid = _case_id(name)
        if cid not in g:
            g.add_node(cid, kind="case", label=name)
        return cid

    for name in citation_path + context:
        add_case(name)

    # the two REAL precedent-chain edges: Cheever -> Estelle -> Miranda.
    for u, v in zip(citation_path, citation_path[1:]):
        g.add_edge(_case_id(u), _case_id(v), key="CITES", rel="CITES")

    # surrounding context authorities -> the landmark (illustrative citation edges).
    landmark_id = _case_id(landmark)
    for name in context:
        g.add_edge(_case_id(name), landmark_id, key="CITES", rel="CITES")

    # cumulative reveal walking the real precedent chain seed -> landmark.
    seed = citation_path[0]
    reveal = [{"label": "seed", "nodes": [_case_id(seed)], "edges": []}]
    for u, v in zip(citation_path, citation_path[1:]):
        reveal.append(
            {"label": "path", "nodes": [_case_id(v)], "edges": [[_case_id(u), _case_id(v), "CITES"]]}
        )

    return to_graph_json(
        g,
        reveal=reveal,
        title=(
            "Citation chain Kansas v. Cheever -> Estelle v. Smith -> Miranda v. Arizona. "
            "Surrounding citation edges are illustrative; the path + authorities are real "
            "(CourtListener/SCDB)."
        ),
    )


# --- Rung 3 (entity matching) before/after — the LEGIBLE small-N gallery -----
#
# The full-graph entity-match before/after collapses 112 -> 102 ingredient nodes across
# ~250 — a real improvement that is invisible to the eye in a zoomed-out hairball (the
# resolved 'after' is computed live in prez_act2). These builders make the *same* improvement
# legible by (a) using a small hand-picked recipe subset and (b) projecting to a
# "drift focus": recipes + only the ingredient nodes whose canonical has more than
# one surface form across the hero set, dropping steps / techniques / singleton
# staples. The before view then shows near-duplicate nodes ("Cumin" / "Cumin
# seeds", "Garlic Clove" / "Minced Garlic" / "garlic") that the after view
# collapses onto shared canonical hubs the recipes visibly converge on.
#
# NOTE on the merge: build_graph's node id lowercases (nid -> name.lower()), so
# case-only variants ("Garlic" / "garlic") ALREADY share a node before resolution.
# The genuine, honest collapses these fixtures show are the multi-word surface
# forms: Garlic Clove / Minced Garlic / garlic -> garlic, Cumin / Cumin seeds ->
# cumin, Oil / vegetable oil -> oil, Tomato Puree -> tomato paste, etc.

# Curated subsets, smallest first. Each is chosen so the recipes share several
# ingredients via DIFFERENT surface forms (the whole point of rung 3).
_RUNG3_SUBSETS = {
    "trio": ["Egyptian Fatteh", "Lamb Tagine", "Chicken Handi"],
    "quartet": ["Egyptian Fatteh", "Lamb Tagine", "Chicken Handi", "French Onion Soup"],
    "garlic5": [
        "Egyptian Fatteh", "Beef Lo Mein", "Cajun Spiced Fish Tacos",
        "Chicken Handi", "Teriyaki Chicken Casserole",
    ],
    "big8": [
        "Egyptian Fatteh", "Beef Lo Mein", "Cajun Spiced Fish Tacos",
        "Chicken Handi", "Teriyaki Chicken Casserole", "Lamb Tagine",
        "French Onion Soup", "Spaghetti Bolognese",
    ],
}


def _drifting_canonicals() -> set[str]:
    """Canonical ingredient names that appear under >1 surface form across the
    full hero set — i.e. the ingredients entity matching actually merges."""
    from collections import defaultdict
    from .data import load_hero_texts
    from .extract import extract_recipe
    from . import resolve

    surfaces: dict[str, set[str]] = defaultdict(set)
    for _title, text in load_hero_texts():
        for ing in extract_recipe(text).ingredients:
            surfaces[resolve.normalise_ingredient(ing.name)].add(ing.name.strip())
    return {canon for canon, forms in surfaces.items() if len(forms) > 1}


def _recipes_by_title(titles: list[str]):
    """Extract the named hero recipes (offline replay), preserving `titles` order."""
    from .data import load_hero_texts
    from .extract import extract_recipe

    by_title = {extract_recipe(text).title: extract_recipe(text) for _t, text in load_hero_texts()}
    missing = [t for t in titles if t not in by_title]
    if missing:
        raise KeyError(f"unknown recipe title(s): {missing}; have {sorted(by_title)}")
    return [by_title[t] for t in titles]


def drift_focus_graph(titles: list[str], normalise: bool, drift: set[str] | None = None):
    """Build the rung-3 'drift focus' projection for a recipe subset.

    Keeps every recipe node plus only the ingredient nodes whose canonical is in
    ``drift`` (the set that actually merges), with their CONTAINS edges. Steps,
    techniques, and non-drifting singleton ingredients are dropped so the
    surface-form duplicates (before) and the shared canonical hubs (after) are the
    whole picture. ``normalise`` toggles before (False) / after (True).
    """
    import networkx as nx
    from . import resolve
    from .graph import build_graph

    if drift is None:
        drift = _drifting_canonicals()

    g = build_graph(_recipes_by_title(titles), normalise=normalise)
    h = nx.MultiDiGraph()
    for n, d in g.nodes(data=True):
        if d.get("kind") == "recipe":
            h.add_node(n, **d)
        elif d.get("kind") == "ingredient" and resolve.normalise_ingredient(d.get("label", "")) in drift:
            h.add_node(n, **d)
    for u, v, k, d in g.edges(keys=True, data=True):
        if d.get("rel") == "CONTAINS" and u in h and v in h:
            h.add_edge(u, v, key=k, **d)
    # drop any drift-ingredient node that ended up with no recipe pointing at it
    h.remove_nodes_from(
        [n for n, d in list(h.nodes(data=True)) if d.get("kind") == "ingredient" and h.in_degree(n) == 0]
    )
    return h


def _rung3_fixture(name_titles: tuple[str, list[str]], normalise: bool, drift: set[str]) -> dict:
    label, titles = name_titles
    h = drift_focus_graph(titles, normalise=normalise, drift=drift)
    ings = sum(1 for _n, d in h.nodes(data=True) if d.get("kind") == "ingredient")
    when = "after entity matching" if normalise else "before entity matching"
    return to_graph_json(
        h,
        title=(
            f"Rung 3 {when} — {len(titles)} recipes, ingredient-drift focus: "
            f"{ings} ingredient node{'s' if ings != 1 else ''} "
            f"({'shared canonical hubs' if normalise else 'near-duplicate surface forms'})"
        ),
    )


# The chosen subset for the canonical, polished rung-3 before/after pair. Public
# so the Act II notebook can build the same legible before/after live.
RUNG3_RECIPES = _RUNG3_SUBSETS["garlic5"]
_RUNG3_CANONICAL = RUNG3_RECIPES


def _recipe_ring(titles_present: list[str], radius: float = 300.0) -> dict[str, tuple[float, float]]:
    """Pin the recipe nodes evenly on a circle (deterministic, id-sorted).

    Identical positions are used for BOTH the before and after fixtures so the
    recipes form a stable frame; the renderer then force-places the ingredient
    nodes around that frame (duplicate spellings settle near their one recipe in
    'before'; shared hubs get pulled to the centre in 'after'). Only recipes are
    pinned — ingredients are left free so the collapse is force-natural, not faked.
    """
    import math

    ids = sorted(titles_present)  # node ids, e.g. "recipe:beef lo mein"
    n = len(ids)
    layout: dict[str, tuple[float, float]] = {}
    for i, rid in enumerate(ids):
        ang = 2 * math.pi * i / n - math.pi / 2  # first recipe at top
        layout[rid] = (radius * math.cos(ang), radius * math.sin(ang))
    return layout


def _rung3_reveal(h, normalise: bool) -> list[dict]:
    """One highlight step: glow the recipes + the nodes that carry the lesson.

    before -> the near-duplicate surface forms that *should* be one (any canonical
    represented by >1 ingredient node in this subset). after -> the shared hubs
    (ingredient nodes ≥2 recipes now point at). Staples fade to context either way.
    """
    from collections import defaultdict
    from . import resolve

    recipes = [n for n, d in h.nodes(data=True) if d.get("kind") == "recipe"]
    if normalise:
        focus = [
            n for n, d in h.nodes(data=True)
            if d.get("kind") == "ingredient" and h.in_degree(n) >= 2
        ]
    else:
        by_canon: dict[str, list[str]] = defaultdict(list)
        for n, d in h.nodes(data=True):
            if d.get("kind") == "ingredient":
                by_canon[resolve.normalise_ingredient(d.get("label", ""))].append(n)
        focus = [n for group in by_canon.values() if len(group) > 1 for n in group]

    edges = []
    for r in recipes:
        for f in focus:
            if h.has_edge(r, f):
                edges.append([r, f, next(iter(h[r][f]))])
    label = "shared hubs" if normalise else "near-duplicates"
    return [{"label": label, "nodes": recipes + focus, "edges": edges}]


def _rung3_collapsed_reveal(h) -> list[dict]:
    """One highlight step on the AFTER graph: light only the canonical nodes that
    *absorbed* more than one surface form — the collapse targets.

    Distinct from ``_rung3_reveal``'s "shared hubs" (every in_degree ≥ 2 hub,
    which also catches staples that never had a spelling problem). Here we replay
    the before-graph grouping: a canonical counts only if >1 distinct surface form
    normalised onto it (garlic clove / minced garlic / garlic → garlic, etc.). The
    in-between frame answers "which nodes did the duplicates collapse onto?".
    """
    from collections import defaultdict
    from . import resolve

    # Replay the before subset to learn which canonicals had multiple spellings.
    drift = _drifting_canonicals()
    before = drift_focus_graph(_RUNG3_CANONICAL, normalise=False, drift=drift)
    by_canon: dict[str, set[str]] = defaultdict(set)
    for _n, d in before.nodes(data=True):
        if d.get("kind") == "ingredient":
            by_canon[resolve.normalise_ingredient(d.get("label", ""))].add(d.get("label", ""))
    collapsed = {canon for canon, forms in by_canon.items() if len(forms) > 1}

    focus = [
        n for n, d in h.nodes(data=True)
        if d.get("kind") == "ingredient"
        and resolve.normalise_ingredient(d.get("label", "")) in collapsed
    ]
    # Light only the collapsed ingredient hubs — no recipe nodes, and no edges
    # (lighting an edge would auto-light its recipe endpoint).
    return [{"label": "collapsed onto one hub", "nodes": focus, "edges": []}]


def _fixture_rung3_collapsed() -> dict:
    """The in-between frame for the rung-3 slide: the AFTER graph (collapsed,
    canonical), but lighting only the hubs that absorbed duplicate spellings —
    so the eye lands on exactly what the entity match merged."""
    drift = _drifting_canonicals()
    h = drift_focus_graph(_RUNG3_CANONICAL, normalise=True, drift=drift)
    recipes = [n for n, d in h.nodes(data=True) if d.get("kind") == "recipe"]
    layout = _recipe_ring(recipes)
    reveal = _rung3_collapsed_reveal(h)
    lit = len(reveal[0]["nodes"])
    return to_graph_json(
        h,
        layout=layout,
        reveal=reveal,
        title=(
            f"Rung 3 — collapsed: {lit} canonical hubs lit, "
            "each absorbing the near-duplicate spellings that merged onto it"
        ),
    )


def _fixture_rung3(normalise: bool) -> dict:
    """The canonical, polished rung-3 before/after fixture (garlic5 subset).

    Pinned recipe ring (shared across before/after) + drift-focus projection +
    a highlight reveal. ``normalise`` picks before (False) / after (True)."""
    drift = _drifting_canonicals()
    h = drift_focus_graph(_RUNG3_CANONICAL, normalise=normalise, drift=drift)
    recipes = [n for n, d in h.nodes(data=True) if d.get("kind") == "recipe"]
    layout = _recipe_ring(recipes)
    reveal = _rung3_reveal(h, normalise)
    ings = sum(1 for _n, d in h.nodes(data=True) if d.get("kind") == "ingredient")
    when = "after entity matching" if normalise else "before entity matching"
    detail = (
        "recipes share canonical ingredient hubs"
        if normalise
        else "every recipe brings its own spelling — duplicate ingredient nodes"
    )
    return to_graph_json(
        h,
        layout=layout,
        reveal=reveal,
        title=f"Rung 3 — {when}: {ings} ingredient nodes, {detail}",
    )


def write_rung3_gallery(out_dir="demos/viz/fixtures") -> list[str]:
    """Write the rung-3 before/after gallery: `rung3-<subset>-{before,after}.json`.

    Separate from ``write_fixtures`` because these are CANDIDATES for the rung-3
    'show the improvement' slide — render them, pick the most legible size, then
    promote the winner into ``_FIXTURES``. Offline (replay), stdlib + networkx.
    """
    out = Path(out_dir)
    if not out.is_absolute():
        out = _DEMOS_DIR.parent / out_dir
    out.mkdir(parents=True, exist_ok=True)

    drift = _drifting_canonicals()
    paths: list[str] = []
    for subset, titles in _RUNG3_SUBSETS.items():
        for when, normalise in (("before", False), ("after", True)):
            data = _rung3_fixture((subset, titles), normalise=normalise, drift=drift)
            path = out / f"rung3-{subset}-{when}.json"
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            paths.append(str(path))
    return paths


def _fixture_roadmap() -> dict:
    """0. roadmap — the "what's coming" overview graph for slide three.

    A hand-built agenda tree: one ``talk`` root, three ``part`` nodes (the three
    acts of the talk), and the ``beat`` slides hanging off each part. Fully pinned
    (every node carries x/y) so the layout is hand-authored and stable — left→right,
    root on the left, each part's beats clustered to its right. Static (no reveal):
    it's a map, not an animation. Kinds: talk (purple hub) / part (blue) / beat (teal).

    The beats mirror the section structure in slidev/slides.md, so if the deck's
    acts change, edit PARTS below and re-run write_fixtures().
    """
    import networkx as nx

    # (part_id, part_label, spine-line, [(beat_id, beat_label, optional tag), ...])
    parts = [
        (
            "graph-basics",
            "The basics",
            "bad graph — the seductive mess",
            [
                ("what-is-a-graph", "What is a graph", ""),
                ("extract-basic", "Extract a basic graph", ""),
                ("teardown", "Tear it down", ""),
            ],
        ),
        (
            "building-better-graphs",
            "Better graphs",
            "good graph — the climb",
            [
                ("shape", "Pydantic for shape", ""),
                ("ontology", "A shape isn't an ontology", ""),
                ("entity-matching", "Entity matching", ""),
            ],
        ),
        (
            "graph-algorithms",
            "Graph algorithms",
            "payoff — what a good graph unlocks",
            [
                ("ppr", "Personalised PageRank", "smarter"),
                ("shortest-path", "Shortest path", "reliable"),
                ("subgraph", "Subgraph matching", "cheaper"),
            ],
        ),
    ]

    g = nx.MultiDiGraph()
    layout: dict[str, tuple[float, float]] = {}

    root = "talk:root"
    g.add_node(root, kind="talk", label="The talk", subtitle="smarter · cheaper · reliable")
    layout[root] = (-560.0, 0.0)

    # three parts stacked in a column; each part's beats fan out to its right so
    # the three subtrees stay spatially separated (minimal edge crossings).
    part_y = {-1: -280.0, 0: 0.0, 1: 280.0}
    for col, (pid, plabel, note, beats) in zip((-1, 0, 1), parts):
        part_node = f"part:{pid}"
        g.add_node(part_node, kind="part", label=plabel, note=note)
        layout[part_node] = (-200.0, part_y[col])
        g.add_edge(root, part_node, key=0, rel="PART")

        # 3 beats centred vertically on their part (rows 80px apart).
        for row, (bid, blabel, tag) in zip((-1, 0, 1), beats):
            beat_node = f"beat:{bid}"
            attrs = {"kind": "beat", "label": blabel}
            if tag:
                attrs["tag"] = tag
            g.add_node(beat_node, **attrs)
            layout[beat_node] = (180.0, part_y[col] + row * 80.0)
            g.add_edge(part_node, beat_node, key=0, rel="COVERS")

    data = to_graph_json(
        g,
        layout=layout,
        title="What's coming — three parts: bad graph -> good graph -> payoff",
    )
    # Agenda labels are full slide titles ("A shape isn't an ontology"), longer than
    # the default 22-char clip — raise maxChars so they render intact on this one graph.
    data["params"] = {"labels": {"maxChars": 40}}
    return data


def _fixture_method() -> dict:
    """0b. method — the per-step working method, drawn as a left->right flow.

    Companion to the roadmap on slide 3: how every step of the talk runs —
    open with a ``principle``, work it in ``code`` (easy recipe examples), then
    point at real-world ``example`` analogues. A 3-node hand-pinned chain
    (amber -> blue -> green), static. Same fixture conventions as _fixture_roadmap.
    """
    import networkx as nx

    # (node_id, kind, label, note, x)
    steps = [
        ("principle", "principle", "Principle", "open with the idea", -320.0),
        ("code", "code", "Code", "easy recipe examples", 0.0),
        ("example", "example", "Examples", "real-world analogues", 320.0),
    ]

    g = nx.MultiDiGraph()
    layout: dict[str, tuple[float, float]] = {}
    for nid, kind, label, note, x in steps:
        node = f"method:{nid}"
        g.add_node(node, kind=kind, label=label, note=note)
        layout[node] = (x, 0.0)

    g.add_edge("method:principle", "method:code", key=0, rel="THEN")
    g.add_edge("method:code", "method:example", key=0, rel="THEN")

    data = to_graph_json(
        g,
        layout=layout,
        title="Each step: principle -> code (recipes) -> real-world examples",
    )
    # The graph IS the direction (principle -> code -> examples). Arrowheads are
    # always drawn (marker-end), but the resting edge/arrow is muted by default —
    # brighten + thicken so the flow reads at a glance.
    data["params"] = {
        "labels": {"maxChars": 40},
        "edges": {"rest": "#aab0ba", "width": 2.5, "arrowScale": 1.8},
    }
    return data


def _toy_recipe():
    """A tiny hand-built recipe — the toy behind the two schema-first 'shape' slides.

    Deliberately small (5 ingredients / 3 steps / 3 techniques) so the Pydantic model
    and the rendered graph are instantly comprehensible *side by side*: a recipe hub,
    its ingredients, the steps that use them, and the technique each step applies.
    """
    from .extract import Ingredient, Recipe, Step

    return Recipe(
        title="Garlic Butter Pasta",
        ingredients=[
            Ingredient(name="spaghetti", quantity=200, unit="g"),
            Ingredient(name="garlic", quantity=3, unit="clove"),
            Ingredient(name="butter", quantity=2, unit="tbsp"),
            Ingredient(name="parmesan", quantity=30, unit="g"),
            Ingredient(name="parsley", quantity=1, unit="tbsp"),
        ],
        steps=[
            Step(text="Boil the spaghetti until al dente.", technique="boil", uses=["spaghetti"]),
            Step(text="Melt the butter, then saute the garlic.", technique="saute", uses=["butter", "garlic"]),
            Step(
                text="Toss the pasta in the garlic butter; finish with parmesan and parsley.",
                technique="toss",
                uses=["spaghetti", "parmesan", "parsley"],
            ),
        ],
    )


def _fixture_recipe_shape() -> dict:
    """Schema-first slide A: the toy recipe with ONLY recipe + ingredient nodes.

    Matches the simplified Pydantic on the slide (just ``Recipe`` + ``Ingredient``)
    so the code and the picture line up one-to-one — a recipe hub with its ingredients
    hanging off it, nothing else. Steps/techniques arrive on the next (build-up) slide.
    """
    import networkx as nx
    from .graph import build_graph

    g = build_graph([_toy_recipe()], normalise=False)
    h = nx.MultiDiGraph()
    for n, d in g.nodes(data=True):
        if d.get("kind") in ("recipe", "ingredient"):
            h.add_node(n, **d)
    for u, v, k, d in g.edges(keys=True, data=True):
        if d.get("rel") == "CONTAINS" and u in h and v in h:
            h.add_edge(u, v, key=k, **d)
    return to_graph_json(h, title="Schema-first (shape): a recipe and its ingredients")


def _fixture_recipe_build() -> dict:
    """Schema-first slide B: the SAME toy recipe, progressively disclosed.

    One reveal step per layer of the schema — ingredients, then steps, then techniques.
    Clicking through the slide grows the graph from 'a recipe and its ingredients'
    (slide A) into the full shape the richer Pydantic model produces. No code on the
    slide; the graph itself tells the story. Cumulative reveal, so each click lights
    the next layer while the earlier ones stay lit.
    """
    from .graph import build_graph

    g = build_graph([_toy_recipe()], normalise=False)

    def nodes_of(kind: str) -> list[str]:
        return [n for n, d in g.nodes(data=True) if d.get("kind") == kind]

    def edges_of(rel: str) -> list[list]:
        return [[u, v, k] for u, v, k, d in g.edges(keys=True, data=True) if d.get("rel") == rel]

    reveal = [
        {
            "label": "ingredients",
            "nodes": nodes_of("recipe") + nodes_of("ingredient"),
            "edges": edges_of("CONTAINS"),
        },
        # steps fan off the recipe (HAS_STEP) and reach back into the ingredients they USE.
        {"label": "steps", "nodes": nodes_of("step"), "edges": edges_of("HAS_STEP") + edges_of("USES")},
        {"label": "techniques", "nodes": nodes_of("technique"), "edges": edges_of("TECHNIQUE")},
    ]
    return to_graph_json(
        g,
        reveal=reveal,
        title="Schema-first (shape), progressively disclosed: ingredients -> steps -> techniques",
    )


def _fixture_drift_at_scale() -> dict:
    """6. drift-at-scale — a large typed graph (all recipes) to stress the SVG renderer."""
    from .data import load_hero_texts
    from .extract import extract_recipe
    from .graph import build_graph

    recipes = [extract_recipe(text) for _title, text in load_hero_texts()]
    g = build_graph(recipes, normalise=False)
    n, m = g.number_of_nodes(), g.number_of_edges()
    return to_graph_json(
        g,
        title=f"Drift at scale: {n} nodes / {m} edges (all hero recipes, normalise=False) — stress test",
    )


# name -> builder. Order is the talk's narrative order:
#   Act I   v0 mess            -> naive-v0
#   Act II  shape (v1)         -> recipe-single, recipe-multi-drift
#           ontology (v2)      -> recipe-v2
#           entity match (v3)  -> rung3-before, rung3-collapsed, rung3-after
#   Act III payoff             -> recipe-ppr, recipe-subgraph, recipe-v3-subs, caselaw-landmark
#   stress test                -> drift-at-scale
_FIXTURES = {
    "roadmap": _fixture_roadmap,
    "method": _fixture_method,
    "naive-v0": _fixture_naive_v0,
    "recipe-single": _fixture_recipe_single,
    # toy single-recipe pair for the two schema-first 'shape' slides (shape + build-up)
    "recipe-shape": _fixture_recipe_shape,
    "recipe-build": _fixture_recipe_build,
    "recipe-multi-drift": _fixture_recipe_multi_drift,
    "recipe-v2": _fixture_recipe_v2,
    # legible small-N before/after for the rung-3 "show the improvement" slide
    "rung3-before": lambda: _fixture_rung3(normalise=False),
    "rung3-collapsed": _fixture_rung3_collapsed,
    "rung3-after": lambda: _fixture_rung3(normalise=True),
    "recipe-ppr": _fixture_recipe_ppr,
    "recipe-subgraph": _fixture_recipe_subgraph,
    "recipe-v3-subs": _fixture_recipe_v3_subs,
    "caselaw-landmark": _fixture_caselaw_landmark,
    "drift-at-scale": _fixture_drift_at_scale,
}


def write_fixtures(out_dir="demos/viz/fixtures") -> list[str]:
    """Build every fixture and write ``<name>.json`` into ``out_dir``.

    ``out_dir`` is resolved relative to the repo root (the parent of ``demos/``) when
    given as the default ``demos/...`` path, so it works regardless of cwd. Returns
    the list of written file paths.
    """
    out = Path(out_dir)
    if not out.is_absolute():
        # default "demos/viz/fixtures" is relative to the repo root (parent of demos/).
        out = _DEMOS_DIR.parent / out_dir
    out.mkdir(parents=True, exist_ok=True)

    paths: list[str] = []
    for name, build in _FIXTURES.items():
        data = build()
        path = out / f"{name}.json"
        path.write_text(
            json.dumps(data, indent=2, sort_keys=False, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        paths.append(str(path))
    return paths
