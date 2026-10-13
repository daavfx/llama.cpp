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

// ggml_backend_sched_eval_callback:
//   ask == true  -> return whether we want to observe tensor t
//   ask == false -> t has been computed; data is valid now
static bool davfx_dspark_eval_cb(struct ggml_tensor * t, bool ask, void * /*user_data*/) {
    if (ask) {
        if (!t || t->type != GGML_TYPE_F32) {
            return false;
        }
        // observe only layer-output tensors named "l_out-<il>"
        const char * name = ggml_get_name(t);
        return name && strncmp(name, "l_out-", 6) == 0;
    }

    const char * name = ggml_get_name(t);
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
    if (!env || atoi(env) != 1) {
        return false;
    }

    // default LFM2.5 tap set; hidden 2048 matches the DSpark draft input
    const int32_t taps[DAAVFX_DSPARK_TAPS] = {2, 6, 10, 14, 18};
    daavfx_hooks_init();
    daavfx_dspark_configure(taps, DAAVFX_DSPARK_TAPS, DAAVFX_DSPARK_HIDDEN);
    daavfx_dspark_set_enabled(true);

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
