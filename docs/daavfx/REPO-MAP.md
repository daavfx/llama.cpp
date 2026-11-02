# REPO-MAP - ours vs upstream

Date: 2026-11-01
Fork root: `F:\DAAVILE_ECOSYSTEM\trading_ecosystem_11\trading_ecosystem_9.0\shared\llama.cpp-abelianIUT`
Origin: `https://github.com/daavfx/llama.cpp.git` (private)
Upstream: local clone `..\llama.cpp-original`, master `36cbf41`
Branch: `daavfx`, HEAD `83f03cd10` (2026-10-31); `origin/daavfx` is at
`eca00f9f9`, so this branch is 8 commits ahead and unpushed.
Flint worktree: `..\llama.cpp-flint-wt`, branch `mod/flint-support`, merge
COMMITTED `0882f7c09` (2026-10-28, "merge upstream LFM3 support (120 commits)").

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
| `docs/daavfx/moe-lab/FLINT-UPSTREAM.md` | new | Flint merge and pipeline |
| `docs/daavfx/TRACK-B-DISTILLATION.md` | new | Teacher-to-student plan (dormant) |
| `docs/daavfx/moe-lab/FLINT-CAMPAIGN.md` | new | Next-model campaign plan |
| `docs/daavfx/overlay/BENCH.md` | tracked | PPL identity, tap cost, speed rows |
| `docs/daavfx/overlay/WIRE.md` | tracked | `daavfx_dspark` SHM contract |
| `docs/daavfx/overlay/DAVFX-BUILD.md` | tracked | CPU/MSVC build recipe |
| `docs/daavfx/overlay/overlay-vs-upstream.patch` | tracked | Full delta vs old base `edd6e2b` |
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
| `..\llama.cpp-flint-wt\build_flint\` | BUILT - build 11833 (commit `b2a60bb67`); `llama-server.exe` + `llama-cli.exe` present, rebuilt with the LFM3 merge | YES |
| `F:\llvb` | Junction to the fork root, needed for MAX_PATH | n/a |
| `F:\llvb_flint` | Junction to the Flint worktree, planned | n/a |
| `F:\qapp` | Quantum app cargo junction, unrelated | n/a |

## 6. Git state

- `daavfx`: HEAD `83f03cd10` (2026-10-31), 8 commits ahead of `origin/daavfx`
  (`eca00f9f9`), unpushed.
- `upstream/master`: `36cbf41` (2026-10-22), 155 commits ahead of daavfx.
- Worktree `mod/flint-support`: merge COMMITTED `0882f7c09` (2026-10-28);
  not in merge state. Two traps for anyone inspecting it: the worktree's
  `.git` gitfile points at `F:/DAAVILE_ECOSYSTEM/...`, so under WSL
  `git -C` on it fails and `git worktree list` reports it `prunable` - use
  `--git-dir`/`--work-tree` to read it. And `src/models/lfm3.cpp` +
  `src/models/flint.cpp` exist ONLY on this branch, not on `daavfx`.

  ## 6b. Why Flint is not on `daavfx` (measured 2026-11-01, operator call)

  Bringing the two source files onto `daavfx` is NOT a cherry-pick. The two
  branches have genuinely diverged from merge base `43011a618` (2026-10-15):

  | direction | commits |
  |---|---:|
  | `mod/flint-support` ahead of `daavfx` | 283 |
  | `daavfx` ahead of `mod/flint-support` | 17 |

  So a real merge (not a fast-forward) is required, it touches the whole
  tree, and the flint worktree is carrying **3,891 dirty files** against
  its own HEAD - essentially the tree renormalised for line endings, which
  is exactly the kind of change that either gets committed by accident or
  produces conflicts at scale. The audit mandate attached to this folder
  (auditor-ISAYY FINAL-REPORT, mandate 3) forbids reset/clean/worktree
  overwrite without an explicit operator instruction, and this operation is
  well inside that boundary.

  NOT DONE - left as an explicit decision. The two files are small
  (`src/models/lfm3.cpp` 197 lines, `src/models/flint.cpp` 194 lines) and
  content-stable against `0882f7c09`, so if the operator wants them on
  `daavfx` the cheap path is a path-scoped copy plus an INFLIGHT row, not a
  branch merge. Verification anchors if that path is taken:

  - `git show mod/flint-support:src/models/lfm3.cpp` (197 lines)
  - `git show mod/flint-support:src/models/flint.cpp` (194 lines)
  - worktree copies differ from the committed blobs (flint.cpp and lfm3.cpp
    were both edited after the merge), so copy from the *branch*, not the
    worktree, unless the newer working copy is wanted.

  Related, same decision class: `docs/daavfx/skills/novel/` is entirely
  UNTRACKED (0 files under git) though `README.md` and `plans/vault/` both
  cite it as a live lane. Its two agent descriptors also carried broken
  relative paths (`../../core` from `agents/` resolves to `skills/core`,
  which does not exist); corrected to `../core` in the working tree on
  2026-11-01. Whether the layer is committed is the operator's call.
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
