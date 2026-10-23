# moe-lab - running big MoE models on small GPUs

The lab for the LFM2.5-8B-A1B on GTX 1650 campaign (2026-10-20/21) and for
whatever model comes next. One folder holds everything the campaign produced:
the plan, the measured results, the destructive experiments, the control-plane
design, the research notes, and the manifests of what was changed in the fork.
The next campaign is Flint; its plan is `FLINT-CAMPAIGN.md` and it has not
started.

The overlay's own docs (WIRE.md, BENCH.md, DAVFX-BUILD.md,
overlay-vs-upstream.patch) stay one level up in docs/daavfx/ - they belong to
the daavfx overlay, not to this lab.

## START HERE

1. **RESULTS.md** - the one-page loot: two proven production configs (one
   command each), the established thesis, the full falsification ledger, and
   the Model X-Ray and Surgery Kit procedure for the NEXT MoE model.
2. **FORK-CHANGES.md** - every change this campaign made to the fork
   (C++ telemetry, env knobs, build tree, tooling) so a future coder can see
   what is ours and what is upstream.
3. **INFLIGHT.md** (fork root) - the ledger: 30 rows, one per change, in
   chronological order, with evidence and status.

## The documents

| File | What it holds |
|---|---|
| RESULTS.md | Production configs, thesis, falsification ledger, X-ray kit procedure |
| FLINT-CAMPAIGN.md | Next-model plan: hypotheses, phases 0-5, stop rules, metrics ledger (not started) |
| FORK-CHANGES.md | Manifest of every in-tree change (C++, env knobs, tools, build, Flint worktree) |
| GTX1650-LFM25-CAMPAIGN.md | Master plan: verified ground truth, the bandwidth wall, phases 0-4, the unified-silicon fabric verdict, the measured state of every phase |
| FOUNDRY.md | The destructive arm: F1-F6 teardowns, F100+ crazy registry, destruction budget, F1 cliff map, F2 ghost verdicts, C++ round verdicts, the accepted win |
| LIVING-KERNEL-DESIGN.md | The control plane (CLOSED by arithmetic, kept as the record): two-plane split, tiered control, policy object, LK-1..LK-6, REVIEW-1/REVIEW-2 amendments |
| CPU-MISS-FALLBACK-DESIGN.md | The per-layer cache policy design and why its precondition failed (flat reuse profile) |
| TYPED-DECISIONS.md | Jev / JEPA / Gemini-Embedding research and the 1-token typed-readout recipe |

## The tooling (in scripts/daavfx/, repo-root relative)

| Tool | Purpose |
|---|---|
| launch-llm.ps1 | One-command launcher for the two proven modes; `-Stop` for hygiene |
| phase1-bench-matrix.ps1 | The go-gated Phase 1 bench matrix with VRAM sampling and a run manifest |
| gguf-surgeon.py | MoE surgery: inspect / roundtrip-test / amputate (--policy, --ghost, --ghosts, --f16, --mass) |
| quality-harness/ | The 12-task agentic judge (taskset, runner, scorer) - the only judge of a surgery result |

## Status

Campaign closed 2026-10-21 with the artifacts above. Nothing left running.
Next: Flint. The plan is `FLINT-CAMPAIGN.md`; it is gated on the operator
freeing the PC. The X-ray kit still answers the first question: does Flint
have a harvestable cold tail, or is it load-balanced like LFM2.5-8B-A1B?
