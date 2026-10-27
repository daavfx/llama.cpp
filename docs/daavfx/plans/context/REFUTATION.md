# REFUTATION.md - the context-pipeline proposal, roasted

Verdict: the research framing is honest and the diagnosis (contradiction
accumulation beats length) is probably right, but PROPOSAL.md's grounding
table is the weakest part of the document - of nine "assets this plan
consumes", five are misdescribed on disk, one is arithmetic fiction, one is
a real number (26.83 GB, not 28), and the two central primitives of P1 do
not exist in the form claimed: the token meter is a dependency string that
the engine never reads, and `covered.txt` is a four-byte integer watermark
that carries no sizes, no costs, and no per-item rows. P1 is largely a
description of what already ships, P2 leans on numbers no file in this tree
can reproduce, and both P1 and P2 were scored an hour after a sibling lane
scored the same thesis 620 to 617 without either document mentioning the
other. What survives is small, cheap, and real: an atomic-write fix in the
store, a comment that is off by 10x, a dormant taxonomy waiting to be fed
into the merge order, and one honest primitive table so the next plan
diffs instead of re-deriving.

Verification date: 2026-10-27. Every file:line below was read on disk this
session. Numbers I could not reproduce from a file or from the transcript's
own measurement are tagged `[PRIOR - suspect]`.

---

## 1. Primitives that do not exist, or behave differently than claimed

### 1a. "the token meter already injected into the engine"

> PROPOSAL.md:46 - "the token meter already injected into the engine. The
> new work is the *accounting layer*: per-item sizes + costs attached to
> the log, and the budget decision made against them."

`tokenMeter` appears exactly once in the entire `dsh-compaction-optchat`
package, and it is a string in an array:

```
packages/compaction/optchat/src/engine.ts:173
  static override inject = ['llm', 'tokenMeter', 'sessions', 'tools']
```

There is no `this.ctx.tokenMeter` read anywhere in the package. The meter
is declared as a dependency and never used. "Injected" is true as wiring
and false as capability.

What it would provide, if used, is worse than nothing for P1's purposes.
`packages/llm/token-meter/src/estimate.ts:88-91` is:

```ts
export function estimateMessage(message: Message): number {
  if (message.role === 'system') return estimateSystemMessage(message)
  return estimateContent(message.content) + ROLE_OVERHEAD
}
```

with `CHARS_PER_TOKEN = 4` (estimate.ts:13), `BLOCK_OVERHEAD = 4`
(estimate.ts:16) and `ROLE_OVERHEAD = 4` (estimate.ts:19). That is the
`char/4` estimate. And `char/4` is the exact primitive BRAINSTORM.md:185
opens with as wrong:

> "| `char/4` token estimate | Miscalibrated per model/tokenizer |"

So the instrument P1 wants to hang its accounting on is, on this disk, the
thing the brainstorm says is miscalibrated. Worse, the two budgets in play
are in different currencies and nothing converts them: the engine optimizes
`VIEW_SOFT_BYTES = 64_000` and `VIEW_HARD_BYTES = 128_000` **bytes**
(view.ts:11-13), while the configured budget is `headroomTokens: 512`
**tokens** (cordis.patch.yml:46). `bytes.ts:1-3` states the position
outright:

```ts
// UTF-8 byte accounting. The recipe's sizes are bytes, never tokens, and
// models cannot count bytes - the caller measures here and shows the ruler.
```

"Given a token budget and a log with per-item sizes, choose which items
pay" is not a well-formed problem on this disk until one currency is
chosen.

**What survives:** the `inject` line is real, so wiring the meter costs one
call site. Use the meter; do not write a new one. But the first honest
deliverable is a per-item token estimate persisted next to the byte size -
not a policy.

### 1b. "the covered-count accounting (`covered.txt`)"

> PROPOSAL.md:45 - "the covered-count accounting (`covered.txt`)"

`packages/compaction/optchat/src/store.ts:147-158`:

```ts
  coveredCount(): number {
    const path = join(this.dir, 'covered.txt')
    if (!existsSync(path)) { return 0 }
    const value = Number(readFileSync(path, 'utf8').trim())
    return Number.isInteger(value) && value >= 0 ? value : 0
  }

  markCovered(count: number): void {
    writeFileSync(join(this.dir, 'covered.txt'), String(count), 'utf8')
  }
```

It is a plaintext integer. No sizes, no costs, no ids, no rows, no
timestamps. It is a watermark. It cannot "carry budget decisions" because
it cannot carry anything but one number.

The only per-item size in the package is `LogEntry.size` (store.ts:23, set
at store.ts:63 as `utf8Length(text)`) and `StoredNode.size` (store.ts:31,
store.ts:81). Both are bytes, and neither is ever read by any code in the
package - a scan for `.size` across `optchat/src/*.ts` returns only the
`readNodes().size` Map method at engine.ts:60 and the declarations in
store.ts. They are write-only metadata.

**What survives:** nothing in `covered.txt`. The `size` field is a free
slot to write the token estimate into (1a), which is the useful move.

### 1c. "the append-only world log (`main.jsonl`)" as the transcript

> PROPOSAL.md:44 - "Rebuild from primitives (all on disk): the append-only
> world log (`main.jsonl`), the due-order merge tree (push.ts)..."

`main.jsonl` is not the conversation log. The store's own header says so
(store.ts:114-118):

```
  // ---- v2 integration surface ---
  // The conversation log itself lives in the session (durable, append-only);
  // the store carries only derived state: the built tree, the saved view, the
  // raw-leaf sidecar (zoom to the message whole), and the covered count (how
  // many conversation messages the tree already covers).
```

`appendLog` has exactly two callers in the package: `eval-bridge.ts:65`
(kind `'note'`, from Lane-A eval records) and `engine.ts:343` (the universe
distiller, kind `'note'`). The conversation's messages reach the store as
tree leaves and the raw sidecar - `engine.ts:212` reads them from
`input.messages` (the compaction engine's region input) and
`store.recordLeaf` writes them to `tree.jsonl` + `raw.jsonl`
(store.ts:121-126). `main.jsonl` is the **universe notes log**, and on
disk `~/.dsh/memory/memory/` holds `session-76991a46-...`,
`session-e9c929bb-...` and `universe` - the session worlds are the
transcript's home and main.jsonl is not in them.

P1's first listed primitive is the wrong file. "The ledger is the log" is
false for the log P1 named; the actual conversation ledger is the session
log, which this package cannot read.

**What survives:** the universe log is a genuinely append-only,
append-only-only artifact (no mutation path exists), so it is a fine
substrate for the *status/supersede* entries P2 wants. It is not the
transcript.

### 1d. "The native wire ... shipped, 10 tests; read path fixed this session"

Two halves, one true and one that fails in detail.

**Conceded:** 10 tests. I counted 10 `#[test]` in
`APPS/quantum_dashboard-fx/src-tauri/src/bin/daavile-wire.rs`: sha1 (605),
base64 (611), handshake RFC vector (622), handshake independent (628),
civil_from_days (636), port_parser (643), traversal rejection (650),
logical names (665), runtime.describe (706), live round-trip (720). And
"14 specs" for the due-order/view claim is also exact: 10 `it(` in
`tests/optchat.spec.ts` plus 4 in `tests/e2e-proof.spec.ts`.

**The read-path fix is real.** `optchat_root()` builds
`~/.dsh/memory/memory` (daavile-wire.rs:235-241) and `store.ts:40` builds
`join(root, 'memory', worldId)` from `dshHomePath('memory')` =
`~/.dsh/memory`, so the real worlds are `~/.dsh/memory/memory/<world>`. I
verified that layout on disk. The extra segment is real and the fix is
correct.

**But the guard test for it is vacuous.**
`memory_worlds_emits_logical_names_not_the_parent_dir`
(daavile-wire.rs:664-703) never calls the production `memory_worlds()` and
never calls the production `scan()`. It defines a *local* `fn scan` with
`if depth > 3 { return }`, no artifacts list, and no second `memory`
segment, then scans a temp root laid out as `memory/session-abc` - one
segment deep. The production root already carries the doubling, so the
test's layout does not model production. The assertion
`assert!(!found.iter().any(|w| w == "memory"))` passes trivially in the
local scan because the temp root has no bare `memory` directory holding
artifacts. And `let prev = std::env::var("USERPROFILE").ok()` at line 674
is captured and never used - dead. The test named "the refuter's guard"
cannot fail for the bug it is named for, so "read path fixed" is a fix
with no test that would catch a regression.

**Two things the wire cannot do, which P1 needs.**
`memory.read` returns `tree_lines`, `view` and `main`
(daavile-wire.rs:456-461). It does not return `covered.txt`, `raw.jsonl`,
or any byte/token total, and the method catalog is fixed at six read-only
entries (daavile-wire.rs:380-382). There is no surface by which any
"cost-accounted" number could be observed. Also, the file carries a stray
no-op at daavile-wire.rs:490-497:

```rust
        if std::env::var("DAWI_DEBUG").is_ok() {
        }    let key = match key {
```

It compiles (an empty block) but it is dead - a mark that the "recent fix"
was not cleaned up or re-read.

**What survives:** the wire is a real, read-only, correct-path surface over
the worlds. It is a valid observation point, not a valid accounting point.

### 1e. "Due-order merge + 128k->64k view policy | `optchat/src/push.ts`, `view.ts`"

The constants are real (VIEW_SOFT_BYTES 64_000 / VIEW_HARD_BYTES 128_000,
view.ts:11-13). The attribution is wrong. `engine.ts` imports `duePairs`
from `./tree.ts`; `view.ts:8` imports `duePairs` from `./tree.ts`. Nothing
in the package imports `push.ts` except `index.ts:2`. And `push.ts`'s own
header (push.ts:1-7) says:

```
// ... Under push alone `life` stays 0; it serves rollback only, kept for
// fidelity.
```

`pushListLines` (push.ts:44-57) has no caller in the package - a scan
finds it only at its own definition and the `index.ts` re-export. The due
formula PROPOSAL.md:42 quotes, `(T+1)/2^l - i`, is `tree.ts:22`
(`dueForPair`), and the merge order is `duePairs` (tree.ts:35-61, sorted
`b.due - a.due || a.index - b.index` at tree.ts:60).

**What survives:** the merge policy is real and pinned by 14 specs. It
lives in tree.ts, not push.ts, and anyone editing push.ts to change
compaction will change nothing.

### 1f. "The novel RAG layer (chunks + citations) | ... | in use by the audit lane"

`docs/daavfx/skills/novel/` exists with `README.md`, `core/RAG_PROMPT.md`,
`core/SKILLS.md`, `index/manifest.json`, `index/retrieval_rules.md`, two
agent JSONs and three chunks. It has **no SKILL.md**, so it is not
discoverable as a skill under any harness that loads `<name>/SKILL.md`
bundles - which is the same defect the sibling lane already recorded in
`docs/daavfx/plans/vault/NOVEL-ANGLE.md` build plan step 3:
"write the missing `skills/novel/SKILL.md` (the RAG layer is currently
undiscoverable)". PROPOSAL.md asserts "in use by the audit lane" with no
file for the "in use" half and no mention of the missing entry point. And
`docs/daavfx/README.md` (2026-10-22) does not list `skills/`, `plans/vault/`,
`plans/context/`, `experimental-dgpu/` or `auditor-*` at all - five
folders are already absent from the lane index (README.md:35-46).

**What survives:** the chunk library and its three-part taxonomy
(`primitives/`, `failed_approaches/`, `abandoned_artifacts/`) are real and
citable. The audit-lane usage is unverified; [PRIOR - suspect].

### 1g. "Session transcripts | `~/.local/share/opencode/opencode.db` | exists; 28 GB"

Conceded, with a correction: the file exists at
`C:\Users\neto_\.local\share\opencode\opencode.db`, measured
**26.83 GB** (28,810,694,656 bytes) plus a 13.5 MB `-wal` (so it is still
being written). "28 GB" is a rounding overstatement of the only real
number in the entire grounding table.

**What survives:** the substrate is real. But a 26.8 GB SQLite WAL-mode
database is not "three existing long session transcripts" (BRAINSTORM.md
section 8) - it is a live, locked, multi-client store, and extracting
transcripts from it is a task nobody has scoped, in either document.

### 1h. "shipped; compaction fired 10-25"

> PROPOSAL.md:15 - "OptChat engine + store | ... | shipped; compaction
> fired 10-25"

No range, no unit, no source, no counter in the code.
`packages/compaction/optchat/src/engine.ts` emits no instrumentation of
any kind - no firing count, no per-merge timing, no bytes-before/after.
This is `[PRIOR - suspect]` and cannot be otherwise: "10-25" of what, over
what period, measured how?

### 1i. "the receipt sidecar (the `daavile-wire.rs` tmp+rename pattern, since the optchat store's `appendFileSync` is torn-line unsafe)"

> PROPOSAL.md:108

Correct, and understated by exactly the part that loses more. PROPOSAL
names `appendFileSync` (store.ts:66, 82, 124) - line-append tearing. It
does not name the two **whole-file, non-atomic** writes:

- `saveView` does `writeFileSync(this.viewPath, JSON.stringify({ lines }))`
  (store.ts:99) and `loadView` catches any parse failure and returns
  `null` (store.ts:109-111). A torn `view.json` therefore silently erases
  the entire memory of the world with no error, no log line and no
  symptom. The engine then proceeds with `store.loadView() ?? []`
  (engine.ts:223, 240, 352) and rebuilds from nothing.
- `markCovered` does `writeFileSync(..., String(count))` (store.ts:157) and
  `coveredCount` turns a torn read into **0**: `Number("4\n7")` -> `NaN` ->
  `Number.isInteger(NaN)` false -> returns 0 (store.ts:152-154). Covered=0
  makes the next compaction re-leaf every message from index 0, appending
  duplicate `i` values into `raw.jsonl`, and `readLeafRaw` returns the
  **first** match (store.ts:137-142) - so `zoom` silently serves stale
  content.

Also `readLog` (store.ts:74-78) `JSON.parse`s every line with no filter;
one torn line throws and the whole log read fails - the same failure class
PROPOSAL attributes only to append.

**What survives:** the tmp+rename import is the right idea and the right
source file (daavile-wire.rs:279-282 already does it for
`services.json`). It has to cover `view.json` and `covered.txt`, not just
a new sidecar.

---

## 2. The transcription's numbers: which are priors, and who leans on them

BRAINSTORM.md:6 says "unverified numbers are tagged `[PRIOR - suspect]`".
The tags do not appear anywhere in the file. Every number below is a prior,
transcribed through the operator's coder from papers, and reproducible
from nothing in this tree:

**All of BRAINSTORM.md section 1 and section 3.** 18 frontier models; fact
recall 57% ordinary / 21% with contradictions; metabolism recovery 73%;
Google's 1M window at 47.8 points; 384 slots per layer; 120 MB; 1,365x
compression at 128K; 90.60 ESM gold / 64.80 recursive (-25.8) / 55.00 for
GLM-5; ~5,100 vs ~300 token footprints; MiniMax 30.40 vs 50.00; p < 0.001;
~2.5 layers; 5.6x LongCodeZip; 97% of teacher at >10x cost; "~53 merging a
little at a time"; PPL 5.75 -> 2,464; 128K for GLM-5.3; t = 0..20,000.

**All of the PR-map numbers in BRAINSTORM.md section 4** - which are
second-hand *twice*: they cite PR #22029, a number in opencode's own
upstream repo that nobody in this tree has fetched, so they are priors
about a third party's code. 0.7/0.3 EMA blend; 15% of context / min 20k /
vs flat 40k; proactive prune at 50%; 80-90% of limit; the last 15k. None
is verifiable here, and the PR number itself is `[PRIOR - suspect]`.

**The candidates that lean on them:**

- **P2 (575) leans twice on unverifiable numbers.** BRAINSTORM.md:157-162
  gives it 57/21/73/47.8, and PROPOSAL.md:86-87 concedes "none of them is
  verifiable here, so Grounding is capped at 88". A cap is not a tag: the
  citation chain is a transcription, of a paper, with no local
  reproduction, and the *safety* claim - "pure code + one model call per
  turn over a bounded delta" (PROPOSAL.md:85) - rests on the word
  "bounded", which is the one quantity nobody measured. In the shipped
  profile the tail retained is `retainRatio: 0.0002` (cordis.patch.yml:45),
  i.e. the "bounded delta" is a full-window call, not a delta call.
- **P1 (617) claims Grounding 94** - the second-highest of the three -
  while its own Rebuild list contains two primitives that do not exist as
  described (main.jsonl as the transcript, 1c; covered.txt as accounting,
  1b) and one that is `char/4` (1a). A grounding score cannot be 94 when
  the primitives it is grounded in were misread.
- **K1 in the sibling lane scored 620 against the same files** seven hours
  earlier. Two scores within three points, one idea, no cross-reference.

**The one number nobody computed, and it is the load-bearing one.** With
the values actually in `cordis.patch.yml:44-46` and the resolution
arithmetic in `compaction-basic/src/config.ts:172-197`:

```
messageBudgetTokens = contextWindow - reservedCompletionTokens
thresholdTokens    = floor(min(contextWindow * 0.0005, pressureBudget))
retainTokens       = floor(messageBudgetTokens * 0.0002)
```

For a 131,072-token window (opencode.jsonc's `z-ai/glm-5.3` limit):
threshold = 65 tokens, retain = 22 tokens. The post-compaction surface
cannot fit under 65 tokens: `renderChatView` (engine.ts:69-74) emits one
`id+n|text` line per tree line with a 512-byte node floor
(engine.ts:154, `nodeBytes ?? 512`), plus `ZOOM_HINT` (engine.ts:60-64),
plus the `<chat>` tags. A single 512-byte line is ~128 tokens at char/4
before anything else. So pressure re-qualifies on the very next request
and compaction fires again. **The knob set cannot converge; it is a proof
loop by construction.** `[PRIOR - suspect]` on the exact window - the
capacity comes from the dsh adapter, not opencode.jsonc, and for the
Kaggle twin it is 262144 - but the inequality holds for any window below
256,000 tokens, which covers every model in both configs.

**And the comment is off by 10x.** cordis.patch.yml:36 reads:

```
  # thresholdRatio 0.005 = compaction fires at 0.5% of the context window
```

while line 44 sets `thresholdRatio: 0.0005` - which is 0.05%, not 0.5%.
`retainRatio: 0.0002` is not mentioned in the comment at all. Everyone
reading the comment instead of the value will carry a factor-of-ten error
into every downstream document. That is precisely the failure mode this
REFUTATION is trying to stop: did the score for P2's Grounding 88 come
from the comment's number or the value's?

---

## 3. Is per-item cost available before compaction? No - and the policy has nothing to choose against

The question PROPOSAL.md:40 poses - "given a token budget and a log with
per-item sizes, choose which items pay" - assumes a per-item token cost
that is knowable in advance. On this stack it is not.

- **Per-item bytes: available, trivially.** `utf8Length` (bytes.ts:3). Not
  a token cost, and bytes.ts:1 says so.
- **Per-item token estimate before the request: available and unused.**
  `estimateMessage` (estimate.ts:88) is callable per message, pre-hoc. The
  optchat package never calls it (1a). It is `char/4` + overheads, and
  BRAINSTORM.md:185 already declared that primitive miscalibrated.
- **Per-item exact token count: not available at all.** The harness's own
  notes state the meter folds usage at post-step over the canonical logged
  envelope and that the projection is deliberately non-atomic; a consumer
  needing an exact same-boundary figure must call
  `ctx.tokenMeter.measure()` at its own request boundary
  (.agents/notes/implemented/architecture/2026-07-29-projected-token-usage-and-request-context.md:37),
  and the meter measures "the canonical logged request envelope and current
  surface", not items
  (.agents/notes/archived/architecture/2026-07-10-after-call-compaction-pressure-and-overflow-recovery.md:22).
- **llama.cpp's `/completion` usage does not attribute.** `prompt_tokens` /
  `completion_tokens` - and, under this fork's tap bridge, the cached vs
  uncached split - are whole-request totals. There is no per-message
  breakdown, and there is no way to get one out of a running server without
  a differential probe (re-send the request minus one item and subtract).

So: **pre-hoc the policy can choose against char/4 estimates, message
counts and byte sizes. Post-hoc it gets one aggregate number for the whole
request, already too late to inform the decision it describes.** PROPOSAL's
"a policy trained on measured costs" (PROPOSAL.md:40-41) is a statement
about a signal that arrives after the decision and does not decompose.

The honest version - and the one BRAINSTORM.md:185 already points at - is
an **EMA calibration**: keep the char/4 estimate as the prior, measure the
actual/estimate ratio per request, and blend. That is the only way
per-item cost becomes knowable-before-the-fact on this stack, and it is a
20-line change that neither PROPOSAL claims nor implements.

A second currency problem compounds it: the engine optimizes bytes
(view.ts:11-13), the config enforces tokens (cordis.patch.yml:46, and
`thresholdRatio` at compaction-basic/src/config.ts:191-194). Two units,
one log, no converter. Any "accounting layer" that lands first has to pick.

**What survives:** byte sizes as the accounting unit, honestly labelled as
bytes. The whole R5 metric `cache_hit_ratio = cache_n/(cache_n+prompt_n)`
is only available post-hoc from provider usage in any case, so it is a
measurement target, not a policy input.

---

## 4. R1/R3: P1 is a description of what exists, so what is actually new?

P1 inverts "compaction requires a summarization call" and R1 demands a
prompt "compiled from a state object". The shipped code already does this:

- `renderChatView(lines)` (engine.ts:69-74) is a compiler:
  `TreeLine[] -> <chat>` block of `id+n|text` lines, oldest first.
- `saveView` / `loadView` (store.ts:98-112) persist the state object.
- `summarize()` returns the compiled view **as the replacement summary**
  (engine.ts:273-276), so the surface becomes summary + retained tail and
  the chat never resets - exactly R1's "compaction edits the state, not the
  history".
- `zoom` (engine.ts:388-418) navigates the compiled state back to the
  verbatim source through `raw.jsonl`.

The prefix property R5 wants is also already claimed in-tree, twice:
view.ts:1-7 ("the previous view is a prefix of the next - the prompt-cache
property") and tree.ts:1-7 ("keeps old lines put while new ones churn,
which is what the prompt cache needs"). That property is only partially
true and PROPOSAL inherits it unexamined: `duePairs` (tree.ts:35-61) is
sorted `b.due - a.due` with `due = (T+1)/2^l - i` (tree.ts:22), so the
most-due pair is the *oldest*. A merge rewrites the view from the merged
line onward and `applyMerge` re-sorts and the parent text differs from the
two children's; the rendered prefix is stable only up to the first merge
point, and the first merge point is at the head. R5's cache-hit metric
would measure a hit ratio that this merge order actively destroys.

**So what is new in R1?** Exactly one tier: `pinned`. `working` is the
view. `retrieved` is `zoom`. Nothing in the package is protected from the
due-order merge - there is no pin, no value-class input, no override -
because `duePairs` ranks purely by age. That is the real gap, and it is
small.

**R2's "three tiers"** is a restatement of CoDA-GQA-L, transcribed
(BRAINSTORM.md:200-207), and the transcription itself carries two warnings
that PROPOSAL does not carry forward: bounded policies trained naively are
catastrophic, and "hand-rolled eviction policies need empirical
validation". PROPOSAL's Recombination line proposes to supply the training
signal from "measured per-item cost" - which section 3 shows is not
available in the form required. R2 therefore cannot start on this disk
without first solving section 3.

**R3's status field is genuinely new.** `LogEntry` is
`{ i, kind, text, size, date }` (store.ts:18-25): no `status`, no
`supersedes`, no provenance beyond an ISO date. And there is a design
constraint P2 does not state: the store's header requires that the tree
be "a pure function of the log alone" and rebuildable from it
(store.ts:3-6), which forbids in-place mutation of a status field. A
supersede marker must be an **appended** entry, never an edit - which
makes the archive append-only in a stronger sense than P2's wording
implies, and which also means the supersede entries need their own kind in
`LogKind` (store.ts:16), which currently has no such value.

R7's provenance requirement is already half-satisfied: `raw.jsonl` keeps
every leaf's verbatim source (store.ts:121-126, read at store.ts:133-144),
so "the model can be pointed back to the verbatim source" is shipped.

**What survives:** `zoom` + `raw.jsonl` are the real provenance story and
the reason compression-based summarization can be the runner-up rather
than the loser. R3's status field is real new work. R1 is documentation.

---

## 5. What PROPOSAL.md missed

### 5a. The idle-time model call was never priced

R4 (BRAINSTORM.md:213-215) says compaction runs between turns because
"blocking compaction pays summarization latency + a full re-prefill at the
worst moment". Nobody priced the thing R4 wants to move off the critical
path.

The merge phase is a **serial** loop. engine.ts:240-263:

```ts
    while (viewBytesNow() > VIEW_SOFT_BYTES) {
      ...
      const text = await this.oneShot(
        MERGE_PROMPT(renderChatView(rest), a.text, b.text), target, signal)
```

Each iteration re-renders the entire current view into the merge prompt
(`renderChatView(rest)`, engine.ts:256). At the configured bounds a batch
runs 128,000 -> 64,000 bytes (view.ts:11-13), removing 64,000 bytes; each
merge nets ~512 bytes (two 512-byte nodes become one 512-byte parent,
engine.ts:154), so **~125 merges per batch**, serially, each with a
shrinking view in its prompt averaging ~96,000 bytes = ~24,000 tokens at
char/4. Prompt prefill alone for one batch: ~125 x 24,000 = **~3.0M
tokens**, before a single output token. The leaf phase is 8-way concurrent
(engine.ts:219-236, `concurrency ?? 8` at engine.ts:155); the merge phase
is not.

`[PRIOR - suspect]` on decode rate - the opencode.jsonc comment for the
27B PTQ1_0 model says "~1 t/s" - but at 1 t/s that is ~833,000 s (~9.6
days) of pure prefill per compaction batch, and at 30 t/s it is ~100,000 s
(~28 h). On the local lane, R4 is not a scheduling preference; it is
arithmetically impossible at these batch sizes.

**What survives:** the fix is two lines in engine.ts, not new
architecture - do not re-render the whole view into the merge prompt (pass
`a`, `b` and a bounded window), and cap merges per turn.

### 5b. The circularity, and where the compaction call actually goes

PROPOSAL never mentions that the thing doing the compaction is the thing
whose context is being managed.

`resolveTarget` (engine.ts:289-298) returns the configured
`compactionProvider`/`compactionModel` pair if both are set, else **"the
conversation's own route"**. The daavile profile sets neither: a scan of
`cordis.patch.yml` for `compactionProvider`, `compactionModel`, `maxTokens`,
`nodeBytes`, `concurrency` returns nothing - the compaction block is five
keys, `auto`/`distillUniverse`/`thresholdRatio`/`retainRatio`/
`headroomTokens` (cordis.patch.yml:39-46). So compaction rides the
conversation's route, and the same file pins that route at
cordis.patch.yml:79-82 to `provider: nvidia`, `model: z-ai/glm-5.3-flash`
- an HTTPS API endpoint. On this machine the "metabolism layer" is a cloud
call, one per leaf, with no generation cap (`maxTokens` unset means
engine.ts:314 spreads nothing, and the 512-byte clamp at engine.ts:331
truncates *after* the model has already emitted everything), plus an
unawaited, uncancelled background cascade (`void this.distillUniverse(...)
.catch(() => {})`, engine.ts:269-271) that fires more of the same calls.

And the framing is a category error: this design lives under
`shared/llama.cpp-abelianIUT/docs/daavfx/plans/context/` and argues
about llama.cpp's `/completion` usage and `cache_n`/`prompt_n`
(PROPOSAL.md:19), while the component it proposes to change is a
TypeScript Cordis plugin that currently routes to NVIDIA.

Point it at a local llama-server and the circularity bites: the server that
must serve the compaction request shares one GPU with the model whose
context is being compacted - opencode.jsonc's comment describes
`serve-model.ps1` running ports 8091-8102 concurrently. With
`thresholdTokens = 65` (section 2) and an 8-concurrent leaf phase, a
compaction storm starves the very model it is compacting.

**What survives:** the honest finding is that the local lane has exactly
one cheap lever - a small, fast, quantized model dedicated to compaction on
its own port with its own `compactionProvider`/`compactionModel` - which
the profile currently does not set, and which is a config change, not a
research programme.

### 5c. The vault-design lane is building this same thing, right now, under another name

`docs/daavfx/plans/vault/PROPOSAL.md:10-45` K1 - "The vault is the memory
system - OptChat worlds as the agent/skill/soul substrate" - and
`plans/context/PROPOSAL.md:25-65` P1 - "The ledger is the log; compaction
is accounting" - are the same thesis with a different tenant. Same
inversion ("the store carries only derived state - rebuildable from the log
alone" appears in both, plans/vault/PROPOSAL.md:23 and PROPOSAL.md:60).
Same primitive list (the world store, the due-order merge, the wire's
read-only `memory.worlds`/`memory.read`, tmp+rename receipts, `~/.dsh`).
Same safety-paragraph template. Same score formula. Same "Next: the
refuter". K1 = 620, P1 = 617.

They also **disagree about the state of the same file, on the same day**:

- `plans/vault/NOVEL-ANGLE.md` (mtime 2026-10-27 13:26) lists as
  *future* build-plan step 1: "Fix the lying wire ... `optchat_root()` +
  `memory_worlds()` emit logical world names".
- `plans/context/PROPOSAL.md` (mtime 2026-10-27 14:56) cites the wire
  as a *shipped* primitive, "read path fixed this session".
- `daavile-wire.rs` itself: mtime 2026-10-27 13:43 - between the two.

So the fix landed between the two documents, the second one cited it as a
primitive without checking that a sibling lane had, ninety minutes earlier,
listed the same fix as unfinished work. Neither document references the
other. That is not two plans; it is one plan written twice.

And there is a third overlap PROPOSAL does not see at all: the
`eval-bridge.ts` module (optchat/src/eval-bridge.ts), which already reads
`~/.dsh/memory/evals/<model>.jsonl` and feeds it into the universe world as
append-only notes (eval-bridge.ts:38-39, 65) - the exact ledger shape that
`harness/PROPOSAL.md:25` Lane A proposes to create, and which PROPOSAL.md's
grounding table omits entirely.

### 5d. One more miss: the study substrate is not three transcripts

BRAINSTORM.md section 8 wants "three existing long session transcripts"
scored offline. The grounding table's answer is a 26.83 GB live SQLite
database with a 13.5 MB WAL (1g). Nobody scoped extraction, nobody
confirmed the schema, and nobody noted that opencode's session records are
not in a shape the optchat log's `LogEntry` (store.ts:18-25) can receive
without a mapping layer. The "one experiment this week" has no substrate.

---

## 6. The directory question - the actual map, defended against the duplication attack

**Current state, verified.** `docs/daavfx/` contains `README.md`
(2026-10-22), `REPO-MAP.md`, `TRACK-B-DISTILLATION.md` and eleven
directories: `app-lane`, `auditor-ISAYY`, `auditor-MAX10`, `break1650`,
`context-pipeline`, `experimental-dgpu`, `harness`, `moe-lab`, `overlay`,
`skills`, `vault-design`. The Lane index (README.md:35-46) declares six of
them. Five are already litter.

**The duplication attack says: do not add a sixth lane, the two plans are
the same plan.** That is correct, and the answer is not a folder - it is a
shared primitive table.

### Proposed map

```
docs/daavfx/
  README.md            the lane index; a folder not declared here is not a lane
  REPO-MAP.md          ours-vs-upstream inventory (unchanged)
  plans/               <-- THE MERGE
    PRIMITIVES.md      ONE table: primitive, file:line, verified-on date,
                       what it does, and what it does NOT do
    context/           was plans/context/   (the compaction/context plan)
    vault/             was plans/vault/       (the memory/skills plan)
    loop/              was harness/            (the self-improvement plan)
  app-lane/            transport + UI record (unchanged)
  skills/novel/        the RAG chunk library (unchanged; add the SKILL.md)
  moe-lab/ break1650/ overlay/ experimental-dgpu/   campaign records (unchanged)
```

### Defense against "you are just adding a folder"

**1. Duplication is cured by PRIMITIVES.md, not by one folder.** The two
plans did not collide because they were in different folders; they collided
because each re-derived "the primitives" from scratch and got different
answers from the same files. Section 1 is the receipt: P1 called
`main.jsonl` the transcript (it is the universe notes log),
`covered.txt` an accounting (it is an integer watermark), `tokenMeter`
injected (it is a string in an array), and `push.ts` the merge policy (it
is retained-for-fidelity rollback scaffolding with no caller). A table with
file:line and a verification date makes the next plan's grounding a diff
against the last one's, instead of a fresh guess. The 620-vs-617 scores
are what happens without it.

**2. Do not merge into `plans/loop/`.** `plans/loop/` is not a plan lane - it is
the onboarding and Lane-A contract package for a *different repo*, the
RYIUK harness at `shared/daavile_harness/daavilefx_harness`. That repo's
own rules (packages/AGENTS.md: package READMEs updated in the same commit,
per-file 100% coverage under `test:coverage`, a keyless recorded-session
snapshot for every model-visible change, `doc-sync` gates, a duplication
detector) cannot be satisfied by a design folder. context-pipeline's
*implementation* lands in that repo; its *design* belongs here. Putting the
design inside the onboarding package would either break those gates or get
the design quietly exempted from them.

**3. Keep `app-lane/` separate, and this is the strongest reason of all.**
`daavile-wire.rs` lives at
`APPS/quantum_dashboard-fx/src-tauri/src/bin/`, and that app's own
AGENTS.md rule 1 is "Do not write to `src-tauri\src\main.rs` or
`premium_backend`" because another developer's Track A is live there. P1
cites the wire as a *shipped primitive* while proposing to build an
accounting layer that would need a new read surface on it. Any plan that
touches the wire must be authored in `app-lane/` and handed over across
the lane boundary - never merged into a context lane that would then edit a
Track A file. Note also that `dsh-compaction-optchat` itself lives under
`F:\DAAVILE_ECOSYSTEM\...\shared\daavile_harness\`, one repo away from the
fork whose docs folder this is - which is the actual reason all four of
these lanes keep producing overlapping plans from partial views.

**4. The index is the enforcement.** `README.md` is eleven days stale and
missing five directories. The rule "not in the index, not a lane" costs
nothing and prevents the next `auditor-MAX10`. It also means the next
plan's refuter can check the index before scoring grounding.

**5. No content is deleted.** `plans/context/` -> `plans/context/`,
`plans/vault/` -> `plans/vault/`, `plans/loop/` -> `plans/loop/`; one
`plans/PRIMITIVES.md`; every plan keeps its PROPOSAL/REFUTATION pair; the
index records, per plan, which premises its own REFUTATION killed
(plans/vault/NOVEL-ANGLE.md already records four: no receipts in optchat,
the wire read path off by one directory, the discovery table publishing a
directory as a world, skill compaction being cache-hostile - four facts
P1 then had to rediscover).

---

## What I would build first instead

Ordered by cost and by what removes real risk first. Five items. The
first two are ~40 lines total and one of them prevents silent data loss.

**1. `packages/compaction/optchat/src/store.ts` - atomic writes, loud
failures.** `saveView` (store.ts:99) and `markCovered` (store.ts:157) go
tmp+rename, borrowing the pattern PROPOSAL wanted to import anyway and
which `daavile-wire.rs:279-282` already implements. `loadView`
(store.ts:109-111) stops catching a parse error and returning `null` -
that is the one code path in this package that silently deletes a world's
entire memory. `coveredCount` (store.ts:152-154) stops converting a torn
read into 0, which currently causes double-leafing and silently stale
`zoom`. `readLog` (store.ts:74-78) stops letting one bad line kill the
whole read. Until this lands, "the log is the truth; every derived state
rebuilds" (PROPOSAL.md:59-60) is false in exactly the direction that
matters.

**2. `packages/compaction/optchat/src/engine.ts` - make `tokenMeter` real.**
One call site. Read `this.ctx.tokenMeter` once and persist the estimate it
already computes (`estimate.ts:88`) per leaf, as the token twin of the
byte `size` that store.ts:23 already carries and nobody reads. This is the
smallest change that makes "compaction as accounting" a true statement
rather than a byte proxy, and every later policy in P1 is denominated in
whatever unit this lands in.

**3. `packages/bundle/daavile-cli/cordis.patch.yml` - revert the proof
knobs, fix the comment, pin the route.** Set `thresholdRatio`/`retainRatio`
back to the base defaults (`compaction-basic/src/config.ts:20,23`: 0.8 and
0.16) or, if the low values must stay for the H3 proof, correct line 36,
which claims 0.005 / 0.5% while line 44 sets 0.0005 / 0.05%. Add
`compactionProvider`/`compactionModel` explicitly so the compaction route
stops silently inheriting the conversation's cloud route
(engine.ts:293-296) and becomes a declared, cheap, local target. Add
`maxTokens` so the 512-byte clamp (engine.ts:77-86, 331) is a generation
cap instead of a post-hoc truncation of an already-paid-for response.

**4. `docs/daavfx/plans/PRIMITIVES.md` (new, after the merge in section 6)
- one table, ~15 rows.** Each row: primitive, file:line, what it does,
what it does not do, verified-on date. Fill it from the scans in section 1:
tokenMeter (declared, never read), covered.txt (an integer watermark),
main.jsonl (universe notes, not the transcript), LogEntry.size (bytes,
write-only), duePairs (the real merge order; push.ts has no caller), 14
specs (verified), 10 wire tests (verified), the guard test that cannot
fail, the 26.83 GB db, the ~125-serial-merge batch cost. This file is what
makes the next plan a diff instead of a re-derivation, and it is the only
artifact that would have prevented the 620-vs-617 collision.

**5. `packages/compaction/optchat/src/tree.ts` - feed `LogKind` into the
merge order.** `LogKind = 'user' | 'agent' | 'tool' | 'echo' | 'work' |
'note'` (store.ts:16) already exists and is used only to shape the leaf
prompt (`<kind>: <input>`, engine.ts:34); it never enters a budget
decision. Change `duePairs` (tree.ts:35-61) so the ranking stops being
purely `(T+1)/2^l - i` (tree.ts:22) and can preserve user instructions and
decisions over tool steps and raw observations. This is R6 with the
smallest possible blast radius: no model call, no status field, no new
file, no new lane. It is therefore the first *feature* that should be
built, ahead of P2's full contradiction reconciler and ahead of everything
that depends on section 3 being solved.

**Directory decision:** merge the three planning lanes into
`docs/daavfx/plans/{context,vault,loop}` behind one `PRIMITIVES.md` and
one index; keep `app-lane/`, `skills/novel/` and the campaign records
where they are; merge nothing into the harness repo, whose rules would
reject a design folder and whose code is the target rather than the home.
Re-index `README.md` the same day, including `skills/`, `plans/vault/`,
`plans/context/`, `experimental-dgpu/` and the two `auditor-*` folders
that have been invisible for five days.
