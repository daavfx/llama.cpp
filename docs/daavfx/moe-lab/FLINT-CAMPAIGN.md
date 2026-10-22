# FLINT-CAMPAIGN - next-model plan for the MoE lab

Date: 2026-10-22
Status: PLAN ONLY. No build, download, inference, or benchmark has run.
Gated on the operator freeing the PC.

## 1. Why Flint is the next test

Flint is a 39.8B total / ~2.5B active MoE with 256 routed experts per layer
(6 routed + 1 shared per token). That is a much wider expert space than
LFM2.5's 32 experts, and it is the exact shape the lab's thesis needs to test:

- LFM taught us that a load-balanced router has no cold tail, so blind expert
  amputation dies at a capacity cliff.
- Flint asks whether 256 experts create a real cold tail, or whether the same
  balance law holds at 8x the width.
- Flint also has enough public quality (Terminal-Bench, SWE-bench) that a
  small local quant can be judged against a known reference, not only against
  our 12-task harness.

The lab does not assume the LFM answer transfers. Every claim below is a
hypothesis with a cheap falsifier.

## 2. Hypotheses and falsifiers

| ID | Hypothesis | Cheap falsifier |
|---|---|---|
| H1 | Q3_K_XL runs at 5-10 t/s on the split (CPU experts + 4 GB Vulkan) | One 128-token generation; if under 2 t/s, the lane is not usable |
| H2 | The 4 GB card cannot hold even Q2_K_XL fully; split is mandatory | Load Q2 with `-ngl 99 -ncmoe 0`; OOM confirms |
| H3 | `--moe-cache-mib` helps only when the working set fits; a 4 GB card needs 512-1024 MiB, not 4096 | Load with 4096; OOM or WDDM paging confirms 4096 is not viable and the 1024 default is the safe start |
| H4 | `GGML_VK_ASYNC_USE_TRANSFER_QUEUE=1` still helps on Flint | A/B one prompt with and without; keep only if generation rises without quality loss |
| H5 | Flint's router is load-balanced like LFM's | Router histogram over 200+ prompts; if selection share is flat, no cold tail |
| H6 | Q2 is a quality cliff, Q3 is usable, IQ4 is the ceiling | 12-task harness plus MT5; reject any quant that fails the MT5 ground truth |
| H7 | Flint can drive the MT5 MCP task | Full 30-turn run; any wrong `run_backtest` args or missing completion fails |

## 3. Phase plan

### Phase 0 - build and load (gated)

1. Build the merged worktree with `build-flint-llama.ps1`.
2. Verify `llama-server --version` lists `flint`.
3. Download only Q2_K_XL first; the fetch selector handles split shards.
4. Load test on port 8083 with `-c 8192`, `-t 6`, `-ncmoe 24`,
   `--moe-cache-mib 1024`, `GGML_VK_ASYNC_USE_TRANSFER_QUEUE=1`.
5. Record load time, peak RAM, peak VRAM, and the exact command.

Stop if the model does not load or if the box needs a page-file increase that
the operator has not approved.

### Phase 1 - quality and MT5 baseline

1. Quality harness, 12 tasks, three runs at the on-spec sampling.
2. MT5 task through `run-flint-bench.ps1`, full 30-turn cap, 4096 max
   tokens (raise only after a load test).
3. Compare with the existing qwen3.5-4b full card and the sealed MT5 truth.
4. Record every tool call, turn, reasoning length, and failure class.

Acceptance for Phase 1:

- At least one full MT5 completion, with the sealed values within tolerance.
- Quality harness at or above the best small-model card, or a clear diagnosis
  of why Flint fails where the small model passes.

### Phase 2 - quant ladder

Run Q3_K_XL, then IQ4_XS if RAM allows. Keep Q2 as the speed reference.

For each quant record:

- model size, load time, peak RAM, peak VRAM
- pp512, tg128, and the MT5 wall clock
- quality score and MT5 verdict
- cache hit rate if telemetry is enabled

Eliminate any quant that fails MT5, regardless of speed.

### Phase 3 - router and cache science

Only after a quant passes Phase 1:

1. Run the router histogram logger (`DAAVFX_ROUTER_LOG`) over the harness plus
   agent prompts.
2. Run the cache profiler (`DAAVFX_MOE_CACHE_STATS=1`) over the same prompts.
3. Answer: is there a cold tail, or is Flint balanced like LFM?
4. If there is a cold tail, quantify the mass gap before proposing any cut.

No surgery in this phase. Data first.

### Phase 4 - surgery, only if Phase 3 earns it

The LFM destruction budget applies:

- F1 amputation only if a cold tail exists and the mass gap is large.
- F2 ghost merge only if clustering shows a real multi-modal group.
- Every mutant must pass the 12-task harness and the MT5 task.
- Keep the quantized mutant as the record; delete f16 intermediates.

If Flint is balanced, close the surgery lane immediately. The LFM result says
blind cuts are a capacity cliff, not free compression.

### Phase 5 - Track B trigger

Track B starts only when one Flint quant passes MT5 and beats or matches the
best small model on quality. Use that model as the teacher; do not distill a
model that has not passed the task.

## 4. Metrics ledger

Every row must carry:

- model, quant, file size, SHA or HF revision
- server binary commit and build number
- command line, context, `-ngl`, `-ncmoe`, cache MiB, threads, env flags
- sampling (temp, top_p, top_k, repeat penalty)
- pp512, tg128, MT5 wall clock
- peak RAM, peak VRAM, CPU percent
- quality score, tasks passed, failure classes
- MT5 trades, profit, PF, DD, verdict
- router histogram artifact and cache profile artifact when available

No row without a command line and a binary identity.

## 5. Stop rules

- Stop the quant ladder if two consecutive quants fail MT5.
- Stop the surgery lane if the router histogram is flat.
- Stop the speed lane if the best quant is under 2 t/s and quality is not
  clearly above the small model.
- Stop and report if the box needs more RAM or page file than the operator
  approved.
- Never leave a server or python process running after a measurement.

## 6. Artifacts

- Build: `build_flint\bin\Release\llama-server.exe`
- Models: `...\local_llm\GGUF\llm-collection\21-flint\`
- Quality: `scripts\daavfx\quality-harness\results\`
- MT5: `llm_bench\runs\`
- Router hist: `scripts\daavfx\results\flint\router-*.csv`
- Cache stats: `scripts\daavfx\results\flint\cache-*.log`
- Scoreboard: `docs\daavfx\moe-lab\FLINT-RESULTS.md` (created only after data)

## 7. Open decisions for the operator

1. First quant: Q2_K_XL smoke or Q3_K_XL directly.
2. Context: 8192 for the first pass, or 4096 to protect RAM.
3. Whether a page-file increase is allowed if Q3 needs it.
4. Whether the MT5 pass is mandatory before any quality-only score is reported.
5. Whether Track B starts from Flint or from the current small-model winner.
