# DAAVFX Worktree Debug Helpers

This directory contains one-off PowerShell and cmd helpers that were
used during the **Tranche 15B** worktree build path investigation
(MASM blocker resolution, cmake detection, PE section comparison).

They are NOT part of the build pipeline. They are NOT called by
`build_worktree.cmd` or `build_worktree.ps1`. They are kept here so
future debugging has the same tools available without re-inventing
them.

## When to use these

If a Tranche 16+ build fails, or if a PE section comparison is
needed, or if cmake is misbehaving in a script context, use these.

## What each script does

| Script | Purpose | When to use |
|--------|---------|-------------|
| `check_asm.cmd` | Quick check that `ml64.exe` is reachable on PATH after VsDevCmd activation | Before kicking off a full build, to fail fast on missing MASM |
| `compare_sections.ps1` | Section-by-section SHA256 comparison of two PE files | After a build, to prove structural parity with live (or with a prior build) |
| `diff_cmake.ps1` | Diff two `CMakeCache.txt` files line-by-line | When the worktree build's cmake config drifts from live's, to find the divergence |
| `pe_info.ps1` | Extract PE header metadata: timestamp, machine, sections summary | When you need to know WHEN a binary was linked, or to debug a "wrong architecture" error |
| `pe_sections.ps1` | Print all PE section names + sizes (no SHA) | Quick visual diff of which sections differ between two builds |
| `debug_pe.ps1` | Lower-level PE parser, used to find the bug in an earlier version of `pe_sections.ps1` | When `pe_sections.ps1` returns wrong sizes (e.g. num_sections reads 0) |
| `debug2.ps1` | Successor to `debug_pe.ps1`, used to find the bug where `numSections` was read from the wrong offset | Same — historical artifact, kept for context |

## Historical note

`pe_sections.ps1` was the first attempt. It had a bug where it read
`numSections` from `peOffset + 2` instead of `peOffset + 6` (the
PE\0\0 signature is 4 bytes at the start of the NT header, then
Machine, then NumberOfSections). The fix is in `compare_sections.ps1`
which uses the correct offsets. `debug_pe.ps1` and `debug2.ps1` were
used to diagnose the bug. All three are kept for posterity.

## Output logs (NOT in this directory)

These logs are produced by the helpers and live at the **worktree
root**:

- `build_worktree.log` — full build log from the most recent
  `build_worktree.ps1` invocation
- `section_compare.log` — output of `compare_sections.ps1` for the
  live-vs-worktree structural parity proof

## How to invoke

```powershell
# Make sure the helper is runnable. From the worktree root:
.\daavfx_helpers\check_asm.cmd

# PE info on a specific binary:
powershell -ExecutionPolicy Bypass -File .\daavfx_helpers\pe_info.ps1 -Path "build\bin\Release\llama-server.exe"

# Section compare (live vs worktree):
powershell -ExecutionPolicy Bypass -File .\daavfx_helpers\compare_sections.ps1 -LivePath "..\..\shared\llama.cpp-atomic\build_vulkan\bin\Release\llama-server.exe" -WorktreePath "build\bin\Release\llama-server.exe"

# Cmake cache diff:
powershell -ExecutionPolicy Bypass -File .\daavfx_helpers\diff_cmake.ps1 -A "build\CMakeCache.txt" -B "..\..\shared\llama.cpp-atomic\build_vulkan\CMakeCache.txt"
```

## Cleanup rule

If a helper is no longer needed (e.g. `debug2.ps1` and `debug_pe.ps1`
are historical only), prefer to **leave them** in this directory
with a one-line note rather than delete. Future coders investigating
PE parsing bugs will thank you.
