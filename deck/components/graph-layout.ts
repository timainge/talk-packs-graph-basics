/**
 * graph-layout.ts
 * ---------------
 * A *deterministic* force-directed layout helper built on d3-force.
 *
 * Why deterministic? These graphs are rendered into a talk deck and into
 * screenshots. The same input graph must always land in the same place, so
 * slides don't jitter between rebuilds and screenshot diffs stay meaningful.
 *
 * d3-force is normally non-deterministic in two ways:
 *   1. Nodes with no initial x/y get placed on a phyllotaxis spiral seeded by
 *      index — that part is actually deterministic — but
 *   2. `forceManyBody` / `forceLink` use `Math.random()` for jiggle, and the
 *      simulation runs on a timer (`alpha` decay over wall-clock ticks).
 *
 * We remove both sources of nondeterminism:
 *   - Seed every node's initial position ourselves (phyllotaxis by index).
 *   - Stop the timer (`simulation.stop()`) and hand-crank a fixed number of
 *     ticks (`simulation.tick(N)`).
 *   - Patch `Math.random` to a seeded PRNG for the duration of the run, so any
 *     internal jiggle is reproducible too.
 *
 * Pure TypeScript — no Vue, no DOM.
 */

import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from 'd3-force';

/** Minimal node shape the layout needs. Extra fields are preserved. */
export interface LayoutNode extends SimulationNodeDatum {
  id: string;
  /** Optional kind, used to size collision radius. */
  kind?: string;
}

/** Minimal link shape. `source`/`target` are node ids (strings). */
export interface LayoutLink {
  source: string;
  target: string;
}

/** Final placed coordinate for a node. */
export interface Point {
  x: number;
  y: number;
}

/** Computed viewBox covering all nodes plus padding. */
export interface ViewBox {
  minX: number;
  minY: number;
  width: number;
  height: number;
}

export interface LayoutResult {
  /** id → final {x, y}. */
  positions: Map<string, Point>;
  /** Bounding viewBox for the whole graph. */
  viewBox: ViewBox;
}

export interface LayoutOptions {
  /** Number of simulation ticks to crank (fixed for determinism). Default 300. */
  ticks?: number;
  /** Charge strength (negative = repulsion). Default -240. */
  charge?: number;
  /** Target link distance. Default 90. */
  linkDistance?: number;
  /** Collision radius padding added to each node's kind radius. Default 6. */
  collidePadding?: number;
  /** Per-kind collision radius lookup. Defaults to a flat 18. */
  radiusForKind?: (kind: string | undefined) => number;
  /** Padding (user units) added around the node extent for the viewBox. Default 60. */
  padding?: number;
  /** PRNG seed, so even the seeded jiggle is reproducible. Default 1. */
  seed?: number;
}

/**
 * Tiny seeded PRNG (mulberry32). Deterministic, fast, good enough to replace
 * Math.random for layout jiggle.
 */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** A node arrives "pinned" if it already carries finite x AND y coordinates. */
function isPinned(n: LayoutNode): boolean {
  return Number.isFinite(n.x) && Number.isFinite(n.y);
}

/**
 * Phyllotaxis (sunflower) seeding: spreads node i evenly over a disc by index,
 * deterministically. Gives the simulation a stable, well-distributed start so
 * it converges to the same layout every time.
 *
 * Nodes that arrive already carrying finite x/y are treated as PINNED: their
 * position is frozen (d3-force `fx`/`fy`) and they are skipped here, so a fixture
 * can hand-author exact coordinates (and, with every node pinned, opt out of the
 * sim entirely). This is what makes a before/after pair share identical anchor
 * positions so the eye sees nodes collapse rather than the whole layout reshuffle.
 */
function seedPositions(nodes: LayoutNode[]): void {
  const golden = Math.PI * (3 - Math.sqrt(5)); // golden angle
  const spacing = 24;
  for (let i = 0; i < nodes.length; i++) {
    const n = nodes[i];
    if (isPinned(n)) {
      // Freeze the supplied coordinate; the sim won't move it.
      n.fx = n.x;
      n.fy = n.y;
      n.vx = 0;
      n.vy = 0;
      continue;
    }
    const radius = spacing * Math.sqrt(i + 0.5);
    const angle = i * golden;
    n.x = radius * Math.cos(angle);
    n.y = radius * Math.sin(angle);
    // Zero velocity so the first tick is reproducible.
    n.vx = 0;
    n.vy = 0;
  }
}

/**
 * Compute a deterministic force-directed layout.
 *
 * Two calls with identical `nodes`/`links`/`opts` return byte-identical
 * coordinates.
 */
export function computeLayout(
  nodes: LayoutNode[],
  links: LayoutLink[],
  opts: LayoutOptions = {},
): LayoutResult {
  const {
    ticks = 300,
    charge = -240,
    linkDistance = 90,
    collidePadding = 6,
    radiusForKind = () => 18,
    padding = 60,
    seed = 1,
  } = opts;

  // Work on copies so we never mutate the caller's data.
  const simNodes: LayoutNode[] = nodes.map((n) => ({ ...n }));
  const simLinks: SimulationLinkDatum<LayoutNode>[] = links.map((l) => ({
    source: l.source,
    target: l.target,
  }));

  // Deterministic start.
  seedPositions(simNodes);

  // Swap in the seeded PRNG for the duration of the run so any internal use of
  // Math.random (d3-force jiggle) is reproducible, then restore it.
  const realRandom = Math.random;
  Math.random = mulberry32(seed);

  try {
    const sim = forceSimulation<LayoutNode>(simNodes)
      .force('charge', forceManyBody<LayoutNode>().strength(charge))
      .force(
        'link',
        forceLink<LayoutNode, SimulationLinkDatum<LayoutNode>>(simLinks)
          .id((d) => d.id)
          .distance(linkDistance),
      )
      .force('center', forceCenter(0, 0))
      .force(
        'collide',
        forceCollide<LayoutNode>().radius(
          (d) => radiusForKind(d.kind) + collidePadding,
        ),
      )
      // No alphaDecay timer dependence — we drive ticks manually below.
      .stop();

    // Hand-crank a fixed number of ticks for determinism.
    sim.tick(ticks);
  } finally {
    Math.random = realRandom;
  }

  // Collect final positions.
  const positions = new Map<string, Point>();
  for (const n of simNodes) {
    positions.set(n.id, { x: n.x ?? 0, y: n.y ?? 0 });
  }

  // Compute extent → viewBox.
  const viewBox = computeViewBox(simNodes, radiusForKind, padding);

  return { positions, viewBox };
}

/** Derive a padded bounding box from final node positions. */
function computeViewBox(
  nodes: LayoutNode[],
  radiusForKind: (kind: string | undefined) => number,
  padding: number,
): ViewBox {
  if (nodes.length === 0) {
    // Sensible default box centred on origin.
    return { minX: -200, minY: -200, width: 400, height: 400 };
  }

  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  for (const n of nodes) {
    const r = radiusForKind(n.kind);
    const x = n.x ?? 0;
    const y = n.y ?? 0;
    minX = Math.min(minX, x - r);
    minY = Math.min(minY, y - r);
    maxX = Math.max(maxX, x + r);
    maxY = Math.max(maxY, y + r);
  }

  minX -= padding;
  minY -= padding;
  maxX += padding;
  maxY += padding;

  return {
    minX,
    minY,
    width: maxX - minX,
    height: maxY - minY,
  };
}
