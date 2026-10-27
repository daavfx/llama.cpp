# 10-MECHANICS - how a reasoning token actually costs money on this box

Written by the infra lane (2026-10-24) on top of the research files in
`research/`. This file is about OUR stack specifically.

## The mechanics, precisely

1. The chat template defines a reasoning region. Qwen-family templates wrap
   it in an `{% if enable_thinking %}` block; other models emit it raw in
   `content` (DeepSeek-R1 style) or as an explicit channel (Claude extended
   thinking). llama.cpp parses that region into `reasoning_content`.
2. Generation is ONE autoregressive stream: `[system][user]<thinking-start>
   ...reasoning tokens...<thinking-end> ...answer tokens...`. There is no
   second pass. The answer is generated once, conditioned on the reasoning
   via attention over the KV cache.
3. Per token, the model runs a full forward pass - identical layers, MoE
   routing, weights read. A reasoning token costs exactly what an answer
   token costs. There is no discount for "internal" tokens.
4. The KV cache is what makes this not-quadratic: each token's K/V pairs are
   appended once and ATTENDED afterwards (a cheap read), never recomputed.
   So within a request there is no recomputation of earlier thinking.
5. Across turns/requests, the KV for a shared prefix can be reused IF the
   serving engine matches it. llama.cpp matches on the rendered prompt via
   slot state with `cache_prompt`; the prefix must be byte-identical.

So the three cost buckets on this box are, in order of measured size:

| Bucket | What | Our measurement |
|---|---|---|
| **Prefill** | every request re-processes the whole rendered history | qwen3.5-4b r2: **104,499 prompt tokens** for 30 turns |
| **Thinking generation** | ~77% of completion tokens | 13,643 of 17,803 tokens |
| **Answer generation** | the rest | ~4,100 tokens |

The finding that reframes the problem: **prefill was 5.9x the completion**.
The thinking tax is real and large, but the prefill stack was larger - and
prefill is the one that is nearly free to fix.

## What our harness does today (verified in code)

- `bench_driver.ps1` keeps the full `$messages` array and resends it every
  turn (line 314) - so every turn re-renders and re-prefills everything.
- The assistant message appended to history carries only `$assistantText`
  (line 370), **not the reasoning** - so the rendered prompt diverges from
  the exact byte sequence the model generated (its turn contained reasoning
  in the middle), which breaks prefix identity and defeats slot reuse at the
  worst possible point.
- The system prompt carries the full MCP tool catalog - the largest stable
  prefix component, sent 30 times.
- No reasoning budget, no thinking control of any kind is sent.

## What llama.cpp on this box does NOT have (verified 2026-10-24)

- No `/slots/{id}/save|restore` endpoints in `tools/server/server.cpp`.
- No `--cache-reuse` in `common/common.cpp`.
- KV cache offloading exists; the MoE expert cache (`--moe-cache-mib`) exists
  and was silently disabled at Flint splits ("no layer has all of its experts
  in host memory").

Conclusion: cross-turn statefulness is our job to build (or to trigger
correctly through the existing prefix matching), not something the server
hands us.
