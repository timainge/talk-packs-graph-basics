"""[MONEY] Load committed benchmark/result artifacts — no private code in this repo.

The real pipelines live in separate, purpose-built repos:
  - judgements   → the *reliable* anchor (precedent / landmark detection)
  - proving-ground → the *cheaper / smarter* anchor (code-graph navigation cost)

We commit only their *exported results* (JSON under artifacts/<source>/) so the talk can
report real numbers and tour real figures without shipping the private pipelines.
"""

from __future__ import annotations

import json
from pathlib import Path

ARTIFACTS_ROOT = Path(__file__).resolve().parent.parent / "artifacts"


def load_benchmark(name: str, source: str = "judgements") -> dict | list:
    """Load a committed benchmark result by stem, e.g.
    load_benchmark('cost_collapse', source='proving-ground')."""
    path = ARTIFACTS_ROOT / source / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No exported benchmark '{name}' under artifacts/{source}/. "
            f"Export it from the private {source} repo and commit the result file."
        )
    return json.loads(path.read_text())


def list_benchmarks(source: str = "judgements") -> list[str]:
    """Available exported benchmark stems for a source."""
    src = ARTIFACTS_ROOT / source
    return sorted(p.stem for p in src.glob("*.json")) if src.exists() else []


def list_sources() -> list[str]:
    """Artifact sources that have at least one committed file."""
    if not ARTIFACTS_ROOT.exists():
        return []
    return sorted(d.name for d in ARTIFACTS_ROOT.iterdir() if d.is_dir() and any(d.glob("*.json")))
