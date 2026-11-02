# 04-LOADER-DEEP-DIVE - from stock mmap to an LLM-era layout compiler

The operator's question verbatim: *"the loading of a model happens 100% hdd
to ram/cpu or dgpu? we cant do something there we are following human useles
practices, we have llms we can do the loader as complex as possible to win
speed and whatever we want, thatsd crazy but the type of shit we need"*.

## What happens today (traced end to end)

1. llama.cpp opens the GGUF and **mmaps** it (file-backed pages from F:)
2. weights are *mapped*, not read: first touch = page fault = 4K random
   read on a 7200rpm HDD = **~12 ms each** (measured `bench-nvme-floor.ps1`)
3. copies that llama.cpp needs on GPU happen via the backend's own upload
   (copy engine, 13.3 GB/s) or, for quantized weights, stay mapped and
   dequantized on the fly by the active backend
4. the loader has no idea what the model is about to do - it fetches pixels
   in file order and pays random-fault latency on a disk built for streams

The load of Flint Q2 (12.63 GB / 3,083,497 pages of 4096 B) is up to
**3.08 million random-page faults in the worst case**; at the measured
~12 ms per 4K fault that is **10.3 hours** of worst-case fault time. The
earlier "39 million" figure was 39 million *milliseconds* relabelled as a
count (3,259,424 pages was also wrong: 12.63e9 / 4096 = 3,083,497, and the
old number implied 3,874.92 bytes/page, an impossible granularity).
Sequential staging turns it into one 12.63 GB sweep at **~60 MB/s**
(1 MiB / 16.7 ms = 59.9 MB/s) - about 3.5 minutes, which is the conclusion
the L1 section below already drew, now with the unit stated correctly.
Drive floor for reference: 0.06-0.2 GB/s effective
(`01-MEASURED-FACTS.md`), i.e. the sequential 1 MiB read is the disk's
ceiling, not its random latency.

**So yes: 100% of the bytes come HDD->RAM (page cache), and the GPU gets
what it needs through copies.** The question is whether that path has to be
that.

## The design space, in full

### The byte's five possible fates

| Fate | Bandwidth on this box | When right |
|---|---|---|
| RAM page cache (stock mmap) | free-ish after first read, but **fault latency 12 ms/4K on F:** | tiny models, cold storage of parts |
| Pinned staging in VRAM | 13.3 GB/s (dGPU copy) | weights the next N tokens will stream through |
| VRAM-resident | device-local memory access, no transfer | hot set, dense layers, attention - the parts every token needs |
| Never-landed (in-shader host read) | 1.4 GB/s dGPU / 4.8 iGPU | measured dead for bulk; possibly useful for tiny hot tensors, e.g. router gates |
| Compute-in-place on CPU | 10.2 GB/s effective (campaign) | the CPU-split path that produces our 18.9 t/s today |

The old design decision was "everything to RAM". The new one: **per tensor
class, chosen at load time from a manifest.**

### The loader's five levels (see also P0 in the plan)

**L1 - Sequential warmer (ships first, no fork change).**
Read the entire file into the OS file cache before llama.cpp starts.
Sequential 1M reads: ~16.7 ms each, ~60 MB/s aggregate on this HDD.
Then llama.cpp's page faults hit cache at DRAM speed. A 12.63 GB model goes
from "minutes of random faults" to "about three and a half minutes of
sequential read" + instant service. This is not clever; it is the disk's own
preference expressed as a tool. It also makes the box *feel* sane during
load, which the operator explicitly cares about.

**L2 - OVERLAPPED read engine (kittyhawk io_engine).**
Multiple outstanding reads at tuned depth, `PrefetchVirtualMemory` for the
whole mapped range, a read-ahead thread, and adapter selection by measured
media type:
- HDD/USB: depth 2-4, 1M+ sequential clusters
- NVMe: depth 8-16, 256K-1M chunks
The loader measures the drive once (read pattern probe at startup, like our
bench) and picks its strategy - generic across drive types, which is the
requirement.

**L3 - Content-aware order.**
Parse the GGUF header, extract the tensor table. Layer/attention/dense
weights are needed at token 0; experts are selected probabilistically. Read
order becomes: attention + norms + embeddings + dense (always-land) first,
experts second (streamed or cached by frequency). The first-token footprint
shrinks to a few hundred MB, so **the first token can start before the whole
file is warm** - that is a load-*interaction* redesign, not just a cache one.

**L4 - Co-activation cluster layout.**
From router traces (the 48x256 logger produces exactly this), cluster the
experts that fire together and rewrite the GGUF so clusters are contiguous.
A sequential prefetch of one cluster then covers the whole pre-activation
set of the next token - one sequential read instead of k random seeks.
Build-time tool, zero runtime cost, and the format is deliberately ours
(the operator's RYF/RYW1 "burn GGUF" thread is the extreme version of this;
we start with a re-ordered GGUF so nothing downstream changes).

**L5 - The LLM-era layout compiler (the ceiling of the idea).**
An offline job (runs on any machine, any drive):
1. collect routing traces over the model's real workloads (we have the
   logger; a small local model can also *generate* diverse workloads to
   route-trace)
2. compute per-expert: selection frequency, co-activation graph,
   streaming class
3. emit (a) a re-ordered GGUF (clustered layout), (b) a prefetch manifest
   per drive profile (which tensor ranges to stage, in what order, at what
   depth), (c) a depth_map: hot experts -> NVMe/C: resident; warm ->
   VRAM staging; cold -> HDD position
4. llama.cpp (or our loader) executes the manifest

The manifest is *produced with model assistance* (a small model synthesizes
representative routing sessions; statistics turn traces into order) and
*consumed by a dumb fast loader* - the intelligence lives in the offline
compile, not in the hot path. That is the inversion of how loaders normally
work, and it is the operator's point exactly: "we have LLMs, we can make the
loader as complex as possible."

### Why this is not Strata's design (the operator's no-copy directive)

Strata ships a fixed 3-tier cache with heuristics chosen by its authors. The
layout compiler is the same *physics* (tiered bytes) with the *policy*
learned from this box's traces and compiled per model per drive. No copied
code, no copied constants; every threshold comes from our measurements
(E0 ceilings, storage audit, traces) and is recorded in the trust ledger.

## Measurement plan

| Claim | Test | Metric |
|---|---|---|
| L1 warmer beats mmap on HDD | time-to-first-token, LFM2.5 from F:, warmer vs stock, 5 reps each | seconds + operator-perceived crawl |
| L2 beats L1 on both drives | same on C: and F: | seconds |
| L3 first-token-early | tokens generated before full file warm | time-to-first-token delta |
| L4 cluster layout helps | QD1 faults eliminated vs L1 (count via perf counters) | faults + t/s after load |
| L5 manifest beats L4 | end-to-end decode t/s with manifest vs plain | t/s |
