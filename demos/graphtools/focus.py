"""[HOW · Act II] The legible entity-matching before/after — a small recipe subset,
projected to just the ingredients that entity matching actually merges.

Across the whole hero set, entity matching collapses ~112 -> ~102 ingredient nodes: a
real improvement that is invisible in a 250-node hairball. ``drift_focus_graph`` makes
the same improvement visible by (a) using a hand-picked handful of recipes that name
the SAME pantry items differently and (b) keeping only the recipe nodes plus the
ingredient nodes whose canonical name has more than one surface form. The "before"
view shows near-duplicate nodes ("Cumin" / "Cumin seeds", "Garlic Clove" / "Minced
Garlic" / "garlic"); the "after" view collapses them onto shared canonical hubs.

Everything runs OFFLINE via the committed extraction cache.
"""

from __future__ import annotations

from collections import defaultdict

import networkx as nx

from . import resolve
from .data import load_hero_texts
from .extract import extract_recipe
from .graph import build_graph


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

    surfaces: dict[str, set[str]] = defaultdict(set)
    for _title, text in load_hero_texts():
        for ing in extract_recipe(text).ingredients:
            surfaces[resolve.normalise_ingredient(ing.name)].add(ing.name.strip())
    return {canon for canon, forms in surfaces.items() if len(forms) > 1}


def _recipes_by_title(titles: list[str]):
    """Extract the named hero recipes (offline replay), preserving `titles` order."""

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




# The chosen subset for the canonical before/after pair (used by the deck fixtures and
# the Act II notebook).
RUNG3_RECIPES = _RUNG3_SUBSETS["garlic5"]
