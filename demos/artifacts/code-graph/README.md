# code-graph — the eShop examples (REAL)

The real-world material behind the talk's **shortest path** and **exact subgraph matching**
examples. Nothing here runs a pipeline; the graph and figures are committed so you can tour them
offline (Act III notebook, sections 2 and 3).

**Source codebase:** Microsoft's public [eShopOnWeb](https://github.com/dotnet-architecture/eShopOnWeb)
reference application (commit `4da8212`), compiled with Roslyn into a typed `networkx.MultiDiGraph`
of **955 nodes / 2,196 edges**. Node kinds: `class`, `interface`, `method`, `ctor`, `property`, …
Edge relationships: `calls`, `contains`, `implements`, `extends`, `di_binds`, `route_handles`, …

## Files

| File | What |
|---|---|
| `eshop-code-graph.graphml` | The full typed graph. Load with `networkx.read_graphml`; opens in Gephi too. |
| `shortest_path.png` | *"Why does editing `Basket..ctor` break checkout?"* — the 4-hop `calls` chain from `CheckoutModel.OnPost` down to the constructor. |
| `decorator_subgraph.png` | The decorator motif found by VF2 subgraph matching: `CachedCatalogViewModelService` wraps `CatalogViewModelService`, both implementing `ICatalogViewModelService`. |
| `bench.json` | Both results with their completeness tags and the published work they sit alongside. |

## What the results say

- **Shortest path** — the path *is* the explanation: a four-hop `calls` chain you can hand an agent
  as context instead of making it discover the intermediate symbols itself. The measured
  tool-call saving from doing so is in `../proving-ground/`.
- **Subgraph match** — the decorator shape is found **all-and-only** against the compiler's view of
  the codebase (precision 1.0 / recall 1.0): exactly one match, and it is the real one. A
  "god-class" anti-pattern search (fan-out ≥ 20) finds **none** — an evidenced negative; the busiest
  type is `BasketViewModelService` at 13.

## Read this before you quote a number

Every edge carries a `completeness` tag. Structural edges (`implements` / `extends` / `contains` /
`project_depends`) are `definitively-absent` when missing — the compiler saw the whole hierarchy.
Behavioural edges (`calls` / `di_binds` / `route_handles`) are `blind-spot-possible`: delegates,
reflection, interface dispatch and DI wiring can hide a call from the symbol finder. So a
*"no path"* answer is trustworthy for the first group and only *probably* true for the second.

Related published work: **LocAgent** (ACL 2025) for graph-guided code localisation; **Tsantalis et
al.** (IEEE TSE 2006) for design-pattern detection by graph similarity; **Joern / Code Property
Graphs** (IEEE S&P 2014) and **CodeQL** for pattern queries over code. Links in the pack's
`FURTHER-READING.md`.
