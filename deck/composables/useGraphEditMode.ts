/**
 * useGraphEditMode.ts
 * -------------------
 * A tiny shared toggle for the GraphView configurator ("editing mode").
 *
 * Two gates decide whether the configurator is ever reachable (see plan §9a):
 *
 *   1. DEV-ONLY (the hard gate). `import.meta.env.DEV` is true under the Slidev
 *      dev server and the viz harness, and FALSE under `slidev build`. So the
 *      panel — and its "copy params" affordance — can never ship in the
 *      deployed deck or appear in a screenshot build. `editModeAvailable`
 *      reflects this; in prod it is permanently false.
 *   2. RUNTIME TOGGLE (so it's not always on in dev). A module-level ref flipped
 *      by Shift+G or a `?edit=1` query param. All GraphView instances share it.
 *
 * Module-level state + a once-only listener mean every <GraphView> reacts to the
 * same toggle without prop-drilling or a Slidev presenter-mode dependency.
 */
import { readonly, ref } from 'vue';

/** True only in a dev build — the hard gate. Constant for the session. */
export const editModeAvailable: boolean = (() => {
  try {
    return Boolean(
      (import.meta as unknown as { env?: { DEV?: boolean } }).env?.DEV,
    );
  } catch {
    return false;
  }
})();

/** Shared, reactive edit-mode flag (module singleton). */
const _editMode = ref(false);

let wired = false;

/** Wire the keyboard + query-param toggles exactly once (browser only). */
function ensureWired(): void {
  if (wired || typeof window === 'undefined' || !editModeAvailable) return;
  wired = true;

  // ?edit=1 opens straight into edit mode.
  try {
    if (new URLSearchParams(window.location.search).get('edit') === '1') {
      _editMode.value = true;
    }
  } catch {
    /* no location — ignore */
  }

  // Shift+G toggles. Ignore when typing into an input/textarea.
  window.addEventListener('keydown', (e: KeyboardEvent) => {
    const t = e.target as HTMLElement | null;
    const tag = t?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || t?.isContentEditable) return;
    if (e.shiftKey && (e.key === 'G' || e.key === 'g')) {
      _editMode.value = !_editMode.value;
    }
  });
}

/**
 * Access the shared edit-mode toggle.
 *   const { editMode, toggle, available } = useGraphEditMode();
 */
export function useGraphEditMode() {
  ensureWired();
  return {
    /** Readonly reactive flag — true when the configurator should be offered. */
    editMode: readonly(_editMode),
    /** Whether edit mode is reachable at all (dev only). */
    available: editModeAvailable,
    /** Programmatic toggle (e.g. a close button). */
    toggle(): void {
      if (editModeAvailable) _editMode.value = !_editMode.value;
    },
    set(v: boolean): void {
      if (editModeAvailable) _editMode.value = v;
    },
  };
}
