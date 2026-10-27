# 01-MEASURED-FACTS - every number, with provenance

Rule from README: numbers here were produced by instrument runs with command
lines and binary identities. Class per `02-TRUST-LEDGER.md`:
[V]=verified, [A]=archive-verified, [F]=falsified, [U]=unverified.

## E0 - the GPU datasheet (probe: `shared\daavfx-vk-probe\daavfx_vk_probe.c`, exe build 2026-10-24; raw Vulkan, no layers except the two interloper kill switches)

| Metric | GTX 1650 (dGPU) | Vega 7 (iGPU) | Notes |
|---|---|---|---|
| PCIe pinned copy H2D | **13.3 GB/s** (256 MB, 8x32 MB disjoint) | **15.5 GB/s** | Gen3 x16 healthy on dGPU; iGPU copies go through its DMA to host |
| PCIe pinned copy D2H | **13.1 GB/s** | **15.0 GB/s** | |
| FP16 FMA achieved | **3,179 GFLOPS** | **1,436 GFLOPS** | naive dependency-chained kernel; dGPU ~53% of ~6 TFLOP theoretical; iGPU via old AMD driver's fp16 shader path |
| INT32 MAD achieved | 1,583 GIOPS | 167 GIOPS | DP4A-class proxy; the iGPU's INT path is weak on the 1.2 API driver |
| **Host-visible in-shader read** | **1.4 GB/s** | **4.8 GB/s** | THE verdict numbers: zero-copy streaming is 3.4x better on the iGPU but still loses to plain copies (15.5/13.3) on BOTH - in-shader host reads are not a viable expert-streaming lane |
| dispatch overhead | 178 ns | **50 ns** | per empty dispatch, 2000 in one submit |
| shaderFloat16 | **1** | 1 (feature bit set; some fp16 pipelines rejected by driver) | the FP16 2x-rate lane is real on both cards |
| queue warmup | **0 ms** (bare exe) | 0 ms | the ~100 s first-submit stall is NOT a bare-Vulkan phenomenon - it appears inside llama.cpp with the full layer stack; keep the warmup layer for app runs |
| cross-vendor divergence | (see archive) | (see archive) | the two GPUs disagree by 1 ULP on atan2 bit patterns [A] |

P8 note: these numbers were taken under load; the card idles P8 (300/405 MHz)
and clock state rises under sustained work. Any dGPU number should be
recorded with the clock/state context.

## Storage (probe: `shared\daavfx-vk-probe\bench-nvme-floor.ps1`, QD1 + sequential, buffered vs FILE_FLAG_NO_BUFFERING, seeded RNG, against real files on F: and a 1 GB test file on C:, 2026-10-24)

| Drive / media | 4K random QD1 | 1M sequential | Effective |
|---|---|---|---|
| **F: - Seagate ST3000NM0053 SATA HDD (all models live here)** | **~12.0 ms/op** | ~16.7 ms/op | **0.06-0.2 GB/s** |
| **C: - ADATA LEGEND 700 NVMe, 35.6 GB free** | ~0.28 ms/op O_DIRECT, ~0.01 buffered | ~0.28 ms/op | GB/s class measured while the trace chain ran; the ORDER OF MAGNITUDE vs F: is the durable fact |
| RAM (DDR4-2400 as configured) | - | - | campaign-measured 10.2 GB/s effective on the CPU-split decode path [V] |

Consequence: a CoW/cold model load from F: (4.9-17.2 GB) at HDD speed is
minutes; the operator's PC-slowness complaint during loads is this number.
Co-activation clustering and read-ahead are not optimizations here - they
are the difference between 12 ms and 16 ms per *byte-batch-sized* read.

## Decode/prefill benchmarks (from the bench history, all with command lines and binaries in `llm_bench\runs\`)

### The reference numbers (this box, measured)

| Model | Config | Result | Class |
|---|---|---|---|
| Qwen2.5-0.5B Q4_K_M | llama.cpp, GPU | **74.77 t/s** | [A] MASTER_REPORT's own llama.cpp tables |
| Qwen2.5-0.5B Q4_K_M | CPU | 198 pp / 4.96 tg | [A] |
| LFM2.5-8B-A1B Q4_K_M | **split `-ngl 99 -ncmoe 24 -t 6`** | **18.9 t/s gen, 111.8 pp** | [V] campaign |
| LFM2.5-8B-A1B Q4_K_M | + `--moe-cache-mib 1536` + `GGML_VK_ASYNC_USE_TRANSFER_QUEUE=1` | 14-17.5 t/s at ~0% CPU | [V] campaign |
| LFM2.5-8B-A1B Q4_K_M | HETERO (historical) | 17.39 t/s | [A] MASTER_REPORT |
| LFM2.5-8B-A1B quality | 12-task harness | 8/12 baseline, 9/12 at guided K=28 | [V] campaign |
| GPU speedup over CPU (0.5B) | - | **12.3-15.7x** | [A] |
| qwen3.5-4b Q4_K_M (agent bench) | GPU assist ngl 600, 16k ctx, 3.76 GB VRAM | **10.2 t/s effective** over 30 turns; CPU run was ~90-100 s/turn vs GPU ~40-55 s/turn | [V] bench card |
| Flint Q2_K_XL (12.63 GB) | split, quality harness | **9/12 tasks, 20/22 checks** (best in the collection) | [V] 2026-10-23 |
| Flint Q3_K_XL (17.22 GB) | split, quality harness | 5/12 | [V] 2026-10-23 |
| Flint Q2_K_XL MT5 agent bench | -c 8192 (stock) | **invalid config**: catalog+dialogue grows to 14.5k tokens > 8192 ctx; every request rejected pre-inference, 0 tokens processed | [V] server log: `request (14519 tokens) exceeds the available context size (8192 tokens)` |
| K2-Horizon-7B Q4_K_M | 2 bench versions | 0 parseable actions in 60 turns - DROPPED | [V] |

### The campaign's falsification ledger (all negative results, kept - from `docs\daavfx\moe-lab\RESULTS.md`)

| Idea | Verdict | Evidence |
|---|---|---|
| Blind index-half expert amputation | REJECTED | 1/12 vs 8/12 baseline |
| Guided per-layer amputation | useful to K=24 | 9/12 at K=28; cliff at K=16 |
| Single-centroid ghost | REJECTED | fill ratio 0.005 |
| Multi-ghost clustering | REJECTED (quality) | fill 33x better, quality unmoved (3/12) |
| ngram spec-decode on CPU split | REJECTED | 1.9-8.4 t/s; verification doubles expert bytes |
| LK-2 ring-distance eviction | REJECTED | 7-10 vs 14-15.6 t/s (LRU+async) |
| Per-layer cache class policy | REJECTED pre-implementation | reuse profile flat (57-79%) |
| LK-0 config advisor | REJECTED by arithmetic | 17.5 t/s static baseline wins |
| Zero-copy host-mapped full model | REJECTED | loader crash (4.8 GB host-visible) + byte ceiling |
| **Async transfer queue** | **ACCEPTED** | **12.0 -> 16-17.5 t/s (+40%), zero code** |
| zero-copy in-shader reads (both GPUs) | REJECTED on measurement (this program) | 1.4 / 4.8 GB/s vs 13.3/15.5 copy |

### The thinking tax (the operator's observation, [U] - to be measured in P1)

The harness already records `reasoning_chars` per turn and the taskset notes
v2 budgeting raised max_tokens because "LFM2.5 spends tokens on
reasoning_content before the answer lands in content". No number exists yet
for the wall-clock fraction of thinking vs answer on this box - P1 Phase 0
computes it from existing transcripts.

## Platform facts recorded (no directive implied)

- RAM configured at DDR4-2400 (mixed sticks); operator declined BIOS changes.
- The 1650 idles P8 (300/405 MHz) and ramps under load; clock state was
  recorded, never changed (no `-lgc` performed without asking).
- The iGPU is only half the dGPU's measured FLOPS - but its host-visible
  in-shader read (4.8 vs 1.4 GB/s), copies (15.5 vs 13.3), and dispatch
  (50 vs 178 ns) all beat the dGPU. The compute job for it is the open
  question the program answers (P2).
