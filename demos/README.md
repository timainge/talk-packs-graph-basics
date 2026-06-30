# demos

Experimentation-first demos for the talk — for readers who want to **play**, not to build the deck.
One runnable thread (**recipes**) plus a gallery of pre-baked **artifacts** you tour. The talk
itself is in [`../deck/slides.md`](../deck/slides.md).

## Run (offline, no API key)

```bash
uv sync --extra dev          # add --extra vector for the Act II hybrid-lookup cell
uv run jupyter lab           # then open notebooks/
```

Everything **replays from a committed cache** (`data/cache/`), so the notebooks run with no API key
and no network. Run any notebook top to bottom.

**First clone — register the notebook output filter (one-time, required):** outputs are stripped from
git via `nbstripout` (wired in the repo-root `.gitattributes`). Install it once:

```bash
uv tool install nbstripout && nbstripout --install --attributes .gitattributes   # from the repo root
```

## Notebooks

| Notebook | What it shows |
|---|---|
| `primer_what_is_a_graph.ipynb` | Hand-build a tiny graph — nodes, edges, weights, properties. |
| `act1_extract.ipynb` | text → typed records → graph; the naive "look, a graph" viz. |
| `act2_schema_drift.ipynb` | the drift / duplicate-smear viz; schema-first v1→v2; entity resolution + hybrid lookup. |
| `act3_algorithms.ipynb` | shortest-path cameo; PPR; subgraph matching; the code-graph cost-collapse. |

## Layout

```
graphtools/          the lib — notebooks stay thin, the mechanics live here
  extract.py         recipe text -> typed records (PydanticAI, v1 + schema-first v2)
  graph.py           records -> NetworkX graph (+ build_graph_v3 substitution edges)
  resolve.py         entity resolution (ontology + fuzzy) + hybrid vector lookup
  drift.py           the drift / duplicate-collapse viz
  algos.py           ppr / authority / explain_path / match_subgraph
  bench.py           load committed benchmark artifacts
  replay.py          record/replay so cached extractions are deterministic
  viz.py / viz_export.py   matplotlib fallback render + node_link_data export
notebooks/           one per act — thin narrative drivers
data/recipes/        14 hero recipes (committed)
data/scale/          200-row RecipeNLG sample for the drift viz (full set via scripts/fetch_scale.py)
data/cache/          recorded LLM outputs (committed -> offline replay)
data/ontology/       units / ingredients / substitutions tables
artifacts/           pre-baked Act III tour material (judgements / code-graph / proving-ground)
viz/fixtures/        the one graph fixture a notebook reads (poc-fraud-ring)
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

## Honest caveats

The `artifacts/` READMEs carry the provenance and bounds for each toured result — read them before
quoting a number. In short: the judgements PPR/HITS results are REAL (public US SCOTUS graph), the
judgements subgraph-match is a labelled **SAMPLE**, and the proving-ground numbers are REAL but
small-n (the claim is *efficiency, not accuracy*).
