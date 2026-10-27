# 01d - Fault-injection shadow harness: substrate inventory

Verdict: **NOT-EXISTS** (disk). The prior audit was right. No per-token activation
stream (hidden states / per-token router probabilities / per-token intermediate
values) exists on disk anywhere in this tree. What exists is in-process taps and
aggregate counters. The shadow-harness candidate is shelved pending a capture
window (see CONSEQUENCE).

Scope note: `shared\llama.cpp-flint-wt` and `shared\llama.cpp-abelianIUT` carry the
SAME daavfx instrumentation (verified by grep; identical file set and line
anchors in both forks). "The fork" below = either worktree.

---

## 1. Env gates found (source receipts)

| Gate | Location | What it captures | What persists |
|---|---|---|---|
| `DAAVFX_ROUTER_LOG=<csv>` | flint-wt/src/daavfx_dspark_bridge.cpp:57-127 | `ffn_moe_topk-<il>` (expert ids) + `ffn_moe_probs-<il>` (F32 gating weights) per token, in the sched eval callback | **Aggregate only**: per-(layer,expert) counters, CSV snapshot-rewrite |
| `DAAVFX_MOE_CACHE_STATS=1` | flint-wt/src/llama-moe-cache.cpp:153-176 | MoE expert-cache hits/misses per layer | **Aggregate only**: stderr print every 1024 plan calls |
| `DAAVFX_DSPARK_TAPS=1` | flint-wt/src/daavfx_dspark_bridge.cpp:203-289 + flint-wt/src/daavfx_per_layer_hooks.c:447-555 | `l_out-<il>` layer outputs (hidden states) at 5 tap layers | **Nothing on disk**: static buffer + session-local shared memory |

### 1a. Router histogram logger is aggregate, not per-token
- daavfx_dspark_bridge.cpp:100-127 (`router_log_capture_probs`): per-token loop
  at line 118 accumulates `g_router_all_mass[il][e] += p[e + tok*W]` -- each
  token's prob vector is consumed into a scalar and discarded.
- daavfx_dspark_bridge.cpp:129-151 (`router_log_capture_topk`): per-token loop at
  line 138 increments `g_router_count[il][e]` -- expert id counted, not recorded.
- daavfx_dspark_bridge.cpp:82-98 (`router_log_flush`): writes header
  `layer,expert,selected,mass_selected,mass_all,tokens` (line 86). This is the
  ONLY fopen in the daavfx instrumentation (line 84) and it writes aggregates.
- Per-token state retained in RAM: `g_router_last_probs[il]` (line 111-116) holds
  ONLY the most recent capture's prob matrix, overwritten each eval, never written
  per-token to disk.

### 1b. MoE cache stats are aggregate counters
- llama-moe-cache.cpp:37-42: counters `hits_by_layer` / `misses_by_layer` /
  `plan_calls`. Printed at line 171 as
  `moe-cache stats: layer %2d hits=%llu misses=%llu rate=%.1f%% slots=%d`.
  No file output, no per-token dimension.

### 1c. DSpark hidden taps never touch disk
- daavfx_per_layer_hooks.c:447: `static float g_dspark_buf[DAAVFX_DSPARK_FLOATS]`
  -- single-slot in-memory buffer (5 taps x 2048 hidden floats).
- daavfx_per_layer_hooks.c:478-526: `daavfx_dspark_capture` memcpy's each tap's
  `l_out-<il>` vector into that buffer; seq counter bumps when all taps are full.
- daavfx_per_layer_hooks.c:528-533: `daavfx_dspark_read` copies the buffer to an
  in-process caller.
- daavfx_dspark_bridge.cpp:20-55: the ONLY persistence channel is a session-local
  Windows shared-memory map `Local\daavfx_dspark_<pid>` (stats + norms + tap
  layout, seqlock epoch) consumed live by the Rust lab (crates/llab). It dies
  with the process; it is telemetry, not an activation stream.
- Host-resident only (bridge.cpp:195-198, v1 note at line 193-194): device taps
  are not even captured; this is a health tap, not a capture substrate.

## 2. RYIUK crates (local_llm\GGUF\RYIUK)

Grep for activation/tensor/hidden/logits/dump/stream/per-token/thought/receipt:
- No activation or tensor dump path in `primal_evolution` or `antihack_math`.
  All dump/receipt hits are provenance/migration receipts (ryiuk-migrate
  copy receipts, antihack collapse receipts, studio_bridge receipt ingestion).
- crates/ryiuk-core/src/thought_particle.rs:376-377 is a serde round-trip in a
  unit test; not a per-token stream.
- Conclusion: RYIUK holds receipts about work, not model internals.

## 3. Router CSVs on disk (scripts\daavfx\results)

Every CSV in the results tree is AGGREGATE per-(layer,expert) -- one row per
(layer,expert) pair, cumulative counters over the whole run. None is a time
series. The `tokens` column is the layer's total token count REPEATED on every
row of that layer -- it is a denominator, not a row index. No token axis, no
per-token prob vector, no request-boundary marker, no timestamp per row.

Router histogram files (header `layer,expert,selected,mass_selected,mass_all,tokens`):

| File | Data rows | Layers | Experts | tokens col |
|---|---|---|---|---|
| results\flint-router-log.csv | 704 | 2-23 | 0-31 | 8960 |
| results\flint\router-q2xl-initial.csv | 704 | 2-23 | 0-31 | 8960 (dup of above) |
| results\flint\router-q2xl-mt5-32k.csv | 9728 | 2-39 | 0-255 | 516 |
| results\flint\router-q3xl-full.csv | 10240 | 2-41 | 0-255 | 516 |
| results\flint\router-q3xl-mt5-32k.csv | 9728 | 2-39 | 0-255 | 516 |
| results\phase3b\router-hist.csv | 704 | 2-23 | 0-31 | 3186 |
| results\phase3b\hist-armB.csv | 704 | 2-23 | 0-31 | 65232 |
| results\phase3b\hist-multighost16-cpu.csv | 704 | 2-23 | 0-31 | 56010 |

Non-router CSVs in the same tree (context, not substrate): 6x vram-*.csv
(timestamp, tag, used_mib -- GPU memory samples) and 1x manifest-*.csv (bench
commands). No activation-like data filenames (.npy/.bin/csv) exist anywhere under
shared\ or local_llm\ (filename sweep; all activation/hidden/logits hits are
unrelated source files in daavile_harness repos).

## 4. Whole-fork hidden-state writer grep

Only file writers of model-internal data in src/ (excluding ggml / llama-arch /
llama-model / llama-graph plumbing):
- daavfx_dspark_bridge.cpp:84 -- the aggregate router CSV (section 1a).
- llama-adapter.cpp:433 (LoRA read), llama-mmap.cpp:376 (GGUF mmap/state),
  llama-quant.cpp:1196 (quantized GGUF output) -- weights/adapters, not
  activations.
- No code path writes hidden states, per-token intermediates, or logits to disk.

---

## What exists vs. what the candidate needs

- EXISTS (in-process, live only): per-token router ids/probs observed transiently
  in the eval callback; hidden-state taps at 5 layers into a single-slot RAM
  buffer; shared-memory telemetry for the process lifetime.
- EXISTS (on disk): per-(layer,expert) cumulative counters over a run
  (8 CSVs above) -- a histogram, sufficient for X-ray topology questions, not
  for fault injection.
- NEEDED: a token-indexed stream (token id / position, per-tap hidden vectors,
  per-layer router probs) on disk, aligned across tiers of the expert cache so a
  divergence between tiers can be attributed to a specific token.
- GAP: ordering + per-token payload. The aggregate CSV loses token order and the
  prob vector; the tap buffer loses history (one slot) and never reaches disk.

## CONSEQUENCE

Shadow-harness candidate is **SHELVED on this receipt**. A capture window must
provide the substrate first: the minimal extension is to persist
`g_router_last_probs`-class data per token (a per-token append row in the
`DAAVFX_ROUTER_LOG` writer at daavfx_dspark_bridge.cpp:82-98, or a ring-buffer
drain at daavfx_per_layer_hooks.c:478-526) with a token/position index. Until
that window runs, no fault-injection shadow harness can be evaluated on this
machine.
