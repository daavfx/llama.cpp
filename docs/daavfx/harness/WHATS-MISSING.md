# DAAVILE Harness — What's Missing and What's Next

Honest gaps, ranked by impact. Everything here is scoped against what we
already own and what the operator's compute can actually run (iGPU+dGPU,
not a datacenter).

---

## Tier 1 — the acceptance tests (prove what's shipped)

### 1. The OptChat end-to-end proof

The engine mounts, zoom registers, the composition is live. But the
compaction path — leaf lines, due-order merges, the view replacing the
transcript — has never fired in a real chat because the pressure threshold
hasn't been crossed.

**What it needs:** one daavile session long enough to hit the compaction
threshold (a real coding task with tool calls, not a hello-world). When it
fires, the transcript gets replaced by the `id+n|text` view, `zoom` becomes
available, and the universe distiller runs for the first time.

**What to watch for:** the replacement user message in the transcript (the
view block), the zoom tool responding, the universe world gaining notes
under `~/.dsh/memory/universe/`.

### 2. The fleet persona end-to-end proof

The persona loop (shim → cortex_run → AgentLoop → report → worker_done) is
wired and tested at the unit level, but the Rust `cortex_run` tool was
shipped without a live LLM run (the standing directive). The first real
dispatch exercises the full loop.

---

## Tier 2 — the improvement loop (the new stuff)

### 3. The Harness² fleet template

**The idea** (from the paper + our own lane history): agents that improve
the harness itself — prompts, skills, tool guidance, guardrails — by
proposing edits, probing with contrast runs, composing what demonstrably
changed behavior, and recording evidence-backed lessons.

**What we already own:**
- The fleet CLI + templates (dispatch + orchestrate)
- The sandbox (dsh-sandbox-local)
- The gauntlet (a contrast judge — "did the behavior change?")
- The INFLIGHT discipline (the research record)
- The persona loop (cortex_run — the brain)

**What's missing:**
- **The eval harness**: a scoring harness for trading-relevant tasks
  (the agent answers questions about the operator's actual data/logic
  configs/vault). The gauntlet needs concrete tasks to judge.
- **The lessons library**: a per-workspace `harness-lessons.jsonl` —
  append-only, evidence-backed entries: `{ context, edit, contrast
  evidence, status }`. The Harness² paper's library, in our format.
- **The fleet template**: proposer → prober → composer as a three-agent
  roster. The proposer reads the task + library and proposes harness diffs;
  the prober runs contrast pairs; the composer judges and records.

### 4. The Athanor model-improvement fleet template

**The idea** (from the paper, adapted to our compute): agents that improve
the MODELS — evaluating the operator's 24 GGUFs on trading-relevant tasks,
merging the best pairs (mergekit = CPU), distilling, and re-evaluating in a
loop the agents drive.

**What we already own:**
- 24 GGUF files (0 mapped, but the models are there)
- llama-server (found at the expected path)
- The sandbox + the fleet machinery
- The cortex personas (the researcher brains)

**What's missing:**
- **The eval harness** (shared with #3): the scoring harness that produces
  comparable scores across GGUFs. This is the prerequisite for both lanes.
- **The mergekit wrapper**: a thin CLI around mergekit (CPU-only) that
  merges two GGUF-convertible models, converts back to GGUF, and registers
  the result.
- **The GGUF→HF→GGUF pipeline**: convert to HF for training/merging, then
  back. This is the heaviest engineering item (quantization awareness).
- **The held-out suite**: trading tasks the agents never see during
  improvement, for honest scoring.
- **The compute reality check**: the operator's iGPU+dGPU can run inference
  for eval (a 4B model at Q4 = ~3GB, fits), and mergekit runs on CPU.
  Full post-training (LoRA/QLoRA) is tight but possible for small models
  with aggressive offloading. The Athanor agents had 8×H100; we have a
  desktop. Scope: eval + merge + distill, not full RL.

**The unified picture:**

```
Harness²: agents improve the HARNESS (prompts, skills, tools)
Athanor:  agents improve the MODEL (eval, merge, distill)
OptChat:  agents remember WHY (the world tree)
```

All three = the same fleet-template pattern: propose → probe → compose →
record. One library format serves both.

### 5. The eval harness (the prerequisite for both)

This is the single highest-leverage item to build next. Without it:
Harness² can't judge edits, Athanor can't score models, the fleet can't
measure improvement.

**What it looks like:**
- A JSONL task file: trading-relevant questions with verifiable answers
  (logic config parameters, vault data facts, backtest results, strategy
  reasoning).
- A scorer that runs the tasks against a model (via ctx.llm.stream or
  llama-server directly) and produces a score.
- A leaderboard: `~/.dsh/memory/evals/<model>.jsonl` — append-only, per
  model, per run.

**Sizing:** the task authoring is the hard part (the operator knows what
"good" looks like for trading tasks). The scoring runner is mechanical.

---

## Tier 3 — quality-of-life (the polish)

### 6. The IDE-realm loading/retry state

The app's IDE iframe shows a dead "localhost refused to connect" during
rebuilds. A small UI lane: a loading/retry state instead of a dead frame.

### 7. The linked-resolution-matrix hang

`linked-resolution-matrix.spec.ts` hangs on this machine (15+ min, zero
test progress) with and without any of our changes. Needs its own triage
session — the fixture symlink farm on Windows is the suspect.

### 8. The fork pin lag

The app's `vendor/daavilefx.source.json` pin lags the fork head when new
fork commits land between deliberate updates. Current lag: 1 commit (the
otel diet). Bump on the next deliberate engine update.

### 9. The fork CRLF phantoms

15,377 phantom-modified files (line-ending noise from `core.autocrlf=true`).
Harmless (pathspec commits avoid them) but noisy in every `git status`.
A one-time `git add --renormalize` or a `.gitattributes` sweep would fix it.

### 10. The main.rs bridge registrations

The P1 orca_bridge registration lines (mod + 3 commands) ride uncommitted
with the next main.rs committer. Coordinate with the coder's lane.

---

## The serving-stack research note

### SGLang HiCache (parked)

HiCache extends prefix caching to CPU RAM (L2) and external storage (L3):
15.5× input throughput, ~98% cache hits on multi-turn conversations. The
OptChat view's cache-stability design (§3.3 of the recipe) is the
client-side counterpart.

- **Cloud models:** the provider handles caching; OptChat's stable-prefix
  design already maximizes it.
- **Local models:** llama.cpp has single-slot prompt caching only. Swapping
  llama-server → SGLang with HiCache enabled would give the OptChat view its
  full payoff on-device (98% hit = the recipe's design exactly). SGLang
  doesn't serve GGUF, but the models can convert.

**Not actionable today.** Parked as the serving-stack upgrade path for when
local model inference becomes the bottleneck worth optimizing.

---

## The dependency graph

```
#5 (eval harness) ──► #3 (Harness² template)
                  ──► #4 (Athanor template)
#1 (OptChat proof) ──► confidence in the memory system
#2 (persona proof) ──► confidence in the orchestration

#3 + #4 ──► the self-improvement loop
#5 is the gate for everything in Tier 2
```

## What I'd build next, in order

1. **The eval harness** (#5) — the gate. Author 10-20 trading tasks, the
   scoring runner, the leaderboard. Sized for one session.
2. **The Harness² lessons library + template** (#3) — uses the eval harness
   to judge contrast runs. The fleet template is composition + orchestration.
3. **The Athanor GGUF eval + merge template** (#4) — uses the same eval
   harness to score the 24 GGUFs. mergekit for the merge experiments.

Each is one session. The eval harness is the unlock for both.
