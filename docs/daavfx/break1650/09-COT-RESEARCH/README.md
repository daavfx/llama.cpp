# 09-COT-RESEARCH - deep chain-of-thought / reasoning research for this box

Operator directive (2026-10-24, verbatim intent):

1. "never mention disabling" - turning reasoning off is NOT a fix and is
   banned as a proposed solution. Disabling is allowed only as the CONTROL
   ARM of a measurement (a ruler), never as the answer.
2. "sure lets fix something by just forgetting it exists? are you idiot?" -
   reasoning has a purpose; we make it CHEAPER or SMARTER, never absent.
3. "accumulating minor ideas can also turn 1 great idea" - the research goal
   is the pile of composable mechanisms, not one silver bullet.
4. The driving question: "if LLM is thinking and then replies all that, is
   that double tokens? does the harness already avoid duplicating words
   already typed by the reasoning? does it RECALCULATE ALL or is it a simple
   reply once thought?" - answered in `03-THE-DUPLICATION-QUESTION.md` with
   our own measured data, and the answer is not what we assumed.

## The folder

| File | Holds |
|---|---|
| `research/01..06` | the research record delivered by the harness lane (2026-10-24): Wei 2022 (CoT origin), DeepSeek-R1 2025 (RL-emergent reasoning, no module), long-CoT survey 2025, prefix caching + KV reuse, vLLM's thinking-token block handling (#41938), ThinKV/ArborKV reasoning-cache frontier |
| `10-MECHANICS.md` | infra lane: how a reasoning token costs money on THIS box - the three cost buckets, what our harness actually does (verified in code), what llama.cpp here does NOT cache |
| `11-THE-DUPLICATION-ANSWER.md` | the operator's question answered at three levels with our measured data: mechanical (no double compute), behavioral (restatement waste), harness (the 104k-prefill monster) |
| `12-OUR-PLAN.md` | the experiment pile R1-R6 + T-A..T-D + the ThinKV tier, all reuse/cheapen/shrink - none disable reasoning; falsification conditions stated |

## The three canonical sources (fetched 2026-10-24)

| Source | What it gives us |
|---|---|
| Wei et al. 2022, "Chain-of-Thought Prompting Elicits Reasoning in LLMs", arXiv:2201.11903 | the origin: intermediate steps emerge in big models via exemplars; the "aha moment" framing; CoT as a capability, not a module |
| DeepSeek-AI 2025, "DeepSeek-R1: Incentivizing Reasoning via RL", arXiv:2501.12948 (Nature) | reasoning can be EMERGED by pure RL on verifiable rewards - no CoT supervision; long-CoT length is learned behavior, and the paper documents the length/accuracy trade explicitly |
| Hao et al. 2025, "Coconut: Chain of Continuous Thought", arXiv:2412.06769 (COLM 2025) | the frontier: reason in LATENT space (last hidden state fed back as the next embedding) instead of typed words - most word tokens are for textual coherence, not reasoning; enables BFS instead of linear commitment |

Everything else in the folder is either mechanical fact about our stack or marked
as prior knowledge (no unverified numbers enter the plan).
