# daavile fx fork of llama.cpp

Private fork of [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) at
`edd6e2b` (v0.5.0-dev era). Everything upstream is untouched except two small
touchpoints; the interesting part is the `daavfx_*` overlay in `src/`.

## What the overlay does

**DSpark hidden-state taps (live).** When `DAAVFX_DSPARK_TAPS=1`, a
`ggml_backend_sched_eval_callback` watches the layer-output tensors
(`l_out-<il>`) and copies the residual stream at chosen layers (default
`{2,6,10,14,18}`, hidden 2048) into a ring buffer -- the producer side for a
speculative-decoding draft that lives outside llama.cpp. The same callback
publishes live stats (capture count, timing, per-tap norms) to session-local
shared memory `Local\daavfx_dspark_<pid>`; any process in the session can read
it. Wire format: [`docs/daavfx/WIRE.md`](docs/daavfx/WIRE.md).

**Per-layer hooks (stats live, callbacks dormant).** Timing tables, layer and
dispatch callback registration, AMD APU auto-profile knobs. The scaffolding
compiles and the stats path runs; the callback paths activate when a consumer
registers (the theater/Vulkan lane).

**Theater dispatch (dormant).** Seqlock snapshot + shared-memory publisher for
CPU/RAM/STORAGE/IGPU/DGPU op routing. The routing call sites live in the Vulkan
lane and are not in this branch yet.

## What the overlay does NOT do

Change model math. Verified: perplexity on the same GGUF and corpus is
**bit-identical** between this fork and stock (`12.0265 +/- 0.30076`, all 17
per-chunk values matching to the digit). Taps cost ~0.03% of token time
(~3-15us per 8KB capture), i.e. observability is effectively free. Numbers:
[`docs/daavfx/BENCH.md`](docs/daavfx/BENCH.md).

## Repo layout

```
src/daavfx_dspark_bridge.{cpp,h}     tap install, eval callback, SHM publisher
src/daavfx_per_layer_hooks.{c,h}     capture ring, stats, hook scaffolding, wire structs
src/daavfx_theater_dispatch.{c,h}    seqlock + SHM dispatch snapshot (dormant)
src/llama-context.cpp                +include, +env-gated install (6 lines)
src/CMakeLists.txt                   +3 sources in LLAMA_CORE_SOURCES
docs/daavfx/WIRE.md                  shared-memory wire format (v1)
docs/daavfx/DAVFX-BUILD.md           build notes (Windows/MSVC; works on Linux too)
docs/daavfx/BENCH.md                 measured numbers (fork vs stock, taps cost)
docs/daavfx/overlay-vs-upstream.patch  the complete delta vs edd6e2b
patches/P1_fold_hsum.patch           PTQ1_0 ternary kernel micro-opt (+22%/+19%)
```

Companion tooling (the lab that drives these binaries, including a reference
reader for the SHM wire format): `github.com/daavfx/llab`.

## Build

Linux:

```sh
cmake -B build -DGGML_NATIVE=ON && cmake --build build --config Release -j
```

Windows/MSVC and tap usage: [`docs/daavfx/DAVFX-BUILD.md`](docs/daavfx/DAVFX-BUILD.md).

## License

Upstream llama.cpp terms (MIT) govern the inherited tree; the overlay follows
the same license.