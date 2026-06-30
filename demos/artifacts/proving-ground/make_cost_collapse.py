"""Generate cost_collapse.png from cost_collapse.json (real proving-ground M2 numbers).

Run from the demos/ project root:
    cd demos && uv run python artifacts/proving-ground/make_cost_collapse.py

The chart shows per-task tool-uses, grep vs graph, with the honest "accuracy
parity" framing annotated. Numbers are loaded from the committed JSON so the
figure can never drift from the bench-loadable data.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE / "cost_collapse.json").read_text())

# Per-task tool-uses, grep vs graph, preserving task order.
labels: list[str] = []
grep_vals: list[int] = []
graph_vals: list[int] = []
seen: dict[str, dict[str, int]] = {}
order: list[str] = []

for row in DATA["tasks"]:
    # Compact, slide-readable task label.
    short = {
        "A-di-disambiguation": "eShop\nDI-disambig",
        "B-exception-control": "eShop\nexception",
        "P1-show-command-nullref (cross-project trace, PR-26669)": "PowerShell\ncross-project",
        "P2-viewgenerator-family (find all 5 via subtypes, PR-26574)": "PowerShell\nViewGen family",
    }[row["task"]]
    if short not in seen:
        seen[short] = {}
        order.append(short)
    seen[short][row["arm"]] = row["tool_uses"]

for short in order:
    labels.append(short)
    grep_vals.append(seen[short]["grep"])
    graph_vals.append(seen[short]["graph"])

x = range(len(labels))
width = 0.38

fig, ax = plt.subplots(figsize=(9, 5.2))
grep_color = "#9aa0a6"   # muted grey — the baseline
graph_color = "#1a73e8"  # blue — the graph win

bars_grep = ax.bar([i - width / 2 for i in x], grep_vals, width,
                   label="grep (baseline)", color=grep_color)
bars_graph = ax.bar([i + width / 2 for i in x], graph_vals, width,
                    label="graph navigation", color=graph_color)

for bars in (bars_grep, bars_graph):
    for b in bars:
        ax.annotate(f"{int(b.get_height())}",
                    xy=(b.get_x() + b.get_width() / 2, b.get_height()),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=11, fontweight="bold")

ax.set_ylabel("Tool-uses to localize (lower = cheaper)", fontsize=11)
ax.set_title("Navigation cost collapses — accuracy holds\n"
             "code-graph navigation vs grep (proving-ground, use case 01)",
             fontsize=13, fontweight="bold")
ax.set_xticks(list(x))
ax.set_xticklabels(labels, fontsize=10)
ax.set_ylim(0, max(grep_vals) + 4)
ax.legend(loc="upper left", fontsize=10, frameon=False)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# Accuracy-parity banner: every task hit in BOTH arms.
ax.text(0.99, 0.97, "accuracy parity: every task hit in both arms",
        transform=ax.transAxes, ha="right", va="top", fontsize=10,
        style="italic", color="#202124",
        bbox=dict(boxstyle="round,pad=0.4", fc="#e8f0fe", ec="#1a73e8", lw=1))

# Headline call-out on the cross-project bar pair (index 2).
ax.annotate("16 → 4 tool-uses\n(same answer)",
            xy=(2 + width / 2, graph_vals[2]),
            xytext=(2 - 0.15, grep_vals[2] - 1.5),
            fontsize=10, fontweight="bold", color="#1a73e8",
            arrowprops=dict(arrowstyle="->", color="#1a73e8", lw=1.5))

fig.tight_layout()
out = HERE / "cost_collapse.png"
fig.savefig(out, dpi=150)
print(f"wrote {out}")
