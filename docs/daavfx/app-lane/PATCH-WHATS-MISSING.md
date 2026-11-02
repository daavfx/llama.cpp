# PATCH-WHATS-MISSING.md - exact replacements for harness/WHATS-MISSING.md

Date: 2026-10-26. Apply mechanically. ASCII only.

!! STALE 2026-11-01 - DO NOT APPLY AS WRITTEN. Verified:
   0 of 3 OLD blocks match the current `plans/loop/WHATS-MISSING.md`. This
   file was written against `harness/WHATS-MISSING.md`, which has since been
   moved to `plans/loop/WHATS-MISSING.md` AND independently edited. Patch 1's
   near-miss is a single character - the target uses an em-dash where this
   file has `--`, so `str.replace` silently no-ops. Re-derive the OLD blocks
   from the live file before applying; do not trust the text below.
   The target also contains 53 non-ASCII characters, which this file's own
   "ASCII only" instruction forbids.

## Patch 1 - Tier 1 item 1 is DONE (delete the gap, keep the watch list)

OLD (the whole item):

```
### 1. The OptChat end-to-end proof

The engine mounts, zoom registers, the composition is live. But the
compaction path - leaf lines, due-order merges, the view replacing the
transcript - has never fired in a real chat because the pressure threshold
hasn't been crossed.

**What it needs:** one daavile session long enough to hit the compaction
threshold (a real coding task with tool calls, not a hello-world). When it
fires, the transcript gets replaced by the `id+n|text` view, `zoom` becomes
available, and the universe distiller runs for the first time.

**What to watch for:** the replacement user message in the transcript (the
view block), the zoom tool responding, the universe world gaining notes
under `~/.dsh/memory/universe/`.
```

NEW:

```
### 1. The OptChat end-to-end proof - DONE (2026-10-25)

The compaction fired in a real session. Store on disk:
`~/.dsh/memory/memory/session-76991a46-be0f-4f6d-b2e3-9cbe0a05c957/`
(`tree.jsonl`, `view.json`, `raw.jsonl`, `covered.txt`); the universe world
distilled notes under `memory/memory/universe/`. Receipt-verified by the
auditor (stage1-audit/harness.md C16). Still worth doing once the free tier
is not the bottleneck: a long session with tool calls (the leaf/merge calls
throughput-bound on the NVIDIA free tier at ~2.5 min/turn), and the
`zoom(id, n)` tool driven live to confirm the raw-leaf sidecar path.
```

## Patch 2 - Tier 2 item 5 is BUILT (mark it, point at the code)

OLD:

```
### 5. The eval harness (the prerequisite for both)

This is the single highest-leverage item to build next. Without it:
Harness^2 can't judge edits, Athanor can't score models, the fleet can't
measure improvement.
```

NEW:

```
### 5. The eval harness - BUILT (2026-10-22, auditor-verified C47)

`packages/eval/eval-adapter/` in the harness repo: `recordFromMetrics` /
`recordFromCard` / `recordFromQuality` -> `upsertEval` (idempotent,
source-keyed) -> `readLeaderboard` / `rebuildLeaderboard`. 16 DAAVILE trading
tasks in `trading-tasks.ts`, the mechanical scorer in `trading-scorer.ts`
(exact / numeric / keyword 40% threshold), Bridge 2 (`eval-bridge.ts`) feeds
the universe. The shipped axis-C payloads now carry synthetic figures
(`50b1a6d0`, ISAYY Batch 0 - the sealed reference figures are out).
Remaining: run the leaderboard against a live model end to end (the router
was never captured), then Harness^2 contrast runs on top of it.
```

## Patch 3 - Tier 3 gains the two real new gaps and the wire lane

Insert after item 10 (before the serving-stack note):

```
### 11. The app's native wire boot line (Phase 3, gated)

`daavile-wire` runs standalone and publishes itself into
`~/.daavfx/services.json`. When the stable binary lands, one line in
`src-tauri/src/main.rs` spawns it at app boot so the wire is native instead
of manually started. Design and current state:
`../app-lane/WIRE-TRANSPORT.md`.

### 12. Reasoning-token thoughts (specced, three lines, two crates)

The chat's "thought" shows route metadata only; llama-server emits
`reasoning_content` for the think-capable families but the app drops it:
`daac/src/agent/agent.rs:14` (LlmFn returns a bare String; AgentStep has no
reasoning field), `premium_backend/src/cortex/agent_bridge.rs:631` (parses
only `message/content`), and the step JSON mapping in `agent_commands.rs`.
Owner decision required: daac is its own repo (shared-crates versioning) and
premium_backend is Track A's live lane.

### 13. The reasoning figures in the beam

The 77-79% thinking tax is the largest measured cost on the box and the
least challenged number in the corpus (auditor-ISAYY FINAL-REPORT section 3,
"the unclaimed lever"). Target for the next brainstorm, not a build item.
```

## Patch 4 - the dependency graph gains the wire edge

OLD:

```
#5 (eval harness) --> #3 (Harness2 template)
                  --> #4 (Athanor template)
```

NEW:

```
#5 (eval harness, BUILT) --> #3 (Harness2 template)
                          --> #4 (Athanor template)
#wire (Phase 2, BUILT) --> every agent surface talks to the app through one table
```

After applying, append an INFLIGHT row in llama.cpp-abelianIUT naming
`docs/daavfx/app-lane/PATCH-WHATS-MISSING.md` as the source.
