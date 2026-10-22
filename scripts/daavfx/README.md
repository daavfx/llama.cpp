# daavfx scripts - campaign tooling

Status: LFM campaign closed 2026-10-21; its scripts and surgeon were used and
validated as recorded in INFLIGHT.md. The four Flint scripts were authored
2026-10-22 and parse-checked, but NOT run: no build, download, or inference.
Nothing here runs unless the operator frees the PC.

Author: agent ID `lfm25-gtx1650-campaign`. Docs: docs/daavfx/README.md (index),
docs/daavfx/REPO-MAP.md (ours vs upstream), docs/daavfx/FLINT-UPSTREAM.md
(Flint pipeline), docs/daavfx/moe-lab/ (LFM campaign + Flint campaign plan).
Ledger: INFLIGHT.md at the fork root.

## What lives here

| File | Purpose | Runs when |
|---|---|---|
| phase1-bench-matrix.ps1 | Phase 1 base-truth rows (CPU ref, -ncmoe split, full-offload wall, FA A/B) with VRAM sampling and a run manifest | go signal only |
| gguf-surgeon.py | FOUNDRY F1/F2 tool: lfm2_moe expert amputation (raw block surgery, zero deps) and ghost-expert merging (dequant path); inspect + roundtrip-test modes for trust | inspect/roundtrip can run anytime (file reads only); surgery outputs validated at go |
| quality-harness/ | FOUNDRY's destruction-budget judge: 12 deterministic agentic tasks, server runner, scorer | when a llama-server is up |
| build-flint-llama.ps1 | Build the merged Flint worktree with MSVC + Vulkan (or `-CpuOnly`), junction `F:\llvb_flint`, output `build_flint\bin\Release` | after the operator frees the PC |
| fetch-flint-gguf.ps1 | Resolve a quant from `unsloth/flint-GGUF`, download all split shards or one `-File` | after the build, one quant at a time |
| run-flint-bench.ps1 | MT5 agent bench for one Flint quant; Flint sampling, `-UseOpenAITools` | after a Flint server loads |
| flint-quant-sweep.ps1 | Quality harness plus MT5 bench over a quant list; one summary JSON | after the load test |

## Quick usage

Phase 1 bench (after "coder done, gemma stopped, go"):

    powershell -File phase1-bench-matrix.ps1 -Go
    # optional: -Bench <path> -Model <path> -OutDir <dir> -Priority BelowNormal

Surgeon trust check (safe, read-only + temp write):

    python gguf-surgeon.py inspect --gguf <model.gguf>
    python gguf-surgeon.py roundtrip-test --gguf <model.gguf> --out %TEMP%\rt.gguf

F1 amputation mutant (the foundry's first surgery):

    python gguf-surgeon.py amputate --gguf LFM2.5-8B-A1B-Q4_K_M.gguf --out mutant-K24.gguf --drop 6,12,18,24 --clamp-used

F2 merge mutant:

    python gguf-surgeon.py merge --gguf <model.gguf> --out mutant-ghosts.gguf --groups "[[3,17],[8,21]]"

Quality harness (with a llama-server already serving the model):

    powershell -File quality-harness\run-harness.ps1 -ServerUrl http://127.0.0.1:8083 -Tag baseline-q4km
    python quality-harness\score.py --responses quality-harness\responses.jsonl

Flint pipeline (not run yet; read FLINT-UPSTREAM.md first):

    powershell -File build-flint-llama.ps1
    powershell -File fetch-flint-gguf.ps1 -Quant Q2_K_XL -List
    powershell -File fetch-flint-gguf.ps1 -Quant Q2_K_XL
    powershell -File run-flint-bench.ps1 -Quant Q2_K_XL
    powershell -File flint-quant-sweep.ps1 -Quants Q2_K_XL,Q3_K_XL -SkipQuality

## Rules

- Do not build, download, or bench Flint until the operator frees the PC.
- Never bench while the human coder's sweep is active. The bench script
  refuses to run without -Go and aborts if port 8082 is still listening.
- Surgery always writes to a NEW file. The production GGUF is never modified.
- Every mutant gets: roundtrip-test clean, inspect clean, harness score row.
  Ledger discipline per ecosystem rules (INFLIGHT.md, receipts).
