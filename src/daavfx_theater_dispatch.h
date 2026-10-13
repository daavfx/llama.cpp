#ifndef DAAVFX_THEATER_DISPATCH_H
#define DAAVFX_THEATER_DISPATCH_H

#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdlib.h>
#include "daavfx_per_layer_hooks.h"

#ifdef __cplusplus
extern "C" {
#endif

#define DAAVFX_DISPATCH_VERSION 1
#define DAAVFX_DISPATCH_RATIONALE_MAX 120

typedef struct {
    uint32_t version;
    uint32_t seq;
    uint32_t chosen_theater;
    uint32_t chosen_op;
    float    confidence;
    float    thermal_pressure;
    float    vram_pressure;
    char     rationale[DAAVFX_DISPATCH_RATIONALE_MAX];
} daavfx_dispatch_snapshot_t;

typedef struct {
    daavfx_dispatch_snapshot_t snapshot;
    volatile uint32_t writer_seq;
    volatile uint32_t reader_seq;
} daavfx_dispatch_state_t;

static inline void daavfx_dispatch_state_init(daavfx_dispatch_state_t * state) {
    memset(state, 0, sizeof(*state));
    state->snapshot.version = DAAVFX_DISPATCH_VERSION;
    state->writer_seq = 0;
    state->reader_seq = 0;
}

static inline bool daavfx_dispatch_try_read(const daavfx_dispatch_state_t * state,
    daavfx_dispatch_snapshot_t * out) {
    uint32_t w = ((const volatile uint32_t *)&state->writer_seq)[0];
    uint32_t r = ((const volatile uint32_t *)&state->reader_seq)[0];
    if (w == r) return false;
    memcpy(out, &state->snapshot, sizeof(*out));
    ((volatile uint32_t *)&state->reader_seq)[0] = w;
    return true;
}

static inline void daavfx_dispatch_write(daavfx_dispatch_state_t * state,
    uint32_t chosen_theater,
    uint32_t chosen_op,
    float confidence,
    float thermal_pressure,
    float vram_pressure,
    const char * rationale) {
    daavfx_dispatch_snapshot_t snap;
    memset(&snap, 0, sizeof(snap));
    snap.version = DAAVFX_DISPATCH_VERSION;
    snap.seq = state->writer_seq + 1;
    snap.chosen_theater = chosen_theater;
    snap.chosen_op = chosen_op;
    snap.confidence = confidence;
    snap.thermal_pressure = thermal_pressure;
    snap.vram_pressure = vram_pressure;
    if (rationale) {
        size_t len = strlen(rationale);
        if (len >= sizeof(snap.rationale)) len = sizeof(snap.rationale) - 1;
        memcpy(snap.rationale, rationale, len);
        snap.rationale[len] = 0;
    }

    ((volatile uint32_t *)&state->reader_seq)[0];
    memcpy(&state->snapshot, &snap, sizeof(snap));
    ((volatile uint32_t *)&state->writer_seq)[0] = snap.seq;
}

/* DaavFX: Rust SHM publisher bridge.
 * Declared here so C code can publish theater decisions to the Rust
 * runtime via the same `Global\\daavfx_dispatch_state` named shared memory.
 */
void daavfx_dispatch_shm_publish(
    uint32_t chosen_theater,
    uint32_t chosen_op,
    float    confidence,
    float    thermal_pressure,
    float    vram_pressure,
    const char * rationale);

#ifdef __cplusplus
}
#endif

#endif
