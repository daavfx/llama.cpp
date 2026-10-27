# PROPOSAL.md - candidates, scored the novel way

Date: 2026-10-26. Scoring per the novel RAG prompt:
`Score = 2*I + S + 3*Novelty + 2*Grounding + 2*PurposeAgnostic - Penalty`,
maximize I subject to S >= threshold (containment). Every grounded claim cites
a chunk (a verified file); the rest is `[PRIOR - suspect]`.

---

### Candidate K1: "The vault is the memory system" - OptChat worlds as the agent/skill/soul substrate

**Consensus says impossible because:** the standard answer (opencode, and
most agent harnesses) is "skills are static markdown files, agents are
frontmatter documents, memory is chat logs" - a mutable skill store is
considered antisocial because edits destroy provenance and compaction is a
model-side trick. `[PRIOR - suspect]` on consensus strength; VERIFIED on our
own docs: the skills tree IS static markdown (AUDIT.md 1).

**Assumption inverted:** "A skill must be a document." If a skill is a WORLD
instead, editing it appends a leaf (with a receipt) instead of overwriting
prose, the view is always the current whole skill, and the store carries only
derived state - rebuildable from the log alone. OptChat already proves the
mechanism on chat transcripts; nothing in it is chat-specific except the
prompt shapes.

**Rebuild from primitives (all verified on disk):** the world store
(`tree.jsonl`/`view.json`/`raw.jsonl`, `optchat/src/store.ts:40`), the
due-order merge formula, the receipt chain (`RyiukReceipt`), the wire
(`app-wire memory.worlds/memory.read`), the discovery table.

**Recombination (distance bonus):** chat-compaction mechanics x skill-registry
semantics x the novel skill's chunk taxonomy (`primitives/failed_approaches/
abandoned_artifacts`) - three domains never combined: the chunks become LEAF
CARGO, so "this approach was tried and failed" is a first-class, citable,
compacting artifact instead of a stale paragraph.

**Safety enumeration:** pure code + filesystem under `~/.dsh`. No network, no
external state, every write atomic with a receipt. The compaction calls hit
the model (existing, gated). Reversible: the log is the truth, the tree
rebuilds. S = 92.

**Purpose-agnostic justification:** it ships as "a self-documenting skill
store with rollback" even before any agent uses it.

**Score:** 2*74 + 92 + 3*88 + 2*95 + 2*80 - 0 = **620**

---

### Candidate K2: "Enforced, not asked" - the human section is a tool-level ban with a test

**Consensus says impossible because:** "permissions for agents" universally
means ACLs/policies in prose; operators assume the trusted harness will
behave. `[PRIOR - suspect]`.

**Assumption inverted:** isolation is not a policy, it is a missing code path.
If the vault's human section is not exposed through the wire's method surface
at all (no `memory.write` method exists - verified: the bin's method set is
`runtime.describe/services.list/health/memory.worlds/memory.read/ping`, all
read-only except nothing), then "agents can't write the human section" is
enforced by the API shape, and the test is "the tool list contains no writer
for `human/`".

**Rebuild:** the `daavfx-wire` bin already serves memory read-only; adding a
writer for worlds keeps `human/` outside the writable set. One gate test:
attempt a write to a human path, assert rejection (the same pattern as the
bin's existing path-traversal rejection test, `daavile-wire.rs` tests).

**Safety:** pure code, reversible, bounded. S = 97.

**Score:** 2*61 + 97 + 3*54 + 2*90 + 2*70 - 0 = **545**

---

### Candidate K3: "Two brains, one table" - per-surface vaults with a discovery layer

**Consensus says impossible because:** shared agent configs are the norm;
per-surface isolation is considered duplication and drift.

**Assumption inverted:** the drift is the point. `services.json` already
describes every live surface in one table; adding a `vault` row per surface
(`~/.dsh/vaults/<surface>/...`) makes isolation the default while discovery
stays unified. The wire client that already reads one table now reads "which
vault is this session bound to" from the same file.

**Rebuild:** the publisher (`daavfx-services.mjs`) merges rows
non-destructively - verified; the app's realm sections already switch
surfaces (`AgentView.tsx` activeMainPage); the Studio already carries
per-persona bindings (model/skills/mcps/soul - verified in
`AgentSessionContext.tsx`).

**Safety:** pure config + filesystem. S = 95. Grounding: 90.

**Score:** 2*66 + 95 + 3*62 + 2*90 + 2*72 - 0 = **553**

---

### Candidate K4 (rejected): replace opencode with our own harness wholesale

Safety fails: the harness (dsh) boots sessions, but the operator's daily
driver is the opencode TUI with 20+ providers and 8 MCPs; replacing it means
porting all of it in one pass. The operator already ruled: keep their base,
level OUR surfaces. REJECTED by safety containment, recorded as a failed
approach for the chunk library.

---

### Ranking

K1 (620) > K3 (553) > K2 (545) > K4 (rejected). They compose: K3 is the
topology, K1 is the substrate inside each vault, K2 is the enforcement rule
inside the substrate. Next: the refuter gets one pass at all of it.
