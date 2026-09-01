---
theme: default
colorSchema: dark
highlighter: shiki
title: A Practitioner's Guide to Graphs
info: |
  ## A Practitioner's Guide to Graphs
  AI Engineer World's Fair 2026 — Graph Track (Track 09)

  bad graph → good graph → payoff
class: text-left
drawings:
  persist: false
transition: slide-left
duration: 35min
lineNumbers: false
---
<script setup lang="ts">
import worldsfair from './assets/worldsfair.svg';
import lockup from './assets/collective-capability-lockup.svg'
</script>

<img :src="worldsfair" class="absolute top-8 left-8 h-12 opacity-60 filter grayscale" />

<h1 style="background: linear-gradient(90deg, #4269d0 0%, #efb118 22%, #ff725c 44%, #6cc5b0 64%, #3ca951 82%, #a463f2 100%); -webkit-background-clip: text; background-clip: text; color: transparent; display: inline-block;">A Practitioner's Guide to Graphs</h1>

How to make your AI applications _smarter_, _cheaper_, and more _reliable_

<img :src="lockup" class="absolute bottom-8 left-8 max-w-[calc(100%-4rem)] opacity-60 filter grayscale" />

<!--  
- Hi I'm Tim Ainge from the Good Collective.
-  Welcome to today's Ai Engineer presentation
-  A Practitioner's Guide to Graphs
-  How to make your AI applications _smarter_, _cheaper_, and more _reliable_
-->
---

<script setup lang="ts">
import valley0 from './assets/valley-of-disillusionment-0.svg'
import valley1 from './assets/valley-of-disillusionment-1.svg'
import valley2 from './assets/valley-of-disillusionment-2.svg'
import valley3 from './assets/valley-of-disillusionment-3.svg'
import valley4 from './assets/valley-of-disillusionment-4.svg'
</script>

# If I have a hammer, is everything a graph?

<div class="absolute top-28 left-1/2 -translate-x-1/2 w-[700px] aspect-[1440/843]">
  <v-switch>
    <template #0><img :src="valley0" class="absolute inset-0 w-full h-full" /></template>
    <template #1><img :src="valley1" class="absolute inset-0 w-full h-full" /></template>
    <template #2><img :src="valley2" class="absolute inset-0 w-full h-full" /></template>
    <template #3><img :src="valley3" class="absolute inset-0 w-full h-full" /></template>
    <template #4><img :src="valley4" class="absolute inset-0 w-full h-full" /></template>
  </v-switch>
</div>


<!--

1. Graphs  
  - have always been a powerful foundation of computer science, 
  - they look beautiful 
  - and sometimes genuinely not the right tool for the job.
 

2. We've all felt wonder of a mesmerising data-science graph
  - or oggled the graph view of our obsidian vault

  ----
  - it can be tempting to rush into 
    - something like graph rag or 
    - rebuilding your e-commerce shop with a graph database
  - Often.. we don't see the instant pay-off we might have expected
  - in frustration many journeys end here ... in the dust at the bottom of the valley of despair and disillusionment

3. What's on the other side, how do we get there?
  - That's exactly the question that sparked the idea for this talk, 
  - Have I nailed the answers?? definitely not all of them!
  - But what I'm finding, is that the more I learn about the fundamentals of graph data structures and algorithms, the more interesting opportunities seem to present themselves. 
  - Many of these graph-native uses cases, or "good fits for graphs", are also a lovely compliment to many of the search, pattern recognition, retrieval or knowledge based problems that are ripe for solving in the AI age.


- This talk isn't going to be about graphRAG or agent memory graphs, 
- Not because I'm throwing shade on those patterns and products
- but partly because there will be many other talks covering each of those single topics
- But more importantly, this talk is for ai builders and I'd like to focus on the underlying patterns which may just help you come up with the next big graph powered AI application.
 -->

---
clicks: 3
---

<script setup lang="ts">
import roadmap from './snippets/graph-fixtures/roadmap.json';
</script>

# The structure of things to come

<!--
  One fixture, focus-stepped per click via the fixture's `reveal` script
  (revealMode="replace" → only the current branch lights, the rest dims).
  $clicks 0 = no focus (plain map); 1/2/3 = focus basics / better / algorithms.
  Single sized container (h-100) so GraphView's height:100% resolves cleanly.
-->
<div class="h-100">
  <GraphView
    :graph="roadmap"
    :step="$clicks > 0 ? $clicks - 1 : undefined"
    reveal-mode="replace"
    :show-edge-labels="false"
    :show-legend="false" />
</div>

<!-- 
1. We'll speed run the basics of graphs
2. We'll Go through some quick tips and tricks for building better graphs to get better results.
3. And then we'll look at graph native the algorithms that leverage your graph the benefits they deliver.

---
1. At the end there will be a link to a presentation repo with the slides, source notebooks, and additional reading.
-->

---
clicks: 3
---

<script setup lang="ts">
import method from './snippets/graph-fixtures/method.json';
</script>

# The structure of things to come

<!--
  Same title, second fixture: the per-step method. Focus-stepped per click —
  $clicks 0 = no focus; 1/2/3 = principle / code / examples (single-node spotlight).
-->
<div class="h-100">
  <GraphView
    :graph="method"
    :step="$clicks > 0 ? $clicks - 1 : undefined"
    reveal-mode="replace"
    :show-edge-labels="false"
    :show-legend="false" />
</div>

<!-- 
1. At each step we'll 
  - open with a principle, 
  - code through an easy examples 
  - (we'll use recipes because I like food, and they should be pretty familiar) 
  - ... and we'll also reference some real-world examples with real world benefits as we go.
-->



---

<script setup lang="ts">
import primer from './snippets/graph-fixtures/primer.json';
</script>

# What is a graph

**Nodes, edges, weights, properties.**


<div class="h-90">
  <GraphView :graph="primer" :show-edge-labels="true" :params="{ edges: { widthByWeight: true } }" />
</div>




<!--
1. a graph is something that has nodes (also called vertices)
2. and edges, that connect or relate two nodes together

That's it, to meet the most basic definition of a graph, but **fancier graphs can also have..**

3. different types nodes and edges which conveys more semantic meaning
4. we can have labels and properties on edges and nodes
5. and of course, edges can have direction.. otherwise how else would we know that cows say moo or is it that moos say cow...  you can see the benefit of directed edges

-->

---

<script setup lang="ts">
import pocNaiveCurated from './snippets/graph-fixtures/poc-naive-curated.json';
</script>


# Extract a basic graph
**Principle:** unstructured data isn't much more helpful than unstructured text.


<div class="grid grid-cols-2 gap-6 items-center">

```python
from pydantic import BaseModel
from pydantic_ai import Agent

class Triple(BaseModel):
    subject: str
    predicate: str
    object: str

# no schema, no vocabulary, no entity resolution
agent = Agent(
    "anthropic:claude-sonnet-4-6",
    output_type=list[Triple],
    system_prompt=(
        "Pull the key facts out as (subject, predicate, "
        "object) triples. Use whatever vocab fits, yolo."
    ),
)

triples = agent.run_sync(recipe_text).output
```

<div class="h-100">
  <GraphView :graph="pocNaiveCurated" :show-edge-labels="true" :show-legend="false" />
</div>

</div>


<!-- 

Whoa, cool, we made a structured data from unstructured text.

Graph schemas vary 
  — from very specific and technical, 
  - to very flexible and free-form (no schema at all). 
  
Not terrible if you want a way to make a graph out of anything in the world.. 

(This schema-free style is called Open Information Extraction, or OpenIE — see FURTHER-READING.md in the pack.)

However we can see that 
 - the relationships are inconsistent, 
 - we have multiple nodes flour & eggs, 
 - you'd be pretty hard pressed to be able to query the ingredients from this graph...
 - and how do I even know the difference between milk and a pan?


The more we know about our domain the better we can do.
-->


---

<script setup lang="ts">
import recipeShape from './snippets/graph-fixtures/recipe-shape.json';
</script>

# Defining the schema (the shape)

**Principle:** give the extractor a shape — a `schema` — to fill. *A shape gets you structure.*

<div class="grid grid-cols-2 gap-6 items-center">

```python
from pydantic import BaseModel, Field
from pydantic_ai import Agent

class Ingredient(BaseModel):
    name: str
    quantity: float | None = None
    unit: str | None = None      # 'cup', 'g', 'tbsp'

class Recipe(BaseModel):
    title: str
    ingredients: list[Ingredient]

# the schema IS the contract — no free-form vocab
...
agent = Agent("anthropic:claude-sonnet-4-6", output_type=Recipe)
recipe = agent.run_sync(recipe_text).output
```

<div class="h-90">
  <GraphView :graph="recipeShape" :show-edge-labels="true" :show-legend="false" />
</div>

</div>


<!--
Now we hand the extractor a shape to fill — a Recipe that has a title and a list of
Ingredients. 

There is some brilliance in structured llm outputs, but the schema principles are also really important to acknowledge.

The benefit: With consistent node and edge types the relationships become meaningful and something we can interrogate.


-->

---
clicks: 3
---

<script setup lang="ts">
import recipeBuild from './snippets/graph-fixtures/recipe-build.json';
</script>

# A recipe is more than its ingredients
**The shape grows with the domain** — add `steps`, and the `technique` each one applies.

<div class="grid grid-cols-2 gap-6 items-center">

```python
class Ingredient(BaseModel):
    name: str
    quantity: float | None = Field(None, description="...")
    unit: str | None = Field(None, description="...")


class Step(BaseModel):
    text: str
    technique: str | None = Field(None, description="...")
    uses: list[str] = Field(default_factory=list, description="...")


class Recipe(BaseModel):
    title: str
    ingredients: list[Ingredient]
    steps: list[Step]

```


  <div class="h-90">
    <GraphView :graph="recipeBuild" :step="$clicks" :focus-reveal="false" :show-edge-labels="false" :show-legend="false" />

  <div class="text-center text-sm opacity-70">
    <span v-if="$clicks < 1"><b>Recipe</b> — one dish at the centre</span>
    <span v-else-if="$clicks < 2"><b>+ Ingredients</b> — what goes into it</span>
    <span v-else-if="$clicks < 3"><b>+ Steps</b> — each step <i>uses</i> some of those ingredients</span>
    <span v-else><b>+ Techniques</b> — the verb each step applies (saute, boil, toss)</span>
  </div>
  </div>
</div>

<!-- ROI / real-world (for spoken script) — separate from the presenter note below:
- What it buys: every field you add to the shape is a new question you can ask *later
  without re-extracting*. Adding steps + techniques means you can now query by method
  ("what can I braise?"), not just by ingredient.
- Payoff line: re-extraction is the expensive part — model the domain richly once and the
  graph keeps paying you back in new queries for free.
- Real-world / transfer: same move as modelling a domain deeply up front — code graphs add
  calls/imports; legal docs add obligations/parties; the richer the shape, the more the
  graph can answer.
-->

<!-- 
  We can take this further:
  1. our model has ingredients,
  2. we can also add steps,
  3. and even techniques.


 -->
---
clicks: 1
---

<script setup lang="ts">
import pocV2Before from './snippets/graph-fixtures/poc-v2-single-before.json';
import pocV2After from './snippets/graph-fixtures/poc-v2-single-after.json';
</script>

# Adding ontology in the prompt
**Principle:** *a schema provides shape, the ontology describes what should go into it.*

<div class="grid grid-cols-2 gap-6 items-center">

```python
# the ontology, expressed as rules in the system prompt
SYSTEM_PROMPT = (
  "Extract recipes into STRICT, schema-conformant form:\n"
  "1. CANONICAL UNITS — convert to SI:\n"
  "   mass → grams ('g'); volume → millilitres ('ml')\n"
  "   (1 cup → 240 ml; 1 tbsp → 15 ml; 1 oz → 28 g)\n"
  "   countable items (eggs, cloves) keep a null unit.\n"
  "2. CANONICAL NAMES — clean, lowercase, singular:\n"
  "   'plain flour' / 'all-purpose' → 'flour'\n"
  "   strip brands & loose adjectives ('chopped', 'fresh'),\n"
  "   keep distinguishing words ('smoked', 'self-raising').\n"
  "Conform to the schema; don't invent ingredients."
)
```

<div class="h-100">
  <GraphView v-if="$clicks < 1" :graph="pocV2Before" :show-edge-labels="true" :show-legend="false" />
  <GraphView v-else :graph="pocV2After" :show-edge-labels="true" :show-legend="false" />
</div>

</div>


<!-- ROI / real-world (for spoken script) — separate from the presenter note below:
- What it buys: canonical names + standard units make records *comparable* and *joinable*.
  Without it, "Eggs" and "egg", cups and grams silently fail to match — your joins return
  nothing and you don't even notice.
- Payoff line: standardisation is what makes cross-document queries actually work; it's the
  difference between a graph that looks right and one that answers right.
- Real-world / transfer: this is the lightweight, in-prompt version of what controlled
  vocabularies / ontologies do in production — UMLS in medicine, FIBO in finance,
  schema.org on the web.
-->

<!-- 

1. **Problem:** the shape is fixed (the schema), but the *details* of extraction still vary.
  - At the moment "Eggs" would not match to "egg", and our units or measure, while charming, are all measured in the "old money"

2. Capturing the right information is about more than a simple data structure, but comes down to with what and how we add content to the graph.
 - In our current demo's that means that we need to tune up prompt to standardise the ingredient labels and units

---
3. and boom, just like that we've standardise ingredients and our units are in this nice standardised system that is more easily comparable

4. we're not out of the wood yet, the mother-of-all-prompts will not guarantee the standardisation of "fresh eggs", "large eggs", "organic eggs", "gluten-free eggs" etc
 -->

---
clicks: 3
---

<script setup lang="ts">
import rung3Before from './snippets/graph-fixtures/rung3-before.json';
import rung3Collapsed from './snippets/graph-fixtures/rung3-collapsed.json';
import rung3After from './snippets/graph-fixtures/rung3-after.json';
</script>

# Simple entity matching
**Principle:** epic power-up = **resolve your entities.** 

<div class="grid grid-cols-2 gap-6 items-center">

```python
# a synonym / index table maps surface forms → one canonical node
INGREDIENTS = {
  "garlic":  ["garlic clove", "minced garlic", "2 cloves garlic"],
  "shallot": ["challots", "eschalot", "golden shallot"],
}

def normalise(name: str) -> str:
    cleaned = clean(name)                       # lowercase, strip, de-plural
    return SYN_TO_CANON.get(cleaned, cleaned)   # exact hit → canonical, else as-is
```

<div class="h-90">
  <GraphView v-if="$clicks < 1" :graph="rung3Before" :show-edge-labels="false" :params="{ labels: { nodeFontSize: 17 }, nodes: { radiusScale: 1.15 }, layout: { spread: 1.15 } }" :show-legend="false"/>
  <GraphView v-else-if="$clicks < 2" :graph="rung3Before" :step="0" :show-edge-labels="false" :params="{ labels: { nodeFontSize: 17 }, nodes: { radiusScale: 1.15 }, layout: { spread: 1.15 } }" :show-legend="false"/>
  <GraphView v-else-if="$clicks < 3" :graph="rung3Collapsed" :step="0" :show-edge-labels="false" :params="{ labels: { nodeFontSize: 17 }, nodes: { radiusScale: 1.15 }, layout: { spread: 1.15 } }" :show-legend="false"/>
  <GraphView v-else-if="$clicks < 4" :graph="rung3After" :step="0" :show-edge-labels="false" :params="{ labels: { nodeFontSize: 17 }, nodes: { radiusScale: 1.15 }, layout: { spread: 1.15 } }" :show-legend="false"/>
</div>

</div>




<!-- ROI / real-world (for spoken script) — separate from the presenter note below:
- What it buys: collapsing duplicate nodes means "find all recipes with garlic" returns
  *all* of them — not just the ones that happened to spell it the same way. Every merge
  also strengthens the relationships around the node (shared-ingredient queries get sharper).
- Payoff line: duplicates silently fragment your answers; resolving them is what turns a
  pile of records into a graph you can trust.
- Real-world / transfer: entity resolution is its own discipline (master data management,
  record linkage). A synonym/index table is the cheap, high-precision first pass when a
  domain dictionary already exists.
-->

<!-- 
1. This is the power move in building a cohesive graph, get your nodes right and the relationships fall into place.
  - We're essentially solving the "potaito/potarto" problem here
  - This doesn't always seem like such a big deal looking at one recipe, because it makes sense in isolation, but if you want to match all recipes that have roasted potatoes and garlic in them.. it starts to matter.
---
2. In this slightly contrived graph we have a few nodes that have been extracted differently in each recipe
  - We can get a long way by using an index or synonym table to match theme as we extract, which is cheap if you have one ready to go for your domain
---
3. Not only have we reduced the sprawl of ingredient nodes, but the relationships between the nodes instantly become more valuable
  - we can now better determine which recipes have garlic, but we also get better resolution of which recipes share ingredients

 -->

---

<script setup lang="ts">
import rung4Scatter from './assets/rung4-scatter.png';
</script>

# Better entity matching
**Principle:**  Hybrid approaches often yield the best results. In this case semantic entity matching.

<div class="grid grid-cols-[2fr_3fr] gap-6 items-center">

```python
# hybrid match = semantic vector score + lexical score
def hybrid_lookup(query, candidates):
    q, *cands = embed([query, *candidates])      # all-MiniLM-L6-v2
    scores = []
    for cand, vec in zip(candidates, cands):
        vector  = (cosine(q, vec) + 1) / 2        # semantic kinship
        lexical = token_sort_ratio(query, cand) / 100  # surface overlap
        scores.append(0.6 * vector + 0.4 * lexical)
    return best_first(candidates, scores)

hybrid_lookup("garbanzo", existing_nodes)   # → 'chickpea'
```

<div class="h-100 flex items-center">
  <img :src="rung4Scatter" class="w-full" />
</div>

</div>

<!-- ROI / real-world (for spoken script) — separate from the presenter note below:
- What it buys: catches the surface forms you *didn't* anticipate — cilantro/coriander,
  scallion/spring onion, garbanzo/chickpea — without listing every variant up front.
- Payoff line: a synonym table handles what you know; embeddings handle the long tail you
  don't. Hybrid (cheap exact matches first, semantic for the rest) is the production
  sweet spot — high precision *and* high recall.
- Real-world / transfer: embedding-based resolution is how dedup scales past hand-built
  dictionaries — same approach transfers to any messy vocab (medical synonyms, legal terms
  of art, product catalogues).
-->

<!-- 
1. Semantic matching is great because it doesn't require you to know terms in advance 
2. It's also much more flexible for matching different expressions or obscure terms

-->


<!--

SECTION SEGUE

SOOOOOOO....
 - with well a structured graph schema
 - strengthened ontology through prompt engineering
 - entity matching with an embedding model

 ... we've got ourselves a pretty descent quality graph

 In trickier domains like code bases, complex legal documents, medical records, financial audit... these same principles apply

 -->


---
clicks: 2
---

<script setup lang="ts">
import pocProjectionEgo from './snippets/graph-fixtures/poc-projection-ego.json';
</script>

# Graph queries
**Principle:** *query by **relationship**, not just by node — and get a subgraph back.*

<div class="grid grid-cols-2 gap-6 items-center">

<div>

```cypher
// graph — walk the relationship
MATCH (r:Recipe)-[:CONTAINS]->(i:Ingredient)
WHERE i.name = 'garlic'
RETURN r, i
```

```sql
-- relational — join through the link table
SELECT r.title
FROM recipes r
JOIN recipe_ingredients ri ON ri.recipe_id = r.id
JOIN ingredients      i  ON i.id  = ri.ingredient_id
WHERE i.name = 'garlic';
```

</div>

<div class="h-90">
  <GraphView :graph="pocProjectionEgo" :step="$clicks" :focus-reveal="false" :show-edge-labels="false" :show-legend="false" />
</div>

<div class="text-center text-sm opacity-70">
  <span v-if="$clicks < 1"><b>garlic?</b> — the question, as a seed node</span>
  <span v-else-if="$clicks < 2"><b>→ recipes that contain garlic</b> — walk one hop out</span>
  <span v-else><b>→ + their other ingredients</b> — the subgraph you'd hand a model</span>
</div>

</div>

<!-- ROI / real-world (for spoken script) — separate from the presenter note below:
- What it buys: query by *relationship* and get a subgraph back — the compact neighbourhood
  you hand a model as context, instead of the whole corpus. (This is the "Project" step.)
- Payoff line: one hop is already two SQL joins through a link table; the cost compounds
  with each hop and explodes when you don't know the hop-count in advance. Graphs win when
  the relationships matter as much as the records.
- Real-world / transfer: this is plain graph-native retrieval — the doorway to letting an
  algorithm walk the structure for you (Act III). Friends-of-friends, reachability,
  "what's related to this, transitively?" — all the same shape.
-->

<!-- 
Speaker notes:

This is the hinge of the talk: we've *built* a good graph — now what do we do with it?

The simplest thing is just to query it. Ask "what can I cook with garlic?" and you walk
the CONTAINS relationship out to the recipes — and what comes back isn't a row, it's a
**subgraph**: garlic, the recipes that use it, and their other ingredients.

- You *could* do this in a relational DB — but notice the SQL: one hop is already two
  joins through a link table. That's the give-away. You're paying for structure you then
  have to reassemble by hand.
- One hop is fine either way. Graphs start to pull ahead when you want *many* hops, or
  when you don't know how many hops in advance — friends-of-friends, reachability,
  "what's related to this, transitively?"
- And that's the doorway to the rest of the talk: once you're traversing structure, the
  natural next step is to let an **algorithm** walk it for you. That's Act III — PPR,
  shortest path, subgraph matching.

(The returned subgraph is the compact neighbourhood you'd hand to a model as context,
instead of the whole corpus.)
 -->

---
clicks: 2
---

<script setup lang="ts">
import pprIntro from './snippets/graph-fixtures/ppr-intro.json';
</script>

# Personalised PageRank
**Plainly:** *pick one node, wander the edges, keep resetting to where you started. Where you land most often is what's relevant.*

<div class="h-80">
  <GraphView
    :graph="pprIntro"
    :play="$clicks === 1"
    :walk-step="$clicks >= 2 ? -1 : 0"
    :show-edge-labels="false"
    :show-legend="false"
  />
</div>

<!-- ROI / real-world (for spoken script) — separate from the presenter note below:
- What it buys: relevance to a *starting point* without recomputing global authority —
  cheap, local, and explainable (you can see why a node scored high).
- Real-world / named systems:
  - Pinterest "Pixie" — random-walk recommendations over a ~3B-node graph at ~60ms (WWW
    2018 — quote it as "as of their 2018 paper").
  - HippoRAG (NeurIPS 2024) — PPR over an extracted KG for multi-hop RAG; reports large
    retrieval gains and big cost/latency savings vs iterative retrieval.
- Transfer: legal precedents most relevant to a case; code paths most reachable from an
  entry point; who-to-follow / related-pin recommendations.
-->

<!--
- This is a variant on the vanilla Page Rank made famous by a certain "Brin & Page 1998"

How it works:
- It works by walking a little dude around the graph and he marks each node as he passes by
- After a present or probabilistic threshold he teleports back to his starting node and starts again
- By repeating this process until he's completely worn out, some nodes will emerge as having lots of marks i.e. a high frequency of being walked
- These nodes are the most related to your starting node, depending what your graph is 
  - this might tell you which is the most what web page to browse, pinterest pin to pin or twitter user to follow
  - it might tell us which legal precedents are most authoritative and in relation to a given case
  - it might tell which code paths are most likely to be executed from a given entry point


Variants:
- It differs from vanilla Page rank only in we focus on our starting node
  - where page rank would walk the graph from all nodes to establish global authority
  - PPR selects a single or small sub-set of nodes and looks at what is relevant to that area of interest.
- There are lots of variants and this approach is also referred to as "random walk", or "random walk with restarts"


Payoff:
- The common traditional reference example for PPR is Pinterest Pixie, how's that for some alliteration...
- For a contemporary reference have a look at HippoRag (v2) which also has some other cool graph tricks like ....

HippoRAG builds its graph with OpenIE-style extraction, then runs PPR from the entities in the question to rank the passages that answer it (links in FURTHER-READING.md).

-->

---
clicks: 1
---

<script setup lang="ts">
import recipePpr from './snippets/graph-fixtures/recipe-ppr.json';
</script>

# Personalised PageRank
**Principle:** *The most value comes from being able to highlight related nodes when they aren't obvious.*


<div class="h-50">
  <GraphView :graph="recipePpr" :step="$clicks" :focus-reveal="true" :show-legend="false"/>
</div>

<!-- 
We demoed an overly simplified example, but PPR really pays dividends when the graph is bigger, messier and more complicated. It helps you find and understand the relationships that are important.

-->

---
clicks: 4
---

<script setup lang="ts">
import caselawPpr from './snippets/graph-fixtures/caselaw-ppr.json';
</script>

# PPR in the wild — landmark law
**Real-world:** *seed a walk at one routine case; out of 27,885, the landmark it stands on surfaces.*

<div class="h-90">
  <GraphView :graph="caselawPpr" :step="$clicks" :reveal-mode="'replace'" :focus-reveal="false" :show-legend="false" />
</div>

<div class="text-center text-sm opacity-70">
  <span v-if="$clicks < 1"><b>Kansas v. Cheever (2013)</b> — a routine criminal-procedure case</span>
  <span v-else-if="$clicks < 2"><b>+ the six cases it cites</b> — all unremarkable</span>
  <span v-else-if="$clicks < 3"><b>one hop further</b> — into the precedent cluster</span>
  <span v-else-if="$clicks < 4"><b>Miranda v. Arizona (1966)</b> — surfaces 2 hops out, never directly cited</span>
  <span v-else><b>#8 of 27,885 by Personalised PageRank</b> — the only landmark in the top-10</span>
</div>

<!--
Speaker notes — the *reliable / landmark* payoff (the case-law thread promised in the abstract).

This is REAL data, not a toy: the US Supreme Court citation network — 27,885 cases, 234,312 citations
(an arrow = "A cited B as precedent"). Source: CourtListener (public domain) + SCDB, via the idc9/law-net
SCOTUS graph. Method matches Fowler & Jeon (2008), *The Authority of Supreme Court Precedent* — so this
isn't our invention, it reproduces a peer-reviewed result on open data.

The beat:
- Seed Personalised PageRank on a *routine* 2013 case — Kansas v. Cheever. Nothing famous.
- Walk the citations. The top of the ranking (out of ~28k cases) is dominated by the six cases Cheever
  directly cites — unremarkable. But sitting at **#8 overall** is **Miranda v. Arizona** — the "you have
  the right to remain silent" landmark — which Cheever never directly cited. It surfaces purely from
  structure, two citation-hops out: Cheever -> Estelle v. Smith -> Miranda.
- That short chain is the **auditable why**: you can read exactly how the landmark is relevant, case by
  case. A keyword/vector search for "Cheever" would never surface Miranda — its wording doesn't resemble
  the query. The citation links route straight to it.

Why it matters for AI apps: graph structure encodes real-world *authority* you'd otherwise have to read
thousands of documents to find — and it gives you a reason you can show, not just a similarity score.
This pairs with the eShop shortest-path beat: same "the path is the explanation" idea, different domain.

(Every node in the picture is a real case and every edge a real citation. The graph shown is a legible
neighbourhood around the chain, not all 28k nodes — say so if asked. The #8 / 27,885 figure is in
demos/artifacts/judgements/ppr_landmark.json.)
-->

---
clicks: 4
---

<script setup lang="ts">
import pocCodepath from './snippets/graph-fixtures/poc-codepath.json';
</script>

# Shortest path
**Principle:** *"how does A relate to B, and through what?"*

<div class="grid grid-cols-2 gap-6 items-center">

```python
# the path IS the explanation — one NetworkX call
path = nx.shortest_path(
    code_graph,                     # the eShop "calls" graph
    source="CheckoutModel.OnPost",  # the symptom
    target="Basket..ctor",          # the constructor we touched
)
# → CheckoutModel.OnPost
#   → CheckoutModel.SetBasketModelAsync
#   → BasketViewModelService.GetOrCreateBasketForUser
#   → BasketViewModelService.CreateBasketForUser
#   → Basket..ctor
```

<div class="h-85">
  <GraphView :graph="pocCodepath" :step="$clicks" :focus-reveal="false" :show-legend="false" />
</div>

</div>

<div class="text-center text-sm opacity-70">
the path <i>is</i> the explanation — a 4-hop <code>calls</code> chain from checkout down to the constructor
</div>

<!-- 
Speaker notes:

**In this case:** *checkout broke after we touched the Basket constructor — how are they connected?*

A symbol search or vector search might return either the `Basket` or `Checkout` symbols we mentioned,
in this case though, we can retrieve the whole chain that connects them for much better context about
how they relate nin the codebase.

Recipe's weren't a great example for this one so this is a real example from an eval we ran using 
the Microsoft eShop reference app. In the eval we saw a an "up to 40%"" reduction in tool calls to
solve the same codebase issues when using a very simple graph based code search.

It's worth noting that sometimes the most direct path is all we need. 

Other times we might want more context:
- or the K-shortest paths, when several routes exist and we want options
- the shortest path that also passes through a specific node
- the cheapest path, where edges carry weights (distance, cost, risk)

This is a good tool to consider when you have known nodes (say... from vector search) and want to
uncover the relationships between them.

 -->


---
clicks: 4
---

<script setup lang="ts">
import pocDecoratorQuery from './snippets/graph-fixtures/poc-decorator-query.json';
import pocDecorator from './snippets/graph-fixtures/poc-decorator.json';
</script>

# Exact subgraph matching
**Principle:** *"find this shape, not this keyword."*


<div class="grid grid-cols-2 gap-6 items-center">

<div>

```cypher
// graph DB — the motif IS the query
MATCH (cache:Class)-[:WRAPS]->(impl:Class),
      (cache)-[:IMPLEMENTS]->(i:Interface),
      (impl)-[:IMPLEMENTS]->(i)
RETURN cache, impl, i
```

```python
# same shape, run in the demo (NetworkX VF2)
pattern = nx.DiGraph()
pattern.add_edge("cache", "impl",  rel="wraps")
pattern.add_edge("cache", "iface", rel="implements")
pattern.add_edge("impl",  "iface", rel="implements")

match_subgraph(graph, pattern, node_match=same_kind)
```
</div>

<div class="h-90">
  <GraphView v-if="$clicks < 4" :graph="pocDecoratorQuery" :step="$clicks" :focus-reveal="false" :show-legend="false" />
  <GraphView v-else :graph="pocDecorator" :step="2" :focus-reveal="false" :show-legend="false" />
</div>

</div>


<!--
Speaker notes:

A sub-graph query can identifies similar or identical little "query" graphs within the larger graph.

This is another eShop example, and one thing I like about this particular example is that instead of starting with a node or set of nodes and navigating our way through the graph, we are querying entirely on relationships. 

We could specify a node id or value in here and it would still be a subgraph match, however in this case we are searching for code that has a certain shape, not knowing anything specific or limiting the search to specific symbols or files.

We'll search for a decorator pattern which is commonly used to enhance an existing class with additional functionality while conforming to the same interface. Examples would be classes that add logging or telemetry to an existing service.

So we are looking for 
 - a class that wraps it's target class, where 
 - the wrapper and 
 - the target class both implement the same interface

Boom, there we go! In our eShop code base we found a Catalogue View Model Service and a Cached version that implements the same API.

If we knew we were looking for caching classes we could search on that, but if we're looking for a specific pattern without a specific implementation or symbol in mind this can be a powerful tool. Imagine applying the same approach to anti-patterns, security issues, malicious transaction patters, or legal arguments.


-->

---

<script setup lang="ts">
import pocLandscape from './snippets/graph-fixtures/poc-landscape.json';
</script>

# What comes next?

<div class="grid grid-cols-[4fr_1fr] gap-4 items-center">

<div class="h-95">
  <GraphView :graph="pocLandscape" :show-legend="false" :show-edge-labels="false" />
</div>

<div class="text-sm leading-relaxed">

<span style="color:#3ca951">●</span> **Toured today**
 
<span style="color:#a463f2">●</span> **Next steps**

<span style="color:#9498a0">●</span> **Out of scope/skipped**

</div>

</div>

<!--
Graphic: poc-landscape.json — hub-and-spoke of the problem classes, status by colour
(graph-theme kinds: toured/frontier/scope). Node positions are PINNED so each category's
members sit adjacent — toured (green) left column, next steps (violet) right column, out-of-scope
(grey) set apart at the bottom. Static, no reveal — the whole map stays readable so "there's more"
lands. Options B (algorithm-level constellation) / C (text scorecard) in todo if we want to compare.
-->

<!--
Speaker notes:

We went deep on three shapes — ranking (PPR), paths (shortest-path), and patterns (subgraph). That's
a deliberate slice, not the whole map.

Graph problems come in a handful of recognisable classes. The point of this slide is honesty: we
toured three of them — the green ones — because they pay off fastest for AI apps and they're the most
*explainable*. There's more.

The next steps — the violet ones — are mostly the learned, AI/KG side. Prediction & completion is how
you keep a knowledge graph healthy: link prediction and KG embeddings that fill in the edges you
didn't extract. Similarity is node and graph embeddings, GNNs, and graph-RAG retrieval like
G-Retriever and GRAG. And clustering / community detection sits here too — it's where the GraphRAG
indexing discourse lives. Any one of these is essentially a whole second talk.

Flow and cost we skip for an AI audience — the grey one, set apart.

So: not the whole landscape — a tour of the shapes that pay off most right now, with a clear signpost
to where it goes next.
-->

---
layout: center
class: text-center
---

<script setup lang="ts">
import qr from './assets/talk-pack-qr.svg'
</script>

# Thank you AI Engineer SF

<div class="flex flex-col items-center gap-5 mt-2">
  <img :src="qr" class="w-56 h-56 rounded-xl bg-white p-3" alt="QR code linking to the talk pack repository" />
  <a href="https://github.com/good-co-au/talk-graph-basics" class="text-2xl font-medium no-underline">github.com/good-co-au/talk-graph-basics</a>
  <div class="opacity-70">The talk pack — slides, notebooks, research, and a way back to me.</div>
</div>

<!--
Speaker notes:

We've covered a lot of ground — thanks for bearing with me.

We looked at navigating paths, ranking how important things are, and finding patterns. We skipped the
traditional flow / cost / search algorithms you'd find in dependency and network modelling — heaps of
use cases, but a bit more run-of-the-mill.

The pack also has notes on the things we couldn't get to today — prediction, similarity and
clustering. Those edge into graph RAG, dynamic graphs and schemaless territory that we deliberately
stayed out of, but it's also where things get super interesting. See FURTHER-READING.md.

I hope some of these concepts give you insight or inspiration, and that you can take them — graph-native
or hybrid — to make smarter, cheaper and more reliable AI applications. Thank you.
-->

