# NOVEL-ANGLE.md - what survives the roast, and the inversion

Date: 2026-10-26. Authored after REFUTATION.md. The refuter's verdict stands:
K1 was "a beautiful substrate in search of a tenant" whose four load-bearing
premises are each false in detail (no receipts in optchat; the wire's read
path is off by one directory for every world on this machine; the discovery
table publishes a directory as a world; the skill compaction direction is
cache-hostile). This file is the synthesis, not a rebuttal of the rebuttal.

---

## The inversion (the actual novel angle)

Every candidate so far - mine and the refuter's - accepted the question as
"which memory substrate do agents get?" and then argued about storage. Both
left the strongest asset on the table, and the refuter found it without
claiming it: **`INFLIGHT.md` is 400,629 bytes of append-only, Work-Note-keyed,
evidence-backed rows across every repo in this ecosystem. It is already the
durable research record. It already has an enforcement culture (append-only
mandates, Work-Note IDs, "every change gets a row"). It is the only artifact
in the entire stack whose whole purpose is: what was done, why, what proved
it, and who owns the next move.**

The OptChat recipe says it out loud and nobody applied it there: "the
session's durable log = the message log; the store carries only derived
state, all rebuildable from the log alone." So:

**INVERTED THESIS - the ledgers are the log; the vault is the read model.**

- The vault does not store content. It **indexes** the ledgers that already
  exist (INFLIGHT.md in every repo, plus the optchat worlds as the chat log).
- Skills stay `<name>/SKILL.md` bundles, edited in place, cache-stable by
  construction - the refuter's attack 4c is accepted in full. The chunk
  taxonomy (`primitives / failed_approaches / abandoned_artifacts`) becomes a
  file convention under the existing RAG layer, not a compaction format.
- Isolation is not a new namespace: the harness's shipped `skill-filesystem`
  rank table (project 100, `.agents` 200, custom 300, dsh-home 400,
  agents-home 500, bundled 600 - verified by the refuter) IS the ranking law.
  Per-surface vaults = per-surface rank rows, declared once, with sync tests.
- Enforcement is not prose: the shipped `sandbox-windows-acl`
  (`read-only` / `workspace-write`, fail-closed, 16 specs) is the denial
  mechanism. A test spawns a confined shell and proves the write fails -
  "test denial through the executor", the repo's own rule, which a
  no-writer-method gate violates.
- The human section gets a real writer: the app's existing
  `writeAgentFolder` path (`appDataDir()/agents/<slug>/`, soul.md + skills +
  memory READMEs already written there) is the human-section home, and the
  auditor's quarantine flow becomes the ONE legitimate agent-append channel,
  every entry carrying an `author:` line.
- Receipts are not fetched from optchat (they do not exist there); the
  receipt IS the Work-Note ID + the commit hash the row already names. When a
  hash-chained sidecar is eventually needed, it is written by the same code
  path with tmp+rename - not `appendFileSync` - and only when there is a
  writer to protect.

This kills every attack simultaneously because it stops asking the memory
store to be something it is not, and asks the ledgers to be what they
already are.

## Why this is novel and not a recombination

Consensus says impossible because: "agent memory" is a storage problem in the
literature (vector stores, world models, scratchpads); ledgers are
"bookkeeping", below the architecture's notice. Assumption inverted: a
governance artifact (the record of what was done and why, with evidence and
ownership) is a strictly better agent substrate than conversation memory,
because it survives model swaps, session death, harness rewrites, and
operator absence - all of which kill every chat log. The OptChat design
already anticipated this (the log is the truth); it just never had a log
worth trusting on the agent side. INFLIGHT.md is that log.

Novelty distance: accounting/governance mechanics x agent-memory semantics x
the shipped rank/ACL machinery - three domains never combined. And the two
things the refuter found that I missed (the rank table, the ACL sandbox) are
what make it do-able: nothing new is invented except the projection.

## What it costs

Zero model calls for the core. The index is a pure filesystem projection
(markdown front-matter + JSONL parse). Compaction is used only where the
refuter's attack 4(c) does not apply: for the "needs you" derivation, which
is derived-and-discardable, never for content anyone will read as truth.
Total new code in the first session: one reader, one projector, one config
row, one denial test.

## What it refuses (recorded as failed approaches for the chunk library)

- Skills-as-worlds / compaction-over-skill-bodies (K1 full form) - rejected:
  cache-hostile, rollback is rollback to a lossy summary, priced per edit.
- A fifth binding mechanism (K3's services.json vault rows) - rejected: two
  unlocked writers already race on that file; the rank table exists.
- Replacing opencode (K4) - rejected by operator ruling and by safety.
- Any "enforcement by API shape" gate - rejected: schema omission is the
  banned pattern in the very repo that owns the sandbox.

## The UX consequence (the operator's Apple Music / PS5 dashboard)

"Front-matter as a database, fully actionable" becomes a query over the
projection: unpushed commits, held verdicts, red gates, bank-gap minutes,
quarantine entries, the latest row per Work-Note. Every row calls a wire
method that already exists (git status, health, ledger reads) - the
dashboard is a read model with buttons, which is exactly what the operator
described. Two surfaces (app + Orca ADE) get their own rank rows and their
own views of the same log; the brain is not shared, the RECORD is.

## The build plan (first session, ordered by the refuter's own logic)

1. **Fix the lying wire** (my bug): `optchat_root()` + `memory_worlds()` emit
   logical world names (`universe`, `session-76991a46...`), the publisher's
   `worlds` list stops publishing a directory, and two tests assert a real
   world reads back and that a bare `"memory"` is never returned. Files:
   `daavile-wire.rs`, `daavfx-services.mjs`.
2. **Give the human section its writer and its ban**: extend the app's
   existing `writeAgentFolder` with an `author:` line and a `human-notes.md`
   channel; add the denial test through the ACL sandbox (read-only grant,
   vault root outside the grant, assert the write fails).
3. **Declare the rank law once**: add `~/.config/opencode/skills` as a
   `customSkillDirs` row; write the missing `skills/novel/SKILL.md` (the RAG
   layer is currently undiscoverable); record the precedence in one place.
4. **Build the projector**: markdown front-matter + INFLIGHT row parsing ->
   `~/.dsh/vaults/<surface>/index.json` (derived, discardable, rebuildable).
   Wire-method it: `vault.needsYou` first - unpushed commits, held verdicts,
   red gates.
5. **The dashboard surface**: the app's Agent realm reads `vault.needsYou`
   and renders the actionable list. Orca ADE attaches as a second client
   through the same table (phase 2, per the operator's phasing).

Steps 1-3 are under a day and three of them are corrections of things this
folder proved false. Step 4-5 are the actual build.
