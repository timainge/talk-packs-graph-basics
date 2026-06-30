/**
 * graph-theme.ts
 * --------------
 * The single source of truth for how the graph *looks*.
 *
 * Design intent: nodes sit on a dark / transparent ground. At rest they are
 * muted (low opacity, no glow). When "active" (highlighted by an algorithm,
 * the current step, a hover, etc.) they brighten to full opacity and pick up
 * a glow. So every colour here is chosen to read well both ways: subdued on
 * dark, and luminous when lit.
 *
 * All the visual tuning lives in this one file on purpose — tweak the look
 * here and every consumer (GraphView.vue, the harness, future slides) follows.
 */

/** Node categories the renderer knows how to colour. */
export type NodeKind =
  | 'recipe'
  | 'ingredient'
  | 'step'
  | 'technique'
  | 'entity'
  | 'case'
  // code-graph (Act III shortest-path / subgraph POCs)
  | 'class'
  | 'interface'
  | 'method'
  // fraud / AML ring (Act III subgraph POC)
  | 'account'
  | 'merchant'
  | 'mule'
  // projection POC — the query seed
  | 'query'
  // roadmap / agenda graph (the "what's coming" overview slide)
  | 'talk'
  | 'part'
  | 'beat'
  // per-step method flow (principle -> code -> examples)
  | 'principle'
  | 'code'
  | 'example'
  // wrap-up "landscape" map (problem-class status: what we toured vs what's ahead)
  | 'maphub'
  | 'toured'
  | 'frontier'
  | 'pack'
  | 'scope'
  // --- next-steps deck (advanced-graph-methods) ---
  // Section A — link prediction (citation / co-authorship)
  | 'paper'
  | 'author'
  // Sections B / C / D — community & cluster colours (8 distinct hues)
  | 'c0'
  | 'c1'
  | 'c2'
  | 'c3'
  | 'c4'
  | 'c5'
  | 'c6'
  | 'c7'
  // Section D — a community-summary super-node (GraphRAG index)
  | 'community'
  // Section E — an induced schema type (schemaless → distilled structure)
  | 'type'
  // Section F — agent memory graph
  | 'user'
  | 'episode'
  | 'fact'
  | 'default';

/** Which glow technique the renderer should use. */
export type GlowMode =
  /** SVG-native: a <filter> with feGaussianBlur + feMerge in <defs>. */
  | 'svg'
  /** CSS: `filter: drop-shadow(...)` on the element. Cheaper, less control. */
  | 'filter';

/**
 * Categorical palette, keyed by node kind.
 *
 * Hues are drawn from Observable10 (https://observablehq.com/@d3/color-schemes)
 * — chosen because they are *distinct hues*, not shades of one colour, so the
 * graph survives a greyscale / colour-blindness check (each kind maps to a
 * visibly different lightness as well as hue).
 */
export interface KindColor {
  /** Hue used when the node is active/lit (full strength). */
  active: string;
  /** Hue used at rest — same family, slightly desaturated reads better muted. */
  rest: string;
}

export const PALETTE: Record<NodeKind, KindColor> = {
  // Observable10 #1 — blue
  recipe: { active: '#4269d0', rest: '#5a78c9' },
  // Observable10 #2 — orange
  ingredient: { active: '#efb118', rest: '#d6a543' },
  // Observable10 #3 — red
  step: { active: '#ff725c', rest: '#e08374' },
  // Observable10 #4 — cyan/teal
  technique: { active: '#6cc5b0', rest: '#73b3a6' },
  // Observable10 #5 — green
  entity: { active: '#3ca951', rest: '#56a368' },
  // Observable10 #6 — purple
  case: { active: '#a463f2', rest: '#9d77cf' },
  // --- code-graph kinds ---
  // brown — a class / type
  class: { active: '#9c6b4e', rest: '#a07c66' },
  // pink — an interface (the contract)
  interface: { active: '#ff8ab7', rest: '#e093b1' },
  // light blue — a method / member
  method: { active: '#97bbf5', rest: '#9fb4d8' },
  // --- fraud / AML kinds ---
  // green — an ordinary account
  account: { active: '#3ca951', rest: '#56a368' },
  // orange — a merchant / endpoint
  merchant: { active: '#efb118', rest: '#d6a543' },
  // red — the mule / ring hub (the thing the pattern surfaces)
  mule: { active: '#ff725c', rest: '#e08374' },
  // --- projection kind ---
  // purple — the query seed
  query: { active: '#a463f2', rest: '#9d77cf' },
  // --- roadmap / agenda kinds (overview slide) ---
  // purple-violet — the talk root (the hub of the roadmap)
  talk: { active: '#a463f2', rest: '#9d77cf' },
  // blue — a top-level part / act
  part: { active: '#4269d0', rest: '#5a78c9' },
  // teal — an individual beat / slide within a part
  beat: { active: '#6cc5b0', rest: '#73b3a6' },
  // --- per-step method flow (principle -> code -> examples) ---
  // amber — the principle (the idea we open with)
  principle: { active: '#efb118', rest: '#d6a543' },
  // blue — the code (easy recipe examples)
  code: { active: '#4269d0', rest: '#5a78c9' },
  // green — the examples (real-world analogues)
  example: { active: '#3ca951', rest: '#56a368' },
  // --- wrap-up landscape map (status by colour) ---
  // neutral light — the hub ("graph problems")
  maphub: { active: '#e8eaed', rest: '#b8bdc6' },
  // green — a class we toured on stage
  toured: { active: '#3ca951', rest: '#56a368' },
  // violet — the AI/KG frontier (the weighted teaser; drawn prominent)
  frontier: { active: '#a463f2', rest: '#9d77cf' },
  // amber — named but parked to the pack
  pack: { active: '#efb118', rest: '#d6a543' },
  // grey — out of scope for this audience
  scope: { active: '#9498a0', rest: '#7e828a' },
  // --- next-steps deck: link prediction (Section A) ---
  // blue — a paper / document node in a citation graph
  paper: { active: '#4269d0', rest: '#5a78c9' },
  // orange — an author / actor
  author: { active: '#efb118', rest: '#d6a543' },
  // --- community / cluster hues (Sections B, C, D) — 8 distinct Observable10 hues ---
  c0: { active: '#4269d0', rest: '#5a78c9' }, // blue
  c1: { active: '#efb118', rest: '#d6a543' }, // orange
  c2: { active: '#3ca951', rest: '#56a368' }, // green
  c3: { active: '#a463f2', rest: '#9d77cf' }, // purple
  c4: { active: '#6cc5b0', rest: '#73b3a6' }, // teal
  c5: { active: '#ff8ab7', rest: '#e093b1' }, // pink
  c6: { active: '#9c6b4e', rest: '#a07c66' }, // brown
  c7: { active: '#ff725c', rest: '#e08374' }, // red
  // --- GraphRAG community-summary super-node (Section D) ---
  // neutral light — a community summary sitting above its members
  community: { active: '#e8eaed', rest: '#b8bdc6' },
  // --- induced schema type (Section E) ---
  // light blue — a distilled node/relation type
  type: { active: '#97bbf5', rest: '#9fb4d8' },
  // --- agent memory graph (Section F) ---
  // purple — the user / subject the memory is about
  user: { active: '#a463f2', rest: '#9d77cf' },
  // teal — a conversation turn / episode
  episode: { active: '#6cc5b0', rest: '#73b3a6' },
  // amber — an extracted fact / entity in memory
  fact: { active: '#efb118', rest: '#d6a543' },
  // Observable10 #8 — grey, neutral fallback
  default: { active: '#9498a0', rest: '#7e828a' },
};

/** Per-kind node radius (in SVG user units / px at viewBox scale). */
export const NODE_RADIUS: Record<NodeKind, number> = {
  recipe: 26,
  ingredient: 16,
  step: 14,
  technique: 16,
  entity: 18,
  case: 22,
  class: 24,
  interface: 22,
  method: 15,
  account: 20,
  merchant: 22,
  mule: 24,
  query: 24,
  talk: 30,
  part: 22,
  beat: 13,
  principle: 24,
  code: 24,
  example: 24,
  // wrap-up landscape map: hub biggest, frontier (the teaser) prominent.
  maphub: 30,
  toured: 22,
  frontier: 25,
  pack: 18,
  scope: 16,
  // next-steps deck
  paper: 18,
  author: 18,
  c0: 16,
  c1: 16,
  c2: 16,
  c3: 16,
  c4: 16,
  c5: 16,
  c6: 16,
  c7: 16,
  community: 28,
  type: 22,
  user: 26,
  episode: 16,
  fact: 16,
  default: 14,
};

/** Global opacity tokens for the muted-at-rest / lit-when-active treatment. */
export const OPACITY = {
  /** Resting node/edge opacity — present but subdued. */
  rest: 0.68,
  /** Active node/edge opacity — full strength. */
  active: 1.0,
  /** Even dimmer, for nodes explicitly de-emphasised behind a highlight.
   *  Kept low on purpose: this is what makes a lit path/subgraph pop against
   *  the muted field (the Act III money shot). The higher `rest` value above is
   *  only used when NO highlight is active. */
  faded: 0.18,
} as const;

/** Label typography (font sizes in SVG user units). */
export const LABEL = {
  /** Primary node labels. */
  nodeFontSize: 13,
  /** Smaller labels, e.g. on minor nodes. */
  nodeFontSizeSmall: 11,
  /** Edge-label chip text. */
  edgeFontSize: 10,
  /** Node labels longer than this are truncated with an ellipsis. */
  maxChars: 22,
  /** Edge-label chips truncate at this (shorter) length. */
  edgeMaxChars: 18,
  fontFamily:
    "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
  /** Light text that reads on the dark ground / dark chips. */
  color: '#e8eaed',
  /** Dimmer label colour for resting/secondary text. */
  colorMuted: '#a6abb3',
} as const;

/** Edge (link) styling. */
export const EDGE = {
  /** Muted edge stroke at rest. */
  rest: '#4a4f57',
  /** Lit edge stroke when active. */
  active: '#c8cdd6',
  /** Stroke width at rest. */
  width: 1.5,
  /** Stroke width when active. */
  widthActive: 2.5,
} as const;

/** Edge-label "chip" colours: a dark pill with light text. */
export const EDGE_CHIP = {
  /** Dark chip background. */
  fill: '#21242b',
  /** Light text on the chip. */
  text: '#d7dbe0',
  /** Subtle chip border. */
  stroke: '#3a3e46',
  /** Corner radius of the chip. */
  radius: 4,
  /** Horizontal padding inside the chip. */
  padX: 5,
  /** Vertical padding inside the chip. */
  padY: 2,
} as const;

/** Glow configuration, used by both glow modes. */
export const GLOW = {
  /**
   * Blur radius / spread of the glow halo (SVG user units). Generous by
   * default so the glow is unmistakable — tune down for production density.
   */
  radius: 6,
  /** Glow colour. Defaults to a warm-white that lifts any hue. */
  color: '#ffffff',
  /** Glow opacity (how strong the halo reads). */
  opacity: 0.9,
  /**
   * When using GLOW_MODE 'svg', the feGaussianBlur stdDeviation. Larger =
   * softer, wider halo. Bumped to 6 for a subtler, more diffuse glow (paired
   * with a single blur merge layer in GraphView.vue rather than a doubled one).
   */
  stdDeviation: 6,
} as const;

/**
 * Active glow technique.
 *
 * 'svg'   → SVG <filter> (feGaussianBlur + feMerge). Most control, composites
 *           cleanly inside the SVG, but some renderers clip it to the element
 *           bounds unless filter region is widened.
 * 'filter'→ CSS `filter: drop-shadow()`. Simpler and robust across browsers;
 *           less control over the merge.
 *
 * Default 'svg'. The smoke test verifies it survives; if not, flip to 'filter'.
 */
export const GLOW_MODE: GlowMode = 'svg';

/** Resolve a node kind to its colour, falling back to `default`. */
export function colorForKind(kind: string | undefined): KindColor {
  return (kind && PALETTE[kind as NodeKind]) || PALETTE.default;
}

/** Resolve a node kind to its radius, falling back to `default`. */
export function radiusForKind(kind: string | undefined): number {
  return (kind && NODE_RADIUS[kind as NodeKind]) ?? NODE_RADIUS.default;
}

/** Bundled theme object, handy for passing around as one value. */
export const theme = {
  PALETTE,
  NODE_RADIUS,
  OPACITY,
  LABEL,
  EDGE,
  EDGE_CHIP,
  GLOW,
  GLOW_MODE,
  colorForKind,
  radiusForKind,
} as const;

export type GraphTheme = typeof theme;
