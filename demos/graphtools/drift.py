"""[--- · Act II] THE drift visualisation — load-bearing, SIDEQUEST (build last).

This is the "slide into the valley": a naive, schemaless graph looks brilliant at
small N and quietly falls apart at scale. The D3.1 spike proved the *fragmentation*
framing (Option A) is a FALSE story for recipes — shared pantry staples (sugar,
salt, butter, water) bind almost everything into one connected component, so the
graph never shatters.

So we pivot to **Option C — duplicate-collapse / node inflation**. The honest
failure mode resolution fixes here is the *duplicate smear*: as N grows, the count
of distinct ingredient *surface forms* climbs fast (every "finely chopped fresh
garlic" / "2 cloves garlic, minced" is a new node), while the count of
*canonicalised* ingredients grows far slower. The widening gap between the two
curves is the valley.

ILLUSTRATIVE CANONICALISATION (not the production resolver)
-----------------------------------------------------------
``resolve.normalise_ingredient`` is a 49-entry curated ontology; the spike showed
it only merges ~1.3% of surface forms — far too weak to show a gap. For the *viz*
we use a stronger, documented, tractable canonicaliser (``_canonicalise`` below):

  1. derive a rough ingredient name (strip leading quantity/unit tokens, drop
     trailing ", chopped" / "(optional)" descriptors) — this is the SURFACE FORM;
  2. strip preparation adjectives + descriptors ("chopped/fresh/dried/minced/
     ground/large/...") anywhere in the name;
  3. lowercase + naive singularisation of each token;
  4. a light fuzzy-bucket pass (rapidfuzz token_sort_ratio >= 90) that merges
     near-duplicate canonical strings, BLOCKED on the head-noun (last token) so the
     pass stays O(N·k) per block, not O(N^2).

This is deliberately heuristic — it over-merges in places and is NOT how the real
resolver works. It exists to make the *shape* of the problem legible, nothing more.
"""

from __future__ import annotations

import json
import re
import warnings
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless / deterministic
import matplotlib.pyplot as plt  # noqa: E402
from rapidfuzz import fuzz, process  # noqa: E402

# --- corpus location --------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "scale"
_SCALE_LOCAL = _DATA_DIR / "local" / "recipes.jsonl"
_SCALE_SAMPLE = _DATA_DIR / "sample.jsonl"


def _default_corpus() -> Path:
    """Full 10k local corpus if present (gitignored), else the committed sample."""
    return _SCALE_LOCAL if _SCALE_LOCAL.exists() else _SCALE_SAMPLE


# --- surface-form derivation ------------------------------------------------

# Leading quantity / fraction / punctuation tokens.
_QTY = re.compile(r"^[\s\d¼-¾⅐-⅞/.\-]+")

# Trailing prep clauses and parentheticals: ", chopped" / "(optional)" / "to taste".
_PREP_TAIL = re.compile(r",.*$|\(.*?\)|\bto taste\b|\boptional\b", re.IGNORECASE)

# Measurement/packaging unit words to drop from the *front* of a derived name.
_UNITS = {
    "c", "cup", "cups", "tsp", "teaspoon", "teaspoons", "tbsp", "tablespoon",
    "tablespoons", "oz", "ounce", "ounces", "lb", "lbs", "pound", "pounds",
    "g", "gram", "grams", "kg", "ml", "l", "litre", "liter", "pkg", "pkgs",
    "package", "packages", "can", "cans", "jar", "jars", "box", "boxes",
    "pint", "pints", "quart", "quarts", "gal", "gallon", "stick", "sticks",
    "clove", "cloves", "slice", "slices", "pinch", "dash", "bunch", "head",
    "envelope", "container", "cube", "cubes", "sprig", "sprigs", "piece",
    "pieces", "fl",
}

# Preparation adjectives / descriptors stripped *anywhere* in the canonical pass.
# Deliberately broad — this over-merges, which is fine for an illustrative viz.
_DESCRIPTORS = set(
    """
    chopped fresh dried minced ground grated shredded sliced diced crushed peeled
    cooked softened melted beaten packed firmly finely coarsely roughly thinly
    thickly cut halved quartered boneless skinless frozen canned drained rinsed
    toasted roasted raw ripe unripe unsalted salted cold warm hot room temperature
    prepared crumbled mashed seeded trimmed washed cubed julienned shelled pitted
    divided plus extra more taste optional such lean light dark heavy sweet mild
    small medium large whole boiling lukewarm pure all natural organic low reduced
    free fat good quality best ready store bought homemade about approximately or
    and into for as needed your favorite favourite new old baby mini jumbo regular
    thin thick fine coarse semi very with without flat smooth creamy solid liquid
    powdered granulated
    """.split()
)


def _derive_surface(raw: str) -> str:
    """Strip leading quantity/unit/punctuation -> a rough ingredient SURFACE form.

    This intentionally keeps preparation adjectives ("finely chopped fresh ...")
    so that genuinely different phrasings of the same ingredient remain *distinct*
    surface forms — that is exactly the inflation we are measuring.
    """
    s = raw.lower().strip()
    s = _PREP_TAIL.sub("", s)
    s = _QTY.sub("", s)
    s = s.replace(".", " ")
    toks = s.split()
    while toks and toks[0] in _UNITS:
        toks.pop(0)
    return " ".join(toks).strip(" .,;:-")


def _singularise(word: str) -> str:
    """Naive English singularisation (no dictionary; heuristic only)."""
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith(("oes", "ses", "xes", "zes")) and len(word) > 4:
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def _canonicalise(surface: str) -> str:
    """Collapse a surface form towards a canonical ingredient name (illustrative).

    Strip preparation descriptors + bare digits, singularise remaining tokens.
    Returns "" if nothing survives. (The fuzzy-bucket pass runs separately, over
    the *set* of these strings, in ``_count_at_scale``.)
    """
    toks = [
        _singularise(t)
        for t in surface.split()
        if t not in _DESCRIPTORS and not t.isdigit()
    ]
    return " ".join(toks).strip()


# Fuzzy-bucket threshold (rapidfuzz token_sort_ratio, 0-100). Two canonical strings
# in the same head-noun block that score >= this are treated as one ingredient.
_FUZZY_THRESHOLD = 90.0


def _fuzzy_bucket(names: set[str]) -> int:
    """Greedily merge near-duplicate canonical strings; return distinct count.

    BLOCKING on the head noun (last token) keeps this O(N·k) per block instead of
    O(N^2): a candidate is only compared against existing representatives that
    share its head noun. Deterministic (inputs sorted before bucketing).
    """
    reps_by_head: dict[str, list[str]] = defaultdict(list)
    total = 0
    for name in sorted(names):
        head = name.rsplit(" ", 1)[-1] if name else name
        cands = reps_by_head[head]
        match = (
            process.extractOne(
                name, cands, scorer=fuzz.token_sort_ratio,
                score_cutoff=_FUZZY_THRESHOLD,
            )
            if cands
            else None
        )
        if match is None:
            cands.append(name)
            total += 1
    return total


# --- corpus loading + counting ----------------------------------------------


def _load_rows(corpus_path: Path, limit: int) -> list[dict]:
    rows: list[dict] = []
    with corpus_path.open(encoding="utf-8") as fh:
        for line in fh:
            if len(rows) >= limit:
                break
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _count_at_scale(rows: list[dict]) -> tuple[int, int]:
    """Return (distinct surface forms, distinct canonicalised ingredients)."""
    surfaces: set[str] = set()
    canon: set[str] = set()
    for row in rows:
        for raw in row.get("ingredients", []):
            surface = _derive_surface(raw)
            if not surface:
                continue
            surfaces.add(surface)
            c = _canonicalise(surface)
            if c:
                canon.add(c)
    return len(surfaces), _fuzzy_bucket(canon)


# --- public figure ----------------------------------------------------------


def drift_figure(
    corpus_path: str | Path | None = None,
    scales: tuple[int, ...] = (10, 100, 1000, 10000),
    path: str | Path | None = None,
):
    """Render the duplicate-smear drift figure (Option C).

    For each N in ``scales`` over the first N recipes of the corpus, count
    (a) distinct raw ingredient SURFACE forms and (b) distinct CANONICALISED
    ingredients (see module docstring for the illustrative canonicaliser). Plot
    both against N on a log x-axis: surface forms climb, canonical grows slower —
    the widening gap is "the slide into the valley".

    Args:
        corpus_path: jsonl of ``{"title", "ingredients": [...]}`` rows. Defaults to
            the full local 10k corpus if present, else the committed sample.
        scales: the N values to measure (clamped to corpus size; deduped).
        path: if given, save a PNG there and return the path; else return the
            matplotlib Figure.

    Returns:
        The saved ``Path`` if ``path`` was given, otherwise the ``Figure``.
    """
    corpus = Path(corpus_path) if corpus_path is not None else _default_corpus()
    if not corpus.exists():
        raise FileNotFoundError(f"drift corpus not found: {corpus}")

    max_n = max(scales)
    all_rows = _load_rows(corpus, max_n)
    avail = len(all_rows)
    if avail < max_n:
        warnings.warn(
            f"drift corpus '{corpus.name}' has only {avail} rows; scales above {avail} "
            f"are clamped — the headline ratio reflects N={avail}, not {max_n}. "
            f"Fetch the full corpus (scripts/fetch_scale.py) for the 10k figure.",
            stacklevel=2,
        )
    ns = sorted({min(n, avail) for n in scales if min(n, avail) > 0})

    surface_counts: list[int] = []
    canon_counts: list[int] = []
    for n in ns:
        s, c = _count_at_scale(all_rows[:n])
        surface_counts.append(s)
        canon_counts.append(c)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(
        ns, surface_counts, "o-", color="#c0392b", linewidth=2.2,
        markersize=7, label="distinct surface forms (naive)",
    )
    ax.plot(
        ns, canon_counts, "s-", color="#27ae60", linewidth=2.2,
        markersize=7, label="distinct canonicalised ingredients",
    )
    # Shade the duplicate smear between the curves.
    ax.fill_between(
        ns, canon_counts, surface_counts, color="#c0392b", alpha=0.08,
    )
    ax.set_xscale("log")
    ax.set_xlabel("recipes ingested (N, log scale)")
    ax.set_ylabel("distinct ingredient nodes")
    ax.set_title("The slide into the valley:\nduplicate ingredient nodes inflate as N grows")
    ax.grid(True, which="both", linestyle=":", alpha=0.4)
    ax.legend(loc="upper left", frameon=False)

    # Annotate the gap at the largest N.
    if ns:
        x = ns[-1]
        ax.annotate(
            f"{surface_counts[-1]:,} surface forms\nvs {canon_counts[-1]:,} canonical "
            f"(×{surface_counts[-1] / max(canon_counts[-1], 1):.2f})",
            xy=(x, surface_counts[-1]),
            xytext=(0.55, 0.30), textcoords="axes fraction",
            fontsize=9, color="#7f1d1d",
            arrowprops=dict(arrowstyle="->", color="#7f1d1d", alpha=0.6),
        )
    fig.tight_layout()

    if path is not None:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=150)
        plt.close(fig)
        return out
    return fig
