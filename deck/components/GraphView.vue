<script setup lang="ts">
/**
 * GraphView.vue — the inline-SVG graph renderer.
 *
 * Renders a directed (possibly multi-)graph as muted circles + curved edges on
 * a dark / transparent ground, with a categorical palette per node kind. A
 * `reveal` script (driven by the `step` prop) can light an ordered path /
 * subgraph: active nodes/edges brighten + glow while the rest of the graph
 * dims into context.
 *
 * Look & feel tunables all live in ./graph-theme.ts. Layout (deterministic
 * d3-force) lives in ./graph-layout.ts. This file is pure presentation: it
 * computes the layout once, then derives per-element visual state.
 */
import {
  computed,
  defineAsyncComponent,
  nextTick,
  onMounted,
  onUnmounted,
  ref,
  watch,
} from 'vue';
import {
  EDGE_CHIP,
  LABEL,
  OPACITY,
  colorForKind,
  radiusForKind,
} from './graph-theme';
import {
  DEFAULT_PARAMS,
  cssColorFilter,
  resolveParams,
  type GraphParams,
} from './graph-params';
import { computeLayout, type Point } from './graph-layout';
import { useGraphEditMode } from '../composables/useGraphEditMode';

/**
 * The configurator is dev-only. Gating the dynamic import on the statically
 * replaced `import.meta.env.DEV` lets the production bundler tree-shake the
 * component (and its "copy params" UI) out of `slidev build` entirely — so it
 * can never ship or appear in a screenshot build (plan §9a/§9d).
 */
const GraphConfigurator = import.meta.env.DEV
  ? defineAsyncComponent(() => import('./GraphConfigurator.vue'))
  : undefined;

// ---------------------------------------------------------------------------
// Data contract (matches demos/viz/fixtures/*.json)
// ---------------------------------------------------------------------------

/** A graph node. */
interface GraphNode {
  id: string;
  kind?: string;
  label?: string;
  /** Optional pre-placed coordinates (skips layout for this node if present). */
  x?: number;
  y?: number;
}
/** A graph edge. `key` disambiguates parallel edges in a multigraph. */
interface GraphEdge {
  source: string;
  target: string;
  /** Multigraph edge key — string or number. */
  key?: string | number;
  /** Relationship label, e.g. CONTAINS / CITES. */
  rel?: string;
  /** Legacy alias for `rel`. */
  label?: string;
  /** Per-edge direction override. Defaults to the graph's `directed` flag;
   *  set `false` on one edge to drop its arrowhead in an otherwise directed
   *  graph (a mixed graph), or `true` to add one in an undirected graph. */
  directed?: boolean;
  /** Edge weight/magnitude. Only rendered when `edges.widthByWeight` is on,
   *  where it scales the stroke width; ignored otherwise. */
  weight?: number;
  /** Extra payload (qty/unit/order/…), ignored by the renderer. */
  [extra: string]: unknown;
}
/** One reveal step: the nodes + edge-triples that become ACTIVE at this click. */
interface RevealStep {
  label?: string;
  nodes?: string[];
  /** Edge identity triples: [source, target, key]. */
  edges?: Array<[string, string, string | number]>;
}
/**
 * One frame of an animated walk (see `WalkData`). Unlike a reveal step (which is
 * cumulative and click-driven), walk frames play on a clock: each frame is the
 * complete state at one tick — where the walker is (`heads`), the edge it just
 * crossed (`edges`), and the cumulative visit "heat" per node so far.
 */
interface WalkFrame {
  /** The walker's current position(s) — drawn brightest, with the active glow. */
  heads?: string[];
  /** Edge(s) traversed to reach this frame: [source, target, key]. Empty on a restart. */
  edges?: Array<[string, string, string | number]>;
  /** Cumulative, normalised (0..1) visit count per node — maps to brightness + size. */
  heat?: Record<string, number>;
  /** True when this position was reached by a teleport back to the seed. */
  restart?: boolean;
  /** True on the final frame: the resolved PPR distribution to freeze on. */
  resolved?: boolean;
}
/**
 * An animated random-walk-with-restart, precomputed offline (graphtools) so the
 * renderer stays pure + deterministic. Played frame-by-frame on a `tickMs` clock
 * while the `play` prop is true; see the playback engine below.
 */
interface WalkData {
  frames?: WalkFrame[];
  /** Milliseconds per frame. */
  tickMs?: number;
  /** Loop back to frame 0 at the end (vs. hold the last frame). */
  loop?: boolean;
  /** The seed node(s) the walk restarts to. */
  seeds?: string[];
}
/** The graph payload. */
interface GraphData {
  directed?: boolean;
  multigraph?: boolean;
  nodes?: GraphNode[];
  /** Primary link list. `edges` accepted as an alias. */
  links?: GraphEdge[];
  edges?: GraphEdge[];
  /** Optional per-step reveal script. */
  reveal?: RevealStep[];
  /** Optional precomputed animated walk (played on a clock; see `play` prop). */
  walk?: WalkData;
  title?: string;
  /** Optional presentation params — the canonical committed look for this graph. */
  params?: GraphParams;
}

const props = withDefaults(
  defineProps<{
    /** The graph to render. Empty/absent → glow smoke test. */
    graph?: GraphData;
    /** Reveal up to this step (for staged build-ups). Undefined → plain static. */
    step?: number;
    /** 'cumulative' lights steps 0..step; 'replace' lights only `step`. */
    revealMode?: 'cumulative' | 'replace';
    /** Show the kind legend. */
    showLegend?: boolean;
    /** Show edge-label chips (also density-gated — auto-hidden when dense). */
    showEdgeLabels?: boolean;
    /** Fit strategy for the viewBox. */
    fit?: 'contain';
    /**
     * Opt-in camera zoom: when true AND a reveal step is active, smoothly ease
     * the viewBox to frame the active node set (the lit path) so it fills the
     * frame. Node coordinates never change — this is camera only, so F11
     * (no per-node position jump) still holds.
     */
    focusReveal?: boolean;
    /**
     * Per-slide presentation params, merged OVER the fixture's own `params`
     * (an escape hatch for one-off slide variations without editing the JSON).
     */
    params?: GraphParams;
    /**
     * Animated-walk playback (needs `graph.walk`). While true, frames advance on
     * the walk's `tickMs` clock; the walker hops, restarts at the seed, and visit
     * "heat" accumulates. Typically bound to a Slidev click, e.g.
     * `:play="$clicks === 1"` — false→true (re)starts from frame 0, true→false stops.
     */
    play?: boolean;
    /**
     * Freeze on a specific walk frame when NOT playing (scrubbing / screenshots /
     * the resolved-PPR payoff). Negative indexes from the end: `-1` = last frame.
     * Ignored while `play` is true.
     */
    walkStep?: number;
    /** Override the walk's per-frame duration (ms). */
    walkTickMs?: number;
    /**
     * Loop the walk instead of playing once. Default (false) plays through and
     * holds the final frame; set true here (or `walk.loop` in the fixture) to cycle.
     */
    walkLoop?: boolean;
  }>(),
  {
    graph: undefined,
    step: undefined,
    revealMode: 'cumulative',
    showLegend: true,
    showEdgeLabels: true,
    fit: 'contain',
    focusReveal: false,
    params: undefined,
    play: false,
    walkStep: undefined,
    walkTickMs: undefined,
    walkLoop: undefined,
  },
);

/** Stable id for this instance's filters (avoids cross-instance clashes). */
const uid = Math.random().toString(36).slice(2, 9);
const glowId = `graph-glow-${uid}`;

// ---------------------------------------------------------------------------
// Resolved theme — defaults ← fixture.params ← :params prop ← live edits.
// Every visual helper below reads from `rt`; nothing reads the raw constants
// directly any more (except the no-graph smoke test). With no params supplied
// this is value-identical to the old hard-coded constants.
// ---------------------------------------------------------------------------

/** Ephemeral live overrides from the configurator (stretch); empty by default. */
const liveParams = ref<GraphParams | undefined>(undefined);

const rt = computed(() =>
  resolveParams(
    DEFAULT_PARAMS,
    props.graph?.params,
    props.params,
    liveParams.value,
  ),
);

// --- Editing mode (dev-only configurator; see useGraphEditMode + plan §9) ----
const { editMode, available: editAvailable } = useGraphEditMode();
/** Per-instance: is THIS graph's configurator panel open? (gear toggles it). */
const panelOpen = ref(false);
/** Show the gear only in a dev build, when edit mode is on, on a real graph. */
const showGear = computed(
  () => editAvailable && editMode.value && hasGraph.value,
);
function togglePanel(): void {
  panelOpen.value = !panelOpen.value;
  if (panelOpen.value && liveParams.value === undefined) liveParams.value = {};
}

/** Per-kind radius, scaled by the global radiusScale knob. */
function nodeRadius(kind: string | undefined): number {
  return radiusForKind(kind) * rt.value.nodes.radiusScale;
}

/** True once a real graph with nodes is supplied. */
const hasGraph = computed(() => {
  const n = props.graph?.nodes;
  return Array.isArray(n) && n.length > 0;
});

// ---------------------------------------------------------------------------
// Normalised input
// ---------------------------------------------------------------------------

const nodes = computed<GraphNode[]>(() => props.graph?.nodes ?? []);
/** Whole-graph directedness — NetworkX writes `directed:false` for an undirected
 *  Graph. Absent → treated as directed (every existing fixture). A per-edge
 *  `directed` overrides this. */
const graphDirected = computed(() => props.graph?.directed !== false);
const links = computed<GraphEdge[]>(
  () => props.graph?.links ?? props.graph?.edges ?? [],
);

/** Stringify an edge key consistently (number 0 and string "0" must match). */
function keyStr(k: string | number | undefined): string {
  return k === undefined ? '' : String(k);
}
/** Canonical edge identity used for highlight matching. */
function edgeIdOf(source: string, target: string, key: string | number | undefined): string {
  return `${source}${target}${keyStr(key)}`;
}

// ---------------------------------------------------------------------------
// Layout (deterministic — computed once per graph)
// ---------------------------------------------------------------------------

const layout = computed(() => {
  if (!hasGraph.value) return null;
  const n = nodes.value.length;
  // Spread scales with graph size: small graphs breathe, large graphs stay
  // compact enough to fit. These feed the deterministic force sim.
  const baseCharge = n <= 40 ? -700 : n <= 120 ? -460 : -340;
  const baseLinkDistance = n <= 40 ? 150 : n <= 120 ? 110 : 95;
  // Params can override the heuristic outright (charge/linkDistance), and the
  // one-knob `spread` multiplies whichever value is in play. null → heuristic.
  const L = rt.value.layout;
  const charge = (L.charge ?? baseCharge) * L.spread;
  const linkDistance = (L.linkDistance ?? baseLinkDistance) * L.spread;
  return computeLayout(
    nodes.value.map((nn) => ({ id: nn.id, kind: nn.kind, x: nn.x, y: nn.y })),
    links.value.map((l) => ({ source: l.source, target: l.target })),
    {
      // Scaled radius so collision spacing matches the drawn node size.
      radiusForKind: nodeRadius,
      charge,
      linkDistance,
      collidePadding: L.collidePadding,
      seed: L.seed,
    },
  );
});

/** id → {x,y} for placed nodes. */
const positions = computed<Map<string, Point>>(
  () => layout.value?.positions ?? new Map(),
);

/** A viewBox as a plain rect, easier to interpolate than the string form. */
interface Box {
  minX: number;
  minY: number;
  width: number;
  height: number;
}

/** The full-graph viewBox from the layout extent. */
const fullBox = computed<Box>(() => {
  if (!layout.value) return { minX: -120, minY: -80, width: 240, height: 160 };
  const { minX, minY, width, height } = layout.value.viewBox;
  return { minX, minY, width, height };
});

// ---------------------------------------------------------------------------
// Reveal / active set
// ---------------------------------------------------------------------------

const reveal = computed<RevealStep[] | null>(() => {
  const r = props.graph?.reveal;
  return Array.isArray(r) && r.length > 0 ? r : null;
});

// ---------------------------------------------------------------------------
// Animated walk — clock-driven playback (the random-walk-with-restart mode).
// Frames are precomputed (graphtools); this just steps a frame index on a timer
// while `play` is true. When a graph carries a `walk` block, the active set and
// per-node "heat" come from the current frame instead of the reveal `step`.
// ---------------------------------------------------------------------------

const walkFrames = computed<WalkFrame[]>(() => props.graph?.walk?.frames ?? []);
/** Walk mode is on whenever the graph carries a non-empty walk block. */
const walkActive = computed(() => walkFrames.value.length > 0);
const walkTick = computed(
  () => props.walkTickMs ?? props.graph?.walk?.tickMs ?? 130,
);
// Run-once is the default: the walk plays through and holds the final frame.
// Opt into looping via the `walkLoop` prop or the fixture's `walk.loop`.
const walkLooping = computed(
  () => props.walkLoop ?? props.graph?.walk?.loop ?? false,
);

/** The internal play-head, advanced by the timer while `play` is true. */
const frameIndex = ref(0);

/** Which frame to actually render: the live play-head while playing; otherwise
 *  `walkStep` if given (negative = from the end), else wherever we last stopped. */
const effectiveFrameIndex = computed(() => {
  const n = walkFrames.value.length;
  if (n === 0) return 0;
  const clamp = (i: number) => Math.max(0, Math.min(i, n - 1));
  if (!props.play && props.walkStep != null) {
    return clamp(props.walkStep < 0 ? n + props.walkStep : props.walkStep);
  }
  return clamp(frameIndex.value);
});

const currentFrame = computed<WalkFrame | null>(() =>
  walkActive.value ? walkFrames.value[effectiveFrameIndex.value] ?? null : null,
);

/** Cumulative visit-heat (0..1) for the current frame. */
const heatMap = computed<Record<string, number>>(
  () => currentFrame.value?.heat ?? {},
);

/**
 * Per-edge recency rank (0..1) along the current walk trail: the newest hop = 1
 * (brightest/thickest, the walker's current step), older trail edges fade toward 0.
 * Last occurrence wins, so a retraced edge re-brightens. Empty outside walk mode.
 */
const edgeTrailRank = computed<Map<string, number>>(() => {
  const m = new Map<string, number>();
  const edges = currentFrame.value?.edges;
  if (!edges || edges.length === 0) return m;
  const n = edges.length;
  edges.forEach(([src, dst, key], i) => {
    // i = n-1 (newest) → 1; i = 0 (oldest) → ~0.35 floor so the tail stays visible.
    const rank = n === 1 ? 1 : 0.35 + 0.65 * (i / (n - 1));
    m.set(edgeIdOf(src, dst, key), rank);
  });
  return m;
});

// --- the timer (rAF-driven, client-only; never runs during SSR/build) -------
let walkRaf: number | null = null;
let walkLast = 0;

function stopWalk(): void {
  if (walkRaf !== null) {
    cancelAnimationFrame(walkRaf);
    walkRaf = null;
  }
}

function tickWalk(now: number): void {
  if (!props.play) {
    walkRaf = null;
    return;
  }
  const n = walkFrames.value.length;
  if (n === 0) {
    walkRaf = null;
    return;
  }
  const elapsed = now - walkLast;
  if (elapsed >= walkTick.value) {
    // Carry the remainder so we don't drift, but never advance >1 frame per RAF.
    walkLast = now - (elapsed % walkTick.value);
    let next = frameIndex.value + 1;
    if (next >= n) {
      if (walkLooping.value) {
        next = 0;
      } else {
        frameIndex.value = n - 1;
        walkRaf = null;
        return;
      }
    }
    frameIndex.value = next;
  }
  walkRaf = requestAnimationFrame(tickWalk);
}

function startWalk(): void {
  stopWalk();
  if (!walkActive.value || typeof requestAnimationFrame === 'undefined') return;
  frameIndex.value = 0; // (re)start the walk from the seed
  walkLast = typeof performance !== 'undefined' ? performance.now() : 0;
  walkRaf = requestAnimationFrame(tickWalk);
}

watch(
  () => props.play,
  (p) => {
    if (p) startWalk();
    else stopWalk();
  },
);

/** Is any highlight active right now? (drives focus+context dimming). */
const highlightActive = computed(
  () =>
    walkActive.value || (reveal.value !== null && props.step !== undefined),
);

/**
 * Out-degree per source node. A high-degree "hub" (e.g. the recipe node, with
 * dozens of CONTAINS/HAS_STEP edges) is the thing that piles identical chips,
 * so we use this to collapse repeated rels around hubs (see chipEdges).
 */
const outDegree = computed<Map<string, number>>(() => {
  const m = new Map<string, number>();
  for (const l of links.value) m.set(l.source, (m.get(l.source) ?? 0) + 1);
  return m;
});
/** A source node counts as a "hub" once it fans out past this many edges. */
const hubDegree = computed(() => rt.value.density.hubDegree);

/** The set of node ids and edge ids that are ACTIVE at the current step. */
const activeSets = computed(() => {
  const activeNodes = new Set<string>();
  const activeEdges = new Set<string>();
  // Walk mode: only the walker head(s) are "active" (brightest + glow). The trail
  // edges (the excursion since the last restart) are lit too, but their endpoint
  // nodes are NOT force-activated — they read via their accumulated heat instead,
  // so the single glowing head stays unambiguously "where the walker is now".
  if (walkActive.value) {
    const f = currentFrame.value;
    if (f) {
      for (const id of f.heads ?? []) activeNodes.add(id);
      for (const [src, dst, key] of f.edges ?? []) {
        activeEdges.add(edgeIdOf(src, dst, key));
      }
    }
    return { activeNodes, activeEdges };
  }
  if (!highlightActive.value || !reveal.value) {
    return { activeNodes, activeEdges };
  }
  const r = reveal.value;
  const step = Math.max(0, Math.min(props.step ?? 0, r.length - 1));
  // Which steps contribute? cumulative → 0..step, replace → just step.
  const from = props.revealMode === 'replace' ? step : 0;
  for (let k = from; k <= step; k++) {
    const s = r[k];
    if (!s) continue;
    for (const id of s.nodes ?? []) activeNodes.add(id);
    for (const [src, dst, key] of s.edges ?? []) {
      activeEdges.add(edgeIdOf(src, dst, key));
      // Light the endpoints of any active edge too, so a path always reads
      // as a connected route even if a node id wasn't listed explicitly.
      activeNodes.add(src);
      activeNodes.add(dst);
    }
  }
  return { activeNodes, activeEdges };
});

// ---------------------------------------------------------------------------
// Camera (viewBox) — defined here, AFTER activeSets, because the focus target
// depends on the active set. Node coordinates never change; only the camera
// frame moves, so F11 (no per-node position jump) holds.
// ---------------------------------------------------------------------------

/**
 * The camera TARGET box. Normally the full graph; but when `focusReveal` is on
 * and a reveal step is active, a box framing just the active nodes (plus a
 * generous margin), keeping the host's aspect ratio so the lit path isn't
 * distorted.
 */
const targetBox = computed<Box>(() => {
  const full = fullBox.value;
  if (!props.focusReveal || !highlightActive.value) return full;
  const { activeNodes } = activeSets.value;
  if (activeNodes.size === 0) return full;

  // Tight bounds around the active nodes (account for their radii + glow halo).
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const n of nodes.value) {
    if (!activeNodes.has(n.id)) continue;
    const p = positions.value.get(n.id);
    if (!p) continue;
    const r = nodeRadius(n.kind) * 1.4;
    minX = Math.min(minX, p.x - r);
    minY = Math.min(minY, p.y - r);
    maxX = Math.max(maxX, p.x + r);
    maxY = Math.max(maxY, p.y + r);
  }
  if (!isFinite(minX)) return full;

  // Margin so the path doesn't kiss the frame edges (and labels have room).
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  const marginFactor = 1.9; // 1 = tight; >1 leaves breathing room
  let w = Math.max((maxX - minX) * marginFactor, 60);
  let h = Math.max((maxY - minY) * marginFactor, 60);

  // Match the full box's aspect ratio so the framed box is a clean zoom-in,
  // not a stretched crop.
  const aspect = full.width / full.height;
  if (w / h < aspect) w = h * aspect;
  else h = w / aspect;

  // Never zoom out past the full graph.
  w = Math.min(w, full.width);
  h = Math.min(h, full.height);
  return { minX: cx - w / 2, minY: cy - h / 2, width: w, height: h };
});

/**
 * The CURRENT (animated) camera box, tweened toward `targetBox` with a short
 * eased transition so focusing in/out glides rather than snapping.
 */
const currentBox = ref<Box>(fullBox.value);
let rafId: number | null = null;
let tweenStart = 0;
let tweenFrom: Box = fullBox.value;
const TWEEN_MS = 360;

function lerpBox(a: Box, b: Box, t: number): Box {
  return {
    minX: a.minX + (b.minX - a.minX) * t,
    minY: a.minY + (b.minY - a.minY) * t,
    width: a.width + (b.width - a.width) * t,
    height: a.height + (b.height - a.height) * t,
  };
}
/** easeInOutCubic. */
function ease(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

function animateCameraTo(dest: Box, instant = false): void {
  if (rafId !== null) {
    cancelAnimationFrame(rafId);
    rafId = null;
  }
  if (instant || typeof requestAnimationFrame === 'undefined') {
    currentBox.value = dest;
    return;
  }
  tweenFrom = currentBox.value;
  tweenStart = performance.now();
  const tick = (now: number) => {
    const t = Math.min(1, (now - tweenStart) / TWEEN_MS);
    currentBox.value = lerpBox(tweenFrom, dest, ease(t));
    if (t < 1) rafId = requestAnimationFrame(tick);
    else rafId = null;
  };
  rafId = requestAnimationFrame(tick);
}

// Re-aim the camera whenever the target changes (step / focus / graph swap).
watch(
  targetBox,
  (dest, prev) => {
    // First paint / graph swap → jump; subsequent step changes → glide.
    animateCameraTo(dest, prev === undefined);
  },
  { immediate: true },
);

/** viewBox string fed to the SVG, from the animated camera box. */
const viewBox = computed(() => {
  const b = currentBox.value;
  return `${b.minX} ${b.minY} ${b.width} ${b.height}`;
});

/**
 * A scalar that scales stroke widths / glow / fonts with the *current* camera
 * box so the graph reads consistently whether framing the whole graph or a
 * zoomed-in path. Normalised against a "reference" box diagonal.
 */
const scale = computed(() => {
  const { width, height } = currentBox.value;
  const diag = Math.hypot(width, height);
  const ref = 900; // reference diagonal that looks right at 1×
  return Math.max(0.6, Math.min(3, diag / ref));
});

// ---------------------------------------------------------------------------
// Edge geometry — group parallel edges by (u,v) and fan them with arcs
// ---------------------------------------------------------------------------

interface RenderEdge {
  id: string;
  source: string;
  target: string;
  rel: string;
  /** SVG path `d`. */
  path: string;
  /** Midpoint of the arc, for the edge-label chip. */
  mid: Point;
  /** Whether this edge is active at the current step. */
  active: boolean;
  /** Whether this edge's (u,v) pair is the chip-bearing representative. */
  showChip: boolean;
  /** Whether to draw an arrowhead (directed) on this edge. */
  directed: boolean;
  /** Walk-trail recency (0..1); 1 = the current hop. 0 when not on the trail. */
  rank: number;
}

/**
 * Build the rendered edges. Parallel edges between the same ordered pair are
 * fanned out as arcs with increasing curvature; a self-edge (u==v) draws a
 * loop. Edge-label chips are de-duplicated to one per (u,v) pair.
 */
const renderEdges = computed<RenderEdge[]>(() => {
  const pos = positions.value;
  const { activeEdges } = activeSets.value;
  const out: RenderEdge[] = [];

  // Group by ordered (source,target) so parallels fan consistently.
  const groups = new Map<string, GraphEdge[]>();
  for (const l of links.value) {
    const gk = `${l.source}${l.target}`;
    const arr = groups.get(gk);
    if (arr) arr.push(l);
    else groups.set(gk, [l]);
  }
  // Track which (u,v) already has a chip (de-dupe parallel labels).
  const chipShown = new Set<string>();
  // id -> kind, so we can trim each edge back to its endpoints' node radii.
  const kindOf = new Map(nodes.value.map((nn) => [nn.id, nn.kind]));

  for (const [, group] of groups) {
    const n = group.length;
    group.forEach((l, i) => {
      const a = pos.get(l.source);
      const b = pos.get(l.target);
      if (!a || !b) return;
      const id = edgeIdOf(l.source, l.target, l.key);
      const active = activeEdges.has(id);
      const rank = edgeTrailRank.value.get(id) ?? 0;
      const rel = (l.rel ?? l.label ?? '').toString();

      let path: string;
      let mid: Point;

      if (l.source === l.target) {
        // Self-loop: a small circle above the node.
        const r = nodeRadius(nodes.value.find((nn) => nn.id === l.source)?.kind);
        const loop = r * 1.6 + i * r * 0.7;
        path = `M ${a.x} ${a.y} C ${a.x - loop} ${a.y - loop}, ${a.x + loop} ${a.y - loop}, ${a.x} ${a.y}`;
        mid = { x: a.x, y: a.y - loop * 1.1 };
      } else {
        // Fan parallels symmetrically around the straight line. The single
        // edge of a pair is drawn (almost) straight; extra ones bow out.
        // curveIndex in {…, -1, 0, +1, …} so the fan is centred.
        const curveIndex = i - (n - 1) / 2;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.hypot(dx, dy) || 1;
        // Curvature grows with fan index; a lone edge gets a hair of curve.
        const bow = (n === 1 ? 0.06 : 0.16) * curveIndex + (n === 1 ? 0.04 : 0);
        // Perpendicular offset of the control point.
        const off = bow * dist;
        const mx = (a.x + b.x) / 2;
        const my = (a.y + b.y) / 2;
        // Unit perpendicular.
        const px = -dy / dist;
        const py = dx / dist;
        const cx = mx + px * off;
        const cy = my + py * off;
        // Trim both ends back to the node boundaries (along the curve's own
        // tangents: c-a at the start, b-c at the end) so the line leaves the
        // source circle and — crucially — the arrowhead lands just OUTSIDE the
        // target circle instead of hidden under it. Skip the trim when the nodes
        // are so close it would invert the segment.
        const sr = nodeRadius(kindOf.get(l.source));
        const tr = nodeRadius(kindOf.get(l.target));
        const endGap = rt.value.edges.endGap;
        const sdx = cx - a.x;
        const sdy = cy - a.y;
        const sl = Math.hypot(sdx, sdy) || 1;
        const edx = b.x - cx;
        const edy = b.y - cy;
        const el = Math.hypot(edx, edy) || 1;
        let sx = a.x;
        let sy = a.y;
        let ex = b.x;
        let ey = b.y;
        if (dist > sr + tr + endGap + 2) {
          sx = a.x + (sdx / sl) * sr;
          sy = a.y + (sdy / sl) * sr;
          ex = b.x - (edx / el) * (tr + endGap);
          ey = b.y - (edy / el) * (tr + endGap);
        }
        path = `M ${sx} ${sy} Q ${cx} ${cy} ${ex} ${ey}`;
        // Quadratic midpoint (t=0.5) sits halfway between line-mid and ctrl.
        mid = { x: (mx + cx) / 2, y: (my + cy) / 2 };
      }

      // One chip per ordered (u,v) pair, and only if the pair has a rel.
      const gk = `${l.source}${l.target}`;
      let showChip = false;
      if (rel && !chipShown.has(gk)) {
        chipShown.add(gk);
        showChip = true;
      }

      const directed =
        typeof l.directed === 'boolean' ? l.directed : graphDirected.value;
      out.push({ id, source: l.source, target: l.target, rel, path, mid, active, showChip, directed, rank });
    });
  }
  return out;
});

// ---------------------------------------------------------------------------
// Node render data
// ---------------------------------------------------------------------------

interface RenderNode {
  id: string;
  kind?: string;
  label: string;
  x: number;
  y: number;
  r: number;
  active: boolean;
  /** Walk-mode visit heat (0..1); 0 outside walk mode. */
  heat: number;
}

const renderNodes = computed<RenderNode[]>(() => {
  const pos = positions.value;
  const { activeNodes } = activeSets.value;
  const heat = heatMap.value;
  const out: RenderNode[] = [];
  for (const n of nodes.value) {
    const p = pos.get(n.id);
    if (!p) continue;
    const active = activeNodes.has(n.id);
    const h = walkActive.value ? heat[n.id] ?? 0 : 0;
    // Heated-but-not-the-walker nodes swell with their visit count, so the
    // high-PPR nodes visibly grow as the walk piles up on them.
    const grow = walkActive.value && !active ? 1 + 0.55 * h : 1;
    out.push({
      id: n.id,
      kind: n.kind,
      label: truncate(n.label ?? n.id, rt.value.labels.maxChars),
      x: p.x,
      y: p.y,
      r: nodeRadius(n.kind) * grow,
      active,
      heat: h,
    });
  }
  return out;
});

/** Truncate a label with an ellipsis. Default matches the theme; the
 *  `labels.maxChars` / `labels.edgeMaxChars` params override per graph. */
function truncate(s: string, max = LABEL.maxChars): string {
  return s.length > max ? `${s.slice(0, max - 1).trimEnd()}…` : s;
}

/**
 * Per-edge stroke-width multiplier from the `weight` attribute, active only when
 * `edges.widthByWeight` is on. Weights are normalised across the graph's weighted
 * edges to a modest [WMIN..WMAX] spread, so width reads as *relative* magnitude
 * rather than a raw value (a weight of 300 doesn't draw a 300×-thick line).
 * Edges with no numeric weight — or when the toggle is off — get 1 (no change).
 */
const weightFactors = computed<Map<string, number>>(() => {
  const m = new Map<string, number>();
  if (!rt.value.edges.widthByWeight) return m;
  const weights = links.value
    .map((l) => l.weight)
    .filter((w): w is number => typeof w === 'number' && isFinite(w));
  if (weights.length === 0) return m;
  const wmin = Math.min(...weights);
  const wmax = Math.max(...weights);
  const WMIN = 0.6; // thinnest multiple (lightest edge)
  const WMAX = 2.6; // thickest multiple (heaviest edge)
  for (const l of links.value) {
    if (typeof l.weight !== 'number' || !isFinite(l.weight)) continue;
    const t = wmax === wmin ? 0.5 : (l.weight - wmin) / (wmax - wmin);
    m.set(edgeIdOf(l.source, l.target, l.key), WMIN + (WMAX - WMIN) * t);
  }
  return m;
});

// ---------------------------------------------------------------------------
// Visual-state helpers (rest vs active vs faded behind a highlight)
// ---------------------------------------------------------------------------

/** Node fill colour for its state. */
function nodeFill(n: RenderNode): string {
  const c = colorForKind(n.kind);
  // In walk mode every node uses its lit hue; the *opacity* carries the heat.
  if (walkActive.value) return c.active;
  return n.active ? c.active : c.rest;
}
/** Node opacity: full when active; rest normally; faded when dimmed behind a highlight. */
function nodeOpacity(n: RenderNode): number {
  const o = rt.value.opacity;
  if (n.active) return o.active;
  // Walk mode: a cold node sits near-invisible, a hot one near-full — the heat ramp.
  if (walkActive.value) return 0.1 + 0.85 * n.heat;
  return highlightActive.value ? o.faded : o.rest;
}
/** A brighter ring on active nodes lifts luminance and reads as "lit". */
function nodeStroke(n: RenderNode): string {
  return n.active ? rt.value.nodes.activeRing : 'transparent';
}

/** Edge stroke colour for its state. */
function edgeStroke(e: RenderEdge): string {
  return e.active ? rt.value.edges.active : rt.value.edges.rest;
}
/** Edge opacity, with focus+context dimming of resting edges behind a highlight. */
function edgeOpacity(e: RenderEdge): number {
  const o = rt.value.opacity;
  // Walk trail: fade older hops, brighten the current one (the comet tail).
  if (walkActive.value && e.active) return 0.25 + 0.75 * e.rank;
  if (e.active) return o.active;
  return highlightActive.value ? o.edgeDimmed : o.edgeRest;
}
function edgeWidth(e: RenderEdge): number {
  const ed = rt.value.edges;
  // Walk trail: thicken toward the current hop, thin for the faded tail.
  // (Walk widths are about motion, so weight scaling doesn't apply here.)
  if (walkActive.value && e.active) {
    return (ed.width + (ed.widthActive - ed.width) * e.rank) * scale.value;
  }
  const wf = weightFactors.value.get(e.id) ?? 1;
  return (e.active ? ed.widthActive : ed.width) * scale.value * wf;
}
/** Only the current hop glows during a walk (a faded tail glowing reads muddy);
 *  outside walk mode every active edge glows as before. */
function edgeShouldGlow(e: RenderEdge): boolean {
  return !walkActive.value || e.rank >= 0.999;
}

/** Label opacity tracks its node so dimmed nodes' labels recede hard. */
function labelOpacity(n: RenderNode): number {
  if (n.active) return 1;
  // Walk mode: labels fade in with heat, so the names the walk favours surface.
  if (walkActive.value) return Math.max(0.12, n.heat);
  return highlightActive.value ? 0.1 : 0.85;
}

// ---------------------------------------------------------------------------
// Edge-label density gate
// ---------------------------------------------------------------------------

/**
 * Auto-hide edge labels on dense graphs even if requested. Gated by both the
 * `showEdgeLabels` prop AND the `labels.showEdges` param (either can suppress),
 * then the density limit.
 */
const edgeLabelsVisible = computed(
  () =>
    props.showEdgeLabels &&
    rt.value.labels.showEdges &&
    links.value.length <= rt.value.density.edgeLabelLimit,
);

/** Truncate a (sometimes verbose) relationship label for the chip. */
function truncRel(s: string): string {
  return truncate(s, 18);
}

/**
 * Chip-bearing edges that should actually show a label. The big clutter source
 * is a hub fanning out N identical rels (a recipe node with dozens of CONTAINS
 * / HAS_STEP edges → dozens of identical chips piling over the hub). We thin in
 * three layers:
 *
 *   1. Hub collapse: for a high-degree source node, a given rel string renders
 *      at most ONCE (so "CONTAINS" appears once near the recipe hub, not 12×).
 *   2. Spatial thinning: drop any resting chip whose midpoint collides with one
 *      already placed.
 *   3. Active always wins: lit-path chips (CITES / SUBSTITUTES_FOR) are placed
 *      first and never thinned — and they surface even past the density gate so
 *      the money shot stays annotated.
 */
const chipEdges = computed<RenderEdge[]>(() => {
  const placed: Point[] = [];
  const result: RenderEdge[] = [];
  // Minimum centre-to-centre spacing between chips (scales with viewBox).
  const minGap = 30 * scale.value;
  const gap2 = minGap * minGap;
  const tooClose = (p: Point) =>
    placed.some((q) => {
      const dx = p.x - q.x;
      const dy = p.y - q.y;
      return dx * dx + dy * dy < gap2;
    });

  // Tracks (sourceNode + rel) already shown for hub collapse.
  const hubRelShown = new Set<string>();
  const place = (e: RenderEdge) => {
    placed.push(e.mid);
    result.push(e);
  };

  if (edgeLabelsVisible.value) {
    // Pass A — active chips first, unconditionally (never thinned).
    for (const e of renderEdges.value) {
      if (e.active && e.showChip && e.rel) place(e);
    }
    // Pass B — resting chips, with hub-collapse + spatial thinning.
    for (const e of renderEdges.value) {
      if (e.active || !e.showChip || !e.rel) continue;
      // Hub collapse: if this source is a hub, only the first chip per rel.
      if ((outDegree.value.get(e.source) ?? 0) >= hubDegree.value) {
        const hk = `${e.source}\u0000${e.rel}`;
        if (hubRelShown.has(hk)) continue;
        hubRelShown.add(hk);
      }
      if (tooClose(e.mid)) continue;
      place(e);
    }
  } else if (highlightActive.value && !walkActive.value) {
    // Dense graph (reveal): only annotate the lit path. In WALK mode we suppress
    // chips entirely — every hop is the same rel, so the labels are pure clutter
    // and the trail is about motion, not relationships.
    for (const e of renderEdges.value) {
      if (e.active && e.showChip && e.rel) place(e);
    }
  }
  return result;
});

/** Estimate a chip's width from its text length (no DOM measurement needed). */
function chipWidth(rel: string): number {
  return (
    truncRel(rel).length * rt.value.labels.edgeFontSize * 0.6 +
    EDGE_CHIP.padX * 2
  );
}
const chipHeight = computed(
  () => rt.value.labels.edgeFontSize + EDGE_CHIP.padY * 2,
);

// ---------------------------------------------------------------------------
// Legend — one swatch per kind actually present
// ---------------------------------------------------------------------------

const legendKinds = computed<string[]>(() => {
  const present = new Set<string>();
  for (const n of nodes.value) present.add(n.kind ?? 'default');
  // Stable, readable ordering.
  const order = ['recipe', 'ingredient', 'step', 'technique', 'entity', 'case', 'default'];
  return order.filter((k) => present.has(k));
});

// ---------------------------------------------------------------------------
// Derived sizing for fonts / arrowheads that should scale with the viewBox
// ---------------------------------------------------------------------------

const nodeFontSize = computed(() => rt.value.labels.nodeFontSize * scale.value);
const edgeFontSize = computed(() => rt.value.labels.edgeFontSize * scale.value);
const glowStd = computed(() => rt.value.glow.stdDeviation * scale.value);

/** Arrowhead size in viewBox units, scaled by the camera and the per-graph
 *  `edges.arrowScale` param (so a sparse flow graph can show bolder arrows). */
const arrowSize = computed(() => 7 * scale.value * rt.value.edges.arrowScale);

// ---------------------------------------------------------------------------
// Glow mode + global colour filter (params-driven)
// ---------------------------------------------------------------------------

/** True when using the SVG <filter> glow (default); false → CSS drop-shadow. */
const glowIsSvg = computed(() => rt.value.glow.mode === 'svg');

/** The SVG-filter reference for active elements (svg mode only). */
const glowFilterAttr = computed(() =>
  glowIsSvg.value ? `url(#${glowId})` : undefined,
);

/** Parse `#rgb`/`#rrggbb` into an `rgba()` string at the given alpha. */
function hexToRgba(hex: string, alpha: number): string {
  let h = hex.replace('#', '');
  if (h.length === 3 || h.length === 4) {
    h = h
      .slice(0, 3)
      .split('')
      .map((c) => c + c)
      .join('');
  }
  const r = parseInt(h.slice(0, 2), 16) || 0;
  const g = parseInt(h.slice(2, 4), 16) || 0;
  const b = parseInt(h.slice(4, 6), 16) || 0;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/** CSS `filter` for active elements in 'filter' glow mode (a coloured halo). */
const glowFilterStyle = computed(() => {
  if (glowIsSvg.value) return undefined;
  const g = rt.value.glow;
  const blur = g.stdDeviation * scale.value;
  const colour = hexToRgba(g.color, g.opacity);
  return `drop-shadow(0 0 ${blur}px ${colour})`;
});

/** Global colour post-effect on the SVG (undefined at the 1/1/1 no-op identity). */
const colorFilter = computed(() => cssColorFilter(rt.value));

// ---------------------------------------------------------------------------
// Readiness flag for screenshot harnesses.
// ---------------------------------------------------------------------------

const ready = ref(false);
/** Per-render counter so batch screenshot harnesses can detect a *new* render
 *  completed (not just observe a stale `true` from the previous fixture/step). */
function markReady() {
  ready.value = true;
  if (typeof window !== 'undefined') {
    const w = window as unknown as { __graphReady?: boolean; __graphRenderId?: number };
    w.__graphReady = true;
    w.__graphRenderId = (w.__graphRenderId ?? 0) + 1;
  }
}
/** Clear the ready flag at the start of a (re)render so a harness can't capture
 *  mid-update; markReady() flips it back true (and bumps the render id). */
function clearReady() {
  ready.value = false;
  if (typeof window !== 'undefined') {
    (window as unknown as { __graphReady?: boolean }).__graphReady = false;
  }
}
onMounted(async () => {
  await nextTick();
  markReady();
});
// Re-assert readiness when the graph or step changes (HMR / prop updates).
watch(
  () => [props.graph, props.step],
  async () => {
    clearReady();
    await nextTick();
    markReady();
  },
);
// Stop any in-flight camera tween / walk timer when the component goes away.
onUnmounted(() => {
  if (rafId !== null) cancelAnimationFrame(rafId);
  stopWalk();
});
</script>

<template>
  <!--
    Single positioned root so the SVG fills it and the HTML legend can anchor
    to a corner. Transparent throughout: the host page owns the dark ground.
  -->
  <div class="graph-view-root">
  <svg
    class="graph-view"
    :viewBox="viewBox"
    :data-ready="ready"
    :style="{ filter: colorFilter }"
    preserveAspectRatio="xMidYMid meet"
    xmlns="http://www.w3.org/2000/svg"
  >
    <defs>
      <!--
        SVG-native glow: blur the source, then merge the blurred copy under the
        crisp original. Wide filter region so the halo isn't clipped.
      -->
      <filter
        :id="glowId"
        x="-100%"
        y="-100%"
        width="300%"
        height="300%"
        filterUnits="objectBoundingBox"
      >
        <feGaussianBlur in="SourceGraphic" :stdDeviation="glowStd" result="blur" />
        <feMerge>
          <!-- Single blur layer (not doubled) for a subtler, more diffuse halo. -->
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>

      <!-- Arrowhead markers: one muted (rest), one bright (active). -->
      <marker
        :id="`arrow-rest-${uid}`"
        viewBox="0 0 10 10"
        refX="9"
        refY="5"
        :markerWidth="arrowSize"
        :markerHeight="arrowSize"
        orient="auto-start-reverse"
        markerUnits="userSpaceOnUse"
      >
        <path d="M 0 1 L 9 5 L 0 9 z" :fill="rt.edges.rest" />
      </marker>
      <marker
        :id="`arrow-active-${uid}`"
        viewBox="0 0 10 10"
        refX="9"
        refY="5"
        :markerWidth="arrowSize * 1.1"
        :markerHeight="arrowSize * 1.1"
        orient="auto-start-reverse"
        markerUnits="userSpaceOnUse"
      >
        <path d="M 0 1 L 9 5 L 0 9 z" :fill="rt.edges.active" />
      </marker>
    </defs>

    <!-- ───────────────────────── smoke test (no graph) ───────────────────── -->
    <g v-if="!hasGraph" :filter="`url(#${glowId})`">
      <circle cx="0" cy="-6" r="26" :fill="colorForKind('recipe').active" :style="{ opacity: OPACITY.active }" />
      <text
        x="0"
        y="40"
        text-anchor="middle"
        :font-size="LABEL.nodeFontSize"
        :font-family="LABEL.fontFamily"
        :fill="LABEL.color"
      >
        glow smoke test
      </text>
    </g>

    <!-- ───────────────────────── real graph ──────────────────────────────── -->
    <template v-else>
      <!-- EDGES (drawn first, under nodes). Resting then active for z-order. -->
      <g class="edges">
        <!-- Resting / dimmed edges first. -->
        <path
          v-for="e in renderEdges.filter((x) => !x.active)"
          :key="`er-${e.id}`"
          :d="e.path"
          fill="none"
          :stroke="edgeStroke(e)"
          :stroke-width="edgeWidth(e)"
          :style="{ opacity: edgeOpacity(e) }"
          :marker-end="e.directed ? `url(#arrow-rest-${uid})` : undefined"
          class="edge"
        />
        <!-- Active edges on top, with glow + bright arrowhead. -->
        <path
          v-for="e in renderEdges.filter((x) => x.active)"
          :key="`ea-${e.id}`"
          :d="e.path"
          fill="none"
          :stroke="edgeStroke(e)"
          :stroke-width="edgeWidth(e)"
          :style="{ opacity: edgeOpacity(e), filter: edgeShouldGlow(e) ? glowFilterStyle : undefined }"
          :marker-end="e.directed ? `url(#arrow-active-${uid})` : undefined"
          :filter="edgeShouldGlow(e) ? glowFilterAttr : undefined"
          class="edge edge-active"
        />
      </g>

      <!-- EDGE-LABEL CHIPS (deduped per u,v; density-gated). -->
      <g v-if="chipEdges.length" class="edge-labels">
        <g v-for="e in chipEdges" :key="`chip-${e.id}`" :style="{ opacity: highlightActive && !e.active ? 0.2 : 1 }">
          <rect
            :x="e.mid.x - chipWidth(e.rel) / 2"
            :y="e.mid.y - chipHeight / 2"
            :width="chipWidth(e.rel)"
            :height="chipHeight"
            :rx="rt.chip.radius"
            :fill="rt.chip.fill"
            :stroke="rt.chip.stroke"
            stroke-width="0.75"
          />
          <text
            :x="e.mid.x"
            :y="e.mid.y"
            text-anchor="middle"
            dominant-baseline="central"
            :font-size="edgeFontSize"
            :font-family="LABEL.fontFamily"
            :fill="e.active ? '#ffffff' : rt.chip.text"
          >
            {{ truncRel(e.rel) }}
          </text>
        </g>
      </g>

      <!-- NODES. Resting then active for z-order; glow only on active group. -->
      <g class="nodes">
        <!-- Resting / dimmed nodes. -->
        <circle
          v-for="n in renderNodes.filter((x) => !x.active)"
          :key="`nr-${n.id}`"
          :cx="n.x"
          :cy="n.y"
          :r="n.r"
          :fill="nodeFill(n)"
          :style="{ opacity: nodeOpacity(n) }"
          class="node"
        />
        <!-- Active nodes: glow in their own hue + bright ring. -->
        <g class="nodes-active" :filter="glowFilterAttr" :style="{ filter: glowFilterStyle }">
          <circle
            v-for="n in renderNodes.filter((x) => x.active)"
            :key="`na-${n.id}`"
            :cx="n.x"
            :cy="n.y"
            :r="n.r * 1.18"
            :fill="nodeFill(n)"
            :style="{ opacity: nodeOpacity(n) }"
            :stroke="nodeStroke(n)"
            :stroke-width="1.5 * scale"
            class="node node-active"
          />
        </g>
      </g>

      <!-- NODE LABELS (separate layer → crisp, never inherit the node glow). -->
      <g v-if="rt.labels.showNodes" class="node-labels">
        <text
          v-for="n in renderNodes"
          :key="`l-${n.id}`"
          :x="n.x"
          :y="n.y + n.r + nodeFontSize * 0.95"
          text-anchor="middle"
          :font-size="nodeFontSize"
          :font-family="LABEL.fontFamily"
          :font-weight="n.active ? 600 : 400"
          :fill="n.active ? '#ffffff' : rt.labels.color"
          :style="{ opacity: labelOpacity(n) }"
          class="node-label"
        >
          {{ n.label }}
        </text>
      </g>
    </template>
  </svg>

  <!-- LEGEND — HTML overlay, corner from params. One swatch per present kind. -->
  <div
    v-if="hasGraph && showLegend && rt.legend.show && legendKinds.length"
    class="graph-legend"
    :class="`pos-${rt.legend.position}`"
  >
    <div v-for="k in legendKinds" :key="k" class="legend-row">
      <span class="legend-swatch" :style="{ background: colorForKind(k).active }" />
      <span class="legend-label">{{ k }}</span>
    </div>
  </div>

  <!-- EDIT MODE (dev only): a gear to open this instance's params tuner. -->
  <button
    v-if="showGear && !panelOpen"
    class="graph-gear"
    title="Tune graph params (Shift+G)"
    @click="togglePanel"
  >
    ⚙
  </button>
  <GraphConfigurator
    v-if="showGear && panelOpen"
    :resolved="rt"
    :overrides="liveParams || {}"
    @update:overrides="liveParams = $event"
    @close="panelOpen = false"
  />
  </div>
</template>

<style scoped>
.graph-view-root {
  position: relative;
  width: 100%;
  height: 100%;
  background: transparent;
}
.graph-view {
  display: block;
  width: 100%;
  height: 100%;
  /* Transparent: no background fill. The host page owns the ground colour. */
  background: transparent;
  overflow: visible;
}

/* Node labels carry a subtle shadow so near-white text reads on any hue. */
.node-label {
  paint-order: stroke fill;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.85), 0 0 3px rgba(0, 0, 0, 0.7);
  pointer-events: none;
}

/* Smooth brightness/opacity transitions; position is never animated. */
.node,
.edge,
.node-label {
  transition:
    opacity 200ms ease,
    fill 200ms ease,
    stroke 200ms ease,
    stroke-width 200ms ease;
}

/* Legend chrome — a small dark card so it reads on the dark ground. */
.graph-legend {
  position: absolute;
  /* Default corner (bottom-right); the .pos-* class from legend.position always
     applies on top and can move it to any corner. */
  bottom: 14px;
  right: 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(20, 23, 28, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(4px);
  font-family: ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  font-size: 12px;
  color: #d7dbe0;
  pointer-events: none;
}
.legend-row {
  display: flex;
  align-items: center;
  gap: 7px;
}
.legend-swatch {
  width: 11px;
  height: 11px;
  border-radius: 3px;
  flex: 0 0 auto;
}
.legend-label {
  text-transform: capitalize;
  letter-spacing: 0.02em;
}

/* Edit-mode gear (dev only). Sits top-right; never present in a prod build. */
.graph-gear {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 50;
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  line-height: 1;
  color: #c4c9d1;
  background: rgba(18, 20, 25, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 7px;
  cursor: pointer;
  pointer-events: auto;
  backdrop-filter: blur(4px);
}
.graph-gear:hover {
  color: #fff;
  background: rgba(30, 34, 41, 0.92);
}

/* Legend corner placement (legend.position param). top-left is the default. */
.graph-legend.pos-top-left {
  top: 14px;
  left: 14px;
  right: auto;
  bottom: auto;
}
.graph-legend.pos-top-right {
  top: 14px;
  right: 14px;
  left: auto;
  bottom: auto;
}
.graph-legend.pos-bottom-left {
  bottom: 14px;
  left: 14px;
  right: auto;
  top: auto;
}
.graph-legend.pos-bottom-right {
  bottom: 14px;
  right: 14px;
  left: auto;
  top: auto;
}
</style>
