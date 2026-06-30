/**
 * graph-params.ts
 * ---------------
 * Per-fixture (and per-slide) *presentation params* for <GraphView>.
 *
 * Think design tokens / CSS variables: a fixture can carry an optional `params`
 * block that overrides how the graph is *drawn* — legend placement, opacity,
 * saturation, glow, label sizes, layout spread — without ever touching the
 * graph's topology. Defaults stay exactly as `graph-theme.ts` defines them; a
 * fixture only overrides what it names.
 *
 * Three ideas keep this safe:
 *   1. One source of truth for defaults — DEFAULT_PARAMS is derived FROM
 *      graph-theme.ts (we don't re-type the hexes), so "no params" renders
 *      byte-identically to before this file existed.
 *   2. One merge with clear precedence — resolveParams(defaults, fixture, prop,
 *      live) folds layers left-to-right, later wins.
 *   3. Fail soft — unknown keys are ignored, numbers are clamped to sane
 *      ranges, bad colours/enums fall back to the default. A bad param must
 *      never throw mid-talk; in dev we warn, in prod we stay silent.
 *
 * Pure TypeScript — no Vue, no DOM. The matplotlib notebook fallback simply
 * ignores all of this.
 */

import {
  EDGE,
  EDGE_CHIP,
  GLOW,
  GLOW_MODE,
  LABEL,
  OPACITY,
  type GlowMode,
} from './graph-theme';

// ---------------------------------------------------------------------------
// Public param shape — everything optional + partial (what a fixture writes).
// ---------------------------------------------------------------------------

export type LegendPosition =
  | 'top-left'
  | 'top-right'
  | 'bottom-left'
  | 'bottom-right';

/** The optional, partial params a fixture / slide / live-edit can supply. */
export interface GraphParams {
  legend?: Partial<{ show: boolean; position: LegendPosition }>;
  opacity?: Partial<{
    rest: number;
    active: number;
    faded: number;
    edgeRest: number;
    edgeDimmed: number;
  }>;
  color?: Partial<{ saturation: number; brightness: number; contrast: number }>;
  nodes?: Partial<{ radiusScale: number; activeRing: string }>;
  edges?: Partial<{
    width: number;
    widthActive: number;
    rest: string;
    active: string;
    /** Arrowhead size multiplier (1 = default). */
    arrowScale: number;
    /** Gap (viewBox units) between the arrow tip and the target node circle. */
    endGap: number;
    /** Scale each edge's stroke width by its `weight` attribute (default off).
     *  Weights are normalised across the graph to a modest spread; edges with no
     *  numeric weight keep the base width. Opt-in so existing graphs are unchanged. */
    widthByWeight: boolean;
  }>;
  labels?: Partial<{
    showNodes: boolean;
    showEdges: boolean;
    nodeFontSize: number;
    edgeFontSize: number;
    color: string;
    maxChars: number;
    edgeMaxChars: number;
  }>;
  glow?: Partial<{
    mode: GlowMode;
    stdDeviation: number;
    color: string;
    opacity: number;
  }>;
  chip?: Partial<{
    fill: string;
    text: string;
    stroke: string;
    radius: number;
  }>;
  layout?: Partial<{
    spread: number;
    /** Explicit charge; null/absent → GraphView's size-based heuristic. */
    charge: number | null;
    /** Explicit link distance; null/absent → heuristic. */
    linkDistance: number | null;
    collidePadding: number;
    seed: number;
  }>;
  density?: Partial<{ edgeLabelLimit: number; hubDegree: number }>;
}

// ---------------------------------------------------------------------------
// Resolved shape — fully populated; the renderer reads this and nothing else.
// ---------------------------------------------------------------------------

export interface ResolvedTheme {
  legend: { show: boolean; position: LegendPosition };
  opacity: {
    rest: number;
    active: number;
    faded: number;
    edgeRest: number;
    edgeDimmed: number;
  };
  color: { saturation: number; brightness: number; contrast: number };
  nodes: { radiusScale: number; activeRing: string };
  edges: {
    width: number;
    widthActive: number;
    rest: string;
    active: string;
    arrowScale: number;
    endGap: number;
    widthByWeight: boolean;
  };
  labels: {
    showNodes: boolean;
    showEdges: boolean;
    nodeFontSize: number;
    edgeFontSize: number;
    color: string;
    maxChars: number;
    edgeMaxChars: number;
  };
  glow: { mode: GlowMode; stdDeviation: number; color: string; opacity: number };
  chip: { fill: string; text: string; stroke: string; radius: number };
  layout: {
    spread: number;
    /** null → GraphView falls back to its size-based heuristic. */
    charge: number | null;
    /** null → heuristic. */
    linkDistance: number | null;
    collidePadding: number;
    seed: number;
  };
  density: { edgeLabelLimit: number; hubDegree: number };
}

// ---------------------------------------------------------------------------
// Defaults — derived from graph-theme.ts so there is one source of truth.
// These reproduce today's behaviour exactly (see notes inline).
// ---------------------------------------------------------------------------

export const DEFAULT_PARAMS: ResolvedTheme = {
  legend: { show: true, position: 'bottom-right' },
  opacity: {
    rest: OPACITY.rest,
    active: OPACITY.active,
    faded: OPACITY.faded,
    // Edges currently share OPACITY.rest at rest …
    edgeRest: OPACITY.rest,
    // … and a hard-coded 0.12 when something else is highlighted.
    edgeDimmed: 0.12,
  },
  // 1.0 across the board → no SVG colour filter is emitted at all (see §5).
  color: { saturation: 1, brightness: 1, contrast: 1 },
  // activeRing matches today's hard-coded white active stroke.
  nodes: { radiusScale: 1, activeRing: '#ffffff' },
  edges: {
    width: EDGE.width,
    widthActive: EDGE.widthActive,
    rest: EDGE.rest,
    active: EDGE.active,
    // 1 = today's arrowhead size; endGap = arrow-tip clearance from the node.
    arrowScale: 1,
    endGap: 1,
    // off by default → no existing graph changes; opt in per-fixture / per-slide.
    widthByWeight: false,
  },
  labels: {
    showNodes: true,
    showEdges: true,
    nodeFontSize: LABEL.nodeFontSize,
    edgeFontSize: LABEL.edgeFontSize,
    color: LABEL.color,
    maxChars: LABEL.maxChars,
    edgeMaxChars: LABEL.edgeMaxChars,
  },
  glow: {
    mode: GLOW_MODE,
    stdDeviation: GLOW.stdDeviation,
    color: GLOW.color,
    opacity: GLOW.opacity,
  },
  chip: {
    fill: EDGE_CHIP.fill,
    text: EDGE_CHIP.text,
    stroke: EDGE_CHIP.stroke,
    radius: EDGE_CHIP.radius,
  },
  layout: {
    spread: 1,
    // null → keep GraphView's node-count heuristic (byte-identical default).
    charge: null,
    linkDistance: null,
    // Matches the value GraphView passes to computeLayout today.
    collidePadding: 14,
    // Matches computeLayout's own default seed.
    seed: 1,
  },
  density: {
    edgeLabelLimit: 60,
    hubDegree: 5,
  },
};

// ---------------------------------------------------------------------------
// Validation spec — drives clamping / type-checking generically.
// ---------------------------------------------------------------------------

type FieldSpec =
  | { kind: 'num'; min: number; max: number; int?: boolean; nullable?: boolean }
  | { kind: 'bool' }
  | { kind: 'hex' }
  | { kind: 'enum'; values: readonly string[] };

/** Schema for every known param, by group → key. Anything not here is dropped. */
const SCHEMA: Record<string, Record<string, FieldSpec>> = {
  legend: {
    show: { kind: 'bool' },
    position: {
      kind: 'enum',
      values: ['top-left', 'top-right', 'bottom-left', 'bottom-right'],
    },
  },
  opacity: {
    rest: { kind: 'num', min: 0, max: 1 },
    active: { kind: 'num', min: 0, max: 1 },
    faded: { kind: 'num', min: 0, max: 1 },
    edgeRest: { kind: 'num', min: 0, max: 1 },
    edgeDimmed: { kind: 'num', min: 0, max: 1 },
  },
  color: {
    saturation: { kind: 'num', min: 0, max: 2 },
    brightness: { kind: 'num', min: 0, max: 2 },
    contrast: { kind: 'num', min: 0, max: 2 },
  },
  nodes: {
    radiusScale: { kind: 'num', min: 0.5, max: 2 },
    activeRing: { kind: 'hex' },
  },
  edges: {
    width: { kind: 'num', min: 0.1, max: 20 },
    widthActive: { kind: 'num', min: 0.1, max: 20 },
    rest: { kind: 'hex' },
    active: { kind: 'hex' },
    arrowScale: { kind: 'num', min: 0, max: 6 },
    endGap: { kind: 'num', min: 0, max: 100 },
    widthByWeight: { kind: 'bool' },
  },
  labels: {
    showNodes: { kind: 'bool' },
    showEdges: { kind: 'bool' },
    nodeFontSize: { kind: 'num', min: 1, max: 80 },
    edgeFontSize: { kind: 'num', min: 1, max: 80 },
    color: { kind: 'hex' },
    // raise to keep long labels intact (e.g. an agenda graph); 200 ≈ "no clip".
    maxChars: { kind: 'num', min: 1, max: 200, int: true },
    edgeMaxChars: { kind: 'num', min: 1, max: 200, int: true },
  },
  glow: {
    mode: { kind: 'enum', values: ['svg', 'filter'] },
    stdDeviation: { kind: 'num', min: 0, max: 40 },
    color: { kind: 'hex' },
    opacity: { kind: 'num', min: 0, max: 1 },
  },
  chip: {
    fill: { kind: 'hex' },
    text: { kind: 'hex' },
    stroke: { kind: 'hex' },
    radius: { kind: 'num', min: 0, max: 24 },
  },
  layout: {
    spread: { kind: 'num', min: 0.5, max: 2 },
    charge: { kind: 'num', min: -100000, max: 0, nullable: true },
    linkDistance: { kind: 'num', min: 1, max: 4000, nullable: true },
    collidePadding: { kind: 'num', min: 0, max: 200 },
    seed: { kind: 'num', min: 0, max: 2 ** 31, int: true },
  },
  density: {
    edgeLabelLimit: { kind: 'num', min: 0, max: 100000, int: true },
    hubDegree: { kind: 'num', min: 1, max: 100000, int: true },
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Dev-only warning. Silent in production builds (and in non-Vite contexts). */
function devWarn(msg: string): void {
  try {
    // import.meta.env is defined under Vite/Vitest; optional-chain everywhere
    // so plain Node never throws on it.
    const env = (import.meta as unknown as { env?: { DEV?: boolean } }).env;
    if (env?.DEV) console.warn(`[graph-params] ${msg}`);
  } catch {
    /* no import.meta.env here — stay silent */
  }
}

const HEX_RE = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/;

function clampNum(v: number, spec: Extract<FieldSpec, { kind: 'num' }>): number {
  let n = v;
  if (spec.int) n = Math.round(n);
  return Math.min(spec.max, Math.max(spec.min, n));
}

/**
 * Validate one raw value against its spec. Returns the cleaned value, or
 * `undefined` to mean "ignore this override and keep what's already resolved".
 */
function clean(
  group: string,
  key: string,
  raw: unknown,
  spec: FieldSpec,
): unknown {
  switch (spec.kind) {
    case 'bool':
      if (typeof raw === 'boolean') return raw;
      break;
    case 'hex':
      if (typeof raw === 'string' && HEX_RE.test(raw)) return raw;
      break;
    case 'enum':
      if (typeof raw === 'string' && spec.values.includes(raw)) return raw;
      break;
    case 'num':
      if (raw === null && spec.nullable) return null;
      if (typeof raw === 'number' && Number.isFinite(raw)) {
        return clampNum(raw, spec);
      }
      break;
  }
  devWarn(`ignoring invalid value for ${group}.${key}: ${JSON.stringify(raw)}`);
  return undefined;
}

/** Structured-clone-free deep copy of the (plain-data) resolved theme. */
function cloneResolved(t: ResolvedTheme): ResolvedTheme {
  return JSON.parse(JSON.stringify(t)) as ResolvedTheme;
}

// ---------------------------------------------------------------------------
// The one merge.
// ---------------------------------------------------------------------------

/**
 * Merge any number of param layers over the defaults, left-to-right (later
 * wins). Every value is validated/clamped on the way in; unknown groups/keys
 * are dropped with a dev-warning. Never throws.
 *
 *   resolveParams(DEFAULT_PARAMS, fixture.params, props.params, liveParams)
 */
export function resolveParams(
  ...layers: Array<GraphParams | ResolvedTheme | undefined | null>
): ResolvedTheme {
  // Start from a clone of the first layer if it's already a full theme
  // (the canonical call passes DEFAULT_PARAMS first), else from DEFAULT_PARAMS.
  const out = cloneResolved(DEFAULT_PARAMS);

  for (const layer of layers) {
    if (!layer || typeof layer !== 'object') continue;
    for (const [group, fields] of Object.entries(layer)) {
      const groupSpec = SCHEMA[group];
      const groupOut = (out as unknown as Record<string, Record<string, unknown>>)[
        group
      ];
      if (!groupSpec || !groupOut) {
        // The DEFAULT_PARAMS layer is itself a ResolvedTheme with all known
        // groups, so this only fires for genuinely unknown groups.
        if (group in DEFAULT_PARAMS) continue;
        devWarn(`ignoring unknown param group "${group}"`);
        continue;
      }
      if (!fields || typeof fields !== 'object') continue;
      for (const [key, raw] of Object.entries(fields)) {
        const fieldSpec = groupSpec[key];
        if (!fieldSpec) {
          devWarn(`ignoring unknown param "${group}.${key}"`);
          continue;
        }
        const cleaned = clean(group, key, raw, fieldSpec);
        if (cleaned !== undefined) groupOut[key] = cleaned;
      }
    }
  }

  return out;
}

/**
 * Build a CSS `filter` string for the global colour post-effect, or `undefined`
 * when all three are at their no-op identity (so the default path emits NO
 * filter attribute at all and stays byte-identical). Applied to the SVG element.
 */
export function cssColorFilter(rt: ResolvedTheme): string | undefined {
  const { saturation, brightness, contrast } = rt.color;
  if (saturation === 1 && brightness === 1 && contrast === 1) return undefined;
  return `saturate(${saturation}) brightness(${brightness}) contrast(${contrast})`;
}

/**
 * Diff a resolved theme (or merged params) against DEFAULT_PARAMS, returning a
 * minimal GraphParams with only the keys that actually changed. Used by the
 * configurator's "copy params" so the pasted block is small.
 */
export function paramsDelta(resolved: ResolvedTheme): GraphParams {
  const delta: Record<string, Record<string, unknown>> = {};
  const def = DEFAULT_PARAMS as unknown as Record<string, Record<string, unknown>>;
  const res = resolved as unknown as Record<string, Record<string, unknown>>;
  for (const group of Object.keys(def)) {
    for (const key of Object.keys(def[group])) {
      if (res[group]?.[key] !== def[group][key]) {
        (delta[group] ??= {})[key] = res[group][key];
      }
    }
  }
  return delta as GraphParams;
}
