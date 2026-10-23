# LANE-A-CONTRACT - how the harness calls the existing eval runners

Owner split (operator decision, 2026-10-22): the daavile-harness agent builds
the Lane-A adapter + leaderboard mirror against THIS contract; the infra/bench
agent owns the runners and audits the adapter. Neither edits the other's files.

## What already exists (do NOT rebuild)

1. **MT5 agent bench** - `backtesting_pipeline\llm_bench\tools\bench_driver.ps1`
   (harness v1.3). 30-turn MCP agent task against the MT5 Strategy Tester with
   SEALED ground truth (`ground_truth\` - never enters any prompt; only the
   scorer reads it). Spawns its own llama-server on port 8077.
   - Invoke: `bench_driver.ps1 -ModelPath <gguf> -ModelName <name> -Ngl <n>
     -Ctx 8192 -LlamaPort 8077 -MaxTurns 30 [-StopAfterTurn n] -LlamaServer
     <llama-server.exe>`
   - Emits per run dir `llm_bench\runs\<name>\`: `driver.log` (turn-by-turn),
     `transcript.jsonl`, `metrics.json` (turns/actions/refused/native/
     reasoning_chars/prompt+completion tokens), `final_report.md` (only if the
     model concludes).
   - Scorecards: hand-written JSON in `llm_bench\scores\<model>.json` (see
     existing cards for the exact schema).
   - REQUIREMENT: the bench MT5 terminal must be up first - 22302 must answer
     (401 without token = healthy). `F:\trading_terminals\mt5-3\terminal64.exe`.
2. **Quality harness** - `llama.cpp-abelianIUT\scripts\daavfx\quality-harness\run-harness.ps1`
   (12 tool-use tasks) + `score.py`.
   - Invoke: `run-harness.ps1 -Tag <tag> -ServerUrl http://127.0.0.1:8083`
     (you run your own llama-server on 8083 first).
   - Emits: `quality-harness\results\responses-<tag>-<stamp>.jsonl` and
     `score-<tag>-<stamp>.jsonl`. Each score line: `{tag, id, task_ok, checks:
     [[name, bool], ...]}`. Sum `task_ok` for tasks_ok/total; flatten `checks`
     for checks_pass/total.
3. **Flint wrappers** (same contract, once built): `run-flint-bench.ps1`
   (wraps #1 with Flint defaults) and `flint-quant-sweep.ps1` (quality + MT5
   per quant, writes one summary JSON).

## The adapter (the coder builds this)

One `eval` entry point in daavile-harness that:
1. Takes a model id + optional axis.
2. Shells out to the runner(s) above (they are the source of truth; no
   re-implementation of scoring).
3. Parses `metrics.json` (axis A) and the score JSONL (axis B).
4. Writes ONE append-only record per run to BOTH homes:
   - `~/.dsh/memory/evals/<model>.jsonl` (harness-native leaderboard)
   - mirror reference: the infra lane keeps `llm_bench\scores\` cards as the
     sealed-lane evidence; the adapter reads, never rewrites them.

Record schema (one JSON object per line):
```json
{"date": "2026-10-22T14:00:00Z", "model": "qwen3.5-4b-q4km", "axis": "mt5-agent",
 "run_dir": "runs/qwen3.5-4b_v13_gpu8k_r2", "turns": 30, "actions": 19,
 "refused": 2, "goal_achievement": false, "result_accuracy_0_10": 0,
 "quality": null, "wall_clock_s": 1740, "tps": 10.2,
 "verdict": "INCOMPLETE (loop)", "card": "scores/qwen3.5-4b_v13_gpu8k.json"}
```
`quality` carries `{tasks_ok, tasks_total, checks_pass, checks_total,
score_file}` when axis B ran; `null` otherwise.

## The dual-axis keep/drop rule

The better a model does on BOTH axes, the higher its chance of being kept.
The leaderboard is the join: `model -> axis A card + axis B score`. Axis C
(operator trading Q&A) is deferred - leave a `trading-qa: null` slot in the
schema so it slots in later without a format break.

## Hard rules

- ASCII only in every file you touch.
- INFLIGHT.md row (append-only) for this work; commit messages end with
  `Work-Note: <your-id>`; no commit or push without the operator.
- Never touch: `llm_bench` internals, `llama.cpp-abelianIUT\src\`, the fork's
  `premium_backend\`, the app's `main.rs` command registry.
- Ports: 8077 (bench), 8083 (quality). NEVER bind or kill 8080 (the
  operator's app server), 22302/22368 (MT5 MCP), 3141, 6790.
- `ground_truth\` content NEVER enters any prompt or tool result.
