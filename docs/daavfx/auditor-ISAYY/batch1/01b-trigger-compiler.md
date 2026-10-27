# 1b - Trigger compiler: the real price of the prefill monster

Batch 1 item 1b (zero-GPU). The question: the scoreboard's headline "5.9x
prefill monster" (104,499 usage-reported prompt tokens vs 17,803 completion
on qwen3.5-4b_v13_gpu8k_r2) - how much of that is REAL prefill work, and what
would R1/R2 (prefix reuse) actually buy?

## Method

llama-server logs a slot print_timing pair per chat request:

```
prompt eval time = 2073.03 ms /   30 tokens
        eval time = 11478.02 ms / 106 tokens
       total time = 13551.06 ms / 136 tokens     (total = prompt + eval, verified)
```

Parse `llm_bench\runs\qwen3.5-4b_v13_gpu8k_r2\llama_server.err.log` (27
requests with the pair; 30 turns ran, last 3 failed or errored into the catch
path). NOTE: the string ` eval time = ` is a suffix of `prompt eval time = ` -
a naive double-match inflates the generation sum by the prompt amount
(47,028 raw vs 17,803 real). The correct parse must exclude prompt lines from
the generation sum. Total cross-checks exactly against the usage counters.

## Result (qwen3.5-4b, GPU assist, 8k ctx, elided history)

| Quantity | Value |
|---|---|
| Usage-reported prompt tokens | 104,499 |
| ACTUALLY PROCESSED prompt tokens (server log) | **29,225** |
| Over-statement factor | 3.58x |
| Usage-reported completion | 17,803 |
| Processed generation tokens (cross-check) | 17,803 (exact match) |
| Prompt processing time | 554.9 s (53 tok/s effective) |
| Generation time | 1,100.4 s (16.2 t/s) |
| Server-side floor | 1,655.4 s vs 1,740 s wall (95%) |

## What this settles

1. **The "5.9x" is a usage-reporting artifact.** llama.cpp's usage counter
   reports the full prompt length of every request whether or not the prefix
   cache was hit; the scheduler actually processed only 29,225 tokens. The
   slot prefix cache IS working on the driver's message array (system + task +
   common early history stays byte-identical across turns; the elided-history
   divergence only invalidates the cache from the elision point on).
2. **R1/R2's honest ceiling is the 554.9 s of prompt processing - 32% of wall
   time - not the 5.9x the scoreboard implied.** R2 (a persistent-session
   proxy) can at best erase part of that 555 s; R1 (prefix-fidelity history)
   pushes the elision divergence later, shrinking the processed-per-turn
   delta. Neither is free, and neither is the first-order win the scoreboard
   suggested.
3. **The real first-order number is elsewhere**: at 16.2 t/s generation and
   53 tok/s prompt processing, the qwen lane's wall is generation-bound
   (1,100 s of 1,655 s). Any lever that raises generation t/s beats the
   prefill lever on this run. That reframes the order: dense decode speed
   (kernels/backends) and the thinking tax (77-79% of the 17.8k) sit ABOVE the
   prefill monster in value.
4. **The instrument ask is now answered by this parse**, not a new capture:
   whenever a usage number is quoted for scheduling decisions, the
   slot-print_timing parse is the mandatory companion (a 5-line scripted
   parse of the existing server logs). Added to the register as protocol.

## Protocol addition (register)

Any prefill/usage figure that enters a verdict or a plan carries BOTH
numbers: usage-reported AND slot-log-processed, from the same run. One
number alone is not admissible - this is the same class of discipline as the
capture-manifest (EXP-1).
