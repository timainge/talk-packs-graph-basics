# demos

Runnable demos for the talk — for readers who want to **play**, not to build the deck. One
runnable thread (**recipes**) plus the committed **real-world results** you tour. The talk itself
is in [`../deck/slides.md`](../deck/slides.md); the reading list is
[`../FURTHER-READING.md`](../FURTHER-READING.md).

## Run (offline, no API key)

```bash
uv sync --extra dev          # add --extra vector for the hybrid entity-matching cell (Act II §3)
uv run jupyter lab           # then open notebooks/
```

Everything **replays from a committed cache** (`data/cache/`), so the notebooks run with no API key
and no network. The one optional exception is the hybrid-matching cell, which downloads the
`all-MiniLM-L6-v2` sentence-transformer (~90 MB) the first time. Run any notebook top to bottom.

**First clone — register the notebook output filter (one-time):** outputs are stripped from git via
`nbstripout` (wired in the repo-root `.gitattributes`):

```bash
uv tool install nbstripout && nbstripout --install --attributes .gitattributes   # from the repo root
```

## Notebooks — one per section of the talk

| Notebook | Talk section | What it shows |
|---|---|---|
| `primer_what_is_a_graph.ipynb` | Speedrun the basics | Hand-build a tiny graph — nodes, edges, weights, properties. |
| `act1_extract.ipynb` | Extract a basic graph → schema | Free-form triples (the mess); then a typed `Recipe` schema → NetworkX graph. |
| `act2_schema_drift.ipynb` | Building better graphs | Ontology in the prompt (v1 → v2); synonym-table entity matching; hybrid embedding + lexical matching. |
| `act3_algorithms.ipynb` | Graph algorithms | The garlic query; PPR (recipes → SCOTUS landmark law); shortest path + decorator-pattern match on the eShop code graph; the tool-call numbers. |

## Layout

```
graphtools/          the lib — notebooks stay thin, the mechanics live here
  extract.py         recipe text -> typed records (Pydantic AI: free-form, schema v1, schema + ontology v2)
  graph.py           records -> NetworkX graph
  resolve.py         entity matching (synonym table + fuzzy) and hybrid vector lookup
  focus.py           the legible before/after projection for entity matching
  algos.py           ppr / explain_path / match_subgraph
  bench.py           load the committed real-world result files
  replay.py          record/replay so cached extractions are deterministic
  viz.py             matplotlib rendering for the notebooks
notebooks/           one per section — thin narrative drivers
data/recipes/        14 hero recipes (committed)
data/cache/          recorded LLM outputs (committed -> offline replay)
data/ontology/       units / ingredients tables
artifacts/           the real-world material: judgements / code-graph / proving-ground
scripts/             fetch_recipes.py — regenerate the hero set from TheMealDB
```

## Caching modes (extractions go through `graphtools.replay`)

| Mode | How | Behaviour |
|---|---|---|
| **replay** (default) | — | read `data/cache/`; on a miss, call live + record. No network on a hit. |
| **refresh** | `GRAPHTOOLS_LIVE=1` | ignore the cached value, call live, **overwrite** the cache. |
| **off (dev)** | `GRAPHTOOLS_CACHE=0` | pure passthrough — always live, never read or write the cache. |

Caching defaults **on** so offline replay just works. Turning it off needs `ANTHROPIC_API_KEY` and
makes runs non-deterministic. Override the model with `GRAPHTOOLS_MODEL`
(default `anthropic:claude-sonnet-4-6`). See `.env.example`.

## Read the bounds before quoting a number

Each `artifacts/*/README.md` carries the provenance and limits of what it holds. In short: the
SCOTUS landmark result and the eShop code graph are **REAL**; the tool-call saving is **REAL but
small-n** (two tasks per repo — the claim is *efficiency, not accuracy*).
