"""[D2.4] Acquire ~10k recipes into demos/data/scale/ to drive the drift viz.

The drift visualisation (Phase 3) needs SCALE plus realistic *entity-name variance*
— many surface forms of the same ingredient ("plain flour" / "all-purpose flour" /
"AP flour" / "maida"; "Crisco" / "shortening"; "scallions" / "green onions") — so that
naive exact-string linking shatters the graph into thousands of islands.

Source
------
**RecipeNLG** (Bień et al., INLG 2020) — 2.23M cooking recipes — via the public,
directly-downloadable Hugging Face mirror **`corbt/all-recipes`**
(https://huggingface.co/datasets/corbt/all-recipes). The original `mbien/recipe_nlg`
upload is gated (needs HF auth); `corbt/all-recipes` is the same corpus, ungated, and
reachable with no credentials. Each row is a single `input` text blob of the form:

    <Title>

    Ingredients:
    - 1 1/2 c. Crisco
    - 3 1/2 c. plain flour
    ...

    Directions:
    - ...

We parse that blob into `{title, ingredients: [str, ...]}` — keeping the *raw* ingredient
lines verbatim (that variance is the whole point of the drift demo).

Two fetch strategies
--------------------
- ``api`` (default): stream rows through the HF datasets-server ``/rows`` endpoint
  (max 100 rows/request). To get a *spread* across the 2.23M-row corpus we sample
  ``--n`` deterministic offsets (fixed seed) and pull a contiguous block at each.
  Lightweight (~a few MB for 10k rows) and works with no auth — this is the path that
  runs in restricted sandboxes.
- ``parquet``: download the dataset's parquet shards and take a uniform random sample
  with pandas. A *truer* random sample, but each shard is >100 MB, so it is heavier and
  may be impractical on metered/slow links. Opt in with ``--strategy parquet``.

Output (idempotent, deterministic seed)
---------------------------------------
- Full dump:  ``data/scale/local/recipes.jsonl``  (gitignored — see note below)
- Re-running with the same ``--n``/``--seed`` reproduces the same file. Pass ``--force``
  to overwrite an existing dump.

``data/scale/local/`` is written under ``local/`` purely so the repo .gitignore
(``data/local/``) does *not* catch it — the full dump is big and should NOT be committed.
We add an explicit ignore for it; only the small ``sample.jsonl`` is committed. Pass
``--out`` to redirect.

Build the committed sample
--------------------------
    uv run python scripts/fetch_scale.py --sample        # writes data/scale/sample.jsonl (~200 rows)

Regenerate the full ~10k
------------------------
    uv run python scripts/fetch_scale.py                 # api strategy, 10k rows
    uv run python scripts/fetch_scale.py --strategy parquet --n 10000   # heavier, truer sample

No LLM calls. Stdlib + httpx + pandas/pyarrow only.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import httpx

DATASET = "corbt/all-recipes"
CONFIG = "default"
SPLIT = "train"
TOTAL_ROWS = 2_147_248  # corbt/all-recipes train split (RecipeNLG)

ROWS_API = "https://datasets-server.huggingface.co/rows"
PARQUET_API = "https://datasets-server.huggingface.co/parquet"
PAGE = 100  # HF datasets-server hard cap on `length` per /rows request
REQUEST_DELAY = 0.3  # polite gap between /rows calls — the endpoint rate-limits (429) on bursts
MAX_RETRIES = 5  # exponential backoff on 429 / transient errors

SCALE_DIR = Path(__file__).resolve().parents[1] / "data" / "scale"
DEFAULT_OUT = SCALE_DIR / "local" / "recipes.jsonl"
SAMPLE_OUT = SCALE_DIR / "sample.jsonl"


# --------------------------------------------------------------------------- parsing


def parse_blob(text: str) -> dict | None:
    """Parse a RecipeNLG `input` blob into {title, ingredients:[str]}.

    The blob is `<title>\\n\\nIngredients:\\n- ...\\n\\nDirections:\\n- ...`. We keep the
    ingredient lines *verbatim* (their surface-form variance is the point of the demo)
    and drop the directions. Returns None if it doesn't look like a recipe.
    """
    if not text:
        return None
    lines = text.splitlines()
    title = ""
    for ln in lines:
        if ln.strip():
            title = ln.strip()
            break
    if not title:
        return None

    ingredients: list[str] = []
    in_ing = False
    for ln in lines:
        low = ln.strip().lower()
        if low.startswith("ingredient"):
            in_ing = True
            continue
        if low.startswith("direction") or low.startswith("instruction") or low.startswith("method"):
            in_ing = False
            continue
        if in_ing:
            item = ln.strip().lstrip("-*•").strip()
            if item:
                ingredients.append(item)
    if not ingredients:
        return None
    return {"title": title, "ingredients": ingredients}


# --------------------------------------------------------------------------- api strategy


def _fetch_page(client: httpx.Client, offset: int, length: int) -> list[dict]:
    """Fetch one page, retrying with exponential backoff on 429 / transient errors."""
    params = {
        "dataset": DATASET,
        "config": CONFIG,
        "split": SPLIT,
        "offset": offset,
        "length": length,
    }
    for attempt in range(MAX_RETRIES):
        resp = client.get(ROWS_API, params=params)
        if resp.status_code == 429:
            wait = float(resp.headers.get("Retry-After", 2 ** attempt))
            time.sleep(min(wait, 30))
            continue
        resp.raise_for_status()
        return resp.json().get("rows", [])
    resp.raise_for_status()  # exhausted retries — surface the last error
    return []


def fetch_via_api(n: int, seed: int) -> list[dict]:
    """Pull ~n recipes by sampling deterministic offsets across the corpus.

    We pick ceil(n/PAGE) start offsets (seeded, sorted, de-duplicated to avoid overlap)
    and fetch a PAGE-sized block at each, so the sample is spread over the full 2.23M
    rows rather than clustered at the front — giving the ingredient-name variance the
    drift viz needs.
    """
    # Over-provision blocks: parsing/dedup drops a few rows per block, and the endpoint
    # occasionally 429s a block past its retries — so request ~1.7x and stop once we hit n.
    n_blocks = (n + PAGE - 1) // PAGE
    want_blocks = int(n_blocks * 1.7) + 4
    rng = random.Random(seed)
    max_offset = max(1, TOTAL_ROWS - PAGE)
    # de-duplicate offsets onto a grid so blocks don't overlap
    offsets = sorted({(rng.randrange(0, max_offset) // PAGE) * PAGE for _ in range(want_blocks * 2)})
    offsets = offsets[:want_blocks]

    out: list[dict] = []
    seen_titles: set[str] = set()
    with httpx.Client(timeout=30, headers={"User-Agent": "graphtools-demo/0.1"}) as client:
        for i, off in enumerate(offsets):
            try:
                rows = _fetch_page(client, off, PAGE)
            except httpx.HTTPError as exc:
                print(f"  ! offset {off}: {exc}", file=sys.stderr)
                continue
            for r in rows:
                rec = parse_blob(r.get("row", {}).get("input", ""))
                if rec is None:
                    continue
                key = rec["title"].lower()
                if key in seen_titles:
                    continue
                seen_titles.add(key)
                out.append(rec)
            if (i + 1) % 10 == 0 or i + 1 == len(offsets):
                print(f"  api: {i + 1}/{len(offsets)} blocks, {len(out)} recipes")
            if len(out) >= n:
                break
            time.sleep(REQUEST_DELAY)  # be polite — the endpoint 429s on bursts
    return out[:n]


# --------------------------------------------------------------------------- parquet strategy


def fetch_via_parquet(n: int, seed: int) -> list[dict]:
    """Download parquet shards and take a uniform random sample with pandas.

    Truer random sample than the api strategy, but each shard is >100 MB. Downloads
    shards one at a time until it has enough rows to sample `n` from, then samples.
    """
    import pandas as pd  # local import: only needed for this heavier path

    with httpx.Client(timeout=120, follow_redirects=True,
                      headers={"User-Agent": "graphtools-demo/0.1"}) as client:
        meta = client.get(PARQUET_API, params={"dataset": DATASET})
        meta.raise_for_status()
        files = [f for f in meta.json().get("parquet_files", []) if f.get("split") == SPLIT]
        if not files:
            raise RuntimeError("no parquet files returned by datasets-server")

        cache = SCALE_DIR / "local" / "parquet"
        cache.mkdir(parents=True, exist_ok=True)
        frames: list[pd.DataFrame] = []
        rows_have = 0
        # one shard already dwarfs 10k rows; pull shards until we comfortably exceed n*20
        for f in files:
            dst = cache / f["filename"]
            if not dst.exists():
                print(f"  parquet: downloading {f['filename']} ({f['size'] / 1e6:.0f} MB)...")
                with client.stream("GET", f["url"]) as resp:
                    resp.raise_for_status()
                    with dst.open("wb") as fh:
                        for chunk in resp.iter_bytes(chunk_size=1 << 20):
                            fh.write(chunk)
            df = pd.read_parquet(dst, columns=["input"])
            frames.append(df)
            rows_have += len(df)
            if rows_have >= max(n * 20, 200_000):
                break

    pool = pd.concat(frames, ignore_index=True)
    pool = pool.sample(n=min(len(pool), n * 3), random_state=seed)  # over-sample, parsing drops some

    out: list[dict] = []
    seen: set[str] = set()
    for blob in pool["input"]:
        rec = parse_blob(blob)
        if rec is None:
            continue
        key = rec["title"].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(rec)
        if len(out) >= n:
            break
    return out


# --------------------------------------------------------------------------- io


def write_jsonl(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=10_000, help="number of recipes to fetch (default 10000)")
    ap.add_argument("--seed", type=int, default=20260618, help="deterministic sample seed")
    ap.add_argument("--strategy", choices=["api", "parquet"], default="api",
                    help="api = light rows endpoint (default); parquet = heavier uniform sample")
    ap.add_argument("--out", type=Path, default=None, help="output jsonl (default data/scale/local/recipes.jsonl)")
    ap.add_argument("--sample", action="store_true",
                    help="build the committed ~200-row data/scale/sample.jsonl instead of the full dump")
    ap.add_argument("--force", action="store_true", help="overwrite an existing output file")
    args = ap.parse_args(argv)

    if args.sample:
        n = 200
        out = args.out or SAMPLE_OUT
    else:
        n = args.n
        out = args.out or DEFAULT_OUT

    if out.exists() and not args.force:
        existing = sum(1 for _ in out.open())
        print(f"{out} already exists ({existing} rows); pass --force to overwrite.")
        return 0

    print(f"fetching {n} recipes from {DATASET} via {args.strategy} (seed {args.seed})...")
    fetch = fetch_via_parquet if args.strategy == "parquet" else fetch_via_api
    records = fetch(n, args.seed)

    if not records:
        print("no records fetched — source unreachable? see data/scale/README.md.", file=sys.stderr)
        return 1

    write_jsonl(records, out)
    print(f"wrote {len(records)} recipes -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
