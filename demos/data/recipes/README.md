# Recipe corpus — the hero set

14 hand-picked recipes from [TheMealDB](https://www.themealdb.com/) (free JSON API), committed as
local JSON so the extraction demos are deterministic. Each file is one recipe; the `text` field is
the human-readable blob (ingredient lines + method) that the extractor is given.

`scripts/fetch_recipes.py` re-fetches them. Keep the set small and curated — the point is a corpus
you can read end to end.
