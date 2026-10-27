# 08-THINKING-DEEP-DIVE - the reasoning-token tax: proof, mechanism, state of the art, our plan

Operator question (2026-10-24): "is it proven it consumes tokens and speed
right? theres no other solution? what internet says? whats a popular name to
this besides thinking? how the llm architecture does this and where, how why?"

Answer: yes, proven - **on this box, by our own runs, thinking is ~77% of all
generated tokens**. Details below, then the mechanism, then the field's
solutions, then ours.

## 1. The proof (measured, our box, our harness)

v1.3 of the bench driver captures the OpenAI-compatible `reasoning_content`
field separately and accumulates `reasoning_chars` in every `metrics.json`.
Across the runs that record it:

| Run | Completion tokens | Reasoning chars | Est. reasoning tokens (~4 ch/tok) | Thinking share |
|---|---|---|---|---|
| qwen3.5-4b_v13_gpu8k_r2 (30 turns, 19 actions) | 17,803 | 54,570 | ~13,643 | **76.7%** |
| granite-4.2-8b_v13b (30 turns, 15 actions) | 17,127 | 54,121 | ~13,530 | **79.0%** |
| qwen3.5-4b_v13_gpu8k (4 turns) | 1,163 | 1,989 | ~497 | 42.8% |
| K2-Horizon-7b_v13 | 670 | 66 | ~17 | 2.5% (the empty-call pathology) |

(Pre-v1.3 runs recorded 0 because v1.2 threw the thinking away - the LFM
"refusals" we later corrected to INCONCLUSIVE were partly this artifact.)

**What that means in wall clock on this box:** every reasoning token is one
full forward pass through the model - same layers, same active experts, same
per-token cost as an answer token. A 30-turn bench run that generates 17.8k
tokens is really generating ~4.1k tokens of answer and ~13.6k of scratchpad.
At the measured 10.2 t/s effective, the run's thinking tax alone is ~22
minutes of GPU time. Cut thinking in half and the identical run finishes ~40%
faster; cut it entirely and the same wall clock buys ~4x more turns.

**And there is a second, specimen cost we discovered while measuring:**
`max_tokens` starvation. Our MT5 wrapper caps generation at 4096 and older
runs at 1600. A model that spends 1500 tokens thinking has 100 left for the
actual JSON-RPC request. Some of the bench's famous failure classes (empty
tool-call blocks, truncated requests) are consistent with thinking eating the
reply budget - the harness must treat max_tokens as a **reasoning + answer**
budget, and be able to split it.

Corroboration from llama.cpp itself, logged at load on the granite run:
"chat template supports preserving reasoning, it is enabled by default (may
use more tokens)". Our bench driver currently sends **no thinking control at
all** - every run pays full price.

## 2. Names (what the field calls it)

| Name | Where you hear it |
|---|---|
| **chain-of-thought (CoT)** | the original research name (Wei et al. 2022); "long CoT" is the modern RL-scale version |
| **test-time compute / inference-time scaling** | the technique family: spend tokens at generation time instead of parameters at training time |
| **reasoning tokens / reasoning_content** | the API field name (OpenAI, DeepSeek, vLLM, llama.cpp); OpenAI o-series markets it as "reasoning" and exposes `reasoning_effort` |
| **thinking / thinking mode** | Qwen3/Qwen3.5 family: templates have an explicit `enable_thinking` branch; Claude calls it "extended thinking" with `budget_tokens`; our harness and the operator call them thinking tokens |
| **scratchpad** | the informal term; the tokens are a visible working memory the model talks to itself in |

## 3. How the architecture actually does it (where, how, why)

**There is no reasoning module.** It is ordinary autoregressive generation
into a designated channel, and everything about it is decided at *training*
and *template* time, not architecture time:

- **Training**: SFT on long chain-of-thought transcripts teaches the format;
  then RL on verifiable rewards (math exact-match, code tests) teaches the
  model to *use* the scratchpad - DeepSeek-R1-Zero showed this emerges
  without any CoT supervision at all. The reasoning tokens are not computation
  the model was forced to do; they are a habit it learned pays off.
- **Where the tokens go**: the chat template defines a reasoning region
  (Qwen3-style templates wrap it in an `{% if enable_thinking %}` block; the
  server parses that region out of the stream into the `reasoning_content`
  field, exactly what our harness now captures). Architecture-wise the tokens
  flow through the identical layers, attention, and MoE routing as any other
  token - nothing is cheaper about them.
- **The three costs**: (1) one full forward pass per token - the direct tax
  measured above; (2) they accumulate into the KV cache, so every later turn
  re-attends to all of them (prefill grows); (3) they consume the reply
  budget (`max_tokens`), which can starve the actual answer.
- **Why models do it**: on hard, multi-step, verifiable tasks (math, code,
  agentic planning), spending intermediate tokens measurably raises accuracy.
  It is the cheapest capability-per-FLOP the industry found in 2024-2025 -
  which is why every frontier model ships it on by default, and why on a box
  like ours it is simultaneously their best feature and our worst tax.

## 4. What the field does about it (the known levers)

| Lever | Mechanism | Where |
|---|---|---|
| **Budget it** | `reasoning_effort` low/medium/high (OpenAI), `thinking.budget_tokens` (Claude), `reasoning_budget` template kwarg | caps the scratchpad, keeps some |
| **Adaptive thinking** | think only on hard prompts/tokens; routers classify difficulty first | research stage, real wall-clock wins reported |
| **Compress the CoT** | distill "long CoT -> short CoT" so the habit survives with fewer tokens | training-time |
| **Draft the thinking** | speculative decoding over reasoning segments - boilerplate reasoning is high-acceptance draft text | exactly our T-A; nobody ships it for thinking specifically |
| **Two-model thinking** | a small model produces the plan, the big model executes it | our T-D |
| **Parallel thinking (throughput)** | batch interleaved reasoning across requests | server-side scheduling, not our problem |

## 5. Our plan (P1, now with measured inputs)

| # | Experiment | The one test | Status |
|---|---|---|---|
| T-0 | the thinking tax | **DONE** - 77-79% measured (this doc, section 1) | measured |
| T-E | **template toggle** | send `chat_template_kwargs: {"enable_thinking": false}` on qwen3.5-4b through the 12-task quality harness: quality delta vs the ~75% token saving | one-line driver change, needs green |
| T-F | **bench budget audit** | re-card the 0-action failure classes with thinking split from answer; if K2-style empty calls are budget starvation, the card class changes from "protocol failure" to "budget starvation" | analysis of existing runs |
| T-C | budget curve | cap reasoning at 25/50/100% via reasoning_budget where templates support it; quality vs tokens | needs T-E |
| T-A | draft-the-thinking | spec-decode on reasoning-heavy prompts; acceptance rate + net t/s | the flagship |
| T-B | iGPU drafting theater | drafts on the iGPU (50 ns dispatch, 4.8 GB/s UMA reads) concurrent with dGPU verify | after T-A |
| T-D | two-model thinking | 0.5B (74 t/s) plans, big model executes | parallel track |

**OPERATOR DIRECTIVE (2026-10-24): disabling the thinking mode is banned as a
solution** ("sure lets fix something by just forgetting it exists?"). The
template toggle exists in this folder ONLY as the control arm of a
measurement - the ruler that prices what thinking buys - never as an answer,
and only when the speed keeps the smart part. The full research record
(Wei 2022, DeepSeek-R1, long-CoT survey, prefix caching/KV reuse, vLLM's
thinking-token block handling, ThinKV/ArborKV), the verified mechanics, and
the reuse-first plan now live in `09-COT-RESEARCH/`.

**The sharpest finding is now the prefill monster, not thinking toggle**: our
driver resends the full dialogue every turn - 104,499 prompt tokens against
17,803 completion on qwen3.5-4b r2 (5.9x), with llama.cpp offering no slot
persistence on this box (verified). Fixing prefix identity (R1) or holding a
session proxy (R2) shrinks the largest measured cost without touching what
the model thinks. That reordering - bench waste first, model behaviour second
- is the program's center of gravity.
