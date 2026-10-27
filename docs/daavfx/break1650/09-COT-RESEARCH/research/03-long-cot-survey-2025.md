# research/03 - Long-CoT survey 2025

Source: harness-lane research (delivered 2026-10-24), from the paper itself.

**Survey:** Liu et al., *Towards Reasoning Era: A Survey of Long
Chain-of-Thought for Reasoning Large Language Models*, arXiv:2503.09567
(2025).

**What it covers:** the shift from short CoT to **long CoT** - reasoning
traces spanning thousands of tokens, with self-correction, backtracking, and
verification patterns. It documents why frontier models default reasoning on
for hard tasks and catalogues the architectural and training choices that
support it.

**Why it matters here:** the operator's observation - "in my harness I can
see the reasoning word by word, letter by letter" - is not a bug, it is the
intended observable output of long CoT. The survey is the field-wide context
for why that output exists, and therefore the reference for what it costs.

Ties directly to the measured tax on this box: 77-79% of generated tokens
are reasoning (`08-THINKING-DEEP-DIVE.md` section 1). Long CoT is the cost
center; this survey is the map of it.
