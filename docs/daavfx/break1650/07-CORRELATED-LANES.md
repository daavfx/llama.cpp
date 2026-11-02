# 07-CORRELATED-LANES - what the other engineer(s) are cooking, and what this program must not break

The operator is now personally handling the harness lane (was a coder agent).
That work is correlated with this program: this program produces benchmark
inputs; the harness lane produces the scoring/leaderboard surface. Both must
stay compatible.

## The harness lane (operator-handled) - `daavilefx_harness`

| Piece | State (2026-10-24) | Correlation with this program |
|---|---|---|
| `packages/eval/eval-adapter` (H0) | **cleared re-audit 10/10 specs**; idempotent re-ingest keyed by canonical model; leaderboard mirror writes `~/.dsh/memory/evals/<model>.jsonl` | **This program's benchmark cards ARE the adapter's inputs.** Every card must carry: model id, run_dir, turns, actions, refused, goal flag, accuracy, quality sub-object, wall clock, verdict - the adapter schema is the card schema |
| Leaderboard mirror + `readLeaderboard` (latest per model+axis) | built | the dual-axis table (quality harness score + MT5 agent score) is the keep/drop rule the operator defined: "better in both = higher chance of keeping" |
| `launch-llm.ps1` (H1) | runtime-verified end to end (load, health, stop, clean port) | this program's GPU experiments can use it; it is WMI-detached and proven |
| Harness^2 template spec (proposer/prober/composer) | types + fleet JSON, no dispatch implementation | the future lane that would automate running experiments from this register |
| OptChat end-to-end proof (H3) | **pending a real long session by the operator** | none directly; it is the harness memory proof, not a perf surface |
| Git history | pushed commits `b64fe849`, `71db9d85`, `eb87f9b9` in `daavfx/daavile-harness` | the lane keeps its own INFLIGHT ledger; the auditor's findings landed there |
| Contract doc (`plans/loop/LANE-A-CONTRACT.md`) | normative: shell out to the runners, never re-implement scoring; the sealed ground truth never enters prompts | read it before touching anything harness-side |

## The quantum app (Tauri) - operator's daily surface

- `APPS\quantum-dashboard-fx`: the Agent/IDE/Quantum realms. The agent chat
  was **de-mocked on 2026-10-23** (`c1028e8`): no seeded demo conversations,
  no canned replies; the only reply path is the real backend.
- **The app's own llama-server runs on port 8080 - never bind, never kill.**
- The app's premium MCP bridge is 3141 (one app at a time).
- The app contains the MT5/MCP terminal suite settings and the Data Forge;
  the Agent realm's chat invokes the cortex commands in `premium_backend`.
- HARD RULE inherited from the fork context: never write to
  `src-tauri\src\main.rs` or `premium_backend` - another dev's live lane.

## The MT5 bench infrastructure

- `terminal64.exe` at `F:\trading_terminals\mt5-3\` must be running before
  any agent bench; 22302 answering = healthy (401 without token is fine),
  metaeditor 22368 down is tolerated.
- MCP endpoints carry bearer tokens in `bench_driver.ps1` (never logged).

## What this program must not break (the audit checklist)

1. Ports: 8080 (app), 8077 (bench driver), 8083 (quality harness), 3141
   (premium MCP), 22302/22368 (MT5 MCP), 6790 (engine). Nothing else binds.
2. The sealed ground truth (`llm_bench\ground_truth\`) never enters any
   prompt - only the scorer reads it.
3. Process hygiene: any server/launcher this program starts, this program
   kills. The operator's own processes are never touched.
4. The fork's `premium_backend/` and the app's `main.rs` registry are
   off-limits (working rule 1).
5. ASCII everywhere; commits carry `Work-Note: <id>` + `Assisted-by:`; no
   push without the operator's explicit OK.
6. The card schema stays compatible with the harness adapter's ingest
   (READ the CONTRACT before changing a card format).

## Lanes status summary

| Lane | Agent | Current posture |
|---|---|---|
| break1650 (this folder) | opencode | plan complete; experiments X1 running; awaiting next green |
| harness/CLI/orca/quantum | operator (ex-coder lane) | H0 cleared, H1 closed, H2 delivered+superseded, H3 awaiting operator session |
| moe-lab | archived | closed; instruments inherited by this program |
| RYIUK archive | operator | audited; trust ledger produced; kimi_k3 design adopted as converged prior art |
