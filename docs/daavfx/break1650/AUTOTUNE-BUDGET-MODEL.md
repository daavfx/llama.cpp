# AUTOTUNE-BUDGET-MODEL - EXP-3 paper (layout-driven launch policy)

Date: 2026-10-26. Zero-GPU: every input is a measured number or a GGUF
header field. This is the paper half of EXP-3 (the probe sweep is gated).

## Inputs (all measured or read, nothing assumed)

Layout signature, from the GGUF header (no model load):

| Model | arch | blocks | experts | top-k | file bytes |
|---|---|---|---|---|---|
| Flint Q2_K_XL | flint | 49 | 256 | 6 | 12.63 GB |
| LFM2.5-8B-A1B | lfm2moe | 24 | 32 | 4 | 4.9 GB |

Device profile, from the E0 probe (stamped per clock state):

| Channel | Rate |
|---|---|
| dGPU VRAM bandwidth (fp16 FMA achieved) | 3,179 GFLOPS |
| dGPU copy (PCIe) | 13.3 GB/s H2D |
| dGPU in-shader host read | 1.4 GB/s |
| dGPU VRAM | 4 GB (90 W card, P8 idle 300/405 MHz) |
| iGPU in-shader host read | 4.8 GB/s |
| iGPU copy | 15.5 GB/s |
| iGPU dispatch | 50 ns (vs dGPU 178 ns) |
| CPU MoE split (campaign) | 10.2 GB/s effective |
| F: disk (model store) | 4K QD1 ~12 ms (HDD) |
| C: disk (NVMe) | 4K QD1 ~0.28 ms |

## The budget model (per decode token)

```
moe_layers        = block_count - dense_layers          (dense_layers: 2 inferred)
expert_fraction   = 1 - active_params / total_params    (~0.945 for Flint; LFM ~0.81)
total_expert_bytes= file_bytes * expert_fraction
expert_bytes_read = file_bytes * expert_fraction * (top_k / expert_count)
                     = file_bytes * expert_fraction * top_k / expert_count
kv_bytes          = ctx * kv_per_token (per model, from hparams)
resident_bytes    = attention + dense + kv  (must fit VRAM when placed)
```

Flint Q2_K_XL: `12.63 * 0.945 * 6/256 = 0.28 GB per token` of expert bytes.
LFM2.5-8B: `4.9 * 0.81 * 4/32 = 0.495 GB per token` - matches the campaign's
measured 0.54 GB/token (10.2 GB/s at 18.9 t/s) to within 9% on estimates
alone. That is the model's calibration receipt: the arithmetic is right
within the noise of the estimates.

## The policy solve (given the signature + device profile)

```
stream_rate = min(bottleneck) over the chosen tier for expert bytes:
    - expert resident in VRAM  -> vram bandwidth (~350+ GB/s class)
    - expert on CPU split      -> 10.2 GB/s effective (MEASURED)
    - expert streamed from RAM -> 1.4 GB/s dGPU / 4.8 GB/s iGPU (MEASURED)
    - expert streamed from disk -> 0.06-0.2 GB/s (MEASURED)  [F:]
policy:
    1. fit attention + dense + KV in 4 GB VRAM
    2. if expert_bytes_read <= cpu_split_rate / target_tps:
           ncmoe = max MoE layers whose experts stay on CPU (like LFM's 18.9)
       else:
           resident_hot_set = VRAM - (1) ; put the hottest experts there
           (needs the router capture - see EXP-2)
    3. threads: CPU-bound if experts on CPU, else 6
```

Worked examples (paper only):
- **LFM2.5-8B** (0.495 GB/tok): 0.495 / 10.2 = 0.049 s/token = 20.5 t/s
  ceiling vs 18.9 measured - the CPU split is the right policy and the model
  agrees with the campaign within 8%.
- **Flint Q2** (0.28 GB/tok): 0.28 / 10.2 = 0.027 s = 36.8 t/s ceiling on the
  same policy - 2x the LFM baseline in theory. This is the number the sweep
  must confirm or refute; the 0.14-0.39 t/s the X-ray reported is a cold-start
  artifact (1a receipt), and 0.43-1.6 t/s appears only for the first 3
  requests of a cold server.
- **A hypothetical 256/8 model**: 8/256 expert bytes/token doubles again;
  the policy spine is unchanged - the signature drives it.

## The probe sweep (gated, one green window)

```
for policy in [cpu-split base, cpu-split +moe-cache 1024, hot-set when EXP-2 lands]:
    llama-bench -p 512 -n 128 -m <model> <policy args>
stamp: clock state, driver state, build, model, command line
adopt: smallest policy within 1.1x of the best measured
```

## What this paper does NOT claim

- No hot-set data exists yet (the selection channel is dead until EXP-2), so
  the Flint hot-set variant of the policy is written but unmeasured.
- The expert_fraction and dense_layers are inferred, not read from the GGUF
  (no field exposes them directly); the calibration receipt says the
  inference is good to ~10%.
- All rates are from today's stampings; re-stamp before any decision.
