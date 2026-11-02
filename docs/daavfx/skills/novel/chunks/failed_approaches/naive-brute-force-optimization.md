# Chunk: naive-brute-force-optimization.md

**Category:** failed_approaches  
**Domain:** parameter optimization  
**Status:** failed

## Summary
Brute-force grid search over all parameter combinations was attempted on the quantum engine's parameter space. It failed because the search space grew combinatorially with each added knob, making exhaustive evaluation infeasible within time budgets.

## Why it failed
- Each added parameter multiplies the grid size exponentially.
- No early pruning; every combination ran to completion.
- No mechanism to reuse partial results across nearby parameter points.

## Lesson for weight-breaking
Brute force is not impossible in principle; the assumption that "every combination must be evaluated independently" is what makes it infeasible. Invert that assumption: reuse work via surrogate models, or prune via impossibility scoring before evaluation.

## Cite as
`[chunk:chunks/failed_approaches/naive-brute-force-optimization.md#why-it-failed]`
