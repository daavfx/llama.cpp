# 01f - iGPU staging-ring pump: kill switch (paper)

**VERDICT: DEAD (paper).** No configuration of the pump beats the banked copy
path on this box. The pump's own claimed mechanism (iGPU in-shader host read at
4.8 GB/s + 50 ns dispatch) tops out at **2.03 GB/s = 3.8 t/s** on the measured
LFM2.5-8B-A1B traffic - i.e. it would *undo* the banked +40% and land **below**
the 12.0 t/s pre-campaign starting point. Its best arithmetically reachable
configuration (iGPU as a pure DMA engine, no shader at all) tops out at
**7.05 GB/s = 13.1 t/s**, still short of the bottom of the already-banked
14-17.5 t/s lane.

The falsification answer: the pump's mechanism does **not** differ measurably
from the banked `GGML_VK_ASYNC_USE_TRANSFER_QUEUE=1` win. All four of its
mechanism elements already exist and are already enabled. Its only delta is to
relocate the read source from DDR4 to DDR4, which is a no-op.

---

## 1. The candidate, restated as a byte path

"Keep the most-used experts in the Vega 7 iGPU's unified memory, streaming them
to the dGPU through a ring buffer on the transfer queue, in parallel with
compute. The iGPU's 4.8 GB/s host-visible in-shader read and 50 ns dispatch let
it feed the dGPU more cheaply than the dGPU's own PCIe path."

Broken into the bytes that actually have to move, one generated token needs the
active expert weights delivered into dGPU VRAM. Minimum serial stages:

1. read the expert out of the iGPU's unified memory,
2. publish it somewhere the dGPU can see (a ring buffer in host memory, or the
   ring is read in-shader by the dGPU),
3. cross the host/VRAM boundary.

Stage 3 is unavoidable: the dGPU computes at 3,179 GFLOPS only from its own
VRAM, and host-visible in-shader reads on the dGPU measure 1.4 GB/s (already
rejected as an expert-streaming lane).

## 2. The banked capture the pump must beat

`RESULTS.md:59` (the accepted-win row) and `01-MEASURED-FACTS.md:70`:

| Config | t/s | Mechanism |
|---|---|---|
| LFM2.5-8B-A1B Q4_K_M, split `-ngl 99 -ncmoe 24 -t 6` | 12.0 | before the capture |
| + `--moe-cache-mib 1536` + `GGML_VK_ASYNC_USE_TRANSFER_QUEUE=1` | **16-17.5 (+40%)**, ~0% CPU | after the capture |
| MAX SPEED (same, no async) | **18.9** t/s gen / 111.8 pp | production baseline |

The capture is overlap, not a new byte source: a dedicated transfer queue +
semaphore handoff so the host->VRAM copy no longer sits in the compute critical
path. Code: `ggml-vulkan.cpp:13433` (host-src/device-dst copies take
`ggml_vk_get_transfer_ctx`), `:13439` (`ggml_vk_buffer_write_async`),
`:5824-5826` (compute submit waits on `ctx->transfer_semaphore`).

The byte path behind that config is already host-resident experts -> device
"banks": `src/llama-moe-cache.cpp` keeps `l.experts` as host tensors and
allocates `g.banks` (a fixed ring of `n_slots` expert slots) with the device
buffer type, with an LRU and an async fill.

## 3. The arithmetic: per-token byte budget

Two measured campaign numbers fix the byte budget directly
(`01-MEASURED-FACTS.md:31,35`): the CPU split sustains **10.2 GB/s** effective
(compute-mixed) at **18.9 t/s** gen.

    10.2 GB/s / 18.9 t/s = 0.5397 GB per token = 539.7 MB per token

Corroboration from the model file on disk: `LFM2.5-8B-A1B-Q4_K_M.gguf` = 4.8 GB
total, A1B = ~1B active params/token, at Q4_K_M ~4.5-5 bpw that is ~560-625 MB
active. Same order; the 539.7 MB figure is the one used below because it comes
from measurement, not from a size estimate.

Required byte rates to land in each lane:

    banked lane 14.0 t/s  ->  7.56 GB/s   (bottom of the accepted lane)
    banked lane 17.5 t/s  ->  9.44 GB/s   (top of the accepted lane)
    max-speed   18.9 t/s  -> 10.20 GB/s   (the production baseline)

Any byte path that cannot sustain at least 7.56 GB/s cannot reach the bottom of
the lane that is already banked.

Modeling rule used for every row below: for stages in series the steady-state
rate is `1 / sum(1/r_i)`. This is the **optimistic** bound - perfect pipelining,
no resource contention, one dedicated engine per stage. Real configurations are
worse (ring-buffer sync, the iGPU read and the PCIe copy both pulling on system
memory, and the compute that consumes the experts being the actual bottleneck).

## 4. Byte-path comparison table

All rates from `01-MEASURED-FACTS.md` E0 (measured, class [V] on this box):

| # | Path (per byte, stages in series) | Stage rates | Steady rate | Cost per byte | Transfer per 540 MB | t/s ceiling |
|---|---|---|---|---|---|---|
| P0 | **Banked copy path (production)**: host DDR4 -> PCIe pinned H2D -> VRAM. One hop; the 13.3 figure already includes the source read from host memory. | PCIe H2D **13.3** | **13.3 GB/s** | 75.2 ps | 40.6 ms | **24.6** |
| P1 | **Pump as described**: iGPU in-shader read -> host ring write -> PCIe H2D -> VRAM. | in-shader host read **4.8**, host write **4.8**, PCIe **13.3** | **2.03 GB/s** | 492 ps | 265.4 ms | **3.8** |
| P2 | **Pump best case** (iGPU as a pure DMA engine, no shader): iGPU DMA -> host ring -> PCIe H2D -> VRAM. | iGPU D2H DMA **15.0**, PCIe **13.3** | **7.05 GB/s** | 142 ps | 76.6 ms | **13.1** |
| P3 | **Pump zero-copy variant**: iGPU in-shader read -> ring -> dGPU reads the ring in-shader (no PCIe). | iGPU read **4.8**, host write **4.8**, dGPU host read **1.4** | **0.88 GB/s** | 1131 ps | 610.4 ms | **1.6** |
| P4 | **Pump with a free DDR4 front copy**: plain memcpy DDR4->DDR4 at the DDR4 spec rate, then PCIe H2D. | DDR4 **29** (spec, not measured here), PCIe **13.3** | **9.12 GB/s** | 110 ps | 59.2 ms | **16.9** |

Context numbers:

    token time at 18.9 t/s = 52.9 ms   (P0's 40.6 ms fits, and overlaps compute)
    token time at 12.0 t/s = 83.3 ms   (P1's 265.4 ms is 3.2x over this)
    token time at 17.5 t/s = 57.1 ms   (P2's 76.6 ms is 1.34x over this)

Every pump row is compared against P0, which is the same hardware doing the same
job with fewer stages.

## 5. Why no configuration wins

**The pump is P0 plus at least one extra serial stage on an unchanged byte path.**

The decisive physical fact: the Vega 7 is integrated. It has **no dedicated
VRAM** - its "unified memory" is a carveout of the same system DDR4 the host
staging already lives in. The probe's own note confirms it
(`01-MEASURED-FACTS.md:11`): "iGPU copies go through its DMA to host". The
iGPU's 15.5/15.0 GB/s "PCIe copies" are DDR4<->DDR4 through the iGPU's DMA
engine, not bus crossings - there is no bus for the iGPU to cross.

So "keep the experts in the iGPU's unified memory" is a relabeling: the bytes are
already in DDR4, which is what P0 already reads. The pump cannot change where the
bytes come from. It can only insert hops in front of the one PCIe crossing P0
already performs. Stages in series only add cost:

- P1 (the candidate's literal mechanism, 4.8 GB/s in-shader): **3.8 t/s**.
  5.0x over the 52.9 ms token budget. 2.8x below the 12.0 t/s the program started
  from. This is a regression, not an optimization.
- P2 (best reachable, assuming the iGPU does nothing but memcpy for the entire
  decode): **13.1 t/s**. Below the bottom of the banked lane (14.0) by ~7%,
  below max-speed (18.9) by ~31%. And this is the best case with zero ring
  overhead and zero contention.
- P3 (feed the ring straight to the dGPU's shader): **1.6 t/s** - this is the
  zero-copy host-mapped lane, `REJECTED` twice already
  (`RESULTS.md:38,58`; `01-MEASURED-FACTS.md:69,71`).
- P4 (a free DDR4 front copy at spec rate): **16.9 t/s** - still below the 18.9
  baseline, and this row is just P0 with a useless stage bolted on the front.

The one number that looks like an iGPU advantage does not survive contact with
the bus: the iGPU's copies are 15.5 vs the dGPU's 13.3, a +16% edge, but the
pump still has to cross the dGPU's 13.3 GB/s bus afterwards. 15.0 and 13.3 in
series is 7.05 - half of the 13.3 the dGPU's own DMA delivers with no iGPU
involvement at all.

Required-rate check, the cleanest form of the kill: to even *reach* the banked
lane the byte path must sustain >= 7.56 GB/s. The best pump row is 7.05 GB/s
(93% of the requirement, and that is the optimistic bound). The candidate's
actual claimed mechanism is 2.03 GB/s (27% of the requirement). Nothing clears.

## 6. Mechanism diff vs the banked win - the re-claim

| Pump claim | What already exists and is already on |
|---|---|
| "keep the most-used experts in a host-side pool" | the MoE cache's LRU over **host** expert tensors (`llama-moe-cache.cpp`, `l.experts`, `--moe-cache-mib 1536`) |
| "streaming them to the dGPU" | the H2D write (`ggml-vulkan.cpp:13439`) |
| "through a ring buffer" | the cache banks are literally a fixed ring of `n_slots` expert slots (`g.banks`, one slot per expert, LRU eviction) |
| "on the transfer queue" | `device->transfer_queue`, dedicated queue family (`ggml-vulkan.cpp:4878-4889`) |
| "in parallel with compute" | `async_use_transfer_queue` + the transfer semaphore (`:5824-5826`) - **this element IS the banked +40% capture** |

There is no fifth row. The only element in the candidate's description that is
not already implemented is "the pool lives in the iGPU's unified memory", and
that is the DDR4-is-DDR4 no-op from section 5. Two adjacent lanes were already
falsified in the same ledger and the pump re-uses both of their numbers: the
ring-distance eviction variant (`LK-2`, `RESULTS.md:55`: 7-10 t/s vs 14-15.6)
and the zero-copy host-mapped read (`RESULTS.md:38`: loader crash + byte
ceiling).

## 7. The two cited numbers, checked against this program's ledger

**"4.8 GB/s host-visible in-shader read."** Refuted by this program's own E0
notes, twice, before the pump was proposed:

    `01-MEASURED-FACTS.md:15`  "zero-copy streaming is 3.4x better on the iGPU
                                but still loses to plain copies (15.5/13.3) on
                                BOTH - in-shader host reads are not a viable
                                expert-streaming lane"
    `01-MEASURED-FACTS.md:71`  "zero-copy in-shader reads (both GPUs) |
                                REJECTED on measurement (this program) |
                                1.4 / 4.8 GB/s vs 13.3/15.5 copy"
    `RESULTS.md:38-39`         "Zero-copy host-mapped streaming was tested
                                (GGML_VK_PREFER_HOST_MEMORY=1) and the loader
                                DIES on 4.8 GB of host-visible allocation"

The number is real; the conclusion drawn from it is not. 4.8 GB/s is 2.8x
*slower* than the dGPU's 13.3 GB/s PCIe pinned copy, and it does not remove the
bus crossing the pump still needs.

**"50 ns dispatch vs 178 ns."** True as a microbenchmark, irrelevant to a byte
path. The E0 row is "per empty dispatch, 2000 in one submit". Dispatch is
amortized across the transfer size; at 539.7 MB/token it does not enter the
per-byte cost at all:

    even 1000 full dispatches at the dGPU's 178 ns = 178 us
    = 0.44% of the 40.6 ms the P0 transfer already costs per token

The 50 ns advantage is worth at most 128 ns per dispatch, against a 40.6 ms
per-token transfer: noise at four orders of magnitude. And the dispatch/overlap
benefit it is supposed to buy was already banked by the transfer queue. The
dispatch row is a receipt for P0's improvement, restated as if it were a new
mechanism.

## 8. VERDICT and the receipt that kills it

**DEAD (paper).**

Receipt K1 (dominance, the arithmetic kill). The source the pump wants is the
same DDR4 the banked path already reads, because the Vega 7 has no VRAM
(`01-MEASURED-FACTS.md:11`, "iGPU copies go through its DMA to host"). The pump
therefore adds >= 1 serial stage to an unchanged byte path and then crosses the
unchanged 13.3 GB/s bus. Its best reachable rate is 15.0 in series with 13.3 =
**7.05 GB/s = 13.1 t/s**, which is below the 14.0 t/s bottom of the lane already
banked. Its claimed mechanism (4.8 GB/s in-shader) is **2.03 GB/s = 3.8 t/s**.

Receipt K2 (already-captured mechanism). All four mechanism elements are
implemented and enabled: host expert pool + slot ring + transfer queue +
compute overlap (`src/llama-moe-cache.cpp`; `ggml-vulkan.cpp:4878-4889`,
`:13433-13439`, `:5824-5826`). The +40% capture is a single env var with zero
code. The pump re-claims it.

Receipt K3 (its own numbers are pre-falsified). 4.8 GB/s in-shader host read is
`REJECTED on measurement (this program)` at `01-MEASURED-FACTS.md:71`, and the
zero-copy loader dies on the same 4.8 GB host-visible allocation
(`RESULTS.md:38-39`). The 50 ns dispatch term is 0.44% of the per-token transfer
cost even at 1000 dispatches.

Adjacent lane closed by the same arithmetic, for completeness: the iGPU as a
*compute* engine rather than a memcpy engine is not the pump, but the same
budget kills it - 4.8 GB/s / 0.5397 GB = **8.9 t/s** ceiling, below the banked
lane, before accounting for the iGPU's 1,436 GFLOPS being 45% of the dGPU's
3,179. Noted at `01-MEASURED-FACTS.md:87-88` as the P2 open question; the byte
arithmetic already answers it.

## 9. The capture that would have proved it ALIVE

For the record, so the verdict is falsifiable rather than asserted: the single
capture that would revive the pump is a head-to-head on the LFM2.5-8B-A1B
traffic where the pump's byte path (iGPU-side staging -> dGPU VRAM) sustains
>= **10.2 GB/s** while the dGPU decodes, landing **>= 18.9 t/s** with the
transfer lane demonstrably not the bottleneck (i.e. the ring never stalls the
compute submit). That is the bar the production baseline sets, and P0 already
clears it with zero extra stages.

That capture is arithmetically unreachable on this box: the maximum serial rate
available to any pump configuration is the iGPU's 15.0 GB/s DMA in series with
the dGPU's 13.3 GB/s bus = 7.05 GB/s, which is 69% of the 10.2 GB/s the
baseline requires. No amount of ring buffering, queue dedication, or dispatch
cheapening changes a series bound. To get a different answer you would have to
change a measured number - a faster bus, or a dGPU that does not need its bytes
in VRAM.
