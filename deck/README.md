# deck — the Slidev deck

The talk itself: structure, content, and the spoken script (in each slide's `<!-- … -->`
speaker-note block). One deck, one entry point: `slides.md`.

## View it

```bash
npm install
npm run dev        # opens the deck; press `p` for presenter view (speaker notes)
```

## Build a static copy

```bash
npm run build      # → deck/dist/  (a self-contained static site)
```

The `build` script sets `--base /talk-packs-graph-basics/` for GitHub Pages project-page hosting.
If you host at a domain root instead, drop that flag.

## How the graphs are rendered

Every graph in the deck is drawn live by the `<GraphView>` Vue component
(`components/GraphView.vue`) from a NetworkX `node_link_data` JSON **fixture** in
`snippets/graph-fixtures/`. Theming (colour-by-kind, glow, click-reveals) is controlled in one
place — `components/graph-theme.ts` — and animates with Slidev's `$clicks`. A slide imports a
fixture and mounts `<GraphView :graph="…" />`.

To regenerate or add a fixture: build the graph in a demo notebook, export it with
`networkx.node_link_data(g, edges="links")`, and drop the JSON into `snippets/graph-fixtures/`
(Slidev only imports JSON from inside its own tree).

> `components/GraphConfigurator.vue` + `composables/useGraphEditMode.ts` are a **dev-only** graph
> editor, gated on `import.meta.env.DEV` and tree-shaken out of the production build.
