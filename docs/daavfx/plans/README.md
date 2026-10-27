# plans/ - the design lanes (one index, one primitive table)

Date: 2026-10-27. Rule: not in this index, not a lane. A new plan starts
with a folder here and a row below, and its refuter checks PRIMITIVES.md
before scoring grounding.

| Lane | Holds | Pair |
|---|---|---|
| `context/` | the context/compaction plan (the transcribed brainstorm, scored candidates, the roast, the synthesis) | BRAINSTORM -> PROPOSAL -> REFUTATION -> SYNTHESIS |
| `vault/` | the agent backend / memory-vault plan (isolation, per-surface vaults, the human section, rank law) | AUDIT -> PROPOSAL -> REFUTATION -> NOVEL-ANGLE |
| `loop/` | the harness self-improvement plan: onboarding, the Lane-A eval contract, Harness^2/Athanor | (the repo-side contract) |

| Record | Holds |
|---|---|
| `PRIMITIVES.md` | the one primitive table; every plan cites a row, not a fresh read |
| `../README.md` | the docs/daavfx front door |

## Rules

1. A plan is a PROPOSAL + its REFUTATION + the SYNTHESIS that survives the
   roast. Scoring without a refuter is prose.
2. `[PRIOR - suspect]` on every number not reproducible from a file or a
   transcript. Numbers transcribed twice (paper -> coder -> plan) are priors.
3. Design lives here; implementation lands in the owning repo and follows
   that repo's gates. The harness repo's rules (per-file 100% coverage,
   keyless snapshots, doc-sync) reject a design folder; the app's Track A
   boundary rejects a context-lane edit to `main.rs`/`premium_backend` or
   `src-tauri/src/bin/`.
4. No content is deleted on a merge; folders move and the index records them.
