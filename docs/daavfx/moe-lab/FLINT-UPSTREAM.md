# FLINT-UPSTREAM - merge, build, and bench the Flint model

Date: 2026-10-22
Status: merge staged, no build, no download, no inference. Nothing in this
document has been executed on the Flint path yet.

## 1. Position

Flint is an upstream llama.cpp architecture, not a separate engine. The goal is
ONE modded llama.cpp (`llama.cpp-abelianIUT`) that contains the abeliant overlay
and Flint support. Do not keep a second Flint-only clone as the product.

- Fork: `..\llama.cpp-abelianIUT` (branch `daavfx`)
- Flint worktree: `..\llama.cpp-flint-wt` (branch `mod/flint-support`)
- Upstream mirror: `..\llama.cpp-original` (master `36cbf41`)
- Merge: `git merge --no-commit --no-ff upstream/master`, zero conflicts, still
  uncommitted. The merge was not applied to the main tree; its overlay and docs
  are uncommitted there.
- Merge-base gap: 155 commits, 469 files, +44327/-16534.

The merge is deliberately staged for review. No commit or push happens without
the operator's explicit approval.

## 2. What upstream added

| Area | Files |
|---|---|
| Architecture enum and tensors | `src/llama-arch.cpp`, `src/llama-arch.h` |
| Graph build | `src/llama-graph.cpp`, `src/llama-graph.h` |
| Model loader | `src/llama-model.cpp`, `src/llama-model.h` |
| Model implementation | `src/models/flint.cpp` (new) |
| Vocab and special tokens | `src/llama-vocab.cpp`, `src/llama-vocab.h` |
| Jinja fix | commit `9febe63d5`, PR #30929 |
| Architecture PR | #30928 |

The merge also carries the upstream SLRU rewrite of `src/llama-moe-cache.cpp`.
That rewrite replaced the old ring-eviction idea. Our worktree keeps the SLRU
and adds only telemetry; the rejected `DAAVFX_MOE_RING_EVICT` path must not be
restored.

## 3. Model facts

| Property | Value |
|---|---|
| Family | Recursive Flint |
| Total / active | 39.8B / ~2.5B |
| Layers | 49 (2 dense + 47 MoE) |
| Routed experts | 256 per MoE layer |
| Shared experts | 1 per MoE layer |
| Experts per token | 6 routed + 1 shared |
| Attention | 35 sliding-window (513) + 14 full |
| Heads | 32 query / 4 KV, head dim 128 |
| Vocab | 150,144 |
| Context | 262,144 |
| License | Apache-2.0 |
| Terminal-Bench 2.1 | 54.9% |
| SWE-bench Pro v2 | 89.7% |
| SWE-bench Verified | 74.2% |

## 4. Quant table

Unsloth Dynamic 3.0:

| Quant | Size |
|---|---|
| IQ1_M | 11.4 GB |
| IQ2_XXS | 11.9 GB |
| Q2_K_XL | 13.6 GB |
| IQ3_XXS | 14.5 GB |
| Q3_K_XL | 18.5 GB |
| Q4_K_XL | 25.1 GB |
| Q5 | 29.9 GB |
| Q6 | 36.3 GB |
| Q8 | 42.3 GB |
| BF16 | 79.6 GB |

Tere Labs:

| Quant | Size |
|---|---|
| IQ4_XS | 22.24 GB |
| Q4_K_M | 25.02 GB |
| Q5_K_M | 28.98 GB |

Plan: Q2_K_XL is the smoke quant. Q3_K_XL is the first real candidate. IQ4_XS
is the quality ceiling test. Q4 and larger do not fit the 31.4 GB box with a
safe page-file margin.

## 5. Local hardware and the wall

- Ryzen 5 5600G, 2x3600 DDR4, 31.4 GB RAM, free 11.6-13.5 GB at planning time.
- GTX 1650 4 GB, 3385 MiB free; Vega 7 iGPU exposes 16328 MiB GTT.
- Expected Flint speed: 5-10 t/s.
- Community 7800XT 16 GB + DDR5 + Vulkan, `-ncmoe 24 -fa 1`: pp 1886 / tg 49.
- Measured LFM split (`-ngl 99 -ncmoe 24`, t6): pp 111.8 / tg 18.9 at 1548 MiB.
- The 4 GB card cannot hold a 13.6-25 GB model. The only local lane is
  CPU/RAM experts with a partial Vulkan offload, or pure CPU.
- `--moe-cache-mib` is real upstream: `common/arg.cpp` L2781/L2787 ->
  `params.moe_cache_size`; `common/common.h` has `size_t moe_cache_size`.
- Do not default the cache to 4096 MiB on a 4 GB card. Start at 512-1024 MiB
  and sweep. The cache competes with the KV cache and the offloaded layers.
- `GGML_VK_ASYNC_USE_TRANSFER_QUEUE=1` was the one measured win on LFM: it
  overlapped miss uploads with compute and moved diverse-prompt generation from
  12.0 to 16.0-17.5 t/s with quality intact.

## 6. Build pipeline

Script: `scripts/daavfx/build-flint-llama.ps1` (exists in both trees, not yet run).

What it does:

1. Finds VS 2022 with C++ tools through `vswhere`.
2. Creates junction `F:\llvb_flint` -> worktree, for MAX_PATH.
3. Configures `build_flint` with `Visual Studio 17 2022`, x64,
   `GGML_NATIVE=ON`, `BUILD_SHARED_LIBS=OFF`.
4. Adds `GGML_VULKAN=ON` unless `-CpuOnly`.
5. Builds `llama-server` and `llama-cli` in Release.
6. Verifies `build_flint\bin\Release\llama-server.exe` and prints `--version`.

Commands (do not run until allowed):

```powershell
.\scripts\daavfx\build-flint-llama.ps1
.\scripts\daavfx\build-flint-llama.ps1 -CpuOnly
.\scripts\daavfx\build-flint-llama.ps1 -Clean
```

Expected output path:
`..\llama.cpp-flint-wt\build_flint\bin\Release\llama-server.exe`.

The current `..\llama.cpp-abelianIUT\build_vulkan_bin\llama-server.exe` is
0.7.0-dev build 11671, commit `43011a618`, 251 architectures, no `flint`.
It cannot load Flint.

## 7. Download

Script: `scripts/daavfx/fetch-flint-gguf.ps1`.

```powershell
.\scripts\daavfx\fetch-flint-gguf.ps1 -Quant Q2_K_XL -List
.\scripts\daavfx\fetch-flint-gguf.ps1 -Quant Q2_K_XL
.\scripts\daavfx\fetch-flint-gguf.ps1 -Quant Q3_K_XL
```

Default destination:
`...\local_llm\GGUF\llm-collection\21-flint\`.

Split files: the selector now downloads every shard of one split quant. If
the quant tag matches unrelated files, it refuses and lists them; pass
`-File <rfilename>` to choose one exact file. There is no string-length sort.

## 8. Run configuration

First load test (no benchmark):

```powershell
$env:GGML_VK_ASYNC_USE_TRANSFER_QUEUE = '1'
.\build_flint\bin\Release\llama-server.exe `
  -m ...\21-flint\Flint-Q2_K_XL.gguf `
  -ngl 99 -ncmoe 24 -t 6 -c 8192 --jinja `
  --moe-cache-mib 1024 --host 127.0.0.1 --port 8083
```

If the loader rejects or OOMs, fall back in this order:

1. `--moe-cache-mib 512`.
2. `-ncmoe 28` or `-ncmoe 32` (more experts on CPU).
3. `-ngl 0` pure CPU with `-t 6`.
4. `-c 4096` if KV allocation is the failure.

Do not kill the operator's app server on port 8080. Use 8083 or a free port.

## 9. Benchmark pipeline

Two layers:

1. Quality gate: `scripts/daavfx/quality-harness/run-harness.ps1` against an
   already-running Flint server. 12 deterministic tasks, score.py judge.
2. MT5 gate: `scripts/daavfx/run-flint-bench.ps1` wraps
   `llm_bench\tools\bench_driver.ps1` with Flint sampling and the native OpenAI
   tool catalog. The driver starts and stops its own server.

Flint sampling, on-spec:

- temperature 1.0
- top_p 0.95
- top_k 20
- repeat penalty 1.0

Optional comparability run at temperature 0.4. Record the sampling in every
result row. Do not mix sampling regimes in one scoreboard.

The wrapper defaults are `MoeCacheMib = 1024`, `Ctx = 8192`, and
`MaxTokens = 4096`, chosen for the 4 GB card. Override only after a successful
load test.

The MT5 task is the ecosystem's real acceptance test:

- Expert `V4_DAAVILEFX_17.23.ex5`
- Symbol `XAUUSD_n1`, M1, 2004.01.01 to 2009.01.01
- Model 4 real ticks, deposit 100000.00 USD, leverage 500
- Setfile `MUSETST-R4.2_x06.2_ctCRPO.set`
- Ground truth run `7698597314023469097`: 1051 trades, profit +2063.16,
  PF 1.0806, DD 21343.48

Tolerances: trades exact, profit +/-0.01, PF +/-0.001, DD +/-0.1.

## 10. What is still missing

- No compile of the merged tree. The moe-cache telemetry uses `fprintf`,
  `getenv`, and `atoi`; `<cstdio>` and `<cstdlib>` were added to both
  `src/llama-moe-cache.cpp` copies, but no compile has confirmed it.
- No Flint GGUF downloaded.
- No load test, no quality score, no MT5 score.
- The fetch selector and wrapper defaults were reviewed and parse-checked; no
  runtime evidence yet.
- The worktree merge is uncommitted.
- The official docs are in the main tree. The four Flint scripts exist in both
  the main tree and the worktree; the worktree builds `build_flint`.
- The build script now validates an existing `F:\llvb_flint` junction target
  before building against it (stale-junction guard).
