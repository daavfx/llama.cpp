# HEX INTEGRATION DECISION - anomalyco/hex vs the orca mod and the agent chat

Date: 2026-10-31. Method: feasibility pass over the public repo + the app's
existing lanes (read-only, nothing installed), mirroring the orca-drift
discipline. ASCII only; unverified numbers are tagged `[PRIOR - suspect]`.

## What Hex is (verified from the repo + SDK README)

Local-first voice dictation in Rust. Hold a key, speak, release; on-device
transcription (Whisper / Parakeet), paste into the focused app. macOS stable,
Windows + Linux betas. Three integration surfaces:

| Surface | Contract (verified from the SDK README) |
|---|---|
| SDK `create({ command: [".../hex-service", "service", "--embedded"], model })` | Host owns recording, permission, settings, and what happens to the text; Hex owns model prep + inference. Helper runs as a **direct child process**, bearer token over a child pipe, authenticated loopback. Host encodes PCM WAV. Never expose the token to renderer/web content. |
| SDK `connect()` | Reuse the **running Hex desktop app's** mic + engine. Desktop capture is macOS-only; elsewhere transcription + live streams work without capture. |
| CLI | `hex history --since 3d --json`, `hex annotate send` - read-only queries and terminal sends. |

Explicit non-goals at baseline: no packaged native helper yet (Windows
consumers must supply `command: ["hex", "service", "--embedded"]` with an
installed Hex), desktop capture is macOS-only, outside PRs are not accepted.

## What we already have (the reuse-first finding, verified on disk)

The Quantum app **already runs a real local voice lane**:

- `src-tauri/premium_backend/src/voice_commands.rs` - R6 voice: cpal mic capture
  (16 kHz mono WAV) + transcription, over the shared `daavfx-voice` crate
  (whisper-cli). Its own header states the in-process engine paths "used by the
  chat" live here.
- `src-tauri/premium_backend/src/speech/mod.rs` - the file/CLI-level commands;
  the mock field is documented as replaced (real capture, real transcribe, real
  Piper TTS).
- Posture: **off by default**; settings exist (`DAAVFX_WHISPER_MODEL`,
  `DAAVFX_PIPER_MODEL`).
- Frontend already references speech settings in the premium Settings divisions.

So the app is not missing local dictation. It has it, off, unproven end-to-end
in the chat.

## The decision

**Orca mod (daavilefx-ade): NO.**
Hex is a standalone product, not an embeddable engine for the fork. The only
mod-adjacent path is Hex's "Send to...", which targets a running OpenCode service
by protocol - `[PRIOR - suspect]` whether our orcad surface speaks that exact
contract (needs their `docs/specs/` + a live probe, not a guess). Nothing of Hex
belongs in the mod's source, and nothing of ours in theirs.

**Agent chat (Quantum app): YES - but in this order.**

1. **First: prove the existing lane.** Wire `voice_commands` (or the chat's
   existing call site) to the agent chat input, enable it, and measure on this
   machine (latency, accuracy, the whisper-cli path). Cost: small. If it works,
   Hex is optional forever.
2. **Then, only if the existing lane disappoints: Hex as the engine behind the
   same seam.** The SDK's contract is built for exactly this - host (our Rust
   main process) owns recording and the result lands wherever we choose; the
   app already owns both halves (cpal capture + a WAV producer). The seam is
   the same one the existing lane uses, so swapping the transcriber is a
   seam-level change, not a rewrite. Hex adds streaming (~100 ms on Vulkan
   x64 `[PRIOR - suspect]` on this GPU) and Annotate; it costs the Windows
   helper dependency.
3. **Global hotkey / dictation-into-any-app: Hex standalone, no integration.**
   If we want dictate-anywhere at the OS level, install Hex's Windows beta
   beside the app; the app keeps only its in-app lane. No code.

**Both?** No. One lane, one seam; the mod stays clean.

## What this costs us (the tracking, done)

Same treatment as orca: `shared/hex-original` (the upstream clone) +
`scripts/daavfx/check-hex-drift.ps1` (upstream-watch: new commits, releases,
notable changes since our recorded SHA) + this ledger (`HEX-DRIFT.md` +
`HEX-DRIFT-LOG.jsonl`). We do not fork hex, so "how behind" is replaced by
"what moved upstream since we last looked".

## Next actions (in order)

1. Read `docs/specs/local-transcription-service.md` upstream (the wire protocol)
   - closes the `[PRIOR - suspect]` on the "Send to..." protocol question.
2. Spike the existing lane into the chat (one settings toggle, one chat input
   call site), measure it here.
3. Only on evidence: Hex SDK behind the seam (Rust main spawns
   `hex service --embedded`, host encodes WAV, token never crosses the bridge).
4. Keep the watch routine; every integration decision re-checks it first.
