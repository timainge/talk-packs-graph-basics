# Recipe corpus — the scale set (drift viz only)

~10k recipes used **only** to drive the drift visualisation (Phase 3 / Act II sidequest).
The drift demo needs SCALE plus realistic **entity-name variance** — many surface forms of
the same ingredient (`plain flour` / `all-purpose flour` / `gluten-free flour`, `green onions`
/ `red onion`, `granulated sugar` / `confectioners' sugar`) — so that naive exact-string
linking shatters the graph into thousands of islands. Not needed until the drift spike.

## Source

| | |
|---|---|
| **Dataset** | **RecipeNLG** (Bień et al., *INLG 2020*) — 2,231,142 cooking recipes |
| **Mirror used** | `corbt/all-recipes` on Hugging Face — the same corpus, **ungated** (no auth) |
| **URL** | https://huggingface.co/datasets/corbt/all-recipes |
| **Rows API** | `https://datasets-server.huggingface.co/rows?dataset=corbt/all-recipes&config=default&split=train` |
| **Parquet** | `https://datasets-server.huggingface.co/parquet?dataset=corbt/all-recipes` (4 shards, ~125–260 MB each) |
| **Train rows** | 2,147,248 |

### Why this mirror

The canonical upload, [`mbien/recipe_nlg`](https://huggingface.co/datasets/mbien/recipe_nlg),
is **gated** — downloading it needs a Hugging Face account + token. `corbt/all-recipes` is the
identical RecipeNLG corpus re-published ungated, so `fetch_scale.py` runs with **no credentials**.
(Sanity check: the first row of both is the same "No-Bake Nut Cookies" recipe.)

### License

RecipeNLG is released for **non-commercial, research use** by the authors (Poznań University of
Technology). See the dataset terms at https://recipenlg.cs.put.poznan.pl/ and the paper:

> Bień, Gilski, Maciejewska, Taisner, Wiśniewski, Ławrynowicz. *RecipeNLG: A Cooking Recipes
> Dataset for Semi-Structured Text Generation.* INLG 2020. https://aclanthology.org/2020.inlg-1.4/

This talk uses it purely as illustrative demo data (research/educational), and we do **not**
commit the bulk dump — only a 200-row sample. Cite RecipeNLG if you reuse it.

## Row schema (normalised output)

`fetch_scale.py` parses each RecipeNLG `input` blob into:

```json
{"title": "Big Mama's Buttermilk Cake",
 "ingredients": ["1 1/2 c. Crisco", "3 1/2 c. plain flour", "1 c. buttermilk", ...]}
```

- `title` — `str`
- `ingredients` — `list[str]`, the **raw** ingredient lines kept verbatim (qty + unit + name);
  this surface-form variance is exactly what the drift viz consumes. Directions are dropped.

One JSON object per line (JSONL).

## What's committed vs generated — real vs stand-in

| File | Status | Notes |
|---|---|---|
| `sample.jsonl` | **committed, REAL** | 200 real RecipeNLG recipes (api strategy, seed `20260618`). Unblocks downstream work. |
| `local/recipes.jsonl` | **gitignored, generate locally** | the full ~10k dump. `local/` is ignored via `data/scale/.gitignore`. |
| `local/parquet/*.parquet` | **gitignored** | parquet shard cache (only with `--strategy parquet`). |

Nothing here is synthetic — both the sample and the full dump are real RecipeNLG rows pulled
from the ungated `corbt/all-recipes` mirror. The fetch is **fully automated** (no manual
download / Kaggle auth needed) because that mirror is directly reachable.

## Regenerate

From `demos/` (always `uv run`):

```bash
# Rebuild the committed 200-row sample
uv run python scripts/fetch_scale.py --sample --force

# Fetch the full ~10k into local/recipes.jsonl (gitignored). Light: ~a few MB over the rows API.
uv run python scripts/fetch_scale.py

# Optional: truer uniform sample via parquet shards (heavier — downloads >100 MB shards)
uv run python scripts/fetch_scale.py --strategy parquet --n 10000
```

Both strategies are deterministic (fixed `--seed`) and idempotent (re-running is a no-op unless
`--force`). See the module docstring in `scripts/fetch_scale.py` for the full option list.
```bash
# DoD sanity check
uv run python -c "import json; rows=[json.loads(l) for l in open('data/scale/sample.jsonl')]; print(len(rows), rows[0].keys())"
```
