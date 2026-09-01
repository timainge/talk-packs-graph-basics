# A Practitioner's Guide to Knowledge Graphs — talk pack

The companion pack for the talk **"A Practitioner's Guide to Knowledge Graphs"**
(AI Engineer World's Fair 2026, Graph Track). It bundles the **deck** and the **runnable demos**
so you can read the talk, run the code, and play with the graphs yourself — **offline, no API key.**

> Part of a three-pack series: **basics** (this one) → advanced → advanced-ai. See
> [Series](#series) below.

The spine of the talk is one progression — **bad graph → good graph → payoff**:

- **Act I — the bottom.** Extract a schemaless graph from text. It *looks* like a knowledge graph.
  It's a mess. Most getting-started tutorials stop here.
- **Act II — the staircase (the heart).** Climb from bad to good one rung at a time: add **shape**
  (a schema), add an **ontology** (standard units, canonical names), add **entity resolution** (so
  duplicate nodes merge). Each rung *shows* the graph measurably improve.
- **Act III — the payoff.** The handful of algorithms that make graphs worth it — Personalised
  PageRank, HITS, shortest-path, subgraph matching — toured on a legal corpus and a code graph.

The promise: done right, graph-native structure makes AI applications **smarter, cheaper, and more
reliable.**

## Watch / read the deck

- **Recording:** https://www.youtube.com/watch?v=3ySF0I5iE_0
- **Hosted deck:** https://timainge.github.io/talk-packs-graph-basics/ _(published from `deck/dist`)_
- **Run it locally:**

  ```bash
  cd deck
  npm install
  npm run dev        # opens the Slidev deck in your browser
  ```

  The spoken script lives in each slide's `<!-- … -->` speaker-note block (press `p` in Slidev to
  see the presenter view). Build a static copy with `npm run build` → `deck/dist/`.

## Run the demos

```bash
cd demos
uv sync --extra dev          # add --extra vector for the hybrid-lookup cell
uv run jupyter lab           # then open notebooks/
```

**Offline by default.** Every LLM extraction **replays from a committed cache** in `demos/data/cache/`
— no API key, no network call. (To re-record from scratch: copy `.env.example` to `.env`, set
`ANTHROPIC_API_KEY`, and run with `GRAPHTOOLS_LIVE=1`.)

**First clone — register the notebook output filter (one-time):** this repo strips notebook *outputs*
from git via `nbstripout` (wired in `.gitattributes`). Install it once so checkouts and commits stay
clean:

```bash
uv tool install nbstripout && nbstripout --install --attributes .gitattributes   # from the repo root
```

## What's inside

### Notebooks (`demos/notebooks/`)

| Notebook | Act | What it shows |
|---|---|---|
| `primer_what_is_a_graph.ipynb` | Primer | Hand-build a tiny graph: nodes, edges, weights, properties. The clean ideal, before the mess. |
| `act1_extract.ipynb` | I — the bottom | text → typed records → graph; the "look, a graph" recipe viz (14 hero recipes). |
| `act2_schema_drift.ipynb` | II — the staircase | the drift viz (duplicate smear); schema-first v1→v2 (`1 cup → 240 ml`); entity resolution (122→102 ingredients) + hybrid lookup. |
| `act3_algorithms.ipynb` | III — the payoff | live shortest-path cameo (buttermilk → milk + acid); PPR / random-walk relevance; code-graph explainability; exact subgraph matching. |

Each notebook runs top-to-bottom offline and ends with a couple of **"now you try"** prompts.

### The library — `graphtools` (`demos/graphtools/`)

Thin, reusable mechanics so the notebooks stay narrative: `extract` (PydanticAI, v1 + schema-first
v2), `graph` (NetworkX build + substitution edges), `resolve` (ontology + fuzzy + hybrid vector
lookup), `algos` (PPR / HITS / shortest-path / subgraph), `drift` (duplicate-collapse viz),
`bench` (load committed artifacts), `replay` (record/replay determinism), `viz` / `viz_export`.

### The deck (`deck/`)

The Slidev deck. Graphs in the deck are rendered live by the `<GraphView>` Vue component from
NetworkX `node_link_data` JSON fixtures (in `deck/snippets/graph-fixtures/`), themed in one place
(`deck/components/graph-theme.ts`).

## The honest caveats (read before reusing a number)

- **The judgements artifacts that are SAMPLES are labelled SAMPLE.** The PPR/HITS landmark results
  are **REAL**, from a public US SCOTUS citation graph; the subgraph-match artifact is an
  illustrative **SAMPLE** with placeholder names. Each Act III cell prints its own `_status`. See
  [`demos/artifacts/judgements/README.md`](demos/artifacts/judgements/README.md).
- **The proving-ground numbers are REAL but small-n.** The claim is *efficiency, not accuracy* —
  accuracy parity with grep, but navigation cost collapses (grep 16 → graph 4 tool-uses). State n.
  See [`demos/artifacts/proving-ground/README.md`](demos/artifacts/proving-ground/README.md).
- **The drift viz** shows duplicate inflation widening with N — *not* a plateau. Frame it as
  "duplicates grow faster than real ingredients."
- **Verify before slide.** Any borrowed statistic (HippoRAG F1, Pixie scale, any dedup figure) is
  yet to be re-checked against its primary source — confirm before quoting it.

## Data, licenses, attribution

| Dataset | Where | Terms |
|---|---|---|
| Hero recipes (14) | `demos/data/recipes/` | from TheMealDB; small illustrative set. |
| Recipe scale sample (200 rows) | `demos/data/scale/sample.jsonl` | RecipeNLG, **research-use — cite Bień et al. (INLG 2020)**. Full ~10k via `demos/scripts/fetch_scale.py`. |
| SCOTUS landmark artifacts | `demos/artifacts/judgements/` | derived from US court opinions (public domain) + SCDB. |
| code-graph / proving-ground artifacts | `demos/artifacts/` | our own measured exports from sibling repos; no private code. |

**Licenses (split):** code is **MIT** ([`LICENSE`](LICENSE)); slides + prose are **CC BY 4.0**
([`CONTENT-LICENSE`](CONTENT-LICENSE)). Cite via [`CITATION.cff`](CITATION.cff).

## Further reading

The named systems and primary sources the talk leans on:

- **Pinterest Pixie** — personalised random walks (PPR) at web scale (WWW 2018).
- **HippoRAG / HippoRAG 2** — PPR as a neurobiologically-inspired retrieval engine
  (NeurIPS 2024 / ICML 2025).
- **RecipeNLG** — the recipe corpus behind the scale demo (Bień et al., INLG 2020).
- **Fowler & Jeon (2008)** — *The Authority of Supreme Court Precedent*; the validation anchor for
  the citation-graph landmark detection.
- Act III algorithm background — **Personalised PageRank**, **HITS** (Kleinberg, 1999),
  **shortest-path / constrained traversal**, **subgraph matching** (VF2; Glasgow; learned variants
  NeuroMatch / G-Retriever / GRAG).

(Numbers borrowed from these sources are *verify-before-slide* — don't reproduce one until it's been
checked against the primary source.)

## Series

This is the **basics** pack. The series:

1. **talk-packs-graph-basics** (this pack) — bad graph → good graph → payoff.
2. **talk-packs-graph-advanced** — learned graph methods: link prediction, embeddings, community
   detection.
3. **talk-packs-graph-advanced-ai** — AI-native: GraphRAG, schemaless extraction, agent memory.

The advanced packs deliberately re-open topics this one side-steps. Suggested order:
**basics → advanced → advanced-ai.**
