"""Record/replay cache — so live LLM demos never depend on a network call on stage.

Three modes (resolved per call):

- **replay** (default): read the committed JSON in data/cache/; on a miss, call the
  producer live and record it. Deterministic — this is what the notebooks/stage use.
- **refresh** (`GRAPHTOOLS_LIVE=1`): ignore the cached value, call live, and *overwrite*
  the cache. Use to re-record after changing a prompt/schema.
- **off** (`GRAPHTOOLS_CACHE=0`, or `set_caching(False)`): pure passthrough — always call
  live, never read or write the cache. For **dev**, so iterating can't pollute the
  committed cache. Default is ON so stage replay keeps working out of the box.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Callable

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

# Programmatic override for caching (e.g. `set_caching(False)` in a dev notebook).
# None = defer to the GRAPHTOOLS_CACHE env var.
_CACHE_OVERRIDE: bool | None = None
_FALSEY = {"0", "false", "off", "no"}

_env_loaded = False


def load_env(force: bool = False) -> None:
    """Load demos/.env into os.environ (without overriding already-set vars).

    `uv run` doesn't auto-load .env, so we call this before reading any GRAPHTOOLS_*
    flag or making an LLM call. Idempotent. Zero-dependency parser: KEY=VALUE lines,
    ignores blanks/comments, strips surrounding quotes.
    """
    global _env_loaded
    if _env_loaded and not force:
        return
    _env_loaded = True
    if not _ENV_FILE.exists():
        return
    for line in _ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def set_caching(enabled: bool | None) -> None:
    """Force the replay cache on/off for this process. ``None`` defers to the
    GRAPHTOOLS_CACHE env var (the default). Handy in a dev notebook cell:
    ``from graphtools.replay import set_caching; set_caching(False)``."""
    global _CACHE_OVERRIDE
    _CACHE_OVERRIDE = enabled


def caching_enabled() -> bool:
    """Is the replay cache active? Default **on** (stage-safe). Turn off for dev with
    ``GRAPHTOOLS_CACHE=0`` (no read, no write) or ``set_caching(False)``."""
    if _CACHE_OVERRIDE is not None:
        return _CACHE_OVERRIDE
    load_env()
    return os.environ.get("GRAPHTOOLS_CACHE", "1").strip().lower() not in _FALSEY


def key_for(text: str, *, tag: str = "") -> str:
    """Stable cache key from input text (+ optional tag, e.g. the schema version)."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{tag + '-' if tag else ''}{digest}"


def cached(key: str, produce: Callable[[], dict | list]) -> dict | list:
    """Return cached JSON for `key`, else run `produce()`, record, and return it.

    Caching off (GRAPHTOOLS_CACHE=0 / set_caching(False)) → pure passthrough.
    Refresh (GRAPHTOOLS_LIVE=1) → ignore the cached value and overwrite it.
    """
    load_env()
    if not caching_enabled():
        return produce()  # dev: always live, no cache read or write (no pollution)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{key}.json"
    if path.exists() and os.environ.get("GRAPHTOOLS_LIVE") != "1":
        return json.loads(path.read_text())
    value = produce()
    path.write_text(json.dumps(value, indent=2, default=str))
    return value
