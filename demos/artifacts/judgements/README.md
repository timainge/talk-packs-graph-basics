# judgements — the landmark-law example (REAL)

The real-world material behind the talk's **"PPR in the wild — landmark law"** example. Nothing
here runs live; the result and figure are committed so the Act III notebook (section 1) can tour
them offline.

## Provenance

A public, redistributable **US Supreme Court citation graph**: **27,885 cases / 234,312 citations**
(an edge means *A cited B as precedent*). Built from CourtListener (Public Domain Mark) opinions plus
Supreme Court Database (SCDB) issue areas, via the `idc9/law-net` dataset; snapshot 2026-03-31. The
method follows **Fowler & Jeon (2008), *The Authority of Supreme Court Precedent*** — so this
reproduces a peer-reviewed result on open data rather than inventing one. Every case name is real.

## Files

| File | What |
|---|---|
| `ppr_landmark.json` | The result: Personalised PageRank seeded on a *routine* 2013 case (**Kansas v. Cheever**) ranks **Miranda v. Arizona (1966)** at **#8 of 27,885** — never directly cited, surfaced two citation hops out. Keys: `seed`, `landmark`, `hops`, `citation_path`. |
| `eval.json` | The landmark set used to check the method, and how PPR / authority / in-degree measures fare against it. Includes the honest caveat that naive global HITS/PageRank gets captured by a densely cross-citing First Amendment cluster (the TKC effect). |
| `figures/fig_ppr_path.png` | The citation chain *Cheever → Estelle v. Smith → Miranda*, rendered. |

`graphtools.bench.load_benchmark("ppr_landmark", source="judgements")` loads the result.

## Read this before you quote a number

- The result is from **US SCOTUS** specifically; confirm the framing before reusing it for another
  jurisdiction.
- The deck's graphic shows a legible neighbourhood around the chain, not all 28k nodes.
- Check any on-screen number against the committed JSON.

References: Fowler & Jeon, *The Authority of Supreme Court Precedent* (Social Networks, 2008) ·
CourtListener (Free Law Project) · Supreme Court Database (SCDB) · `idc9/law-net`. Links in the
pack's `FURTHER-READING.md`.
