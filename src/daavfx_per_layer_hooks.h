/**
 * daavfx_per_layer_hooks.h
 * 
 * Per-layer callback hooks for llama.cpp inference pipeline.
 * Designed for DAAVFX theater-sharded dispatch.
 * 
 * Integration: Include this header in llama.cpp's ggml_compute_graph
 * and call the hooks at each layer boundary.
 * 
 * Build: Add to llama.cpp CMakeLists.txt:
 *   target_sources(llama PRIVATE daavfx_per_layer_hooks.c)
 */

#ifndef DAAVFX_PER_LAYER_HOOKS_H
#define DAAVFX_PER_LAYER_HOOKS_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Theater IDs matching trinity_scheduler.rs
 */
typedef enum {
    DAAVFX_THEATER_CPU        = 0,
    DAAVFX_THEATER_RAM        = 1,
    DAAVFX_THEATER_STORAGE    = 2,
    DAAVFX_THEATER_RAM_STORAGE = 3,
    DAAVFX_THEATER_IGPU       = 4,
    DAAVFX_THEATER_DGPU       = 5,
    DAAVFX_THEATER_COUNT      = 6,
} daavfx_theater_t;

/**
 * Operation kinds matching OpKind in trinity_scheduler.rs
 */
typedef enum {
    DAAVFX_OP_MATMUL        = 0,
    DAAVFX_OP_SOFTMAX       = 1,
    DAAVFX_OP_LAYERNORM     = 2,
    DAAVFX_OP_ROPE          = 3,
    DAAVFX_OP_KV_CACHE      = 4,
    DAAVFX_OP_SAMPLING      = 5,
    DAAVFX_OP_WEIGHT_PAGING = 6,
    DAAVFX_OP_EMBED         = 7,
    DAAVFX_OP_COUNT         = 8,
} daavfx_op_kind_t;

/**
 * Per-layer callback context
 */
typedef struct {
    int32_t  layer_index;        // Current layer (0-based)
    int32_t  total_layers;       // Total layers in model
    daavfx_op_kind_t op;         // Operation being performed
    daavfx_theater_t assigned;   // Theater assigned by scheduler
    uint64_t start_ns;           // Start timestamp (nanoseconds)
    uint64_t end_ns;             // End timestamp (nanoseconds)
    float    cost_ms;            // Measured cost in milliseconds
    float    thermal_pressure;   // Current thermal pressure (0.0-1.0)
    int32_t  ngl;                // Number of GPU layers (-ngl value)
    bool     cancelled;          // Set to true to abort inference
} daavfx_layer_context_t;

/**
 * Callback function type.
 * Called after each layer completes.
 * Return false to continue, true to request cancellation.
 */
typedef bool (*daavfx_layer_callback_t)(const daavfx_layer_context_t* ctx, void* user_data);

/**
 * Callback for operation-level dispatch decisions.
 * Called before each operation starts, allowing the scheduler to
 * redirect work to a different theater.
 */
typedef struct {
    daavfx_theater_t (*select_theater)(
        daavfx_op_kind_t op,
        int32_t layer,
        float thermal_pressure,
        void* user_data
    );
    void* user_data;
} daavfx_dispatch_callback_t;

/**
 * Global state for the hook system
 */
typedef struct {
    daavfx_layer_callback_t   layer_cb;
    daavfx_dispatch_callback_t dispatch_cb;
    void*                     user_data;
    bool                      enabled;
    int32_t                   total_layers;
    float                     thermal_pressure;
    uint64_t                  layer_start_ns;
    bool                      amd_igpu_profile;
    uint32_t                  ngl;
    int32_t                   n_batch;
    int32_t                   n_ubatch;
    int32_t                   cache_ram;
    uint32_t                  cpu_ops;
    uint32_t                  igpu_ops;
    uint32_t                  ram_ops;
} daavfx_hooks_state_t;

/**
 * Initialize the hook system.
 * Call once at startup, before loading any model.
 */
void daavfx_hooks_init(void);

/**
 * Register callbacks.
 */
void daavfx_hooks_register_layer(daavfx_layer_callback_t cb, void* user_data);
void daavfx_hooks_register_dispatch(daavfx_dispatch_callback_t cb, void* user_data);

/**
 * Enable/disable hooks at runtime.
 */
void daavfx_hooks_set_enabled(bool enabled);
bool daavfx_hooks_is_enabled(void);

/**
 * Update thermal pressure (call periodically from main thread).
 */
void daavfx_hooks_set_thermal_pressure(float pressure);

/**
 * Register a device for theater dispatch with measured throughput.
 */
void daavfx_dispatch_register_device(daavfx_theater_t theater, float compute_tps);

/**
 * Set thermal pressure for a specific device.
 */
void daavfx_dispatch_set_thermal(daavfx_theater_t theater, float pressure);

/**
 * Set total layer count (call after loading model).
 */
void daavfx_hooks_set_total_layers(int32_t total);

/* DaavFX AMD APU runtime knobs */
void daavfx_hooks_set_amd_profile(bool enabled);
bool daavfx_hooks_is_amd_profile(void);
uint32_t daavfx_hooks_get_ngl(void);
void daavfx_hooks_set_batch(int32_t batch, int32_t ubatch);
int32_t daavfx_hooks_get_batch(void);
int32_t daavfx_hooks_get_ubatch(void);
void daavfx_hooks_set_cache_ram(int32_t cache_ram);
int32_t daavfx_hooks_get_cache_ram(void);

/**
 * Get the assigned theater for a given operation.
 * Called from ggml_compute to decide where to execute.
 */
daavfx_theater_t daavfx_hooks_get_theater(daavfx_op_kind_t op, int32_t layer);

/**
 * Called at layer start. Records timestamp.
 */
void daavfx_hooks_layer_start(int32_t layer, daavfx_op_kind_t op);

/**
 * Called at layer end. Computes cost, invokes callback.
 * Returns true if cancellation requested.
 */
bool daavfx_hooks_layer_end(int32_t layer, daavfx_op_kind_t op);

/**
 * Get layer timing data for external query.
 */
typedef struct {
    int32_t  layer;
    daavfx_op_kind_t op;
    daavfx_theater_t theater;
    float    cost_ms;
    uint64_t start_ns;
    uint64_t end_ns;
} daavfx_layer_timing_t;

/**
 * Retrieve timing data for all completed layers.
 * Returns number of entries written to `out`.
 * `out` must have capacity for at least `total_layers` entries.
 */
int32_t daavfx_hooks_get_timings(daavfx_layer_timing_t* out, int32_t max_entries);

/**
 * Get summary statistics.
 */
typedef struct {
    float    total_ms;
    float    sequential_ms;       // Sum of all layer costs
    float    parallel_ms;         // Max of parallel groups
    float    speedup_pct;         // (sequential - parallel) / sequential * 100
    int32_t  layers_completed;
    int32_t  layers_total;
    float    op_ms[DAAVFX_OP_COUNT];
    int32_t  op_count[DAAVFX_OP_COUNT];
    float    theater_ms[DAAVFX_THEATER_COUNT];
    int32_t  theater_count[DAAVFX_THEATER_COUNT];
} daavfx_hooks_summary_t;

daavfx_hooks_summary_t daavfx_hooks_get_summary(void);

/* ------------------------------------------------------------------ */
/* daavile fx: DSpark hidden-state taps                                */
/*                                                                     */
/* Captures the residual-stream hidden states of the LFM target at the */
/* DSpark tap layers ([2,6,10,14,18]) so the Rust draft can consume    */
/* concatenated target hiddens [5 * 2048 = 10240] without touching     */
/* Python. Ring-buffer semantics: each capture overwrites the last.    */
/* ------------------------------------------------------------------ */

#define DAAVFX_DSPARK_TAPS       5
#define DAAVFX_DSPARK_HIDDEN     2048
#define DAAVFX_DSPARK_FLOATS     (DAAVFX_DSPARK_TAPS * DAAVFX_DSPARK_HIDDEN)

/* Enable/disable tap capture (off by default; ~40KB memcpy per token). */
void daavfx_dspark_set_enabled(bool enabled);
bool daavfx_dspark_is_enabled(void);

/* Configure tap layer indices (default {2,6,10,14,18}) and hidden size. */
void daavfx_dspark_configure(const int32_t* tap_layers, int32_t n_taps, int32_t hidden_size);

/* Called by cb_eval when a tensor whose name matches "l_out" at a tap layer
 * finishes evaluating (data != NULL pass). Copies t->data into the ring. */
void daavfx_dspark_capture(int32_t layer_index, const void* data, int32_t n_floats);

/* Snapshot all taps into `out` (DAAVFX_DSPARK_FLOATS floats, tap-major).
 * Returns number of floats written (0 if disabled / nothing captured). */
int32_t daavfx_dspark_read(float* out, int32_t max_floats);

/* Monotonic sequence counter — increments on each full 5-tap capture set.
 * Lets the consumer detect a fresh snapshot vs a partially-written one. */
uint64_t daavfx_dspark_seq(void);

/* Live tap stats for external observers (the bridge publishes these to
 * Local\daavfx_dspark_<pid> shared memory; the Rust lab maps it read-only).
 * Layout is a wire format shared with crates/llab - keep fields in sync. */
typedef struct {
    uint32_t version;                       /* struct version, 1 */
    uint32_t enabled;                       /* 0/1 */
    uint64_t seq;                           /* full 5-tap sets captured */
    uint64_t captures;                      /* per-tap captures */
    uint64_t bytes;                         /* floats copied into the ring */
    uint64_t total_ns;                      /* time spent inside capture */
    float    norms[DAAVFX_DSPARK_TAPS];     /* last L2 norm per tap */
    float    last_ns;                       /* last capture duration */
    int32_t  taps[DAAVFX_DSPARK_TAPS];      /* configured layer indices */
    int32_t  hidden;                        /* hidden size */
    uint32_t epoch;                         /* seqlock: stable when even */
    uint32_t _pad;
} daavfx_dspark_stats_t;

void daavfx_dspark_get_stats(daavfx_dspark_stats_t* out);

#ifdef __cplusplus
}
#endif

#endif /* DAAVFX_PER_LAYER_HOOKS_H */
