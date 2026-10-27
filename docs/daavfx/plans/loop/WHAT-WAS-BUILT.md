# DAAVILE Harness — What We Built

## The short version

The daavile harness started as a copy of the DeepSeek Harness (dsh). Over three
weeks it became its own thing: the agent runtime for the DAAVILE trading stack,
with its own identity, its own memory system, its own orchestration, and its
own path to self-improvement.

Everything below is shipped and pushed unless marked otherwise.

---

## Identity and surface

- **DAAVILE rebrand**: banner art spells DAAVILE, the hero portrait is the DAA
  wordmark, theme brand `DAAVILE HARNESS`, taglines `RYIUK · DAAVILE HARNESS`.
  All 8 skill stubs + embedded guides rebranded; executables stay
  `orca`/`orca-dev`/`orca-ide`/`ORCA_CLI_COMMAND` (the real staged shims).
- **The daavile profile** (`dsh --profile daavile`): boots the vendored
  Hermes TUI over a loopback WebSocket gateway, registered as a first-class
  ADE terminal surface.
- **The DAAVILE skin**: black canvas (#000000), dark grey structure
  (#2A2A2A), one warm orange accent (#E09A38). The identity skin is served
  with every `gateway.ready` and paints the terminal via OSC-11.
- **GitHub home**: `daavfx/daavile-harness` (private), the ADE fork at
  `daavfx/daavilefx-ade`.

## The Desk layout

- Two-row masthead (bold brand tag over a clipped hairline — the empty-box
  lesson: bordered Boxes render as two-row frames in the vendored ink, so use
  clipped glyph runs).
- WelcomeCard: the DAAVILE wordmark hero (responsive: full wordmark at ≥57
  cols, DAA mark at ≥29, text-only below), brand welcome line, session hint
  (`/sessions to browse and switch`), a clipped session label.
- DeskRail: the fixed right column — SESSION facts (sid, title, sessions,
  tokens, calls), RUNNING rows (roster builders clipped to 3 + hidden
  counter), CONTEXT facts (model, profile, cwd). Fact labels padded to 9
  cells (the `sessions0` → `sessions 0` fix), section headers over clipped
  hairlines, quiet state as a dim `○ quiet` row.
- Composer: opencode-style rounded frame with border-aware cursor drags.

## The OptChat memory system

The recipe: one append-only log per chat, a binary summary tree built by a
cheap model, and a constant-size view — dense near now, coarse in the past —
served as the agent's whole context, with `zoom` to open any line back down
to raw messages. Nothing is ever dropped; the context never grows; the view
is prompt-cache-stable by construction.

**The DAAVILE extension**: every chat is its own infinite **world**
(`memory/<world>/`). The **universe** (`memory/universe/`) is a distinguished
world distilled from the other worlds' coarsest lines — the main brain, where
the operator's decisions, strategies, and facts live. New sessions bootstrap
from the universe view.

### What's shipped

- **The core** (`packages/compaction/optchat/src/`): Taelin's rollback push,
  the binary tree (`node(l,i)` = `id+n`), the fixed due formula
  `(T+1)/2^l - i`, the 128k→64k sawtooth view policy, the per-world store.
  10 specs pin the recipe's guarantees (the incremental due-order merge
  reproduces the push list exactly, t up to 2048).
- **The engine** (`OptChatCompactionEngine`): extends `BasicCompactionEngine`
  — the inherited replay/trigger/region/pricing machinery with the summarizer
  replaced by the world-tree builder. Each compacted region becomes leaf
  lines (512 bytes, one cheap compaction call per message) + due-order merges
  (one call per merge); the returned summary = the whole-conversation view.
  The session's durable log = the recipe's message log; the store carries
  only derived state (tree, view, raw-leaf sidecar, covered-count), all
  rebuildable from the log alone.
- **The zoom tool**: `zoom(id, n)` opens a view line into its two halves;
  `n = 1` gives the message whole from the raw-leaf sidecar. Registered by
  the engine constructor.
- **The universe distiller**: unawaited, post-compaction. The world's
  coarsest lines become universe-world notes on a content-hash dedupe, then
  the universe's own tree grows with the same calls.
- **The composition**: the daavile profile's `compaction-basic` row now
  mounts the OptChat engine. Live boot mounts clean (5.5s, zero activation
  warnings).
- **Honest state**: the mount + zoom registration are proven; the compaction
  path (leaf/merge calls + the view replacement) awaits a real chat crossing
  the pressure threshold — the first daavile session long enough to hit it
  is the acceptance test.

## Fast-boot

The boot went from **12s+ paint** to **~2.9s mount**:

| Fix | What it did |
|---|---|
| The existsSync dragon | The installation-scope BFS stat-ed the same candidate directories once per anchor across the whole dependency closure — 15.7s of existsSync self-time, wall times swinging 2.9–30s with NTFS cache state. `packageDirFromAnchor` now memoizes per resolution run. |
| Defender exclusions | The 45s cold-scan stall after rebuilds (every `open()` pays the scanner on freshly written files). The operator applied exclusions for the harness checkout + DSH_HOME + the compile cache. |
| `NODE_COMPILE_CACHE` | Shipped in both global shims (self-invalidating by source hash, ~0.5–1s warm). |
| The registry (phase 1+2) | The module-source registry (blob + resolve map) — measured zero-delta warm, so it ships **opt-in** (`DSH_REGISTRY_SOURCES=1`). The tooling exists; the lane is closed at its ceiling. |

The remaining ~3s floor = the eager cordis plugin mount + the TUI child
spawn. Next levers: the profile diet (disable unused plugins) or lazy mount.

## Orchestration

- **Host-driven orchestration over direct pipe RPC** (~70× faster than the
  CLI path): the app's `orca_bridge.rs` talks to the engine's named pipe
  directly with the contract envelope, persistent Runs, subscription mailbox.
- **Fleet CLI**: `daavile orchestration fleet --spec <file>` — dispatch a
  whole fleet from one JSON spec. Branched workers get real isolated
  new-child engine worktrees.
- **Watch TUI**: `daavile orchestration watch` — live mission-control frames
  (workerList states + counts, mailbox events rendered + acked).
- **Engine-supervised persona workers**: the cortex-worker shim spawned as
  the worker terminal process, calling the quantum MCP's `cortex_run`, then
  reporting `worker_done` over the engine pipe. The loop is closed:
  shim → 3141 cortex_run → cortex AgentLoop → report → worker_done.
- **Fleet templates**: four named rosters (MQL5 Audit Chain, Quant Research,
  Review Pass, Local Persona Pass) — one click + task tweaks.
- **cortex_run MCP tool + LlmOverrides (seed/grammar)**: the persona
  brain-wire — deterministic repeats for A/B benches, GBNF whole-generation
  constraint.

## Skills and identity

- **daavfx-cli** (renamed from orca-cli): the CLI skill — operate
  DAAVILE-managed worktrees, terminals, repos, automations, the embedded
  browser. Legacy alias `orca-cli` kept.
- All 8 skill stubs + embedded guides rebranded. A legacy guide alias keeps
  old instructions resolving.
- The skills install now points at `https://github.com/daavfx/daavilefx-ade`
  (our repo), not the upstream.
- Resources regenerated (`daavfx-cli@r1`, manifest verify green).

## The ADE fork (vendor/daavilefx)

- **Host MCP injection** (change 11): 29 dashboard tools injected into every
  engine-spawned agent via `DAAVFX_AGENT_MCP_SERVERS` env + a live-tunable
  `agent-mcp-servers.json` file channel.
- **Browser milestone**: the Install skill button resolves to this repo's
  skills (daavfx-cli from daavfx/daavilefx-ade), with DAAVILE-branded guides.
- **Rider fixes**: fleet/watch handlers emit proper RuntimeRpcSuccess
  envelopes; the acp host-MCP helper wraps its readFileSync default;
  tc:cli/node/web all 0.

## The build and delivery pipeline

- **build:cli-bundle**: single-file esbuild bundle of the compiled CLI entry
  (2.36MB), gitignored, wired bundle-first + tsx fallback in the global
  shims.
- **build-cli-registry**: the module-source registry (blob + index) for the
  opt-in serving layer.
- **build-ide-engine.mjs**: the app's beforeDevCommand — builds the engine
  bundle + stages the web client to `public/ide/` (the staleness gate picks
  changed fork sources automatically on the next launch).

## Boot-time provenance

The boot went from 12s+ to ~2.9s across three lanes:

1. **zai-81/82**: the investigation (6,268 module loads, 647 packages,
   CPU-bound 7.4s), the bundle, the resolution-router discovery.
2. **zai-88**: the fresh profile (cold/warm split = Defender first-open
   scans), the compile cache.
3. **zai-91**: the existsSync dragon (the installation-scope probe memo —
   15.7s of self-time eliminated, boot 2.9s quiet / 5-6s typical).

---

## Repository map

| Repo | What it is |
|---|---|
| `daavfx/daavile-harness` | The harness (this repo) — the agent runtime |
| `daavfx/daavilefx-ade` | The ADE fork (the embedded engine) |
| `daavfx/quantum-dashboard-fx` | The Tauri app (Agent · IDE · Quantum) |
| `daavilefx_harness` (local) | This working tree |

## INFLIGHT index (zai-81 → zai-93)

| Row | What |
|---|---|
| zai-81 | Fast-boot investigation + CLI bundle + boot splash |
| zai-82 | The resolution router = the fast-boot optimization target |
| zai-85 | Harness TUI design level-up (wordmark hero, masthead fix) |
| zai-87 | Desk rail polish + session hints |
| zai-88 | Fast-boot profile, cold/warm split (Defender), compile cache |
| zai-89 | Registry phase 1 (opt-in) — recorder, generator, serving layer |
| zai-90 | Registry phase 2 resolve map — measured zero-delta, lane closed |
| zai-91 | The existsSync dragon — installation-scope probe memo |
| zai-92 | OptChat memory core — worlds + universe, clean-room TS port |
| zai-93 | OptChat integration — compaction seam + zoom + universe distiller |

Earlier (daavile-01 → daavile-16): the profile, the TUI port, the gateway,
the identity skin, the Desk layout, the family naming, the GitHub homes.
