<script setup lang="ts">
/**
 * GraphConfigurator.vue — the in-place params tuner (stretch goal, plan §9).
 *
 * A floating, dev-only panel bound to ONE <GraphView> instance. Each control
 * writes into a live `overrides` object (v-model) that the host feeds to the
 * top of its param merge order, so edits re-render instantly. The only way
 * tweaks leave the session is the "Copy params" button — it emits the minimal
 * delta-from-defaults as a ready-to-paste `"params": { … }` block. No
 * write-back to files, no localStorage; reload discards everything.
 *
 * This component is pure UI: it reads the current ResolvedTheme to seed every
 * control's displayed value and emits override changes. It never touches the
 * fixture or the renderer directly.
 */
import { computed, ref } from 'vue';
import {
  DEFAULT_PARAMS,
  paramsDelta,
  type GraphParams,
  type ResolvedTheme,
} from './graph-params';

const props = defineProps<{
  /** Current merged theme (defaults ← fixture ← prop ← live) — seeds controls. */
  resolved: ResolvedTheme;
  /** The live override object this panel edits (v-model). */
  overrides: GraphParams;
}>();

const emit = defineEmits<{
  (e: 'update:overrides', v: GraphParams): void;
  (e: 'close'): void;
}>();

// --- Control catalogue: mirrors the param groups in graph-params §4 ----------
type Control =
  | { k: string; type: 'num'; min: number; max: number; step: number }
  | { k: string; type: 'numNullable'; min: number; max: number; step: number }
  | { k: string; type: 'bool' }
  | { k: string; type: 'color' }
  | { k: string; type: 'enum'; options: readonly string[] };

interface Group {
  key: string;
  label: string;
  controls: Control[];
}

const GROUPS: Group[] = [
  {
    key: 'legend',
    label: 'Legend',
    controls: [
      { k: 'show', type: 'bool' },
      {
        k: 'position',
        type: 'enum',
        options: ['top-left', 'top-right', 'bottom-left', 'bottom-right'],
      },
    ],
  },
  {
    key: 'color',
    label: 'Colour · global filter',
    controls: [
      { k: 'saturation', type: 'num', min: 0, max: 2, step: 0.05 },
      { k: 'brightness', type: 'num', min: 0, max: 2, step: 0.05 },
      { k: 'contrast', type: 'num', min: 0, max: 2, step: 0.05 },
    ],
  },
  {
    key: 'opacity',
    label: 'Opacity',
    controls: [
      { k: 'rest', type: 'num', min: 0, max: 1, step: 0.02 },
      { k: 'active', type: 'num', min: 0, max: 1, step: 0.02 },
      { k: 'faded', type: 'num', min: 0, max: 1, step: 0.02 },
      { k: 'edgeRest', type: 'num', min: 0, max: 1, step: 0.02 },
      { k: 'edgeDimmed', type: 'num', min: 0, max: 1, step: 0.02 },
    ],
  },
  {
    key: 'nodes',
    label: 'Nodes',
    controls: [
      { k: 'radiusScale', type: 'num', min: 0.5, max: 2, step: 0.05 },
      { k: 'activeRing', type: 'color' },
    ],
  },
  {
    key: 'edges',
    label: 'Edges',
    controls: [
      { k: 'width', type: 'num', min: 0.1, max: 20, step: 0.1 },
      { k: 'widthActive', type: 'num', min: 0.1, max: 20, step: 0.1 },
      { k: 'rest', type: 'color' },
      { k: 'active', type: 'color' },
    ],
  },
  {
    key: 'labels',
    label: 'Labels',
    controls: [
      { k: 'showNodes', type: 'bool' },
      { k: 'showEdges', type: 'bool' },
      { k: 'nodeFontSize', type: 'num', min: 1, max: 80, step: 1 },
      { k: 'edgeFontSize', type: 'num', min: 1, max: 80, step: 1 },
      { k: 'color', type: 'color' },
    ],
  },
  {
    key: 'glow',
    label: 'Glow',
    controls: [
      { k: 'mode', type: 'enum', options: ['svg', 'filter'] },
      { k: 'stdDeviation', type: 'num', min: 0, max: 40, step: 0.5 },
      { k: 'color', type: 'color' },
      { k: 'opacity', type: 'num', min: 0, max: 1, step: 0.02 },
    ],
  },
  {
    key: 'chip',
    label: 'Edge-label chip',
    controls: [
      { k: 'fill', type: 'color' },
      { k: 'text', type: 'color' },
      { k: 'stroke', type: 'color' },
      { k: 'radius', type: 'num', min: 0, max: 24, step: 1 },
    ],
  },
  {
    key: 'layout',
    label: 'Layout · re-runs sim',
    controls: [
      { k: 'spread', type: 'num', min: 0.5, max: 2, step: 0.05 },
      { k: 'collidePadding', type: 'num', min: 0, max: 200, step: 1 },
      { k: 'seed', type: 'num', min: 0, max: 99, step: 1 },
      { k: 'charge', type: 'numNullable', min: -5000, max: 0, step: 10 },
      { k: 'linkDistance', type: 'numNullable', min: 1, max: 600, step: 5 },
    ],
  },
  {
    key: 'density',
    label: 'Density',
    controls: [
      { k: 'edgeLabelLimit', type: 'num', min: 0, max: 500, step: 5 },
      { k: 'hubDegree', type: 'num', min: 1, max: 50, step: 1 },
    ],
  },
];

// --- Read/write helpers ------------------------------------------------------

/** Current displayed value for a control (live override → else resolved). */
function val(group: string, key: string): unknown {
  const res = props.resolved as unknown as Record<string, Record<string, unknown>>;
  return res[group]?.[key];
}

/** Immutably set one override key and emit the new object. */
function setVal(group: string, key: string, value: unknown): void {
  const next: Record<string, Record<string, unknown>> = JSON.parse(
    JSON.stringify(props.overrides ?? {}),
  );
  (next[group] ??= {})[key] = value;
  emit('update:overrides', next as GraphParams);
}

function onNum(group: string, key: string, e: Event): void {
  const v = Number((e.target as HTMLInputElement).value);
  if (Number.isFinite(v)) setVal(group, key, v);
}
function onNullable(group: string, key: string, e: Event): void {
  const raw = (e.target as HTMLInputElement).value;
  setVal(group, key, raw === '' ? null : Number(raw));
}
function onBool(group: string, key: string, e: Event): void {
  setVal(group, key, (e.target as HTMLInputElement).checked);
}
function onText(group: string, key: string, e: Event): void {
  setVal(group, key, (e.target as HTMLInputElement).value);
}

// --- Copy / reset ------------------------------------------------------------

const copied = ref(false);

/** The minimal `"params": { … }` block for the current look (delta vs defaults). */
const paramsBlock = computed(() => {
  const delta = paramsDelta(props.resolved);
  // Pretty-print as it would sit in the fixture JSON.
  const body = JSON.stringify({ params: delta }, null, 2);
  return body;
});

async function copyParams(): Promise<void> {
  const text = paramsBlock.value;
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    // Clipboard blocked (insecure context) — fall back to a prompt.
    window.prompt('Copy the params block:', text);
  }
  copied.value = true;
  window.setTimeout(() => (copied.value = false), 1200);
}

function reset(): void {
  emit('update:overrides', {});
}

/** Is this control currently overridden from the default? (for a dot marker) */
function isChanged(group: string, key: string): boolean {
  const def = DEFAULT_PARAMS as unknown as Record<string, Record<string, unknown>>;
  return val(group, key) !== def[group]?.[key];
}
</script>

<template>
  <div class="gconf" @keydown.stop>
    <header class="gconf-head">
      <span class="gconf-title">Graph params</span>
      <button class="gconf-x" title="Close (Shift+G)" @click="emit('close')">
        ×
      </button>
    </header>

    <div class="gconf-body">
      <section v-for="g in GROUPS" :key="g.key" class="gconf-group">
        <div class="gconf-group-label">{{ g.label }}</div>
        <div
          v-for="c in g.controls"
          :key="c.k"
          class="gconf-row"
        >
          <label class="gconf-key">
            <span class="gconf-dot" :class="{ on: isChanged(g.key, c.k) }" />
            {{ c.k }}
          </label>

          <!-- numeric slider -->
          <template v-if="c.type === 'num'">
            <input
              type="range"
              :min="c.min"
              :max="c.max"
              :step="c.step"
              :value="val(g.key, c.k) as number"
              @input="onNum(g.key, c.k, $event)"
            />
            <span class="gconf-val">{{ val(g.key, c.k) }}</span>
          </template>

          <!-- nullable number (auto = heuristic) -->
          <template v-else-if="c.type === 'numNullable'">
            <input
              type="number"
              :min="c.min"
              :max="c.max"
              :step="c.step"
              :placeholder="'auto'"
              :value="val(g.key, c.k) === null ? '' : (val(g.key, c.k) as number)"
              @input="onNullable(g.key, c.k, $event)"
            />
            <button
              class="gconf-auto"
              title="Reset to heuristic"
              @click="setVal(g.key, c.k, null)"
            >
              auto
            </button>
          </template>

          <!-- boolean -->
          <template v-else-if="c.type === 'bool'">
            <input
              type="checkbox"
              :checked="val(g.key, c.k) as boolean"
              @change="onBool(g.key, c.k, $event)"
            />
          </template>

          <!-- colour -->
          <template v-else-if="c.type === 'color'">
            <input
              type="color"
              :value="val(g.key, c.k) as string"
              @input="onText(g.key, c.k, $event)"
            />
            <span class="gconf-val">{{ val(g.key, c.k) }}</span>
          </template>

          <!-- enum -->
          <template v-else-if="c.type === 'enum'">
            <select
              :value="val(g.key, c.k) as string"
              @change="onText(g.key, c.k, $event)"
            >
              <option v-for="o in c.options" :key="o" :value="o">{{ o }}</option>
            </select>
          </template>
        </div>
      </section>
    </div>

    <footer class="gconf-foot">
      <button class="gconf-btn primary" @click="copyParams">
        {{ copied ? 'Copied ✓' : 'Copy params' }}
      </button>
      <button class="gconf-btn" @click="reset">Reset</button>
    </footer>
  </div>
</template>

<style scoped>
.gconf {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 50;
  width: 264px;
  max-height: calc(100% - 24px);
  display: flex;
  flex-direction: column;
  background: rgba(18, 20, 25, 0.94);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(6px);
  font-family: ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  font-size: 11px;
  color: #d7dbe0;
  pointer-events: auto;
}
.gconf-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.gconf-title {
  font-weight: 600;
  letter-spacing: 0.02em;
}
.gconf-x {
  background: none;
  border: none;
  color: #aeb3bb;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
}
.gconf-x:hover {
  color: #fff;
}
.gconf-body {
  overflow-y: auto;
  padding: 6px 10px;
}
.gconf-group {
  margin-bottom: 8px;
}
.gconf-group-label {
  text-transform: uppercase;
  font-size: 9px;
  letter-spacing: 0.08em;
  color: #8b909a;
  margin: 6px 0 3px;
}
.gconf-row {
  display: grid;
  grid-template-columns: 92px 1fr auto;
  align-items: center;
  gap: 6px;
  padding: 2px 0;
}
.gconf-key {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #c4c9d1;
  font-variant-numeric: tabular-nums;
}
.gconf-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: transparent;
  flex: 0 0 auto;
}
.gconf-dot.on {
  background: #6cc5b0;
}
.gconf-val {
  min-width: 30px;
  text-align: right;
  color: #9ea3ab;
  font-variant-numeric: tabular-nums;
}
.gconf-row input[type='range'] {
  width: 100%;
}
.gconf-row input[type='number'] {
  width: 100%;
  background: #1b1e24;
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #e8eaed;
  border-radius: 4px;
  padding: 1px 4px;
}
.gconf-row input[type='color'] {
  width: 28px;
  height: 18px;
  padding: 0;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 3px;
  background: none;
}
.gconf-row select {
  background: #1b1e24;
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #e8eaed;
  border-radius: 4px;
  padding: 1px 2px;
}
.gconf-auto {
  font-size: 9px;
  background: #262a31;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #aeb3bb;
  border-radius: 4px;
  padding: 1px 5px;
  cursor: pointer;
}
.gconf-foot {
  display: flex;
  gap: 8px;
  padding: 8px 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
.gconf-btn {
  flex: 1;
  background: #262a31;
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #d7dbe0;
  border-radius: 6px;
  padding: 5px 8px;
  cursor: pointer;
  font-size: 11px;
}
.gconf-btn:hover {
  background: #2e333b;
}
.gconf-btn.primary {
  background: #3a4658;
  border-color: #4a5a72;
  color: #eaf0f8;
}
.gconf-btn.primary:hover {
  background: #44526820;
  background: #455268;
}
</style>
