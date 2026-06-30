# judgements artifacts — tour, don't run

These are **exported outputs** committed so the Act III "landmark" beats can be toured without
running any pipeline. Nothing in this folder runs live — they are pre-baked figures and result JSON.

## Provenance & status

- **`ppr_landmark.json`, `hits_landmarks.json`, `eval.json`, `figures/` — REAL.** They come from a
  public, redistributable **US SCOTUS citation graph** (the sibling `caselaw-graph` build):
  CourtListener Public Domain Mark + the Supreme Court Database (SCDB) issue areas, via the
  `idc9/law-net` dataset — **27,885 cases / 234,312 citations** (snapshot 2026-03-31), validated
  against **Fowler & Jeon (2008)**. Case names are real US landmarks (Miranda, Mapp, Gideon, …).
- **`subgraph_match.json` — SAMPLE.** An illustrative fact-pattern motif with obvious placeholder
  names. It carries a `_status` SAMPLE line; do not present it as a finding. The real subgraph /
  shortest-path payoff is carried by the sibling **`code-graph`** artifacts instead.

> US public-domain court opinions, so the data is safe to redistribute. The figures are presentation
> exports only — no pipeline code ships here.

## What `bench.load_benchmark` loads

`load_benchmark(name, source='judgements')` resolves to `artifacts/judgements/<name>.json`. Three
stems back the three Act III judgements beats:

- **`ppr_landmark.json`** — *"PPR surfaced this landmark N hops from the seed."* Keys: `seed`,
  `landmark`, `hops`, `citation_path`. (REAL: directed PPR, routine seed *Kansas v. Cheever (2013)*
  → **Miranda (1966)**, 2 citation-hops.)
- **`hits_landmarks.json`** — *"top authorities (landmarks) + top hubs."* Keys: `authorities[]`,
  `hubs[]`, each with a score. (REAL: HITS on the exclusionary-rule carve-out — authorities led by
  Miranda; hubs are Miranda-progeny survey opinions.)
- **`subgraph_match.json`** — *"fact-pattern matches."* Keys: `pattern`, `matches[]`. (SAMPLE.)

`figures/` holds the rendered PNGs: `fig_hits_authorities.png`, `fig_carveout_network.png`,
`fig_ppr_path.png`.

## Caveats to carry to a slide

- The PPR/HITS landmark results are from **US SCOTUS** specifically — confirm the framing before
  reusing them for any other jurisdiction.
- `subgraph_match.json` is a **SAMPLE** — names are placeholders, not findings.
- Verify any on-screen number against the committed JSON before it goes on a slide.

## References

Fowler & Jeon, *The Authority of Supreme Court Precedent* (Social Networks, 2008) · CourtListener
(Free Law Project) · Supreme Court Database (SCDB) · `idc9/law-net`.
