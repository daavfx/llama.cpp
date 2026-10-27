# 03-THE-PLAN - P0 through P4

The full program. Every experiment carries one falsifiable hypothesis, one
settling test, and a gate. Nothing here runs without the operator's green
light (README rule 1); file editing and build work are exempt.

**Design law**: on this box the enemy is bytes moved per token, not FLOPS.
Decode at 18.9 t/s uses ~94 GFLOPS - two orders of magnitude below what the
dGPU can do. So compute work is only worth doing where compute binds
(prefill) or where it buys bytes (smaller, faster kernels over the same
weights). Everything else attacks bytes: shrink, hide, or move faster.

---

## P0 - The generic io_engine (operator priority #1: accelerate model loading on ANY drive)

**Problem (measured)**: loading a 4.9-17.2 GB model from F: (7200rpm HDD,
4K random QD1 ~12 ms) takes minutes and makes the box crawl. Stock llama.cpp
mmaps the file and pays a page fault per page on demand - a random-access
pattern, the worst possible for a spinning disk. The kimi-k3-in-c research
already proved the real disk bottleneck is **QD1 read latency**, not
bandwidth, and our own measurement confirms it.

**Design (the "as complex as possible" loader, staged so each level ships):**

| Level | What | Complexity | Status |
|---|---|---|---|
| L0 | stock mmap (today) | zero | baseline |
| L1 | **Model warmer**: a pre-loader that reads the whole GGUF *sequentially* into the file cache before llama.cpp opens it. A sequential 1M read costs ~16.7 ms on this HDD (~65 GB/s aggregate vs 12 ms per random 4K = ~0.35 GB/s). No fork change, works for any loader, any drive | low | **P0 Phase 1** |
| L2 | **OVERLAPPED async read engine + `PrefetchVirtualMemory`**: multiple outstanding reads at tuned depth (2 on HDD, 8+ on NVMe), read-ahead thread, adapter-selected by media type (HDD/USB: sequential-cluster mode; NVMe: parallel-depth mode) - the Kittyhawk `io_engine` design | medium | P0 Phase 2 (needs fork or loader injection) |
| L3 | **Content-aware sequential order**: read the GGUF header, learn the model's tensor schedule, and pre-stage tensors in *load order* so llamacpp's first-touch faults hit warm cache pages | medium | P0 Phase 2.5 |
| L4 | **Co-activation cluster layout**: from router traces (the 48x256 logger), group experts that fire together and rewrite the GGUF so a cluster is one contiguous run - a sequential read grabs a whole pre-activation set | high | P0 Phase 3 (needs traces + a convert pass) |
| L5 | **LLM-era layout compiler**: an offline job that runs over routing traces and produces (a) a re-ordered GGUF, (b) a per-drive-profile prefetch manifest, (c) a depth_map of expert residency (hot -> NVMe/V:RAM, cold -> HDD). The loader executes the manifest; the manifest is produced by a small model or statistical analysis at conversion time. This is the "we have LLMs, make the loader as complex as possible" tier | highest | P0 Phase 4, after L2 proves |

**Where bytes land (the operator's question answered)**: today mmap pulls
HDD->RAM page cache and the GPU then copies RAM->VRAM over PCIe. The design
space the loader gets to choose from: RAM page cache (stock), pinned
staging buffers (copy engine, 13.3 GB/s), VRAM-resident (weights that live),
or **never-landed** (in-shader host reads - measured dead: 1.4/4.8 GB/s).
The loader picks per tensor class, not per file.

**Gate**: L1 must show load-time and PC-slowness improvement on F: before
any fork work. **Success metric**: time-to-first-token; secondary: page
fault count; tertiary: operator-perceived crawl.

---

## P1 - The thinking-token problem (operator priority #2: reinvent reasoning cost)

**Problem**: models emit long `reasoning_content` streams before the answer
landed in `content`; each thinking token is a full forward pass through the
whole model. On a box where every forward pass costs real money, a 2,000-
token think is a 100x wall-clock multiplier. Nothing in the ecosystem treats
thinking as a tax to be managed - it's the newest, least-optimized surface.

**Design:**

| Lever | Idea | Why it can work |
|---|---|---|
| **T-A. Draft the thinking** | thinking text is *predictable* text (boilerplate reasoning structure) - the exact distribution where speculative decoding gets high acceptance rates. Drafting theater: iGPU/CPU small model drafts tokens, dGPU verifies | acceptance rate on boilerplate is the whole game of spec-decode; it was never tried on thinking segments |
| **T-B. Theater-sharded thinking** | the iGPU (50 ns dispatch, 4.8 GB/s in-shader reads over unified memory) runs the draft/partial-think theater concurrently with the dGPU's verify/compute theater, reading the same host memory | the iGPU finally gets a compute job that matches its strengths: cheap dispatch, zero-copy access, independent stream |
| **T-C. Thinking budget** | a control that caps `reasoning_content` length per turn (the harness already separates it), measuring the quality-vs-token curve | deterministic, stores nothing, trivially A/B-able |
| **T-D. Two-model thinking** | a small local model (0.5B at 74 t/s) produces the thinking; the big model consumes only the compressed plan | "thinking" is largely rehearsal; rehearsal is cheap to simulate at small scale |

**Phase 0 (analysis only, zero GPU)**: from existing transcripts compute
the thinking tax per model: token share and wall-clock share of
`reasoning_chars` vs `content`, per turn class. This decides which lever to
prototype first and gives T-A its acceptance-rate target.

**Phase 0 RESULT (2026-10-24)**: **DONE - the tax is 77-79% of all generated
tokens** on this box (qwen3.5-4b r2: 13,643 of 17,803; granite v13b: 13,530
of 17,127; full table + mechanism + the field's levers in
`08-THINKING-DEEP-DIVE.md`). Two new experiments fell out of the analysis:
**T-E** (the `enable_thinking: false` template toggle - one line, and if
quality holds it buys ~4x actions per wall-clock hour), and **T-F** (the
0-action failure classes must be re-audited for `max_tokens` starvation
before they are called model failures).

**Gate**: T-A prototype beats the plain-decode t/s *on reasoning-heavy
prompts* only; elsewhere it must not regress.

---

## P2 - Concurrent same-memory expert split (the iGPU's assigned job - answers "concurrent reading same memory dgpu and igpu helps somehow?")

**YES - on MoE, within a layer, and it is falsifiable per layer.** The top-k
selected experts of one MoE layer are independent GEMVs over the same token
vector; they do not need each other to compute. They can therefore be
split across theaters **concurrently, all reading the same host memory**:

- **iGPU**: its experts read zero-copy through UMA (4.8 GB/s in-shader, no
  PCIe traffic, 50 ns dispatch)
- **dGPU**: its share copy-streams to VRAM (13.3 GB/s) and computes at
  3.2 TFLOPS
- **CPU**: remainder on its proven DDR4 path (10.2 GB/s effective)

Aggregate drain: 4.8 + 13.3 + 10.2 ~= **28 GB/s of expert reads from the
same pool** vs 10.2 today. Sync cost: the partial outputs are small vectors
(k=hidden_size values) summed per token per layer - an all-reduce of a few
KB, trivial against the expert work.

**Gate**: hot-set concentration (P1 traces / router-logger data) decides how
many experts per layer are actually in play; Phase 1 prototype is
single-layer, single-token, in the probe harness (not llama.cpp) - prove the
synth time beats the solo time before touching the engine.

---

## P3 - The dGPU squeeze (the operator's sanctioned "every good, bad and stupid idea" - kernels)

Target: the measured gap between 3,179 GFLOPS achieved and ~6 TFLOP
theoretical on TU117, and the prefill disaster (0.14-0.39 t/s pp on Flint).

| Experiment | Idea | Note |
|---|---|---|
| E2a | TU117-tiled dequant-GEMV: hand-written compute shader for K-quants (128-bit loads, subgroup ops, tile shapes for 14 SMs) | replaces stock generic shaders on the expert path |
| E2b | concurrent FP16+INT32 dual-issue probe: submit fp16 and integer kernels on separate queues; measure combined throughput vs sequential | the honest retraction of the archived "116 TFLOPS" is that concurrent FLOPS-equivalent was counted, not FP16 - but the silicon effect is real and unmeasured as *throughput*; E0 gets the number |
| E2c | L-Mul (int-add + bit-shift multiply) in the matmul kernel | the archived Phase 18 cliffhanger; never run |
| E2d | TU117 mma.sync emulation (`m16n8k8` f16 fragments, double-buffered shared) - EMULATION, not hardware: TU117 is the sm_75 tier without tensor hardware; the honest value is proving the software path's throughput | the operator's `lemon_pepper_mma_kernel` thread, revived as a measured experiment. GATED behind G-3a: if `VK_KHR_cooperative_matrix` is exposed, the coopmat path replaces this row entirely and the TN-era claim re-prices |
| E2f | clock-state captured with every number (P8 vs ramped) | no clock locking without asking; record the state instead |

**Gate**: each kernel beats the stock path on llama-bench's pp/tg for the
same tensor class, with identical outputs or documented tolerance.

---

## P4 - MoE or dense? (the route decision, answered with data)

**Both, in different lanes, and the measured physics already picked their
roles.**

| Lane | Role | Why | Ceiling |
|---|---|---|---|
| **Dense <=7B, VRAM-resident** | **speed lane** | all bytes fit in 4 GB; no routing; the 74.77 t/s 0.5B pattern scales until weights stop fitting | 74.77 t/s proven at 0.5B; this lane's ~145 target is kernel work (P3) |
| **MoE 8B-40B** | **capability lane** | bytes/token = only the active slice - the ONLY physics that decouples a 17-31 GB model from this box's storage and VRAM | 18.9 t/s today; P2's ~28 GB/s aggregate + P0's io_engine + P1's thinking tax are the levers toward 2x |
| **Dense >8B** | **dead lane** | every token streams all weights: 8+ GB/token; impossible from HDD, marginal from NVMe | recorded so nobody re-derives it |

**Conclusion**: MoE is the route to big models on this box and the theaters
(P2) and the streaming stack (P0/P1) are what make it work; dense is the
route to raw speed demos and the kernels (P3) are what make it work. The
program's primary bet is the MoE capability lane, because that is the lane
where the operator's models (LFM2.5, Flint) and the operator's 75->145
question both live.

---

## Sequencing (next green window)

1. Router traces drain -> hot-set verdict (running, no action needed)
2. **P0 Phase 1** - the warmer (hours, generic, fixes loads every drive)
3. **P1 Phase 0** - thinking-tax analysis (pure analysis, zero GPU)
4. **P2 prototype** - the concurrent expert split in the probe harness
5. P0 Phase 2 (io_engine), P1 T-A, P3 experiments as one-offs
6. **SEQUENCING RULE (amended 2026-10-26)**: the original rule held "P0/P1/P2
   before P3 because P3's kernels do nothing if the bytes can't arrive". The
   audit then showed the MoE bytes levers may be spending against a
   NON-BINDING constraint - so the rule no longer holds as written. The
   amended shape is TWO LANES, ONE BOX: the MOE lane runs the reuse pipeline
   (P0 io_engine, P1 thinking tax, R1/R2 prefix reuse); the DENSE + PREFILL
   lane is kernel work (P3), which is now the only lane that can prove or kill
   the dense 2x. Kernels for MoE decode stay behind their bytes evidence.

## What would falsify this entire plan

- Traces show routers are diffuse (load-balanced like LFM2.5's, no hot set)
  AND T-A acceptance rates on thinking text are low AND P2's sync overhead
  eats the concurrency win -> then the program reduces to P0 (storage) and
  P3 (dense kernels) and the MoE lane is closed with receipts. This is a
  legitimate outcome and gets recorded like any other.
