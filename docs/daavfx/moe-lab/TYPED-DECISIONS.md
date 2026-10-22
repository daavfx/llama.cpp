# TYPED-DECISIONS.md - Jev/JEPA/embeddings research + the readout recipe

Date: 2026-10-20
Owner: operator, agent ID `lfm25-gtx1650-campaign`
Trigger: operator asked whether "jev" beats LLM architecture for the
campaign's tasks, and to research JEPA + Gemini Embedding.
State: research note + design consequence. Zero execution. Hold unchanged.

Sources fetched 2026-10-20: huggingface.co/openjev/openjev (model card),
arxiv 2301.08243 (I-JEPA), Wikipedia "World model (AI)" (V-JEPA/Genie 3/
Cosmos 3), deepmind.google/models/gemini/embedding (Gemini Embedding 2).

## 1. What Jev / OpenJev is

OpenJev (openjev/openjev, CC BY-NC 4.0, 27B, Qwen3.5 base) is a TYPED
DECISION model. You send a state + questions with your own options in the
request; it returns a choice / yes-no probability / score. Mechanism: each
option gets a letter; the model is asked for a single token; the decision is
read from the letter scores at the first output position; fixed calibration
turns scores into probabilities. No free-form text, no chain of thought, no
per-task training. Up to 52 options per pass, 16,384-token prompts, one image
per request (screenshots for browser/desktop agents).

Measured (their card): ~80 ms short text decision, ~210 ms web decision
(H100 FP8); answer flips 2.3% when options are shuffled (18.5% before
tuning); 84.0% on their frozen 10,000-question set (hosted Jev API 85.4%,
same-base-before-tuning 80.4%, generative 9B 75.7%). GGUF builds exist for
llama.cpp, 16.5 GB (Q4_K_M) to 28.6 GB (Q8_0), text only. Use cases include
routing, moderation, judging other models (grounded/hallucinated, which
answer is better), and browser/computer-use agents (which element, which
operation, is the task done). "Kev" (per operator) is another name in the
same hosted decision-model family; not fetched here.

## 2. Fact-check of "jev is better for deterministic"

Mostly TRUE with one precision: an autoregressive LLM at temperature 0 is
also deterministic (same prompt -> same argmax). Jev's real wins are:

- TYPEDNESS: the answer is scores over YOUR options; nothing to parse, no
  malformed JSON possible.
- SPEED: one forward pass, one token; no generation wait.
- STABILITY: order-shuffle flip rate 2.3% vs 18.5% untuned.
- CALIBRATION: probabilities with thresholds, not vibes.

What it is NOT: a text generator. It cannot write code, draft tokens, or
compose answers. It replaces the LLM exactly where an LLM was being misused
as a text-emitter for a decision.

## 3. The steal: poor-man's Jev readout on our own models

OpenJev is 27B and does not fit this box (16.5 GB at Q4_K_M > 4 GB VRAM; CPU
single-token readouts semi-viable at ~0.3-1.5 s per decision, coarse cadence
only; license is non-commercial). We do not need the weights; we need the
MECHANISM, and llama.cpp exposes it:

    1. Frame the decision as a lettered option set (A..Z, <= 52 options).
    2. Prompt ends asking for a single letter. Grammar (GBNF) or logit bias
       restricts the first output position to the option letters.
    3. Request 1 token at temperature 0 with logprobs enabled
       (llama-server exposes per-token top logprobs; verify the exact flag
       at go).
    4. Decision = argmax letter score (optionally calibrated like their
       READOUT_T / threshold settings).

Deterministic by construction, typed by construction, one pass. Runs on
lfm2.5-350m (VRAM, ms-scale) or the 8B itself (CPU, coarse cadence).

## 4. Where this changes our designs

- LIVING-KERNEL policy brain: policy slots become typed micro-decisions
  (pin/unpin expert X? knob set A/B/C? draft k=2/4/8?) scored by single-pass
  readouts instead of sampled JSON. Faster, unparseable-output-proof, and
  the "constrained policy object" gains a stronger form: the brain emits a
  vector of choices, each backed by calibrated letter scores. Mandatory
  interface for all LK decision points (REVIEW-1).
- Flagship readout (REVIEW-1, LK-5 Semantic Anticipatory Routing): the
  moment a prompt arrives, a 1-token readout on the resident 350m draft
  classifies the workload cluster (codegen / JSON tool-call / prose /
  math-debug) and the policy bus swaps in that cluster's pre-computed pin
  map before the 8B finishes warming its dense blocks. Language
  understanding steering memory physics - the one thing a bandit cannot do.
- FOUNDRY F3 (semantic KV eviction): salience scoring per KV segment is a
  readout (is-this-segment-load-bearing? A/B/C scale), one pass per segment
  batch.
- Quality harness: an optional LLM-judge lane (groundedness, answer-rubric)
  via readouts on a small model; the deterministic v0 scorer stays primary.
- Theater/market (LK-2): auction parameters can be proposed as readouts.

## 5. JEPA (research summary)

Joint Embedding Predictive Architecture (LeCun): encoder maps observations
to embeddings; a predictor estimates future embeddings from current ones +
action; training minimizes error in embedding space, not pixel/token space.
Family: I-JEPA (2023), V-JEPA 2 (2025, video world model, zero-shot robot
control), LeWorldModel (2026, end-to-end from pixels), Genie 3 (DeepMind,
interactive world generation), Cosmos 3 (NVIDIA, MoT: AR transformer for
reasoning + diffusion transformer for multimodal generation). LeCun's claim:
text-trained LLMs cannot predict beyond text; world models handle causal /
physical reasoning. VERDICT for us: no text-out head, not a competitor for
any of our generation tasks. Our Tier-1 expert-prediction (router-history ->
next experts in a compact latent) is already JEPA-flavored; that is the only
place the concept lives in this campaign.

## 6. Gemini Embedding 2 (research summary)

SOTA multimodal embedding model (text/image/video/audio/documents into one
space), 8,192-token inputs, 128-3072 Matryoshka dims, 100+ languages, API
only (GA), aimed at retrieval/RAG/clustering/recs. VERDICT for us: not the
token path; possibly useful later for telemetry-digest compression (embed
router history -> tiny latent for Tier-1 input) and the RAG lane; local
equivalents already on disk (llm-collection/21-embeddings).

## 7. Per-role architecture verdict (the answer to the operator's question)

| Role | Winner | Why |
|---|---|---|
| Product (8B agent: code, text, tools) | autoregressive LLM | the task IS text generation; Jev cannot compose |
| Decisions inside loops (tool choice, grounded, done?, pin/unpin) | Jev-style readout on our models | typed, 1 pass, stable, deterministic |
| Spec-decode draft | small same-family LLM | must generate token sequences |
| Living-kernel brain output | readouts (see section 4) | upgrade over sampled JSON |
| Next-expert prediction (Tier 1) | latent micro-predictor (JEPA-spirit) | us-scale, no decoding |
| Telemetry digest / RAG | embeddings (local; Gemini 2 if API acceptable) | compression + retrieval, not generation |

## 8. Constraints and holds

- No OpenJev download during the hold (16.5+ GB, license CC BY-NC 4.0,
  coder sweep active). Revisit only if a hosted-class judge becomes
  necessary.
- llama-server logprobs flag spelling to be verified at go (recipe section 3
  step 3).
- Everything here is design consequence only; no code changed in this pass.
