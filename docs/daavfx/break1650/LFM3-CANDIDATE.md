# LFM3-CANDIDATE.md - the speed-lane candidate card (L-1)

Date: 2026-10-28. Model: LFM3-1.7B-QAD-Q4_0 (LiquidAI), 1,049,615,680 bytes
(0.98 GB), dense 1.73B hybrid, thinking model (reasoning on by default).

## Chain executed today (operator green light)

1. Onboarding (previous day): download + GGUF magic verified; registry entry
   lfm3-1.7b (port 8120). Zero box time.
2. Rebuild: the Flint worktree (F:\llvb_flint junction -> llama.cpp-flint-wt)
   rebuilt with the staged LFM3 merge (474 paths). Build 11833 (was 11832),
   llama-server.exe + llama-cli.exe produced. lfm3.cpp is globbed by
   src/CMakeLists.txt:9 into the llama target with UNITY_BUILD batch 16, so
   there is no standalone lfm3.cpp.obj - it compiles inside a unity_N batch
   (src/llama.vcxproj lists it). The script's trailing
   "BUILD-SCRIPT-FAILED" line is false: llama-server --version prints
   "0.7.0-dev (build 11833, commit b2a60bb67)" and exits nonzero.
   Merge committed: 0882f7c09 on mod/flint-support (Work-Note: lfm3-wave (L-1)).
   The DAAVFX overlay survived (EXP-1 bridge commit b2a60bb67 is HEAD~1).

## Axis B - quality harness (same v2 taskset as every other model)

7/12 tasks (58.3%), 20/28 checks (71.4%). Raw:
scripts\daavfx\quality-harness\results\responses-lfm3-1.7b-Q4_0-20261028-172514.jsonl
and score-lfm3-1.7b-Q4_0-20261028-172514.jsonl.

Ledger context (recomputed from the score rows, all same tree):
- qwen3.5-4b baseline: 8/12 (23/28) - the champion reference
- LFM2.5-8B configs: 9/9/8 of 12 - but those are 8B models
- flint-Q2_K_XL 9/12 (older taskset, 22 checks); flint-Q3_K_XL 5/12
- Failure class: thinking-budget artifacts, not knowledge holes.
  tool-call-weather lost json_valid_first_block although the reply WAS the
  correct JSON ({"tool":"get_weather","arguments":{"city":"Tokyo"}}) - the
  scorer's first-block regex hit reasoning text first. code-fix-offbyone
  emitted no verbatim fix line; code-fix-compare, exact-word-count and
  injection-ignore failed clean.

## E0 speed receipts (GTX 1650, driver 610.88, SM 1200 MHz / mem 6000 MHz,
94% util, 22.31 W sampled under load; full Vulkan ngl 99, ctx 8192, threads 6)

- Decode: 56.18-58.34 t/s across every task; sustained 256-token runs
  57.18 / 57.47 / 57.32 / 56.58; median ~57.5 t/s (17.1-17.8 ms/token).
  Model loads in ~11 s.
- Prompt eval: 57.8-92.3 t/s on 25-42-token prompts; 102.1 t/s on the
  3018-token prompt (9.79 ms/token).
- vs 18.9 t/s (LFM2.5-8B split, the standing speed record): ~3x.
- vs qwen3.5-4b GPU 10.2 t/s: ~5.6x.
- Caveat: one session, one model instance. The quiet-box re-run (which also
  re-measures the +40% async claim now flagged inside its noise band)
  should repeat this.

## Axis A - MT5 agent bench (v1.3 driver)

Protocol probes first (scoreboard rule: read the transcript before burning
30 turns):
- JSON-RPC path (6-turn leash): 0 actions. Emits <tool_call> XML envelopes
  with invented names (method "list", tools "backtest"/"run"/"execute"),
  repeats the same invented names, and burns the full 1600-token budget on
  turn 4 with empty content. runs\lfm3-1.7b-Q4_0_probe.
- Native OpenAI tools path (-UseOpenAITools): first crashed every turn on a
  driver bug (fixed below); after the fix, an 8-turn leash gave 12 actions,
  0 refusals, a real trajectory: get_workspace_info -> find/list/glob ->
  get_expert_advisor_parameters + read_file -> tester_run_backtest ->
  tester_get_status. runs\lfm3-1.7b-Q4_0_probe_nt32k.
- Full 30-turn run (32k ctx): HELD by the operator at turn 19. Banked:
  discovery, found Experts\V4_DAAVILEFX_17.23.ex5 (7134 bytes), read_file;
  a 400 context overflow at turn 13 (the 67-tool catalog plus results
  exceeded 32k) after which it degraded into re-discovery loops. No FINAL
  REPORT, no exact-value transcription. runs\lfm3-1.7b-Q4_0.

Driver fix that unblocked the native path (bench_driver.ps1 v1.3.1, this
lane's file, zero GPU): ExtractActions returned a bare List[object];
PowerShell unrolls pipeline output, an empty list vanished, $actions became
$null, and every native turn died on $actions.Add with "You cannot call a
method on a null-valued expression". Fixed with Write-Output -NoEnumerate
plus a null guard at the call site. Parse-checked.

## Verdict (dual-axis keep/drop)

- Speed lane: NEW RECORD. 57.5 t/s decode at 0.98 GB full-VRAM is 3x the
  standing 18.9 t/s split config and ~5.6x the qwen GPU number, with quality
  one task behind the 4B baseline. Keep as the speed-lane champion candidate.
- MT5 agent lane: worker-tier at best. The protocol works through native
  tool calls and it can launch the real backtest, but it does not hold the
  task thread across a context overflow and never produced a final report.
  Not a qwen3.5-4b replacement for agentic MT5 work.
- Open: a 49k-ctx (or lower ResultCap) re-run is the one experiment that
  could move Axis A from worker-tier to a complete-tier verdict. Not run.

## Receipts

- quality: scripts\daavfx\quality-harness\results\ (responses + score jsonl)
- speed: same tree, results\llm-lfm3-server.log (slot print_timing lines)
- bench: llm_bench\runs\lfm3-1.7b-Q4_0 and its _probe/_probe_nt/_probe_nt2/
  _probe_nt32k siblings
- build: F:\llvb_flint\build_flint\bin\Release\ (build 11833); merge commit
  0882f7c09 on mod/flint-support
