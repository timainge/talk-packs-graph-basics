# Recipe corpus — the live hero set

~12 hand-picked recipes, committed as local JSON, for **deterministic live extraction**
in Act I/II. Each file is one recipe.

## Sources (fastest first)

- **TheMealDB** — free JSON API (~300 recipes, categories + cuisines), zero friction. Good default.
- **schema.org/Recipe JSON-LD** — most real recipe sites (incl. RecipeTin Eats) embed a clean
  structured blob per page. "Scraping" is just pulling the JSON-LD — and *it's already a
  de-facto recipe schema in the wild* (a nice Act II beat). Get permission first (asking Nagi).

Keep this set small and curated — it's what we extract live. Scale lives in `../scale/`.
