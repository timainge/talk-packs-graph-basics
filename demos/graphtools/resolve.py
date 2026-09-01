"""[HOW · Act II] Entity resolution + hybrid lookup — recipe graph v1 -> v2.

This is the talk's heart (Technique 3, "the power-up"). Get the entities right and
the relationships fall out. Stubs below mark the beats; fill as the demo is built.

  - normalise_ingredient: "plain flour" / "all-purpose" / "AP" / "maida" -> one node
  - canonical_unit:       cups <-> grams, verbatim unit -> canonical
  - hybrid_lookup:        vector + lexical match against existing entities (needs `vector` extra)

Ontology files (`data/ontology/{ingredients,units}.yaml`) are loaded once at import.
"""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

import yaml
from rapidfuzz import fuzz, process

# --- ontology loading -------------------------------------------------------

_ONTOLOGY_DIR = Path(__file__).resolve().parent.parent / "data" / "ontology"

# Fuzzy-match threshold (rapidfuzz token_sort_ratio, 0-100). A surface form must
# score at least this against a canonical name to be auto-resolved; below it we
# return the cleaned input untouched (better an unmerged node than a wrong merge).
FUZZY_THRESHOLD = 88.0


def _load_yaml(name: str) -> dict:
    path = _ONTOLOGY_DIR / name
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _build_ingredient_index(raw: dict) -> tuple[dict[str, str], list[str]]:
    """Return (synonym -> canonical map, list of canonical names).

    The canonical name maps to itself; every synonym maps to its canonical.
    Keys are cleaned (lowercased, whitespace-collapsed) for exact lookup.
    """
    syn_to_canon: dict[str, str] = {}
    canonicals: list[str] = []
    for canon, synonyms in (raw or {}).items():
        canon_clean = _clean(canon)
        canonicals.append(canon)
        syn_to_canon[canon_clean] = canon
        for syn in synonyms or []:
            syn_to_canon[_clean(syn)] = canon
    return syn_to_canon, canonicals


def _clean(text: str) -> str:
    """Lowercase, strip, collapse internal whitespace, drop surrounding punctuation."""
    text = (text or "").lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = text.strip(" .,;:")
    return text


_INGREDIENTS_RAW = _load_yaml("ingredients.yaml")
_SYN_TO_CANON, _CANONICALS = _build_ingredient_index(_INGREDIENTS_RAW)

_UNITS_RAW = _load_yaml("units.yaml")
_UNITS: dict[str, dict] = _UNITS_RAW.get("units", {})
_DENSITY_CUP_G: dict[str, float] = _UNITS_RAW.get("density_cup_g", {})

# Canonical base unit per class.
_CLASS_BASE = {"mass": "g", "volume": "ml", "count": "unit"}


# --- entity resolution ------------------------------------------------------


def normalise_ingredient(name: str) -> str:
    """Map a surface form to a canonical ingredient name.

    Strategy: clean -> exact synonym-table hit -> rapidfuzz fuzzy match against
    canonical names above ``FUZZY_THRESHOLD`` -> else return the cleaned input.
    """
    cleaned = _clean(name)
    if not cleaned:
        return cleaned

    # 1. exact synonym / canonical hit
    hit = _SYN_TO_CANON.get(cleaned)
    if hit is not None:
        return hit

    # 2. fuzzy fallback against canonical names + known synonyms
    match = process.extractOne(
        cleaned,
        sorted(_SYN_TO_CANON),  # sorted → deterministic tie-break independent of YAML order
        scorer=fuzz.token_sort_ratio,
        score_cutoff=FUZZY_THRESHOLD,
    )
    if match is not None:
        return _SYN_TO_CANON[match[0]]

    # 3. no confident match — return cleaned input rather than mis-merge
    return cleaned


# --- unit standardisation ---------------------------------------------------


def canonical_unit(
    quantity: float | None, unit: str | None
) -> tuple[float | None, str | None]:
    """Convert a verbatim (quantity, unit) to canonical units.

    Canonicalises within a unit class: mass -> g, volume -> ml, count -> unit.
    Generic volume conversions (incl. cup -> ml at ~240 ml) are handled here.

    NOTE: density-based cup -> g conversion needs ingredient context (e.g. a cup
    of flour vs a cup of water differ in grams) and so is *not* done here — the
    signature is unit-only by design. The density table lives in units.yaml and
    is applied by the higher-level v2 extractor (D2.3). Future work: ingredient-aware
    cup -> g helper.
    """
    if unit is None:
        return quantity, None

    key = _clean(unit)
    spec = _UNITS.get(key)
    if spec is None:
        # unknown unit — return the cleaned verbatim form, quantity untouched
        return quantity, key or None

    base = _CLASS_BASE[spec["class"]]
    if quantity is None:
        return None, base

    return float(quantity) * float(spec["factor"]), base


# Weighting for the hybrid score. Vector similarity captures semantic kinship
# ("AP" ~ "all-purpose flour" even with no shared characters); lexical ratio
# catches surface/typo overlap the embedding may smear. We lean on the vector
# signal (0.6) as the primary cue and use lexical (0.4) as a tie-breaker that
# rewards literal token overlap. Both are normalised to [0, 1] first.
_VECTOR_WEIGHT = 0.6
_LEXICAL_WEIGHT = 0.4

# Embedding model — small, fast, offline once cached (~90MB weights).
_EMBED_MODEL_NAME = "all-MiniLM-L6-v2"


@cache
def _embed_model():
    """Lazily load + cache the sentence-transformers model.

    Imported *inside* the function so ``import graphtools`` stays light and fully
    offline — torch / sentence-transformers are only pulled when hybrid_lookup
    is actually called.
    """
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(_EMBED_MODEL_NAME)


def hybrid_lookup(query: str, candidates: list[str], top: int = 5) -> list[str]:
    """Rank `candidates` against `query` by a hybrid vector + lexical score.

    Combines a semantic **vector** score (sentence-transformers
    ``all-MiniLM-L6-v2`` cosine similarity, mapped from [-1, 1] to [0, 1]) with a
    **lexical** score (rapidfuzz ``token_sort_ratio``, 0-100 mapped to [0, 1]) as a
    weighted sum: ``0.6 * vector + 0.4 * lexical``. Returns the best-first list of
    the top-``top`` candidate strings.

    Requires the `vector` extra (sentence-transformers); imported lazily so the
    base ``import graphtools`` stays light and offline.
    """
    if not candidates:
        return []

    model = _embed_model()
    embeddings = model.encode(
        [query, *candidates], normalize_embeddings=True
    )
    query_vec = embeddings[0]
    cand_vecs = embeddings[1:]

    scored: list[tuple[float, str]] = []
    for cand, cand_vec in zip(candidates, cand_vecs):
        # cosine similarity (both already L2-normalised) -> [-1, 1] -> [0, 1]
        cosine = float(query_vec @ cand_vec)
        vector_score = (cosine + 1.0) / 2.0

        # rapidfuzz token_sort_ratio is 0-100 -> [0, 1]
        lexical_score = fuzz.token_sort_ratio(query, cand) / 100.0

        combined = _VECTOR_WEIGHT * vector_score + _LEXICAL_WEIGHT * lexical_score
        scored.append((combined, cand))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [cand for _, cand in scored[:top]]
