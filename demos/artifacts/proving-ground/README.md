# proving-ground artifacts — the *cheaper / smarter* anchor

These are **exported results** committed so the *cheaper* beat can be toured with real numbers.
Nothing here runs live.

- `cost_collapse.json` — the grep-vs-graph localization table (per task: repo, arm, hit, tool-uses,
  tokens), bench-loadable via
  `graphtools.bench.load_benchmark('cost_collapse', source='proving-ground')`.
- `cost_collapse.png` — bar chart of tool-uses per task (grep vs graph), annotated "accuracy parity".
- `make_cost_collapse.py` — deterministic generator: reads the JSON, writes the PNG. Run with
  `cd demos && uv run python artifacts/proving-ground/make_cost_collapse.py`.

## The honest through-line

**Accuracy parity with grep, but navigation COST collapses.** On descriptively-named .NET code grep
is a strong baseline and *both arms hit every task* — this is **not** "AI finds bugs grep can't". The
measured, defensible claim is efficiency: **compiler-precise navigation makes an agent meaningfully
cheaper to run on big code**, and the saving grows with codebase size. Cross-project localization on
a large PowerShell repo: grep wandered **16** tool-uses across 1337 files; the graph agent jumped via
the index in **4** — same answer.

Don't overclaim. The lift is *efficiency that scales with size* (plus a few things grep structurally
can't do: DI-wiring disambiguation, exact callers), not a higher hit-rate.

## Headline numbers (transcribed into `cost_collapse.json`)

| Number | Value |
|---|---|
| eShop — mean tool-use reduction | ~45% (accuracy 1.0 both arms, n=2 tasks) |
| PowerShell — cross-project (P1) | grep 16 → graph 4 tool-uses; 59k → 47k tokens (both hit) |
| PowerShell — mean tool-use reduction | ~68% (accuracy parity) |
| Downstream reliability (sonnet-4-6) | claim error 0.078 → 0.005 with graph navigation |

## Bounds / caveats to carry to the slide

- The samples are tiny (eShop n=2, PowerShell n=2 tasks) — this is a *measured PoC of the mechanism
  and direction*, not a population estimate. State n on the slide.
- The downstream-reliability number (0.078 → 0.005) is **decisive on sonnet-4-6** on a small set of
  tuning subjects; **no lift on opus-4-7**. Don't present it as a universal model result.
- PowerShell uses a **build-free syntactic** index (runs where the compiler can't load the repo);
  eShop uses a compiled (Roslyn) index.

## Verify before slide

Every figure above is transcribed from the committed `cost_collapse.json`. Before any talk run,
re-confirm each number still matches the JSON; if you regenerate the data, re-run
`make_cost_collapse.py`. The committed exports are presentation-ready — no pipeline code ships here.
