/**
 * daavfx_theater_dispatch.c
 *
 * Cheap in-process atomic dispatch reader.
 * Real cross-process SHM can be added later; this keeps the hot path
 * to a single seq-checked struct copy.
 */

#include "daavfx_per_layer_hooks.h"
#include "daavfx_theater_dispatch.h"
#include <string.h>

#ifdef _WIN32
#include <windows.h>
#endif

static daavfx_dispatch_state_t g_dispatch_state;

#ifdef _WIN32
static const char * DAAVFX_SHM_NAME = "Global\\daavfx_dispatch_state";
static HANDLE g_shm_map = NULL;
static daavfx_dispatch_state_t * g_shm_view = NULL;
static bool g_shm_owner = false;
#endif

void daavfx_dispatch_init(void) {
    daavfx_dispatch_state_init(&g_dispatch_state);

#ifdef _WIN32
    /* DaavFX: open/create named shared memory so Rust runtime can observe
     * theater choices written by the C inference hook. */
    g_shm_map = CreateFileMappingA(
        INVALID_HANDLE_VALUE,
        NULL,
        PAGE_READWRITE,
        0,
        sizeof(daavfx_dispatch_state_t),
        DAAVFX_SHM_NAME);
    if (g_shm_map) {
        g_shm_view = (daavfx_dispatch_state_t *)MapViewOfFile(
            g_shm_map,
            FILE_MAP_WRITE,
            0,
            0,
            sizeof(daavfx_dispatch_state_t));
        if (!g_shm_view) {
            CloseHandle(g_shm_map);
            g_shm_map = NULL;
        }
    }
#endif
}

bool daavfx_dispatch_pick(daavfx_dispatch_state_t * state,
    daavfx_op_kind_t op, int32_t layer, daavfx_layer_context_t * ctx,
    daavfx_theater_t * out_theater) {
    (void)op;
    (void)layer;
    (void)ctx;

    daavfx_dispatch_snapshot_t snap;
    if (!daavfx_dispatch_try_read(state, &snap)) {
        return false;
    }

    if (snap.chosen_theater >= 6) {
        return false;
    }

    if (out_theater) {
        *out_theater = (daavfx_theater_t)snap.chosen_theater;
    }
    return true;
}

daavfx_dispatch_state_t * daavfx_dispatch_get_state(void) {
    return &g_dispatch_state;
}

static daavfx_theater_t daavfx_dispatch_fallback(daavfx_op_kind_t op, int32_t layer) {
    (void)layer;

    switch (op) {
        case DAAVFX_OP_MATMUL:
        case DAAVFX_OP_EMBED:
            return DAAVFX_THEATER_CPU;

        case DAAVFX_OP_KV_CACHE:
        case DAAVFX_OP_SAMPLING:
            return DAAVFX_THEATER_RAM;

        case DAAVFX_OP_SOFTMAX:
        case DAAVFX_OP_LAYERNORM:
        case DAAVFX_OP_ROPE:
        default:
            return DAAVFX_THEATER_CPU;
    }
}

daavfx_theater_t daavfx_hooks_resolve_theater(daavfx_dispatch_state_t * state,
    daavfx_op_kind_t op, int32_t layer) {
    daavfx_theater_t chosen = DAAVFX_THEATER_CPU;
    if (state && daavfx_dispatch_pick(state, op, layer, NULL, &chosen)) {
        return chosen;
    }
    return daavfx_dispatch_fallback(op, layer);
}

void daavfx_dispatch_set_snapshot(
    daavfx_dispatch_state_t * state,
    uint32_t chosen_theater,
    uint32_t chosen_op,
    float confidence,
    float thermal_pressure,
    float vram_pressure,
    const char * rationale) {
    if (!state) return;
    daavfx_dispatch_write(state, chosen_theater, chosen_op,
                          confidence, thermal_pressure, vram_pressure, rationale);

#ifdef _WIN32
    /* Mirror to named SHM so Rust runtime can observe theater decisions. */
    if (g_shm_view) {
        daavfx_dispatch_write(g_shm_view, chosen_theater, chosen_op,
                              confidence, thermal_pressure, vram_pressure, rationale);
    }
#endif
}

daavfx_dispatch_state_t * daavfx_dispatch_state_get(void) {
    return &g_dispatch_state;
}
