# research/06 - ThinKV / ArborKV: the reasoning-cache frontier

Source: harness-lane research (delivered 2026-10-24), from the papers.

Two 2026 papers show where the field is going: **managing reasoning-token KV
cache intelligently** instead of disabling reasoning. Both accept the premise
that reasoning tokens are valuable and optimise how their KV is stored,
compressed, and evicted.

## ThinKV (ICLR 2026)

> "The long-output context generation of large reasoning models enables
> extended chain of thought (CoT) but also drives rapid growth of the
> key-value (KV) cache, quickly overwhelming GPU memory... ThinKV is based on
> the observation that attention sparsity reveals distinct thought types with
> varying importance within the CoT. It applies a hybrid
> quantization-eviction strategy, assigning token precision by thought
> importance and progressively evicting tokens from less critical thoughts as
> reasoning trajectories evolve."

> **Result:** "near-lossless accuracy with less than 5% of the original KV
> cache, while improving performance with up to 5.8x higher inference
> throughput."

**Relevance to this box:** our KV is the scarce resource (4 GB VRAM shared
with weights, and the MoE cache disabled at these splits). Thought-importance
grading is a DIRECT fit: the router logger already gives us per-layer signals;
attention sparsity instrumentation would give us per-token thought-type
signals. This is the natural next tier after prefix reuse proves out.

## ArborKV (ICML 2026)

> "Tree-of-Thoughts (ToT) organizes inference to tree-structured search with
> branching and backtracking, but it substantially amplifies the key-value
> (KV) cache... We address this challenge by observing that KV reuse in
> ToT-style inference is governed by search dynamics: near-term decoding
> depends primarily on the active branch and its ancestors, whereas inactive
> subtrees have low short-term reuse probability yet must remain recoverable
> for backtracking."

**Relevance:** if we ever build the theater-sharded parallel drafts (P1 T-B:
iGPU drafts variant A, dGPU drafts variant B, verify all), the draft variants
ARE a ToT over the answer distribution - and ArborKV's reuse policy is the
correct cache discipline for them. File as the dependent tier.

## The stance these papers codify

Neither proposes disabling reasoning. The research direction is: keep the
reasoning, make the cache smarter about it. That is exactly our program's
stance (12-OUR-PLAN.md).
