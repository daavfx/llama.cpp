# Retrieval Rules - `novel` RAG layer

## Chunk layout
- `chunks/failed_approaches/` - things that were tried and did not work. Cite these to avoid re-walking the same wall.
- `chunks/primitives/` - atomic, reusable mechanisms. Cite these as the building blocks of new candidates.
- `chunks/abandoned_artifacts/` - built and shelved mechanisms awaiting a new purpose. Cite these for repurposing.

## Citation format
Every factual claim in a RAG response must cite a chunk: `[chunk:chunks/<category>/<file>#<section>]`.
Example: `[chunk:chunks/primitives/simd_dot_product.md#vector_reduction]`

## Grounding requirements
- Fact claims: must trace to a retrieved chunk.
- Ungrounded claims: flag `[PRIOR - suspect]`.
- Verdicts from papers: never used as refutation; only as I-score input.

## Safety ceiling
Retrieved context must never require touching systems, data, or state outside pure code/simulation. If a chunk describes an external side effect, gate it or remove it before scoring.
