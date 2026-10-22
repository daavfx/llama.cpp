# RESULTS.md - what the LFM2.5-8B-A1B campaign produced (2026-10-21)

One page. Everything below was MEASURED on this box (GTX 1650 4GB, Ryzen
5 5600G, 32 GB DDR4-2400, llama.cpp fork `daavfx` @ 43011a618 / 0.7.0,
Vulkan backend).

## 1. The two production configurations

| Mode | Config | Speed | CPU | Quality |
|---|---|---|---|---|
| MAX SPEED | `-ngl 99 -ncmoe 24 -t 6` | **18.9 t/s** tg, 111.8 pp | busy | 8/12 harness (baseline) |
| ZERO-CPU | same + `--moe-cache-mib 1536` + `GGML_VK_ASYNC_USE_TRANSFER_QUEUE=1` | 14-17.5 t/s (content dependent) | ~0% | same |
| RAM-SAVING | guided K=28 (mass-ranked per layer) | 18.9 t/s | busy | **9/12** harness, ~550 MB less RAM |

Launch (one command, hygiene included):

    powershell -File scripts\daavfx\launch-llm.ps1 -Mode split      # max speed
    powershell -File scripts\daavfx\launch-llm.ps1 -Mode zerocpu    # zero-CPU
    powershell -File scripts\daavfx\launch-llm.ps1 -Stop            # kill it

## 2. The thesis the campaign established

- **LFM2.5-8B-A1B's router is load-balanced BY DESIGN** (aux-loss-free
  equalizer, `exp_probs_b`). Measured: selection share of any index half =
  50.7%, gating mass 50.6%, `exp_probs_b` means +0.0076 / -0.0076. There is
  **no cold tail to harvest** - the "delete the unused experts" lane is closed
  for this model, permanently.
- **The quality cliff** (12-task agentic harness): K=28 guided 9/12,
  K=24 guided 8/12 (baseline-equal), K=16 guided 3/12, K=16 blind 1/12.
  Capacity cliff between K=24 and K=16; guidance is worth +17 points at K=16
  but cannot beat geometry.
- **The 60 t/s carrot** (full-GPU K=16) is real but poisoned: 60.1 t/s at
  3/12 quality, and the model answers 17x23 = 143 instead of 391.
- **Bandwidth map**: DDR4 28-30 GB/s > PCIe 11.5 theoretical / 3-8 real.
  The CPU split already sustains 10.2 GB/s effective (compute-mixed, 36% of
  DDR4 peak). Only VRAM residency beats DDR4, and that needs K<=18 where
  quality dies. Zero-copy host-mapped streaming was tested
  (GGML_VK_PREFER_HOST_MEMORY=1) and the loader DIES on 4.8 GB of
  host-visible allocation.
- **Spec-decode is structurally negative on the CPU-expert split**:
  verifying k draft tokens pulls up to 16 experts/layer instead of 4, so
  bytes per accepted token roughly double. Measured 1.9-8.4 t/s. Plus a
  vocab wall: the 8B has 128,000 tokens (bos 124894), every LFM2.5 small has
  65,536 (bos 1) - no same-family draft can exist.

## 3. The falsification ledger (all negative results, all kept)

| Idea | Verdict | Evidence |
|---|---|---|
| Blind index-half amputation | REJECTED | 1/12 vs 8/12 baseline |
| Guided per-layer amputation | USEFUL UP TO K=24 | 9/12 at K=28; cliff at K=16 |
| Single-centroid ghost | REJECTED | fill ratio 0.005 (ghost never fires) |
| Multi-ghost clustering | REJECTED (quality) | fill 33x better (0.168), quality unmoved (3/12) |
| Spec-decode (ngram) | REJECTED | 1.9-8.4 t/s, acceptance 0-32% |
| LK-2 ring-distance eviction | REJECTED | 7-10 t/s vs 14-15.6 (LRU+async) |
| Per-layer cache class policy | REJECTED pre-implementation | reuse profile flat (57-79%) |
| LK-0 config advisor | REJECTED by arithmetic | 17.5 t/s lane < 18.9 static baseline |
| Zero-copy host-mapped | REJECTED | loader crash + byte ceiling |
| Async transfer queue | **ACCEPTED** | 12.0 -> 16-17.5 t/s (+40%), zero code |

## 4. The Model X-Ray and Surgery Kit (for the NEXT MoE model)

Everything is in-tree and env-gated; nothing requires a rebuild.

    # 1. X-ray the router (which experts carry the mass, per layer)
    set DAAVFX_ROUTER_LOG=<out.csv>
    #    run any workload; the CSV has layer,expert,selected,mass_selected,mass_all,tokens

    # 2. X-ray the cache (per-layer reuse profile)
    set DAAVFX_MOE_CACHE_STATS=1
    #    prints per-layer hits/misses/rate/slots every 1024 calls

    # 3. Read the verdict (the campaign's decision rule)
    #    - halves ~50/50 + exp_probs_b antisymmetric  -> load-balanced model,
    #      amputation/ghost lanes are DEAD (this is LFM2.5-8B-A1B)
    #    - a real cold tail (mass concentrated in few experts) -> surgery is live:
    python scripts\daavfx\gguf-surgeon.py inspect --gguf <model>
    python scripts\daavfx\gguf-surgeon.py amputate --gguf <model> --out <mutant> \
        --policy <top-K per layer from the histogram> --clamp-used
    #    then llama-quantize (Q4_K_M) and score with the harness

    # 4. Score the mutant (destruction budget)
    powershell -File scripts\daavfx\quality-harness\run-harness.ps1 -Tag <name> -ServerUrl http://127.0.0.1:8083
    python scripts\daavfx\quality-harness\score.py --responses <file>

Tool inventory: scripts/daavfx/{gguf-surgeon.py (policy/ghost/ghosts/f16/mass modes),
quality-harness/, phase1-bench-matrix.ps1, launch-llm.ps1}. Docs:
docs/daavfx/moe-lab/{README.md (index), RESULTS.md (this file),
FORK-CHANGES.md (what we changed in the fork), GTX1650-LFM25-CAMPAIGN.md
(plan + measured state), FOUNDRY.md (falsifications),
LIVING-KERNEL-DESIGN.md (closed control-plane design),
TYPED-DECISIONS.md, CPU-MISS-FALLBACK-DESIGN.md}. Ledger: INFLIGHT.md.

## 5. Hygiene

- Never leave a server running when idle: `launch-llm.ps1 -Stop`.
- Long jobs: launch detached (WMI), poll the log, never block a shell.
- Roundtrip-test the surgeon before trusting a mutant (byte-exact gate).
- The 12-task harness is the only judge of a surgery result; tokens/sec alone
  celebrated a lobotomized model.
