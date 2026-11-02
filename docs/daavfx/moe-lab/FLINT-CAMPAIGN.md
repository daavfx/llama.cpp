# FLINT-CAMPAIGN - next-model plan for the MoE lab

Date: 2026-10-22
Status: PLAN ONLY. No build, download, inference, or benchmark has run.
Gated on the operator freeing the PC.

## 1. Why Flint is the next test

Flint is a 39.8B total / ~2.5B active MoE with 256 routed experts per layer
(6 routed + 1 shared per token). That is a much wider expert space than
LFM2.5's 32 experts, and it is the exact shape the lab's thesis needs to test:

- LFM taught us that a load-balanced router has no cold tail, so blind expert
  amputation dies at a capacity cliff.
- Flint asks whether 256 experts create a real cold tail, or whether the same
  balance law holds at 8x the width.
- Flint also has enough public quality (Terminal-Bench, SWE-bench) that a
  small local quant can be judged against a known reference, not only against
  our 12-task harness.

The lab does not assume the LFM answer transfers. Every claim below is a
hypothesis with a cheap falsifier.

## 2. Hypotheses and falsifiers

| ID | Hypothesis | Cheap falsifier |
|---|---|---|
| H1 | Q3_K_XL runs at 5-10 t/s on the split (CPU experts + 4 GB Vulkan) | One 128-token generation; if under 2 t/s, the lane is not usable |
| H2 | The 4 GB card cannot hold even Q2_K_XL fully; split is mandatory | Load Q2 with `-ngl 99 -ncmoe 0`; OOM confirms |
| H3 | `--moe-cache-mib` helps only when the working set fits; a 4 GB card needs 512-1024 MiB, not 4096 | Load with 4096; OOM or WDDM paging confirms 4096 is not viable and the 1024 default is the safe start |
| H4 | `GGML_VK_ASYNC_USE_TRANSFER_QUEUE=1` still helps on Flint | A/B one prompt with and without; keep only if generation rises without quality loss |
| H5 | Flint's router is load-balanced like LFM's | Router histogram over 200+ prompts; if selection share is flat, no cold tail |
| H6 | Q2 is a quality cliff, Q3 is usable, IQ4 is the ceiling | 12-task harness plus MT5; reject any quant that fails the MT5 ground truth |
| H7 | Flint can drive the MT5 MCP task | Full 30-turn run; any wrong `run_backtest` args or missing completion fails |

## 3. Phase plan

### Phase 0 - build and load (gated)

1. Build the merged worktree with `build-flint-llama.ps1`.
2. Verify `llama-server --version` lists `flint`.
3. Download only Q2_K_XL first; the fetch selector handles split shards.
4. Load test on port 8083 with `-c 8192`, `-t 6`, `-ncmoe 24`,
   `--moe-cache-mib 1024`, `GGML_VK_ASYNC_USE_TRANSFER_QUEUE=1`.
5. Record load time, peak RAM, peak VRAM, and the exact command.

Stop if the model does not load or if the box needs a page-file increase that
the operator has not approved.

### Phase 1 - quality and MT5 baseline

1. Quality harness, 12 tasks, three runs at the on-spec sampling.
2. MT5 task through `run-flint-bench.ps1`, full 30-turn cap, 4096 max
   tokens (raise only after a load test).
3. Compare with the existing qwen3.5-4b full card and the sealed MT5 truth.
4. Record every tool call, turn, reasoning length, and failure class.

Acceptance for Phase 1:

- At least one full MT5 completion, with the sealed values within tolerance.
- Quality harness at or above the best small-model card, or a clear diagnosis
  of why Flint fails where the small model passes.

### Phase 2 - quant ladder

Run Q3_K_XL, then IQ4_XS if RAM allows. Keep Q2 as the speed reference.

For each quant record:

- model size, load time, peak RAM, peak VRAM
- pp512, tg128, and the MT5 wall clock
- quality score and MT5 verdict
- cache hit rate if telemetry is enabled

Eliminate any quant that fails MT5, regardless of speed.

### Phase 3 - router and cache science

Only after a quant passes Phase 1:

1. Run the router histogram logger (`DAAVFX_ROUTER_LOG`) over the harness plus
   agent prompts.
2. Run the cache profiler (`DAAVFX_MOE_CACHE_STATS=1`) over the same prompts.
3. Answer: is there a cold tail, or is Flint balanced like LFM?
4. If there is a cold tail, quantify the mass gap before proposing any cut.

No surgery in this phase. Data first.

### Phase 4 - surgery, only if Phase 3 earns it

The LFM destruction budget applies:

- F1 amputation only if a cold tail exists and the mass gap is large.
- F2 ghost merge only if clustering shows a real multi-modal group.
- Every mutant must pass the 12-task harness and the MT5 task.
- Keep the quantized mutant as the record; delete f16 intermediates.

If Flint is balanced, close the surgery lane immediately. The LFM result says
blind cuts are a capacity cliff, not free compression.

### Phase 5 - Track B trigger

Track B starts only when one Flint quant passes MT5 and beats or matches the
best small model on quality. Use that model as the teacher; do not distill a
model that has not passed the task.

## 4. Metrics ledger

Every row must carry:

- model, quant, file size, SHA or HF revision
- server binary commit and build number
- command line, context, `-ngl`, `-ncmoe`, cache MiB, threads, env flags
- sampling (temp, top_p, top_k, repeat penalty)
- pp512, tg128, MT5 wall clock
- peak RAM, peak VRAM, CPU percent
- quality score, tasks passed, failure classes
- MT5 trades, profit, PF, DD, verdict
- router histogram artifact and cache profile artifact when available

No row without a command line and a binary identity.

## 5. Stop rules

- Stop the quant ladder if two consecutive quants fail MT5.
- Stop the surgery lane if the router histogram is flat.
- Stop the speed lane if the best quant is under 2 t/s and quality is not
  clearly above the small model.
- Stop and report if the box needs more RAM or page file than the operator
  approved.
- Never leave a server or python process running after a measurement.

## 6. Artifacts

- Build: `build_flint\bin\Release\llama-server.exe`
- Models: `...\local_llm\GGUF\llm-collection\21-flint\`
- Quality: `scripts\daavfx\quality-harness\results\`
- MT5: `llm_bench\runs\`
- Router hist: `scripts\daavfx\results\flint\router-*.csv`
- Cache stats: `scripts\daavfx\results\flint\cache-*.log`
- Scoreboard: `docs\daavfx\moe-lab\FLINT-RESULTS.md` (created only after data)

## 7. Open decisions for the operator

1. First quant: Q2_K_XL smoke or Q3_K_XL directly.
2. Context: 8192 for the first pass, or 4096 to protect RAM.
3. Whether a page-file increase is allowed if Q3 needs it.
4. Whether the MT5 pass is mandatory before any quality-only score is reported.
5. Whether Track B starts from Flint or from the current small-model winner.

## 8. X-RAY VERDICT (H2, harness-lane coder, 2026-10-22)

**VERDICT: WITHDRAWN 2026-11-01 - superseded by section 9 below.**

The router histogram (flint-router-log.csv, 705 rows, 22 MoE layers x 32
experts, 8960 tokens sampled via 10 diverse prompts through Q2_K_XL at
-ngl 10) shows:

- **Only 209/704 (29.7%) of (layer, expert) slots were ever selected.**
  The bottom 70% of experts are completely dead.
- **The top 50% of experts carry 100% of selections.** In LFM2.5-8B-A1B,
  the same metric was 50.7% (near-perfect balance). Flint is the OPPOSITE.
- **CV (coefficient of variation) = 2.180** across all slots (LFM was near 0
  for the load-balanced profile).
- Per-layer active experts range from 5/32 to 17/32; even the busiest layer
  leaves half its experts idle.
- The heaviest experts (layer 11/expert 21: 12 selections, layer 18/expert 26:
  11 selections) carry 10x the median.

**What this means for the campaign:**

- LFM2.5 taught us "load-balanced = no cold tail = surgery dies." Flint
  BREAKS that law: the 256-expert architecture creates a real cold tail.
- The surgery lane (Phase 4) is LIVE: amputation and ghost-merge are
  viable paths for Flint, unlike LFM.
- The quant sweep (M4) should proceed: even without surgery, the quant
  ladder determines the usable baseline.

**Caveats (small sample, honest):**
- 8960 tokens across 10 simple prompts; a more diverse workload may
  activate more experts.
- Only layers 2-23 are logged (22 of the model's MoE layers); layers 0-1
  may be dense or not instrumented.
- The Q2_K_XL quant may affect routing vs the full-precision model.
- `selected` counts logging events, not individual token-level selections
  (the logger batches); the exact semantics depend on the DAAVFX_ROUTER_LOG
  implementation.

**Artifacts:**
- Router CSV: `scripts\daavfx\results\flint\router-q2xl-initial.csv` (705 rows)
- Server log: `scripts\daavfx\results\flint-server.log`
- Build: `build_flint\bin\Release\llama-server.exe` (flint worktree)

**Load note:** Q2_K_XL at -ngl 99 OOMs on the 4GB GPU (H2 CONFIRMED).
Partial split at -ngl 10 loads and generates. The "0.14-0.39 t/s prompt
processing" figure quoted here is WITHDRAWN - it was a cold-start reading;
`auditor-ISAYY\batch1\01a` re-derived the same log as 11.1-14.5 t/s pp /
7.7-9.2 t/s tg warm. The X-ray data was collected during those slow
prompts; the router histogram does not require fast inference, only correct
routing decisions.

---

## 9. REVISED X-RAY VERDICT (2026-11-01, derived from the surviving substrate)

The section 8 verdict is withdrawn for two independent reasons.

**Reason 1 - wrong source.** `router-q2xl-initial.csv` (704 rows, 22 layers
spanning 2..23, 32 experts/layer, 394 selections) is the shape of
LFM2.5-8B-A1B, not Flint. Verified by GGUF header read: LFM2.5-8B-A1B has
24 blocks with 22 MoE layers, `expert_count=32`, `expert_used_count=4`;
Flint Q2_K_XL has 49 blocks with 47 MoE layers, `expert_count=256`,
`expert_used_count=6`, `expert_shared_count=2`. A 32-wide capture cannot
have come from a 256-wide model. It also carries 394 selections against a
required 36,045 (`auditor-ISAYY\batch1\01c`), i.e. 1.09% of the topology.

**Reason 2 - the channel that would have fixed it is dead.** Across all
three Flint-shaped captures (`router-q3xl-full.csv`, `router-q2xl-mt5-32k.csv`,
`router-q3xl-mt5-32k.csv`; 30,080 rows) BOTH `selected` and `mass_selected`
are zero. Only `mass_all` (the pre-topk router gate) flows. REPAIR (EXP-2)
is still open. What follows is derived from `mass_all` alone.

### What is still computable, and the answer

Flint's gating is sigmoid (`expert_gating_func=2` from the header), so the
top-6 selection set IS the top-6 gate set. `router-q3xl-full.csv` gives
40 layers x 256 experts x 516 tokens. Dividing `mass_all` by the `tokens`
denominator recovers a mean gate per slot; every slot lands in [0,1], which
confirms the interpretation. Measured:

| Statistic | Value | Reading |
|---|---|---|
| Slots with gate > 0 | 10,236 of 10,236 | **no dead experts** |
| Normalised entropy | 0.801 | 80% of load-balanced |
| Gini of gate mass | 0.668 | moderate |
| Top-6 of 256 carry | 45% of gate mass (uniform = 2.34%) | 19x enriched |
| Slots for 95% of gate mass | 6,871 of 12,032 (67%) | long tail, not absent |

**This is a third answer, and it splits the lane.** It is neither the
section 8 "cold tail, surgery is live" nor LFM2.5's "load-balanced,
surgery dies":

- **Amputation / ghost surgery: DEAD.** You cannot remove 70% of experts
  when all 10,236 slots are alive and the bottom half collectively hold
  55% of gate mass. Removing them removes mass, not fat.
- **Hot-set caching: ALIVE and priced below.**

### Pricing the cache (trust-ledger UNVERIFIED row 1)

Expert size = 3 x 2048 x 512 params = 1.07 MB at Q2_K_XL (0.34 B/param,
cross-checked: 13.56 GB file / 39.8 B params). Full expert stream per
token = 47 MoE layers x top-6 = 301.6 MB. LRU simulated over the derived
per-layer gate distribution, 150k draws/layer, 3 layers:

| k per layer | Cache | Hit rate | MB/token read | GB/s @ 18.9 t/s |
|---:|---:|---:|---:|---:|
| 32 | 1.61 GB | 29.6% | 212.3 | 4.01 |
| 64 | 3.22 GB | 43.4% | 170.7 | 3.23 |
| 96 | 4.83 GB | 56.1% | 132.4 | 2.50 |
| 128 | 6.43 GB | 67.6% | 97.7 | 1.85 |

Three consequences:

1. **The cache pays for itself ~10x.** Over a 516-token session a layer
   issues 6 x 516 = 3,096 reads; at k=64 across 47 layers each cached slot
   is re-served ~21 times, against a breakeven of 2 reads.
2. **It does NOT convert the bandwidth wall into a cache-hit wall.** At the
   box's real VRAM budget (k=64 = 3.22 GB, i.e. the GTX 1650's usable
   ~3.1-3.4 GB) the residual requirement is 3.23 GB/s - 16x the HDD's
   0.2 GB/s ceiling. The cache is necessary but not sufficient; it needs
   P0's io_engine beside it.
3. **The two lanes are coupled.** The P0 io_engine is the lane currently
   funded by the 1000x-wrong unit error fixed in `04-LOADER-DEEP-DIVE.md`.
   Fixing that fix and landing this cache are the same bet.

**Caveat (stated, not hidden).** These are UPPER BOUNDS. `mass_all` is a
token-averaged gate, so top-6 here is the top-6 for the average token; real
per-token selection carries more variance, which strictly lowers hit rate.
An i.i.d. proxy also ignores temporal correlation in routing. Upper bound
is the correct direction for a green-window call: if the ceiling at real
VRAM is 43%, better capture data cannot rescue the lane.

### What this settles and what stays open

- SETTLED: trust-ledger UNVERIFIED row 1 no longer needs its "~1 h,
  CPU-light" Glider #2 run - it is answered above from data on disk since
  2026-10-23. EXP-2 remains open for the transition statistic (the
  `tokens` column is a repeated denominator, not a row index, so no time
  axis exists in these files).
- OPEN: EXP-2 (repair the argsort observation) for per-token selection and
  the transition statistic; the 49k-ctx LFM3 re-run.
