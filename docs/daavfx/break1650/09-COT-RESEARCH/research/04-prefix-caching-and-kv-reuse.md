# research/04 - Prefix caching and KV reuse: the direct answer to "double tokens?"

Source: harness-lane research (delivered 2026-10-24), from the *Prefix
Caching* system-design entry (qfc-network/ai-infra) plus the vLLM/serving
implementation literature.

## The key insight: the KV cache is reusable, and it already does what the operator intuited

> "Every LLM inference request that shares a token prefix with a prior request
> can skip recomputing the KV cache for that prefix - the cache from the prior
> request can be reused directly."

## So is it "double tokens"? No - if the prefix is reusable

The reasoning tokens ARE tokens. They go through the same transformer layers
as answer tokens. But the KV cache stores the key-value pairs for those
tokens so they do NOT need to be recomputed on subsequent decoding steps or
subsequent requests that share the same prefix.

| What people fear | What actually happens |
|---|---|
| "It re-does the reasoning from scratch every time" | Prefill computes KV once; decode reuses cached KV for every generated token |
| "The reasoning is re-tokenised and re-processed" | the token IDs are in the sequence; the KV cache holds their computed representations |
| "Thinking tokens are pure waste" | they are capability-bearing tokens; the waste is when serving engines cache blocks that will never be reused (file 05) |

## Where the real cost is

> "A 1,000-token system prompt that hits the cache saves 1,000 tokens of
> prefill computation per request, potentially cutting TTFT by 50-80% for
> common deployments."

> "For a 70B model on H100, prefill throughput is approximately 10,000-20,000
> tokens/second... A 2,000-token shared system prompt + RAG context costs
> 0.1-0.2 seconds of prefill per request with no caching."

**Translation:** the slowness is PREFILL cost for the reasoning tokens. The
fix is KV cache reuse, not disabling reasoning. On this box prefill is far
more expensive than on an H100 (Flint measured 0.14-0.39 t/s pp at the split
config), so prefill reuse is worth MUCH more here than the H100 math above.

## Matching unit: blocks

> "PagedAttention's block abstraction (fixed-size KV cache pages, typically
> 16-32 tokens per block) is the natural unit for prefix matching. A prefix
> is reusable if and only if the full block it belongs to has been previously
> computed and is still resident."

Key implementations: vLLM Automatic Prefix Caching (APC, 2024), SGLang
RadixAttention (2023), TensorRT-LLM KV cache reuse (2024).
