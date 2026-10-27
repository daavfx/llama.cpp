# SYNTHESIS.md - the closest plan, grounded in what exists

Date: 2026-10-27. Author: the composer lane, after AUDIT ->
PROPOSAL -> REFUTATION. This file is what the operator asked for: the
overview, the proposal, and the refutation, combined into the closest plan
that concentrates what we already have plus what we plan to build, with the
folder question answered. ASCII only.

---

## 1. The verdict in one page

**The research framing is right; the proposal's grounding table was wrong in
five of nine rows.** The refuter proved it on disk: `tokenMeter` is a
dependency string the engine never reads; `covered.txt` is a four-byte
integer watermark; `main.jsonl` is the universe notes log, not the
transcript; `push.ts` has no caller; the wire's read-path fix has a guard
test that cannot fail. Of the two scores, 617 and the sibling lane's 620
for the same thesis, neither is the number that matters - what matters is
that both plans re-derived the primitives from scratch and got different
answers from the same files.

**The honest diagnosis behind the operator's instinct is confirmed and
priced.** The proof-loop receipt is the strongest finding in the whole
folder: with `thresholdRatio: 0.0005` and `retainRatio: 0.0002`
(cordis.patch.yml:44-45) on a 131K window, threshold = 65 tokens while a
single 512-byte leaf renders at ~128 tokens - so compaction re-fires on the
very next request, forever. Those knobs are the H3 proof values; they were
never reverted, and the comment on line 36 says 0.005 (a factor of ten
above the value on line 44). That is the concrete, measurable, on-this-disk
version of "extra complex and brittle."

**What is actually new** is much smaller than either proposal claimed: one
new tier (`pinned`), one new field (`status`, as an appended entry, never an
edit), and one EMA calibration. Everything else - the compiled view, the
state object, the provenance via `raw.jsonl`, the append-only world log -
already ships.

---

## 2. The primitive table (the artifact that prevents the collision)

The table now lives at `../PRIMITIVES.md` - one copy, one verification date.
The rows below are its content as of 2026-10-27; edit the PRIMITIVES file,
not this section. `[PRIOR - suspect]` where neither the transcript
nor a file can reproduce the value.

| # | Primitive | File:line | What it does | What it does NOT do | Status |
|---|---|---|---|---|---|
| 1 | `tokenMeter` | optchat/src/engine.ts:173 | names a dependency in `inject` | nothing reads it; it is not "injected" as a capability | exists as a string |
| 2 | `estimateMessage` | llm/token-meter/src/estimate.ts:88 | gives a per-message token estimate, `char/4` + 4+4 | per-model accuracy; the brainstorm calls this primitive miscalibrated | exists, callable, unused by optchat |
| 3 | `LogEntry` | optchat/src/store.ts:18-25 | `{i, kind, text, size, date}` | no status, no supersedes, no token twin of `size` | shipped |
| 4 | `LogEntry.size` | store.ts:23,63 | utf8 byte length | never read by any code in the package; write-only metadata | shipped, free slot |
| 5 | `covered.txt` | store.ts:152-158 | an integer watermark | carries no sizes, costs, ids, or rows | shipped |
| 6 | `main.jsonl` | store.ts:114-118 (header) | the universe notes log; the only append-only path (`appendLog` callers: eval-bridge.ts:65, engine.ts:343) | it is NOT the conversation transcript; the session log lives in the session and this package cannot read it | shipped, misread by both proposals |
| 7 | `renderChatView` | engine.ts:69-74 | compiles `TreeLine[]` into the `<chat>` view block | nothing protects a line from the due-order merge | shipped |
| 8 | `duePairs` / `due = (T+1)/2^l - i` | tree.ts:22,35-61 | the merge order, purely by age | no value class, no pin, no `LogKind` input | shipped |
| 9 | `push.ts` | packages/compaction/optchat/src/push.ts | retained-for-fidelity scaffolding | has NO caller in the package | dormant |
| 10 | `raw.jsonl` | store.ts:121-126,133-144 | every leaf's verbatim source; `zoom`'s target | n/a - this is the provenance story, and it works | shipped |
| 11 | The native wire | app:src-tauri/src/bin/daavile-wire.rs | 10 Rust tests; `memory.worlds`/`memory.read` read the real worlds after the off-by-one fix | no `raw.jsonl`, no byte/token total, no write method; the guard test cannot fail | shipped with a vacuous test |
| 12 | 14 optchat specs | harness packages/compaction/optchat/tests/{optchat,e2e-proof}.spec.ts | 10 `it(` + 4 `it(` | none of them pins a budget/policy decision | verified |
| 13 | Proof knobs | daavile-cli/cordis.patch.yml:44-46 | threshold 0.0005, retain 0.0002, headroom 512 | cannot converge (65-token threshold vs ~128-token leaf); line 36's comment says 0.005 (10x) | live, wrong |
| 14 | Compaction route | cordis.patch.yml:79-82, engine.ts:293-298 | the conversation's own route (`nvidia`/`z-ai/glm-5.3-flash`, HTTPS) | `compactionProvider`/`compactionModel` are unset, so a cloud call per leaf | undeclared |
| 15 | Merge cost | engine.ts:240-263 | serial merges, each re-rendering the whole view | ~125 merges x ~24K tokens ~= 3.0M prefill tokens per batch `[PRIOR - suspect]` on decode rate | unpriced |
| 16 | `LogKind` | store.ts:16 | shapes the leaf prompt (`<kind>: <input>`, engine.ts:34) | never enters a budget decision | unused lever |
| 17 | The study substrate | `~/.local/share/opencode/opencode.db` | 26.83 GB + 13.5 MB WAL | no extraction, no schema confirmed, no mapping into `LogEntry` | unexamined |
| 18 | Every section-1 number | BRAINSTORM.md sections 1,3,4 | - | none reproducible in this tree (18 models, 57/21/73/47.8, 384 slots, 90.60/64.80/55.00, ~5,100/~300, PPL 5.75->2,464, the whole PR-map) | `[PRIOR - suspect]` |

---

## 3. The directory decision

```
docs/daavfx/
  README.md            the lane index; not in the index = not a lane
  REPO-MAP.md          ours-vs-upstream inventory (unchanged)
  plans/               <-- THE MERGE, done as moves not copies
    PRIMITIVES.md      the table in section 2 above, moved here
    context/           was plans/context/
    vault/             was plans/vault/
    loop/              was harness/  (onboarding + Lane A contract)
  app-lane/            transport + UI record (unchanged; Track A boundary)
  skills/novel/        the RAG chunk library (unchanged; add SKILL.md)
  moe-lab/ break1650/ overlay/ experimental-dgpu/   campaign records (unchanged)
```

Defense, in four lines:
1. Duplication is cured by PRIMITIVES.md, not by one folder. The 620-vs-617
   collision happened because each plan re-derived the primitives; a table
   with file:line and a date makes the next plan a diff.
2. Do NOT merge into the harness repo (`shared/daavile_harness/daavilefx_harness`).
   That repo's rules (per-file 100% coverage, keyless snapshot per
   model-visible change, doc-sync gates) reject a design folder. Its code is
   the target, not the home. `plans/loop/` here is a plan lane; move it to
   `plans/loop/` and leave the repo's own docs alone.
3. Keep `app-lane/` separate for the strongest reason: `daavile-wire.rs` is
   Track A territory. Any plan that needs a new wire method is authored in
   `app-lane/` and handed across the lane boundary.
4. Re-index README.md the same day - it is eleven days stale and misses five
   directories, which is how a sixth lane got created without a collision
   check.

---

## 4. What gets built, in order (all of it verified-doable on disk)

Six items. The first four are the refuter's list with the merge applied; the
last two are what this lane adds.

### Step 1 - optchat store: atomic writes and loud failures

File: `packages/compaction/optchat/src/store.ts` (~40 lines).
- `saveView` (store.ts:99) and `markCovered` (store.ts:157) go tmp+rename
  (the pattern daavile-wire.rs:279-282 already implements).
- `loadView` (store.ts:109-111) stops converting a parse error into `null` -
  the one path in the package that silently deletes a world's memory.
- `coveredCount` (store.ts:152-154) stops converting a torn read into 0
  (currently causes double-leafing and stale `zoom`).
- `readLog` (store.ts:74-78) survives one bad line.
- Specs: a torn view file must fail loudly; a torn readLog line is skipped,
  not fatal; `markCovered` leaves no `.tmp` residue.
Why first: until this lands, "the log is the truth" is false in the one
direction that matters.

### Step 2 - engine: make the token real and pin the route

Files: `packages/compaction/optchat/src/engine.ts`,
`packages/bundle/daavile-cli/cordis.patch.yml`.
- Wire the meter: read `this.ctx.tokenMeter` once (engine.ts:173 already
  names it) and persist `estimateMessage`'s value per leaf as the token twin
  of the byte `size` store.ts:23 already carries and nobody reads. One call
  site; every later policy is denominated in whatever unit this lands in,
  so it lands first.
- Pin the compaction route: add `compactionProvider`/`compactionModel` to the
  patch so the compaction call stops silently riding the conversation's
  cloud route (engine.ts:293-298) and becomes a declared local target (the
  small fast quantized model on its own port, per the operator's existing
  fleet).
- Add `maxTokens` so the 512-byte clamp (engine.ts:331) is a generation cap
  instead of a post-hoc truncation of an already-paid-for response.
- Fix the patch: revert threshold/retain to base defaults (0.8/0.16 per
  compaction-basic/src/config.ts) or keep proof values but correct the
  line-36 comment and add a "PROOF ONLY - revert" banner.
- Spec: a session with a stubbed meter records a token twin per leaf; the
  route resolution prefers the explicit pair.

### Step 3 - the guard test that can fail

File: `apps/quantum-dashboard-fx/src-tauri/src/bin/daavile-wire.rs`.
- The `memory_worlds_emits_logical_names_not_the_parent_dir` test defines its
  own local `fn scan` and a temp layout one segment shallow, so it cannot
  fail for the bug it is named for. Rewrite it to call the production
  `memory_worlds()` against a temp home (`USERPROFILE` set for the test), a
  layout that includes the doubling segment, and a trapped "memory" dir with
  artifacts (which is what actually broke).
- Delete the stray no-op at daavile-wire.rs:490-497 (leftover debug block).
- Also: state the auth position. The wire currently binds loopback with no
  token; the discovery row for the engine already names
  `token-in-runtime-file`. Either the memory methods gain the same or the
  README states plaintext-loopback as the accepted posture for this surface.
- Why third: a fix with no test that can fail is not a fix.

### Step 4 - `LogKind` into the merge order (the first real feature)

File: `packages/compaction/optchat/src/tree.ts`.
`LogKind` (store.ts:16) exists and is used only to shape the leaf prompt.
Make `duePairs` prefer preserving `user` and `agent` lines over `tool`,
`echo`, and `raw` observations - R6 with the smallest blast radius: no model
call, no status field, no new lane. This is the first thing worth building
that is not a correction.

### Step 5 - the status tier, appended not edited

File: `packages/compaction/optchat/src/store.ts` + `tree.ts`.
Add `'supersede'` to `LogKind`; a supersede is an APPENDED entry (the store
header requires the tree be a pure function of the log alone, so in-place
status mutation is forbidden) carrying the new fact and the id of what it
supersedes; the leaf prompt treats the pair as active/superseded and never
blends. This is R3 in the cheapest honest form. Spec: a contradicted leaf
supersedes and the view shows the active one; `zoom` still reaches both.

### Step 6 - the EMA calibration and the measurement kit

File: `packages/llm/token-meter/` (own the ratio) or optchat engine (fold
usage). Keep `char/4` as the prior, measure `actual/estimate` per request,
blend 0.7/0.3 (the transcribed PR map's numbers are priors, but the EMA
*shape* is the only honest way per-item cost becomes knowable pre-hoc).
Then the kit from BRAINSTORM.md section 6, on our own transcripts: canaries
at t=0, probes at t=10/30/50, contradiction count, cache-hit ratio, cost
per retained fact. Extraction of the 26.83 GB substrate is a task, not a
footnote - decide whether opencode's `session`/`message`/`part` tables or the
daavile gateway's session store is the cheaper source.

---

## 5. What we are explicitly NOT building (recorded as assumptions killed)

- Skills-as-worlds / compaction over skill bodies. Killed in
  `plans/vault/REFUTATION.md` attack 4 for being cache-hostile and
  rollback-to-lossy. Unchanged here.
- "Compaction as a trained policy." Section 3 shows per-item exact cost
  arrives post-hoc and does not decompose. Killed until the EMA lands.
- R2's three-tier bounded-state transplant. Killed until step 3 exists; the
  transcription's own warnings (naive bounded policies are catastrophic) are
  carried forward as `[PRIOR - suspect]`.
- Provider-native compaction. Killed on portability (opaque encrypted
  checkpoint, provider/model-locked).
- A fifth binding surface in services.json for vault rows. Killed: two
  writers already race on that file without a lock; the harness's
  skill-filesystem rank table is the ranking law.

## 6. The Orca drift check (queued, not rushed)

The operator's last ask: routinely diff `github.com/stablyai/orca` against
our fork `daavfx/daavilefx-ade` for drift. This gets its own sub-agent run
after this file lands - it needs a clone/fetch of upstream and a
bundle-diff, and the operator said no rush. Track it as an `app-lane/`
recurring item, not a plan item.

## 7. Index update (part of this commit, not a footnote)

- Move `plans/context/` -> `plans/context/`, `plans/vault/` ->
  `plans/vault/`, `plans/loop/` -> `plans/loop/` (moves, not copies; no content
  deleted).
- Write `plans/PRIMITIVES.md` from section 2.
- README.md gains all eleven directories in the lane index and the rule:
  not in the index, not a lane.
