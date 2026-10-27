# research/05 - vLLM thinking-token cache issue: production reality

Source: harness-lane research (delivered 2026-10-24), from vLLM GitHub Issue
#41938: "[Feature]: Opt-in: stop caching KV blocks after thinking start
tokens."

This is the most directly relevant engineering document to our situation:
how a production serving engine actually deals with reasoning-token blocks.

## The problem vLLM identified

> "Reasoning models (DeepSeek-R1, Qwen3, QwQ, etc.) produce
> `<think>...</think>` tokens whose content varies across requests even for
> identical prompts. Under prefix caching, these thinking blocks get hashed,
> cached, and never reused - pure waste of cache capacity that pressures
> eviction of actually-reusable prompt blocks."

## The proposed solution (NOT disabling reasoning)

> "Once the thinking start token sequence is detected during incremental
> block hashing, we stop computing hashes for subsequent blocks. No hash
> means `cache_full_blocks` never registers them - they still exist in GPU
> memory for the current request but don't pollute the shared cache pool."

> **Test result:** "7.6% reduction in peak GPU KV cache usage with feature
> enabled - thinking blocks are not registered in the cache pool, freeing
> space for reusable entries. Prefix cache hit rate is identical."

## What this proves for us

1. **Reasoning tokens are kept** - they remain in GPU memory for the current
   request. Nothing is disabled.
2. **The optimisation is about what gets SHARED ACROSS REQUESTS** - thinking
   blocks are request-specific and should not occupy the shared prefix-cache
   pool.
3. **The wasted capacity was the problem, not the reasoning itself.**

Ties to the temperature A/B (router traces running): at temperature 0 the
thinking is deterministic, so for the SAME prompt the thinking block WOULD be
reusable across identical requests - which is exactly the case where our own
repeated harness runs (same 12 tasks, same seed) could reuse it. That is a
bench-level reuse opportunity vLLM's default behaviour deliberately avoids,
but our workload (repeated identical prompts at temp 0) makes it real.
