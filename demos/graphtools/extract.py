"""[HOW · Act I] Schema-first extraction: recipe text -> typed records.

Recipe model GROWS across the acts (see plan.md):
  v1 (here)  — CONTAINS {qty, unit}, HAS_STEP, TECHNIQUE. More than a star, still naive.
  v2 (Act II)— resolved ingredients + canonical units + IS_A category. TODO in resolve.py.
  v3 (Act III)— enriched edges SUBSTITUTES_FOR / PAIRS_WITH / DERIVES_FROM. TODO.

Extraction is wrapped in replay.cached() so the live demo is deterministic.
"""

from __future__ import annotations

import functools
import os

from pydantic import BaseModel, Field

from .replay import cached, key_for

MODEL = os.environ.get("GRAPHTOOLS_MODEL", "anthropic:claude-sonnet-4-6")


# --- recipe model v1 -------------------------------------------------------

class Ingredient(BaseModel):
    name: str
    quantity: float | None = Field(None, description="numeric amount, if stated")
    unit: str | None = Field(None, description="verbatim unit, e.g. 'cup', 'g', 'tbsp'")


class Step(BaseModel):
    text: str
    technique: str | None = Field(None, description="primary verb, e.g. 'saute', 'fold'")
    uses: list[str] = Field(default_factory=list, description="ingredient names used here")


class Recipe(BaseModel):
    title: str
    ingredients: list[Ingredient]
    steps: list[Step]


# --- the extractor ---------------------------------------------------------

@functools.cache
def _agent():
    """Build the extractor lazily — importing graphtools must not require an API key
    (graph.py / algos.py reuse this module's schemas with no LLM involved)."""
    from pydantic_ai import Agent

    from .replay import load_env

    load_env()  # pull demos/.env into the environment (uv run doesn't auto-load it)
    return Agent(
        MODEL,
        output_type=Recipe,
        system_prompt=(
            "Extract the recipe into structured records. Capture each ingredient with its "
            "numeric quantity and verbatim unit, and each step with its primary technique "
            "verb and the ingredients it uses. Do not normalise or invent values yet."
        ),
    )


def extract_recipe(text: str) -> Recipe:
    """Extract a Recipe from raw text. Replays from cache by default (see replay.py)."""
    data = cached(key_for(text, tag="recipe-v1"), lambda: _agent().run_sync(text).output.model_dump())
    return Recipe.model_validate(data)


# --- the schema-first v2 extractor (Act II) --------------------------------

# v2 reuses the v1 Recipe/Ingredient/Step models unchanged (so `import graphtools`
# and build_graph keep working), but the prompt now carries the schema contract:
# conform to it, standardise units (mass -> grams, volume -> millilitres), and emit
# clean canonical ingredient names. This is the "put the schema + units in the prompt"
# beat — the before/after that motivates resolve.py.

V2_SYSTEM_PROMPT = (
    "You extract recipes into a STRICT, schema-conformant graph-ready form. "
    "Follow these rules exactly:\n"
    "1. CANONICAL UNITS. Convert every quantity to standardised SI units:\n"
    "   - mass -> grams, with unit 'g' (e.g. 0.5 kg -> 500 g; 1 oz -> 28 g; 1 lb -> 454 g).\n"
    "   - volume -> millilitres, with unit 'ml' (e.g. 1 cup -> 240 ml; 1 tbsp -> 15 ml; "
    "1 tsp -> 5 ml; 1 litre -> 1000 ml).\n"
    "   - For volume-or-mass dry goods given in cups/tbsp/tsp, convert as VOLUME to ml "
    "(do not guess densities). Keep the numeric `quantity` and set `unit` to 'g' or 'ml'.\n"
    "   - Genuinely countable items (eggs, cloves, cans, whole onions) keep a null unit and "
    "their count as quantity. A 'pinch'/'to taste' with no number -> quantity null, unit null.\n"
    "2. CANONICAL NAMES. Use a clean, lowercase, singular common name for each ingredient "
    "('plain flour'/'all-purpose' -> 'flour'; 'Challots' -> 'shallot'; 'Cannellini Beans' -> "
    "'cannellini bean'). Strip brand names, packaging and adjectives that are not part of the "
    "ingredient identity (drop 'chopped', 'fresh', 'large'; keep distinguishing words like "
    "'smoked' or 'self-raising').\n"
    "3. STEPS. Capture each step with its primary technique verb (lowercase) and the canonical "
    "ingredient names it uses (matching the names in `ingredients`). If a single step, "
    "as written in the recipe, uses multiple verbs, break them down into multiple steps, "
    "each with a single verb that acts on one or more ingredients\n"
    "Conform to the schema; do not invent ingredients that are not present in the text."
)


@functools.cache
def _agent_v2():
    """Lazy schema-first extractor for Act II. Separate cached agent from v1 so the two
    prompts/caches never collide; same lazy/no-API-key-on-import contract as `_agent`."""
    from pydantic_ai import Agent

    from .replay import load_env

    load_env()  # pull demos/.env into the environment (uv run doesn't auto-load it)
    return Agent(
        MODEL,
        output_type=Recipe,
        system_prompt=V2_SYSTEM_PROMPT,
    )


def extract_recipe_v2(text: str) -> Recipe:
    """Schema-first extraction (Act II): canonical units (grams/millilitres) and clean
    canonical ingredient names, driven by the schema-in-the-prompt instruction above.

    Reuses the v1 Recipe model but caches under the `recipe-v2` tag so v1 and v2 caches
    don't collide. Replays from cache by default (see replay.py)."""
    data = cached(key_for(text, tag="recipe-v2"), lambda: _agent_v2().run_sync(text).output.model_dump())
    return Recipe.model_validate(data)


# --- v0: the naive baseline (Act I) ----------------------------------------

# v0 is the bottom of the staircase: ask for relationships with NO domain schema,
# NO controlled vocabulary, NO entity resolution — just free-form (subject, predicate,
# object) triples. Works on *any* text. The graph you get from it
# (graph.build_naive_graph) is untyped, the
# predicate vocabulary is inconsistent, and entities don't align — that mess is the
# point. Act II then adds shape → ontology → matching to fix exactly this.

class Triple(BaseModel):
    subject: str
    predicate: str
    object: str


class _Triples(BaseModel):
    triples: list[Triple]


@functools.cache
def _agent_freeform():
    """Lazy free-form extractor — no domain schema, no controlled vocabulary."""
    from pydantic_ai import Agent

    from .replay import load_env

    load_env()
    return Agent(
        MODEL,
        output_type=_Triples,
        system_prompt=(
            "Pull the key facts out of the text as (subject, predicate, object) triples. "
            "Use whatever natural words fit — do NOT follow any fixed schema, vocabulary, "
            "or naming convention, and do NOT normalise or deduplicate. Capture entities "
            "and how they relate, verbatim."
        ),
    )


def extract_freeform(text: str) -> list[dict]:
    """[v0] Extract free-form (subject, predicate, object) triples — no schema.

    Returns a list of ``{"subject", "predicate", "object"}`` dicts. Feed to
    ``graph.build_naive_graph`` for the naive Act I graph. Replays
    from cache by default (tag ``freeform``)."""
    return cached(
        key_for(text, tag="freeform"),
        lambda: [t.model_dump() for t in _agent_freeform().run_sync(text).output.triples],
    )
