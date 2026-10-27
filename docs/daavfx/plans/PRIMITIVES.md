# PRIMITIVES.md - the one table every plan grounds against

Date: 2026-10-27. Rule: a plan that cites a primitive cites a row. If the
row is missing or stale, the plan adds the row with its file:line and a
verification date instead of re-reading the file. `[PRIOR - suspect]` means
no file in this tree and no transcript can reproduce the value.
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
