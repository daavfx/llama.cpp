# Living kernel: a small LLM as the control plane of the unified fabric

Date: 2026-10-20
Owner: operator, agent ID `lfm25-gtx1650-campaign`
State: CLOSED (2026-10-21) - kept as the record, not as a live plan. The
architecture below was never falsified; its ACTION SPACE was. Measured
outcomes: LK-1 (spec scheduling) negative on the split path (1.9-8.4 t/s -
the union economics invert on CPU-resident experts); LK-2 (ring-distance
eviction) negative (7-10 vs 14-15.6 t/s); F2R (ghost miss absorber) dead
(fill 0.005 single, 0.168 clustered, quality unmoved); the per-layer cache
class policy dead pre-implementation (flat reuse profile 57-79%); LK-0
(config advisor) dead by arithmetic (17.5 t/s lane < 18.9 t/s static
baseline). What survives conceptually: the two-plane split (control plane at
request boundaries, never in the token path), the LLM-for-semantics /
bandit-for-numbers division, and the typed-readout interface. Evidence in
RESULTS.md and FOUNDRY.md. Nothing in this document was implemented in the
fork.
Companion to GTX1650-LFM25-CAMPAIGN.md (section 5).
AMENDED 2026-10-20 after operator review (REVIEW-1); wrong claims corrected
in place, amendments and new mechanisms summarized in section 10.

The operator's question, taken at full strength: forget the inference product
for a moment. Can a small LLM BE the kernel of a unified CPU+RAM+iGPU+dGPU
fabric - the glue that merges them into one machine?

Answer: the naive version is dead, the idea underneath is alive, and this
design is the alive version.

## 0. Why the naive version dies (kept roast, one paragraph)

A fabric token takes 40-80 ms on this box. Any LLM decision, even a 230M model
emitting 30 tokens, takes 100 ms to seconds. An LLM in the per-token or per-op
path is an order of magnitude slower than the machinery it would steer. Plus
free-form LLM output cannot be trusted on a hot path: one hallucinated action
bricks the run. This is not fixable with faster models on this silicon. It
stays dead. Fine. Bury it.

## 1. The reframe that saves the idea

A kernel is 10 percent dispatch and 90 percent policy: where bytes live, when
they move, what gets evicted, what gets pinned, which knobs are set, which
draft parameters run. The 10 percent must be fixed code forever (fences, LRU
steps, GEMM dispatch). The 90 percent is decision-making over telemetry -
which is exactly what learned policy is good at. Precedent, all real:

- Learned indexes (Kraska et al.): models replace B-tree internals and win.
- Bao / Neo (Marcus et al.): models steer database query planning and beat
  hand-written heuristics.
- Decima (Mao et al.): RL-learned cluster job scheduling.
- AlphaTensor (DeepMind): RL discovers new matrix multiplication algorithms,
  better than known human ones.

Nobody has built this as the control plane of a single-box heterogeneous
inference fabric. That is the hole. We are standing in front of it.

So: the living kernel = a small LLM as the fabric's POLICY ORGAN. It reads
telemetry, it writes policy, it never touches a token. Data plane = the
existing llama.cpp machinery. Control plane = the small LLM plus a policy bus
plus gates. The "unified kernel" the operator asked for is this two-plane
machine: one intelligence steering four executors.

## 2. The policy object (the brain's only output)

Tier details live in section 1. What needs pinning down here is the SHAPE of
the brain's output: a CONSTRAINED policy object (schema-validated JSON, never
free text):

    {
      "cluster":  "A",
      "pin_map":  { "layer_expert_id": "pinned" | "evictable", ... },
      "ghost_cutoff_prob": 0.05,
      "draft":    { "model": "lfm2.5-350m", "k": 4 },
      "bandit":   { "evict_penalty": 1.3, "reserve": 0.2, "threads": 6 }
    }

REVIEW-1 division of labor: numeric knob tuning (bandit block) is owned by a
Tier 1.5 contextual bandit (LinUCB / Thompson sampling), NOT by the LLM -
a pretrained 350M has no inductive bias for latency/bandwidth Pareto surfaces
and would emit vibe numbers. The LLM's readouts own exactly what a bandit
cannot do: SEMANTIC decisions (workload cluster from the raw prompt text,
quality-sensitivity calls like ghost_cutoff shifts).

Applied at request boundaries only. Invalid schema = ignored, policy
unchanged.

Tier 3 - kernel author (overnight, the endgame): the living kernel writes and
patches actual shader/CPU kernel variants (Phase 2 patch lane), runs them
through the type-aware correctness gates (REVIEW-1/2: integer-exact for
integer paths; max abs error <= 1e-5 + cosine >= 0.99999 on reference
tensors for float reductions), benches them, grades the deltas in the
optimization ledger, and adopts winners. The P1 patch culture, automated.
This is the AlphaTensor-shaped endgame: the fabric rewrites its own kernels
while the operator sleeps, and only gate-passing mutants survive.

## 3. Silicon assignment (the real unification)

| Executor | Job in the two-plane machine |
|---|---|
| dGPU (GTX 1650) | Data plane: dense path, draft model, expert cache, attention |
| CPU | Expert compute, telemetry aggregation, gate running |
| RAM | The pool (36 GB model space with VRAM) |
| iGPU (Vega 7) | PARKED (REVIEW-1). The brain runs on the lfm2.5-350m draft model ALREADY RESIDENT in GTX VRAM between requests (a 1-token readout is ms-scale, zero extra memory, no second copy, no 2022-driver dependency). iGPU shares the same ~30 GB/s DDR4 straw as the CPU; fallback lane only if spec decode is ever off |
| NVMe | Cold expert shelf for the 26B/36B era (parked) |

This is what theater-dispatch was scaffolding for. Its fine-grained "op
routing" reading stays dead (fence latency). Its reborn form is the POLICY
BUS: a versioned SHM snapshot (`Local\daavfx_lk_<pid>`, docs/daavfx/WIRE.md pattern,
seqlock + version guard) carrying policy objects to apply-side hooks in the
fork.

## 4. The level-up mechanisms (each novel-ish, each buildable from in-tree parts)

LK-1 Speculative scheduling. The mirror of speculative decoding, one level
up: Tier-1 predictors guess the NEXT request's expert needs from the current
session's router history; the fabric pre-stages experts and KV during idle
and draft windows. REVIEW-1 correction: wrong guesses are NOT cheaply
absorbed by the LRU. Upstream llama-moe-cache.cpp:167 gives a single GPU
one shared LRU across all 22 MoE layers, and MoE layers execute as a
sequential ring (2 -> 23): after layer 23, the least-recently-used experts
are layer 2's - exactly the ones needed next. Speculative overflow evicts
early-layer hot experts and causes ring-wide thrash (SpecMD, 2026, confirms
flat LRU/LFU failure under speculative MoE prefetching). The cache must be
distance-aware: see the circular-layer-distance law in LK-2. Prediction
quality upgrade: the draft model's hidden states already compute the future
(LK-6).

LK-2 Expert market. All 704 experts (22 MoE layers x 32, confirmed via
gguf-surgeon inspect) are actors. Each bids for VRAM residency; the auction
clears between requests. REVIEW-1 amendments:

- Numeric market parameters (eviction penalty, reserve, threads) are tuned
  by a Tier 1.5 contextual bandit (sample-efficient, deterministic, fast) -
  not by the LLM.
- Eviction law is circular-layer-distance (Belady-MIN for MoE rings),
  REVIEW-2 form:
  RingDist(l, l_now) = ((l - l_now) mod 22) + 1   (range 1..22; the +1
  kills the l == l_now divide-by-zero; MoE block indices 2..23 map to
  0..21 first so the ring wraps at the right boundary)
  Priority(l, j) = expected_gate_score(l, j) / RingDist(l, l_now)^alpha
  with alpha in [0.5, 1.5] tuned by the Tier 1.5 bandit (alpha -> 0 trusts
  static hotness, alpha -> 1.5 trusts strict ring order). An expert one
  layer ahead with moderate probability outranks a hotter expert one layer
  behind that will not be touched for another 21 steps. Lead-time horizon
  (REVIEW-2): one MoE layer executes in ~1.8-3.6 ms while one 2.06-3.01 MB
  PCIe upload takes ~0.2-0.3 ms + WDDM sync - a prefetch for layer l_now+1
  races a fast GPU layer and can lose, so speculative staging triggers at
  delta_lead = 2 layers ahead; eviction applies the same RingDist at
  auction time. This replaces flat LRU inside the upstream slot-map
  machinery (a localized eviction-policy patch, not a rewrite).
- The LLM contributes only the semantic side: cluster classification (LK-5)
  and quality-sensitivity calls (ghost_cutoff shifts).

LK-3 Distillation handoff. The Tier-2 LLM generates decision DATA (telemetry
digest -> good policy pairs). A distilled micro-model (Tier 1.5) is trained
on that data and takes over fast steering; the brain then only handles drift
and novelty (new workload shapes, model swaps). This is how a living kernel
scales without per-token LLM cost - the AlphaTensor lineage applied to
placement policy.

LK-4 Self-writing kernels. Tier 3 above. Overnight campaign over the Phase 2
patch lane: propose -> gate -> bench -> ledger grade -> adopt or revert.
REVIEW-1 amendments:

- Gates are type-aware. Integer paths (quant block unpack, PTQ1_0-style
  transforms) keep the integer-exact / byte-identical gate. Float reduction
  paths CANNOT be byte-identical across workgroup/reduction-order changes
  (IEEE-754 addition is non-associative); their gate is max abs error
  <= 1e-5 AND cosine similarity >= 0.99999 on reference tensors, then the
  12-task quality harness.
- Mutate templates, not raw strings: the search evolves parameterized
  #define templates (LOCAL_SIZE_X/Y, subgroup tile sizes, loop unroll,
  shared-memory padding, VK_DAVAFX_SHARD_MAX_DISPATCHES) around the
  existing mul_mat_vec / mul_mat_id / conv_transpose_1d shaders, reading
  GGML_VK_PERF_LOGGER timings as the fitness signal (FunSearch-style
  evolutionary control). Raw free-form GLSL generation is off the menu -
  it produces compiler errors and TDR timeouts.

## 5. Safety rails (why this cannot brick the fabric)

- Schema-or-nothing: the brain emits a policy object; anything invalid is
  dropped. No free-form actions, ever.
- Correctness gates (REVIEW-1, type-aware): integer-exact paths stay
  byte-identical-or-rejected; float reduction paths gate on max abs error
  <= 1e-5 + cosine >= 0.99999 on reference tensors, then the quality
  harness. Policies are graded by ledger deltas (amn-gate grade
  discipline); regression = auto-revert to last-known-good policy.
- Cadence floor: policies apply at request boundaries. Worst case = one
  request at bad settings, then revert. The hot path is never modified at
  runtime by the brain.
- Provenance: every adopted change gets a ledger row + Work-Note; kernel
  mutants get receipts. Nothing adopted silently.
- Bench hygiene (REVIEW-1): the control plane IS the 350m draft model
  already resident on the dGPU - readouts run between requests, off the
  bench-critical CPU cores. iGPU and idle threads are fallbacks only.

## 6. What stays dead

- The LLM in the per-token path: latency math, permanent.
- The LLM emitting raw commands: schema-or-nothing, permanent.
- The 8B (or any product model) as its own kernel: the scheduler must be a
  different species from the product, permanent.
- Ungated kernel "optimizations": no type-aware gate proof (integer-exact
  or float-tolerance per REVIEW-1), no adoption, permanent. The gate is
  the admission.

## 7. Apply-side mechanics (honest v0 vs v1)

- v0 (no new hot-path code): policy applied by RESTART at SESSION
  boundaries ONLY. REVIEW-1 correction: a restart destroys the WDDM Vulkan
  context, the --moe-cache-mib VRAM residency, the KV cache, and the
  recurrent shortconv state. Restarting between TURNS of a live session is
  self-inflicted amnesia - forbidden for interactive use. Restarts are
  acceptable only where no state exists to lose (fresh session start).
- v1 (in-fork patches, small) - THE PRIMARY PATH: pin-map runtime patch
  (moe-cache already has slot maps; a policy-poll hook can update the
  pinned set at cache boundaries); a knob-reload patch for the safe subset
  of GGML_VK_*; policy SHM bus (Local\daavfx_lk_<pid>, theater-dispatch
  reborn). Build this from day one for anything interactive.

## 8. Build order

- Precondition: campaign Phases 1-3 (benches, moe-cache bring-up, pin patch,
  spec decode). The brain steers machinery that must exist first. No
  machinery, no brain.
- LK-0: telemetry digest writer + policy schema + apply-side v0 (config
  regen + restart at SESSION boundaries only - never between turns of a
  live session; see section 7). Manual policies first, no LLM. Proves the
  plumbing.
- LK-1: brain v0 = the resident 350m draft emitting policy via 1-token
  typed readouts (TYPED-DECISIONS recipe) - never sampled JSON. Human
  reviews each policy before apply. It is an assistant first.
- LK-2: close the loop unattended at request boundaries with auto-revert.
- LK-3: distill Tier 1.5 from accumulated decision data.
- LK-4: overnight kernel author with full gate chain.

## 9. Open questions

- Control model placement: RESOLVED by REVIEW-1 - the brain is the
  lfm2.5-350m draft model already resident in GTX VRAM, running 1-token
  readouts between requests. iGPU / idle CPU threads are fallbacks only
  (spec decode off).
- Policy schema v0 exact fields: freeze after campaign Phase 1 data exists.
- SHM bus: reuse theater-dispatch structs or a fresh docs/daavfx/WIRE.md-style section
  (`Local\daavfx_lk_<pid>`). Fresh section preferred; version-gated.
- Where the digest lives: a rolling JSONL under 00-CPU-BENCH-MASTER or
  llab-data conventions - keep the existing bench culture intact.
- Destructive arm: experiments against the assumptions this design rests on
  live in [FOUNDRY.md](FOUNDRY.md) (F1-F6 teardowns, F100+ crazy registry).
  Whatever survives the foundry feeds this design's policy space
  (amputation/merge maps, eviction rules, idle-time precomputation).
- Typed readouts: policy-slot decisions should be made as Jev-style
  single-token lettered-option readouts (argmax over letter logits at temp 0,
  grammar-restricted) rather than sampled JSON. Research, fact-check and
  recipe: [TYPED-DECISIONS.md](TYPED-DECISIONS.md). Mandatory interface for
  all LK decision points (REVIEW-1).

## 10. REVIEW-1 amendments (2026-10-20)

Operator review landed five roasts and five upgrades; all five roasts
verified (shared-LRU confirmed in llama-moe-cache.cpp:167; SpecMD and SPICE
confirmed as real 2026 papers). New mechanisms adopted:

LK-5 SEMANTIC ANTICIPATORY ROUTING. The one thing only the LLM brain can
do: the millisecond a prompt arrives - before the 8B processes a single
token, while it is still warming dense blocks 0-1 on the GTX - a 1-token
readout on the resident 350m classifies the prompt into an empirical
workload cluster (A codegen / B JSON tool-call / C prose / D math-debug).
Each cluster carries a pre-computed pin map (from Phase 3b histograms); the
policy bus swaps it in and PCIe pre-staging of that domain's top experts
begins before the router fires. Zero-latency semantic prefetch: language
understanding steering memory physics.
REVIEW-2 FIX - DRAFT-PREFILL PIGGYBACK (three physics traps closed):
(1) QUEUE COLLISION: the 350m readout and the 8B dense blocks share the one
TU117 - a concurrent 5-20 ms prefill just serializes behind 8B blocks 0-1
on the same 128 GB/s GDDR5 bus (the shard layer exists precisely because
big submits fault nvoglv64).
(2) COUPON-COLLECTOR PREFILL FLUSH: with 4-of-32 experts active per token,
a 512-token prefill activates nearly every expert in every layer - swapping
a decode-oriented cluster pin map BEFORE prefill lets prefill thrash the
unpinned cache before tg even starts. The cluster pin map therefore applies
at the Prefill -> Decode boundary, not at prompt arrival.
(3) SHORTCONV POLLUTION: a Jev rubric suffix appended to the raw prompt
would corrupt the 350m's recurrent shortconv state (not selectively
evictable), forcing a full re-prefill before drafting.
THE PIGGYBACK: the 350m must prefill the raw prompt anyway to initialize
its KV + shortconv for speculative decoding - so piggyback on it. Prefill
the raw prompt first; snapshot the 24-block shortconv state (a few KB in
VRAM) and record KV length L; append a ~10-token Jev suffix and run the
1-token temp-0 readout (< 1 ms incremental, not 5-20 ms); restore the
shortconv snapshot and truncate the 350m KV back to L. Zero redundant
prefill, clean draft state, and the cluster pin map lands exactly where
prefill ends.

LK-6 DRAFT-HIDDEN-STATE PROBE (the SPICE maneuver). Router history only
says where you have been. When the 350m drafts k=4 tokens, its mid-layer
hidden states are already computing the future: a Tier 1.5 probe maps draft
hidden states across the k draft tokens directly to the 22x32 expert
activation probabilities of the 8B, known BEFORE verification starts.
REVIEW-2 size and deep-layer fixes: a direct d_draft(1024) -> 704 head is
720,896 weights = 1.44 MB FP16 (not ~100 KB), and a single mid-layer tap
predicts early 8B MoE layers (blocks 2-8; lexical routing) far better than
deep ones (blocks 16-23, after 14 rounds of MoE + shortconv updates).
Therefore:
- Low-rank bottleneck head 1024 -> r=48 -> 704: (1024x48 + 48x704) x 2 B =
  ~165 KB FP16 (~83 KB INT8) - fits the 5600G L2 cache and regularizes the
  offline least-squares fit.
- Inputs: two concatenated DSpark taps on the 350m (block_12 +
  pre-logit-norm).
- Per-layer blending by offline validation R^2_l:
  p_hat_l = R^2_l x Probe(h_draft)_l + (1 - R^2_l) x p_hist_l
  so a poorly-predicted deep layer (R^2_21 = 0.2, say) falls back to the
  session histogram instead of poisoning the cache with noisy guesses.
Training data = paired runs of both models (DSpark taps are the capture
path). Verify against the SPICE-paper claim class (up to 3.12x TPOT with
confidence-aware orchestration).

GHOST EXPERTS AS LIVE MISS ABSORBERS (F2R). See FOUNDRY.md F2 runtime lane:
cold-tail experts merged into one ghost per layer, 22 ghosts ~= 135.6 MB
pinned in VRAM (one COMPLETE expert = gate+up+down = 3 x 2.06 MB = 6.16 MB;
the earlier 45 MB figure used a single slab by mistake); a cache miss whose
router probability is below
ghost_cutoff_prob substitutes the resident ghost at 128 GB/s instead of a
DDR4 read. The brain dials ghost_cutoff by task sensitivity (0 for
precision work, up to ~0.08 for casual chat). Quality is judged by the
harness; the substitution error is bounded by p_i x expert distance.

Verdicts accepted with refinements: (1) brain relocated from iGPU to the
resident dGPU draft model - the contention argument was overstated for
idle windows, but the second-copy/driver argument is decisive; (2) bandit
takes numeric knobs, LLM keeps semantics; (3) restart-v0 demoted to
session boundaries only; (4) flat LRU replaced by circular distance; (5)
byte-identical gate split into integer-exact vs float-tolerance gates,
and kernel search restricted to parameterized template evolution.
