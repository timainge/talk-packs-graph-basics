"""[D0.1] Load the committed recipe hero set — the deterministic corpus the talk
extracts live. Pure local IO, no network, no API key.

Each file in ``data/recipes/*.json`` is one recipe shaped::

    {"title", "ingredients": [{"name","quantity","unit"}...],
     "instructions", "source", "text"}

``text`` is a human-readable blob (ingredient lines + method) ready to feed the
LLM extractor in ``graphtools.extract``.
"""

from __future__ import annotations

import json
from pathlib import Path

RECIPES_DIR = Path(__file__).resolve().parent.parent / "data" / "recipes"


def load_hero_recipes(recipes_dir: Path | str | None = None) -> list[dict]:
    """Return the parsed hero recipes, sorted by filename for stable ordering."""
    directory = Path(recipes_dir) if recipes_dir is not None else RECIPES_DIR
    records: list[dict] = []
    for path in sorted(directory.glob("*.json")):
        records.append(json.loads(path.read_text()))
    return records


def load_hero_texts(recipes_dir: Path | str | None = None) -> list[tuple[str, str]]:
    """Return ``(title, text)`` pairs ready to feed the extractor."""
    return [(r["title"], r["text"]) for r in load_hero_recipes(recipes_dir)]
