# FORK-CHANGES.md - what this campaign changed in the fork

Date: 2026-10-21, updated 2026-10-22 for the Flint merge
Owner: agent ID `lfm25-gtx1650-campaign`
Purpose: a future coder must be able to tell, at a glance, what is OURS and
what is upstream. Everything below is either a change we made to this fork or
an artifact we produced. Nothing here is committed (the fork's working tree
carries the changes; INFLIGHT.md is the ledger).

Scope note: sections 1-6 describe the MAIN TREE (`llama.cpp-abelianIUT`) as of
the LFM campaign. The Flint work happens in the sibling worktree
`..\llama.cpp-flint-wt`; section 7 records the differences. Do not copy the
main tree's `src/llama-moe-cache.cpp` over the worktree file.

## 1. C++ changes in the fork (src/)

### 1.1 src/daavfx_dspark_bridge.cpp - router histogram logger (NEW, env-gated)

Env: `DAAVFX_ROUTER_LOG=<csv path>` (independent of DAAVFX_DSPARK_TAPS).

Captures, through the existing ggml_backend_sched_eval_callback:
- `ffn_moe_probs-<il>`  (F32, [n_expert, n_tokens]) - the unbiased gating
  mass basis
- `ffn_moe_topk-<il>`    (I64 in this tree, I32 accepted) - the selected ids

Aggregates per (layer, expert): selection count, selected-gating mass, total
prob mass. CSV columns: layer,expert,selected,mass_selected,mass_all,tokens.
Snapshot-rewritten every 256 prob tokens and at exit.

Bugs found and fixed while building it (all real, all upstream-shaped):
- the topk tensor type is I64 here, not I32 (the filter silently rejected it)
- the probs width is K_phys on mutants, not 32 (a hardcoded width check
  silently rejected every capture on a compressed model)
- the flush window (4096 tokens) was never crossed in short runs and
  TerminateProcess skips atexit, so nothing was ever written

Use: the X-ray. It is how the campaign learned that LFM2.5-8B-A1B's router
is load-balanced (50.7% / 50.6% across index halves, exp_probs_b means
+0.0076 / -0.0076).

### 1.2 src/llama-moe-cache.cpp - reuse telemetry + env-gated ring eviction

Env: `DAAVFX_MOE_CACHE_STATS=1` prints, every 1024 plan() calls, per layer:
hits, misses, hit rate, slots held. This is what killed the per-layer cache
class policy before it was written (reuse is flat: 57-79% across 22 layers).

Env: `DAAVFX_MOE_RING_EVICT=1` (DEFAULT OFF) - eviction by ring distance
instead of flat LRU: evict the slot whose layer is stalest in ring order
((cl - il) mod n_layer), LRU-order tie-break free because the scan walks the
LRU list. MEASURED AND REJECTED: 7-10 t/s vs 14-15.6 for plain LRU + async
(upload-evict cycle: the rule evicts the just-executed layer's just-uploaded
experts one layer-step later). Kept in-tree as the record of a falsified
hypothesis; leave it OFF.

Also added: `n_layer` member to moe_cache_lru (set in init) - required by
the ring-distance computation.

WORKTREE NOTE (2026-10-22): upstream `36cbf41` rewrote this file as an SLRU
cache (`head[2]/tail[2]`, `is_protected`, `n_protected`, `victim(il)`). The
worktree merge keeps the SLRU and drops `DAAVFX_MOE_RING_EVICT` entirely; it
adds only the `DAAVFX_MOE_CACHE_STATS` counters. The ring patch described
above remains only in the main tree as the record of a falsified hypothesis.

## 2. Env knobs we use (all upstream, no code)

| Knob | Effect | Verdict |
|---|---|---|
| `GGML_VK_ASYNC_USE_TRANSFER_QUEUE=1` | miss uploads overlap compute on the transfer queue | **ACCEPTED**: diverse-prompt 12.0 -> 16-17.5 t/s (+40%), zero code |
| `GGML_VK_PREFER_HOST_MEMORY=1` | Vulkan allocates HOST_VISIBLE buffers (ggml-vulkan-buffers.cpp:220) | REJECTED: loader dies on 4.8 GB host-visible; byte ceiling anyway |
| `DAAVFX_ROUTER_LOG` | router histogram CSV | ACCEPTED (ours) |
| `DAAVFX_MOE_CACHE_STATS` | per-layer cache reuse profile | ACCEPTED (ours) |
| `DAAVFX_MOE_RING_EVICT` | ring-distance eviction | REJECTED (ours) |

## 3. Build tree (not in the repo)

- `F:\llvb` - junction to the fork root. REQUIRED for the build: the nested
  vulkan-shaders-gen configure dies past MAX_PATH at the long real path
  ("compiler identification is unknown"). Same pattern as the ecosystem's
  F:\qapp junction.
- `build_vulkan_bench/` - the campaign's build (GGML_VULKAN=ON,
  GGML_NATIVE=ON, BUILD_SHARED_LIBS=OFF, LLAMA_CURL=OFF, VS2022 x64).
  Produces llama-bench, llama-server, llama-quantize. The pre-existing
  `build_vulkan_bin/` (only llama-server.exe) was NOT touched.
- The build must run under `vcvars64` (the nested project needs the VS
  env). Long jobs are launched detached via WMI Win32_Process.Create with an
  EXIT-code line in the log - the shell reaps child processes.

## 4. Tooling we wrote (scripts/daavfx/, untracked)

| File | What it is |
|---|---|
| launch-llm.ps1 | one-command launcher for both proven modes, PID file, `-Stop` hygiene |
| phase1-bench-matrix.ps1 | go-gated bench matrix (6 rows), VRAM sampler, manifest CSV |
| gguf-surgeon.py | GGUF v3 codec (own parser/writer) + MoE surgery: inspect, roundtrip-test, amputate (--policy/--ghost/--ghosts/--f16/--mass) |
| quality-harness/{taskset.json,run-harness.ps1,score.py} | the 12-task agentic judge |
| README.md | usage + rules |

Surgeon notes worth keeping: own GGUF v3 codec (raw-span KV preservation),
amputation is dependency-free raw block surgery, merge does Hungarian
neuron-permutation alignment of SwiGLU inner neurons (scipy; greedy
fallback), writer pads inter-tensor gaps to each declared offset and streams
per-tensor producers. TRUTH GATE: roundtrip-test must report IDENTICAL
before any mutant is trusted.

## 5. Results artifacts (scripts/daavfx/results/, untracked)

Size note: the earlier "~23 GB" figure covered the results folder AND the
mutant GGUFs under `F:\llvb` and the fork root. The text/jsonl results are
small; the multi-GB files are the seven mutant GGUFs kept as the record.

- phase1/ - 6 bench rows (jsonl) + VRAM CSVs + manifest (the base truth)
- phase3b/ - router histograms (router-hist.csv, hist-armB.csv,
  hist-multighost16-cpu.csv), server logs, per-run score files
- quality-harness/results/ - responses + score jsonl for every harness run
- F:\llvb\mutant-*.gguf - the mutants (re-derivable from the policies; kept
  as the record; 30 GB of f16 intermediates were deleted)

## 6. Not changed (deliberately)

- the overlay's own code (daavfx_per_layer_hooks, theater dispatch) - the
  living-kernel design was closed by arithmetic before touching them
- llama-context.cpp, llama-graph.cpp, the model loader - the decoupled
  router-to-slab clamp was designed and costed, never implemented
- the fork's git history: nothing committed; INFLIGHT.md is the ledger

## 7. Flint merge (worktree, 2026-10-22)

Worktree: `..\llama.cpp-flint-wt`, branch `mod/flint-support`.
Merge: `git merge --no-commit --no-ff upstream/master` at `36cbf41`, zero
conflicts, still uncommitted. The main tree is untouched.

Upstream additions now in the worktree:

- `src/models/flint.cpp` (new), `src/llama-arch.cpp/.h`, `src/llama-graph.cpp`,
  `src/llama-model.cpp/.h`, `src/llama-vocab.cpp/.h`
- Jinja hex-escape fix `9febe63d5` (#30929)
- Upstream SLRU rewrite of `src/llama-moe-cache.cpp`

Our worktree changes:

- `src/daavfx_dspark_bridge.cpp` - router histogram logger applied cleanly
- `src/llama-moe-cache.cpp` - telemetry ported to the SLRU: per-layer hits,
  misses, `plan_calls`, env `DAAVFX_MOE_CACHE_STATS=1`, print every 1024 calls
- Ring eviction dropped; it was falsified on LFM and the upstream file changed
- Overlay copy: `docs/daavfx/`, `scripts/daavfx/`, `daavfx_helpers/`,
  `INFLIGHT.md`, `asm_preload.cmake`

Build (not run): `scripts/daavfx/build-flint-llama.ps1` creates junction
`F:\llvb_flint`, configures `build_flint` with VS2022 x64, `GGML_NATIVE=ON`,
`BUILD_SHARED_LIBS=OFF`, and `GGML_VULKAN=ON` unless `-CpuOnly`. It builds
`llama-server` and `llama-cli` in Release.

Not copied to the worktree: `_archive-2026-10-13/` (524 MB) and the seven root
mutant GGUFs. They stay in the main tree as the record.

## 8. Where the 2026-10-22 docs live

- `docs/daavfx/REPO-MAP.md` - ours vs upstream, every artifact path
- `docs/daavfx/FLINT-UPSTREAM.md` - Flint facts, merge, build, bench pipeline
- `docs/daavfx/moe-lab/FLINT-CAMPAIGN.md` - next-model plan, phases 0-5
- `docs/daavfx/TRACK-B-DISTILLATION.md` - teacher-to-student plan
- `INFLIGHT.md` - append the Flint rows before any commit

New scripts exist in BOTH `scripts/daavfx/` trees (main and worktree). The
docs are canonical in the main tree `docs/daavfx/`. The worktree is where the
merged binary is built.
