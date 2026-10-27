# 1a - Contradiction resolver: the false 0.14-0.39 t/s Flint prefill constant

Batch 1 item 1a. Zero-gate: derived entirely from logs already on disk. The
constant this re-derives falsified is the one that killed the Flint lane:
"At `-ngl 10` the model loads and generates but at 0.14-0.39 t/s prompt
processing" (delivered with the Flint X-ray, 2026-10-24; quoted in
`01-MEASURED-FACTS.md` and `moe-lab/FLINT-CAMPAIGN.md` as the speed verdict).

## The evidence (llama.cpp's own slot timings)

Source: `scripts\daavfx\results\server-flint-Q2_K_XL-20261023-183511.log.err`
(the Q2 quality-phase server of the Flint sweep, 17,710 bytes). llama.cpp
prints `slot print_timing` per completed request with prompt-eval and eval
rates. All eleven requests, in order:

| # | task | prompt eval | eval (tg) | total time | tokens |
|---|---|---|---|---|---|
| 1 | 0 | 0.69 t/s (15 tok) | 0.47 t/s | - | ~115 |
| 2 | 133 | **0.44 t/s** (27 tok) | 1.00 t/s | 141.8 s | 108 |
| 3 | 217 | **0.27 t/s** (22 tok) | 0.43 t/s | 156.4 s | 55 |
| 4 | 254 | 1.02 t/s (24 tok) | 1.64 t/s | 145.8 s | 225 |
| 5 | 458 | 1.52 t/s (17 tok) | 3.16 t/s | 91.8 s | 273 |
| 6 | 716 | 3.72 t/s (34 tok) | 6.68 t/s | 27.3 s | 156 |
| 7 | 840 | 5.40 t/s (30 tok) | 7.27 t/s | 13.5 s | 89 |
| 8 | 901 | **13.88 t/s** (29 tok) | 7.72 t/s | 12.1 s | 107 |
| 9 | 981 | **11.11 t/s** (29 tok) | 7.84 t/s | 31.8 s | 259 |
| 10 | 1213 | **14.47 t/s** (30 tok) | 9.15 t/s | 13.6 s | 136 |
| 11 | 1321 | **11.95 t/s** (17 tok) | 9.21 t/s | 29.1 s | 273 |

(The `prompt processing, ... / X tokens per second` continuation lines are
the same requests mid-flight; the `prompt eval time = ...` summary lines are
the totals used above.)

## The resolution

**The 0.14-0.39 t/s figure is a cold-start reading, not a steady-state
property.** The server was cold from a multi-GB mmap load (page cache cold,
Vulkan pipeline and descriptor cache warming, MoE cache un-primed). The
first requests run 0.27-0.69 t/s pp with 141-156 s totals; by the eighth
request the same server delivers **11.1-14.5 t/s prompt-eval and 7.7-9.2 t/s
generation** - the same order as LFM2.5-8B's 18.9 t/s split, on a model 2.5x
its size. The acceleration across the session is ~20-50x.

**Consequences that re-price the lane:**

1. The Flint "speed killed it" verdict is withdrawn. The bench-config
   steady state is ~9 t/s tg / ~12 t/s pp, and the lane's real enemy is the
   warm-up cost (the first 3 requests costing 141-156 s each), which is an
   io_engine (P0) problem - exactly what the loader lane exists to fix.
2. The warm-up curve is the missing constant the lane needed: per-request
   latency improves ~10x within one 12-task session, so a bench that runs
   the same model twice (as our A/B harness does) pays the warm-up once.
3. The 32k MT5 bench rerun (the pending dual-axis test) was cancelled on
   this constant. Re-derived, it becomes worth running: a ~9 t/s tg model
   with a 32k ctx can drive 30 turns.

## The second finding (the confound that rode along)

The harness responses for the same sweep show timeouts:

| Run | answered | timed out |
|---|---|---|
| Flint Q2_K_XL | 10/12 | 2/12 |
| Flint Q3_K_XL | 6/12 | 6/12 |

First-request totals of 141-156 s exceed the harness HTTP timeout, and the
harness records the aborted request as a failed task. The published quality
scores (Q2 9/12, Q3 5/12) are therefore **partially confounded** - they
measure (warm-up race) as much as (model capability). The Q2-vs-Q3 quality
difference is not established. Re-scoring requires a harness timeout sized
to the warm-up curve (>=300 s), at one bench run of box time.

## What lands in Batch 2 (proposed edits, pending operator stamp)

- `01-MEASURED-FACTS.md`: replace the 0.14-0.39 t/s row with the warm-up
  table (cold 0.27-0.69 -> warm 11-14.5 pp / 7.7-9.2 tg), citing this file.
- `moe-lab/FLINT-CAMPAIGN.md`: strike the speed-kill verdict; keep the
  open decisions as open.
- The quality scores stay on record with the confound flag appended until
  the re-score run.

## Receipts

- `scripts\daavfx\results\server-flint-Q2_K_XL-20261023-183511.log.err`
  (llama-server slot print_timing; tasks 0..1321)
- `scripts\daavfx\quality-harness\results\responses-flint-{Q2,Q3}_K_XL-*.jsonl`
  (12 rows each; ok/error fields)
- `scripts\daavfx\results\flint-sweep-20261023-214917.json`
  (`turn_latencies_ms: []` - the bench-side record of the same run is empty,
  which is why the false constant survived unchallenged)
