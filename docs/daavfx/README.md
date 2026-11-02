# docs/daavfx - official documentation for the abeliant fork

This folder is the single source of truth for everything the DAAVFX agents
added to `llama.cpp-abelianIUT`. Upstream llama.cpp documentation stays in
`docs/` and is not duplicated here.

Date: 2026-11-01
Fork HEAD: `83f03cd10` (daavfx branch, 2026-10-31). `origin/daavfx` sits at
`eca00f9f9`, so this branch is 8 commits ahead and unpushed.
Flint worktree: upstream `36cbf41` merged and COMMITTED; binary built
(build 11832, commit `f92d149db`) and smoke-verified. The LFM3 merge
(120 upstream commits) is COMMITTED (`0882f7c09`) and rebuilt: build 11833
carries the lfm3 arch (`src/models/lfm3.cpp`, unity-batched in the llama
target). Speed candidate measured, see `break1650\LFM3-CANDIDATE.md`.

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
| app-lane/ | The transport + UI lanes: wire bin, agent UI fixes, audit status |
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
| Flint merge (36cbf41) | `..\..\..\llama.cpp-flint-wt` | committed, zero conflicts |
| Flint build script | `scripts\daavfx\build-flint-llama.ps1` | run, fixed, verified (build 11832) |
| Flint quant fetch | `scripts\daavfx\fetch-flint-gguf.ps1` | run, verified (Q2_K_XL 12.63 GB, Q3_K_XL 17.22 GB) |
| Flint quant sweep | `scripts\daavfx\flint-quant-sweep.ps1` | run; Q2 9/12 + Q3 5/12 quality (timeout-confounded); cards written |
| LFM3 candidate | `local_llm\GGUF\llm-collection\29-lfm3-1.7b\` + gguf-play registry | downloaded (0.98 GB Q4_0) + registered; merge committed `0882f7c09`, built 11833; quality 7/12; E0 57.5 t/s decode (3x the 18.9 split record); MT5 agent worker-tier (probe launches the backtest; full run held at turn 19). Card: `break1650\LFM3-CANDIDATE.md` |
| Bench driver v1.3.1 | `...\backtesting_pipeline\llm_bench\tools\bench_driver.ps1` | run 35+ benches; harness fixes landed (health-wait 600 s, LlamaServer param honored, leash moved to loop top); v1.3.1 fixed the -UseOpenAITools crash (ExtractActions List unroll -> -NoEnumerate) |
| Cascade calibration | `break1650\CASCADE-GATE-CALIBRATION.md` | paper rung: the 0.5B-first cascade is dead for the agent lane on our own cards; LFM3 collapses its premise |
| Router logger EXP-1 | worktree + main `src\daavfx_dspark_bridge.cpp` | provenance manifest + validator (self-test PASS) |
| Scoreboard + truth log | `llm_bench\SCOREBOARD.md`, `auditor-ISAYY\batch1\01b-trigger-compiler.md` | 5.9x prefill monster = usage-reporting artifact; thinking tax 77-79% is the top cost |
| Harness repo | `shared\daavile_harness\daavilefx_harness` | main at `9139563f` (seal fix + context step12 merged, lossless) |

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
