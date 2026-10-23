# DAAVILE Harness — Proposal: The Self-Improvement Loop

## The one-sentence pitch

Agents that improve the harness, agents that improve the models, and a
memory system that remembers why — all running on the operator's desktop,
fed by the eval harness that scores everything.

---

## The three lanes

### Lane A — the eval harness (the gate)

Every improvement loop needs a score. Without one: Harness² can't judge
harness edits, Athanor can't compare models, the fleet can't measure whether
anything got better.

**What it is:**
- A JSONL task file: 10-20 trading-relevant questions with verifiable
  answers. Authored by the operator (the only person who knows what "good"
  looks like for their strategies, their vault data, their logic configs).
- A scoring runner: sends the tasks to a model (via `ctx.llm.stream` or
  llama-server directly), checks the answers, produces a score.
- A leaderboard: `~/.dsh/memory/evals/<model>.jsonl` — append-only, per
  model, per run, per timestamp.

**The tasks** (examples the operator would author):
- "What is the current `sl_value` for the GRID logic in engine A group 3?"
- "Read the vault's XAUUSD tick data range and report the first and last dates."
- "Given this backtest result, what is the profit factor and max drawdown?"
- "Which GGUF in the collection has the largest context window?"
- "Explain the difference between the REPEL and REVERS logics."

**The runner** (~150 lines TS): loads the tasks, streams the model, checks
answers (exact match / numeric tolerance / LLM-judged), writes the score.

**Sized for one session.** The task authoring = operator time (30-60 min);
the runner = mechanical.

---

### Lane B — the Harness² template (agents improve the harness)

Once the eval harness exists, this becomes real:

**The fleet template** (a three-agent roster):
1. **The proposer** — reads the task + the lessons library, proposes a
   harness edit (a prompt change, a new skill, a tool guidance tweak).
2. **The prober** — runs the eval harness twice: once with the base
   harness, once with the edit. Reports the contrast.
3. **The composer** — judges the contrast (did the behavior change? did the
   score improve?), adopts or rejects, records the lesson.

**The lessons library**: `~/.dsh/memory/harness-lessons.jsonl` —
append-only:
```json
{
  "date": "2026-10-22T14:00:00Z",
  "context": "the daavile profile's compaction prompt",
  "edit": "added the ruler to the leaf-compaction prompt",
  "contrast": { "base_score": 0.62, "edit_score": 0.71, "delta": 0.09 },
  "status": "adopted"
}
```

**The loop:** the proposer picks the highest-value lesson-adjacent edit, the
prober measures it, the composer records it. Over sessions, the library
becomes the harness's institutional memory.

---

### Lane C — the Athanor template (agents improve the models)

The model-improvement sibling, sized to the operator's desktop:

**Phase 1 — the GGUF leaderboard** (uses Lane A's eval harness):
- Score all 24 GGUFs on the trading tasks.
- Record per-model scores in the leaderboard.
- The agents read the leaderboard and decide what to try.

**Phase 2 — the merge experiments**:
- mergekit merges two GGUF-convertible models (CPU-only, cheap).
- The merged model is scored on the eval harness.
- The agents compare against the parents and decide: keep, discard, or
  stack another merge.

**Phase 3 — distillation** (when the compute allows):
- The best-performing model generates training data (the operator's
  trading tasks with model-generated reasoning).
- SFT/LoRA on a small model (4B at Q4 fits in ~3GB — the iGPU+dGPU can
  train with aggressive offloading).
- Convert back to GGUF, score, record.

**What's NOT in scope** (honest): the Athanor paper's agents had 8×H100
per agent and ran 104 hours. Full RL + self-distillation at that scale is
a datacenter budget. The DAAVILE version = eval + merge + light SFT —
the improvement loop without the training farm.

---

## The dependency chain

```
Lane A (eval harness)
  ├─► Lane B (Harness² template) — uses eval to judge harness edits
  ├─► Lane C (Athanor template) — uses eval to score models
  └─► both feed the OptChat memory (the universe records WHY)
```

Lane A is the gate. Without a score, nothing else measures improvement.

---

## What the operator authors (the only human-in-the-loop part)

1. **The trading tasks** (10-20 questions with answers) — 30-60 min of
   operator time, the highest-leverage hour in this entire proposal.
2. **The improvement priorities** — which dimension matters most: correct
   logic-config recall? backtest reasoning? vault data lookup? code
   generation for strategies?
3. **The accept/reject calls** — the agents propose, the operator reviews
   the evidence and says yes/no (or trusts the eval score alone once it's
   calibrated).

---

## What this is NOT

- **Not a training farm.** The Athanor paper's full post-training at 8×H100
  scale is a datacenter budget. We do eval + merge + light SFT.
- **Not a SaaS.** Everything runs on the operator's desktop, in the
  operator's home directory, on the operator's models.
- **Not a framework to install.** Every piece is a DAAVILE fleet template
  + a harness plugin, using the machinery we already own.
- **Not speculative.** The eval harness is mechanical; the fleet templates
  use the composition we already have; the only novel authoring is the
  trading tasks (operator time).

---

## The ask

1. **Author the trading tasks** (the operator, 30-60 min) — the gate for
   everything.
2. **I build the eval runner** (one session) — the scorer, the leaderboard,
   the `eval` fleet command.
3. **I build the Harness² template** (one session) — the proposer/prober/
   composer roster, the lessons library.
4. **I build the GGUF leaderboard** (one session) — the Phase 1 Athanor
   template (score all 24 GGUFs, the agents read the scores).

Lanes B and C can run in parallel once Lane A exists. Each produces
append-only evidence the OptChat universe remembers.
