# HEX DRIFT LEDGER — upstream watch for anomalyco/hex

Verified 2026-10-31. Hex is not forked by us — we consume it at a boundary
(SDK / CLI), so this is an upstream-watch, not a fork-drift. Same discipline as
the orca drift ledger: a script, a baseline, a routine.

## The watch

```
pwsh scripts/daavfx/check-hex-drift.ps1            # local refs, instant
pwsh scripts/daavfx/check-hex-drift.ps1 -Fetch     # refresh upstream first
pwsh scripts/daavfx/check-hex-drift.ps1 -Log       # append a machine row
```

Run it on the same cadence as the orca check (upstream ships often) and before
any integration decision. `HEX-DRIFT-LOG.jsonl` is the machine record.

## Baseline

| | |
|---|---|
| Clone | `shared/hex-original` (depth 1; deepen with `-Fetch` to 50) |
| Upstream HEAD | `aa3059a` — "Fix #624: cancel dictation shortcut on KDE Wayland (#628)" |
| Last recorded SHA: `aa3059a` (2026-10-31, 14:05 UTC) | |
| Reachable tags at baseline | none (shallow clone; `-Fetch` pulls tags) |
| License | MIT (they do not accept outside PRs — the repo is a product, not a library) |
| Windows posture | beta, x64 + ARM64, not code-signed, **no packaged native helper yet** (SDK consumers must spawn an installed `hex service --embedded`) |

## Why we track it

Hex is a candidate input path for voice-into-the-agent-chat (decision recorded in
`HEX-INTEGRATION.md`). Two upstream facts drive our watch list:

1. The Windows helper story ("no packaged helper yet") is the one thing that
   decides whether in-app integration is a spawn-an-installer job or a
   dependency job. Every release note matters until it lands.
2. Their "Send to…" targets a running **OpenCode service** by protocol. If that
   protocol ever aligns with our engine's surface, an annotate-to-session path
   opens for our fleet. Watch their `docs/specs/` changes.

## Known upstream direction (from the README at baseline)

Local-first dictation (Rust, on-device Whisper/Parakeat), streaming on Vulkan
(~100ms on Windows x64), Annotate (screen-record + draw + talk → agent),
TypeScript SDK (`@kitlangton/hex`, host-owns-recording contract), CLI
(`hex history`, `hex annotate send`, read-only JSON), custom transformations in
an embedded JS engine.
