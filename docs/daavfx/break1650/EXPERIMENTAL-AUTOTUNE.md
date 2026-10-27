# EXPERIMENTAL-AUTOTUNE - the model-agnostic lane

Date: 2026-10-26. Status: EXPERIMENTAL - nothing here has run; these are
gated candidates added by the auditor lane after the router-logger findings
(batch1 `01e` receipts). Origin: the operator's question - "we don't need to
know the model, just the blocks, experts, layers, etc".

## What triggered this lane

The router-logger forensics (batch1 `01e-router-concentration-curves` when
written; receipts in this file) established two things:

1. The router capture channel for selections is DEAD on the merged tree
   (0 selections across 30,080 rows from two builds) while the same bridge
   code captured 227k-287k selections on the pre-merge tree. The graph now
   emits topk as a VIEW with a full-argsort sibling
   (`src/llama-graph.cpp:2309-2312`) - observing the argsort tensor is both
   the repair AND an upgrade (full routing order, not the k-slice).
2. A capture can be topo-impossible and still get committed: the X-ray
   verdict that launched the Flint surgery lane was grounded in a capture
   whose shape (22x32) and guard arithmetic (`W > 32` skip) make a
   Flint Q2 (256-expert) source impossible through the binary used.
   A capture must carry its own pedigree.

Both point the same direction: the machinery should be **generic over the
layout**, and the capture should be **self-describing**. Model names are not
information; layout signatures are.

## The layout signature

Read straight from the GGUF header (cheap header read, no load):

```
arch = general.architecture            (flint / lfm2moe / ...)
block_count                            (49 for Flint Q2, 24 for LFM2.5-8B)
expert_count                           (256 / 32)
expert_used_count                      (top-k: 6 / 4)
first_block_dense                      (inferable: layers before the first MoE)
```

Verified against both models on this box (header reads, 2026-10-26):
flint = 49/256/6, lfm2moe = 24/32/4. No other knowledge required.

## Experimental tasks (all gated)

| ID | Task | The angle | Gate |
|---|---|---|---|
| EXP-1 | **Capture provenance manifest**: every router capture writes a sidecar JSON (model id, arch, block/expert counts, layer span observed, total selections, certificate from `capture-sufficiency.py`) next to the CSV | makes a wrong-shape or insufficient capture mechanically inadmissible in review | source-only edit to the bridge flush; no GPU |
| EXP-2 | **Topk/argsort capture repair**: observe `ffn_moe_argsort` (the full sorted order emitted by the merged tree) in addition to (or instead of) the dead topk view; relax the ask-gate host-buffer requirement for the capture path | repairs the dead channel AND upgrades it to full-order routing data | source-only edit; needs a rebuild (CPU-only window) + one capture window |
| EXP-3 | **Layout-driven auto-tune**: given the signature + the measured device profile (E0: FP16 3179 GFLOPS, MAD 1583 GIOPS, copy 13.3 GB/s, HV read 1.4/4.8, dispatch 178/50 ns, VRAM 4 GB) derive a launch policy (ngl layers, -ncmoe split, moe-cache MiB, threads, quant choice, ctx) WITHOUT naming the model; confirm with a short llama-bench probe | the model-agnostic spine the operator asked for | paper first (the budget solve), one green window for the probe sweep |
| EXP-4 | **Signature registry**: one JSON per layout signature on disk (what it is, which policies worked, capture certificates) | the same 24 GGUFs collapse to a few signatures; one probe per signature teaches all models in that class | none beyond EXP-3 phase 1 |

## EXP-3 sketch (the auto-tune shape)

```
inputs:  arch, block_count, expert_count, expert_used, quant bpw
         + device profile (E0 numbers, stamped per clock state)
solve:   moe_bytes_per_token  = expert_used * expert_count * ffn_bpw
         dense_bytes          = (block_count - moe_layers) * dense_bpw
         kv_bytes             = ctx * kv_per_token
         vram_budget          = device VRAM - kv - margin
         policy: keep attention + first-N MoE layers on dGPU, CPU split
                 at the N where moe-bytes-per-token * pp_duty <= vram bw gain
probe:   llama-bench -p 512 -n 64 over 2-3 candidate policies (one GPU,
         one green window, clock stamped)
adopt:   smallest policy that holds >= CPU-split baseline x 1.1
```

For a load-balanced router (LFM) the tuner's answer will look like the
campaign's 18.9 t/s split config; for a cold-tailed one (if EXP-2 ever shows
one) it adds the surgery option. Same spine, no model knowledge.

## Why this is safe to build on paper first

EXP-1/EXP-2 are source edits with a defined verification (EXP-1: inject a
wrong-shape header, confirm the gate rejects; EXP-2: rebuild, re-capture,
confirm selections > 0). EXP-3's budget math runs against numbers already
measured on this box. No box time is required until the rebuild + probe.

## Explicitly not claimed yet

- EXP-3's probe sweep needs a green window (one GPU at a time, clock and
  driver state stamped, per the standing rule).
- EXP-2 does not restore trust in the OLD verdict's data - that verdict is
  already rejected on provenance grounds; EXP-2 only repairs future
  captures.
- Nothing here runs llama.cpp without the operator's per-run green light.
