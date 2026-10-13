// daavile fx: DSpark hidden-tap bridge.
// Implements a ggml_backend_sched_eval_callback that feeds layer-output
// hidden states at the DSpark tap layers into the C hook ring buffer
// (daavfx_per_layer_hooks.c). Enabled via env DAAVFX_DSPARK_TAPS=1.
//
// The Rust side (daavfx-cortex speculative::dspark) reads the ring via
// daavfx_dspark_read()/daavfx_dspark_seq() FFI.

#pragma once

#include "llama-cparams.h"
#include <functional>

// Install the DSpark tap callback into cparams before context creation.
// Returns true if the env gate is on and the callback was installed.
bool daavfx_dspark_try_install(llama_cparams & cparams);

// Poll helpers for external consumers (Rust FFI wrappers live in the same TU).
bool     daavfx_dspark_bridge_enabled();
uint64_t daavfx_dspark_bridge_seq();
int32_t  daavfx_dspark_bridge_read(float* out, int32_t max_floats);
