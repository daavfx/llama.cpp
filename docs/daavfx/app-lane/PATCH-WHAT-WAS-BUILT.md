# PATCH-WHAT-WAS-BUILT.md - exact replacements for harness/WHAT-WAS-BUILT.md

Date: 2026-10-26. Apply mechanically: replace each OLD block with the NEW
block, keep everything else. ASCII only.

!! PARTLY STALE 2026-11-01. Verified: 1 of 4 OLD blocks match the current
   `plans/loop/WHAT-WAS-BUILT.md` (Patch 2 only). Patches 1, 3 and 4 miss -
   Patch 1 by a single character (em-dash vs `--`), which makes it a silent
   no-op rather than a visible failure. Re-derive the OLD blocks from the
   live file before applying.
   Note the target lives at `plans/loop/`, not `harness/`: `harness/` is a
   working-tree deletion that has never been committed, so both paths exist
   at HEAD.

## Patch 1 - the OptChat honest-state paragraph (now false)

The doc says the compaction awaits a real chat. It fired on 2026-10-25 and
left a store on disk. The auditor caught this too (stage1-audit/harness.md,
C16: "fired on disk 2026-10-25").

OLD (the "Honest state" bullet in the OptChat section):

```
- **Honest state**: the mount + zoom registration are proven; the compaction
  path (leaf/merge calls + the view replacement) awaits a real chat crossing
  the pressure threshold - the first daavile session long enough to hit it
  is the acceptance test.
```

NEW:

```
- **Honest state**: H3 FIRED. A real session crossed the threshold on
  2026-10-25 (two prompts, thresholdRatio 0.0005 / retainRatio 0.0002 /
  headroomTokens 512 in the daavile profile) and the store materialized on
  disk at `~/.dsh/memory/memory/session-76991a46-be0f-4f6d-b2e3-9cbe0a05c957/`:
  `tree.jsonl` (4 leaf lines), `view.json` (the whole-conversation view),
  `raw.jsonl` (the leaf sidecar), `covered.txt`. The universe world
  distilled its notes in the background (`memory/memory/universe/`). The
  leaf/merge calls ran on the throttled NVIDIA free tier - throughput, not
  logic, was the only limit. The auditor receipt-verified the proof
  (auditor-ISAYY/stage1-audit/harness.md C16).
```

## Patch 2 - the composition bullet (the live boot proof)

OLD:

```
- **The composition**: the daavile profile's `compaction-basic` row now
  mounts the OptChat engine. Live boot mounts clean (5.5s, zero activation
  warnings).
```

NEW:

```
- **The composition**: the daavile profile's `compaction-basic` row now
  mounts the OptChat engine. Live boot mounts clean (5.5s, zero activation
  warnings), and the profile additionally carries: gateway-url discovery,
  `DAAVILE_HEADLESS=1` for the no-TUI boot, the retained-threshold tuning
  above, the deepseek-account stack (authenticates; the account itself is
  out of balance), and the llm-pi-ai twin woken with the opencode + nvidia
  routes (see `../app-lane/WIRE-TRANSPORT.md`).
```

## Patch 3 - extend the INFLIGHT index

OLD (the table rows):

```
| zai-92 | OptChat memory core - worlds + universe, clean-room TS port |
| zai-93 | OptChat integration - compaction seam + zoom + universe distiller |
```

NEW (append after zai-93):

```
| zai-92 | OptChat memory core - worlds + universe, clean-room TS port |
| zai-93 | OptChat integration - compaction seam + zoom + universe distiller |
| zai-88/89/90/91 (app repo) | Model selection dropdown, the three fake lanes killed, ChatStatusBar honesty + tests, foundry B4 port fix |
| WK-20261022-harness-gateway-link (harness repo) | Agent-driven sessions: gateway-url discovery file, DAAVILE_HEADLESS boot, the direct wire client |
| WK-20261025-harness-wire-2 (harness repo) | Wire Phase 2: services --ensure self-healing, the optchat-memory discovery row |
| WK-20261026-opencode-zai-92/93 (app repo) | daavile-wire bin (the app's own native wire), the in-app OptChat Memory page |
```

## Patch 4 - the repository map gains one row

OLD (the table):

```
| `daavfx/quantum-dashboard-fx` | The Tauri app (Agent / IDE / Quantum) |
```

NEW:

```
| `daavfx/quantum-dashboard-fx` | The Tauri app (Agent / IDE / Quantum); `src-tauri/src/bin/daavile-wire.rs` is its native wire bin |
```

## Why these patches exist

The audit's action list item 3 requires the doc corrections; these four are
the subset that touches this lane's claims. The moe-lab and loader
corrections stay with their own lanes. After applying, append an INFLIGHT
row in llama.cpp-abelianIUT naming
`docs/daavfx/app-lane/PATCH-WHAT-WAS-BUILT.md` as the source.
