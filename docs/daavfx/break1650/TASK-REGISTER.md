# TASK-REGISTER - every open task, its lane, gate, and order

Compiled 2026-10-26 from the break1650 plan (`03-THE-PLAN.md`,
`05-EXPERIMENTS.md`, `09-COT-RESEARCH/12-OUR-PLAN.md`) plus the auditor's
conclusions (`auditor-ISAYY/conclusions/03-candidate-scoreboard.md`,
`05-gpu-driver-and-cuda-candidates.md`) and the kernel-lane report.

RULE 0: nothing GPU/CPU-runneous without the operator's explicit green, asked
every time. Rule 1: one variable per receipt, clock AND driver state stamped.
Rule 2: the seal-grep gate runs before any corpus build over
`backtesting_pipeline`.

## STOPPED RIGHT NOW (operator directive 2026-10-25/26)

All llama.cpp execution. The last live item was the LFM router-trace chain
(killed before any later writes). Its router CSVs never landed; the
substrate-gap root-cause is queued for the capture window (G-4/1d receipts).

## Lane map

| Lane | Owner | Scope |
|---|---|---|
| Kernel + probe lane | this program (prepare now, execute per windows) | G-3 probes, G-4 audit, E2 kernels, stop rules |
| Reuse + storage lane (MoE) | this program | P0 io_engine, P1 thinking tax, R1/R2 prefix reuse, loader levels |
| Bench + audit lane | this program | scorecards, trust ledger, doc rot, seal mandate |
| moe-lab lane | archived | closed; instruments inherited |
| Harness lane | operator + coder | Batch-1 report in flight (not landed); seal fix committed `50b1a6d0` (unpushed) |
| App lane | operator | app-lane docs + patches post two must-fixes |

## EXP - the experimental lane (from the router forensics + operator's auto-tune question)

Full text: `break1650/EXPERIMENTAL-AUTOTUNE.md`. Zero-GPU source work first,
one capture window after.
| # | Task | Gate | State |
|---|---|---|---|
| EXP-1 | Capture provenance manifest (sidecar JSON beside every router CSV) + wrong-shape injection test | source-only | **DONE** (both trees + validator self-test PASS) |
| EXP-2 | Topk-channel repair: observe ffn_moe_argsort; relax ask-gate host requirement | source + rebuild (CPU-only window) + one capture | open |
| EXP-3 | Layout-driven auto-tune (paper budget solve from the E0 profile, then a 2-3-policy probe sweep) | paper now; probe in one green window | **PAPER DONE** (AUTOTUNE-BUDGET-MODEL.md calibrates to 9% on LFM); probe gated |
| EXP-4 | Signature registry (a few signatures cover the whole GGUF collection) | after EXP-3 phase 1 | open |

## Phase A - offline, now-preparable (zero GPU, no green needed; HOLDING until the operator says start)

| # | Task | Owner | Gate | Notes |
|---|---|---|---|---|
| A1 | 1e redo: router concentration curves from `router-q3xl-full.csv` (10240 rows, full topology) and the 705-line capture; transitions deferred; LFM-capture-failure root-cause hypotheses | kernel lane | none (pure reads) | **DONE** (`auditor-ISAYY\batch1\01e-router-concentration-curves.md`) |
| A2 | 1b trigger compiler: price the 5.9x prefill monster; test the usage-reporting hypothesis (104,499 = full prompt length, not processed tokens); emit the instrument ask for the capture window | kernel lane | none | **DONE** (`01b-trigger-compiler.md`): 5.9x is a usage-reporting artifact; real processed prefill = 29,225 tok / 554.9s; R1/R2 ceiling is 32% of wall, not 5.9x |
| A3 | 1g ledger diff PREPARED not landed (rows 2/8 -> VERIFIED, count drift) | kernel lane | operator stamp | propose-first law |
| A4 | G-4 shader-path audit: `NVIDIA_PRE_TURING` classification paths + the 162 .comp set vs what the backend selects on TU117; top-5 kernel gaps | kernel lane | none (pure reads); do not touch the coder's files | the kernel-lane report's Phase A, per EXECUTION |
| A5 | Wait for the coder's Batch-1 report | both | - | lands before B1 |

## Phase B - one CPU-only window (green light; safe while the operator works)

| # | Task | Owner | Gate |
|---|---|---|---|
| B1 | G-2a CUDA build: CUDA backend for the merged Flint tree -> `build_cuda/`; CPU-only, no GPU, INFLIGHT row first | coder (first follow-up after their report) | operator says the machine is free for a compile |
| B2 | Batch 2 doc consolidation overlaps: `07-CORRELATED-LANES.md` register rebuild; 1a corrections into `01-MEASURED-FACTS.md` + `FLINT-CAMPAIGN.md`; loader 1000x unit fixes (04:19/21/46); stale ledger counts; harness onboarding statuses; app-lane receipt re-drawer + dash-tolerant patch notes | kernel lane | none (doc edits) |

## Phase C - THE one green window (operator's box free; order is law)

```
quiet-box 18.9 re-run -> stamp ->
G-1 driver flip (No Sysmem Fallback) -> stamp ->
G-3a coopmat/capability probe -> stamp ->
G-3b device-local VRAM bandwidth -> stamp ->
G-3c L2 knee (GEMV t/s vs matrix size) -> stamp ->
CUDA-vs-Vulkan A/B with the Batch-3 logger capture piggybacked -> stamp ->
G-3d dense 0.5B 145-target probe ->
G-3e DP4A through real quant paths (free rider of the A/B) ->
(G-3f HAGS on/off if the window holds) ->
G-4 findings folded into the register
```

Two windows allowed if operator time is short. Memory OC excluded (own
later window). Ad-hoc runs banned: nothing contaminates each stamp.

## Phase D - decide from data

| # | Task | Gate |
|---|---|---|
| D1 | Flint 32k MT5 re-run (the dual-axis test the false constant killed; re-justified by 1a: warm ~9 t/s tg) | own window; one variable per receipt |
| D2 | Batch 2 register lands; 1g lands on the operator stamp |
| D3 | axis C stays quarantined; seal-grep gate before any corpus build over `backtesting_pipeline` |
| D4 | Re-rank prefetch/pump ONLY if the capture reports latency-bound stalls |
| D5 | Kernel experiments ranked by Phase A/B findings: coopmat -> prefill GEMM; then tiled dequant-GEMV (E2a); MMQ int path; sparse-residency streaming prototype behind capture + VRAM-bw; E2b dual-issue; E2c L-Mul last |

## Explicitly banned or excluded

- gpu-unlock SS/firmware poking on TU117: BANNED (irreversible surface;
  reference-only per 00-CONTEXT; card is power-bound at 90 W).
- Memory OC mixed into the A/B: excluded.
- Any Vulkan kernel writing before the capture says latency-bound.
- Disabling reasoning as a "fix": banned (09-COT-RESEARCH).
- Two doc edits without a stamp: banned.
