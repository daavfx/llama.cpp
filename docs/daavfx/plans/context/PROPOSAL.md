# PROPOSAL.md - the theoretical plan (novel-skill scored)

Date: 2026-10-26. Method: the `novel` RAG discipline over
`BRAINSTORM.md` + the on-disk assets. Score =
`2*I + S + 3*Novelty + 2*Grounding + 2*PurposeAgnostic - Penalty`,
maximize I subject to S >= threshold. `[PRIOR - suspect]` for anything not
verifiable from the transcribed text or a disk file.

---

## What we already own that this plan consumes (grounding)

| Asset | Path | State |
|---|---|---|
| OptChat engine + store | `daavilefx_harness/packages/compaction/optchat/` | shipped; compaction fired 10-25 |
| Due-order merge + 128k->64k view policy | `optchat/src/push.ts`, `view.ts` | shipped, 14 specs pin it |
| The native wire (read-only memory methods) | `quantum-dashboard-fx/src-tauri/src/bin/daavile-wire.rs` | shipped, 10 tests; read path fixed this session |
| The compaction profile knobs | `daavile-cli/cordis.patch.yml` | shipped (thresholdRatio/retainRatio/headroomTokens) |
| The token meter + timing | `optchat` engine's `tokenMeter`; llama-server's `cache_n`/`prompt_n` | partially instrumented |
| The novel RAG layer (chunks + citations) | `docs/daavfx/skills/novel/` + the config copy | in use by the audit lane |
| Session transcripts (the study substrate) | `~/.local/share/opencode/opencode.db` | exists; 28 GB |

---

### Candidate P1: "The ledger is the log; compaction is accounting"

**Consensus says impossible because:** compaction must be a model call.
The standard answer (opencode's own pipeline, transcribed in
BRAINSTORM.md section 2) is: detect token pressure, call the LLM to
summarize, replace the oldest N. Harnesses treat compaction as a
summarization feature; nobody treats it as bookkeeping. `[PRIOR - suspect]`
on the strength of the consensus; grounded on the transcribed mechanics.

**Assumption inverted:** "Compaction requires a summarization call." If the
transcript is an append-only log whose per-message cost is already counted
(the harness already sums tokens before each request), then compaction is a
*budget problem*, not a language problem: given a token budget and a log
with per-item sizes, choose which items pay. A model call is one way to
choose; a policy trained on measured costs is another. The OptChat due
formula `(T+1)/2^l - i` is already a policy that needs no call.

**Rebuild from primitives (all on disk):** the append-only world log
(`main.jsonl`), the due-order merge tree (push.ts), the view compiler
(view.ts: the previous view is a prefix of the next), the covered-count
accounting (`covered.txt`), the token meter already injected into the
engine. The new work is the *accounting layer*: per-item sizes + costs
attached to the log, and the budget decision made against them.

**Recombination (distance bonus):** KV-cache eviction policy (CoDA-GQA-L's
ring buffer + novelty bank + EMA centroids, transcribed R2) ×
compaction-as-accounting (the log's per-item sizes) × contradiction
reconciliation (transcribed R3, the 57/21/73 receipt). The eviction
literature assumes a trained model; here the "training signal" is the
measured per-item cost and the contradiction events already emitted by the
transcribed metabolism layer.

**Safety enumeration:** pure code, pure accounting, filesystem under
`~/.dsh`. No new model calls on the critical path (R4: idle-time compaction
means the call already happens off-turn). Reversible: the log is the truth;
every derived state rebuilds. S = 93.

**Purpose-agnostic justification:** it ships as "a cost-accounted transcript
store with a policy-driven view" even before any new policy is trained.

**Score:** 2*72 + 93 + 3*85 + 2*94 + 2*78 - 0 = **617**

---

### Candidate P2: "Contradiction metabolism as a first-class pipeline stage"

**Consensus says impossible because:** contradiction resolution belongs to
the model, not the harness; a harness that parses facts will mis-parse them.

**Assumption inverted:** the harness does not need to parse facts. It needs
to detect *conflict events* - "this message states X; an earlier pinned
item states not-X" - and the cheapest detector is the model that is already
in the loop, running once per turn over only the delta (delta-prune,
transcribed R3). The expensive part (resolution) stays with the model; the
cheap part (detection + never-blend bookkeeping) is harness work.

**Rebuild:** the pinned set (R1's state object), a status field per item
(`active` / `superseded`), a delta comparator that emits conflict events,
and the idle-time reconciler (R4). All four are files under `~/.dsh`.

**Safety:** pure code + one model call per turn over a bounded delta.
S = 91. Grounding: the 57/21/73 and 47.8-point receipts are transcribed;
none of them is verifiable here, so Grounding is capped at 88 and tagged.

**Score:** 2*68 + 91 + 3*80 + 2*88 + 2*75 - 0 = **575**

---

### Candidate P3: "Operator-verifiable rollout with correctness receipts"

**Consensus says impossible because:** harness changes to compaction are
(measure nothing, ship, hope) - the transcribed PR map is a list of
admissions that each default was wrong for months.

**Assumption inverted:** every compaction decision can carry a receipt that
predates the change: the policy name, the budget, the per-item sizes that
drove it, and the canaries retained after it (transcribed section 6). Then
a policy change is a diff over receipts, not a vibe. This is the Bend
pattern (honesty as executable gates) applied to context management.

**Rebuild:** the ledger row format (Work-Note IDs already exist), the
receipt sidecar (the `daavile-wire.rs` tmp+rename pattern, since the
optchat store's `appendFileSync` is torn-line unsafe), and the canary
harness (inject at turn 1, probe at 10/30/50 - offline, no GPU).

**Safety:** pure accounting. S = 97.

**Score:** 2*55 + 97 + 3*58 + 2*90 + 2*72 - 0 = **541**

---

### Candidate P4 (rejected): provider-native compaction as the default

The transcribed text is explicit: it is an opaque encrypted checkpoint,
only valid for the same provider/model/endpoint. It kills portability and
makes the store unrunnable on the local llama-server lane. REJECTED by
safety containment; recorded as a failed approach for the chunk library.

---

### Ranking

P1 (617) > P2 (575) > P3 (541) > P4 (rejected). Composition: P3 is the
evidence layer, P2 the integrity stage, P1 the compaction core. Next: the
refuter.
