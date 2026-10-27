# plans/vault/ - audit, proposal, refutation, and the novel angle

Date: 2026-10-26. Author: opencode-zai (the coder lane, at the operator's
request: "check the backend yourself, use the novel skill, audit the problem,
propose, then spawn a refuter").

Scope: the agent/skills/AGENTS.md/souls backend that the DAAVILE app + Orca
ADE will own, replacing the shared flat-file opencode model for OUR surfaces.
The original `C:\Users\neto_\.config\opencode` stays untouched (operator
ruling); this is the design for ours.

Method: the `novel` skill's RAG discipline (grounded citations, assumption
inversion, safety containment, dual-axis scoring), applied to the architecture
itself rather than to kernels.

## Read in this order

| File | Holds |
|---|---|
| `AUDIT.md` | What the real backend is, verified on disk; the isolation problem; every cited fact |
| `PROPOSAL.md` | The candidate solutions with the novel scoring (K1: skills-as-worlds, 620) |
| `REFUTATION.md` | The hired roaster's disagreement: four load-bearing premises false, on-disk receipts |
| `NOVEL-ANGLE.md` | The synthesis: the ledgers ARE the log, the vault is the read model; the build plan |

## The ground rules this design must satisfy

1. The original opencode config is untouched and keeps its own brain.
2. Per-surface vaults (the app and Orca each own one), never a shared brain.
3. Mini-vaults inside a vault, plus a HUMAN section that agents may read but
   never write - enforced by structure, not by prose.
4. Every claim in this folder cites a file on disk. Unverified claims are
   tagged `[PRIOR - suspect]`.

## Status

Written, not committed to any repo that requires per-action approval. The
app-lane docs folder (`../app-lane/`) is the sibling record of what already
shipped in the transport/UI lanes; this folder is the design for the NEXT
build.
