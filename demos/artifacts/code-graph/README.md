# code-graph — tour artifacts

Regenerate everything here with:

```bash
uv run python -m codegraph.bench      # bench.json + eshop-code-graph.graphml
uv run python -m codegraph.figures    # shortest_path.png + decorator_subgraph.png
```

Substrate: the proving-ground compiled index (`data/proving-ground/eshoponweb-member-index.json`,
eShopOnWeb @ `4da8212`) → a typed `networkx.MultiDiGraph` (**955 nodes / 2196 edges**).

## Files

| File | What |
|---|---|
| `eshop-code-graph.graphml` | The full typed graph (Gephi / slide visual). |
| `shortest_path.png` | **Beat 1** — the auditable *"why does editing `Basket..ctor` break checkout"* chain (4 hops, calls-only, repo-owned, `trust: possibly-blind`). |
| `decorator_subgraph.png` | **Beat 2** — the VF2 Decorator motif, found **all-and-only** on eShop. |
| `bench.json` | Both results + completeness tags + published anchors. |

## Headline results

- **Shortest-path** — presented via proving-ground **M4** (cited, not re-derived): claim-error
  **0.078 → 0.005** on sonnet-4-6 (tier-1 hallucinated citations → 0; citation P/R 1.0); **no lift**
  on opus-4-7 (0.1585 → 0.1688). *Model-conditional — state the bound.*
  Anchor: **LocAgent** (ACL 2025).
- **Subgraph** — Decorator correctness **precision 1.0 / recall 1.0**, all-and-only vs the
  compiler-oracle ground truth (`CachedCatalogViewModelService` wraps `CatalogViewModelService` via
  `ICatalogViewModelService`). God-class anti-pattern: **none** at a real bar (fan-out ≥ 20); busiest
  type is `BasketViewModelService` at 13 — an *evidenced negative*.
  Anchors: **Tsantalis** (TSE 2006), **Joern/CPG** (IEEE S&P 2014), **CodeQL**.

## Completeness honesty (carried from proving-ground §3.9)

Every edge is tagged `definitively-absent` (structural: `implements`/`extends`/`contains`/
`project_depends` — the compiler saw the whole hierarchy) or `blind-spot-possible` (`calls`/
`di_binds`/`route_handles` — delegate / reflection / interface-dispatch / DI-magic / syntactic
routing are invisible to `SymbolFinder`). A *no-path* answer is labelled trustworthy vs known-blind
accordingly.
