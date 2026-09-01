"""[HOW · Act I] Extracted records -> NetworkX graph.

Node types: Recipe, Ingredient, Step, Technique.
Edge types: CONTAINS {qty, unit}, HAS_STEP {order}, USES, TECHNIQUE.

In-memory MultiDiGraph: zero infra, and PPR / shortest-path / VF2 all run on it
directly (see algos.py). Node ids are typed strings ("ingredient:flour") so the graph is
human-readable in the notebook.
"""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import yaml

from . import resolve
from .extract import Recipe

_ONTOLOGY_DIR = Path(__file__).resolve().parent.parent / "data" / "ontology"


def nid(kind: str, name: str) -> str:
    return f"{kind}:{name.strip().lower()}"


def build_graph(recipes: list[Recipe], normalise: bool = False) -> nx.MultiDiGraph:
    """Build the recipe graph from a list of extracted recipes.

    ``normalise=False`` (v1, the default) keys ingredient nodes on their *raw*
    surface names — intentionally unmatched, so Act II has duplicate nodes to
    collapse. ``normalise=True`` keys them on ``resolve.normalise_ingredient``
    so a recipe's "plain flour" and a substitution's "flour" share one node (used by
    ``build_graph_v3`` for the Act III graph).
    """

    def canon(name: str) -> str:
        return resolve.normalise_ingredient(name) if normalise else name.strip()

    def ensure_ingredient(name: str) -> str:
        """Add the ingredient node *with attributes* and return its id.

        Done before every edge so a step that USES an ingredient missing from the
        ingredient list can't create an attribute-less ghost node."""
        cname = canon(name)
        iid = nid("ingredient", cname)
        if iid not in g:
            g.add_node(iid, kind="ingredient", label=cname)
        return iid

    g = nx.MultiDiGraph()
    for r in recipes:
        rid = nid("recipe", r.title)
        g.add_node(rid, kind="recipe", label=r.title)

        for ing in r.ingredients:
            iid = ensure_ingredient(ing.name)
            g.add_edge(rid, iid, key="CONTAINS", rel="CONTAINS", qty=ing.quantity, unit=ing.unit)

        for order, step in enumerate(r.steps):
            sid = nid("step", f"{r.title}#{order}")
            g.add_node(sid, kind="step", label=step.text[:48])
            g.add_edge(rid, sid, key="HAS_STEP", rel="HAS_STEP", order=order)
            if step.technique:
                tid = nid("technique", step.technique)
                g.add_node(tid, kind="technique", label=step.technique)
                g.add_edge(sid, tid, key="TECHNIQUE", rel="TECHNIQUE")
            for ing_name in step.uses:
                g.add_edge(sid, ensure_ingredient(ing_name), key="USES", rel="USES")
    return g


def _load_substitutions() -> dict:
    """Load the curated substitution table (data/ontology/substitutions.yaml)."""
    path = _ONTOLOGY_DIR / "substitutions.yaml"
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def add_substitution_edges(g: nx.MultiDiGraph, table: dict | None = None) -> nx.MultiDiGraph:
    """Add Ingredient-[SUBSTITUTES_FOR]->Ingredient edges from the curated table.

    Names are canonicalised with ``resolve.normalise_ingredient`` so edges connect
    to the same ingredient nodes ``build_graph`` creates. Substitute nodes absent
    from the graph are added (kind="ingredient") so the path is always traversable.
    The optional ``plus`` annotation (e.g. milk *plus* lemon juice) rides on the edge.
    Mutates ``g`` in place and returns it.
    """
    if table is None:
        table = _load_substitutions()

    def _ensure_node(canon: str) -> str:
        iid = nid("ingredient", canon)
        if iid not in g:
            g.add_node(iid, kind="ingredient", label=canon)
        return iid

    for src_name, subs in (table or {}).items():
        src_canon = resolve.normalise_ingredient(src_name)
        src_id = _ensure_node(src_canon)
        for sub in subs or []:
            to_canon = resolve.normalise_ingredient(sub["to"])
            if to_canon == src_canon:
                continue
            to_id = _ensure_node(to_canon)
            plus = sub.get("plus")
            g.add_edge(
                src_id, to_id, key="SUBSTITUTES_FOR", rel="SUBSTITUTES_FOR", plus=plus
            )
    return g


def build_graph_v3(recipes: list[Recipe], with_substitutions: bool = True) -> nx.MultiDiGraph:
    """Build the recipe graph and enrich it with SUBSTITUTES_FOR edges (v3-lite).

    Same structure as ``build_graph`` plus ingredient-to-ingredient substitution
    edges from ``data/ontology/substitutions.yaml`` — so a path through substitutions
    can be asked for ("no buttermilk -> milk + acid").

    Built with ``normalise=True`` so recipe ingredient nodes and substitution
    endpoints share canonical node ids (otherwise "plain flour" and "flour" would
    be two unconnected nodes and the substitution graph would float free).
    """
    g = build_graph(recipes, normalise=True)
    if with_substitutions:
        add_substitution_edges(g)
    return g


def nodes_of(g: nx.MultiDiGraph, kind: str) -> list[str]:
    """All node ids of a given kind — handy for seeding algorithms in the notebooks."""
    return [n for n, d in g.nodes(data=True) if d.get("kind") == kind]


def build_naive_graph(triples: list[dict]) -> nx.MultiDiGraph:
    """[v0] Build the naive graph from free-form triples (Act I).

    Every node is an untyped ``entity`` keyed on the *raw* surface string (no
    resolution), and every edge carries the *raw* predicate (no controlled
    vocabulary). The result is deliberately messy — duplicate near-identical nodes,
    inconsistent relation labels, no types — which is exactly what Act II fixes.
    Accepts ``extract.extract_freeform`` output (or any {subject,predicate,object}).
    """
    g = nx.MultiDiGraph()
    for t in triples:
        s = str(t.get("subject", "")).strip()
        o = str(t.get("object", "")).strip()
        p = str(t.get("predicate", "")).strip()
        if not s or not o:
            continue
        sid, oid = nid("entity", s), nid("entity", o)
        g.add_node(sid, kind="entity", label=s)
        g.add_node(oid, kind="entity", label=o)
        g.add_edge(sid, oid, rel=p or "related")  # auto key → parallel edges kept
    return g
