# 05-EXPERIMENTS - the executable register

One hypothesis, one settling test, one gate each. Status as of 2026-10-24.
**Nothing in the "pending" state runs without the operator's green light.**

## Meta rules

- Every run records: command line, binary identity (commit/build), clock/state
  context for GPU work, and the raw artifact path.
- Verdicts land in the trust ledger (`02-TRUST-LEDGER.md`) as
  VERIFIED/FALSIFIED, never "inconclusive-by-argument".
- GPU runs: one at a time; CPU/disk work may run concurrently with GPU work.
- Clean kill discipline after every run (no orphaned servers/scorers).

## In flight (stopped by operator directive 2026-10-25; restart only on green)

| # | Experiment | State | Artifacts |
|---|---|---|---|
| X1 | **Router traces, LFM2.5-8B, temps 0.0/0.2/1.0** - harness responses completed (12/12 x 3 temps) but **the router CSVs never landed** (logger produced nothing; substrate-gap root-cause queued for the capture window) | STOPPED mid-flight; server+chain already killed | `scripts\daavfx\quality-harness\results\responses-lfm-t*.jsonl` (exist); `router-traces\` empty |
| X2 | **iGPU E0 datasheet** (UMA lane: HV in-shader read, copies, FP16, dispatch) | **DONE** [V] - see `01-MEASURED-FACTS.md` | `shared\daavfx-vk-probe\RESULTS-E0.md` |
| X3 | **Storage floor bench** (F: HDD vs C: NVMe, buffered vs O_DIRECT, QD1 vs sequential) | **DONE** [V] | `shared\daavfx-vk-probe\bench-nvme-floor.ps1`, RESULTS-E0 |
| X4 | Flint 32k MT5 benches (Q2+Q3, the real dual-axis verdict after the ctx-overflow config failure) | PENDING - re-justified by 1a (warm ~9 t/s tg); own window (D1) | launcher `tools\launchers\run-flint-benches-32k.ps1` (health-wait 600 s, LlamaServer clobber fixed) |

## GPU window candidates G-1..G-4 (kernel lane; order is law; full text in
`auditor-ISAYY/conclusions/05-gpu-driver-and-cuda-candidates.md` and
`TASK-REGISTER.md`)

| # | Candidate | One settling test | Gate |
|---|---|---|---|
| G-1 | Driver lock: "Prefer No Sysmem Fallback" (WDDM paging collapse has a receipt on this box; flip makes VRAM pressure fail-loud) | re-measure any VRAM-pressure case post-flip; before/after policy stamped | operator green; AFTER the quiet-box 18.9 re-run, BEFORE the A/B - never between baseline and re-run |
| G-2a | CUDA backend build for the merged tree -> `build_cuda/` | `llama-server` boots a Flint/LFM model on CUDA | CPU-only window; INFLIGHT row first; no GPU |
| G-2b | CUDA vs Vulkan A/B on `-ngl 99 -ncmoe 24 -t 6` | pp/tg medians per backend, one GPU at a time, capture piggybacked | the green window, after G-1 |
| G-3a | **Coopmat/capability probe**: enumerate device extensions on the 1650; is `VK_KHR_cooperative_matrix` exposed? | the "no tensor cores (sm_75)" claim settles; gates the dense-2x lane and E2d | ~20-line probe addition; the green window |
| G-3b | Device-local VRAM bandwidth (read/write) - E0's biggest hole | the 74.77 -> 145 target becomes sizeable | the green window |
| G-3c | L2 size + working-set knee: GEMV t/s vs matrix size | where the hot set falls out of L2 | the green window |
| G-3d | Dense 0.5B 145-target probe | the archive's 74.77 claim re-derived on the awake card | after G-3a/b/c |
| G-3e | DP4A INT8 GEMV through the real Q4_K/Q8_0 shader paths | free rider of the A/B | the green window |
| G-3f | HAGS on/off | one variable, both states stamped | if the window holds |
| G-4 | Phase A shader-path audit: `NVIDIA_PRE_TURING` classification paths + the 162 .comp set vs what the backend selects on TU117; top-5 kernel gaps | kernel-state map; zero GPU | pure reads; HOLDING until the operator says start |
| G-5 | Sparse-residency streaming prototype | behind G-4 + G-3b | later window |

Memory OC and gpu-unlock SS poking: banned/excluded per the register.

## P0 - loading (operator priority #1)

| # | Experiment | One settling test | Gate to start |
|---|---|---|---|
| L1 | **Sequential warmer beats mmap** | time-to-first-token x5 reps, LFM2.5 from F:; also counts operator-perceived crawl | green window on F: |
| L2 | **OVERLAPPED engine beats L1** | same on F: and C:; depth sweep 2/4/8/16 | L1 done |
| L3 | **First-token-early** | tokens emitted before full file warm | L2 done |
| L4 | **Cluster layout kills QD1 faults** | page-fault count + post-load t/s | traces exist (X1) |
| L5 | **Manifest beats L4** | end-to-end decode t/s, manifest vs plain | L4 done |

## P1 - the thinking tax (operator priority #2)

| # | Experiment | One settling test | Gate |
|---|---|---|---|
| T-0 | **Thinking-tax analysis** | per-model, per-turn: token share + wall-clock share of reasoning vs content, from existing transcripts (zero GPU) | **DONE** - 77-79% thinking share measured (qwen r2 13,643/17,803; granite 13,530/17,127); see `08-THINKING-DEEP-DIVE.md` |
| T-E | **template toggle** | `chat_template_kwargs: {"enable_thinking": false}` on qwen3.5-4b through the 12-task harness: quality delta vs ~75% token saving | one-line driver change; green light |
| T-F | **bench budget audit** | re-examine the 0-action failure classes as possible `max_tokens` starvation (thinking eats the reply budget) before calling them model failures | analysis of existing runs |
| T-A | **Draft-the-thinking acceptance rate** | spec-decode on reasoning-heavy prompts: acceptance rate + net t/s vs plain decode | T-0 done; harness/spec tooling |
| T-B | **iGPU drafting theater** | same prompts, drafts on iGPU concurrent with dGPU verify; wall clock vs solo dGPU | T-A promising |
| T-C | **Thinking budget curve** | cap reasoning length at 25/50/100%; quality vs tokens | any time |
| T-D | **Two-model thinking** | 0.5B (74 t/s) plans, big model executes; quality vs the single-model baseline | any time |

## P2 - concurrent same-memory expert split (the iGPU's job)

| # | Experiment | One settling test | Gate |
|---|---|---|---|
| P2-1 | **Within-layer expert split, synthetic** | probe harness: same 6-8 expert GEMVs assembled from an LFM router trace, split iGPU/dGPU/CPU concurrently vs solo; wall clock + sync cost | X1 traces (hot-set data) |
| P2-2 | **Layer-level in-engine** | the same split inside llama.cpp's MoE graph (SLRU/moe-cache path), decode t/s vs 18.9 baseline | P2-1 wins |
| P2-3 | **Aggregate-drain ceiling** | measure the real combined read drain against the 28 GB/s arithmetic | P2-1 |

## EXP - experimental (the model-agnostic lane; details in EXPERIMENTAL-AUTOTUNE.md)

| # | Experiment | One settling test | Gate |
|---|---|---|---|
| EXP-1 | capture provenance manifest | **DONE** - bridge writes `<csv>.manifest` (observed width/layer span/selection count/truncated flag) beside every flush; `auditor-ISAYY\batch1\capture-manifest-check.ps1` self-test PASSES (good=ADMISSIBLE, truncated=REJECTED-TRUNCATED, zero-selections=REJECTED-NO-SELECTIONS) | source-only, both trees, no build |
| EXP-2 | topk/argsort capture repair | rebuild, re-capture with a known model, confirm selections > 0 and the shape matches the model | source + CPU-only rebuild + one capture window |
| EXP-3 | layout-driven auto-tune | **PAPER DONE** (`AUTOTUNE-BUDGET-MODEL.md`): signature-driven budget solve calibrates against the LFM measured 0.54 GB/token within 9%; probe sweep remains gated | paper done; probe gated |
| EXP-4 | signature registry | one probe teaches every model in the signature class | after EXP-3 phase 1 |

## P3 - dGPU kernels (the operator's "every idea" lane)

| # | Experiment | One settling test | Gate |
|---|---|---|---|
| E2a | TU117-tiled dequant-GEMV vs stock shader | llama-bench pp/tg on dense layers, identical outputs | green window |
| E2b | concurrent FP16+INT32 dual-issue | E0-style probe on 2 queues; combined vs sequential throughput | green window (E0 extension) |
| E2c | L-Mul in matmul kernel | throughput + bit-agreement vs FP16 FMA | green window |
| E2d | TU117 mma.sync EMULATION (`m16n8k8` f16 fragments) - TU117 is the sm_75 tier WITHOUT tensor hardware, so this is a software path, gated behind G-3a (if coopmat is exposed the coopmat path replaces this row) | 2x vs FMA baseline on a 64^3 tile | green window, after G-3a |
| E2f | clock-state control | every dGPU number with clock context | always |

## Standing decisions recorded (for the auditor)

- RAM 2400 + P8 recorded, not changed (operator directive).
- Model migration to C: (35.6 GB free; LFM 4.9 + Q2 12.6 + Q3 17.2 = 34.7)
  is the operator's disk, the operator's call - the fact is on record because
  L1-L5 change the calculus but not the preference.
- "Doctor with zero-copy reads": measured dead on both GPUs (1.4/4.8 vs
  13.3/15.5) - recorded so no future plan re-nominates heroics.

## Audit gate states (2026-10-26; receipts in `auditor-ISAYY/`)

| Gate | State |
|---|---|
| Batch 0 seal containment | DONE - commit `50b1a6d0` (harness repo, unpushed); auditor passed it receipt-level |
| 1a contradiction resolver | DONE - the 0.14-0.39 pp constant is a cold-start reading; warm is 11-14.5 pp / 7.7-9.2 tg; quality scores confounded by harness timeouts (Q2 2/12, Q3 6/12) |
| 1b trigger compiler | OPEN (A2 in the register) |
| 1c capture-sufficiency | DONE - `capture-sufficiency.py` + report; rejects the 705-line capture (S=394 vs 36,045 required), positive control admits a full capture |
| 1d substrate | DONE - per-token activations NOT-EXISTS; shadow-harness shelved |
| 1e concentration curves | OPEN (A1 in the register; sub-agent infra failure) |
| 1f iGPU pump | DONE - DEAD on paper (K1/K2/K3 receipts) |
| 1g ledger diff | OPEN (A3; propose-first, operator stamp required) |
| Batch 2 register rebuild | OPEN (B2 in the register) |
| Batch 3 capture | OPEN - piggybacks the green window (G-2b / the logger capture) |
