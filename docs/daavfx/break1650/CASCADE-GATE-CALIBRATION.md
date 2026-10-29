# CASCADE-GATE-CALIBRATION.md - the paper kill switch for the model cascade (paper rung, zero box time)

Date: 2026-10-28. Candidate (external-angles-audit.md row 1): a 0.5B answers
everything from VRAM (the 74.77 t/s receipt, 01-MEASURED-FACTS.md:44), a
confidence gate escalates hard queries to the 4B split-offload (the 18.9 t/s
class). The candidate's own kill switch was free: calibrate on paper over the
existing 21-card corpus before any GPU minute. This file is that calibration.

## The size ladder on this bench family (llm_bench_v1.2 cards, runs in runs/)

| Size | Model | Residency | MCP | Calls | Turns | Fidelity | Goal | Acc | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 0.23B | LFM2.5-230M-Q4_K_M | CPU 8k | no | 0 | 30 | 0 | F | 0 | fail: 30 turns text, zero JSON-RPC |
| 0.35B | LFM2.5-350M-Q4_K_M | CPU 8k | no | 0 | 1 | 0 | F | 0 | fail: emitted YAML-ish, quit |
| 1.2B | LFM2.5-1.2B-Q4_K_M | CPU 8k | yes | 2 | 2 | 0 | F | 0 | fail: hallucinated a connection failure, quit in 25s |
| 2B | qwen3.5-2b-q4km | CPU 8k | yes | 30 | 30 | 2 | F | 0 | worker-: pressed the right button, repeated one wrong arg 18x |
| 2B | Ternary-Bonsai-2B | CPU 8k | yes | 1 | 1 | 1 | F | 0 | fail: invented a shell tool, quit |
| 4B | frognano-4b-q4km | CPU 8k | yes | 37 | 30 | 1 | F | 0 | worker: best file-hunting, never found the tester API |
| 4B | gemma-4-E4B | dGPU ngl40 | yes | 7 | 30 | 1 | F | 0 | worker: wrong execution path, 1600-tok rambles |
| 4B | qwen3.5-4b-q4km | dGPU 16k | yes | 12 | 30 | 0 | F | 0 | worker: explores, cannot architect the workflow |
| 4B | qwen3.5-4b-q4km | CPU 8k | yes | 29 | 22 | 8 | TRUE | 10 | COMPLETE: exact sealed values, 2211s (the champion) |

Quality axis (12-task harness): qwen3.5-4b baseline 8/12 (23/28 checks).

## What the ladder says

1. No model under 2B completed a single spec item on this task family. The
   1.2B failure is catastrophic, not graceful: it fabricated a connection
   failure that never happened (the honesty-scoring event of the corpus).
2. The 2B tier reaches worker- (30 calls, right tool, one wrong argument).
   The drop from 2B to 1.2B is a cliff, not a slope.
3. The 0.5B tier - the cascade's proposed fast tier - has NO agent card in
   this corpus. Its only receipt is speed (74.77 t/s, MASTER_REPORT) with no
   agentic evidence at all. It sits below the 1.2B cliff edge.
4. Placement correction carried from the audit: the 4B measured 3.76 GB
   alone, so both-resident is impossible on this card; the slow tier is the
   existing 18.9 t/s split config (experts on CPU/DDR4).

## The calibration verdict

For the MT5-agent task family the cascade as proposed is DEAD as a speed
play. The escalation trigger would fire on nearly every agentic turn
(predicted >90%), so the "cheap tier answers most turns" premise fails on
this box's own receipts. A 0.5B-first cascade only makes sense for turns that
are not agentic, and this bench is nothing but agentic turns.

## The premise moved under it today (2026-10-28)

LFM3-1.7B-Q4_0 measured on the same card: ~57.5 t/s sustained decode,
full-VRAM (0.98 GB weights), quality 7/12 vs the 4B's 8/12. That collapses
the cascade's reason to exist: the fast tier is now the 1.7B itself, and the
quality gap to the 4B is one task. The surviving shape is a two-server
same-family cascade, not a 0.5B cascade:

  LFM3-1.7B answers first at ~57 t/s; low-confidence turns escalate to the
  qwen3.5-4b split (18.9 t/s).

Its gate is the same paper question, now with data: over the LFM3 MT5
transcript, what fraction of turns would the 1.7B have answered within
tolerance. The probe that would have priced it is recorded in
LFM3-CANDIDATE.md (protocol failure - see there).

## What stays free (paper rung, next)

- Draftable-fraction ledger (spec-decode sizing) from on-disk transcripts.
- The two-server cascade probe rides the already-registered G-3d window.
- Digital-twin calibration (nov_angle candidate 1).

## Receipts

- Cards: `...\llm_bench\scores\*.json` (21 files), runs `...\llm_bench\runs\`.
- Quality ledger recomputed from `scripts\daavfx\quality-harness\results\score-*.jsonl`.
- Speed receipts: 01-MEASURED-FACTS.md:44 (74.77 t/s 0.5B); LFM3 E0 in
  LFM3-CANDIDATE.md (this wave).
