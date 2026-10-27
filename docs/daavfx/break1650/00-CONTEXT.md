# 00-CONTEXT - hardware, software stack, lanes, correlation

## The box (all measured, 2026-10-22/24)

| Component | Identity | Measured state |
|---|---|---|
| CPU | AMD Ryzen 5 5600G, 6c/12t | sustains 10.2 GB/s effective on the MoE CPU-split decode path; 18.32 t/s DSpark estimate |
| dGPU | NVIDIA GeForce GTX 1650, TU117, 4 GB, PCIe Gen3 x16, driver 610.352, Vulkan 1.4 | E0: PCIe copy 13.3/13.1 GB/s, FP16 FMA 3179 GFLOPS naive (~53% of ~6 TFLOP theoretical), INT32 MAD 1583 GIOPS, host-visible in-shader read **1.4 GB/s**, dispatch 178 ns, **shaderFloat16 = 1**, power limit 90 W, idle state P8 = 300/405 MHz (see P8 note below) |
| iGPU | AMD Radeon Graphics (Vega 7, 5600G), Vulkan API 1.2 driver 2.0.0 | E0: copy 15.5/15.0 GB/s, host-visible in-shader read **4.8 GB/s** (3.4x the dGPU), FP16 FMA 1436 GFLOPS (driver's fp16 shader path weak: some fp16 pipelines rejected VK_ERROR_INVALID_SHADER_NV), INT32 167 GIOPS, dispatch **50 ns** |
| RAM | 32 GB DDR4, mixed A-DATA + Kingston | **configured 2400 MT/s** (Win32_PhysicalMemory) - the campaign docs assumed 3600-class bandwidth; never changed (operator declined BIOS changes) |
| Disk C: | ADATA LEGEND 700 NVMe 512 GB, **35.6 GB free** | 4K random O_DIRECT ~0.28 ms/op; buffered 4K ~0.01 ms |
| Disk F: | Seagate ST3000NM0053 3 TB **SATA HDD 7200rpm**, 1258 GB free, **holds all model GGUFs** | 4K random QD1 ~**12 ms/op**; 1M sequential ~16-17 ms; 0.06-0.2 GB/s effective |
| Disk E: | 250 GB WD HDD (231 GB) | not benchmarked |
| Disk H: | JMicron USB 1 TB (471 GB) | not benchmarked; bus-type USB |

P8 note: the card idles at 300/405 MHz (P8) and ramps under sustained load.
Several historical dGPU estimates (DSpark "7.2 t/s") were taken while the
card had no reason to leave P8. The program treats clock state as a
measurement variable: lock-or-record before every number. The stamping rule
now also carries DRIVER state (post-G-1) on every GPU number.

## The claim this program has never tested (corrected 2026-10-26)

"No tensor cores (sm_75)" was a datasheet note this program treated as
settled. It is UNVERIFIED, and the opportunity it hid is live:

- The fork's Vulkan backend classifies a device as pre-Turing **iff it lacks
  `VK_KHR_cooperative_matrix`** (`ggml/src/ggml-vulkan.cpp:96-108`) - i.e. the
  shipped code expects Turing+ cards to HAVE coopmat.
- The fork ships the coopmat shader family now: `coopmat.comp`,
  `coopmat2.comp`, `coopmat2_decode_vector.comp` - a tensor-class matmul path.
- The E0 probe (`shared/daavfx-vk-probe/daavfx_vk_probe.c:157`) creates its
  device with `enabledExtensionCount = 1` and never enumerates device
  extensions - so nobody on this box has ever asked the driver whether
  `VK_KHR_cooperative_matrix` is exposed on 610.352 / Vulkan 1.4.
- Settling it is experiment G-3a (a ~20-line probe addition) and it gates the
  whole dense-2x lane. If coopmat is absent, the honest conclusion is that
  TU117's tensor-class path is software-only; if present, the card was never
  the gaming part the datasheet claimed.

## Software stack

| Piece | State |
|---|---|
| llama.cpp fork `llama.cpp-abelianIUT` (branch `daavfx` @ 43011a618) | main tree; binary `build_vulkan_bin\llama-server.exe` 0.7.0-dev build 11671 (pre-Flint) |
| Worktree `llama.cpp-flint-wt` (branch `mod/flint-support`) | upstream master 36cbf41 merged (Flint arch) + all DaavFX overlay, committed; binary `build_flint\bin\Release\llama-server.exe` **build 11832** (current test binary; loads both LFM2.5 and Flint) |
| DaavFX overlay in fork src/ | `daavfx_dspark_bridge.cpp` (router histogram logger, env `DAAVFX_ROUTER_LOG`, widened 2026-10-24 to 48 layers x 256 experts with a loud out-of-bounds guard and a stored-probs-stride fix), `daavfx_per_layer_hooks.c/h`, `daavfx_theater_dispatch.c/h`, `llama-moe-cache.cpp` (reuse telemetry `DAAVFX_MOE_CACHE_STATS` + `--moe-cache-mib`) |
| Vulkan layers (ours, in `shared\daavfx-vk-layer\`) | `VkLayer_daavfx` (queue-warmup: pays the first-submit penalty during load; spawned-thread design) and `daavfx_vk_shard_layer` (splits large submits: a documented Turing fault `nvoglv64+0xE90A8C`). Loader trace (2026-10-24) additionally showed every app auto-stacks `VK_LAYER_AMD_switchable_graphics` (amdvlk64) + `VK_LAYER_OBS_HOOK` (OBS capture) + `VK_LAYER_NV_present/NV_optimus` into every device chain; the first two have env kill switches (`DISABLE_LAYER_AMD_SWITCHABLE_GRAPHICS_1=1`, `DISABLE_VULKAN_OBS_CAPTURE=1`) which the probe uses during measurement |
| Bench harness `llm_bench\` (infra lane) | `tools\bench_driver.ps1` v1.3: spawns llama-server on 8077, drives a 30-turn MT5 MCP agent task, captures reasoning + native tool calls, writes metrics.json; sealed ground truth (1051 trades / profit +2063.16 / PF 1.0806 / DD 21343.48; tolerances trades exact, profit +/-0.01, PF +/-0.001, DD +/-0.1) never enters prompts; WMI-detached launchers in `tools\launchers\`; health-wait 600 s |
| Quality harness `scripts\daavfx\quality-harness\` | 12 deterministic-check tasks (tool-call JSON, code fix, schema, injection, exact-format); temperature comes from `taskset.json` (default 0.2); `score.py` scorer; taskset variants for temperature A/B exist (`taskset-temp0.json`, `taskset-temp10.json`) |
| Models on disk (F:) | LFM2.5-8B-A1B Q4_K_M (4.9 GB, the speed reference), Flint `flint-UD-Q2_K_XL.gguf` 12.63 GB + `flint-UD-Q3_K_XL.gguf` 17.22 GB, Qwen2.5/3.5 family, granite 8B, K2 (dropped), + ~20 more; full collection ~30 models |

## Lanes and correlation (who is cooking what, 2026-10-24)

| Lane | Agent | Scope | Status |
|---|---|---|---|
| Infra/bench/audit (this program's author) | opencode `flint-bench-harness-2026-10-22` | fork `src\`, build/fetch/bench scripts, `llm_bench\`, scorecards, E0 probe, audits | this plan |
| Harness lane (was a coder agent, **now operator-handled**) | operator | `daavile-harness` repo: Lane-A eval adapter (`packages\eval\eval-adapter\`, cleared re-audit 10/10 specs; idempotent ingest keyed by canonical model; leaderboard mirror to `~/.dsh/memory/evals/`), `launch-llm.ps1` runtime-verified (H1), Harness^2 template spec (H0), OptChat end-to-end proof pending (H3 - needs a long real session) | correlated: the dual-axis leaderboard (quality harness score + MT5 agent score per model = keep/drop rule) is the consumer of this program's benchmark outputs |
| moe-lab lane | archived coder | `docs\daavfx\moe-lab\` (LFM2.5 campaign: production configs, falsification ledger, X-ray/surgery kit) | closed; its instruments (router logger, cache profiler, surgeon, quality judge) are this program's tools |
| Quantum app | operator + agents | Tauri app `APPS\quantum-dashboard-fx` (Agent/IDE/Quantum realms); agent chat de-mocked (commit `c1028e8`); its own llama-server uses port 8080 (NEVER kill); premium MCP 3141; MT5 MCP terminal 22302 (must be up for agent benches; 401-unauth = healthy) + metaeditor 22368 (down, tolerated) | correlated: the app is the operator's daily surface; any GPU experiment must not disturb it |
| RYIUK archive | operator's own research | `local_llm\GGUF\RYIUK` (8,933 files): PRIMAL/provenance system, candle-kernels-patched (CUDA MoE kernels vendored, WMMA stubbed for sm_75), primal_bench_vk (hostile-float Vulkan probes, bit-exact determinism x100), 235 research md files | audited 2026-10-24 by 4 sub-agents; trust ledger in `02-TRUST-LEDGER.md`; the gem is `kimi_k3_aproach.md` (PROJECT KITTYHAWK) which converges with this plan |

## The operator's standing directives (verbatim intent)

1. "ask me every time you run llama or something local" - per-run green light.
2. "finish your shit" - deliver, don't lecture; no BIOS/hardware directives to
   the operator (the 2400-RAM and P8 facts are recorded, not assigned).
3. "I don't want to copy what's already created... I want to break the GTX
   1650 and find out wtf boosts this shit" - the program must be original;
   external designs (Strata, gpu-unlock) are references, not the plan.
4. "we have LLMs we can do the loader as complex as possible to win speed" -
   the loader may use model-informed, trace-informed, speculative strategies
   (see `04-LOADER-DEEP-DIVE.md` level 5).
5. The thinking-token observation: models emit long `reasoning_content`
   before the answer; on this box every thinking token is a full forward
   pass - the operator flagged this as a core reinvention target (P1).
