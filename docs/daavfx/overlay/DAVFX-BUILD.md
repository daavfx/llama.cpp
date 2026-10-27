# Build (Windows / MSVC, CPU)

Tested on: AMD Ryzen 5 5600G, Windows 11, VS 2022 17.x, CMake >= 3.28.

## 1. Get the upstream base

Clone llama.cpp at the pinned commit and apply the overlay:

```
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
git checkout edd6e2b          # pinned base of this overlay
```

Copy the six `src/daavfx_*.{c,h,cpp}` files from this repo into `src/`, then:

```
git apply -p1 path\to\upstream-touchpoints.patch
```

(Or make the two edits by hand -- the patch is 3 added CMake sources and one
include + install guard in `llama-context.cpp`.)

## 2. Configure + build (CPU only)

```
cmake -B build_cpu -G "Visual Studio 17 2022" -A x64 -DGGML_NATIVE=ON -DBUILD_SHARED_LIBS=OFF
cmake --build build_cpu --config Release -- /m
```

Binaries land in `build_cpu\bin\Release\` (llama-server, llama-bench, llama-cli,
llama-perplexity, llama-quantize, ...).

Notes:
- `GGML_NATIVE=ON` bakes in the host CPU ISA (AVX2 on Zen3). Keep it ON for
  personal machines; OFF for redistributable binaries.
- If you rename the source folder after configuring, the CMake cache holds
  absolute paths and the build refuses to run; reconfigure (or patch the
  cached paths) instead of copying build trees across machines.
- `DAAVFX_DSPARK_TAPS=1` in the environment at llama-context creation time
  enables the tap bridge. Without it the fork behaves like a stock build
  (no callback installed, zero overhead).

## 3. Verify taps are live

Run any binary with the env var set, e.g.:

```
set DAAVFX_DSPARK_TAPS=1
llama-cli.exe -m model.gguf -p "hello" -n 16 -t 4
```

While it runs, read `Local\daavfx_dspark_<pid>` (see WIRE.md) -- `seq` should
tick once per token step once the prompt is being evaluated.

## Optional: PTQ1_0 kernel patch

`patches/P1_fold_hsum.patch` is a standalone micro-optimization for the PTQ1_0
(ternary) CPU vec_dot path: one horizontal sum per sub-block instead of two,
integer-exact by associativity. It applied cleanly to a b11065-era tree; on
newer bases check context before applying.
