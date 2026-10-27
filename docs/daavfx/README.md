# docs/daavfx - official documentation for the abeliant fork

This folder is the single source of truth for everything the DAAVFX agents
added to `llama.cpp-abelianIUT`. Upstream llama.cpp documentation stays in
`docs/` and is not duplicated here.

Date: 2026-10-22
Fork HEAD: `43011a618` (daavfx branch)
Upstream synced to: `36cbf41` (2026-10-22, Flint support included)
State: Flint merge prepared in a worktree, NOT committed. No build, no
download, no benchmark was run for this documentation pass.

## Break-the-1650 program

`break1650/` - the self-contained plan folder for the GTX 1650 program
(loading redesign, thinking-token economics, concurrent expert split, dGPU
kernels). It is written to stand alone for an outside auditor: context,
measured facts, trust ledger, full plan, experiments, prior runs, and
correlated lanes. Start at `break1650/README.md`.

The acceptance bench and its scorecards live in
`F:\DAAVILE_ECOSYSTEM\trading_ecosystem_11\trading_ecosystem_9.0\main_ecosystem_trading\backtesting_pipeline\llm_bench\README.md`.

## Read in this order

1. `REPO-MAP.md` - what is ours, what is upstream, where every artifact lives.
2. `plans/README.md` - the design lanes (one index, one primitive table).
3. `plans/context/` - the context/compaction reinvention (the newest plan).
4. `plans/vault/` - the agent backend: isolation, per-surface vaults, the human section.
5. `plans/loop/` - the harness self-improvement loop (onboarding, the Lane-A contract).
6. `moe-lab/FLINT-UPSTREAM.md` - Flint facts, the merge, the build and bench pipeline.
7. `break1650/README.md` - the GTX 1650 program (self-contained plan folder).
8. `moe-lab/README.md` - the completed LFM campaign (results, falsified ideas).
9. `moe-lab/FLINT-CAMPAIGN.md` - the plan for the next model.
10. `TRACK-B-DISTILLATION.md` - teacher-to-student plan for a small local agent.
11. `app-lane/` - the transport + UI lanes (wire bin, agent UI fixes, audit status).
12. `skills/novel/` - the RAG chunk library (used by the audit lanes).
13. `overlay/WIRE.md`, `overlay/BENCH.md`, `overlay/DAVFX-BUILD.md` - the existing overlay contract.
14. `experimental-dgpu/` - the dGPU kernel experiments.

Absent from this index means the folder does not exist as a lane; the
`auditor-ISAYY/` and `auditor-MAX10/` records are audit runs over the plans,
not lanes.

## Layout

| Path | What it holds |
|---|---|
| `overlay/` | What the fork adds and how it is built: `WIRE.md`, `BENCH.md`, `DAVFX-BUILD.md`, `overlay-vs-upstream.patch` |
| `REPO-MAP.md` | Complete ours-vs-upstream inventory |
| `moe-lab/` | LFM campaign record, the Flint campaign plan, and `FLINT-UPSTREAM.md` (Flint merge state and usage contract) |
| `break1650/` | The GTX 1650 program: self-contained plan folder for an outside auditor |
| `plans/` | The design lanes; one index, one primitive table (PRIMITIVES.md) |
| pp-lane/ | The transport + UI lanes: wire bin, agent UI fixes, audit status |
| experimental-dgpu/ | The dGPU kernel experiments |
| `TRACK-B-DISTILLATION.md` | Distillation plan for a small local tool agent (dormant until a dual-axis winner) |

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
