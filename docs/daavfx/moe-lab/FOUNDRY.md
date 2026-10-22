# FOUNDRY.md - the ablation foundry: destructive-experimental program

Date: 2026-10-20
Owner: operator, agent ID `lfm25-gtx1650-campaign`
State: EXPERIMENT REGISTER. Nothing built or run. Hard gate unchanged: the
human coder's model sweep finishes first.
Companion docs: GTX1650-LFM25-CAMPAIGN.md (conservative arm: make the 8B run
well), LIVING-KERNEL-DESIGN.md (control plane). This doc is the RADICAL arm:
destroy assumptions, recast, measure. Operator doctrine: destroy first,
create second, measure third.

## 0. Doctrine

Every plan we have written rests on load-bearing assumptions nobody in this
campaign has tried to break. The foundry exists to break them on purpose and
measure what actually falls. Output fidelity is NOT a gate here. The gates
that ARE kept: (a) the destruction budget (section 2), (b) crash containment
(each experiment runs in a disposable process against a COPIED model file,
never the production GGUF), (c) ledger discipline (every run gets a row,
RYIUK receipt for provenance).

## 1. The bootstrap question, answered for the record

The operator asked: is the living kernel bootstrapping? "LLMs are slow and we
fix them with an LLM" sounds circular. Resolution:

- The brain (350m) and the product (8B) are different models. The brain runs
  fine while the product is slow, so there is no hard circular dependency.
- The brain does not make the 8B's tokens faster by being an LLM. It fixes
  DECISIONS around the token path: what to pin, what to prefetch, what to
  stage, what to forget. No amount of silicon fixes decisions; decisions were
  never the model's bottleneck before because no fabric had decisions to
  make. The bandwidth wall is physics; the decision surface is unexplored.
- The loop IS bootstrapping, deliberately, the compounding kind: fabric
  produces telemetry -> brain writes policy -> fabric behaves differently ->
  richer telemetry. A compiler written in its own language, an OS that boots
  itself, AlphaZero bootstrapping from random play to superhuman: all the
  same shape. The only failure mode of such loops is circular dependency
  (the fix needing the broken thing to already work). Ours does not: the
  control plane is fully functional with the target at zero speed.

## 2. The destruction budget

"If it isn't measured it isn't destroyed, it is just damaged." (D. EBorgStark)

One number, set by the operator per experiment: the maximum acceptable loss
in exchange for the measured gain. Suggested first setting for an agentic /
coding workload: "task success within 2-3% of baseline, style shifts
tolerated, speed or memory gain > 25%, else revert." This is a DIAL, not a
gate. The byte-identical religion from the campaign docs is just one
position of this dial (budget = 0) - appropriate for kernel mutants, wrong
for model surgery. Nobody ever told us a nonzero budget was allowed. Set it
and the foundry opens.

Caution, stated once and not re-imposed: a benchmark suite underestimates
distribution shift (the Space Rover problem). A conservative budget avoids
false passes; the operator decides where that sits.

## 3. The instruments

Tooling status: AUTHORED 2026-10-20, UNVALIDATED until the go signal (the
human coder's sweep owns the box). Lives in scripts/daavfx/:

- gguf-surgeon.py: inspect / roundtrip-test / amputate / merge. Own GGUF v3
  codec, raw-span KV preservation, provenance KV (general.foundry_note).
  Amputation is dependency-free raw block surgery; merge uses the fork's
  gguf-py dequant. TRUST RULE: a surgeon build is only used after
  roundtrip-test reports IDENTICAL on the target model.
  STATUS 2026-10-20: parser validated live against the real 4.80 GB file
  (inspect clean; two codec bugs found and fixed en route: GGUF v3 KV order
  is key-then-type-then-value, and the value parser must not re-read the
  type field). Writer still unvalidated: roundtrip-test at go.
- phase1-bench-matrix.ps1: the campaign Phase 1 launcher (go-gated,
  port-8082-guarded, VRAM-sampled).
- quality-harness/: the destruction-budget judge. 12 deterministic agentic
  tasks (tool-call JSON, code fixes, instruction following, format
  discipline), server runner, stdlib scorer. Baseline the untouched model
  first; every mutant gets a score row.

Also:

- Quality-budget harness: fixed agentic task set (tool-call JSON validity,
  multi-step task success, code-edit correctness), baseline-scored with the
  untouched 8B, then re-scored per mutant. Reuses ecosystem machinery (ledger
  rows, receipts, the bench culture). Built FIRST; no harness, no surgery.
- Surgery tools, in order of effort:
  - LOADER-LEVEL (no math changed): expert disable mask, expert merge
    (weighted-average two experts' tensors), partial-layer offload variants.
    All buildable as a small standalone tool (llama-model-saver.cpp exists in
    the fork as a starting point for GGUF rewrite).
  - KV-LEVEL: attention-only KV eviction/pruning between tokens (hybrid
    memory: shortconv state is recurrent and CANNOT be evicted - it IS the
    memory; attention-block KV can).
  - WEIGHT-LEVEL (dormant monster): test-time adaptation via the fork's
    examples/training code. Activated only after F1-F3 produce results.

## 4. The teardown list (F-series)

Each row: assumption destroyed, mechanism, expected shape, measurement,
cost/risk.

F1 EXPERT AMPUTATION. Assumption: all ~32 experts per MoE layer are needed.
exp_probs_b exists to skew usage; skew implies a cold tail. Mechanism: mask
coldest X% of experts per layer (renormalize routing), sweep X in
{10, 25, 50, 75}. Expected: quality cliff is workload-dependent, likely
gentle to ~25% on single-domain sessions. Measures where the cliff actually
is. Cost: small loader/surgery tool; risk: distribution drift (that is the
measurement). CONFIRMED LAYOUT (inspect 2026-10-20): 22 MoE layers x 32
experts, 4 used per token, slab ~2.06 MB, experts ~= 92% of file bytes.
At K=16 the mutant file is ~2.6 GB: it FITS the 1650's usable VRAM, so an
amputated 8B can run FULLY on the GPU. F1 links directly to the campaign's
closed full-offload lane.

F1 RUN 1 (blind, 2026-10-20): K=16 keeping raw indices 0-15 REJECTED -
harness 8/12 -> 1/12; arithmetic control: intact 17x23 = \boxed{391} in 71
tok vs mutant 143 (confident, wrong; 1024-tok probe spent only 197 tok ->
real damage, not budget starvation); degraded formatting (missing JSON
quotes). Mutant ran full-GPU at pp512 144.8 / tg128 60.1 t/s (3.2x split).

F2 VERDICT (ghosted-K24 run 1, 2026-10-21): SINGLE-CENTROID GHOST = DEAD
ON ARRIVAL, exactly as the REVIEW-5 dilution trap predicted. Setup: 23
hottest kept per layer (mass-ranked policy), 9 coldest merged into ONE
norm-restored ghost slot; both arms taken through the identical
f16 -> llama-quantize Q4_K_M pipeline (fair A/B, same 3.71 GB). Quality:
ghosted 8/12 = amputated 8/12 = baseline (the ghost neither helps nor
hurts at K=24 - amputation itself is quality-neutral here). TELEMETRY
(the real result): with DAAVFX_ROUTER_LOG live, the ghost slot fired
75 times against 15,068 baseline demand for the removed experts =
FILL RATIO 0.005; zero firings in 19 of 22 layers. The +-0.33x dilution
estimate was OPTIMISTIC - a centroid of ~orthogonal directions has tiny
projection on every token, so the ghost never re-enters top-4 and the
model IS amputated-K23 plus a dead slot. Router-logger bugs found and
fixed en route: topk tensors are I64 in this tree (was filtering I32);
probs width is K_phys on mutants (was hardcoded 32); flush window
4096 -> 256 tokens (TerminateProcess skips atexit).

CONSEQUENCES FOR F2/F2R:
1. Any single-centroid ghost is decoration. Next iteration: MULTI-GHOST
   CLUSTERING - group the complement by router-row cosine similarity into
   3-4 clusters (one ghost each, dilution ~1/sqrt(3) with cluster-coherent
   directions); costs extra slabs per layer (K_phys = kept + n_ghosts).
2. The real fix for full-GPU is the DECOUPLED ROUTER-TO-SLAB mapping:
   keep ALL 32 router rows (5.76 MB total) + index-clamp selected ids to
   the ghost slab range in the graph (needs the metadata flag + loader
   relaxation + cast/min/cast clamp, ~40 lines) - undiluted 32-expert
   routing over compressed slabs.
3. A CPU MISS FALLBACK for the moe-cache path stays the cheapest win:
   a cache miss computed on the 5600G from DDR4 (~0.20 ms) beats a
   synchronous PCIe upload (~0.72 ms) by 3.5x.

F2 VERDICT FINAL (multi-ghost run, 2026-10-21): CLUSTERING FIXED THE
FIRING, NOT THE QUALITY. Multi-ghost K=16 (13 hottest kept + 3
cosine-clustered ghosts, K_phys 16, 2.63 GB full-GPU): ghost fill ratio
0.168 - 33x better than the single-centroid 0.005 - but the harness stayed
at the amputated level (3/12 GPU, 2/12 CPU re-run vs guided-amputated 3/12;
baseline 8/12). The removed experts' contributions are not reproducible by
any merge: the load balancer made them individually load-bearing. FINAL
F1/F2 PICTURE: the quality cliff between K=24 (baseline-equal) and K=16
(dead) is a CAPACITY cliff. Expert reduction cannot take this model below
~K=24 without damage, and the full-GPU 60 t/s lane needs K<=18 - so the
60 t/s dream is closed for THIS model via expert reduction. The
compression story for a load-balanced MoE is the SPLIT ITSELF (all 32
experts available across RAM+VRAM at 18.9 t/s); speed now comes from
(a) moe-cache hybrid compute + CPU miss fallback (0% CPU proven),
(b) Phase 3a speculative decoding (provably lossless), (c) LK
orchestration. A future model with a REAL cold tail (no aux-loss balancer,
or trained without one) would reopen the amputation/ghost lane. Tooling
built and kept: surgeon --policy/--ghost/--ghosts/--f16/--mass, router
logger (I64 + dynamic width + 256-token flush), the f16->llama-quantize
fair-A/B pipeline. F1 CLIFF MAP (guided sweep, 2026-10-21; harness = 12
agentic tasks):

| config | path | tasks | checks |
|---|---|---|---|
| K=32 baseline | split | 8/12 (66.7%) | 23/28 (82.1%) |
| K=28 guided | split | **9/12 (75.0%)** | 23/28 (82.1%) |
| K=24 guided | split | 8/12 (66.7%) | 21/28 (75.0%) |
| K=16 guided | full-GPU | 3/12 (25.0%) | 11/28 (39.3%) |
| K=16 blind | full-GPU | 1/12 (8.3%) | 5/28 (17.9%) |

READINGS:
1. Guidance works: guided beats blind by +17 points at K=16, and K=28 sits
   at-or-above baseline. But the cliff between K=24 (baseline-equal) and
   K=16 (dead) is STEEP even with perfect per-layer guidance - the load
   balancer makes every expert load-bearing in practice.
2. Split-path K=28/K=24 = ZERO speed change (4 active experts regardless)
   - capacity cuts buy RAM only, not t/s. Not compelling as production
   configs.
3. The full-GPU 60 t/s lane requires K<=18 (VRAM: K=16 server measured
   ~1.1 GB overhead incl. display; K=20 = 3.17 GB model -> OOM at 8k ctx).
   K=16 quality = 25% (dead). The only roads to 60 t/s at production
   quality: (a) F2 ghost-merge to K~18-20-effective + reduced ctx, hoping
   ghosts soften the cliff; (b) the split + moe-cache + F2R stack (0% CPU,
   ghosts absorb misses, 32 routing targets intact) - needs the LK-1/LK-2
   runtime patches; (c) spec-decode amortization on the split (Phase 3a).
4. Per-expert bookkeeping (REVIEW-4): one slab 2.06 MB, one complete
   expert 6.16 MB, one index across 22 layers 135.6 MB.

Blind-vs-guided at K=16 answered: +17 points from guidance; the rest is
capacity. F1 doctrine validated end to end: harness first, mutants after,
controls always.

REVIEW-3 CORRECTION (inversion trap, pending histogram confirmation): the
"kept the router-FAVORED half" reading above is likely BACKWARDS. Under
auxiliary-loss-free load balancing (the design exp_probs_b exists for), the
bias is an EQUALIZER, not a hotness badge: naturally-hot experts get their
bias pushed NEGATIVE to throttle them; naturally-cold experts get bias
pushed POSITIVE to coax tokens in. Keeping indices 0-15 (positive bias)
probably kept the artificially PROPPED-UP COLD half and amputated the
naturally-hot half - which explains the crater BETTER than "cold tail is
not expendable". Also, +-0.0115 is tiny against raw router logits either
way. And the proposed K=28/K=24 next rungs cannot full-GPU anyway:
per-index cost measured at 135.6 MB (4.80-2.63)/16, so K=28 ~= 4.26 GB and
K=24 ~= 3.71 GB both exceed the ~3.4 GB usable ceiling; on the split path
they would run at the same ~18.9 t/s as K=32 (4 active experts regardless
of total). The full-GPU sweet spot is empirically K ~= 16-18 at 8k ctx
(measured K=16 server overhead ~1.1 GB incl. display); K=19-20 only with
smaller ctx or display off. QUEUE RE-ORDERED: histogram logger FIRST, then
GUIDED amputation at K=28/24 (split, quality cliff) + K=20/19/16 (full-GPU),
then F2 merge at the cliff point.

PHASE 3B HISTOGRAM RESULT (2026-10-20, router logger landed in the daavfx
bridge as env DAAVFX_ROUTER_LOG; 60 requests x 3 reps over harness + agent
prompts; 235,516 routing events): THE ROUTER IS PERFECTLY LOAD-BALANCED.
Selection share of indices 0-15: 50.7%; gating-mass share: 50.6%;
exp_probs_b means +0.0076 / -0.0076. BOTH prior readings (hot-half,
inverted-cold-half) were wrong: the bias ENFORCES balance and succeeds.
There is NO cold tail at the routing level. The blind K=16 crater is
explained by per-layer structure instead: within-layer mass spreads are
huge (layer 2: expert 21 at 412 vs expert 23 at 3.2 - 128x) but the top
experts DIFFER per layer ({21,11,14,18} vs {25,0,6,18}), so any global
index slice removes per-layer workhorses. CONSEQUENCES: (1) "amputate the
unused experts" is dead for this model - guided per-layer cuts still face
a cliff because the load is balanced by design; (2) F2 ghost-MERGING
(fold the tail, keep the capacity) becomes the primary compression path;
(3) the router logger now feeds LK-1/LK-2/F2R permanently.

REVIEW-4 CORRECTIONS (byte math + Simpson's paradox):
- EXPERT SIZE BOOKKEEPING: 2.06 MB is ONE PROJECTION SLAB (gate OR up OR
  down). One COMPLETE expert (all 3 projections) = ~6.16 MB. One expert
  index across all 22 layers = 22 x 6.16 = ~135.6 MB (measured:
  (4.80-2.63)/16). Therefore pinning ONE complete ghost per layer across
  22 layers = ~135.6 MB (not 45 MB) - still trivial inside a 1536 MiB
  moe-cache.
- SIMPSON'S PARADOX: the 50.7/50.6 aggregate halves split is an artifact
  of summing scrambled per-layer permutations by raw index. The REAL cold
  tail exists in PER-LAYER RANK space (128x within-layer spread). No cold
  tail in INDEX space; a real one per layer in RANK space. Guided
  per-layer K=16 vs blind K=16 is the decisive test.
- OPERATOR QUESTIONS on moe-cache (answered 2026-10-20): (1)
  llama-context:530 disables pipeline_parallel ONLY (multi-GPU only, inert
  single-GPU); code-read says spec-decode coexists - combination not yet
  fired, tested at Phase 3a. (2) moe-cache tg on the 32-expert model: hot
  prompts 18.5-18.8 t/s (= split baseline, no gain), diverse prompts 12.0
  t/s (per-miss upload stalls) - current value = CPU liberation (0% CPU)
  + the LK foundation, not raw tg.

REVIEW-5 (2026-10-21): moe-cache slot math corrected AGAIN - 1536 MiB /
6.16 MB per complete expert = ~249 slots (~35% of 704), NOT "all experts"
(the earlier 745 figure reused the 2.06 MB slab size; second instance of
the same error). The diverse-prompt 12.0 t/s now derives cleanly: ~65%
miss rate x ~57 misses/token x ~0.72 ms synchronous PCIe upload
(6.16 MB @ ~8.5 GB/s effective incl. WDDM) ~= 41 ms stall/token; a miss
uploaded to VRAM is 3.5x SLOWER than computing it on CPU from DDR4
(~0.20 ms). Fixes, in value order: CPU miss fallback (compute misses on
the idle 5600G instead of uploading), LK-2 circular-distance pinning,
F2R ghost absorber (miss at 128 GB/s instead of 0.72 ms PCIe).

CENTROID-DILUTION TRAP (REVIEW-5): merging m mutually-orthogonal router
rows into one norm-restored centroid cuts the ghost's dot-product logit by
~1/sqrt(m) (9 cold experts -> 0.33x) - the ghost loses top-4 and the
ghosted-K24 silently becomes amputated-K23. Countermeasures: (a) multi-
ghost clustering by router-row cosine similarity + bias boost; (b) the
decoupled router-to-slab mapping: keep ALL 32 router rows (5.76 MB total
across 22 layers - noise) and clamp selected idx >= K_phys-1 to the ghost
slab in the graph. LOADER REALITY discovered while costing (b): the model
loader VALIDATES ffn_*_exps and ffn_gate_inp shapes against
expert_count, so (b) needs a metadata flag (e.g. lfm2moe.expert_clamp=1)
+ loader relaxation for the slab count + a graph-side id clamp
(cast-F32/min/cast-I32, GROVEMOE-style) + a reshape fix that uses the
router tensor's actual width - ~40 lines across loader+graph, NOT 5.
Until that lands, ghostify v1 slices routers to K_phys (kept + 1 ghost
row = weighted mean + L2 restore) and MEASURES the dilution via
DAAVFX_ROUTER_LOG (ghost-slot selection count vs the removed experts'
histogram counts).

C++ ROUND 1 VERDICT (LK-2 ring-distance eviction, 2026-10-21): FALSIFIED
by measurement - REJECTED. The patch (env DAAVFX_MOE_RING_EVICT=1,
in-tree for the record) evicts the slot whose layer is stalest in ring
order instead of the flat LRU head. Belady-style reasoning said it should
fix the "LRU evicts early-layer hot experts" pathology; the measurement
said otherwise: story-generation 7.0-10.0 t/s vs LRU+async 14.0-15.6
(reproduced in-session), hot 10.0 vs 16.1. POST-MORTEM HYPOTHESIS: the
ring rule systematically evicts the just-executed layer's JUST-UPLOADED
experts one layer-step later, every token - an upload-evict cycle that
LRU's global recency view avoids (fresh uploads are MRU under LRU and
survive to their next use; under ring-evict they die within one layer
step). The within-pass next-need ordering is not the whole story; the
cross-token survival of fresh uploads dominates. LESSON: LRU is already
approximately Belady for this rotating access pattern, and the async
transfer queue had already absorbed most of the stall the eviction rule
was meant to fix. Patch stays in-tree env-gated (default OFF = stock);
env-gate discipline paid for itself in the first C++ round.

STANDING CONFIG after C++ round 1: plain split 18.9 t/s (CPU busy) or
split + moe-cache 1536 + GGML_VK_ASYNC_USE_TRANSFER_QUEUE=1 at 14-17.5
t/s with 0% CPU - operator's choice between throughput and CPU
liberation. C++ round 2 (CPU miss fallback: dynamic hit/miss graph
partitioning) = heavyweight, needs a design doc before code.

TOOL NOTE: merge --out-type rewrites the WHOLE tensor at f16/q8_0 (a
q8_0 K=24 file = ~6.2 GB and CPU expert reads ~1.9x heavier -> split tg
would halve) - wrong tool for split-path F2 tests. amputate --ghost is
the right shape: kept slabs stay RAW at original quant, one weighted
Hungarian-aligned ghost slab per layer quantized to the tensor's own
type, routers sliced to K_phys = kept + 1 ghost row.

F2 EXPERT MERGING (ghost experts). Assumption: experts are discrete.
Mechanism: average the cold tail into K ghost experts (research precedent:
expert merging). Expected: milder cliff than amputation at the same byte
saving. Measures amputation-vs-merging frontier.

RUNTIME LANE (F2R, added in REVIEW-1): ghosts are not only an offline
experiment - they are a LIVE miss absorber. One ghost per MoE layer,
pinned in GTX VRAM (22 x ~2.06 MB ~= 45 MB total). When the router picks
an expert that is a cache miss AND its gating probability is below
ghost_cutoff_prob, the fabric does NOT fetch the 2.06 MB slab from DDR4:
it substitutes the resident ghost at 128 GB/s. Implementation lanes:

- Lane B first (zero code): gguf-surgeon writes the merged ghost slab into
  every cold-expert slot of the layer; the model runs completely stock;
  the quality harness measures the approximation cost before any runtime
  patch is invested. Costs cache dedup (ghost copies cached as separate
  entries) - acceptable for the first experiment.
- Lane A (the real design): one canonical ghost + a routing remap patch in
  the lfm2moe graph build (after top-k, if p_i < cutoff -> expert index :=
  ghost id; pin ghosts explicitly in the moe-cache). Interacts with the
  slot maps; pairs with the LIVING-KERNEL ghost_cutoff_prob policy knob
  (0 for precision tasks, up to ~0.08 for casual chat).

The "1-2 experts carry 80% of gating weight" claim is a HYPOTHESIS until
Phase 3b histograms say so; the substitution error is bounded by
p_i x expert distance and judged by the harness, not by vibes.

REVIEW-2 MATH FIXES (both lanes):
- SWIGLU NEURON-PERMUTATION ALIGNMENT. An lfm2moe expert is a SwiGLU
  bottleneck E_i(x) = W_down,i (SiLU(W_gate,i x) odot (W_up,i x)) with a
  1792-dim inner layer. Neuron k in expert 17 has ZERO alignment with
  neuron k in expert 18 - training learns arbitrary row/column
  permutations. Raw averaging of gate/up/down across unaligned experts
  makes the elementwise product multiply mismatched features and collapses
  the ghost's output norm toward zero. gguf-surgeon merge now
  permutation-aligns each group's members to the group's anchor expert
  BEFORE averaging: build the 1792x1792 cosine-similarity matrix of
  concatenated [W_gate_k; W_up_k] rows, solve the assignment (scipy
  linear_sum_assignment when available; greedy fallback otherwise), then
  permute gate/up rows and down columns. ~seconds per layer offline, zero
  training data. scipy is optional (pip install scipy upgrades greedy to
  optimal assignment).
- LANE B IS AN UPPER-BOUND-ON-DAMAGE TEST. Stock llama.cpp has no
  ghost_cutoff_prob check: a cold expert selected with a large router
  weight (p_i = 0.60) still gets the ghost substituted unconditionally.
  Worse, if 2-3 of the top-4 routed experts land in ghost-filled slots,
  stock mul_mat_id executes the same 2.06 MB ghost slab several times and
  computes p2*G + p3*G + p4*G instead of (p2+p3+p4)*G. Lane A (cutoff
  check + deduplicated index remap) STRICTLY beats Lane B in quality AND
  speed; Lane B exists only to measure how bad unconditional replacement
  gets before we invest in the runtime patch.

F3 SEMANTIC KV EVICTION. Assumption: KV is sacred. Mechanism: the control
brain reads session structure and evicts low-salience attention KV between
requests (keep attention-sink tokens; conv state untouchable). Expected:
long-session drift, then recovery on re-reads. Measures how much memory the
holy cache actually needs on real sessions.

F4 INTER-TURN SPECULATIVE EXECUTION. Assumption: the fabric computes only
when asked. Single-user chat idles the fabric ~90% of wall-clock.
Mechanism: during human-idle, pre-generate candidate continuations and
pre-stage experts from session router history; on the real event, keep the
match or discard. Expected: hit rate pays directly in felt latency; misses
cost idle electricity. The foundry's free lunch: nobody spends idle time.

F5 SESSION-LoRA (test-time adaptation). Assumption: weights freeze at
deploy. Mechanism: grow a small LoRA delta on session traces during idle,
via examples/training in the fork. Expected: unknown, plausibly real on
repetitive agent workflows. Risk: divergence; contained by disposable-model
discipline. The literal "living weights" experiment. DORMANT until F1-F3
data exists.

F6 ZERO-INTERVENTION RECOMBINATION. Assumption: the graph the GGUF
describes is the machine. Mechanism: NONE. No training, no fine-tuning -
just precompile the weights into NEW graphs (depth-pruning, layer-grafting
across same-family GGUFs) and score. Expected: mostly slag, occasionally
something functional. The purest destroy-create experiment: the operator's
"weights are live tissue" doctrine with zero learning machinery.

## 5. The crazy registry (F100+, unpriced, unjudged)

- F100 Malamute: decode the SAME hidden state through the attention stack of
  a different member of the family.
- F101 Machine-dreaming: during idle, self-generate, then amputate/merge on
  the dream distribution to pre-evolve a mutant before the human's next
  turn.
- F102 Vocabulary lockdown: freeze only the JSON/grammar tool-call token
  distribution to full precision, crush everything else harder.
- F103 Cross-model graph graft: bolt a layer from another GGUF in place,
  score with the harness. Note: the 36 GB capacity discovery means the
  foundry can host 30B+ mutants that fit nowhere else on this box.

## 6. What stays dead even in the foundry

- Unmeasured destruction (vandalism is not an experiment).
- The per-token brain: latency physics, unchanged.
- F5 with an infinite self-improvement loop and no revert ceiling: runaway
  weight drift bricks the model's usefulness; the budget dial IS the ceiling.

## 7. Order of operations

1. Quality-budget harness, baselined on the untouched 8B (needs the coder's
   sweep done first).
2. F1 amputation sweep (cheapest big information: one tool, many X values).
3. F2 merge sweep against F1's cliff points.
4. F3, F4 in parallel (independent mechanisms).
5. F5, F6 last: both need the harness mature and the surgery tooling proven.
6. Whatever survives feeds the living kernel as pin/amputation policies
   (LK-tier work) and the campaign as config knowledge.
