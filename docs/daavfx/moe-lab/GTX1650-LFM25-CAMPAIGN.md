# GTX 1650 + LFM2.5-8B-A1B campaign plan

Date: 2026-10-20
Owner: operator, agent ID `lfm25-gtx1650-campaign`
State: PLAN. Nothing has been run. No compile, no bench, no config change.
Hard gate: the operator's human coder is currently benchmarking all models on
this box. Every phase below waits until that sweep finishes and the operator
gives the go signal ("coder done, gemma stopped, go"). A compile from this
campaign would eat cores and pollute his numbers.

Scope lock (operator mandate): model under test is LFM2.5-8B-A1B only. No other
model enters the bench matrix. No BIOS changes (RAM stays at JEDEC 2400).

## 1. Ground truth (verified read-only on 2026-10-20)

Hardware:

| Thing | Reality |
|---|---|
| dGPU | GTX 1650 4GB (TU117), PCIe 3.0 x16 confirmed (~11.5 GB/s), 2 screens attached, WDDM. Observed idle floor with a live server: 857 MiB (display + Vulkan context). Usable VRAM: ~3.1-3.4 GB |
| CPU | Ryzen 5 5600G, 6C/12T Zen3, AVX2 |
| RAM | 32GB (2x16GB, Kingston Fury XMP-3200 + A-DATA, mixed) running JEDEC 2400 dual channel: ~38 GB/s theoretical, ~28-32 real, shared by CPU and iGPU. BENCH.md's "2x 3600" note is stale (docs/daavfx/BENCH.md) |
| iGPU | Vega 7 (GCN5), reads the same DDR4 (zero-copy possible), no int8 dot ext, weak FP16, 1 screen attached. Driver 30.0.13014.8 (2022-era) |
| PCIe | x16 Gen3 both directions, verified via nvidia-smi |

Tree (shared/llama.cpp-abelianIUT, branch `daavfx` @ 43011a618, base 0.7.0 #30603):

- `lfm2_moe` supported: `src/models/lfm2moe.cpp`; llama-bench exposes `-ncmoe/--n-cpu-moe`.
- Upstream MoE expert cache in-tree: `--moe-cache-mib N` (env `LLAMA_ARG_MOE_CACHE_MIB`), `src/llama-moe-cache.cpp` (639-line LRU, slot maps, per-backend caches for multiple GPUs; upstream #29887 + #30112).
- Vulkan backend: MUL_MAT_ID (193 refs), CONV_TRANSPOSE_1D (10), FLASH (58). Requires Vulkan 1.2/1.3. No coopmat on TU117 (standard mulmat paths, fine).
- 30 `GGML_VK_*` env knobs, including `PERF_LOGGER`, `PIPELINE_STATS`, `MAX_NODES_PER_SUBMIT`, `MMVQ` force/disable, `INTEGER_DOT_PRODUCT`, `FUSION`, `SERIALIZE_SUBMISSIONS`, `ASYNC_USE_TRANSFER_QUEUE`, `PREFER_HOST_MEMORY`, `SUBALLOCATION_BLOCK_SIZE`.
- daavfx overlay: DSpark taps (`DAAVFX_DSPARK_TAPS=1` -> `Local\daavfx_dspark_<pid>`, see docs/daavfx/WIRE.md), per-layer hooks, dormant theater-dispatch (CPU/RAM/STORAGE/IGPU/DGPU routing; call sites not in this branch yet).
- `shared/daavfx-vk-layer`: `VK_LAYER_DAAVFX_shard` built. Turing nvoglv64 queueSubmit fault workaround; `VK_DAVAFX_SHARD_MAX_DISPATCHES` (default 3).
- Tooling gap: `build_vulkan_bin/` contains only llama-server.exe. cmake 4.3.2 + Vulkan SDK 1.4.350 + VS2022 present. `asm_preload.cmake` shim handles the known MASM blocker. No ninja; use the VS generator.

Model: LFM2.5-8B-A1B Q4_K_M, 4.80 GB, arch key `lfm2moe`. 24 blocks, all with
shortconv; GQA attention blocks with 4 KV heads (small KV cache); routed
experts `ffn_{gate,up,down}_exps`, router `ffn_gate_inp`, routing bias
`exp_probs_b`. Hidden 2048, 8.3B total / 1.5B active, vocab 128k, ctx 128k.
Confirmed via gguf-surgeon inspect (2026-10-20): expert_count 32,
expert_used_count 4 (only 4-of-32 active per token), expert_ffn 1792,
22 MoE layers (blocks 2..23; 0-1 dense), expert slab ~2.06 MB (Q4_K) /
~3.01 MB (Q6_K down on some layers). Routed experts ~= 92% of file bytes.

Draft candidates already on disk (same tokenizer family):
`24-lfm2.5-230m`, `25-lfm2.5-350m`, `26-lfm2.5-1.2b-instruct`.

## 2. The wall

Per generated token on the split path:

- Dense path (conv + attn + router + norms): ~0.5-0.9 GB at Q4 reads from
  GDDR5 (128 GB/s private island, fast, never the problem).
- Active routed experts: ~0.4-0.7 GB must come through RAM (CPU experts) or
  PCIe (upload into VRAM cache).

Ceilings at batch=1 on this box:

- CPU experts: RAM-bound, 12-25 t/s realistic at Q4 on the 5600G at 2400 MT/s.
- Full model in VRAM: impossible. 4.80 GB does not fit 3.4 GB usable; full-GPU
  needs IQ3_XS-class (~3.3 GB) and a 1.5B-active MoE degrades visibly below Q4
  because only 1.5B params carry the signal.

Campaign principles: partition bytes so each pipe carries only what it must;
amortize bytes across tokens (spec decode); shave per-op cost (kernels). Never
try to widen a pipe in software (impossible) or in BIOS (off-limits).

## 3. Phases

### Phase 0 - build the bench (gated on coder's sweep finishing)

STATUS 2026-10-20: COMPLETE. Coder's sweep finished; operator gave the go.
- Built via junction `F:\llvb` -> fork root (MAX_PATH: the nested
  vulkan-shaders-gen configure blew past 260 chars on the long path -
  "compiler identification is unknown"; the junction mirrors the F:\qapp
  pattern from AGENTS.md rule 3). Build ran under vcvars64.
- Targets: llama-bench (42.9 MB), llama-server (50.4 MB), llama-quantize
  (41.9 MB) in build_vulkan_bench\bin\Release\, GGML_VULKAN=ON,
  GGML_NATIVE=ON (AVX2), BUILD_SHARED_LIBS=OFF, LLAMA_CURL=OFF.
- Devices: Vulkan0 = AMD Radeon (Vega 7, 16328 MiB GTT),
  Vulkan1 = NVIDIA GTX 1650 (4149 MiB, 3385 MiB free - matches the
  ~3.4 GB usable estimate).
- Surgeon writer TRUST GATE PASSED: roundtrip-test reports IDENTICAL
  (5,155,564,768 bytes byte-for-byte) after fixing two writer bugs found
  by the gate: (1) data_start was computed from an offset-less info
  section while the file was written with 8-byte offsets per tensor
  (2048-byte skew on this model); (2) inter-tensor alignment padding was
  never written. Mutants are now trustworthy to build.

Out-of-tree `build_vulkan_bench/` in the fork. VS2022 x64 Release,
`-DGGML_VULKAN=ON -DGGML_NATIVE=ON`. Run `daavfx_helpers/check_asm.cmd` first;
apply the asm_preload shim if the MASM blocker bites. Do not touch
`build_vulkan_bin/` or the live server.

Deliverable: `llama-bench.exe` + fresh `llama-server.exe` (llama-quantize
builds free in the same tree; unused unless franken-quants are ever revived).
Verify `--list-devices` shows the GTX 1650 (Vega appears as a second Vulkan
device; parked).

### Phase 1 - base truth (gated on "coder done, gemma stopped, go")

STATUS 2026-10-20: SIX ROWS COMPLETE (fired on operator order while a game
was running; self-consistency is good, stddev ~1%, a quiet-box re-run can
confirm). Results (llama-bench jsonl, build 43011a618, model 8.47B params /
4.79 GiB, pp512 + tg128, 2 reps):

| row | config | pp512 t/s | tg128 t/s | peak VRAM |
|---|---|---|---|---|
| cpu-t6 | -ngl 0, t6 | 107.7 | **14.6** | 1231 MiB |
| cpu-t12 | -ngl 0, t12 | 106.6 | 11.5 | - |
| split | -ngl 99 -ncmoe 24, t6 | **111.8** | **18.9** | **1548 MiB** |
| split-fa0 | split + -fa 0 | 102.6 | 19.1 | - |
| split-fa1 | split + -fa 1 | 106.0 | 17.6 | - |
| full-oom | -ngl 99 | OOM at load: 1.06 GB short on Vulkan1 | - | - |

Findings:
1. THE SPLIT WORKS: 18.9 t/s tg / 111.8 t/s pp, 1548 MiB VRAM - inside the
   predicted 12-25 t/s band, +29% tg over the best CPU row. Production
   config: `llama-server -m <8B> -ngl 99 -ncmoe 24 -t 6`.
2. t6 BEATS t12 for tg on this box (14.6 vs 11.5 - Zen3 CCD split penalty).
   t6 is the CPU default from now on; t12 only helps pp marginally (nil).
3. pp is ~flat everywhere (102-112) - prefill is bound elsewhere (CPU
   expert GEMMs at ubatch 512), not by the dense path. Kernel work on the
   CPU mul_mat_id path may move pp more than GPU shaders.
4. FA is a wash at this ctx (tg: fa0 19.1 >= auto 18.9 > fa1 17.6, within
   ~1.5 t/s of noise). Re-test at 16k+ ctx where KV grows.
5. The wall is now MEASURED, not assumed: full offload is 1.06 GB short.
   F1 amputation at K=16 saves ~2.2 GB - the full-GPU lane is viable with
   room for KV + buffers.

Launcher authored and waiting: scripts/daavfx/phase1-bench-matrix.ps1
(refuses to run without -Go; aborts while port 8082 is listening).

Protocol per docs/daavfx/BENCH.md: `llama-bench -o jsonl`, recorded priority and thread
count, pp512 + tg128, 8k ctx, LFM2.5-8B-A1B Q4_K_M ONLY.

Rows:

1. `-ngl 0`, t6 and t12: CPU reference.
2. `-ngl 99 -ncmoe 99`: the split (dense on GTX, experts on CPU). Headline row.
3. `-ngl 99` full: expected OOM; documents the wall.
4. Split row with flash attention on/off.
5. VRAM capture per row (nvidia-smi query during the run).
6. MoE-cache smoke: PASS with a two-regime perf signature (2026-10-20,
   server-side, port 8083):
   - llama-context.cpp:530 caveat RESOLVED: it only disables
     pipeline_parallel for multi-GPU splits - inert on this single-GPU box,
     no conflict with speculative decoding.
   - The cache WORKS on Vulkan: during a 128-token generation the server
     CPU delta was 0.03s over 11.5s wall (~0%) - experts execute on the
     GPU from the cache; the CPU expert GEMMs are gone.
   - Perf two-regime: hot-prompt short gens match plain split (18.5-18.8
     t/s); a diverse prompt (story-writing, wide expert fan-out) drops to
     12.0 t/s - per-miss PCIe upload stalls when the working set churns.
     This is measured motivation for LK-1/LK-2 (circular-distance eviction,
     pinning, prefetch) and F2R (ghost absorber kills most misses).
   - VRAM: server ~3.0 GB with 1536 MiB cache - fits ONLY without the game
     (the first smoke attempt at 3816/4096 MiB with the game running
     produced WDDM paging collapse: 0.6 t/s; not a moe-cache fault).
   - MODEL DISCOVERY: LFM2.5-8B-A1B is a REASONING model via the jinja
     template - answers arrive in `content` only after `reasoning_content`
     spends its budget. Harness max_tokens must rise accordingly (done in
     taskset v1.1); raw /completion endpoints bypass thinking.
   - No moe-cache log lines at default verbosity: it logs nothing on
     success; the disable-warning is the only signal, and its absence +
     VRAM delta + 0% CPU are the positive proof.

Rows land in llab-data + a new docs/daavfx/BENCH.md section; fix the stale "2x 3600" RAM
note in that doc while there.

### Phase 2 - max squeeze (every step gated by A/B rows; measure before code)

1. `GGML_VK_PERF_LOGGER=1` on the split config: per-op hot list for lfm2_moe
   on TU117. This list decides the patch order. Nothing gets patched on vibes.
2. Env sweep (zero code): `MMVQ` force/disable (batch-1 tg path),
   `INTEGER_DOT_PRODUCT`, `FUSION`, `GRAPH_OPTIMIZE`, `MAX_NODES_PER_SUBMIT` x
   `SERIALIZE_SUBMISSIONS` (interacts with the shard layer),
   `ASYNC_USE_TRANSFER_QUEUE`, `PREFER_HOST_MEMORY`, `SUBALLOCATION_BLOCK_SIZE`.
3. Shard layer A/B: `VK_LAYER_DAAVFX_shard` on/off, `MAX_DISPATCHES` sweep.
4. Patch lane (fresh branch, INFLIGHT.md entry, P1 discipline: integer-exact,
   byte-identical output, patch file in `patches/`). Suspects in expected
   order: `mul_mat_vec` (dense path, batch=1), `mul_mat_id` (expert GEMM
   workgroups for TU117), `conv_transpose_1d` (shortconv fires in all 24
   blocks), FA kernels for the attention blocks.

### Phase 3 - synthetic Strix (flagship; quality-exact)

3a. Speculative decoding, stock first: draft = lfm2.5-350m (safe; 1.2b is the
    acceptance upgrade if VRAM allows) fully resident in VRAM. Measure
    acceptance and t/s on the best Phase 2 config. Property: rejection-sampled
    output distribution is identical to the target running alone. It is the
    only provably lossless speed lever in this stack.
3b. Expert histogram logger (one bench run) -> hot-expert pinning patch in
    llama-moe-cache (pinned hot set + LRU tail). LFM2.5's `exp_probs_b` bias
    makes expert usage skewed; pin what is measurably hot.
3c. Draft-window prefetch fusion: after each verified block, the target's
    recent router choices predict the next block's experts; upload them into
    the cache while the draft generates (draft time is free PCIe/RAM time).
    DSpark taps / per-layer hooks are the natural steering surface.
3d. Optional, operator call: iGPU as a third expert consumer via the upstream
    per-backend caches (#30112). Expected small (+10-20% ceiling). Risks: GCN
    quant paths weak, WDDM sync on tiny GEMMs, stutter/TDR-flicker risk on the
    single iGPU-attached screen (auto-recovers; shard layer mitigates), likely
    needs an Adrenalin installer update (an installer, not BIOS). Only if
    3a-3c land and the box is still hungry.

### Phase 4 - parked (documented, not forgotten)

Franken-GGUF mixed quants; F16 expert streaming beyond the cache; expert
compression over PCIe (~20% ceiling, shader decompress eats it); `-np` batched
server posture (wrong shape for single-user agent chat); fine-grained
cross-device op routing (killed by latency math, section 5).

## 4. Synthetic Strix math (why spec-decode is the flagship)

PHASE 3A VERDICT (2026-10-21): FALSIFIED for the split path - measured, not
assumed. Findings:

1. VOCAB WALL: LFM2.5-8B-A1B has vocab 128,000 (bos 124894); EVERY
   LFM2.5 small (230m/350m/1.2b) has the old 65,536 vocab (bos 1) - Liquid
   expanded the tokenizer for the big model. No same-family draft can ever
   draft for the 8B. (Also discovered: this fork's --spec-type list includes
   draft-simple/eagle3/mtp/dflash/DSPARK/ngram-* - the DSpark taps are a
   built-in speculative type in 0.7.0, parked for the LK stack.)
2. NGRAM SPECULATION MEASURED (spec-type ngram-cache, draft-n-max 4):
   1.9-8.4 t/s vs the 18.9 t/s baseline - a 2-10x REGRESSION. Acceptance
   0-32%. Root cause: the campaign math in this section assumed GPU-resident
   experts (verify-batch union stays in VRAM cache -> amortized). On the
   CPU-expert split the union INVERTS the economics: verifying k=4 draft
   tokens pulls up to 16 experts per layer from DDR4 instead of 4 - bytes
   per ACCEPTED token roughly double. Speculative decoding is structurally
   negative on the CPU-expert split path, regardless of draft quality.
3. Remaining spec lanes: draft-dspark (external draft machinery, LK-native,
   untested), or spec on the moe-cache path (verify hits run from VRAM;
   needs the CPU-miss-fallback + pinning first). Parked - not scheduled.

MOE-CACHE + ASYNC TRANSFER QUEUE (2026-10-21, zero-code win): with
GGML_VK_ASYNC_USE_TRANSFER_QUEUE=1 the diverse-prompt stall mostly
dissolves: story-generation 16.0-17.5 t/s (vs 12.0 synchronous; the
18.9 plain-split baseline within reach), hot prompts ~16.1. The miss
uploads now overlap compute on the transfer queue instead of stalling.
This makes split + moe-cache 1536 + async the BEST measured all-around
config: 0% CPU, all 32 experts, quality intact, ~16-17.5 t/s across
prompt types (vs 12.0-18.9 spread without async). Production candidate
pending a longer soak; the CPU-miss-fallback and LK-2 pinning remain the
C++ upgrades on top.

ZERO-COPY HOST-MAPPED LANE (2026-10-21, FALSIFIED BY CRASH + ARITHMETIC):
GGML_VK_PREFER_HOST_MEMORY=1 makes ggml-vulkan allocate
HOST_VISIBLE|HOST_COHERENT buffers (ggml-vulkan-buffers.cpp:220) - the
theory being that the GPU streams expert slabs straight from host RAM
over PCIe with no staging, no cache, no eviction. Measured: the loader
DIES silently after ~10 min (4.8 GB of host-visible allocation, no
device-local fallback, no log - driver-level death). Byte accounting
also caps it: per token the 4 active experts x 22 layers x 6.16 MB =
542 MB must cross PCIe (11.5 GB/s theoretical, 3-8 realistic) versus
DDR4's 28-30 GB/s, and the CPU path already sustains 10.2 GB/s effective
(53 ms/token at 18.9 t/s = 36% of DDR4 peak, i.e. compute-mixed rather
than transfer-bound). A per-expert host-visible implementation would
land at PARITY (15-18.5 t/s) at best - it would buy CPU freedom, not
speed. The physics is now fully mapped: DDR4 beats PCIe for this
traffic, and VRAM residency is the only thing that would beat DDR4 -
which needs K<=18, where quality dies.

CAMPAIGN CLOSURE NOTE (2026-10-21): the surviving configurations are
(1) plain split 18.9 t/s, CPU-bound, all 32 experts, quality intact;
(2) split + moe-cache 1536 + async 14-17.5 t/s, 0% CPU, same quality.
The LK-0 "config advisor" is DEAD BY ARITHMETIC (the best alternative
lane, 17.5 t/s, is below the static baseline 18.9 - a router can only
pick the worse lane). The only remaining 3.2x delta is dual-tier routing
(full-GPU K=16 at 60.1 t/s for easy prompts, split for hard ones), whose
safety story is weak: K=16's failures include SILENT wrongness (a valid
but incorrect code fix) that no cheap gate catches, and our failure set
does not form a semantic class (tool-call-calc passed while
tool-call-weather failed; code-write-function passed while
code-fix-offbyone failed). Reviving it needs DATA first: a labeled
K=16-safety corpus (50-100 prompts, harness-scored) and a judge that
catches silent wrongness.

Expert amortization at k=4 draft tokens, 8-of-32 experts, uniform routing:
expected union ~= 22 of 32 experts per step -> ~5.5 expert-equivalents per token
vs 8 -> ~30% less expert traffic. Routing skew (which `exp_probs_b` exists to
create) pushes savings toward 50%. Measured, not promised, in 3a.

Draft VRAM budget: 350m Q8 ~= 0.4 GB (safe); 1.2b Q8 ~= 1.3 GB (tight next to
the dense path + KV + Vulkan buffers in 3.4 GB usable).

Quality: exact by construction (rejection sampling against the target's own
distribution). Speedup target: 1.5-2.5x tg, honestly bracketed.

## 5. Unified-silicon fabric: CPU + RAM + iGPU + dGPU (the crazy section)

Operator's question, taken seriously: not chasing speed, what can a unified
execution fabric over all silicon in this box theoretically provide? Roast
first, viability second.

### 5.1 Roast: what "unified kernel" cannot mean

- A literal single kernel spanning devices is physically impossible. There is
  no shared instruction stream, no shared clock, no coherent memory across
  PCIe. What can be built is a scheduler, not a kernel. Calling it a kernel is
  hype; kill the word.
- Per-op cross-device routing is dead on arrival. A 24-layer token is
  thousands of small ops; a cross-device fence or dispatch costs ~10-100 us.
  Route per-op and the schedule itself becomes the bottleneck. This kills the
  naive reading of theater-dispatch "op routing" at fine grain.
- Splitting one expert GEMM across executors (K-split) is dead on arrival:
  cross-device reductions per expert per layer. Only whole-expert assignment
  survives, and that is exactly what upstream #30112 per-backend caches
  already do.
- "RAM as VRAM for the dGPU" is a fallacy. The 1650 cannot read host memory
  directly; it can only receive uploads over PCIe. There is no UMA between a
  discrete card and DIMMs. The moe-cache streaming design is the only form of
  this that exists.
- iGPU economics for homogeneous matmul: Vega 7 shares the one thin pipe with
  the CPU. The reader is not the bottleneck; the pipe is. CPU and iGPU pulling
  the same expert stream fight for the same ~30 GB/s and can end up slower
  together than the CPU alone.
- Verdict on the hype: a unified fabric does not create bandwidth, does not
  create coherence, and does not survive fine-grained routing on this hardware.

### 5.2 Viability: what it can actually provide

1. CAPACITY. The one real superpower. 32 GB RAM + 4 GB VRAM = ~36 GB model
   address space under one engine. This box cannot hold LFM2.5-8B at F16
   (16.6 GB) anywhere else, nor the 26B/36B MoE folders at usable quants. The
   unified fabric is a "biggest model we can hold" machine: zero-quant-loss 8B,
   or the bigger MoEs runnable. Achievable with existing upstream machinery
   (`-ncmoe`, `--moe-cache-mib`, backend scheduler) and zero new code. The
   honest pitch: not speed, capability.
2. CONCURRENCY ceiling. Disjoint-byte partitioning: VRAM-resident weights ride
   128 GB/s; RAM-resident weights ride ~30 GB/s (CPU and/or iGPU as reader);
   PCIe uploads ride 11.5 GB/s. If all pipes stay busy simultaneously,
   non-resident ingest approaches ~41.5 GB/s vs ~28-30 pure CPU. Realistic
   utilization 60-80% -> +10-20% tg. The moe-cache plus async uploads already
   buy most of this; the rest is scheduler polish, not revolution.
3. HETEROGENEITY: expert-actor theater. The genuinely novel shape.
   - Unit of placement = one expert (~2.06 MB at Q4_K): perfect actor size.
     22 MoE layers x 32 experts = 704 actors (confirmed via gguf-surgeon
     inspect).
   - Each actor gets an affinity: PINNED (VRAM, measured hot), RAM-CPU
     (default), RAM-iGPU (optional slice). Rebalancing happens BETWEEN
     requests or per few-hundred tokens, never per-op. Coarse cadence is the
     difference between a scheduler that costs nothing and one that costs the
     run.
   - Steering data already produced by this campaign: router histograms
     (3b), DSpark taps (layer health), and the draft window (3c) as the slack
     in which actors move.
   - This is what the dormant theater-dispatch scaffolding was born for, at
     expert granularity and coarse cadence. Nothing else on this hardware
     does this, and every input part is already in-tree.
   - Level-up extension: a small LLM as the CONTROL PLANE over this fabric
     ("living kernel") - it reads telemetry and writes policy objects at
     request boundaries, never touching a token. Design:
     [LIVING-KERNEL-DESIGN.md](LIVING-KERNEL-DESIGN.md).
4. STORAGE tier (the even-crazier shelf, for the 26B/36B era): expert spill
   to NVMe (~3.5 GB/s) for cold actors. Unnecessary at 8B scale (RAM holds
   it); decisive for 36B-class models on a 36 GB fabric. Keep shelved.

### 5.3 Verdict

| Shape | Verdict (as predicted) | MEASURED (2026-10-21) |
|---|---|---|
| Capacity unification (36 GB model space) | REAL, cheap, exists in-tree | CONFIRMED - the split config is the compression: all 32 experts live across RAM+VRAM at 18.9 t/s |
| Concurrency polish (+10-20% ceiling) | REAL, expensive | PARTLY - the async transfer queue delivered +40% on the cache path's weak case (12.0 -> 16-17.5) with zero code |
| Expert-actor theater (coarse cadence) | NOVEL, worth the risk | NOT BUILT - the action space it would steer (pin maps, ghost cutoffs, spec params, layer classes) was measured and mostly died |
| LLM control plane over the fabric (living kernel) | NOVEL, the level-up shape | CLOSED by arithmetic - LK-0's best alternative lane (17.5) sits below the static baseline (18.9) |
| Per-op cross-device routing | WASTE, latency math kills it | NOT ATTEMPTED (math agreed) |
| Single-GEMM cross-device splits | WASTE, reduction cost kills it | NOT ATTEMPTED (math agreed) |
| iGPU as second matmul workhorse | WASTE on this silicon | PARKED after REVIEW-1; brain relocated to the resident 350m draft on the dGPU |
| "RAM as VRAM" magic | WASTE as stated | CONFIRMED: only moe-cache streaming works, and the zero-copy variant (GGML_VK_PREFER_HOST_MEMORY=1) crashes the loader |

## 6. Open flags

- `llama-context.cpp:530` disables something when `moe_cache_size > 0`.
  RESOLVED 2026-10-21: it disables pipeline_parallel only (multi-GPU only,
  inert on this single-GPU box); no conflict with speculative decoding.
- Exact expert count and expert/dense byte split: RESOLVED 2026-10-20 via
  gguf-surgeon inspect (32 experts, 4 used, 22 MoE layers, ~92% of bytes in
  experts; sections 1 and 5.2.3 updated). Surgeon WRITER: VALIDATED
  2026-10-20, roundtrip-test IDENTICAL on the full 4.80 GB file (two writer
  bugs found and fixed by the gate; see Phase 0 status).
- Phase 1 bench matrix: ARMED but awaiting a quiet box (operator in-game at
  fire time; benches on a loaded box are garbage by our own protocol).
- iGPU lane likely needs an Adrenalin installer update (not BIOS): operator
  approval required before 3d.
- Draft VRAM budget: 350m safe, 1.2b tight; measure before committing.
- TDR note: iGPU compute may stutter/flicker the single iGPU-attached screen
  under load; auto-recovers; dGPU screens unaffected; shard layer mitigates.

## 7. Execution gates

- ALL phases wait for the human coder's model-benchmark sweep to finish.
- Go signal: operator says "coder done, gemma stopped, go".
- This doc is the campaign source of truth. Results land in docs/daavfx/BENCH.md and
  llab-data per the existing protocol. Phase 2 patch work lands on a fresh
  branch with an INFLIGHT.md entry, P1 discipline (integer-exact, byte-identical
  output, patch file in patches/).
