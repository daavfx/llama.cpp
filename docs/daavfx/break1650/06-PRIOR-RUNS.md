# 06-PRIOR-RUNS - digest of past campaigns, benches, and archive findings

For auditor context: what was already run, what it learned, and which of it
is still live equipment. Nothing here is a plan; it is the receipt pile.

## A. The LFM2.5-8B-A1B moe-lab campaign (2026-10-21) - `docs\daavfx\moe-lab\`

**The two production configs (measured, reusable):**

| Mode | Config | Speed | CPU | Quality |
|---|---|---|---|---|
| MAX SPEED | `-ngl 99 -ncmoe 24 -t 6` | **18.9 t/s** tg, 111.8 pp | busy | 8/12 |
| ZERO-CPU | same + `--moe-cache-mib 1536` + `GGML_VK_ASYNC_USE_TRANSFER_QUEUE=1` | 14-17.5 t/s | ~0% | same |
| RAM-SAVING | guided K=28 (mass-ranked per layer) | 18.9 t/s | busy | **9/12**, ~550 MB less RAM |

Launcher (WMI-detached, verified): `launch-llm.ps1 -Mode split|zerocpu|Stop`.

**The thesis established (still governing):**
- LFM2.5's router is load-balanced BY DESIGN (aux-loss-free equalizer,
  `exp_probs_b`): selection share of any index half = 50.7% - **no cold tail
  to harvest**. Expert surgery is dead for this model, permanently.
- The quality cliff: K=28 -> 9/12, K=24 -> 8/12, K=16 -> 3/12, blind K=16
  -> 1/12. Guided surgery is worth +17 points at K=16 but cannot beat geometry.
- Bandwidth map: DDR4 28-30 GB/s > PCIe 11.5 theoretical / 3-8 real; the CPU
  split sustains 10.2 GB/s effective (compute-mixed at 36% of DDR4 peak).
- Spec-decode is structurally negative on the CPU-expert split: verifying k
  draft tokens pulls up to 16 experts/layer instead of 4 - bytes per accepted
  token roughly double. Measured 1.9-8.4 t/s.
- The one accepted win: `GGML_VK_ASYNC_USE_TRANSFER_QUEUE=1` (+40%, zero code).

## B. The MT5 agent bench (`llm_bench\`) - all models, sealed ground truth

Reference: Expert `V4_DAAVILEFX_17.23.ex5`, `XAUUSD_n1`, M1, 2004-01-01 to
2009-01-01, Model 4 real ticks, deposit 100000, leverage 500, setfile
`MUSETST-R4.2_x06.2_ctCRPO.set`. Sealed run `7698597314023469097`: 1051
trades, profit +2063.16, PF 1.0806, DD 21343.48.

| Model | Result | Card file |
|---|---|---|
| qwen3.5-4b (CPU 8k, v1.2 harness) | **COMPLETE** - 22 turns, 29 actions, exact sealed values | `scores\qwen3.5-4b-q4km.json` |
| qwen3.5-4b (GPU assist 16k) | INCOMPLETE loop on hallucinated tool names, 10.2 t/s effective | `scores\qwen3.5-4b_v12_gpu.json` |
| gemma4-E4B (GPU) | USABLE honest-failure card, 26 turns / 25 actions | `scores\gemma4-e4b_v12_gpu.json` |
| granite-4.2-8b (v13b) | first protocol-CLEAN full run; 30 turns pure exploration, never reached a real backtest | `scores\granite-4.2-8b_v13.json` |
| K2-Horizon-7B (v1 + v13) | **FAILED-PROTOCOL** - 0 parseable actions in 60 turns | `scores\K2-Horizon-7b_v13.json` |
| LFM2.5-8B-A1B | INCONCLUSIVE - the old "refusals" were a v1.2 harness artifact (reasoning dropped, 1600-tok cap) | `scores\LFM2.5-8B-A1B_v12.json` |
| Flint Q2_K_XL (v13, -c 8192) | config failure: catalog+dialogue 14.5k tokens > 8192 ctx, rejected pre-inference | 32k rerun pending (X4) |

Environment requirement learned: the bench MT5 terminal must be up first -
22302 answering 401-unauth = healthy (terminal64 at
`F:\trading_terminals\mt5-3\terminal64.exe`; metaeditor 22368 down tolerated).

## C. The Flint campaign (2026-10-22/24) - `docs\daavfx\moe-lab\FLINT-CAMPAIGN.md`

- Upstream merge 36cbf41 (Flint arch) committed into the worktree; build
  11832 (commit f92d149db) is the current test binary.
- Flint upstream arch: 39.8B total / ~2.5B active, 47 MoE layers x 256
  routed experts, 35 sliding-window + 14 full-attention, ctx 262144.
- Quants fetched: `flint-UD-Q2_K_XL.gguf` (12.63 GB), `flint-UD-Q3_K_XL.gguf`
  (17.22 GB). Others planned up to IQ4_XS (22.24 GB, Tere Labs repo).
- **Load note (measured)**: Q2 loads ~4-6 min from F: at ngl 10; "no layer
  has all of its experts in host memory, MoE cache is disabled" at these
  splits; prompt processing at ngl 10 = 0.14-0.39 t/s.
- Quality: **Q2 9/12 (best in the collection)**, Q3 5/12.
- Agent bench: invalidated by the context-sizing config failure; the real
  test is the pending 32k rerun (X4).
- **X-ray**: the first router histogram was invalid (the logger captured only
  5.8% of Flint's topology: LFM-sized [24][32] arrays silently dropped
  everything else). Logger widened to 48x256 with a loud guard + stored
  stride; the cold-tail verdict is re-derived from the 2026-10-24 traces
  (X1) - surgery for Flint remains unproven until then.

## D. Driver bugs found and fixed in the bench driver (all receipt-backed)

1. `-StopAfterTurn` leash was structurally unreachable (no-action paths
   `continue` past it) - moved to the loop top; K2's t25 ctx-death explained.
2. `-LlamaServer` param was clobbered by a hardcoded path (PS variable names
   are case-insensitive) - the Flint sweep would have silently benchmarked
   the wrong binary.
3. Health-wait too short for 12 GB cold mmap loads (90 s -> 600 s) - healthy
   servers were being killed mid-load.
4. Two crashes in our own E0 probe (pointer-to-pointer, submit-info misuse)
   which initially masqueraded as a Vulkan "pathology" - retracted.

## E. The RYIUK archive audit (2026-10-24, four sub-agents)

The archive (`local_llm\GGUF\RYIUK`, 8,933 files) contains:
- PRIMAL/provenance system (`primal_evolution`): hostile-float silicon
  fingerprinting (the two GPUs disagree by 1 ULP on atan2; 100-run bit-exact
  determinism), receipt DAG, anti-collapse arithmetic measured at a 2,545x
  cost (gates itself out of runtime use).
- `candle-kernels-patched`: vendored candle CUDA kernels with a whole `src/
  moe/` directory (vllm.rs heritage: expert-indexed DP4A GEMV, warp-per-row
  GGUF decode GEMM, WMMA paths **stubbed for sm_75**). WMMA tensor-core MoE
  capability is fully dormant on this box - the sm_75 WMMA-f16 revival is
  experiment E2d.
- `kimi_k3_aproach.md` (1,039 lines, PROJECT KITTYHAWK): the operator's own
  matured MoE-streaming design - per-expert streaming, RAM hot-expert cache,
  co-activation clustering, depth_map precision ("never stream a
  high-precision weight"), Windows io_engine, the pre-router ("predict router
  output one token ahead... if it works, that's a paper"), greedy-as-a-knob.
  5 designed experiments, never run. **This converges with this program.**
- MASTER_REPORT.md: the operator's real llama.cpp tables (74.77 t/s 0.5B GPU;
  FFN->Q8_0 = all the PPL gain; GPU 12.3-15.7x over CPU).
- Claims correctly killed by their own audits: 116 TFLOPS (41x theoretical,
  synthetic loop), 40,000 t/s (empty loop), 9.7 TFLOPS (compiler artifact),
  48 TFLOPS (needs INT4), provenance-as-runtime (2,545x overhead).
Full classification in `02-TRUST-LEDGER.md`.

## F. The Vulkan platform work (ours, still live equipment)

- `shared\daavfx-vk-layer\`: queue-warmup layer (pays the first-submit stall
  during load) + submit-split layer (documents the nvoglv64+0xE90A8C fault on
  large submits). Both built and DLL-shipped.
- Loader trace discovery: every app auto-stacks AMD-switchable + OBS-hook +
  NV-present/optimus implicit layers; the first two have kill switches, used
  during measurements.
- `shared\daavfx-vk-probe\`: the E0 datasheet bench (all numbers in
  `01-MEASURED-FACTS.md`), the storage bench, RESULTS-E0 - the program's
  instrument set, deliberately small and dependency-free.
