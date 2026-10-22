# CPU MISS FALLBACK - design (C++ round 2)

Date: 2026-10-21
Owner: operator, agent ID `lfm25-gtx1650-campaign`
State: DESIGN + step 1 instrumentation. No behavior change yet (the new
stats are env-gated and read-only).

## 1. The want

On the moe-cache path a cache MISS costs a PCIe upload of one expert slab
(~2.06 MB, ~0.72 ms effective, ~0.2-0.3 ms with the async transfer queue
overlapped). The 5600G could compute that same expert from DDR4 in
~0.20 ms and the GPU would not stall at all. If misses were computed on the
CPU instead of uploaded, the hybrid could plausibly beat BOTH parents:
GPU computes the hits while the CPU computes the misses, in parallel,
with no upload stall at all.

## 2. Why the literal version is impossible

The literal plan: for every token, split the 4 selected experts into
VRAM-resident hits and misses, run the hits as a GPU mul_mat_id and the
misses as a CPU mul_mat_id, then recombine.

Blocker: ggml graphs are STATIC. The graph for a decode step is built
BEFORE the top-k ids exist - the ids are runtime data (the router's
output). Anything that depends on WHICH experts were selected (hit vs
miss) is therefore a runtime decision, and a ggml op cannot straddle two
backends: a Vulkan kernel cannot read host memory, and a CPU kernel
cannot read device memory. Partitioning per expert per token would need
either runtime graph surgery (ggml has none) or a new fused cross-backend
op (no precedent, no clean semantics for the partial-sum recombination).

The moe-cache exists precisely because it dodges this: the graph always
runs mul_mat_id on the DEVICE, and the copy callback stages whatever the
runtime selected into the device buffer at runtime. The staging is data
movement, not graph structure - which is exactly why it works.

## 3. The viable reframing: per-LAYER class policy

Move the decision from per-token to per-layer, where it can be made at
BUILD time (static graph, fully supported):

  class A  - experts permanently in VRAM (no cache, no upload, no CPU)
  class B  - experts host-resident AND cache-eligible (VRAM cache slots)
  class C  - experts host-resident and NEVER cached (pure CPU compute,
             ~0.20 ms per expert, no upload stall, no cache pressure)

Class C is the "CPU miss fallback" in the only form the architecture
allows: layers whose reuse rate is too low to pay for a cache slot simply
never get staged - their experts just compute on the CPU, while the
layers that DO reuse get the cache and the GPU.

Budget math (1536 MiB cache, 6.16 MB per complete expert, ~249 slots):
the cache can cover ~11 layers of 22 experts each, or 22 layers of ~11
experts each, or anything between. WHICH layers is the whole game, and
the answer is empirical:

  reuse(l) = hits(l) / (hits(l) + misses(l)) per layer, per token

## 4. Step 1 (implemented now): cache reuse telemetry

llama-moe-cache.cpp already knows n_hit for every plan() call (the
scheduler copy callback runs at runtime with the real ids). Add per-layer
hit/miss counters plus an env-gated summary print
(DAAVFX_MOE_CACHE_STATS=1) so the reuse profile is directly observable:

  moe-cache stats: layer  2 hits=1234 misses=120 rate=91.1% slots=11
  moe-cache stats: layer 23 hits=  11 misses=77 rate=12.5% slots=11

The summary prints every 1024 plan() calls (about once per 1024 tokens).

## 5. Step 2 (after the profile exists): the policy

Inputs: the reuse profile (step 1) plus the router mass histogram
(DAAVFX_ROUTER_LOG) - the histogram says which experts carry the gating
mass, the reuse profile says which experts keep coming back.

Policy: assign cache slots to the layers with the best reuse-per-slot
ratio, in the order of that ratio, until the budget is spent. Layers with
reuse below a threshold become class C (never staged) or class A
(permanently resident) depending on the budget.

Implementation surface: llama-moe-cache.cpp (slot allocation per layer -
the group already tracks per-layer slot maps) plus the existing
--ncmoe layer list (which layers are host-resident at all). No graph
changes, no new ops, no loader changes - the static-graph constraint is
respected by construction.

## 6. Risks and what would falsify it

- If the reuse profile turns out FLAT (every layer reuses equally), there
  is no class C to carve out and the policy collapses to "cache
  everything you can" - which is the current behavior. The step-1 profile
  decides this before any code is written. Cheap falsification first.
- If reuse is concentrated but the misses that remain are exactly the
  expensive ones (big slabs, cold layers), the win could be small.
- Interaction with the async transfer queue: the fallback reduces upload
  volume, which changes the overlap profile. Re-measure with and without
  the async knob (the async knob stays the baseline for comparison).

## 7. Measurement protocol (step 2 acceptance)

Config under test: -ngl 99 -ncmoe <host layers> -t 6 --jinja
--moe-cache-mib <budget> (+ GGML_VK_ASYNC_USE_TRANSFER_QUEUE=1 as the
control).

Acceptance: diverse-prompt t/s (story generation, the 12-17.5 t/s band
today) and hot-prompt t/s both at or above the async baseline, with the
12-task quality harness at baseline (the change is data placement only -
no math changes - so any quality move is a bug signal).

## 8. STEP 1 RESULT (2026-10-21): PROFILE IS FLAT - PRECONDITION FAILS

Measured with the new telemetry (DAAVFX_MOE_CACHE_STATS=1), 600 tokens of
mixed agentic/prose prompts, 1536 MiB cache, async on:

| layers | hit rate | slots held |
|---|---|---|
| best (6, 10, 11, 15) | 76-79% | 7-9 |
| median (most layers) | 65-70% | 8-14 |
| worst (2, 17) | 57-59% | 14-16 |

Spread across 22 layers: 57%-79%. NO layer stands out, and the coldest
layers hold the MOST slots (layer 2: 59% reuse, 14 slots) while the hottest
hold the fewest (layer 10: 79% reuse, 9 slots) - that is LRU already doing
exactly what it should: weak layers churn, strong layers keep a small hot
set.

VERDICT: section 6's cheap falsifier fired - the profile is flat enough
that carving out class C (never-staged layers) has nothing to exploit.
There is no cold-layer island to move to the CPU. The per-layer class
policy is DEAD as designed; do not implement it.

What the profile DOES say: ~1/3 of expert reads still miss on average,
and a miss costs ~0.72 ms (upload) vs ~0.20 ms (CPU compute). The
fallback's value therefore has to come from attacking the MISS RATE
itself, not from choosing where misses land. Standing arithmetic: the
1536 MiB cache holds ~249 slots for a 704-expert working set - it can
never cover the rotation, so the miss rate is structural, and a bigger
cache only moves the number, never eliminates it. The only remaining
lever that changes the economics is the MISS PATH ITSELF: make a miss
cost CPU-compute time (0.20 ms) instead of upload time (0.72 ms), which
is the per-token dynamic split that section 2 shows is impossible in
ggml's static-graph model... unless the split is done at a coarser
granularity than per-expert: per-LAYER-BATCH. Recorded as the open
question for round 3, not solved here.

Side finding (worth keeping): moe-cache t/s is strongly content-dependent
- 2.2 t/s on a cold fill storm, 9.7-11.0 t/s on mixed prose, 14-17.5
t/s on the story prompts in the previous session. The cache path's value
scales with how repetitive the workload is; the 59-79% reuse band is the
mechanism.
