# Measured numbers

All rows produced with `llama-bench -o jsonl`, BelowNormal priority, t = 6
threads, `-ngl 0`, on the reference machine (Ryzen 5 5600G, 2x 3600 DDR4,
Windows 11). "stock" = same upstream base without the overlay.

## 1. The overlay does not change model math

Perplexity, same GGUF (Qwen3.5-2B Q4_K_M, current-converter), same frozen
90,726-byte corpus, ctx 2048, 17 chunks:

| engine | final PPL | stderr | per-chunk values |
|---|---|---|---|
| stock  | **12.0265** | 0.30076 | 5.4915, 5.7134, 7.5912, 9.1511, ... 12.0265 |
| fork   | **12.0265** | 0.30076 | identical to the digit |

Verdict: numerically the same model, bit-for-bit identical chunk scores.

## 2. Tap capture is free

In-process measurement (QPC inside the capture path): ~2.8-15us per 2048-float
capture, ~20us per token step, **~0.03% of token time**.

A/B bench, qwen2b-fresh, mod engine, t6, sequential runs:

| config | pp512 tok/s | tg128 tok/s |
|---|---|---|
| taps off | 92.0 | 14.05 |
| taps on  | 97.8 | 14.86 |

Within run-to-run noise (the taps-on run won by ~6%, i.e. there is no
measurable penalty). Leave taps on while debugging.

## 3. Speed rows (same day, fork build)

| model | engine | pp512 | tg128 |
|---|---|---|---|
| qwen2b-fresh (Qwen3.5-2B Q4_K_M) | stock | 112.2 | 17.9 |
| qwen2b-fresh | fork  | 97.8-118.2 | 14.9-18.2 |
| LFM2.5-230M Q8  | stock | 510.8 | 100.1 |
| LFM2.5-350M Q8  | stock | 308.4 | 65.0 |
| LFM2.5-1.2B-Instruct Q8 | stock | 90.4 | 21.7 |

(Full machine-readable rows live in the companion dataset repo `llab-data`.)

## 4. Kernel patch (PTQ1_0, from the kernel campaign)

P1 fold-hsum on the ternary vec_dot path, b11065-era tree, pp128/tg32 r1:

| config | t6 pp/tg | t12 pp/tg |
|---|---|---|
| pre-patch | 0.99 / 0.86 | 1.23 / 0.93 |
| post-patch | 1.21 / 1.02 | 1.41 / 1.16 |

+22%/+19% and +15%/+25% respectively; generated text byte-identical
(integer-exact change). See `patches/P1_fold_hsum.patch`.
