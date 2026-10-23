# CODER-ONBOARDING - catch-up pack for the harness lane agent

You are taking the HARNESS LANE. You have the daavile-harness context. You do
NOT have the context of the two other lanes that have been running on this
machine (infra/bench + moe-lab). This file is that missing context, compressed.
Read it top to bottom, then start at "Your tasks".

## Who is who

| Lane | Agent | Owns |
|---|---|---|
| Harness lane | YOU | `daavile-harness` repo, fleet templates, Lane A adapter, leaderboard mirror, OptChat |
| Infra/bench lane | the opencode agent (auditor) | llama.cpp fork `src\`, commits, build/fetch/bench scripts, `llm_bench\`, scorecards; audits YOUR outputs |
| moe-lab lane | the moe-lab coder | `docs\daavfx\moe-lab\`, X-ray kit, router analysis, surgery, `launch-llm.ps1` |

The operator is the only human. Nothing gets committed or pushed without him.

## The three places you must know

1. **The harness docs you already have**: this folder
   (`docs\daavfx\harness\`): PROPOSAL.md, WHAT-WAS-BUILT.md,
   WHATS-MISSING.md, plus LANE-A-CONTRACT.md (your adapter spec) and this
   file. LANE-A-CONTRACT.md is the contract between you and the bench
   runners - it is normative, not background.
2. **The bench** (infra lane, do not modify):
   `F:\DAAVILE_ECOSYSTEM\trading_ecosystem_11\trading_ecosystem_9.0\main_ecosystem_trading\backtesting_pipeline\llm_bench\`
   - `SCOREBOARD.md` - the dual-axis keep/drop table (READ THIS FIRST)
   - `scores\*.json` - one honest card per model run (schema reference for you)
   - `runs\<name>\metrics.json` - machine-readable run results (your input)
   - `ground_truth\` - SEALED. Never in a prompt. Ever.
3. **The fork + moe-lab** (moe-lab lane + infra lane):
   `F:\DAAVILE_ECOSYSTEM\trading_ecosystem_11\trading_ecosystem_9.0\shared\llama.cpp-abelianIUT\`
   - `docs\daavfx\README.md` - front door to ALL the docs
   - `docs\daavfx\moe-lab\RESULTS.md` - the LFM campaign loot (2 production
     configs, the falsification ledger, the X-ray kit procedure)
   - `docs\daavfx\moe-lab\FLINT-CAMPAIGN.md` - the next-model plan (Flint)
   - `INFLIGHT.md` - the work ledger (30 rows of history + rules)
   - `scripts\daavfx\` - the runners, launchers, quality harness

## What just happened (the state you inherit)

- The LFM campaign closed: big MoE on a 4GB GPU is solved at 18.9 t/s (split
  config), the router is load-balanced (no cold tail), 10 falsification
  entries, all documented in moe-lab.
- The Flint upstream merge is COMMITTED (6 commits, 2026-10-22) into a
  worktree `shared\llama.cpp-flint-wt` - not built yet. Flint = 39.8B MoE,
  quants from 11.4 GB (IQ1_M) to 42.3 GB (Q8). Build/fetch/sweep scripts are
  written and parse-checked in `scripts\daavfx\`.
- The MT5 v13 chain just finished (2026-10-22): K2 confirmed failed-protocol
  (0 actions / 60 turns total), qwen GPU-8k looped (speed record 10.2 t/s but
  regression vs its CPU run), granite first protocol-clean run (still
  incomplete, 1.6 t/s). Cards + SCOREBOARD.md are written.
- The MT5 bench needs the bench MT5 terminal RUNNING before any agent run
  (22302 answers 401 without token = healthy). It was down this morning and
  invalidated two runs before the operator's agent restarted it.

## Your tasks (in order)

**H0 - the eval adapter (now, CPU-light).** Per LANE-A-CONTRACT.md: one `eval`
entry point that shells out to the runners, parses metrics.json + score JSONL,
and appends one record per run to `~/.dsh/memory/evals/<model>.jsonl` (schema
in the contract). Plus the Harness^2 template spec (proposer -> prober ->
composer) + `harness-lessons.jsonl` format. Work in the daavile-harness repo.
The infra agent audits against the contract.

**H1 - runtime-verify launch-llm.ps1 (the moe-lab coder's unverified item,
~2 min GPU).** `shared\llama.cpp-abelianIUT\scripts\daavfx\launch-llm.ps1`
launches an 8B llama-server DETACHED via WMI and -Stop kills pid + port owner.
It was hardened but never runtime-verified (the PC was busy). Load -Mode
split, confirm health, then -Stop and confirm the port is free. Report the
result to the moe-lab lane (it closes their row update 25).

**H3 - the OptChat end-to-end proof (after H1).** WHAT-WAS-BUILT.md Tier 1 #1:
one real long session that crosses the compaction threshold; watch the view
replacement, zoom, and the universe distiller. Document what fired in
WHAT-WAS-BUILT.md's honest-state section.

**H2 - X-ray on Flint (WAIT for the infra agent).** Only after the infra
agent builds the merged fork and fetches Q2_K_XL. You run the X-ray kit
(moe-lab RESULTS.md) with DAAVFX_ROUTER_LOG over a short session and write the
verdict row (load-balanced vs harvestable cold tail) into
moe-lab\FLINT-CAMPAIGN.md. That verdict gates the infra agent's quant sweep.

## Hard rules (all lanes)

- ASCII only in every file. No unicode dashes/arrows/quotes.
- INFLIGHT.md: append a row for yourself (id, date, what, why, files, status)
  before you start; keep it current. Commit messages end `Work-Note: <your-id>`,
  use `Assisted-by:`, never `Co-authored-by:`.
- No commit, no push, without the operator's explicit OK.
- Never touch: `llm_bench\` internals, the fork's `src\`, `premium_backend\`,
  the app's `main.rs` registry.
- Ports: yours to use are 8083 (quality server) and any ephemeral; NEVER
  8080, 8077 (bench), 22302/22368 (MT5 MCP), 3141, 6790, 6768.
- The PC: the operator risks it for bench runs, but ask before heavy
  inference. No parallel GPU runs with the infra lane's work.
