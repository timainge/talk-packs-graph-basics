import { defineShikiSetup } from '@slidev/types'

/**
 * Code highlighting theme.
 *
 * `one-dark-pro` is the Shiki bundle of the One Dark Pro VS Code theme, so
 * code fences in the slides match the editor + Jupyter notebooks 1:1.
 *
 * Both keys are set to the same theme on purpose — the deck runs dark-only
 * (`colorSchema: dark` in slides.md), so there's no separate light variant to
 * worry about.
 */
export default defineShikiSetup(() => {
  return {
    themes: {
      dark: 'one-dark-pro',
      light: 'one-dark-pro',
    },
  }
})
