# 02-TRUST-LEDGER - the RYIUK archive claim classification (copied in full for auditor self-containment)

Source: the four-agent audit of ``local_llm\GGUF\RYIUK`` (2026-10-24) plus
the operator's own kept-verifications and retractions. The canonical copy
lives at ``local_llm\GGUF\RYIUK\TRUST-LEDGER.md``; what follows is verbatim
so this folder stands alone. **This file is why nothing in this program
rests on an unverified claim.**

---
# TRUST-LEDGER - every major RYIUK archive claim, classified by evidence (2026-10-24)

The problem this solves: the archive mixes measured truth, self-retracted
inflation, and never-tested ideas. This ledger labels each one. Sources:
`keep\AUDIT_VERIFIED.md` (the deliberately kept audit), the archive's own
retractions (INT7 correction, `OLD\VS AI LLM\RYIUK EVIDENCE.md` roast,
MASTER_REPORT), the 2026-10-24 four-agent audit, and the fresh E0
instrument measurements (`shared\daavfx-vk-probe\RESULTS-E0.md`).

Status classes:
- VERIFIED  - measured with receipts, reproduced, or consistent with fresh instruments
- FALSIFIED - dead, with the receipt that killed it (do not revive without new physics)
- UNVERIFIED- plausible, never measured; each entry carries the ONE test that settles it

---

## VERIFIED (trust, build on)

| Claim | Number | Evidence |
|---|---|---|
| GTX 1650 FP16 throughput | 13.4 TFLOPS (FP16/concurrent class) | operator's own honest retraction of 116 (INT7 correction); E0 naive-FMA achieved 3.2 TFLOPS - consistent for untuned kernels |
| Vega 7 iGPU sustained | 579 GFLOPS dependency-chained | own correction: "the actual silicon throughput"; the 805 "isolated" figure stays UNVERIFIED |
| Qwen2.5-0.5B Q4_K_M on 1650 GPU | **74.77 t/s** | MASTER_REPORT real llama.cpp tables - the 75 t/s target is real silicon |
| LFM2.5-8B-A1B HETERO | 17.39 t/s | MASTER_REPORT; consistent with campaign's 18.9 split |
| GPU speedup over CPU (small models) | 12.3-15.7x | MASTER_REPORT llama.cpp tables |
| Precision-consumer finding | FFN->Q8_0 = all the PPL gain; attn->F16 = pure cost (tg -28.9%) | MASTER_REPORT measured bench (290 tensors) |
| iGPU 2048^3 matmul | ~2.08 s sustained; dGPU overall 443 ms | primal_bench receipts (phase_a2) |
| Provenance overhead | 2,545x (scalar add 1,936x, matmul64 3,839x) | antihack_math criterion - measured; gate correctly blocks runtime use |
| Cross-GPU atan2 bit divergence | 1 ULP (Vega 1078530010 vs 1650 1078530011) | vulkan_probe_receipt.json, bit-level, 100-run stable |
| GPU compute determinism | identical hash x100 restarts | stress_results.txt |
| Zero-copy in-shader read on dGPU | **1.4 GB/s** | E0 (2026-10-24) - kills in-shader streaming on the 1650 |
| PCIe pinned copy | **13.3 GB/s H2D / 13.1 D2H** | E0 (2026-10-24) |
| FP16 feature bit on 1650 | shaderFloat16 = 1 | E0 |
| CPU-only LLM reality | 4.2 t/s (Mistral 7B Q4, pre-fix 8.3) | INT7 HARDWARE TRUTH table |
| Live trading (A3) | +$235.84, PF 1.2785, 155 trades | keep\A3_LIVE_TRADING_RESULTS.md |
| Container tests | candle 77/77, primal_evolution 100/100, ants 8/8 | keep\AUDIT_VERIFIED.md |

## FALSIFIED (dead, receipts on file - do not revive without new physics)

| Claim | Death receipt |
|---|---|
| 116.54 TFLOPS concurrent FP32+INT32 | own audit: 41x theoretical = impossible; synthetic loop artifact |
| 40,000 tokens/s | RYIUK EVIDENCE.md roast: "measured an empty loop... revving in neutral" |
| 9.7 TFLOPS | compiler pre-calculation artifact (own correction) |
| 272 t/s / COMPETITIVE ADVANTAGE claims | marketing file; its own auditor destroyed it |
| 48 TFLOPS dGPU | "would need INT4" - ghost |
| Provenance arithmetic as a runtime path | 1,936-3,839x overhead; runtime_ready: false by own gate (sampling/audit layer ONLY) |
| Full-model zero-copy host-mapped on dGPU | loader crash + byte ceiling; NOW ALSO: in-shader HV read measured 1.4 GB/s (E0) |
| Blind K=16 amputation | 1/12 quality vs 8/12 (FOUNDRY) |
| ngram spec-decode on the CPU split | 1.9-8.4 t/s, verification doubles expert bytes (FOUNDRY) |
| LK-0 config advisor | dead by arithmetic: 17.5 < 18.9 static (FOUNDRY) |
| Ring-distance eviction | 7-10 t/s vs 14-15.6 LRU+async (FOUNDRY) |
| AMN transformer head | learned to copy the deterministic parser; amputated (ryiuk-core lib.rs) |
| L-Mul claim as-measured-anywhere | never measured at all - lives in UNVERIFIED, not here (no fake numbers were recorded for it) |

## UNVERIFIED - TESTABLE (the ranked list; each with its one settling test)

Ranked by (impact if true) / (cost to test). Items 1-3 need zero training and
zero downloads; the GGUF targets are already on disk.

| # | Claim / idea | The one test | Cost | What our instruments already say |
|---|---|---|---|---|
| 1 | **Hot-expert LRU cache converts the bandwidth wall into a cache-hit wall** (kimi_k3: "the single biggest lever and nobody ships it") | Glider #2: routing-trace LRU simulation on Flint Q2/Q3 + LFM GGUFs - run the FIXED 48x256 router logger over a real session, compute per-layer hit-rate vs cache size | ~1 h, CPU-light | E0 says streaming ceiling 47 t/s IF hot-set concentrates; the router log answers concentration directly |
| 2 | **NVMe O_DIRECT floor on F:** (Glider #1: "this one number decides the floor") | devbw-style 4K/1M sequential+random read bench on the model disk | ~30 min | kimi-k3-in-c measured the bottleneck as QD1 read latency, not bandwidth |
| 3 | **Windows io_engine (OVERLAPPED + PrefetchVirtualMemory) beats mmap for model loads** | prototype loader vs mmap on the same GGUF: time-to-first-token + page-fault count | ~2-4 h build | explains the 5-min loads that make the PC crawl during our benches |
| 4 | **Theater-sharded speculative decoding** (iGPU drafts / dGPU verifies / CPU drafts - "nobody's doing it") | draft k tokens on iGPU+CPU in parallel, verify batch on dGPU; acceptance-rate + net t/s vs 18.9 baseline | ~1 day | our ngram falsification was CPU-split-specific (verification doubled PCIe bytes); sharded drafts change the byte math - re-test is legitimate |
| 5 | **Depth_map precision ladder** (bytes/param inversely proportional to streaming frequency) | Glider #3: depth_map v2 on gemma-4-26B-A4B-Q4 (tool never written; precision consumer already exists in the fork and is benchmarked) | ~half day | MASTER_REPORT already proved FFN-targeted precision works |
| 6 | **Pre-router: predict router output one token ahead to drive prefetch** ("if it works, that's a paper") | logits of layer N-1 MLP-gate vs actual N router top-k: measure predictability (even 60% correct transforms prefetch) | ~half day | the 48x256 router logger produces the ground-truth pairs for free |
| 7 | **Greedy decoding raises prefetch hit rate** ("randomness is a knob") | A/B the router trace at temp 1.0 vs temp 0 on the same session; compare hot-set concentration | ~30 min | bench_driver already has the temperature knob |
| 8 | **UMA zero-copy on the iGPU lane** (iGPU reads DDR4 natively ~40 GB/s; our 1.4 GB/s was the dGPU over PCIe) | E0 probe with DAAVFX_PROBE_DEVICE=0: HV in-shader read on Vega 7 | ~15 min | if Vega reads host memory at 10-20 GB/s in-shader, the iGPU becomes the streaming theater and the dGPU the compute theater |
| 9 | **L-Mul Phase 18** (float multiply = integer add + bit shift; "the final unlock") | implement in one WGSL/.comp matmul kernel; compare throughput + bit-agreement vs FP16 FMA | ~1 day | pairs with the concurrent FP32+INT32 observation; nothing fake was ever recorded about it - it was simply never run |
| 10 | **Concurrent FP32+INT32 dual-issue on Turing** (the kernel of the 116 saga, minus the fake number) | E0-style: FP16 kernel + INT kernel submitted concurrently vs sequential; measure combined throughput | ~2 h | the 13.4 TFLOPS honest number leaves room for dual-issue gains |
| 11 | **Operator-affinity matrix** (dGPU wins FMA/Mul, CPU wins scalar Add, RAM wins Copy, iGPU wins transfer) | 4 ops x 4 theaters x 4 primals, randomized, identical workloads | one afternoon | vulkan_probe receipts already show the theaters diverge at bit level |
| 12 | **Co-activation clustering in GGUF layout** (fire-together experts live together; sequential prefetch grabs clusters) | cluster the E0/router traces, simulate cluster-prefetch vs random on the io_engine prototype | ~1 day | depends on #1 and #2 results |
| 13 | **iGPU 805 GFLOPS isolated** | re-run under locked conditions with the E0 harness | ~30 min | 579 verified; 805 plausible but unmeasured |
| 14 | MIDI/PPM primal experiments (the "emotionally important" pending pair) | the 30-minute benches named in the kimi roast | 30 min | pure curiosity tier - below the line |

---

## The rule that keeps this ledger honest

Any claim may be promoted from UNVERIFIED to VERIFIED only by an instrument
run recorded in the ledger (probe, harness, router logger, or llama-bench
with a command line and binary identity). Any claim measured contradicting
its row moves to FALSIFIED with the receipt. No claim moves on argument
alone - that is the failure mode that put this archive in _MAYBE.

