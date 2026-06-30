"""[Act I] Render a small recipe graph as a clean matplotlib figure.

The "look, a graph" payoff: take a `nx.MultiDiGraph` from `graph.build_graph`
and draw it legibly — nodes coloured by `kind`, short labels, edge `rel` labels.

matplotlib only (deterministic, already a dep). No pyvis, no network.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # headless: render to file without a display

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import networkx as nx

# colour + draw order per node kind. recipe is the hub, so it reads warmest.
_KIND_STYLE: dict[str, dict] = {
    "recipe": {"color": "#e4572e", "size": 1700},
    "ingredient": {"color": "#4c9f70", "size": 1100},
    "step": {"color": "#3a7ca5", "size": 1100},
    "technique": {"color": "#d4a017", "size": 900},
}
_DEFAULT_STYLE = {"color": "#9aa0a6", "size": 900}
_LAYOUT_SEED = 7  # deterministic spring layout


def _short(label: str, width: int = 22) -> str:
    """Truncate a node label to keep the figure legible."""
    label = (label or "").strip()
    if len(label) <= width:
        return label
    return label[: width - 1].rstrip() + "…"


def render_graph(g: nx.Graph, path: str | None = None, ax=None):
    """Draw a recipe graph built by `graph.build_graph`.

    Nodes are coloured by their ``kind`` attribute with a legend; labels use the
    node ``label`` attribute (truncated); edges are labelled with their ``rel``.

    Args:
        g: a networkx graph with ``kind``/``label`` node attrs and ``rel`` edge attrs.
        path: if given, save a PNG (tight bbox) and return ``(fig, ax)``.
        ax: optional axes to draw into; otherwise a new figure is created.

    Returns:
        ``(fig, ax)``.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(11, 8))
    else:
        fig = ax.figure

    # deterministic layout — fixed seed so the slide looks the same every run.
    # k scales with graph size so larger graphs spread out and don't overlap.
    k = max(0.9, 2.2 / max(len(g), 1) ** 0.5)
    pos = nx.spring_layout(g, seed=_LAYOUT_SEED, k=k, iterations=300)

    # group nodes by kind so each colour gets one legend entry.
    kinds_present: list[str] = []
    for kind, style in list(_KIND_STYLE.items()) + [("_other", _DEFAULT_STYLE)]:
        if kind == "_other":
            nodes = [
                n for n, d in g.nodes(data=True) if d.get("kind") not in _KIND_STYLE
            ]
        else:
            nodes = [n for n, d in g.nodes(data=True) if d.get("kind") == kind]
        if not nodes:
            continue
        kinds_present.append(kind)
        nx.draw_networkx_nodes(
            g,
            pos,
            nodelist=nodes,
            node_color=style["color"],
            node_size=style["size"],
            edgecolors="white",
            linewidths=1.5,
            ax=ax,
        )

    nx.draw_networkx_edges(
        g,
        pos,
        edge_color="#b0b4b8",
        width=1.3,
        arrows=True,
        arrowsize=12,
        node_size=1300,
        connectionstyle="arc3,rad=0.06",
        ax=ax,
    )

    labels = {n: _short(d.get("label", n)) for n, d in g.nodes(data=True)}
    nx.draw_networkx_labels(g, pos, labels=labels, font_size=8, ax=ax)

    # edge relationship labels — dedupe per (u, v) so parallel edges don't pile up.
    edge_labels: dict[tuple, str] = {}
    if g.is_multigraph():
        for u, v, d in g.edges(data=True):
            rel = d.get("rel")
            if not rel:
                continue
            edge_labels.setdefault((u, v), rel)
    else:
        edge_labels = {
            (u, v): d["rel"] for u, v, d in g.edges(data=True) if d.get("rel")
        }
    nx.draw_networkx_edge_labels(
        g,
        pos,
        edge_labels=edge_labels,
        font_size=6.5,
        font_color="#555a5f",
        rotate=False,
        bbox={"boxstyle": "round,pad=0.1", "fc": "white", "ec": "none", "alpha": 0.7},
        ax=ax,
    )

    # legend keyed on the kinds actually drawn.
    handles = [
        mpatches.Patch(
            color=(_KIND_STYLE.get(k, _DEFAULT_STYLE))["color"],
            label=("other" if k == "_other" else k),
        )
        for k in kinds_present
    ]
    ax.legend(handles=handles, loc="upper left", frameon=True, fontsize=9)

    ax.set_axis_off()
    ax.margins(0.08)

    if path is not None:
        fig.savefig(path, dpi=150, bbox_inches="tight")
    return fig, ax
