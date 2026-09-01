# A Practitioner's Guide to Graphs — talk pack

The companion pack for the talk **"A Practitioner's Guide to Graphs — how to make your AI
applications smarter, cheaper and more reliable"** (AI Engineer World's Fair 2026, Graph Track).
It bundles the **deck** (with the spoken script in the speaker notes), the **runnable demos**, and
the **further reading** promised from the stage — all runnable **offline, no API key**.

> Arrived here via `github.com/good-co-au/talk-graph-basics` (the link in the recording)? This is
> the right place — the pack lives under this account.

## What the talk covers

1. **Speedrun the basics.** What a graph is: nodes, edges, types, labels, properties, direction.
2. **Building better graphs** (extracting graphs from unstructured text):
   - give the extractor a **schema** — a shape to fill (structured outputs);
   - add an **ontology** in the prompt — canonical names, standard units;
   - **match entities** before creating nodes — a synonym table first, then a hybrid
     embedding + lexical matcher for the terms you didn't know in advance.
3. **Graph-native algorithms and what they buy you:**
   - a simple **graph query** (Cypher vs SQL — why traversal is where graphs excel);
   - **Personalised PageRank** — ranking what matters *from here*; Pinterest Pixie, HippoRAG, and a
     real US Supreme Court citation graph where a landmark case surfaces two hops out;
   - **shortest path** — the path *is* the explanation; a real code graph (Microsoft's eShopOnWeb)
     and our measured tool-call saving;
   - **exact subgraph matching** — find the *shape*, not the keyword; the decorator pattern found in
     the same code graph.

The talk deliberately does **not** cover graph RAG or agent-memory graphs; pointers for those and
for prediction / similarity / clustering are in [`FURTHER-READING.md`](FURTHER-READING.md).

## Watch / read the deck

- **Recording:** https://www.youtube.com/watch?v=3ySF0I5iE_0
- **Hosted deck:** https://timainge.github.io/talk-packs-graph-basics/ _(built from `deck/` by
  [`deploy-deck.yml`](.github/workflows/deploy-deck.yml) on every push to `main`)_
- **Run it locally:**

  ```bash
  cd deck
  npm install
  npm run dev        # opens the Slidev deck in your browser
  ```

  The spoken script lives in each slide's `<!-- … -->` speaker-note block (press `p` in Slidev for
  the presenter view). `npm run build` writes a static copy to `deck/dist/`.

## Run the demos

```bash
cd demos
uv sync --extra dev          # add --extra vector for the hybrid entity-matching cell
uv run jupyter lab           # then open notebooks/
```

**Offline by default.** Every LLM extraction **replays from a committed cache** in `demos/data/cache/`
— no API key, no network call. The one exception is the optional hybrid-matching cell, which
downloads a small sentence-transformer model (~90 MB) the first time you run it. (To re-record the
extractions from scratch: copy `.env.example` to `.env`, set `ANTHROPIC_API_KEY`, and run with
`GRAPHTOOLS_LIVE=1`.)

**First clone — register the notebook output filter (one-time):** notebook *outputs* are stripped
from git via `nbstripout` (wired in `.gitattributes`):

```bash
uv tool install nbstripout && nbstripout --install --attributes .gitattributes   # from the repo root
```

## What's inside

### Notebooks (`demos/notebooks/`) — one per section of the talk

| Notebook | Talk section | What it shows |
|---|---|---|
| `primer_what_is_a_graph.ipynb` | Speedrun the basics | Hand-build a tiny graph: nodes, edges, weights, properties. |
| `act1_extract.ipynb` | Extract a basic graph → give it a schema | Free-form triples (the mess), then a typed `Recipe` schema → NetworkX graph. 14 real recipes. |
| `act2_schema_drift.ipynb` | Building better graphs | Ontology in the prompt (`1 cup → 240 ml`), synonym-table entity matching (the garlic / cumin / oil collapse), hybrid embedding + lexical matching. |
| `act3_algorithms.ipynb` | Graph algorithms | The garlic query; PPR on recipes then on the SCOTUS citation graph; shortest path and the decorator-pattern match on the eShop code graph; the tool-call numbers. |

Each notebook runs top-to-bottom offline and ends with a couple of **"now you try"** prompts.

### The library — `graphtools` (`demos/graphtools/`)

Thin, reusable mechanics so the notebooks stay narrative: `extract` (Pydantic AI; free-form, schema
v1, schema + ontology v2), `graph` (NetworkX build), `resolve` (synonym table + fuzzy, hybrid vector
lookup), `focus` (the legible before/after projection), `algos` (PPR / shortest path / VF2 subgraph
match), `bench` (load the committed real-world results), `replay` (record/replay so the LLM calls
are deterministic), `viz`.

### The real-world material (`demos/artifacts/`)

| Folder | What | Status |
|---|---|---|
| `judgements/` | PPR on a public **US Supreme Court citation graph** (27,885 cases): a routine 2013 case → *Miranda v. Arizona* at #8, two hops out. | **REAL** |
| `code-graph/` | Microsoft **eShopOnWeb** compiled into a typed graph (955 nodes / 2,196 edges): the checkout → `Basket..ctor` path and the decorator-pattern match. | **REAL** |
| `proving-ground/` | Our own agent evals: graph-navigated code search vs grep — same accuracy, **40–50% fewer tool calls per task on eShop (mean 45%, n = 2)**; 56–75% on a large PowerShell repo. | **REAL, small-n** |

Each folder's README carries the provenance and the bounds. **Read them before quoting a number** —
in particular, the tool-call saving is measured on *two tasks per repo*: a proof of the mechanism,
not a population estimate.

### The deck (`deck/`)

The Slidev deck. Graphs are rendered live by the `<GraphView>` Vue component from NetworkX
`node_link_data` JSON fixtures (`deck/snippets/graph-fixtures/`), themed in one place
(`deck/components/graph-theme.ts`). See [`deck/README.md`](deck/README.md).

## Data, licences, attribution

| Dataset | Where | Terms |
|---|---|---|
| Hero recipes (14) | `demos/data/recipes/` | from [TheMealDB](https://www.themealdb.com/); small illustrative set. |
| SCOTUS citation result | `demos/artifacts/judgements/` | derived from US court opinions (public domain) + SCDB, via `idc9/law-net`. |
| eShop code graph | `demos/artifacts/code-graph/` | derived from Microsoft's MIT-licensed eShopOnWeb reference app. |
| Tool-call evals | `demos/artifacts/proving-ground/` | our own measurements; no private code. |

**Licences (split):** code is **MIT** ([`LICENSE`](LICENSE)); slides + prose are **CC BY 4.0**
([`CONTENT-LICENSE`](CONTENT-LICENSE)). Cite via [`CITATION.cff`](CITATION.cff).

## Further reading

[`FURTHER-READING.md`](FURTHER-READING.md) — the sources behind each section, the PPR / shortest-path
/ subgraph-matching variants and where they're used, and notes on what we didn't get to
(prediction, similarity, clustering, graph RAG).

## Series

This is the **basics** pack. The series:

1. **talk-packs-graph-basics** (this pack) — bad graph → good graph → payoff.
2. **talk-packs-graph-advanced** — learned graph methods: link prediction, embeddings, community
   detection.
3. **talk-packs-graph-advanced-ai** — AI-native: GraphRAG, schemaless extraction, agent memory.

The advanced packs deliberately re-open topics this one side-steps. Suggested order:
**basics → advanced → advanced-ai.**
