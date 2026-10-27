# daavfx_dspark shared-memory wire format (v1)

When a llama.cpp process from this fork runs with `DAAVFX_DSPARK_TAPS=1`, the
bridge creates a session-local named shared memory section:

```
Local\daavfx_dspark_<pid>          (pid = the llama process id, decimal)
```

Size = `sizeof(daavfx_dspark_stats_t)` = **96 bytes**. Layout is fixed by
`src/daavfx_per_layer_hooks.h`; mirror it exactly in consumers.

## Struct (C layout, natural alignment)

```c
typedef struct {
    uint32_t version;                       /* = 1 */
    uint32_t enabled;                       /* 0/1, taps active */
    uint64_t seq;                           /* full 5-tap sets captured since start */
    uint64_t captures;                      /* per-tap captures (seq*5 when all taps hit) */
    uint64_t bytes;                         /* floats copied into the ring */
    uint64_t total_ns;                      /* total time inside capture (QPC) */
    float    norms[DAAVFX_DSPARK_TAPS];     /* last L2 norm per tap (5 entries) */
    float    last_ns;                       /* last single capture duration */
    int32_t  taps[DAAVFX_DSPARK_TAPS];      /* configured layer indices, default {2,6,10,14,18} */
    int32_t  hidden;                        /* hidden size, default 2048 */
    uint32_t epoch;                         /* seqlock: see below */
    uint32_t _pad;
} daavfx_dspark_stats_t;
```

Byte offsets: version 0, enabled 4, seq 8, captures 16, bytes 24, total_ns 32,
norms 40, last_ns 60, taps 64, hidden 84, epoch 88, pad 92.

## Read protocol (seqlock)

The writer increments `epoch` **before** updating fields (odd value) and again
**after** (even value). A reader must:

1. read `epoch`; if odd, retry
2. read the whole struct
3. read `epoch` again; accept only if unchanged and even

## Rust reference reader (as used by the llab dashboard)

```rust
#[repr(C)]
#[derive(Clone, Copy, Default)]
struct DsparkStats {
    version: u32, enabled: u32,
    seq: u64, captures: u64, bytes: u64, total_ns: u64,
    norms: [f32; 5], last_ns: f32,
    taps: [i32; 5], hidden: i32,
    epoch: u32, _pad: u32,
}

// kernel32 FFI: OpenFileMappingW(FILE_MAP_READ=4, ..), MapViewOfFile(..),
// read_volatile on the struct, UnmapViewOfFile, CloseHandle.
```

## Semantics

- `seq` bumps only when all 5 taps have been captured for one token step --
  a stable "fresh full snapshot" signal. The in-process ring buffer
  (`daavfx_dspark_read`) serves the same guarantee.
- `norms[i]` is the L2 norm of the **last** capture written for tap i; it
  updates per token. Use it as a liveness/health signal (e.g. watch for
  collapse to 0 = dead layer, or explosion = instability).
- The mapping persists while the process lives. After process exit the name
  disappears; readers should treat open-failure as "server not running".
- The section is `Local\` (per login session): no privileges required, visible
  to any process in the same session.

## Stability

- `version` guards the layout; consumers must refuse to interpret a section
  whose `version` they don't know.
- Field additions bump `version`; do not reorder existing fields within a
  version.
