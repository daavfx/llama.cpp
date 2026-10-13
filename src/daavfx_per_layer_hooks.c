/**
 * daavfx_per_layer_hooks.c
 * 
 * Implementation of per-layer callback hooks for llama.cpp.
 * Designed for DAAVFX theater-sharded dispatch.
 */

#include "daavfx_per_layer_hooks.h"
#include "daavfx_theater_dispatch.h"
#include <string.h>
#include <math.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <time.h>
#endif

#define DAAVFX_MAX_DEVICES 4
#define DAAVFX_MAX_LAYERS 256
#define DAAVFX_MAX_TIMINGS (DAAVFX_MAX_LAYERS * 7)  // max ops per layer

typedef struct {
    daavfx_theater_t theater;
    float            compute_tps;       /* recent measured throughput */
    float            thermal_pressure;  /* 0..1 */
    uint64_t         last_used_ns;
} daavfx_device_info_t;

static daavfx_device_info_t g_devices[DAAVFX_MAX_DEVICES];
static int32_t              g_device_count = 0;

static daavfx_hooks_state_t g_hooks = {0};
static daavfx_layer_timing_t g_timings[DAAVFX_MAX_TIMINGS];
static int32_t g_timing_count = 0;
static daavfx_dispatch_state_t g_dispatch_state = {0};
static int32_t g_last_dispatch_layer = -1;
static daavfx_theater_t g_last_dispatch_theater = DAAVFX_THEATER_CPU;
#define DAAVFX_DISPATCH_CACHE 128
static int32_t g_dispatch_cache_layer[DAAVFX_DISPATCH_CACHE];
static daavfx_theater_t g_dispatch_cache_theater[DAAVFX_DISPATCH_CACHE];

// Layer timing tracking per-op
typedef struct {
    uint64_t start_ns;
    bool     active;
} layer_op_state_t;

static layer_op_state_t g_layer_state[DAAVFX_MAX_LAYERS][7];  // 7 op kinds

static uint64_t get_ns(void) {
    // Windows: QueryPerformanceCounter
#ifdef _WIN32
    static LARGE_INTEGER freq = {0};
    LARGE_INTEGER now;
    if (!freq.QuadPart) QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&now);
    return (uint64_t)((now.QuadPart * 1000000000ULL) / freq.QuadPart);
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
#endif
}

void daavfx_hooks_init(void) {
    memset(&g_hooks, 0, sizeof(g_hooks));
    memset(g_timings, 0, sizeof(g_timings));
    g_timing_count = 0;
    g_hooks.thermal_pressure = 0.3f;  // default assumption
    g_hooks.ngl = 32;                // default all-offload ceiling
    daavfx_dispatch_init();
    daavfx_hooks_set_amd_profile(false);
}

void daavfx_hooks_register_layer(daavfx_layer_callback_t cb, void* user_data) {
    g_hooks.layer_cb = cb;
    g_hooks.user_data = user_data;
}

void daavfx_hooks_register_dispatch(daavfx_dispatch_callback_t cb, void* user_data) {
    g_hooks.dispatch_cb = cb;
    if (user_data) g_hooks.user_data = user_data;
}

void daavfx_hooks_set_enabled(bool enabled) {
    g_hooks.enabled = enabled;
}

bool daavfx_hooks_is_enabled(void) {
    return g_hooks.enabled;
}

void daavfx_hooks_set_thermal_pressure(float pressure) {
    g_hooks.thermal_pressure = pressure < 0.0f ? 0.0f : (pressure > 1.0f ? 1.0f : pressure);
}

void daavfx_hooks_set_total_layers(int32_t total) {
    g_hooks.total_layers = total > DAAVFX_MAX_LAYERS ? DAAVFX_MAX_LAYERS : total;
}

void daavfx_hooks_set_amd_profile(bool enabled) {
    g_hooks.amd_igpu_profile = enabled;
    if (!enabled) return;

    g_hooks.ngl = 32;
    g_hooks.cpu_ops = (1u << DAAVFX_OP_SOFTMAX) |
                      (1u << DAAVFX_OP_LAYERNORM) |
                      (1u << DAAVFX_OP_ROPE) |
                      (1u << DAAVFX_OP_SAMPLING);
    g_hooks.igpu_ops = (1u << DAAVFX_OP_MATMUL);
    g_hooks.ram_ops = (1u << DAAVFX_OP_EMBED) |
                      (1u << DAAVFX_OP_KV_CACHE);
}

void daavfx_hooks_set_batch(int32_t batch, int32_t ubatch) {
    g_hooks.n_batch = batch > 0 ? batch : g_hooks.n_batch;
    g_hooks.n_ubatch = ubatch > 0 ? ubatch : g_hooks.n_ubatch;
}

void daavfx_hooks_set_cache_ram(int32_t cache_ram) {
    g_hooks.cache_ram = cache_ram;
}

bool daavfx_hooks_is_amd_profile(void) {
    return g_hooks.amd_igpu_profile;
}

uint32_t daavfx_hooks_get_ngl(void) {
    return g_hooks.ngl;
}

int32_t daavfx_hooks_get_batch(void) {
    return g_hooks.n_batch;
}

int32_t daavfx_hooks_get_ubatch(void) {
    return g_hooks.n_ubatch;
}

int32_t daavfx_hooks_get_cache_ram(void) {
    return g_hooks.cache_ram;
}

void daavfx_dispatch_register_device(daavfx_theater_t theater, float compute_tps) {
    int32_t idx = -1;
    for (int32_t i = 0; i < g_device_count; i++) {
        if (g_devices[i].theater == theater) { idx = i; break; }
    }
    if (idx < 0 && g_device_count < DAAVFX_MAX_DEVICES) {
        idx = g_device_count++;
        g_devices[idx].theater = theater;
        g_devices[idx].compute_tps = compute_tps;
        g_devices[idx].thermal_pressure = 0.0f;
        g_devices[idx].last_used_ns = 0;
    }
    if (idx >= 0 && compute_tps > 0.0f) {
        g_devices[idx].compute_tps = compute_tps;
    }
}

void daavfx_dispatch_set_thermal(daavfx_theater_t theater, float pressure) {
    for (int32_t i = 0; i < g_device_count; i++) {
        if (g_devices[i].theater == theater) {
            g_devices[i].thermal_pressure = pressure < 0.0f ? 0.0f : (pressure > 1.0f ? 1.0f : pressure);
            break;
        }
    }
}

daavfx_theater_t daavfx_hooks_get_theater(daavfx_op_kind_t op, int32_t layer) {
    daavfx_theater_t amd_choice = DAAVFX_THEATER_CPU;
    if (g_hooks.amd_igpu_profile) {
        /* DaavFX AMD APU split routing:
         * - MATMUL: Vulkan iGPU
         * - SOFTMAX/LAYERNORM/ROPE/SAMPLING: CPU
         * - EMBED/KV_CACHE: RAM storage
         */
        switch (op) {
            case DAAVFX_OP_MATMUL:
                amd_choice = DAAVFX_THEATER_IGPU;
                break;
            case DAAVFX_OP_EMBED:
            case DAAVFX_OP_KV_CACHE:
                amd_choice = DAAVFX_THEATER_RAM_STORAGE;
                break;
            case DAAVFX_OP_SOFTMAX:
            case DAAVFX_OP_LAYERNORM:
            case DAAVFX_OP_ROPE:
            case DAAVFX_OP_SAMPLING:
            default:
                amd_choice = DAAVFX_THEATER_CPU;
                break;
        }
        g_last_dispatch_layer = layer;
        g_last_dispatch_theater = amd_choice;
        g_dispatch_cache_layer[layer % DAAVFX_DISPATCH_CACHE] = layer;
        g_dispatch_cache_theater[layer % DAAVFX_DISPATCH_CACHE] = amd_choice;
        return amd_choice;
    }

    /* 0) Fast per-layer cache */
    if (g_last_dispatch_layer == layer) {
        return g_last_dispatch_theater;
    }
    for (int32_t i = 0; i < DAAVFX_DISPATCH_CACHE; i++) {
        if (g_dispatch_cache_layer[i] == layer) {
            g_last_dispatch_layer = layer;
            g_last_dispatch_theater = g_dispatch_cache_theater[i];
            return g_last_dispatch_theater;
        }
    }

    /* 1) Cheap inline SHM availability check */
    if (g_dispatch_state.writer_seq != g_dispatch_state.reader_seq) {
        daavfx_theater_t shm = DAAVFX_THEATER_CPU;
        if (daavfx_dispatch_pick(&g_dispatch_state, op, layer, NULL, &shm) && shm != DAAVFX_THEATER_CPU) {
            g_last_dispatch_layer = layer;
            g_last_dispatch_theater = shm;
            return shm;
        }
    }

    /* 2) Fallback to local device selection */
    /* No devices registered -> default CPU */
    if (g_device_count == 0) {
        g_last_dispatch_layer = layer;
        g_last_dispatch_theater = DAAVFX_THEATER_CPU;
        return DAAVFX_THEATER_CPU;
    }

    /* High thermal pressure -> CPU/RAM path */
    float max_pressure = 0.0f;
    for (int32_t i = 0; i < g_device_count; i++) {
        if (g_devices[i].thermal_pressure > max_pressure) {
            max_pressure = g_devices[i].thermal_pressure;
        }
    }
    if (max_pressure > 0.75f) {
        g_last_dispatch_layer = layer;
        g_last_dispatch_theater = DAAVFX_THEATER_CPU;
        return DAAVFX_THEATER_CPU;
    }

    /* Find candidate devices for this op */
    daavfx_device_info_t* best = NULL;
    float best_score = -1.0f;

    for (int32_t i = 0; i < g_device_count; i++) {
        daavfx_device_info_t* dev = &g_devices[i];

        /* Skip devices under local thermal pressure */
        if (dev->thermal_pressure > 0.6f) continue;

        /* Filter by device capability for op */
        bool capable = false;
        switch (dev->theater) {
            case DAAVFX_THEATER_CPU:
                capable = true;
                break;
            case DAAVFX_THEATER_IGPU:
            case DAAVFX_THEATER_DGPU:
                capable = (op == DAAVFX_OP_MATMUL || op == DAAVFX_OP_SOFTMAX || op == DAAVFX_OP_LAYERNORM);
                break;
            case DAAVFX_THEATER_RAM_STORAGE:
                capable = (op == DAAVFX_OP_KV_CACHE || op == DAAVFX_OP_EMBED);
                break;
            default:
                break;
        }
        if (!capable) continue;

        /* Score = throughput / (1 + thermal penalty) */
        float score = dev->compute_tps / (1.0f + dev->thermal_pressure * 4.0f);

        /* Prefer recently unused device to balance load */
        if (dev->last_used_ns > 0) {
            uint64_t age_ns = get_ns() - dev->last_used_ns;
            float age_s = (float)(age_ns / 1000000000ULL);
            score += age_s > 10.0f ? 0.5f : 0.0f;
        }

        if (score > best_score) {
            best_score = score;
            best = dev;
        }
    }

    if (!best) {
        g_last_dispatch_layer = layer;
        g_last_dispatch_theater = DAAVFX_THEATER_CPU;
        return DAAVFX_THEATER_CPU;
    }
    best->last_used_ns = get_ns();

    g_last_dispatch_layer = layer;
    g_last_dispatch_theater = best->theater;
    g_dispatch_cache_layer[layer % DAAVFX_DISPATCH_CACHE] = layer;
    g_dispatch_cache_theater[layer % DAAVFX_DISPATCH_CACHE] = best->theater;
    return best->theater;
}

void daavfx_hooks_layer_start(int32_t layer, daavfx_op_kind_t op) {
    if (!g_hooks.enabled || layer < 0 || layer >= DAAVFX_MAX_LAYERS) return;
    if (op < 0 || op > 6) return;

    g_layer_state[layer][op].start_ns = get_ns();
    g_layer_state[layer][op].active = true;
}

bool daavfx_hooks_layer_end(int32_t layer, daavfx_op_kind_t op) {
    if (!g_hooks.enabled || layer < 0 || layer >= DAAVFX_MAX_LAYERS) return false;
    if (op < 0 || op > 6) return false;
    if (!g_layer_state[layer][op].active) return false;

    uint64_t end_ns = get_ns();
    uint64_t start_ns = g_layer_state[layer][op].start_ns;
    float cost_ms = (float)((end_ns - start_ns) / 1000000.0);

    g_layer_state[layer][op].active = false;

    // Record timing
    if (g_timing_count < DAAVFX_MAX_TIMINGS) {
        daavfx_layer_timing_t* t = &g_timings[g_timing_count++];
        t->layer = layer;
        t->op = op;
        t->theater = daavfx_hooks_get_theater(op, layer);
        t->cost_ms = cost_ms;
        t->start_ns = start_ns;
        t->end_ns = end_ns;
    }

    // DaavFX: publish theater choice to Rust SHM writer so runtime can switch CPU↔iGPU dynamically
    if (daavfx_hooks_is_amd_profile() && g_hooks.enabled) {
        daavfx_dispatch_state_t* state = daavfx_dispatch_get_state();
        if (state) {
            daavfx_theater_t assigned = daavfx_hooks_get_theater(op, layer);
            daavfx_dispatch_set_snapshot(state,
                (uint32_t)assigned,
                (uint32_t)op,
                0.95f,
                g_hooks.thermal_pressure,
                0.2f,
                "amd-auto");
        }
    }

    // Invoke callback
    if (g_hooks.layer_cb) {
        daavfx_layer_context_t ctx = {
            .layer_index = layer,
            .total_layers = g_hooks.total_layers,
            .op = op,
            .assigned = daavfx_hooks_get_theater(op, layer),
            .start_ns = start_ns,
            .end_ns = end_ns,
            .cost_ms = cost_ms,
            .thermal_pressure = g_hooks.thermal_pressure,
            .ngl = 0,
            .cancelled = false,
        };
        return g_hooks.layer_cb(&ctx, g_hooks.user_data);
    }
    return false;
}

int32_t daavfx_hooks_get_timings(daavfx_layer_timing_t* out, int32_t max_entries) {
    int32_t n = g_timing_count < max_entries ? g_timing_count : max_entries;
    memcpy(out, g_timings, n * sizeof(daavfx_layer_timing_t));
    return n;
}

daavfx_hooks_summary_t daavfx_hooks_get_summary(void) {
    daavfx_hooks_summary_t s = {0};
    s.layers_total = g_hooks.total_layers;
    s.layers_completed = g_timing_count > 0 ? g_timings[g_timing_count - 1].layer + 1 : 0;

    // Compute sequential (sum of all ops) and parallel (max per layer)
    float layer_max[DAAVFX_MAX_LAYERS] = {0};
    for (int32_t i = 0; i < g_timing_count; i++) {
        s.sequential_ms += g_timings[i].cost_ms;
        int32_t l = g_timings[i].layer;
        if (l >= 0 && l < DAAVFX_MAX_LAYERS) {
            if (g_timings[i].cost_ms > layer_max[l]) {
                layer_max[l] = g_timings[i].cost_ms;
            }
        }

        /* DaavFX per-op profiling: accumulate by op kind and theater */
        if (g_timings[i].op >= 0 && g_timings[i].op < DAAVFX_OP_COUNT) {
            s.op_ms[g_timings[i].op] += g_timings[i].cost_ms;
            s.op_count[g_timings[i].op]++;
        }
        if (g_timings[i].theater >= 0 && g_timings[i].theater < DAAVFX_THEATER_COUNT) {
            s.theater_ms[g_timings[i].theater] += g_timings[i].cost_ms;
            s.theater_count[g_timings[i].theater]++;
        }
    }

    // Parallel time = max of layer_max (in practice, sum of max per parallel group)
    // For simplicity, use max layer cost * layers_completed as approximation
    float max_layer = 0;
    for (int32_t i = 0; i < s.layers_completed && i < DAAVFX_MAX_LAYERS; i++) {
        if (layer_max[i] > max_layer) max_layer = layer_max[i];
    }
    s.parallel_ms = max_layer * s.layers_completed;

    if (s.sequential_ms > 0) {
        s.speedup_pct = ((s.sequential_ms - s.parallel_ms) / s.sequential_ms) * 100.0f;
        if (s.speedup_pct < 0) s.speedup_pct = 0;
    }

    s.total_ms = s.sequential_ms;
    return s;
}

/* ------------------------------------------------------------------ */
/* ggml op mapping                                                    */
/* ------------------------------------------------------------------ */

#include "ggml.h"

int32_t daavfx_op_kind_from_ggml(enum ggml_op op) {
    switch (op) {
        case GGML_OP_MUL_MAT:
        case GGML_OP_MUL_MAT_ID:
            return DAAVFX_OP_MATMUL;
        case GGML_OP_RMS_NORM:
        case GGML_OP_GROUP_NORM:
        case GGML_OP_L2_NORM:
            return DAAVFX_OP_LAYERNORM;
        case GGML_OP_ROPE:
        case GGML_OP_ROPE_BACK:
            return DAAVFX_OP_ROPE;
        case GGML_OP_FLASH_ATTN_EXT:
            return DAAVFX_OP_SOFTMAX;
        default:
            return DAAVFX_OP_MATMUL;
    }
}

/* ------------------------------------------------------------------ */
/* daavile fx: DSpark hidden-state taps                                */
/* ------------------------------------------------------------------ */

#include <stdio.h>

static float     g_dspark_buf[DAAVFX_DSPARK_FLOATS];
static int32_t   g_dspark_tap_layers[DAAVFX_DSPARK_TAPS] = {2, 6, 10, 14, 18};
static int32_t   g_dspark_hidden      = DAAVFX_DSPARK_HIDDEN;
static uint32_t  g_dspark_captured    = 0;   /* bitmask of taps filled this token */
static uint64_t  g_dspark_seq         = 0;
static bool      g_dspark_enabled     = false;

/* live stats for observers (see daavfx_dspark_stats_t) */
static uint64_t  g_dspark_captures    = 0;
static uint64_t  g_dspark_bytes       = 0;
static uint64_t  g_dspark_total_ns    = 0;
static uint64_t  g_dspark_last_ns     = 0;
static float     g_dspark_norms[DAAVFX_DSPARK_TAPS];

void daavfx_dspark_set_enabled(bool enabled) {
    g_dspark_enabled = enabled;
    if (!enabled) { g_dspark_captured = 0; }
}

bool daavfx_dspark_is_enabled(void) {
    return g_dspark_enabled;
}

void daavfx_dspark_configure(const int32_t* tap_layers, int32_t n_taps, int32_t hidden_size) {
    if (!tap_layers || n_taps <= 0 || n_taps > DAAVFX_DSPARK_TAPS) return;
    for (int32_t i = 0; i < n_taps; i++) g_dspark_tap_layers[i] = tap_layers[i];
    for (int32_t i = (int32_t)n_taps; i < DAAVFX_DSPARK_TAPS; i++) g_dspark_tap_layers[i] = -1;
    if (hidden_size > 0) g_dspark_hidden = hidden_size;
    g_dspark_captured = 0;
}

void daavfx_dspark_capture(int32_t layer_index, const void* data, int32_t n_floats) {
    if (!g_dspark_enabled || !data || layer_index < 0) return;

    /* find which tap this layer is */
    int tap = -1;
    for (int i = 0; i < DAAVFX_DSPARK_TAPS; i++) {
        if (g_dspark_tap_layers[i] == layer_index) { tap = i; break; }
    }
    if (tap < 0) return;

#ifdef _WIN32
    LARGE_INTEGER t0, t1, freq;
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&t0);
#endif

    const float* src = (const float*)data;
    float* dst = &g_dspark_buf[tap * g_dspark_hidden];
    int32_t n = n_floats < g_dspark_hidden ? n_floats : g_dspark_hidden;
    memcpy(dst, src, (size_t)n * sizeof(float));
    for (int32_t i = n; i < g_dspark_hidden; i++) dst[i] = 0.0f;  /* zero-pad */

    /* L2 norm of the captured vector: live health signal for observers */
    double sum = 0.0;
    for (int32_t i = 0; i < n; i++) sum += (double)src[i] * (double)src[i];
    g_dspark_norms[tap] = (float)sqrt(sum);

    uint64_t ns = 0;
#ifdef _WIN32
    QueryPerformanceCounter(&t1);
    if (freq.QuadPart > 0) {
        ns = (uint64_t)(((t1.QuadPart - t0.QuadPart) * 1000000000ULL) / freq.QuadPart);
    }
#else
    ns = 0;
#endif
    g_dspark_captures++;
    g_dspark_bytes    += (uint64_t)n * sizeof(float);
    g_dspark_total_ns += ns;
    g_dspark_last_ns   = ns;

    g_dspark_captured |= (1u << tap);

    /* all taps present -> bump sequence so the consumer sees a fresh set */
    if (g_dspark_captured == (1u << DAAVFX_DSPARK_TAPS) - 1u) {
        g_dspark_seq++;
        g_dspark_captured = 0;
    }
}

int32_t daavfx_dspark_read(float* out, int32_t max_floats) {
    if (!out || max_floats < DAAVFX_DSPARK_FLOATS) return 0;
    if (!g_dspark_enabled || g_dspark_seq == 0) return 0;
    memcpy(out, g_dspark_buf, sizeof(g_dspark_buf));
    return DAAVFX_DSPARK_FLOATS;
}

uint64_t daavfx_dspark_seq(void) {
    return g_dspark_seq;
}

void daavfx_dspark_get_stats(daavfx_dspark_stats_t* out) {
    if (!out) return;
    uint32_t epoch = out->epoch;  /* caller owns the seqlock; preserve it */
    out->version  = 1;
    out->enabled  = g_dspark_enabled ? 1u : 0u;
    out->seq      = g_dspark_seq;
    out->captures = g_dspark_captures;
    out->bytes    = g_dspark_bytes;
    out->total_ns = g_dspark_total_ns;
    out->last_ns  = (float)g_dspark_last_ns;
    for (int i = 0; i < DAAVFX_DSPARK_TAPS; i++) {
        out->norms[i] = g_dspark_norms[i];
        out->taps[i]  = g_dspark_tap_layers[i];
    }
    out->hidden = g_dspark_hidden;
    out->epoch  = epoch;
}
