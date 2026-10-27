# 12-OUR-PLAN - the reasoning program (no-disable edition)

Operator directives binding this plan:
1. Disabling reasoning is NOT a solution. It is banned as a fix. It appears
   here only as the CONTROL ARM of a measurement (the ruler), never the
   answer, and only ever A/B'd against quality keeping the smart part.
2. Reasoning has a purpose (research/01, research/02). We make it cheaper,
   smarter, or better reused - never absent.
3. Minor ideas accumulate. The plan is a pile of composable mechanisms.

## The current stack of costs (measured, `08-THINKING-DEEP-DIVE.md`)

thinking generation 77-79% of completion tokens; prefill 5.9x the completion
(104,499 vs 17,803 prompt tokens on qwen3.5-4b r2); the MT5 catalog resend
30 times; prefix reuse defeated by history omitting the reasoning.

## The experiments (ranked by value / risk)

| # | Experiment | Mechanism | Cost | Status |
|---|---|---|---|---|
| R1 | **prefix fidelity in the driver** | append reasoning to the rendered assistant turn so the KV prefix matches; measure per-turn prefill time before/after | one driver change + one bench run | needs green |
| R2 | **persistent-session proxy** | thin local proxy: one llama.cpp request held open, turns sent as increments; prefill becomes O(delta) | small build + bench run | needs green |
| R4 | **repeated-run thinking reuse** | at temp 0 the thinking of identical prompts is deterministic - A/B the harness rerun for thinking reuse (research/05's request-specific logic inverted for our deterministic case) | harness-level | needs green |
| R5 | **restatement measurement** | per-turn overlap(reasoning tail, answer head) across our existing transcripts; then a tightened reply format | pure analysis | ready now |
| T-A | **draft the thinking** | spec-decode over reasoning segments on the iGPU theater (50 ns dispatch, UMA reads) - acceptance rate on boilerplate reasoning is the whole game | 1-2 days | the flagship |
| T-B | **iGPU drafting theater** | drafts concurrent with dGPU verify over shared memory | after T-A | |
| T-C | **budget curve (ruler)** | measure the price/value curve of reasoning length (quality vs tokens) so every other lever can be priced - NOT to set a permanent cap | analysis + runs | |
| T-D | **two-model thinking** | 0.5B (74 t/s) plans, big model executes | parallel track | |
| ThinKV tier | thought-importance-graded KV (research/06) | attention-sparsity classification -> per-thought precision/eviction | after R1/R2 prove | |

## Why nothing here disables anything

Every lever either (a) removes OUR waste (prefill, catalog resend, prefix
divergence, restatement) or (b) makes the model's own work cheaper to
execute (drafting, theater splitting). The thinking itself is never removed -
if the measurement ever shows a case where a task class genuinely does not
need it, that is a per-task-class finding, recorded with the receipt, not a
global switch.

## Falsification

The pile dies if: (1) R1/R2 show llama.cpp's prefix matching never triggers
even with byte-identical prefixes, AND (2) T-A acceptance on reasoning
boilerplate stays under ~0.4, AND (3) R5 restatement overlap is under 10% -
then the 77% is irreducible at the serving layer and the only remaining lever
is training-time (CoT compression / distillation, the operator's own trained
models). That outcome is recorded, not argued.
