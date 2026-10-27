# 1e - router concentration curves and the capture-channel verdict

Batch 1 item 1e, zero-GPU. Scope per the auditor's correction: CURVES ONLY -
the transition statistic is deferred to the capture window (the captures are
aggregate histograms with no time axis; `tokens` is a repeated denominator,
not a row index - verified on all four CSVs).

## What exists on disk (all four captures, shape-verified)

| File | Rows | Shape | Selections | mass_selected | mass_all |
|---|---|---|---|---|---|
| router-q2xl-initial.csv | 704 | 22 layers x 32 experts | **394** | 186.88 | 9071.01 |
| router-q3xl-full.csv | 10240 | 40 layers x 256 experts | **0** | 0 | 4642.81 |
| router-q2xl-mt5-32k.csv | 9728 | 38 layers x 256 experts | **0** | 0 | 4209.62 |
| router-q3xl-mt5-32k.csv | 9728 | 38 layers x 256 experts | **0** | 0 | 4472.46 |
| phase3b hist-armB.csv (old tree) | 704 | 22 x 32 | 227,240 | 93,122 | - |
| phase3b hist-multighost16-cpu.csv | 704 | 22 x 32 | 287,284 | 100,342 | - |

## Finding 1 - the selection channel is dead post-merge only

Identical bridge callback code; the pre-merge tree captured six figures of
selections, the merged tree (two different builds, four captures) captured
zero across 30,080 rows while the probs channel (mass) flows normally. The
graph changed at the merge (`src/llama-graph.cpp:2309-2312`): `selected_
experts` is now a VIEW of the argsort, and the full sorted order is emitted
separately as `ffn_moe_group_topk` / `ffn_moe_argsort`. The bridge's
ask-gate on the view path is what silently stops observing. Repair =
observe the argsort tensor (EXP-2 in `EXPERIMENTAL-AUTOTUNE.md`); this is
strictly an upgrade when it works - the full sorted order, not the k-slice.

## Finding 2 - the verdict-grounding capture is topologically impossible

The pre-widen guard in the binary that produced router-q2xl-initial.csv
(`git show 2c962baf1:src/daavfx_dspark_bridge.cpp:96` - `il >= 24 || W < 1
|| W > 32 -> return`) would have skipped ALL probs capture on a 256-wide
tensor. A Flint Q2 run (expert_count = 256, verified from the GGUF header)
would have produced an EMPTY file. The file has 704 rows with non-zero mass
and 394 selections (~4 tokens of routing against its own tokens column).
Its shape matches LFM2.5-8B-A1B (24 blocks / 32 experts, expert_used 4,
verified from its header) - 22 MoE layers in the 2..23 span. The capture
therefore cannot have come from the model it was committed as evidence for.
This is the receipt that retroactively supports the project's existing hold
on the Flint surgery verdict, with a reason: not "insufficient" - WRONG
SOURCE-COMPATIBLE SHAPE, and ~4 tokens of routing at that.

## Curves (what the surviving data supports)

Mass-basis concentration from the one full-topology capture
(router-q3xl-full.csv; mass_all is captured, selections are not):

- selection-basis curves: NOT COMPUTABLE until EXP-2 repairs the channel
- mass-basis curve: computable now; computed per-layer mass concentration
  against the 1c sufficiency certificate, stored next to the CSVs in the
  results folder by the capture manifest (EXP-1)
- the coupon-collector sufficiency of the surviving 394-selection capture:
  already computed by the 1c calculator: INSUFFICIENT (S=394 vs required
  S=36,045 against N=12,032)

## Substrate gap

The three LFM temp-0/0.2/1.0 router traces (the planned transition-stat
workload) never landed: harness responses exist (12/12 x 3 temps in
`quality-harness\results\responses-lfm-t*.jsonl`) but the router-traces
output dir is EMPTY. Root-cause candidates recorded for the capture window:
env inheritance into the spawned server process, and the dead selection
channel (Finding 1) - the flush may have written rows with no selections and
then been overwritten or lost. The capture window (EXP-2) settles both.

## Verdict

The concentration-curve question is SUBSTRATE-BLOCKED, not answered.
Sequencing for the capture window: EXP-2 (repair + rebuild) -> EXP-1
(manifest) -> one capture with a known model (LFM2.5 first, it has the
proven full-capture baseline) -> then curves, then the transition stat.
All of that is one gated capture, no bench hours.
