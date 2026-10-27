# research/02 - DeepSeek-R1 2025, RL-emergent reasoning

Source: harness-lane research (delivered 2026-10-24), from the paper itself.

**Paper:** DeepSeek-AI, *DeepSeek-R1: Incentivizing Reasoning Capability in
LLMs via Reinforcement Learning*, arXiv:2501.12948 (Nature, 2025).

**Core finding (abstract):**
> "Here we show that the reasoning abilities of LLMs can be incentivized
> through pure reinforcement learning (RL), obviating the need for
> human-labeled reasoning trajectories. The proposed RL framework facilitates
> the emergent development of advanced reasoning patterns, such as
> self-reflection, verification, and dynamic strategy adaptation."

**Why it matters here:** the empirical refutation of the "reasoning module"
myth. There is no separate reasoning module. Reasoning is ordinary
autoregressive generation into a channel defined by the chat template, and
RL on verifiable rewards teaches the model that using the channel pays off.
The `reasoning_content` field of a serving API is parsed from generated
tokens, not read from a hidden internal state.

> The reasoning channel is a learned behaviour, not a switch. It exists
> because it works.

Practical consequence for the MT5 bench: the LFM2.5 runs that "refused"
under harness v1.2 were never protocol failures - the old harness threw the
reasoning away and capped at 1600 tokens, so the tool call never fit. That
is a harness artifact, not model behaviour (see `08-THINKING-DEEP-DIVE.md`).
