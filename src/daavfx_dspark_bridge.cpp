// daavile fx: DSpark hidden-tap bridge implementation.
// See daavfx_dspark_bridge.h. Env gate: DAAVFX_DSPARK_TAPS=1.

#include "daavfx_dspark_bridge.h"
#include "daavfx_per_layer_hooks.h"

#include "ggml.h"
#include "ggml-backend.h"

#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <windows.h>

static bool g_bridge_installed = false;

// lab observability: tap stats published to session-local shared memory.
// The Rust lab (crates/llab) maps "Local\daavfx_dspark_<pid>" read-only and
// shows tap seq / norms / capture cost live. Epoch = seqlock (odd = writing).
static HANDLE g_dspark_map = NULL;
static daavfx_dspark_stats_t * g_dspark_shm = NULL;

static void dspark_shm_init(void) {
    if (g_dspark_shm) return;
    char name[64];
    snprintf(name, sizeof(name), "Local\\daavfx_dspark_%lu", (unsigned long) GetCurrentProcessId());
    g_dspark_map = CreateFileMappingA(INVALID_HANDLE_VALUE, NULL, PAGE_READWRITE, 0,
                                      (DWORD) sizeof(daavfx_dspark_stats_t), name);
    if (!g_dspark_map) return;
    g_dspark_shm = (daavfx_dspark_stats_t *) MapViewOfFile(g_dspark_map, FILE_MAP_ALL_ACCESS, 0, 0,
                                                           sizeof(daavfx_dspark_stats_t));
    if (g_dspark_shm) {
        memset(g_dspark_shm, 0, sizeof(*g_dspark_shm));
        g_dspark_shm->version = 1;
    }
}

static void dspark_shm_publish(void) {
    if (!g_dspark_shm) return;
    daavfx_dspark_stats_t s;
    memset(&s, 0, sizeof(s));
    daavfx_dspark_get_stats(&s);
    g_dspark_shm->epoch++;  /* odd: write in progress */
    g_dspark_shm->version  = s.version;
    g_dspark_shm->enabled  = s.enabled;
    g_dspark_shm->seq      = s.seq;
    g_dspark_shm->captures = s.captures;
    g_dspark_shm->bytes    = s.bytes;
    g_dspark_shm->total_ns = s.total_ns;
    g_dspark_shm->last_ns  = s.last_ns;
    memcpy(g_dspark_shm->norms, s.norms, sizeof(s.norms));
    memcpy(g_dspark_shm->taps,  s.taps,  sizeof(s.taps));
    g_dspark_shm->hidden   = s.hidden;
    g_dspark_shm->epoch++;  /* even: stable snapshot */
}

// ---- Router histogram logger (Phase 3b) --------------------------------
// Env gate: DAAVFX_ROUTER_LOG=<csv path>. Captures ffn_moe_topk-<il>
// (selected expert ids, I32) and ffn_moe_probs-<il> (unbiased weights
// basis, F32) from the sched eval callback and aggregates per
// (layer, expert): selection count, selected-gating mass, total prob
// mass. Snapshot-rewrites the CSV every ROUTER_FLUSH_TOKENS prob tokens
// and at exit; TerminateProcess loses only the last partial window.
static char       g_router_log_path[260] = {0};
static uint64_t   g_router_count[24][32];
static double     g_router_sel_mass[24][32];
static double     g_router_all_mass[24][32];
static uint64_t   g_router_tokens[24];
static float    * g_router_last_probs[24];
static int64_t    g_router_last_ntok[24];
static uint64_t   g_router_prob_tokens_total = 0;

#define ROUTER_FLUSH_TOKENS 256

static void router_log_flush(void) {
    if (!g_router_log_path[0]) return;
    FILE * f = fopen(g_router_log_path, "w");
    if (!f) return;
    fprintf(f, "layer,expert,selected,mass_selected,mass_all,tokens\n");
    for (int il = 0; il < 24; ++il) {
        if (!g_router_tokens[il]) continue;
        for (int e = 0; e < 32; ++e) {
            fprintf(f, "%d,%d,%llu,%.6f,%.6f,%llu\n", il, e,
                    (unsigned long long) g_router_count[il][e],
                    g_router_sel_mass[il][e],
                    g_router_all_mass[il][e],
                    (unsigned long long) g_router_tokens[il]);
        }
    }
    fclose(f);
}

static void router_log_capture_probs(int il, struct ggml_tensor * t) {
    const int64_t ntok = t->ne[1];
    const int W = (int) t->ne[0];   // expert width: 32 baseline, K_phys on mutants
    if (il >= 24 || W < 1 || W > 32 || !ggml_is_contiguous(t)) return;
    free(g_router_last_probs[il]);
    g_router_last_probs[il] = (float *) malloc((size_t) W * ntok * sizeof(float));
    if (!g_router_last_probs[il]) { g_router_last_ntok[il] = 0; return; }
    memcpy(g_router_last_probs[il], t->data, (size_t) W * ntok * sizeof(float));
    g_router_last_ntok[il] = ntok;
    const float * p = g_router_last_probs[il];
    for (int64_t tok = 0; tok < ntok; ++tok) {
        g_router_tokens[il] += 1;
        for (int e = 0; e < W; ++e) g_router_all_mass[il][e] += p[e + tok * W];
    }
    g_router_prob_tokens_total += (uint64_t) ntok;
    if (g_router_prob_tokens_total / ROUTER_FLUSH_TOKENS !=
        (g_router_prob_tokens_total - (uint64_t) ntok) / ROUTER_FLUSH_TOKENS) {
        router_log_flush();
    }
}

static void router_log_capture_topk(int il, struct ggml_tensor * t) {
    if (il >= 24) return;
    const float * probs = g_router_last_probs[il];
    const int64_t ntok_probs = g_router_last_ntok[il];
    const int64_t ntok = t->ne[1];
    if (!ggml_is_contiguous(t)) return;
    // ggml_argsort_top_k emits I64 indices in this tree; accept I32 too
    const int is64 = (t->type == GGML_TYPE_I64);
    for (int64_t tok = 0; tok < ntok; ++tok) {
        for (int64_t k = 0; k < t->ne[0]; ++k) {
            const int64_t e64 = is64 ? ((const int64_t *) t->data)[k + tok * t->ne[0]]
                                     : (int64_t)((const int32_t *) t->data)[k + tok * t->ne[0]];
            if (e64 >= 0 && e64 < 32) {
                const int e = (int) e64;
                g_router_count[il][e] += 1;
                if (probs && tok < ntok_probs) {
                    g_router_sel_mass[il][e] += probs[e + tok * 32];
                }
            }
        }
    }
}

// ggml_backend_sched_eval_callback:
//   ask == true  -> return whether we want to observe tensor t
//   ask == false -> t has been computed; data is valid now
static bool davfx_dspark_eval_cb(struct ggml_tensor * t, bool ask, void * /*user_data*/) {
    const char * name = ggml_get_name(t);
    if (g_router_log_path[0] && name && ask) {
        if (strncmp(name, "ffn_moe_topk-", 13) == 0) {
            return (t->type == GGML_TYPE_I64 || t->type == GGML_TYPE_I32) &&
                   t->buffer && ggml_backend_buffer_is_host(t->buffer);
        }
        if (strncmp(name, "ffn_moe_probs-", 14) == 0) {
            return t->type == GGML_TYPE_F32 && t->buffer && ggml_backend_buffer_is_host(t->buffer);
        }
    }
    if (ask) {
        if (!t || t->type != GGML_TYPE_F32) {
            return false;
        }
        // observe only layer-output tensors named "l_out-<il>"
        return name && strncmp(name, "l_out-", 6) == 0;
    }

    if (g_router_log_path[0] && name) {
        if (strncmp(name, "ffn_moe_probs-", 14) == 0 && t->type == GGML_TYPE_F32) {
            router_log_capture_probs(atoi(name + 14), t);
            return true;
        }
        if (strncmp(name, "ffn_moe_topk-", 13) == 0 && t->type == GGML_TYPE_I32) {
            router_log_capture_topk(atoi(name + 13), t);
            return true;
        }
    }
    if (!name || strncmp(name, "l_out-", 6) != 0) {
        return true;
    }
    const int il = atoi(name + 6);
    if (!ggml_is_contiguous(t)) {
        return true;
    }
    // daavile fx: capture into the hook ring buffer; hidden size from ne[0].
    // v1: host-resident tensors only — synchronous D2H inside eval_cb can
    // deadlock the sched pipeline; device taps need an async readback (ticket).
    ggml_backend_buffer_t buf = t->buffer;
    if (buf && ggml_backend_buffer_is_host(buf)) {
        daavfx_dspark_capture(il, t->data, (int32_t) t->ne[0]);
    }
    dspark_shm_publish();
    return true;
}

bool daavfx_dspark_try_install(llama_cparams & cparams) {
    const char * env = getenv("DAAVFX_DSPARK_TAPS");
    const char * rlog = getenv("DAAVFX_ROUTER_LOG");
    const bool want_spark = env && atoi(env) == 1;
    const bool want_router = rlog && rlog[0];
    if (!want_spark && !want_router) {
        return false;
    }
    if (want_router) {
        strncpy(g_router_log_path, rlog, sizeof(g_router_log_path) - 1);
        g_router_log_path[sizeof(g_router_log_path) - 1] = 0;
        atexit(router_log_flush);
        fprintf(stderr, "%s: router histogram logger -> %s\n", __func__, g_router_log_path);
    }
    if (want_spark) {
    // default LFM2.5 tap set; hidden 2048 matches the DSpark draft input
    const int32_t taps[DAAVFX_DSPARK_TAPS] = {2, 6, 10, 14, 18};
    daavfx_hooks_init();
    daavfx_dspark_configure(taps, DAAVFX_DSPARK_TAPS, DAAVFX_DSPARK_HIDDEN);
    daavfx_dspark_set_enabled(true);
    }

    // daavfx: register measured device throughputs for theater dispatch
    daavfx_dispatch_register_device(DAAVFX_THEATER_CPU,      18.32f);
    daavfx_dispatch_register_device(DAAVFX_THEATER_IGPU,     18.45f);
    daavfx_dispatch_register_device(DAAVFX_THEATER_DGPU,      7.20f);
    daavfx_dispatch_set_thermal(DAAVFX_THEATER_DGPU, 1.00f);  // GTX 1650 4GB: hot/limited

    /* DaavFX AMD APU profile: auto-tune for Vega/RDNA integrated graphics.
     * - batch/parallelism: larger batches improve GPU utilization
     * - cache-ram: enable prompt cache to avoid iGPU memory thrash
     * - ngl: all-offload ceiling for layer split
     */
    {
        bool amd_igpu_found = false;
        for (size_t i = 0; i < ggml_backend_dev_count(); ++i) {
            auto * dev = ggml_backend_dev_get(i);
            if (!dev) continue;
            auto dtype = ggml_backend_dev_type(dev);
            if (dtype != GGML_BACKEND_DEVICE_TYPE_IGPU) continue;

            const char * name = ggml_backend_dev_name(dev);
            const char * desc = ggml_backend_dev_description(dev);
            bool is_amd = (name && strstr(name, "AMD")) || (desc && strstr(desc, "AMD"));
            if (is_amd) {
                amd_igpu_found = true;
                break;
            }
        }

        if (amd_igpu_found) {
            daavfx_hooks_set_amd_profile(true);
            daavfx_hooks_set_batch(2048, 512);        // batch/parallelism tuning
            daavfx_hooks_set_cache_ram(4096);          // cache-aware: 4KB prompt cache
            daavfx_dispatch_register_device(DAAVFX_THEATER_RAM_STORAGE, 14.53f);  // measured CPU RAM t/s

            /* Real thermal feedback: sample CPU busy fraction and derive thermal pressure.
             * Vega 7 UMA: high CPU load correlates with iGPU thermal throttling. */
            {
                FILETIME idle, kernel, user;
                if (GetSystemTimes(&idle, &kernel, &user)) {
                    ULARGE_INTEGER idle_u, kernel_u, user_u;
                    idle_u.LowPart = idle.dwLowDateTime; idle_u.HighPart = idle.dwHighDateTime;
                    kernel_u.LowPart = kernel.dwLowDateTime; kernel_u.HighPart = kernel.dwHighDateTime;
                    user_u.LowPart = user.dwLowDateTime; user_u.HighPart = user.dwHighDateTime;
                    ULONGLONG total = (kernel_u.QuadPart - idle_u.QuadPart) + user_u.QuadPart;
                    float cpu_busy = total > 0 ? (float)((user_u.QuadPart) / (double)total) : 0.0f;
                    float thermal = cpu_busy > 0.85f ? 0.75f : cpu_busy * 0.5f;
                    daavfx_dispatch_set_thermal(DAAVFX_THEATER_IGPU, thermal);
                    daavfx_hooks_set_thermal_pressure(thermal);
                }
            }

            fprintf(stderr, "%s: DaavFX AMD APU profile enabled (Vega/RDNA iGPU)\n", __func__);
        }
    }

    cparams.cb_eval           = davfx_dspark_eval_cb;
    cparams.cb_eval_user_data = nullptr;
    g_bridge_installed        = true;
    dspark_shm_init();

    fprintf(stderr, "%s: daavile fx DSpark taps + theater dispatch installed\n", __func__);
    fprintf(stderr, "%s: devices: CPU=%.2f t/s, iGPU=%.2f t/s, dGPU=%.2f t/s\n",
            __func__, 18.32f, 18.45f, 7.20f);
    return true;
}

bool daavfx_dspark_bridge_enabled() {
    return g_bridge_installed && daavfx_dspark_is_enabled();
}

uint64_t daavfx_dspark_bridge_seq() {
    return daavfx_dspark_seq();
}

int32_t daavfx_dspark_bridge_read(float * out, int32_t max_floats) {
    return daavfx_dspark_read(out, max_floats);
}
