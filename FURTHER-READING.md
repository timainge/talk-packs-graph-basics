# Further reading

The pointers promised from the stage: the sources behind each section of the talk, the variants
of each algorithm and where they're used, and notes on the things we didn't get to. Everything is
grouped in the order the talk ran. Where a source is a paper, the link is to the open version
where one exists.

> **A note on numbers.** The pack does not vouch for third-party figures (Pixie's latency, HippoRAG's
> gains, and so on). Where the deck quotes one it is attributed and dated; check the primary source
> before you repeat it. Our own measured numbers carry their bounds in `demos/artifacts/*/README.md`.

## 1. Building better graphs

**Extracting a "no schema" graph (the naive baseline).** The free-form `(subject, predicate,
object)` approach has a name — *Open Information Extraction*.
- [Open information extraction — Wikipedia](https://en.wikipedia.org/wiki/Open_information_extraction)
  — a short history of the idea and its systems. Useful when you need a graph out of *anything*;
  the price is inconsistent vocabulary and unmatched entities.

**Give the extractor a shape (schema / structured outputs).**
- [Pydantic AI](https://ai.pydantic.dev/) — the agent framework used in the demos; `output_type=`
  is how the schema becomes the contract.
- [schema.org/Recipe](https://schema.org/Recipe) — most recipe sites already embed this; a reminder
  that a de-facto schema often exists before you design one.

**Add an ontology (what goes *into* the shape).** The in-prompt rules in the talk are the
lightweight version of what controlled vocabularies do in production:
- [UMLS](https://www.nlm.nih.gov/research/umls/index.html) (medicine),
  [FIBO](https://spec.edmcouncil.org/fibo/) (finance), [schema.org](https://schema.org/) (the web).

**Match your entities.**
- Fellegi & Sunter, *A Theory for Record Linkage* (JASA, 1969) —
  [DOI 10.1080/01621459.1969.10501049](https://doi.org/10.1080/01621459.1969.10501049) — the
  classic probabilistic framing of "are these two records the same thing?".
- [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) — the lexical (spelling) score in the demo's
  hybrid matcher.
- [Sentence-Transformers](https://sbert.net/) — the embedding model (`all-MiniLM-L6-v2`) behind the
  semantic (meaning) score. Hybrid = cheap exact matches first, embeddings for the long tail.

## 2. Graph queries

- [Neo4j Cypher manual — patterns and variable-length paths](https://neo4j.com/docs/cypher-manual/current/patterns/variable-length-patterns/)
  — the `[:TYPE*1..n]` syntax that makes "5, 10, 20 hops" a one-liner.
- [NetworkX](https://networkx.org/documentation/stable/) — the in-memory graph library every demo
  runs on. No database needed to learn the algorithms.

## 3. Personalised PageRank (PPR) — and its variants

**The idea and its family.** Vanilla PageRank teleports to a random node (global importance); PPR
teleports back to a chosen seed (importance *relative to the seed*). Names you'll meet for the same
family: *random walk with restart (RWR)*, *topic-sensitive PageRank*, *personalised random walks*.

- Brin & Page, *The Anatomy of a Large-Scale Hypertextual Web Search Engine* (WWW 1998) —
  [Stanford InfoLab](http://infolab.stanford.edu/~backrub/google.html) — the original.
- Haveliwala, *Topic-Sensitive PageRank* (WWW 2002) —
  [ACM DL](https://dl.acm.org/doi/10.1145/511446.511513) — bias the walk toward a topic's seed set.
- Jeh & Widom, *Scaling Personalized Web Search* (WWW 2003) —
  [ACM DL](https://dl.acm.org/doi/10.1145/775152.775191) — the canonical PPR paper.
- Tong, Faloutsos & Pan, *Fast Random Walk with Restart and Its Applications* (ICDM 2006) —
  [DOI 10.1109/ICDM.2006.70](https://doi.org/10.1109/ICDM.2006.70) — RWR for proximity /
  recommendation; the formulation most graph databases implement.
- Andersen, Chung & Lang, *Local Graph Partitioning using PageRank Vectors* (FOCS 2006) —
  [ACM DL](https://dl.acm.org/doi/10.1109/FOCS.2006.44) — "forward push", the approximation that
  makes PPR cheap on huge graphs. Also the bridge to *clustering* (below).
- NetworkX [`pagerank(personalization=...)`](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.link_analysis.pagerank_alg.pagerank.html)
  — what the demo calls.

**Where it's used.**
- *Recommendations at scale* — Eksombatchai et al. (Pinterest), *Pixie: A System for Recommending
  3+ Billion Items to 200+ Million Users in Real-Time* (WWW 2018) —
  [arXiv:1711.07601](https://arxiv.org/abs/1711.07601). The reference point mentioned in the talk.
- *Who to follow* — Gupta et al., *WTF: The Who to Follow Service at Twitter* (WWW 2013) —
  [PDF](https://stanford.edu/~rezab/papers/wtf_overview.pdf) — PPR as the "circle of trust" seed.
- *Retrieval for LLMs* — Gutiérrez et al., *HippoRAG* (NeurIPS 2024) —
  [arXiv:2405.14831](https://arxiv.org/abs/2405.14831) · [code](https://github.com/OSU-NLP-Group/HippoRAG);
  and *HippoRAG 2 — From RAG to Memory* (ICML 2025) —
  [arXiv:2502.14802](https://arxiv.org/abs/2502.14802). Builds a graph with OpenIE-style extraction,
  then runs PPR from the entities in the question to rank passages — the contemporary example from
  the talk.
- *Landmark law* — Fowler & Jeon, *The Authority of Supreme Court Precedent* (Social Networks,
  2008) — [DOI 10.1016/j.socnet.2007.05.001](https://doi.org/10.1016/j.socnet.2007.05.001) — the
  peer-reviewed result our SCOTUS example reproduces. Data: [CourtListener](https://www.courtlistener.com/)
  · [Supreme Court Database](http://scdb.wustl.edu/) · [idc9/law-net](https://github.com/idc9/law-net).

## 4. Shortest path — and its variants

**Variants named in the talk and where to find them.**
- *Shortest path* — Dijkstra (1959) — [DOI 10.1007/BF01386390](https://doi.org/10.1007/BF01386390);
  NetworkX [`shortest_path`](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.shortest_paths.generic.shortest_path.html).
- *K shortest paths* (several routes, ranked) — Yen (1971) —
  [DOI 10.1287/mnsc.17.11.712](https://doi.org/10.1287/mnsc.17.11.712); NetworkX
  [`shortest_simple_paths`](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.simple_paths.shortest_simple_paths.html).
- *Cheapest path on weighted edges* — Dijkstra with `weight=`; with a heuristic, A* — Hart, Nilsson
  & Raphael (1968) — [DOI 10.1109/TSSC.1968.300136](https://doi.org/10.1109/TSSC.1968.300136).
- *Path through a given node* — two shortest paths joined (as in the notebook), or a variable-length
  pattern with a `WHERE` clause in Cypher.

**Where it's used.** Every package manager already ships "shortest path as explanation":
[`npm explain` / `npm why`](https://docs.npmjs.com/cli/v11/commands/npm-explain/) ·
[`pnpm why`](https://pnpm.io/cli/why) · [`cargo tree --invert`](https://doc.rust-lang.org/cargo/commands/cargo-tree.html)
· [`go mod why`](https://pkg.go.dev/cmd/go#hdr-Explain_why_packages_or_modules_are_needed).
Security scanners present findings as paths too:
[CodeQL path queries](https://codeql.github.com/docs/writing-codeql-queries/creating-path-queries/).

**Paths as context for agents (the eShop example).**
- Chen et al., *LocAgent: Graph-Guided LLM Agents for Code Localization* (ACL 2025) —
  [arXiv:2503.09089](https://arxiv.org/abs/2503.09089) — the published anchor for graph-navigated
  code search; our own small-n measurement is in `demos/artifacts/proving-ground/`.
- Tan et al., *Paths-over-Graph* (2024) — [arXiv:2410.14211](https://arxiv.org/abs/2410.14211) —
  retrieving multi-hop knowledge-graph paths to ground LLM answers.

## 5. Exact subgraph matching

**The algorithms.**
- Ullmann, *An Algorithm for Subgraph Isomorphism* (JACM 1976) —
  [ACM DL](https://dl.acm.org/doi/10.1145/321921.321925) — the original backtracking search.
- Cordella et al., *VF2* (IEEE TPAMI 2004) — [DOI 10.1109/TPAMI.2004.75](https://doi.org/10.1109/TPAMI.2004.75)
  — what NetworkX's [`DiGraphMatcher`](https://networkx.org/documentation/stable/reference/algorithms/isomorphism.vf2.html)
  implements and the demo uses.
- McCreesh, Prosser & Trimble, *The Glasgow Subgraph Solver* (ICGT 2020) —
  [PDF](https://ciaranm.github.io/papers/icgt2020-glasgow-subgraph-solver.pdf) — the fast
  constraint-programming solver for when VF2 is too slow.

**Where it's used** — "find the shape, not the keyword":
- *Code patterns / vulnerabilities* — Yamaguchi et al., *Modeling and Discovering Vulnerabilities
  with Code Property Graphs* (IEEE S&P 2014) — [DOI 10.1109/SP.2014.44](https://doi.org/10.1109/SP.2014.44)
  ([Joern](https://joern.io/)); [CodeQL](https://codeql.github.com/); Tsantalis et al., *Design
  Pattern Detection Using Similarity Scoring* (IEEE TSE 2006) —
  [DOI 10.1109/TSE.2006.112](https://doi.org/10.1109/TSE.2006.112) — the decorator-pattern search in
  the talk is this idea.
- *Fraud / money-laundering shapes* — Blanuša et al. (IBM), *Graph Feature Preprocessor* (ICAIF 2024)
  — [arXiv:2402.08593](https://arxiv.org/abs/2402.08593); Bellei et al., *The Shape of Money
  Laundering* (Elliptic2, 2024) — [arXiv:2404.19109](https://arxiv.org/abs/2404.19109); Hooi et al.,
  *FRAUDAR* (KDD 2016) — [ACM DL](https://dl.acm.org/doi/10.1145/2939672.2939747).

**Fuzzy / learned matching** (approximate shapes; not covered on stage):
- Ying et al., *Neural Subgraph Matching* (NeuroMatch, 2020) — [arXiv:2007.03092](https://arxiv.org/abs/2007.03092).
- Roy et al., *IsoNet* (NeurIPS 2022) — [PDF](https://indradyumna.github.io/pdfs/IsoNet_main.pdf);
  *IsoNet++* (NeurIPS 2024) — [poster](https://neurips.cc/virtual/2024/poster/93261).
- He et al., *G-Retriever* (NeurIPS 2024) — [arXiv:2402.07630](https://arxiv.org/abs/2402.07630) —
  subgraph retrieval for LLMs framed as a prize-collecting Steiner tree.
- Hu et al., *GRAG: Graph Retrieval-Augmented Generation* (NAACL Findings 2025) —
  [arXiv:2405.16506](https://arxiv.org/abs/2405.16506).

## 6. What we didn't get to

The talk toured **paths**, **ranking** and **patterns**. Three more classes of graph problem are
worth knowing about; each is a talk of its own and edges into the graph-RAG / dynamic-graph territory
the talk deliberately stayed out of.

**Prediction & completion — "which edges are missing or likely?"** Keeps a knowledge graph healthy
by filling in relationships the extractor never saw.
- Liben-Nowell & Kleinberg, *The Link-Prediction Problem for Social Networks* (JASIST 2007) —
  [DOI 10.1002/asi.20591](https://doi.org/10.1002/asi.20591) — the neighbourhood heuristics
  (common neighbours, Adamic–Adar) that are still strong baselines; NetworkX
  [link prediction](https://networkx.org/documentation/stable/reference/algorithms/link_prediction.html).
- Bordes et al., *Translating Embeddings for Modeling Multi-relational Data* (TransE, NeurIPS 2013)
  — [paper](https://papers.nips.cc/paper/5071-translating-embeddings-for-modeling-multi-relational-data);
  Sun et al., *RotatE* (ICLR 2019) — [arXiv:1902.10197](https://arxiv.org/abs/1902.10197) —
  knowledge-graph embeddings that score typed triples for completion.

**Similarity — "what else looks like this?"** Turning structure back into vectors so that nodes
(or whole subgraphs) with similar neighbourhoods land near each other.
- Perozzi et al., *DeepWalk* (KDD 2014) — [arXiv:1403.6652](https://arxiv.org/abs/1403.6652);
  Grover & Leskovec, *node2vec* (KDD 2016) — [arXiv:1607.00653](https://arxiv.org/abs/1607.00653).
- Kipf & Welling, *Graph Convolutional Networks* (ICLR 2017) — [arXiv:1609.02907](https://arxiv.org/abs/1609.02907);
  Hamilton et al., *GraphSAGE* (NeurIPS 2017) — [arXiv:1706.02216](https://arxiv.org/abs/1706.02216)
  — graph neural networks, the engine under the learned matchers and many graph-RAG retrievers.

**Clustering / community detection — "what natural groups are in here?"**
- Blondel et al., *Fast unfolding of communities in large networks* (Louvain, 2008) —
  [arXiv:0803.0476](https://arxiv.org/abs/0803.0476); Traag et al., *From Louvain to Leiden* (2019)
  — [arXiv:1810.08473](https://arxiv.org/abs/1810.08473).
- Edge et al. (Microsoft), *From Local to Global: A Graph RAG Approach to Query-Focused
  Summarization* (2024) — [arXiv:2404.16130](https://arxiv.org/abs/2404.16130) — the "GraphRAG"
  pattern: Leiden communities → LLM summaries → global search. This is where the community-detection
  discourse lives, and the pattern the talk chose not to cover.
- Kleinberg, *Authoritative Sources in a Hyperlinked Environment* (HITS, JACM 1999) —
  [ACM DL](https://dl.acm.org/doi/10.1145/324133.324140) — hubs vs authorities; a close cousin of
  PageRank we cut from the talk because its lesson overlaps too much with PPR's.

**Flow and cost** (max-flow / min-cut, spanning trees, routing) — the classic network algorithms we
skipped for an AI audience: NetworkX [flows](https://networkx.org/documentation/stable/reference/algorithms/flow.html).

## The rest of the series

- **talk-packs-graph-advanced** — learned graph methods: link prediction, embeddings, community
  detection (the *prediction / similarity / clustering* threads above, in depth).
- **talk-packs-graph-advanced-ai** — AI-native: GraphRAG, schemaless extraction, agent memory.
