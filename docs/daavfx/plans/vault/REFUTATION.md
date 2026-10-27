# REFUTATION.md - the hired roaster's pass at AUDIT.md + PROPOSAL.md

Date: 2026-10-26. Author: REFUTER (the auditor lane, at the operator's
request). Read AUDIT.md and PROPOSAL.md in full first; every attack below cites
a file I read on disk in this session. Anything I could not verify is tagged
`[PRIOR - suspect]`, per the house rule.

---

## VERDICT

The proposal is a **beautiful substrate in search of a tenant** - K1 scores
itself 620 on numbers it made up, and the biggest hole is that **almost nothing
in the "verified on disk" receipt table is actually true for the thing K1 wants
to build on**: the OptChat world store has no receipt chain (it does not exist -
`store.ts` has no receipt code anywhere in the package), the wire bin's memory
methods cannot read the worlds that actually exist on this machine
(`memory.read("universe")` returns nulls - the store nests one level deeper than
the reader looks), the discovery table publishes a world list that is wrong
(`worlds: ["memory"]` is a directory, not a world), and the "agent shape" the
vault is supposed to host already has two shipped, tested implementations on
disk that the audit never mentions (the harness's `dsh-skill-filesystem` +
`dsh-tool-skill` registry, and the app's own `AgentSessionContext.tsx` soul.md
writer). K1 is a rewrite of the compaction engine's file layout dressed as a
governance architecture, its S=92 "safety" score is fiction because the writes
it calls atomic are not atomic (`writeFileSync`/`appendFileSync`, no locking,
no rename - the exact pattern `daavile-wire.rs:274-277` had to implement by
hand for `services.json`), and its human-section enforcement is claimed to come
free with the API shape while a Windows ACL sandbox that would actually deliver
it sits unread in the harness repo. K2 (545) is under-scored and is the only
candidate worth anything; K3 (553) ships a drift problem it calls a feature
with no mechanism to reconcile it.

---

## ATTACKS

### 1. The receipt chain does not exist. PROPOSAL.md lists it as a verified
primitive.

**Claim attacked** (PROPOSAL.md:27-29): "Rebuild from primitives (all verified
on disk): the world store (`tree.jsonl`/`view.json`/`raw.jsonl`,
`optchat/src/store.ts:40`), the due-order merge formula, **the receipt chain
(`RyiukReceipt`)**, the wire (`app-wire memory.worlds/memory.read`), the
discovery table."

**Why it fails.** I grepped the whole optchat package (`packages/compaction/
optchat/`) for `receipt` - zero hits in `src/`, zero in `tests/`. The package
contains exactly six source files (`bytes`, `engine`, `eval-bridge`, `index`,
`push`, `store`, `tree`, `view`). There is no `RyiukReceipt`, no hash chain, no
`parent_hash`, no provenance of any kind. `store.ts`'s `LogEntry` (store.ts:18-25)
carries `{i, kind, text, size, date}` - a position, a kind, a string, a byte
count and a timestamp. That is not a receipt; it is a diary line with a line
number. The "editing appends a leaf (with a receipt)" sentence in
PROPOSAL.md:19-23 is therefore asserting a primitive that does not exist, and
`AUDIT.md` did not tag it `[PRIOR - suspect]`. This is the load-bearing claim of
K1 - "the log is the truth, the tree rebuilds" (PROPOSAL.md:39) depends on the
log being tamper-evident, and a log anyone can rewrite with `notepad` and a
byte-count field is not.

**What survives.** The append-only *layout* is real and worth keeping
(`main.jsonl`, `tree.jsonl`, `view.json`, `covered.txt` are all genuinely on
disk at `~/.dsh/memory/memory/<world>/`). The concept "store carries only
derived state, rebuildable from the log" is true **of the tree and view only** -
`raw.jsonl` and `covered.txt` are also derived, but `view.json` is written with
`writeFileSync` (store.ts:99) so it is a *snapshot*, not a log; if you edit
`main.jsonl` by hand the view goes stale until the next compaction call. Nothing
in the design detects that. Receipts are a thing to BUILD, not a thing to rebuild
from.

### 2. The wire cannot read the worlds that exist. This kills the "reuse the
live surface" path.

**Claim attacked** (AUDIT.md:67): "The native wire (ws-jsonrpc) |
`src-tauri/src/bin/daavile-wire.rs` (app) | built, 9/9 tests, live" - and
PROPOSAL.md:28-29 leaning on `app-wire memory.worlds/memory.read`.

**Why it fails.** Verified on disk:

- `daavile-wire.rs:230-235` - `optchat_root()` is `$USERPROFILE/.dsh/memory`.
- `store.ts:40` - `OptChatStore` constructs `join(root, 'memory', worldId)`, and
  `engine.ts:211` passes `memoryRoot` = `dshHomePath('memory')`, so the real
  world dir is `~/.dsh/memory/memory/<world>` - **one level deeper** than the
  reader looks.
- I enumerated `~/.dsh/memory` (verified this session): the actual worlds are
  `memory/memory/session-76991a46-...`, `memory/memory/session-e9c929bb-...`
  and `memory/memory/universe`. There is no `~/.dsh/memory/universe`.
- Worse, the package is not even self-consistent about that prefix:
  `eval-bridge.ts:102` builds the universe store from `dshHomePath()` with **no
  `'memory'` segment**, so its `universeStore()` targets
  `~/.dsh/memory/universe` while the engine targets
  `~/.dsh/memory/memory/universe`. Two code paths in one package write the same
  logical world to two different directories.

Consequence, computed by hand through `handle_request`
(`daavile-wire.rs:415-451`):

| call | result |
|---|---|
| `memory.read {world:"universe"}` | `{world:"universe", tree_lines:0, view:null, main:null}` - the dir does not exist |
| `memory.read {world:"memory/universe"}` | works - `tree_lines>0`, `main` present |
| `memory.worlds` | returns `["memory/..."]`-style paths (`memory_worlds()` scans at depth 1-2, daavile-wire.rs:334-361) |

So the **method the proposal presents as the agent's read path is off by one
directory segment for every single world on this machine**, and
`services.json` compounds it: the `optchat-memory` row (written by
`daavfx-services.mjs:186-197`) publishes `"worlds":["memory"]` - which is the
*parent directory*, not a world. It also publishes `"alive":true` derived from
`existsSync(memoryRoot)` (mjs:193), so a client sees a live memory service whose
world list is a lie. The tests in the bin (`daavile-wire.rs:645`:
`memory.read {world:"../../etc"}` must err) assert the traversal guard, and they
pass - and none of them assert that a real world reads back, because it doesn't.

**What survives.** The traversal guard is genuinely good work (relative, no
backslash, no `..`, max 2 segments, daavile-wire.rs:421-434) and it is the exact
pattern the human-section ban should copy. The WS frame stack and the discovery
merge are fine. But any design that says "the wire already serves the memory"
is describing a server whose read path is broken today.

### 3. `services.json` is written by two writers, one of which does not know
about the other's rows, and the audit's "merges non-destructively - verified"
hides that.

**Claim attacked** (AUDIT.md:68, PROPOSAL.md:85): "Discovery table |
`~/.daavfx/services.json` | publishing" and "the publisher
(`daavfx-services.mjs`) merges rows non-destructively - verified".

**Why it fails.** There are two writers to one file and neither coordinates:

- `daavfx-services.mjs:233-237` writes the **whole table** (`version`, `updated`,
  `services`, `notes`) via `writeFileSync(tmpdir) + renameSync` - a full
  replacement, atomic per-write, not a merge. It is also the **only** thing that
  produces the `notes` array.
- `daavile-wire.rs:252-278` `publish_self()` does a `read_to_string` ->
  parse -> insert the `app-wire` row -> `write(tmp) + rename`. That one *is*
  additive to whatever it read - but it cannot see rows it has not read, and it
  **drops nothing and adds nothing except its own row**.

Verified consequence on the live file (`~/.daavfx/services.json`, read this
session): it carries `optchat-memory` with `alive:true, worlds:["memory"]` and
an `orcad-engine` row with `alive:false`. If the Rust bin last wrote it, the
`notes` key the Node publisher always emits is absent - the file I read has
`"notes":[]`, i.e. the Node writer ran last and the Rust bin's row survived the
merge. Whichever ran first, the two writers disagree about what the schema is
(Node emits 4 keys including `notes`; the Rust bin's default template at
daavile-wire.rs:260 emits a different shape). There is no lock file anywhere.
K3 proposes adding per-surface `vault` rows into this file (`~/.dsh/vaults/
<surface>/...`) - into a table two processes already race on with no locking,
where one of the two writers does not know the "row" concept exists and would
happily rewrite the file without them.

**What survives.** The idea of one discovery table is right; the file is the
wrong vehicle for *mutable* per-surface config until it has one owner and a
lock. `daavile-wire.rs:274-277` already proves the atomic-write pattern works
(tmp + rename).

### 4. K1's compaction-as-memory design destroys the two properties it claims to
provide: cache stability and rollback.

**Claim attacked** (PROPOSAL.md:19-23): "If a skill is a WORLD instead, editing
it appends a leaf (with a receipt) instead of overwriting prose, the view is
always the current whole skill, and the store carries only derived state -
rebuildable from the log alone." And :35 "the chunks become LEAF CARGO, so
'this approach was tried and failed' is a first-class, citable, compacting
artifact instead of a stale paragraph."

**Why it fails - three separate reasons, all grounded:**

**(a) Skill edits do not have the shape of chat turns.** The engine's leaf
prompt (`engine.ts:25-42`, `LEAF_PROMPT`) is built for *messages*: it takes
`(kind, view, input)` where `kind` is `message.role` and prompts the model with
"the user words matter most (keep them close to verbatim)... least of all tool
steps" (engine.ts:40). A skill edit is not a `user`/`agent`/`tool` utterance.
The log's `kind` union is literally `'user' | 'agent' | 'tool' | 'echo' | 'work'
| 'note'` (store.ts:16) - there is no `skill-edit` kind, no structured field
carrying "which section changed" or "which chunk file". You would be appending
a note-kind leaf containing prose the model is instructed to *lossily
summarize*. The audit's own framing (AUDIT.md:78-81) hand-waves this as
"nothing connects it to the agent surface" - true, and the reason is that the
input shape differs. This is the question the refuter brief asked and the
proposal never answered: **no, they don't have the same shape.**

**(b) Every compaction call is priced and nondeterministic, which is precisely
what you do not want in a skill store.** `engine.ts:224-228` fires **one model
call per region message** (concurrency 8 by default, engine.ts:155), then one
more per merge (engine.ts:255-259), and the text is *clamped* to a byte budget
with an ellipsis (`clampLine`, engine.ts:77-86; default `nodeBytes: 512`).
A 512-byte clamp on a skill body is not "a first-class citable artifact" - it
is a truncated skill. Worse, two identical leaves compacted at different times
produce different trees, so the "view always equals the whole skill" claim is
true only of a *lossy summary of* the skill. Rollback then means "re-read the
log and rebuild" - but the log is the lossy part. **You cannot roll a skill back
to a state the store never recorded.**

**(c) It breaks prompt-cache stability, which is the feature the whole package
is built around and the proposal never once mentions.** `README.md:7` (optchat)
claims "the view is prompt-cache-stable by construction" - that property holds
because *between batches* the view only grows at its tail (view.ts:1-6: "the
previous view is a prefix of the next"). A skill-as-world has the opposite
access pattern: an edit lands in the **middle** of the body. The merge machinery
in `view.ts:24-63` is explicitly a *batch* rewrite once past
`VIEW_HARD_BYTES = 128_000` (view.ts:13) back down to `VIEW_SOFT_BYTES = 64_000`
(view.ts:11) - a mid-sequence edit that triggers compaction rewrites the prefix
and invalidates the cache. The harness's own docs state the invariant twice and
carefully, e.g. `tool-skill/README.md:137` ("The initial durable catalog is
appended after the existing reusable prefix. Dynamic changes are append-only
history after that catalog, so earlier reusable tokens stay intact") and
`skill-filesystem/README.md:138` ("Body-only edits leave the catalog digest
unchanged"). The shipped skill system is *designed around* append-only
body edits; the proposal would move skills onto a store whose guarantee runs the
other direction.

**What survives.** The chunk taxonomy (`primitives / failed_approaches /
abandoned_artifacts`) is genuinely useful as a *file convention* - it already
is one; the chunks live in plain markdown under `skills/novel/chunks/` and the
citation format `[chunk:chunks/<category>/<file>#<section>]` works today with
zero new code. Making "failed approach" a first-class concept is free and
should ship immediately. Making it a *compacting artifact* costs a model call
per edit and destroys the rollback you wanted.

### 5. The human section's write path does not exist, and "agents can never write
the human side" breaks flows the operator actually has.

**Claim attacked** (PROPOSAL.md:56-61): "isolation is not a policy, it is a
missing code path. If the vault's human section is not exposed through the wire's
method surface at all (no `memory.write` method exists ... then 'agents can't
write the human section' is enforced by the API shape, and the test is 'the tool
list contains no writer for `human/`'." Also README.md ground rule 3: "a HUMAN
section that agents may read but never write - enforced by structure, not by
prose."

**Why it fails - four ways:**

**(a) The operator needs a write path and the design has none.** The operator
writes constantly: REFUTATION.md (this file), NOVEL-ANGLE.md (named in
README.md:23 and *missing from disk* - I checked, it does not exist), the
INFLIGHT ledgers (AUDIT.md:72 lists them as a consumer asset), and notes to
self. In the proposal the human section is a read-only for-agents corner of a
store whose only writer is the wire, which has no write method. So the human
section cannot be written by *anyone* through the designed path. Human notes
would go in by hand-editing `main.jsonl`/`tree.jsonl`, which is exactly the
"not a receipt" problem from attack 1.

**(b) "Agents can never write the human side" forbids a legitimate flow the
app already implements.** `AgentSessionContext.tsx:580-609`
(`writeAgentFolder`) writes an agent's on-disk record via the app - `soul.md`,
`agent.json`, `skills/README.md`, `memory/README.md` under
`appDataDir()/agents/<slug>/`. Look at the default soul text at :565-573: it is
*doctrine* - "Verify before claiming. Cite files, runs, and receipts. Prefer
reversible actions; every write must be undoable." By the proposal's taxonomy
that is human-section content, and the app's Studio UI is already a write path
to it. Meanwhile the whole point of the coder/auditor lane split is the auditor
producing a verdict the operator *and later agents* must read - a quarantine
entry, a "the lie stays on record forever" note (see
`agents/daavile-auditor.md:38-41`, which mandates append-only quarantine
records). A rule that lets an agent append a quarantine record to the durable
ledger but not a one-line human-readable note is a rule that will be worked
around within a week.

**(c) The API-shape enforcement argument is wrong as stated.** "No
`memory.write` method exists, therefore the human section is safe" - the bin
has no write method **for worlds at all** (verified: methods are exactly
`runtime.describe / services.list / health / memory.worlds / memory.read /
ping`, daavile-wire.rs:365-453). The method surface is read-only against
`~/.dsh/memory`, not against a `human/` subtree. K2's enforcement therefore
requires *adding* a writer (PROPOSAL.md:63-64: "adding a writer for worlds
keeps `human/` outside the writable set") and the safety claim is about a
method that has to be invented first. That is a fine design; it is not
"enforced by the API shape" as a present fact.

**(d) Real enforcement exists on this machine and the proposal ignores it.**
`packages/sandbox/sandbox-windows-acl/` is a shipped, tested Windows
write-confinement backend: `workspace-write` / `read-only` restricted-token
modes, per-workspace capability SIDs, fail-closed `init()` that "throws on ANY
Win32 failure - never spawns unrestricted" (README.md:57), 16 spec files
including `path-boundary.spec.ts` and `control.spec.ts`. The harness convention
doc in that same repo states the governing rule explicitly
(`packages/AGENTS.md`): "Enforce a decision in the operation that makes it.
Schema omission, prompt filtering, facades, wrappers, and listener order are
not enforcement when direct or alternate callers can bypass them; **test denial
through the executor**." A "no writer method" gate is exactly the schema-omission
pattern that repo bans. K2's own framing (AUDIT.md:82-84: "executable gates: a
test that fails when an agent writes the human section") is reachable *today* by
running the agent shell under `mode: read-only` with the vault root outside the
grant - a real, tested denial at the executor.

**What survives.** A read-only-by-default human section, with a narrow,
logged, machine-attributable append channel (the audit lane's
quarantine pattern) is the right shape. And K2 is the *only* candidate in the
proposal whose top-line claim ("isolation is a missing code path, and here is a
denial test") is both correct and cheap.

### 6. K3 ships drift with no reconciliation, on a namespace surface that already
exists twice.

**Claim attacked** (PROPOSAL.md:79-83): "Assumption inverted: the drift is the
point. `services.json` already describes every live surface in one table; adding
a `vault` row per surface (`~/.dsh/vaults/<surface>/...`) makes isolation the
default while discovery stays unified. The wire client that already reads one
table now reads 'which vault is this session bound to' from the same file."

**Why it fails.**

**(a) Two surfaces, two already-working skill sources, and the proposal invents a
third.** The harness's `skill-filesystem` already implements per-surface skill
isolation with a documented rank order (`skill-filesystem/README.md:50-56`):
`<projectRoot>/.dsh/skills` (rank 100), `<projectRoot>/.agents/skills` (200),
`Config.customSkillDirs` (300), `<dshHome>/skills` (400), `<agentsHome>/skills`
(500), `bundledSkillDir` (600). That *is* K3 - project-scoped vs user-scoped vs
custom, with user-level `~/.agents/skills` already holding 17 live skills on
this machine (verified: computer-use, herdr, hyperframes and its 7 siblings,
media-use, mt5-setfile-test, orchestration, find-skills). And the *app* already
has its own surface binding in `AgentSessionContext.tsx` (per-persona `model` /
`skills` / `mcps` / `soul`, :42-53, with `localStorage` overlays at :616-645).
So the proposal's K3 = "a `vault` row in services.json" adds a **fourth** binding
mechanism next to three.

**(b) The drift is not "the point", it is unmanaged.** Nothing in K3 says what
happens when the app's Studio persona has `skills: ["novel"]` bound while the
harness's preset for the same session has `customSkillDirs: []`. In the current
tree the answer is visible: the same operator doctrine exists as
`~/.config/opencode/agents/daavile-operator.md` (5,085 bytes) *and* as the
app's `soul.md` default text (`AgentSessionContext.tsx:559-573`) *and* as
`AGENTS.md` at the repo root - three copies of one doctrine, none marked as the
source of truth, and the audit's own receipt table (AUDIT.md:58-59) celebrates
"the doctrine exists and works; it is just homeless" without noticing it is
homeless **twice**. Adding a per-surface vault row without a declared precedence
and a sync test multiplies that.

**(c) It also cannot answer "which vault" for a cloud lane.** The operator's
Orca ADE surfaces run against cloud providers (see the config's
`nvidia-kimi`/`nvidia-step5`/`tokenrouter` rows). Nothing in the design states
whether a cloud-driven session is bound to the local per-surface vault, and the
wire bin binds nothing - it has no concept of a session bound to a vault at all
(`~/.dsh/gateway-url` is the only per-session pointer, daavile-wire.rs:323-330).

**What survives.** Per-surface isolation is a real goal and the rank table is
the mechanism to express it. Wire `vault` rows into the *existing* rank system
rather than into `services.json`.

### 7. AUDIT.md's "verified" facts contain errors that matter, and its
[PRIOR - suspect] tags are on the wrong items.

**Claim attacked** (AUDIT.md:10-22): the structure block, "agents/*.md 9 files
6 built-in (09-18) + 3 daavile (10-26) ... Skills are per-folder with
`core/{RAG_PROMPT,SKILLS}.md`, `chunks/<category>/<file>.md`,
`index/{manifest.json,retrieval_rules.md}`, plus `agents/*.json` descriptors"
and "The agent contract is one `.md` per agent with **three frontmatter fields**
(`agents/daavile-operator.md:1-4`)".

**Why it fails - verified against the files:**

- **"three frontmatter fields" is wrong.** `daavile-operator.md:1-4` has exactly
  two: `description`, `mode: all`. So do `daavile-auditor.md` and
  `TRADING_DAAVILE.md`. The **built-ins have more than three**:
  `debugger.md:1-12` carries `description, mode, tools (write/edit/bash booleans),
  temperature, steps` - six fields including a per-agent tool grant. So the audit
  both undercounts the contract *and* misses that per-agent tool declaration
  already exists - the very mechanism K2 claims is absent.
- **"Skills are per-folder with core/chunks/index" is true of exactly one
  skill.** `~/.config/opencode/skills/` has 7 dirs; only `novel` has
  `core/`, `chunks/`, `index/`, `agents/`. The other six are a single flat
  `SKILL.md` (`deck-reporting-law` 3,828 B; `herdr` 13,867 B; `investing-daavile`
  4,404 B; `mt5-fleet-sweep` 5,901 B; `trading-daavile` 6,982 B; `media-use`
  7,982 B + 158 support files). So the "chunk taxonomy" the vault is supposed to
  host describes 1 of 7 skills, and the RAG-shaped one is also the one with the
  smallest body.
- **"11 skills" (AUDIT.md:70) - the novel layer holds 13 sub-skills.** Counted
  from `core/SKILLS.md`: weight-inversion, assumption-archaeology,
  consensus-as-target, rag-override, cross-domain-recombination,
  abandoned-artifact-repurposing, method-not-verdict, safety-containment,
  dual-axis-scoring, assumption-inversion, novel-angle-search, grounded-citation,
  purpose-agnostic-shipping, prior-quarantine = 14 (I count 14; the audit says
  11; either way it is not 11).
- **"The 15 KB config holds 20+ providers/models" - it is 16 providers, 34
  models** (verified by key scan of `opencode.jsonc`: local-lfm, local-qwen2b,
  local-qwen4b, local-k2, local-gemma26, local-laguna, local-granite8b,
  local-granitetiny, local-bonsai, tokenrouter, nvidia-kimi, nvidia-deepseek,
  nvidia-deepseek-v41, nvidia-glm, nvidia-step5, kaggle-glm). "20+ providers" is
  not true; "50 provider/model entries" is.
- **"the only structural keys are provider/model/mcp" (AUDIT.md:29) is false.**
  Top-level keys are `autoupdate`, `provider`, `mcp`, `tokenrouter`
  (`opencode.jsonc:2,4,419,174`). The audit scanned with a pattern that missed
  `tokenrouter` and therefore **missed that the config carries plaintext
  provider API keys** (`opencode.jsonc:179` and `:192`). Not scoring this, but a
  "no isolation, everything is world-readable" audit that fails to notice the
  world can read a live API key has an isolation claim that is too weak by its
  own standard.
- **"There is NO permission block and NO agent-scoped MCP or tool declarations
  anywhere in the config" (AUDIT.md:28-29)** - the `tools:` frontmatter in six of
  nine agent files contradicts the second half of that sentence about the
  *agents*, though not about the config. The audit then compounds it at
  AUDIT.md:42-47: "`[PRIOR - suspect]` on intent; verified on structure: nothing
  prevents it" for the daavile-operator soul being readable by `debugger` - while
  `debugger.md:6-9` grants `write: true, edit: true, bash: true` to that same
  agent. The structure does not merely permit reading; it grants the debugger
  write access to wherever `debugger` runs, which makes the isolation problem
  *worse* than stated, and the audit used its suspect tag on the wrong axis.

Meanwhile the audit's `[PRIOR - suspect]` tags sit on the two *softest* claims
(consensus strength at PROPOSAL.md:16, intent at AUDIT.md:47) and are **absent**
from the three hardest, most load-bearing claims: the receipt chain, the wire's
read path, and the "publisher merges non-destructively" line. That is backwards.

**What survives.** The core complaint is real and well-founded: one flat
namespace, agent `.md` files and skill bodies all world-readable, doctrine
sitting next to generic personas, the only durable isolation being a SQLite DB
agents cannot query (AUDIT.md:40-43). The structure enumeration is off in detail
but right in shape.

### 8. Scoring: 620 is invented arithmetic, and the axes it self-awards are the
axes the evidence contradicts.

**Claim attacked** (PROPOSAL.md:45): "Score = 2*74 + 92 + 3*88 + 2*95 + 2*80 - 0
= **620**".

**Why it fails.** There is no rubric, no rubric definition, no second rater, and
no citation for any of the six numbers. Worse, each is contradicted by what I
verified:

- **Grounding 95** is incompatible with attack 1: one of the four named
  primitives does not exist.
- **Safety 92** ("every write atomic with a receipt", PROPOSAL.md:39) is
  incompatible with `store.ts:66` (`appendFileSync`), `:82` (`appendFileSync`),
  `:99` (`writeFileSync`), `:124`, `:157` - **five unsynchronized writes with no
  lock, no tmp+rename, and no fsync**. Two `OptChatStore` instances over the same
  world (the app's UI and a wire client) can interleave `appendFileSync` calls
  and produce interleaved JSONL lines; `readLog()` (store.ts:70-78) will then
  throw `JSON.parse` on a torn line and take the whole world down. The bin the
  audit calls "built, 9/9 tests" had to hand-roll `tmp + rename` at
  `daavile-wire.rs:274-277` precisely because this was a known problem - and the
  store, which is the thing K1 would build governance on top of, still has it.
- **Novelty 88** is not novel: per-surface skill roots, frontmatter-gated
  visibility (`disable-model-invocation`, `user-invocable` -
  skill-filesystem/README.md:38), and a per-agent skills/soul binding all
  already ship. The genuinely novel bit is "compaction mechanics over skills",
  and attack 4 shows that is the harmful bit.
- **Penalty 0** with no listed penalties, while the proposal itself concedes
  "(1) nothing connects it to the agent surface" (AUDIT.md:81) - a penalty the
  audit assigns to nobody.

By the same invented rubric my alternative scores **604** against their 620
(2*78 + 91 + 3*70 + 2*90 + 2*85 - 3 = 604) and the -3 is the honest cost that
it does not deliver the operator's preferred topology. But scoring is theater;
the point is that **K1's 620 rests on four premises that are each false**.

**What survives.** The scoring discipline itself (safety-gated, must-cite) is
good practice and should be kept - with a rule: **any candidate naming a
primitive must cite `file:line` for it, and an unverifiable primitive caps the
candidate at its actual verifiable subset.** K1 under that rule is a 3-line
change to the store, not a vault.

---

## WHAT THE PROPOSAL MISSED ENTIRELY

1. **Prompt-cache stability of a skill load.** Never mentioned, and the two
   shipped packages that own this problem both document the invariant in a
   "KV Cache effect" section (`tool-skill/README.md:137`, :151, :207;
   `skill-filesystem/README.md:138`). The proposal's design direction is
   cache-hostile for skills (attack 4c).
2. **Concurrent read/write across surfaces.** Two surfaces over one world store:
   the app writes via `writeAgentFolder` to `appDataDir()/agents/<slug>/`
   (AgentSessionContext.tsx:589-604), the harness writes to
   `~/.dsh/skills` / `<project>/.agents/skills` / `~/.agents/skills`
   (skill-filesystem/README.md:50-56), and the proposal would add
   `~/.dsh/vaults/<surface>/`. Nothing arbitrates. The store has no locking
   (attack 8).
3. **Migration cost from the existing skills tree.** The prose in PROPOSAL.md
   treats "replace the shared flat-file opencode model" as free. On disk the
   estate is: 7 opencode skills (1 RAG-shaped, 6 flat), 17 `~/.agents/skills`
   skills (all `<name>/SKILL.md` bundles), the app's per-persona soul/skills
   bindings, and `AGENTS.md` doctrine duplicated in three places. Any vault must
   either import all three layouts or coexist with them. The design says
   "per-surface vaults ... never a shared brain" and then is silent on which of
   these become *which* vault's content, and who runs the import.
4. **The relationship between INFLIGHT.md and the vault.** AUDIT.md:72 lists the
   INFLIGHT ledgers as a consumed asset; the design has no answer. That ledger
   is **400,629 bytes** on disk in `APPS/quantum_dashboard-fx/INFLIGHT.md`, is
   append-only by mandate, is keyed by Work-Note IDs, and is the *actual*
   durable research record the vault claims to be. Either the vault subsumes it
   (and the migration is the whole cost) or it does not (and the vault is a
   second, competing ledger - the exact duplication the AGENTS.md in this repo
   warns about). Silent.
5. **Orca ADE reachability of `~/.dsh`.** Never addressed. `services.json`'s
   `orcad-engine` row is `alive:false` right now (verified this session), the
   runtime file lives at `%APPDATA%\com.daavfx.quantum-dashboard\daavilefx-engine\
   orca-runtime.json`, and `daavfx-services.mjs:32` hardcodes a Windows
   `AppData` path and `:33-34` hardcode F:\ drive paths. The wire bin resolves
   home via `USERPROFILE` (daavile-wire.rs:223-227, :324-328). For a cloud-
   provider Orca ADE session there is **no statement anywhere about whether it
   can reach `~/.dsh/memory` or `~/.dsh/vaults`, and no auth on the wire either**
   - the discovery row itself says `auth: token-in-runtime-file` only for the
   engine, and `app-wire` has no auth field at all (services.json). A vault that
   holds human-section notes served over unauthenticated loopback WS is a
   safety claim that has not been examined.
6. **Cost.** Every world compaction call is a live model call (engine.ts:224,
   255, 358) with concurrency 8 and a byte-clamped result. For `media-use` - one
   skill, 158 files, 2.1 MB of support material - a skill-as-world design would
   either compact nothing useful or burn a lot of tokens. There is no cost line
   in the proposal at all.
7. **The operator's actual daily driver.** K4 is rejected with "the operator
   already ruled: keep their base, level OUR surfaces" (PROPOSAL.md:101-102) -
   a ruling I accept - but then every remaining candidate assumes the vault is
   reached *through our surfaces* while the coder/auditor lanes in question run
   in opencode TUI against `~/.config/opencode`. Nothing in K1/K3 changes what
  the coder lane reads this afternoon.

---

## WHAT I WOULD BUILD FIRST INSTEAD

Concrete, five steps, all verified-file-based, all deliverable in one sitting.
No new substrate. No new writer. Nothing that touches `premium_backend/` or
`main.rs` (rule 1 of the app's AGENTS.md).

**Step 1 - Fix the wire's memory read path and make the discovery table stop
lying.** (2 files, ~30 lines.)
- `APPS/quantum_dashboard-fx/src-tauri/src/bin/daavile-wire.rs:230-235`:
  `optchat_root()` must return `~/.dsh/memory` **and** every caller must
  additionally join `"memory"`, or (cleaner) make the reader's world name the
  *logical* name and resolve `root.join(world)` where root is
  `~/.dsh/memory/memory`. Then `memory.read({world:"universe"})` returns the
  view it currently returns nulls for.
- Same file, `memory_worlds()` (daavile-wire.rs:334-361): emit **logical**
  names (`universe`, `session-76991a46...`) not filesystem-relative paths.
- `scripts/daavfx/daavfx-services.mjs:186-197`: `worlds` must be the same
  logical list (read `memory/memory/*`), and `alive` must be "at least one
  world dir exists" not "the parent exists".
- Add the two tests that were missing: one asserting
  `memory.read({world:"universe"})` returns `view != null` against a fixture
  world laid out exactly as `store.ts:40` lays it out; one asserting
  `memory.worlds` never returns a bare `"memory"`. These are the tests the
  failure hides behind - the existing suite only proves the traversal guard
  (`daavile-wire.rs:645`).
Why first: every later step depends on being able to *read* what is already on
disk, and today nothing can.

**Step 2 - Give the human section the write path it needs, and make it the
app's existing agent folder.** (1 file, no new primitive.)
- Adopt `appDataDir()/agents/<slug>/` from
  `AgentSessionContext.tsx:589-604` as the human section's home - it already
  writes `soul.md` + `skills/README.md` + `memory/README.md`, and the doctrine
  text at :565-573 is exactly what the proposal wants quarantined.
- Add the operator's write channel the proposal has no path for: a single
  `human-notes.md` appended by the operator (or by the auditor lane on the
  operator's behalf, with an attribution line) via the same
  `writeAgentFolder`-style helper, so `human/` has an *authorized writer* that
  is not an agent's free-form `edit`.
- State the one rule that survives attack 5: **a human-section write carries an
  `author:` line and the app's own code is the only writer that omits it.**
  The audit lane's quarantine flow (`agents/daavile-auditor.md:33-41`) then has
  a legitimate home rather than being forbidden.
Why second: it is the operator's actual complaint (nowhere to put a note), it
needs no vault, and it converts the "never writable" rule into something
enforceable and useful.

**Step 3 - Wire the real enforcement, using the mechanism that exists.**
(config, no new code.)
- The harness's Windows ACL backend
  (`packages/sandbox/sandbox-windows-acl/`) already gives `mode: read-only` and
  `workspace-write` with fail-closed `init()` and 16 passing spec files,
  including `path-boundary.spec.ts` and `control.spec.ts`.
- Configure the coder/auditor lane shell under `read-only` with the grant root
  = the workspace only, and assert a denial test the way that repo demands
  (`packages/AGENTS.md`: "Enforce a decision in the operation that makes it...
  test denial through the executor") - i.e. a test that spawns a confined shell
  and proves `New-Item` under the human section fails, not a test that greps a
  tool list.
- Model Experience note: this costs one extra catalog entry at most (the
  bundled `diagnose-windows-sandbox-acl` skill, README.md:167-171) and
  *zero* on non-Windows.
Why third: it is the only candidate (K2) whose claim survives contact, and it
is a config file plus one test rather than a subsystem.

**Step 4 - Merge the four skill sources into the existing rank table and stop
inventing a fifth.** (config + a 10-line import.)
- Add one `customSkillDirs` entry pointing at the existing trees so the
  harness reads them with no copy: `~/.agents/skills` is already rank 500 by
  default; add `~/.config/opencode/skills` as a `customSkillDirs` row (rank 300)
  and `<projectRoot>/.agents/skills` is already rank 200.
- Write the one missing file the import needs: `skills/novel/SKILL.md`
  (frontmatter `name` + `description` + `whenToUse`, per
  `skill-filesystem/README.md:36`). The `novel` layer currently has **no
  `SKILL.md`** - it has `README.md`, `core/`, `chunks/`, `index/`, `agents/` -
  so `dsh-skill-filesystem` cannot discover it at all ("Discovery is one level
  deep", same README:147). Until that file exists, the RAG layer the whole
  design leans on is invisible to the harness.
- Once, in that same file, declare the precedence rule K3 never wrote:
  project beats custom beats user-agents beats user-dsh beats opencode-config,
  and the harness's own rank order becomes the single source of truth.
Why fourth: it makes the RAG layer reachable for the first time and kills the
duplicate-third-source problem for the cost of one file and one config row.

**Step 5 - Put the receipts where the design wants them, cheaply, and only
after 1-4 are green.** (1 new file, deferred.)
- When (and only when) there is a writer to protect: add a hash-chained sidecar
  beside the world - `receipts.jsonl` - written by the *same* code path that
  appends, with `tmp + rename` in the daavile-wire.rs:274-277 pattern (NOT
  `appendFileSync`), so a torn write is detectable and a rewrite is visible.
  That is the `RyiukReceipt` K1 claimed already existed.
- Do **not** re-plumb skills onto the OptChat world store. Skills stay
  `<name>/SKILL.md` bundles, edited in place, cache-stable by construction
  (attack 4c). The chunk taxonomy
  (`primitives/failed_approaches/abandoned_artifacts`) stays a *file
  convention* under the RAG layer and is adopted immediately under Step 4 -
  it is the one genuinely good idea in the proposal and it costs nothing.
- Cross-check the ledger question before building: decide, in writing, whether
  `INFLIGHT.md` (400,629 bytes) is the record or the vault is. If the vault,
  the migration is a task, not a footnote.

**Ordering rationale:** steps 1-2 are the operator's complaint and cost under a
day. Step 3 is the only candidate that survives refutation. Step 4 makes the
existing RAG layer usable. Step 5 is the part worth building *last*, because
everything the proposal claims it already has it does not.
