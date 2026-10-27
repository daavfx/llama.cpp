# CONTEXT-PIPELINE - the context/compaction reinvention (transcribed brainstorm)

Date: 2026-10-26. Source: the operator's brainstorm with a coder, transcribed
(instructions stripped). This file is the RECORD, not the design. The
method pass (novel-skill scoring, refutation, synthesis) runs over it in the
next files. ASCII only; unverified numbers are tagged `[PRIOR - suspect]`.

---

## 1. The operator's claims, and the evidence map that came back

Claim-by-claim, as transcribed, with the papers that were attached.

### 1.1 The frustration is measured, not felt

- Chroma tested 18 frontier models: every one degrades as input length grows,
  long before the window is full - a continuous signal-to-noise decline, not
  an overflow cliff.
- A 2026 paper localizes the primary driver: **contradiction accumulation,
  not length**. Ordinary conversation: fact recall drops to 57%. With
  contradictions mixed in: 21%. Google's 1M-token window still drops 47.8
  percentage points under contradictions.
- An external "metabolism" layer that resolves contradictions during idle
  time recovered accuracy to 73% - above the contradiction-free baseline.

Consequence as stated: "store everything and hope" is measurably wrong. The
problem is not capacity; the model cannot distinguish signal from
accumulated noise and contradiction.

### 1.2 The five families of novel proposals

1. **Compression of the KV/attention state**: StreamingLLM, SnapKV,
   LongLLMLingua, Dynamic Memory Compression (attention/prompt cost);
   AutoCompressor, Gisting, ICAE, Activation Beacon (learned compact
   interfaces).
2. **Bounded persistent state** (the most radical): CoDA-GQA-L replaces the
   KV cache with a **fixed 384-slot buffer per layer that never grows** - 120
   MB whether the document is 2K or 128K tokens (1,365x compression at 128K).
   The state is serializable: `torch.save()` it, return a week later, query
   without re-reading a single token.
3. **Parametric internalization**: Deep Context Distillation, Cartridges,
   Doc-to-LoRA (content compiled into parameter/KV modules).
4. **Retrieval with tiered memory**: hot turns verbatim, warm topic chunks
   in SQLite, cold session summaries on disk.
5. **Filesystem/markdown memory**: the family closest to the operator's
   instinct.

### 1.3 "Humans are just next-word predictors" - partially true

- Holds: an FAU study combining EEG/MEG with LLM predictive probabilities
  found the brain becomes active *before* a word starts; neural response is
  weaker for high-probability words, stronger for unexpected ones. The
  researchers say the two systems organize language internally in a
  comparable way.
- Breaks: the brain predicts **over multiple timescales and
  hierarchically**, while current LLMs predict nearby words and lack this.
  The angular gyrus forecasts ~2.5 layers deeper than Heschl's gyri
  (p < 0.001). Humans predict a hierarchy; LLMs predict a flat sequence.

### 1.4 "AI should complement, not imitate" - directly supported

- The augmentation-not-emulation argument: if human cognition carries noise
  and systematic biases, complementary AI should *compensate for* those
  limitations rather than reproduce them - role allocation, transparent
  uncertainty, mutual modeling of functionally relevant features, without
  replicating cognitive mechanisms.
- The Noetic Intelligence framework: machine-native cognitive capabilities
  distinct from human cognition; AI as a partner with asymmetric,
  complementary strengths rather than an imitation target.

### 1.5 "Structured connections beat brute-force sparsity" - half-right

- Right: a 2025 paper challenges the prevailing MoE paradigm. Sparse expert
  activation prioritizes computational efficiency, but the quality and
  nature of inter-module interactions matter as much as cost - structured
  collaboration (hierarchical fusion, differentiated credit assignment,
  co-adaptive reasoning tools) improved compositional reasoning and
  out-of-distribution robustness over simple sparsity. Prioritizing
  cognitive synergy over simple sparsity is a promising direction.
- Wrong: "we can easily achieve" is not supported. These are
  proof-of-concept experiments on specific benchmarks; the paper frames
  structured collaboration as an underexplored research gap, not a solved
  engineering task. Emergent modularity already exists implicitly in dense
  transformers, and extracting it reliably is hard.

### 1.6 "Pure .md can do a better job" - backed, with a sharp caveat

- Backed: ByteRover stores all knowledge as human-readable markdown on the
  local filesystem - no vector DB, no graph DB, no embedding service - and
  reports state-of-the-art accuracy on LoCoMo and competitive results on
  LongMemEval. OctaMind stores long-term memory as `working_memory.md`,
  `episodic_memory.md`, `semantic_memory.md`, etc., with FAISS indexes built
  on demand, arguing markdown-native architectures offer inspectability,
  debuggability, versionability, low operational overhead. A systematic
  study confirms deployed agents already use filesystem memory (a directory
  tree of markdown the agent reads, writes, and reorganizes).
- Caveat: the same study found **organization erodes for all but the
  strongest management agent**, and **no agent they measured converts
  organization into better answers**. Organization reliably buys *search
  economy* - roughly halving retrieval cost where material is large.

### 1.7 The verdict table (as transcribed)

| Claim | Verdict |
|---|---|
| Current context/storage stack is overcomplicated and brittle | Backed |
| Novel alternatives exist | Backed (five families) |
| Humans are just next-word predictors | Partially (hierarchy vs flat) |
| AI should complement, not imitate, humans | Backed |
| Structured connections beat brute-force sparsity | Directionally backed, not "easy" |
| Pure .md can do a better job than storing | Backed, with limits |

The strongest version of the operator's position is not "throw away storage
and use .md" but: stop treating the context window as the memory; use an
auditable external store (markdown works); keep the model's internal state
bounded and compressed; design for complementarity.

---

## 2. The pipeline as it exists today (transcribed mechanics)

Per turn the harness sends the grow-until-the-limit prefix:

| Turn | What the LLM receives |
|---|---|
| 1 | System prompt + 1st message |
| 2 | System prompt + msg1 + response1 + 2nd message |
| ... | Entire history grows until the model's limit (128K for GLM-5.3) |

Compaction = summarization + pruning, executed by the harness:

1. The harness detects token count > limit.
2. It calls the LLM with a "summarize this conversation" prompt.
3. It replaces the oldest N messages with a single summary message.
4. It continues: system prompt + summary + recent messages + the new message.
   The LLM never sees more than its limit - the harness enforces it.

Accounting as transcribed:

| What | Tracked by |
|---|---|
| Token count per message/part | The harness (the model's tokenizer) |
| Total prompt size | The harness (sums before each request) |
| Compaction trigger | The harness (at ~80-90% of limit) |
| Compaction execution | The harness (calls the LLM to summarize) |
| Hard limit enforcement | The LLM API (returns error if exceeded) |

The transcribed verdict: the table is mechanically correct but encodes the
wrong diagnosis. Reinvent it around *integrity* and *prefix economics*, not
around "summarize the oldest N."

---

## 3. Three receipts that break the current design's assumptions

**A. Compaction is a knowledge-integrity problem, not a size problem.**
A 180-turn study: recall drops to 57% with ordinary conversation, collapses
to 21% with contradictory information, while Google's 1M-token window still
drops 47.8 points under contradictions. Remove the contradictions and
performance recovers regardless of length. Summarizing contradictions into
a single soup message makes them harder to detect later.

**B. Recursive summarization compounds loss, measurably.**
VehicleMemBench: Gemini-3-Pro-Preview scores 90.60 ESM with gold memory,
64.80 under recursive summarization (-25.8); GLM-5 gets 55.00. Every
compaction summarizes a summary; error accumulates.

**C. Retrieval is not automatically the fix.**
AgentMemBench (five strategies, identical conditions): the external KV
store dominates quality, compression-based summarization is the clear
runner-up *because it inherits provenance*; recency windows, summaries, and
entity graphs collapse at long horizons; EKV's recall advantage costs
footprint (~5,100 vs ~300 tokens). VehicleMemBench shows KVS sometimes
scoring below recursive summarization (MiniMax: 30.40 vs 50.00) - retrieval
fails silently when the query misses.

So: summaries lose information, retrieval loses queries, and the real decay
driver is contradictions. An honest reinvention has to handle all three.

## 4. What the current pipeline already gets wrong (the PR map)

| Current behavior | Why it is wrong | What the codebase already admits |
|---|---|---|
| `char/4` token estimate | Miscalibrated per model/tokenizer | PR #22029: an EMA ratio (0.7/0.3 blend) from actual usage tokens |
| Summarize everything old, keep the last 15k | The summarizer gets the full bloated history including tool outputs | Prune before compaction; context-relative protect budget (15% of context, min 20k) instead of a flat 40k |
| Compact only at the limit | Late compaction = maximal re-prefill cost and rot | Proactive prune at 50% usage after each step |
| Budget = context limit | Overflow on the summarize call itself | Available input = context limit - output reserve - prompt reserve |
| Generic "summarize this conversation" prompt | Ignores the plan; instructions drift out of sync | PAACE: pruning alone is insufficient for multi-step agents; content must be rewritten in sync with the plan; a distilled compressor retains 97% of teacher performance at >10x lower inference cost |

Structural details noted: the harness updates the same summary on later
compactions rather than re-summarizing from scratch; provider-native
compaction is supported as an opaque encrypted checkpoint - better quality,
but only valid for the same provider/model/endpoint (portability lost).

## 5. The seven-rule blueprint (as transcribed)

- **R1. Separate storage from view.** The transcript is the archive (never
  mutated); the prompt is *compiled* from a state: `pinned` + `working` +
  `retrieved`. Compaction edits the state, not the history.
- **R2. Three tiers, borrowed from bounded-state attention.**
  CoDA-GQA-L's structure: recent window (exact, ring buffer) + exact
  landmark bank (write-gated, novelty-filtered) + summary prototypes (EMA
  centroids); 384 slots per layer, constant, serializable. Two warnings:
  dedupe must operate on content, not position (keys with RoPE look
  orthogonal for the same word at different positions); any bounded policy
  trained naively is catastrophic (PPL 5.75 -> 2,464 without the phase-2
  training), so hand-rolled eviction policies need empirical validation.
- **R3. Make compaction a reconciliation step, not a summarization step.**
  Run a contradiction pass first: new fact vs pinned facts -> supersede
  (keep both with status active/superseded), never blend. Accuracy goes
  above the contradiction-free baseline (73% vs 57% vs 21%). The lightweight
  version (delta-prune) resolves contradictions before they enter context.
- **R4. Compact during idle, not on the critical path.** Metabolism runs
  between turns; blocking compaction pays summarization latency + a full
  re-prefill at the worst moment.
- **R5. Treat the prompt prefix as a cache artifact with an explicit
  budget.** Only compaction may mutate the prefix, and it pays for it in a
  measured, batched way. Everything else appends. Track
  `cache_hit_ratio = cache_n / (cache_n + prompt_n)` as a first-class metric.
- **R6. Prune by value class, in this order:** tool outputs -> raw
  observations -> assistant reasoning -> user instructions -> pinned facts
  (never). Never summarize: system prompt, tool schemas, the active plan,
  decisions with receipts, open questions. PR #22029's protect list
  (compress, todowrite, background_output, diagnostics) is a starting
  taxonomy.
- **R7. Every archived item carries provenance.** That is why
  compression-based summarization is the AgentMemBench runner-up rather
  than the winner - it inherits the provenance of the turns it compresses,
  so the model can be pointed back to the verbatim source.

## 6. The measurement kit (all offline, zero-gate)

- **Canary facts**: inject 20-50 known facts at turn 1; probe them at turns
  10/30/50; plot retention per strategy. Measures *our* pipeline on *our*
  workloads - the benchmarks are only priors.
- **Contradiction count**: every turn, log "new fact conflicts with pinned
  fact" events. If >0 and unhandled, the 21% failure mode is brewing.
- **Cache hit ratio** (`cache_n / (cache_n + prompt_n)`) per turn.
- **Cost per retained fact** (not per token): tokens spent / canaries still
  answerable.
- **Re-prefill cost of compaction**: the token spike at the compaction
  boundary. If compaction costs more than it saves over the next N turns,
  the threshold is wrong.

## 7. What to read, ranked (as transcribed)

1. PAACE (arXiv:2512.16970) - plan-aware compression; prune-is-insufficient;
   distilled compressor.
2. Contradiction Metabolism / delta-prune - the integrity framing and the
   57/21/73 numbers.
3. AgentMemBench - the only clean five-strategy comparison with footprint
   costs.
4. VehicleMemBench - recursive summarization decay with real per-model
   numbers.
5. CoDA-GQA-L / stateful neural databases - the bounded-state template and
   its training traps.
6. LongCodeZip (ASE 2025) - if the agent is code-heavy: 5.6x compression
   with a plug-and-play compressor.
7. Recursive Language Models (Zhang et al.) - the "recurse instead of
   compact" school, for contrast.

## 8. The one experiment to run this week (as transcribed)

Take three existing long session transcripts. For each, simulate three
strategies offline: (a) current summarize-and-prune at 80%, (b) PAACE-style
plan-aware prune-then-rewrite, (c) three-tier (pinned + recent 15k +
provenance-tagged archive with retrieval). Score all three with canary
retention + contradiction count + simulated `cache_n`. No GPU, no green
light, pure paper.

Closing warning as transcribed: the research consensus is that no single
strategy wins across horizons - summaries collapse long-range, retrieval
collapses on misses, bounded state needs training. The honest redesign is a
*hybrid with an explicit state machine and explicit budgets per tier*, not
a smarter summarizer.

---

## Operator's directory question (for the method files to answer)

The operator asked which folder is authoritative and whether this should
merge into `plans/loop/` or stay independent. Current lanes in
`docs/daavfx/`: `plans/loop/` (the merge plan), `plans/vault/` (the agent
backend), `skills/` (the novel RAG layer), `app-lane/` (transport + UI),
and now this one. The method pass ends with an explicit map, not a shrug.

## The last task (queued, not rushed)

Routinely check the upstream Orca repo (`https://github.com/stablyai/orca`)
against our fork (`daavfx/daavilefx-ade`) for drift and to see what we
might need and how far behind our last checkpoint we are. A sub-agent runs
that at the end.
