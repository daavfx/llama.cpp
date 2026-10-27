# research/01 - Wei 2022, the original CoT paper

Source: harness-lane research (delivered 2026-10-24), from the paper itself.

**Paper:** Wei et al., *Chain of Thought Prompting Elicits Reasoning in Large
Language Models*, arXiv:2201.11903 (NeurIPS 2022).

**Core finding (abstract):**
> "Experiments show that inducing a chain of thought via prompting can enable
> sufficiently large language models to better perform reasoning tasks that
> otherwise have flat scaling curves. When combined with the 540B parameter
> PaLM model, chain of thought prompting achieves new state of the art of
> 58.1% on the GSM8K benchmark of math word problems."

**Why it matters here:** CoT is not a wrapper or a UX feature. It is an
emergent property of scale that measurably improves accuracy on multi-step
problems. The accompanying Google Research framing: models of sufficient
scale can solve complex reasoning problems that are not solvable with
standard prompting.

> **The reasoning is the capability. Disabling it is disabling the
> capability** - which is why our program never proposes that as a fix.
