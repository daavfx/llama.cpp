# `novel` - Weight-Breaking RAG Layer

This directory holds a retrieval-augmented generation (RAG) structure for daavfx agents running under **opencode CLI** and **Orca ADE**. It implements the `RAG_PROMPT.md` role (weight-breaking idea engine) and `SKILLS.md` skill inventory, backed by citeable retrieval chunks.

## Structure

| Path | Purpose |
|------|---------|
| `core/RAG_PROMPT.md` | System prompt / role definition for the weight-breaking idea engine |
| `core/SKILLS.md` | Skill inventory (weight-inversion, rag-override, cross-domain-recombination, etc.) |
| `chunks/failed_approaches/` | Atomic chunks: things tried and failed - cite to avoid re-walking walls |
| `chunks/primitives/` | Atomic chunks: reusable mechanisms to recombine into candidates |
| `chunks/abandoned_artifacts/` | Atomic chunks: built-and-shelved mechanisms awaiting a new purpose |
| `index/retrieval_rules.md` | How to retrieve and cite chunks |
| `index/manifest.json` | Machine-readable manifest of the layer |
| `agents/opencode_agent.json` | Opencode harness agent config |
| `agents/orca_agent.json` | Orca ADE agent config |

## How agents use it

1. **Load the role:** Read `core/RAG_PROMPT.md` and `core/SKILLS.md` into the agent context.
2. **Retrieve chunks:** Pull relevant chunks from `chunks/` based on the query.
3. **Generate candidates:** Follow the METHOD in `RAG_PROMPT.md` - state the consensus assumption, invert it, recombine >=2 primitives from different domains.
4. **Cite facts:** Every factual claim cites a chunk via `[chunk:chunks/<category>/<file>#<section>]`. Ungrounded claims are tagged `[PRIOR - suspect]`.
5. **Score:** Compute `Score = 2*I + S + 3*Novelty + 2*Grounding + 2*PurposeAgnostic - Penalty`. Maximize I subject to S >= threshold.
6. **Output:** Emit the strict OUTPUT FORMAT, then a build plan in pure code for the top candidate.

## Safety ceiling

All candidates must remain within: **pure code, pure reasoning, sandboxed simulation**. No external systems, no irreversible state, no unknown side effects. Never soften safety to preserve a high-I candidate.
