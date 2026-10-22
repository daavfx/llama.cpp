# docs/daavfx - official documentation for the abeliant fork

This folder is the single source of truth for everything the DAAVFX agents
added to `llama.cpp-abelianIUT`. Upstream llama.cpp documentation stays in
`docs/` and is not duplicated here.

Date: 2026-10-22
Fork HEAD: `43011a618` (daavfx branch)
Upstream synced to: `36cbf41` (2026-10-22, Flint support included)
State: Flint merge prepared in a worktree, NOT committed. No build, no
download, no benchmark was run for this documentation pass.

The acceptance bench and its scorecards live in
`F:\DAAVILE_ECOSYSTEM\trading_ecosystem_11\trading_ecosystem_9.0\main_ecosystem_trading\backtesting_pipeline\llm_bench\README.md`.

## Read in this order

1. `REPO-MAP.md` - what is ours, what is upstream, where every artifact lives.
2. `FLINT-UPSTREAM.md` - Flint facts, the merge, the build and bench pipeline.
3. `moe-lab/README.md` - the completed LFM campaign (results, falsified ideas).
4. `moe-lab/FLINT-CAMPAIGN.md` - the plan for the next model (not started).
5. `TRACK-B-DISTILLATION.md` - teacher-to-student plan for a small local agent.
6. `WIRE.md`, `BENCH.md`, `DAVFX-BUILD.md` - the existing overlay contract.

## Layout

| Path | What it holds |
|---|---|
| `BENCH.md` | Measured overlay numbers: PPL identity, tap cost, speed rows |
| `WIRE.md` | `daavfx_dspark` shared-memory layout and seqlock protocol |
| `DAVFX-BUILD.md` | Original CPU build recipe for the overlay |
| `overlay-vs-upstream.patch` | The tracked overlay patch against the old base |
| `REPO-MAP.md` | Complete ours-vs-upstream inventory |
| `FLINT-UPSTREAM.md` | Flint merge state and usage contract |
| `moe-lab/` | LFM campaign record plus the Flint campaign plan |
| `TRACK-B-DISTILLATION.md` | Distillation plan for a small local tool agent |

## Hard rules

- No commit and no push without explicit human approval for that action.
- Private fork: the upstream contribution rules are exempt, but the commit
  hygiene still applies (`Assisted-by:` when approved, never `Co-authored-by:`).
- ASCII only in code and docs. No emdash, no unicode arrows.
- Every change gets an `INFLIGHT.md` row while it is in flight.
- Build and bench only when the operator says the machine is free.

## Current artifacts

| Artifact | Path | Status |
|---|---|---|
| Flint merge worktree | `..\..\..\llama.cpp-flint-wt` | uncommitted, zero conflicts |
| Flint build script | `scripts\daavfx\build-flint-llama.ps1` | written, not run |
| Flint quant fetch | `scripts\daavfx\fetch-flint-gguf.ps1` | written, not run |
| Flint MT5 bench | `scripts\daavfx\run-flint-bench.ps1` | written, not run |
| Flint quant sweep | `scripts\daavfx\flint-quant-sweep.ps1` | written, not run |
| Harness v1.3 | `...\backtesting_pipeline\llm_bench\tools\bench_driver.ps1` | written, parse-checked |
| Bench index | `...\backtesting_pipeline\llm_bench\README.md` | layout, standings, task spec |
| moe-cache telemetry | worktree `src\llama-moe-cache.cpp` | ported to upstream SLRU, not compiled |

## Commands (documented only, do not run yet)

All commands below run from the fork root. The same four scripts exist in
`scripts\daavfx\` in the main tree and in the Flint worktree; the worktree is
where `build_flint` is produced.

```powershell
# build the merged fork (CPU + Vulkan)
.\scripts\daavfx\build-flint-llama.ps1

# list, then download one quant
.\scripts\daavfx\fetch-flint-gguf.ps1 -Quant Q3_K_XL -List
.\scripts\daavfx\fetch-flint-gguf.ps1 -Quant Q3_K_XL

# one MT5 agent run
.\scripts\daavfx\run-flint-bench.ps1 -Quant Q3_K_XL

# quality harness plus MT5 bench for a quant list
.\scripts\daavfx\flint-quant-sweep.ps1 -Quants Q2_K_XL,IQ3_XXS,Q3_K_XL
```

## Position on the model

One modded llama.cpp must serve every local need. Flint is merged into this
fork, not kept as a separate upstream clone. The merged binary keeps the
`daavfx` tap bridge and the MoE cache telemetry, and adds Flint inference.
