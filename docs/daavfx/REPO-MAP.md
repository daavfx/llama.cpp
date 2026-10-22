# REPO-MAP - ours vs upstream

Date: 2026-10-22
Fork root: `F:\DAAVILE_ECOSYSTEM\trading_ecosystem_11\trading_ecosystem_9.0\shared\llama.cpp-abelianIUT`
Origin: `https://github.com/daavfx/llama.cpp.git` (private)
Upstream: local clone `..\llama.cpp-original`, master `36cbf41`
Branch: `daavfx`, HEAD `43011a618` (2026-10-15)
Flint worktree: `..\llama.cpp-flint-wt`, branch `mod/flint-support`, merge staged, NOT committed

## The short answer

Everything under `src/` except the six `daavfx_*` files and two touchpoints is
upstream llama.cpp. Everything under `docs/daavfx/`, `scripts/daavfx/`,
`daavfx_helpers/`, `INFLIGHT.md`, `DAAVFX.md`, `patches/P1_fold_hsum.patch`,
the mutant GGUFs, and `_archive-2026-10-13/` is ours. The build trees and
junctions are local artifacts, not source.

## 1. Source changes in `src/` (ours)

| File | Kind | What it does |
|---|---|---|
| `src/daavfx_dspark_bridge.cpp` / `.h` | ours, tracked | Tap install, sched eval callback, SHM publisher, router histogram logger |
| `src/daavfx_per_layer_hooks.c` / `.h` | ours, tracked | Capture ring, timing stats, hook scaffolding, wire struct |
| `src/daavfx_theater_dispatch.c` / `.h` | ours, tracked | Seqlock + SHM dispatch snapshot (dormant) |
| `src/llama-context.cpp` | ours, touchpoint | Include + env-gated tap install (small) |
| `src/CMakeLists.txt` | ours, touchpoint | Adds the three overlay sources |
| `src/llama-moe-cache.cpp` | upstream + ours | Upstream SLRU cache plus our reuse telemetry and rejected ring eviction |
| All other `src/*` | upstream | llama.cpp model, graph, vocab, KV, quant code |

Uncommitted right now in the main tree: `src/daavfx_dspark_bridge.cpp` (+116)
and `src/llama-moe-cache.cpp` (+73). Everything else in `src/` is clean.

## 2. Docs (ours)

| Path | Tracking | What it is |
|---|---|---|
| `docs/daavfx/README.md` | new | Front door for this folder |
| `docs/daavfx/REPO-MAP.md` | new | This file |
| `docs/daavfx/FLINT-UPSTREAM.md` | new | Flint merge and pipeline |
| `docs/daavfx/TRACK-B-DISTILLATION.md` | new | Teacher-to-student plan |
| `docs/daavfx/moe-lab/FLINT-CAMPAIGN.md` | new | Next-model campaign plan |
| `docs/daavfx/BENCH.md` | tracked | PPL identity, tap cost, speed rows |
| `docs/daavfx/WIRE.md` | tracked | `daavfx_dspark` SHM contract |
| `docs/daavfx/DAVFX-BUILD.md` | tracked | CPU/MSVC build recipe |
| `docs/daavfx/overlay-vs-upstream.patch` | tracked | Full delta vs old base `edd6e2b` |
| `docs/daavfx/moe-lab/README.md` | untracked | LFM campaign index |
| `docs/daavfx/moe-lab/RESULTS.md` | untracked | Production configs, thesis, falsification ledger, X-ray kit |
| `docs/daavfx/moe-lab/FORK-CHANGES.md` | untracked | Manifest of campaign changes |
| `docs/daavfx/moe-lab/GTX1650-LFM25-CAMPAIGN.md` | untracked | Master plan and measured phase state |
| `docs/daavfx/moe-lab/FOUNDRY.md` | untracked | Destructive arm F1-F6, cliff maps |
| `docs/daavfx/moe-lab/LIVING-KERNEL-DESIGN.md` | untracked | Closed control-plane design |
| `docs/daavfx/moe-lab/CPU-MISS-FALLBACK-DESIGN.md` | untracked | Per-layer cache policy and its falsifier |
| `docs/daavfx/moe-lab/TYPED-DECISIONS.md` | untracked | Jev/JEPA/embedding research |

## 3. Tooling (ours, untracked)

| Path | What it is |
|---|---|
| `scripts/daavfx/launch-llm.ps1` | One-command launcher for the two LFM production modes; `-Stop` hygiene |
| `scripts/daavfx/phase1-bench-matrix.ps1` | Go-gated bench matrix with VRAM sampler and manifest |
| `scripts/daavfx/gguf-surgeon.py` | GGUF v3 codec, inspect, roundtrip, amputate, merge, ghost |
| `scripts/daavfx/quality-harness/` | 12-task agentic judge: `taskset.json`, `run-harness.ps1`, `score.py` |
| `scripts/daavfx/results/` | Phase 1/3a/3b logs, VRAM CSVs, manifests, harness scores |
| `scripts/daavfx/build-flint-llama.ps1` | NEW, not run: build the merged fork |
| `scripts/daavfx/fetch-flint-gguf.ps1` | NEW, not run: resolve and download one quant |
| `scripts/daavfx/run-flint-bench.ps1` | NEW, not run: MT5 bench wrapper for Flint |
| `scripts/daavfx/flint-quant-sweep.ps1` | NEW, not run: quality plus MT5 sweep |
| `scripts/daavfx/README.md` | Tooling index; the four Flint scripts exist in both trees |

Note on size: `FORK-CHANGES.md` says the campaign's results and mutants total
about 23 GB. The text/jsonl results are small; the gigabytes are the mutant
GGUFs kept as the record (root of the fork and `F:\llvb`).

## 4. Root-level files (ours)

| Path | What it is |
|---|---|
| `DAAVFX.md` | Fork README: overlay description and layout |
| `INFLIGHT.md` | Work ledger, 28 campaign rows and counting |
| `patches/P1_fold_hsum.patch` | PTQ1_0 ternary `vec_dot` micro-optimization |
| `asm_preload.cmake` | Local assembly preload helper (untracked) |
| `daavfx_helpers/` | PE/debug/diff helpers: `check_asm.cmd`, `compare_sections.ps1`, `debug_pe.ps1`, `debug2.ps1`, `diff_cmake.ps1`, `pe_info.ps1`, `pe_sections.ps1`, `README.md` |
| `_archive-2026-10-13/` | 524 MB archive of earlier work, untracked, NOT copied to the worktree |
| `armA-K24-amputated-q4km.gguf` | Mutant record (large) |
| `armB-K24-ghosted-q4km.gguf` | Mutant record (large) |
| `mutant-K16.gguf` | Mutant record (large) |
| `mutant-K16-guided.gguf` | Mutant record (large) |
| `mutant-K16-multighost-q4km.gguf` | Mutant record (large) |
| `mutant-K24-guided.gguf` | Mutant record (large) |
| `mutant-K28-guided.gguf` | Mutant record (large) |

`app/` and `vendor/` are upstream llama.cpp trees, not ours.

## 5. Build trees and junctions (local, not source)

| Path | What it is | Flint-capable |
|---|---|---|
| `build_vulkan_bin/` | Current `llama-server.exe`, build 11671, commit `43011a618` | NO |
| `build_vulkan_bench/` | Campaign build with bench/quantize/server | NO |
| `build_cpu_mod/` | Older CPU build | NO |
| `..\llama.cpp-flint-wt\build_flint\` | Planned merged build (script ready) | YES, after build |
| `F:\llvb` | Junction to the fork root, needed for MAX_PATH | n/a |
| `F:\llvb_flint` | Junction to the Flint worktree, planned | n/a |
| `F:\qapp` | Quantum app cargo junction, unrelated | n/a |

## 6. Git state

- `daavfx`: one local branch, HEAD `43011a618`; no commit for the campaign.
- `upstream/master`: `36cbf41` (2026-10-22), 155 commits ahead of daavfx.
- Worktree `mod/flint-support`: merge done with zero conflicts, still in merge
  state ("All conflicts fixed but you are still merging"), no commit.
- Worktree carries the overlay copy: `docs/daavfx/` (all), `scripts/daavfx/`,
  `daavfx_helpers/`, `INFLIGHT.md`, `asm_preload.cmake`, the dspark bridge
  patch, and the moe-cache telemetry port.
- Not copied to the worktree: `_archive-2026-10-13/` (524 MB) and the root
  mutant GGUFs. They stay in the main tree as the record.

## 7. What is NOT ours

Everything in `ggml/`, `common/`, `conversion/`, `examples/`, `tools/`,
`tests/`, `models/`, `include/`, `gguf-py/`, `grammars/`, `vendor/`, `app/`,
`ci/`, `cmake/`, and the upstream docs under `docs/` (except `docs/daavfx/`).
Also: `AGENTS.md`, `CLAUDE.md`, `README.md`, `CONTRIBUTING.md`, `LICENSE`.
