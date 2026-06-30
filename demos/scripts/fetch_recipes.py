"""[D0.1] Fetch the recipe hero set from TheMealDB into demos/data/recipes/.

TheMealDB (https://www.themealdb.com/api.php) is a free JSON recipe API — no key,
no scraping. We look up a *fixed* list of meals by name so the corpus is
deterministic and curated for cuisine variety + ingredient overlap (flour /
butter / onion appear across several, giving later graph demos shared nodes).

Each meal becomes one JSON file `data/recipes/<slug>.json`:

    {
      "title": str,
      "ingredients": [{"name", "quantity", "unit"}, ...],
      "instructions": str,
      "source": str,
      "text": str,              # human-readable blob to feed an LLM extractor
    }

Idempotent: re-running overwrites the same files; meals already present are
re-fetched only if missing unless --force is passed.

Run:  uv run python scripts/fetch_recipes.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import httpx

API = "https://www.themealdb.com/api/json/v1/1"

# Curated for cuisine spread + shared ingredients (flour, butter, onion, garlic...).
HERO_MEALS = [
    "Spaghetti Bolognese",       # Italian
    "Beef Wellington",           # British
    "Chicken Handi",             # Indian
    "Teriyaki Chicken Casserole",  # Japanese
    "Beef Lo Mein",              # Chinese
    "Cajun spiced fish tacos",   # Mexican / Cajun
    "Croatian Bean Stew",        # Croatian
    "Lamb Tagine",               # Moroccan
    "Pancakes",                  # American / breakfast (flour, butter)
    "French Onion Soup",         # French (onion, butter)
    "Tuna Nicoise",              # French / salad
    "Vegetarian Chilli",         # vegetarian
    "Apple Frangipan Tart",      # dessert (flour, butter)
    "Egyptian Fatteh",           # Egyptian / Middle Eastern
]

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "recipes"


def slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s or "recipe"


def parse_ingredients(meal: dict) -> list[dict]:
    """TheMealDB stores ingredients/measures in strIngredient1..20 / strMeasure1..20.

    The measure is a free-text blob like '1 cup', '200g', 'to taste'. We split a
    leading numeric quantity off into `quantity` and keep the remainder as `unit`.
    """
    out: list[dict] = []
    for i in range(1, 21):
        name = (meal.get(f"strIngredient{i}") or "").strip()
        measure = (meal.get(f"strMeasure{i}") or "").strip()
        if not name:
            continue
        quantity, unit = split_measure(measure)
        out.append({"name": name, "quantity": quantity, "unit": unit})
    return out


def split_measure(measure: str) -> tuple[str | None, str | None]:
    """Best-effort split of '1 1/2 cups' -> ('1 1/2', 'cups'); '200g' -> ('200', 'g')."""
    if not measure:
        return None, None
    m = re.match(r"^\s*([\d]+(?:[\s.¼-¾/]+\d*)*)\s*(.*)$", measure)
    if m and m.group(1).strip():
        qty = m.group(1).strip()
        unit = (m.group(2) or "").strip() or None
        return qty, unit
    # No leading number (e.g. 'to taste', 'Dash') — treat the whole thing as a unit/note.
    return None, measure or None


def to_text(title: str, ingredients: list[dict], instructions: str) -> str:
    lines = [title, "", "Ingredients:"]
    for ing in ingredients:
        qty = " ".join(p for p in (ing.get("quantity"), ing.get("unit")) if p)
        lines.append(f"- {qty + ' ' if qty else ''}{ing['name']}".rstrip())
    lines += ["", "Method:", instructions.strip()]
    return "\n".join(lines)


def fetch_meal(client: httpx.Client, name: str) -> dict | None:
    resp = client.get(f"{API}/search.php", params={"s": name})
    resp.raise_for_status()
    meals = resp.json().get("meals")
    return meals[0] if meals else None


def build_record(meal: dict) -> dict:
    title = (meal.get("strMeal") or "Untitled").strip()
    ingredients = parse_ingredients(meal)
    instructions = (meal.get("strInstructions") or "").strip()
    source = (meal.get("strSource") or "").strip() or f"TheMealDB id {meal.get('idMeal')}"
    return {
        "title": title,
        "ingredients": ingredients,
        "instructions": instructions,
        "source": source,
        "text": to_text(title, ingredients, instructions),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="re-fetch even if the file exists")
    args = ap.parse_args(argv)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    written, skipped, missing = 0, 0, []

    with httpx.Client(timeout=20, headers={"User-Agent": "graphtools-demo/0.1"}) as client:
        for name in HERO_MEALS:
            slug = slugify(name)
            path = DATA_DIR / f"{slug}.json"
            if path.exists() and not args.force:
                skipped += 1
                continue
            try:
                meal = fetch_meal(client, name)
            except httpx.HTTPError as exc:
                print(f"  ! {name}: {exc}", file=sys.stderr)
                missing.append(name)
                continue
            if meal is None:
                print(f"  ? {name}: not found on TheMealDB", file=sys.stderr)
                missing.append(name)
                continue
            record = build_record(meal)
            slug = slugify(record["title"])  # prefer the canonical title for the slug
            path = DATA_DIR / f"{slug}.json"
            path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
            print(f"  + {record['title']} -> {path.name}")
            written += 1

    total = len(list(DATA_DIR.glob("*.json")))
    print(f"\nwrote {written}, skipped {skipped}, files on disk {total}")
    if missing:
        print(f"missing: {', '.join(missing)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
