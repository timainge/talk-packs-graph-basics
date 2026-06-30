"""[SIDEQUEST] Fetch a URL as markdown, then render a naive graph from it.

Two providers, both return markdown for an arbitrary URL (keys in demos/.env):
  - **Jina AI Reader** (`JINAAI_API_KEY`) — GET https://r.jina.ai/<url>
  - **Firecrawl** (`FIRECRAWL_API_KEY`) — POST https://api.firecrawl.dev/v1/scrape

`naive_graph_from_url(url)` chains: fetch markdown → `extract.extract_freeform` (v0,
no schema) → `graph.build_naive_graph` → a messy naive graph you can `viz.render_graph`.
That's the Act I point, live on anything: "look, a knowledge graph!" … that's a mess.

Fetch + extraction route through `replay.cached`, so re-running the same URL is offline
(and `GRAPHTOOLS_CACHE=0` disables caching for dev — see replay.py).
"""

from __future__ import annotations

import os

from .replay import cached, key_for, load_env

JINA_ENDPOINT = "https://r.jina.ai/"
FIRECRAWL_ENDPOINT = "https://api.firecrawl.dev/v1/scrape"


def _provider(provider: str) -> str:
    """Resolve 'auto' → whichever key is present (Jina preferred)."""
    load_env()
    if provider != "auto":
        return provider
    if os.environ.get("JINAAI_API_KEY"):
        return "jina"
    if os.environ.get("FIRECRAWL_API_KEY"):
        return "firecrawl"
    raise RuntimeError("No JINAAI_API_KEY or FIRECRAWL_API_KEY in env (demos/.env).")


def _fetch_jina(url: str) -> str:
    import httpx

    headers = {"X-Return-Format": "markdown", "Accept": "text/plain"}
    if key := os.environ.get("JINAAI_API_KEY"):
        headers["Authorization"] = f"Bearer {key}"
    r = httpx.get(JINA_ENDPOINT + url, headers=headers, timeout=60, follow_redirects=True)
    r.raise_for_status()
    return r.text


def _fetch_firecrawl(url: str) -> str:
    import httpx

    headers = {"Authorization": f"Bearer {os.environ.get('FIRECRAWL_API_KEY', '')}"}
    r = httpx.post(
        FIRECRAWL_ENDPOINT,
        headers=headers,
        json={"url": url, "formats": ["markdown"]},
        timeout=90,
    )
    r.raise_for_status()
    return r.json().get("data", {}).get("markdown", "")


def fetch_markdown(url: str, provider: str = "auto") -> str:
    """Fetch `url` as markdown via Jina or Firecrawl. Cached by (provider, url)."""
    prov = _provider(provider)
    fetcher = {"jina": _fetch_jina, "firecrawl": _fetch_firecrawl}[prov]
    return cached(key_for(url, tag=f"fetch-{prov}"), lambda: fetcher(url))  # type: ignore[return-value]


def naive_graph_from_url(url: str, provider: str = "auto", max_chars: int = 8000):
    """Fetch → free-form extract (v0) → naive graph. Returns (graph, markdown).

    `max_chars` caps the markdown fed to the extractor (web pages get large) — keeps
    the demo fast/cheap; raise it for richer graphs.
    """
    from .extract import extract_freeform
    from .graph import build_naive_graph

    markdown = fetch_markdown(url, provider=provider)
    triples = extract_freeform(markdown[:max_chars])
    return build_naive_graph(triples), markdown
