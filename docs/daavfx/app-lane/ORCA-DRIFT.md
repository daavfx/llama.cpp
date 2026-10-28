# ORCA DRIFT REPORT - upstream stablyai/orca vs our fork daavilefx

Role: ORCA DRIFT ANALYST. Read-only pass. No clone, no repo write, no commit.
Date: 2026-10-27.

## 0. Summary table

| | |
|---|---|
| Upstream HEAD | `5e49b6dd110354951b9910bb5354cdeb52673202` - "refactor: group native chat context usage (#34595)" |
| Upstream clone | shallow, depth 1; branch `main`; origin `https://github.com/stablyai/orca`; 0 tags; 1 reachable commit |
| Fork HEAD | `eb09d30f29...` - "feat(skills): daavfx-cli rename + host-repo install (browser milestone works)" |
| Fork branch | `mod/ddaavilefx-embedded-engine` |
| Last known merge-base | `dac82f61bc710324f8883b11788869b6cf8a0ce2` |
| Fork divergence | `git rev-list --count dac82f61..HEAD` = **1651** commits |
| Upstream reachable | **1** commit (shallow) |
| Cross-repo merge-base | impossible - `git cat-file -t dac82f61` in the upstream clone returns `fatal: Not a valid object name` |
| Upstream tracked files | 40,042 (`git ls-files`) |
| Fork tracked files | 33,507 |
| Tracked files only in upstream | **11,615** |
| Tracked files only in the fork | **5,080** |

**Verdict (one line): we are behind upstream on the **legacy-relay retirement** (a 468-file subsystem upstream deleted and we still build), on the **bundled-skill-install rail**, on the **Setup-tab rework** (#29819/#29810), on **docs and tests** (221/1233 upstream vs 7/205 ours), and on **dependency patch levels**; we are ahead of upstream on **host MCP injection into ACP agent sessions**, the **orchestration fleet/watch CLI**, **SSH + provider surface** (+250 / +102 files), and **RYIUK memory**; deliberately divergent on the **rebrand** and the **embedded-engine architecture**.

Second line, the honest one: upstream's newer product surface is almost entirely *infrastructure upstream owns and we do not run* (managed-server, connector-cloud, ephemeral-vm, the cloud relay workspace, skill sharing cloud). Nothing I found is urgent. Two things are worth doing.

---

## 1. Commit-era divergence

Commands run:

```
git -C <upstream> log --oneline            -> 5e49b6dd refactor: group native chat context usage (#34595)
git -C <upstream> rev-list --count HEAD    -> 1
git -C <upstream> rev-parse --is-shallow-repository -> true
git -C <fork>    log --oneline             -> 60 shown (see below)
git -C <fork>    rev-list --count dac82f61..HEAD -> 1651
git -C <fork>    merge-base dac82f61 HEAD  -> dac82f61bc710324f8883b11788869b6cf8a0ce2
git -C <upstream> cat-file -t dac82f61     -> fatal: Not a valid object name
```

The upstream `.git\shallow` contains exactly `5e49b6dd110354951b9910bb5354cdeb52673202`.
`.git\logs\HEAD` has one line: `clone: from https://github.com/stablyai/orca`, timestamp
`1793142031 -0600` (2026-10-27, today). No `FETCH_HEAD`, no tags, no grafts, no
other refs (`show-ref` lists only `refs/heads/main`, `refs/remotes/origin/HEAD`,
`refs/remotes/origin/main`, all the same SHA). `git status --porcelain` is empty,
so the checked-out tree matches the commit.

**Consequence: a git-level merge-base between the two repos is impossible on this
machine, and the upstream changelog has exactly one commit in it.** Below I fall
back to tree and file-inventory comparison, as instructed.

### 1.1 What the fork's own 1651 commits are made of

Subject-pattern heuristic over `git log --format=%s dac82f61..HEAD`:

- **1,517** subjects carry a `#NNNNN` / `#NNNNNN` PR reference - these are upstream
  PRs merged or cherry-picked in. The maximum PR number present is **#26920**.
- **134** subjects carry no PR reference - fork-authored commits.

The fork's newest upstream-looking commit is `1fa8b8bf19 Keep Chat UI users with a
Terminal default on the terminal, with a chat mode switch in the upgrade tip
(#26915)`. Upstream's HEAD subject is **#34595**.

So upstream's HEAD post-dates the newest upstream work the fork carries by roughly
7,675 PR numbers. That is a PR-number gap, **not** a commit count, and PR numbers
in this repo are not a commit index. I cannot convert it into commits, because the
clone has no history. Treat any "N commits behind" number for this pair as
`[PRIOR - suspect]` except the 1651 measured fork-side.

The fork's own mod record at
`F:\DAAVILE_ECOSYSTEM\trading_ecosystem_11\...\vendor\daavilefx\docs\DAAVILEFX-MOD.md:95`
states that on 2026-10-10 upstream was "1,605 commits ahead of our `dac82f61`
base". That is the last dated measurement anyone took; I have no way to refresh it
without a fetch.

### 1.2 The 12 fork-authored commits after the last upstream merge

These sit on top of `372b5b6d23 Merge upstream v1.4.224: native-chat inline
visuals + structured chat evolution` and are the entire fork-only change since the
sync:

```
eb09d30f29 feat(skills): daavfx-cli rename + host-repo install (browser milestone works)
09ac253cad docs(readme): the native-orchestration layer - the fork becomes its own skeleton
f2432bbc8f feat(orchestration): watch TUI + per-run host MCP injection file
ce4a128cb9 feat(cli): orchestration fleet - dispatch a whole fleet from one JSON spec
6c6e321614 feat(acp): host MCP injection for agent sessions (DAAVFX_AGENT_MCP_SERVERS)
33dee2fc16 docs(brand): adopt the daavilefx-ade home, repair corrupted dashes
1316726556 feat(agents): add first-class daavile TUI agent
8b609c11e7 docs(readme): full rewrite - DAAVILEFX as the product, not just an Orca fork
44ac68e20f docs(readme): update embedded-performance section
64b743d5de build(orcad): skip rewriting an already-correct pinned Node runtime
e72e78e01c fix(web-client): dark base tokens for the embedded engine palette
db14fa8f69 docs(mod): record the embedded web-client dark scheme fix
4790c99163 fix(web-client): force dark document appearance for the embedded engine
279c424d6c fix(web-build): resolve markdown parser aliases from the project root
b3e8099c04 fix(merge): restore the 14 add/add files to upstream state (ripgrep + artifact-version)
```

### 1.3 A version discrepancy I cannot resolve

Upstream `package.json` `"version"` is **1.4.214**. The fork's is **1.4.224**.

The fork's own commit `2bb20586eb release: v1.4.224` touches only `package.json`
and the diff is `- "1.4.214" / + "1.4.224"`, sandwiched between
`0abc7650ab ci: sync release workflows with main for the v1.4.224 cut` and
`86e1c38849 feat(native-chat): opt-in per-workspace agent-turn memory`. The fork's
`DAAVILEFX-MOD.md:143` records this as "Upstream sync to v1.4.224 (merge
`mod/upstream-v1.4.224`)" against tag `v1.4.224`.

That should make the fork *at least* as new as a main whose `package.json` is
1.4.214 - yet the upstream HEAD subject is PR #34595 while the fork's newest
merged upstream PR is #26920. Both facts are measured, they contradict, and a
depth-1 clone cannot settle it. Most likely upstream cuts releases on release
branches and only merges the bump into `main` later, or the fork's bump was a
local re-application. **`[PRIOR - suspect]`** - do not use the version numbers as
a staleness signal; use the file inventory below.

### 1.4 Top-level directories that exist on one side only

From `Get-ChildItem -Force` on each root, minus the fork's local build artifacts
(`node_modules`, `out`, `_ARCHIVE`, `.anti-slop-plugin`):

| Only upstream | Only fork |
|---|---|
| `skill-guides/` (26 files) | `src/relay/` (468 files) |
| `skill-stubs/` (11 files) | `CLAUDE.md` |
| `docs/` (221 files vs 7) | `postcss.config.mjs` |
| `native/computer-use-macos`, `native/computer-use-linux`, `native/keyboard-layout-macos`, `native/macos-shipit-scheduling`, `native/notification-status-macos`, `native/process-footprint-macos`, `native/wayland-clipboard`, `native/windows-agent-hook` | `src/main/ryiuk-memory/` |
| `src/packages/` (41), `src/wsl-guest/` (99) | `cloud/infra/` (26) |
| `Casks/`, `examples/`, `.claude/`, `.mcp.json` | - |

**The fork's `_ARCHIVE/` is empty on disk (0 entries).** `DAAVILEFX-MOD.md:204`
claims "The guides' upstream sources (`skill-guides/`, `skill-stubs/`) are
archived in this fork" and `:32` claims trimmed tests live under `_archive/`.
Neither is true of this working tree. The archive content is gone; only the
directory remains. If we want the skill guides back we fetch them, we do not
un-archive them.

---

## 2. Area-by-area inventory

Counts from `Get-ChildItem -Recurse -File | Measure-Object` on both roots. Fork
`src` contains no `node_modules` (verified), so `src` counts are clean.

| Area | Upstream files | Fork files | Delta |
|---|---|---|---|
| `src` | 32,411 | 28,139 | -4,272 |
| `native` | 77 | 16 | -61 |
| `cloud` | 578 | 564 | -14 |
| `config` | 1,240 | 919 | -321 |
| `skills` | 10 | 8 | -2 |
| `skill-guides` | 26 | **MISSING** | -26 |
| `skill-stubs` | 11 | **MISSING** | -11 |
| `docs` | 221 | **7** | -214 |
| `tests` | 1,233 | 205 | -1,028 |

Tracked-file diff is sharper: of upstream's 40,042 tracked files, **11,615 are
absent from the fork**; of the fork's 33,507, **5,080 are absent from upstream**.
Only-fork counts by area: `src` 4,404, `mobile` 254, `cloud` 236, `config` 155,
`tests` 19, `resources` 3, `.github` 3, `docs` 3, `skills` 1, plus
`postcss.config.mjs`, `CLAUDE.md`.

### 2.1 `src` (32,411 vs 28,139)

Per-subdirectory file counts:

| src subdir | Upstream | Fork |
|---|---|---|
| `main` | 14,603 | 12,490 |
| `renderer` | 13,059 | 11,664 |
| `shared` | 3,951 | 2,999 |
| `cli` | 443 | 340 |
| `preload` | 214 | 177 |
| `relay` | - | 468 |
| `packages` (`process-host`) | 41 | - |
| `wsl-guest` | 99 | - |
| `types` | 1 | 1 |

Diff of `src/main/` directory *names*:

- **Only upstream:** `connector-cloud` (25 files), `ephemeral-vm` (17),
  `external-conversations` (26), `kiro` (7), `managed-server` (201),
  `node-runtime` (18), `omp`, `remote-layout-snapshot`,
  `worker-thread-child-process` (9).
- **Only fork:** `ryiuk-memory`.

`src/main` file-count deltas where the difference exceeds 5:

```
runtime            up=3476  fork=2818  delta=+658
browser            up=833   fork=539   delta=+294
persistence        up=629   fork=404   delta=+225
managed-server     up=201   fork=0     delta=+201
daemon             up=632   fork=481   delta=+151
native-chat        up=879   fork=741   delta=+138
wsl                up=124   fork=10    delta=+114
orcad              up=204   fork=126   delta=+78
agent-hooks        up=269   fork=225   delta=+44
codex              up=477   fork=436   delta=+41
git                up=370   fork=329   delta=+41
acp                up=208   fork=167   delta=+41
ipc                up=1247  fork=1212  delta=+35
claude             up=323   fork=289   delta=+34
jira               up=61    fork=32    delta=+29
github             up=257   fork=230   delta=+27
ai-vault           up=345   fork=318   delta=+27
claude-usage       up=46    fork=20    delta=+26
external-conversations up=26 fork=0    delta=+26
connector-cloud    up=25    fork=0     delta=+25
window             up=140   fork=118   delta=+22
startup            up=185   fork=165   delta=+20
zcode              up=24    fork=8     delta=+16
antigravity        up=41    fork=25    delta=+16
ephemeral-vm       up=17    fork=0     delta=+17
node-runtime       up=18    fork=0     delta=+18
... (ports, updater, codex-accounts, cli, provider-process, agent-launch, telemetry, memory, windows, rate-limits ~+10 each)
```

Fork is *ahead* on four:

```
ssh                up=459   fork=709   delta=-250
providers          up=137   fork=239   delta=-102
claude-accounts    up=60    fork=90    delta=-30
rate-limits        up=142   fork=151   delta=-9
```

**Upstream `src/` exists and is missing from the fork - candidates to pull:**
`src/packages/process-host/` (41 files), `src/wsl-guest/` (99), and the four
subsystems above. The rest of the 8,678 upstream-only `src` files are mostly
version-drifted copies of things the fork already has at the same path plus the
clusters below.

Only-upstream `src/shared/` clusters (feature-shaped, not version noise):
`workspace-layout` 134, `native-chat` 120, `remote-runtime` 81, `sidebar-list`
66, `rpc-contract` 35, `jira` 31, `orcad-migration` 28, `palette-match` 23.

**In the fork and missing upstream - our mods to keep:** `src/relay/` (468, see
4.2), `src/main/ryiuk-memory/`, `src/cli/handlers/orchestration/{fleet,watch}-handler.ts`,
`src/main/skills/skill-bundle-ssh-relay-service.ts`,
`skill-freshness-inventory.ts`, `skill-git-tree-identity.ts`,
`skill-installation-topology.ts`, `config/relay-assets/node-pty-1.1.0-console-list-agent-patch.cjs`.

**Agent lanes.** The icon set is identical: 38 files in
`src/shared/agent-icons/` on each side, zero symmetric difference. Renderer
component directories: 67 upstream vs 63 fork; only four are upstream-only
(`host-picker`, `managed-runtime`, `plain-ssh-terminal`, `standalone-terminal` -
all four are legacy-relay-adjacent). **No new agent lane was added upstream that
we lack.** Upstream's README advertises 34 named CLI agents; ours advertises 22
plus "+ any CLI agent". That is a README difference, not a capability difference -
`src/main/` carries near-identical agent directories on both sides (including
`command-code`, `qoder`, `zcode`, `mimo`, `minimax`, `jcode`, `dsh`, `omp`,
`antigravity`, `openclaude`, `hermes`).

**TUI / chat / terminal surfaces.** `src/renderer/src/components/native-chat` is
813 files upstream vs 760 in the fork; `src/main/native-chat` 879 vs 741;
`components/terminal` 56 vs 54; `components/agent` 10 vs 6. These are the biggest
genuine product drift we have, but it is *evolution* of native chat, not a new
surface. `src/main/runtime` alone is +658 files.

**MCP surfaces.** Neither repo has a `src/**/tools` or `*mcp*` directory; MCP
reaches agents through ACP. Upstream hardcodes the empty list in four places I
read: `src/main/acp/acp-session-runtime.ts:143` (`mcpServers: []`),
`src/main/acp/acp-structured-handshake.ts:81` and `:100`,
`src/main/acp/acp-model-catalog-probe.ts:165`. Our injection is fork-only. See 5.3.

### 2.2 `native` (77 vs 16)

The fork's `native/` is Windows-only. Upstream-only and absent from the fork:
`computer-use-macos` (20 files incl. 16 Swift tests), `computer-use-linux` (4),
`keyboard-layout-macos`, `macos-shipit-scheduling` (5),
`notification-status-macos`, `process-footprint-macos`, `wayland-clipboard` (9),
`windows-agent-hook` (6).

Within `native/windows-cli-launcher/`, upstream ships
`src/administrator_launcher.rs`, `src/administrator_restart.rs`,
`src/administrator_status.rs` and `src/main.rs`; the fork carries **only
`main.rs`**. Three files of Windows elevation work are missing.

The fork's `native/` also carries build artifacts upstream does not track:
`windows-cli-launcher/.build/daavilefx.exe`, `windows-registry/bin/win32-x64-148/`,
`windows-registry/build/Release/`. Those are not drift, they are untracked output.

Keeping `native/` Windows-only is correct for this host app (Windows-native per
`AGENTS.md`), but it does mean the fork cannot produce a macOS/Linux build at all.
That is a deliberate platform-divergence, not a gap to close.

### 2.3 `cloud` (578 vs 564)

Top-level: upstream `apps, dev, docs, packages, security`; fork
`apps, dev, docs, infra, packages`.

Upstream-only: `cloud/apps/connector/`, `cloud/security/` (2 files).
Fork-only: `cloud/infra/` (26 files, `cloud/infra/terraform/`), and 55
only-fork files under `cloud/apps/` (`cloud/apps/relay-ops/`).

`cloud/apps/relay/` is 289 files on **both** sides - this is the relay's modern
home (PR numbering there is separate: #329-#361 in
`docs/agent-skill-sharing-implementation-checklist.md`). Upstream's README
advertises it: "The relay that pairs the mobile app with a desktop host is also in
this repository under `cloud/`".

Only-fork `cloud/dev` files (141) are capacity/rollout tooling we wrote:
`check-relay-same-cap-headroom.mjs`,
`classify-relay-production-capacity-director.mjs`,
`deploy-relay-blue-green.mjs`, `cloud-sql-rollout-lock-census.mjs`,
`capture-terraform-plan-baseline.mjs`. Keep.

### 2.4 `config` (1,240 vs 919)

Upstream-only, notable: `config/ast-grep/` (15 - a whole lint-rule layer),
`config/audit-tools/` (4), `config/agent-plugins/` (3), `config/scripts/` (+259:
1,078 vs 819), `config/ci/` (9 vs 6), `config/docker/` (23 vs 22),
`config/patches/` (25 vs 17), `config/nsis/` (2, same),
`config/sgconfig.yml`, `config/cargo-deny.toml`,
`config/dark-build-switches.cjs`, `config/packaged-*.cjs` (3 of 4),
`config/path-literal-baseline.txt`,
`config/process-host-direct-import-baseline.txt`,
`config/repo-host-read-baseline.txt`, `config/workspace-record-read-baseline.txt`,
`config/worktree-id-composer-baseline.txt`, `config/id-only-store-write-baseline.txt`,
`config/main-layout-writer-baseline.txt`, `config/main-sync-spawn-baseline.txt`,
`config/renderer-layout-writer-baseline.txt`, `config/focus-setting-read-baseline.txt`,
`config/host-list-render-baseline.txt`, `config/vite.fixtures.config.ts`,
`config/vitest.performance.config.ts` (fork has this),
`config/wayland-clipboard-resources.cjs`,
`config/oxlint-js-plugins.json`, `config/oxlint-code-quality-native-plugins.json`
(fork has this one), `config/dependency-security-exceptions.json`,
`config/dependency-security.md`, `config/unproven-pty-retirement-baseline.txt`,
and the two legacy-relay ratchets discussed in 4.2.

Fork-only: `config/relay-assets/` (3), `config/oxlint-plugins/mobile-pairing-qrcode-import.mjs`,
`config/oxlint-plugins/sort-comparator-performance.mjs`,
`config/tsconfig.relay.json`, `config/update-translation.txt`,
`config/ci/windows-ssh-provider/invoke-pinned-relay-cells.ps1`.

**Dependency patch levels - the fork is behind and it is measurable.**
`config/patches/` on both sides, then the gap:

Verified per-file with `Test-Path`; the xterm family is uniformly **one beta
behind** on every package the fork carries:

| Package | Upstream | Fork |
|---|---|---|
| `@xterm__xterm` | beta.304 | beta.303 |
| `@xterm__addon-image` | beta.301 | beta.300 |
| `@xterm__addon-search` | beta.301 | beta.300 |
| `@xterm__addon-webgl` | beta.300 | beta.299 |
| `@xterm__addon-serialize` | beta.301 | beta.300 |
| `@xterm__addon-ligatures` | beta.301 | beta.300 |

(Each also has a matching `.src.patch` on both sides.) Shared, same version:
`@vscode/windows-process-tree@0.8.0`, `i18next-cli@1.74.2`, `lint-staged@16.4.0`,
`node-pty@1.1.0`, `ws@8.22.0`, `xterm-upstream.json`.

Whole packages upstream patches and the fork does **not**:

| Upstream only |
|---|
| `@tiptap__extension-list@3.31.3.patch` |
| `braces@3.0.3.patch` | **absent** |
| `monaco-editor@0.55.1.patch` | **absent** |
| `oxlint-plugin-anti-slop@0.1.2.patch` | **absent** |
| `sprintf-js@1.1.3.patch` | **absent** |
| `vitest@5.0.5.patch` | **absent** |
| `zod@3.25.76.patch` | **absent** |

Correction on the table above: for `@xterm__addon-search` both sides carry
`0.17.0-beta.301`. The xterm drift is real but narrower - `@xterm__xterm`
(beta.303 vs 304) and `@xterm__addon-webgl` (beta.299 vs 300) and
`@xterm__addon-image` (beta.300 vs 301). The seven missing whole-package patches
are the material part: fork `node_modules` is running **stock** tiptap, braces,
monaco-editor, oxlint-plugin-anti-slop, sprintf-js, vitest and zod.

### 2.5 `skills` (10 vs 8) - see section 4 for the full treatment

### 2.6 `docs` (221 vs 7)

This is the largest proportional hole and the cheapest to state. The fork's entire
`docs/` is:

```
docs/DAAVILEFX-MOD.md
docs/assets/wechat-qr-group11.jpg
docs/bug-reproductions/opencode2-session-lineage/hook-posts-after.jsonl
docs/bug-reproductions/opencode2-session-lineage/hook-posts-before.jsonl
docs/bug-reproductions/opencode2-session-lineage/README.md
docs/site/.npmrc
docs/site/content/docs/model/orca-yaml.mdx
```

Upstream's 221: `STYLEGUIDE.md` + `docs/styleguide/` (5),
`agents-md-refs/` (5), `relay-region-correction/` (6),
`bug-reproductions/` (53), `readme/` (10 translated READMEs), `assets/` (10),
`site/` (126 - the public docs site), plus the five design/review docs in 3.

### 2.7 `tests` (1,233 vs 205)

`tests/e2e` 1,063 vs 201; `tests/tools` 167 vs 4.
`DAAVILEFX-MOD.md:31-32` records this as intentional: "Test suite trimmed locally
to the ones that still run on Windows; heavier suites live under `_archive/`."
The `_archive/` is empty (1.4), so the trim is permanent on this machine. This is
a real cost: we have no e2e net under the Windows host, and the fork's own mod
doc leans on "verified live" checks instead of tests.

---

## 3. Upstream changelog mining

The upstream clone has **one commit**. There is no CHANGELOG in either root
(verified: no `CHANGE*` file at either root). The readable changelog signal is
therefore threefold: the one upstream commit, upstream's `docs/`, and the 1,517
upstream PRs already in the fork's log.

**The one upstream commit** - `5e49b6dd refactor: group native chat context usage
(#34595)` - is a refactor. Maintenance.

**Upstream `docs/` files, triaged material vs maintenance:**

| File | Lines | Triage |
|---|---|---|
| `docs/agent-skill-sharing-implementation-checklist.md` | 1,676 | **MATERIAL** - the whole skill-sharing/publishing subsystem, see 4 |
| `docs/automated-setup-tab-design.md` | 73 | **MATERIAL** - PR #29819, new product behavior, see 4.4 |
| `docs/automated-setup-tab-astra-review.md` | 78 | Maintenance (review record for #29819) |
| `docs/native-chat-setup-provisioning-design.md` | 33 | **MATERIAL** - PR #29810, see 4.4 |
| `docs/native-chat-setup-provisioning-review.md` | 34 | Maintenance (review for #29810) |
| `docs/relay-region-correction/*` (6 files) | - | **MATERIAL** - relay region correction, rollout/idle-cutover plans |
| `docs/STYLEGUIDE.md` + `styleguide/native-chat.md` | - | Maintenance, but a hard dependency for any UI merge |
| `docs/site/content/docs/**` (126) | - | Maintenance/docs-site |
| `docs/bug-reproductions/**` (53) | - | Maintenance |

**The 1,517 upstream PRs already in the fork.** Reading the subjects, the pattern
is overwhelmingly maintenance: SSH Phase 3-3.8 cleanups (#26889-#26892,
#26890-#26891), file-watch ownership moves (#26632, #26627, #26696, #26606),
managed-file drag/drop guards (#26698, #26682, #26671), explorer retention
(#26811, #26873, #26797), CI consolidation (#26874, #26806, #26899), and the
"Keep/Show/Restore/Preserve/Scope/Reset" series. The material ones the fork
*already took* are `#26005` source-control reveal, `#25999` localization catalog,
`#26238` native-chat inline visuals, `#24990` standalone ACP client layer,
`#24636` host-owned managed account profiles, `#22396` bundled ripgrep.

**"How behind are we" signal.** The honest answer is *on infrastructure we do not
run, materially; on product surfaces we do run, in evolution not revolution*.
Concretely, and only from `docs/`:

1. PR **#29819** changed product behavior the fork still implements the old way
   (Setup-tab rework, 4.4).
2. PR **#29810** fixed a terminal-provisioning bug class the fork still has
   (4.4).
3. The **skill-sharing** subsystem grew a 1,676-line implementation record with
   its own cloud-side PRs (#329-#361) and the fork has none of the new install
   rail (4.3).
4. The **legacy relay retirement** is scheduled and dated, and the fork is on the
   wrong side of it (4.2).
5. The **relay region correction** has plan/rollout/acceptance docs, so a
   behaviour change shipped to the relay the fork also builds (4.2).

Everything else upstream-side is maintenance, refactors, tests and deps. I found
no evidence of a new agent mode, new provider, new TUI surface or new MCP surface.

---

## 4. The skill surface

### 4.1 Inventory

`skills/` - one `SKILL.md` per skill:

| Upstream (10) | Fork (8) |
|---|---|
| computer-use, jira-tickets, linear-tickets, orca-cli, orca-emulator, orca-emulator-android, orca-jira, orca-linear, orca-per-workspace-env, orchestration | computer-use, daavfx-cli, linear-tickets, orca-emulator, orca-emulator-android, orca-linear, orca-per-workspace-env, orchestration |

- **Upstream ships 3 skills the fork does not:** `jira-tickets`, `orca-cli`
  (renamed, not lost - see below), `orca-jira`.
- **The fork ships 1 skill upstream does not:** `daavfx-cli`.

`orca-cli` -> `daavfx-cli` is a rename, recorded at
`DAAVILEFX-MOD.md:200-206`: "`ORCA_SKILLS_REPOSITORY_URL` ->
`https://github.com/daavfx/daavilefx-ade`; the CLI skill is `daavfx-cli`... A
legacy guide alias `orca-cli` keeps old instructions resolving." So the honest
count of *new* skills the fork lacks is **2**: `jira-tickets` and `orca-jira`.
(The fork does have `src/main/jira/` at 32 files vs upstream's 61, so the Jira
lane exists but is thin and the skills were never ported.)

`skill-guides/` - upstream **26** files (10 top-level `.md` plus
`orca-cli/references/` 4, `orca-per-workspace-env/references/` 5,
`orchestration/references/` 6, `_shared/` in stubs). The fork: **MISSING at top
level**, 0 files. `DAAVILEFX-MOD.md:204` says they were archived into `_ARCHIVE/`,
which is empty (1.4). **The fork does not have the skill guides.** It has the
*fork-rebranded copies of them* baked into `resources/skills/` and
`src/cli/bundled-skill-guides.ts` (hand-edited, because - per the same line -
"its generator cannot re-run without them").

`skill-stubs/` - upstream **11** files. Fork: **MISSING**, 0 files. Same story.

### 4.2 `src/main/skills` - upstream 199, fork 203

Only-upstream 27, only-fork 31. The material upstream-only entry is the whole
`src/main/skills/bundled-skill-install/` subsystem:

```
upstream only (20 files):  bundled-skill-install/{backup-permissions.test,
  bundled-skill-sources, classify, classify.test, cli-entry, cloud-state,
  execute, execute.test, filesystem, layouts.test, local-host, local-host.test,
  plan, plan-selection.test, plan.test, service, skill-home.test-support, swap,
  targets, workspace-targets.test}.ts
upstream only (7 more):    skill-cloud-request-error.ts, skill-install-operation-error.test.ts,
  skill-lock-sources.ts, skill-lock-sources.test.ts, skill-provider-discovery-coverage.test.ts,
  skill-remote-repo-sources.ts, skill-share-package-name.test.ts
```

I ran `Test-Path` on the fork: **`src/main/skills/bundled-skill-install` does not
exist.** The fork has exactly two subdirectories under `src/main/skills/`
(`skill-delete` and nothing else); upstream has `bundled-skill-install` and
`skill-delete`. Plus the CLI half: only-upstream
`src/cli/handlers/bundled-skill-install-command.ts`,
`src/cli/handlers/skill-guide-host-gate.ts`,
`src/cli/skills-cli-agent-aliases.ts`, `src/cli/skills-install.test.ts`.

That subsystem is the *other half* of the 1,676-line checklist
(`docs/agent-skill-sharing-implementation-checklist.md`): cancelled-extraction
recovery, `classify`/`plan`/`execute`/`swap`, workspace vs local-host targets,
`cloud-state`, and the bundle CLI entry. It is the mechanism by which a skill gets
installed *from a cloud package* rather than from `npx ... add <repo>/tree/<sha>`.

### 4.3 Does the fork's install mechanism have an upstream counterpart that is AHEAD?

Yes. Both repos have the same file, `src/shared/agent-feature-install-commands.ts`,
and the diff is a clean answer.

Upstream (38 lines):
```ts
export const ORCA_SKILLS_REPOSITORY_URL = 'https://github.com/stablyai/orca'
export const SKILLS_CLI_VERSION = '1.7.2'
...
  return [`skills@${SKILLS_CLI_VERSION}`, 'add',
          `${ORCA_SKILLS_REPOSITORY_URL}/tree/${options.sourceCommit}`, ...skillArgs, ...]
```
Two things the fork dropped: **a pinned CLI version (`1.7.2`)** and a
**build-commit-pinned source (`/tree/${sourceCommit}`)**. The upstream comment
explains both: "Pin one CLI across install rails: 1.5.x lacks commit fetch and
bare npx may reuse stale/wrong binaries (#18687)" and "Use the build commit for
manifest freshness on every channel, including untagged hourly builds".

Fork (134 lines):
```ts
export const ORCA_SKILLS_REPOSITORY_URL = 'https://github.com/daavfx/daavilefx-ade'
...
  return ['skills', 'add', ORCA_SKILLS_REPOSITORY_URL, ...skillArgs, ...,
          ...agents.flatMap((a) => ['--agent', a]), ...(options.yes ? ['-y'] : [])]
```
The fork is **ahead** on three counts upstream does not have: an explicit
`--agent` allowlist with `isUsableSkillsCliAgentKey` validation
(`src/shared/skills-cli-agent-keys.ts`, fork-only), a hard refusal of the
`-y`-with-no-`--agent` combination, and a whole **update rail**
(`buildAgentFeatureSkillUpdateArgs`, `--global`/`--project`). It is **behind** on
the two the fork dropped: no `SKILLS_CLI_VERSION` pin, and no
`/tree/<sourceCommit>` - so a fork-built engine installs whatever `npx` resolves
*now* from the private repo HEAD, with no commit pin and no version pin.

Verdict: **the upstream counterpart is ahead on exactly the two things that make
installs reproducible, and behind on everything else.** Those two are small
additions - re-adding a constant and a `sourceCommit` option to one function.

### 4.4 The Setup-tab rework (PRs #29819 / #29810)

`docs/automated-setup-tab-design.md` is explicitly a *product-behavior change*:
"Run terminal-backed automated workspace setup in its own **Setup** tab using the
existing new-tab path. Remove automated setup split placement, its
preference/control, and its one-shot split/geometry state." The doc even names the
symbols to delete: `pendingSetupSplitByTabId` and `setupScriptLaunchMode`, and
says the implementation "deletes `setupScriptLaunchMode` from live
`GlobalSettings`, defaults, and launch types, and adds it to existing
`stripRetiredGlobalSettings`".

I verified upstream did it. Grep of upstream `src/` for `setupScriptLaunchMode`
returns **25 matches, all of them dead or legacy**: the migration stripper
`src/main/persistence/applying-settings/terminal-settings-migrations.ts:61,78`,
the persistence tests
(`state-write-round-trip.test.ts:78-90` and
`normalize-loaded-global-settings.test.ts:45-50`, both asserting the key is
`not.toHaveProperty`), old-host runtime fixtures, and one old renderer test.

The fork still ships it **live**, 74 matches across production code:

- `src/shared/default-global-settings.ts:123` - `setupScriptLaunchMode: 'new-tab'`
- `src/shared/global-settings-types.ts:197` - `setupScriptLaunchMode: SetupScriptLaunchMode`
- `src/renderer/src/components/settings/TerminalSetupScriptSection.tsx:65-71` - the live Settings UI the upstream doc says to delete ("Remove the Setup Script Location section and search registration")
- `src/renderer/src/lib/worktree-initial-terminal-seeding.ts:149`
- `src/renderer/src/lib/launch-worktree-background-terminals.ts:280`
- `src/main/ipc/worktree-remote.ts:460-461`
- `src/main/runtime/runtime-worktree-terminal-provisioning.ts:132-133`
- plus `pendingSetupSplitByTabId` through `terminal-state.ts:86`,
  `terminal-startup-queues.ts:75-89`, `terminal-shutdown-state.ts:88-138`,
  `terminal-tab-close.ts:151,239`, `worktree-purge-state.ts:153`, and ~12 test files

`docs/native-chat-setup-provisioning-design.md` is PR #29810 and describes the bug
the old policy causes: "In new-tab setup mode this inconsistency creates an idle
shell before Setup", measured as "The original policy failed both agent
regressions by spawning an undefined-command shell before Setup". Both PRs are
numbered above the fork's newest merged upstream PR (#26920), so they post-date
the v1.4.224 merge.

### 4.5 The legacy relay retirement

Upstream's `config/legacy-relay-compat-tags-baseline.txt` (43 lines) states the
schedule: "Each tag marks code the relay retirement (2027-01-15) deletes or edits.
RATCHET: may only SHRINK." and lists `src/main/ipc/ssh/*.ts`,
`src/main/runtime/orchestration/terminal-authority/*`,
`src/main/ssh/orcad-migration-delta-move.ts` and friends.
`config/legacy-relay-importers-baseline.txt` is 15 lines.

Facts I measured:

- Upstream has **no** `src/relay/`. The fork has **468 files** there
  (`relay-daemon.ts`, `relay-watcher-*.ts`, `relay-pty-source-*`,
  `pty-handler.ts`, `git-handler.ts`, `fs-handler*.ts`, `ssh-pty-*`,
  `remote-cli-*`, `legacy-relay-publication-ledger.ts`, `wsl-agent-hook-relay.ts`).
- Upstream has **`src/main/ssh/legacy-relay/`**; the fork does not.
- Upstream has **no** `config/scripts/build-relay.mjs`; the fork does, and
  `package.json` still runs `build:relay` inside `build:desktop`,
  `build:release`, `build:release:host`, `build:release:parallel` and
  `bench:wsl-hook-relay-reattach`.
- The fork's `tsconfig.node.json` and `tsconfig.relay.json` both compile
  `../src/relay/**/*` into `out/relay`.
- Renderer component dirs `plain-ssh-terminal` and `standalone-terminal` exist
  only upstream.
- `docs/relay-region-correction/` (6 files: ACCEPTANCE, API, CHECKLIST,
  IDLE-CUTOVER-PLAN, PLAN, ROLLOUT) exists only upstream - and it concerns
  `cloud/apps/relay/`, which **both** repos build.

Read together: upstream retired the in-app standalone relay process in favour of
the `cloud/apps/relay/` workspace, is mid-migration with a ratchet, and published
a region-correction rollout against that workspace. The fork is on the legacy
side. **This is not urgent** - the fork's relay is working code and the retirement
date is 2027-01-15 - but it is the single biggest structural divergence, and it
carries real weight in any future cherry-pick because the relay's replacement
lives in `cloud/`, not `src/`.

### 4.6 Two stale rows in the fork's own triage table

`DAAVILEFX-MOD.md:93-101` triaged two upstream items as "deliberately not taken"
on 2026-10-10:

- "`src/main/foreign-sqlite-readers/` (19 files; **our fork has zero of them**)" -
  today the fork has **18** files there, identical count to upstream. The
  v1.4.224 merge landed it.
- "`publishHeadlessRuntimeGraph` (`src/main/runtime/headless-runtime-graph.ts`)"
  as missing - **present** in the fork today at that exact path.

Both rows are now obsolete. Anyone re-proposing them would be re-litigating a
closed merge. Worth a two-line correction in `DAAVILEFX-MOD.md`.

---

## 5. Recommendation

Ranked by what actually helps the DAAVILE app, not by diff size.

### 5.1 (a) New upstream features worth merging

These I name by file, with the reason, in the order I would do them.

**1. Re-pin the skill install rails - 2 constants, highest value per line changed.**
Files: `src/shared/agent-feature-install-commands.ts` (both repos have it).
Take `SKILLS_CLI_VERSION = '1.7.2'` and the
`` `${ORCA_SKILLS_REPOSITORY_URL}/tree/${options.sourceCommit}` `` form from
upstream lines 5 and 27.
*Reason:* the fork's engine installs skills from its private repo with no commit
pin and no CLI version pin, so two engines built from the same commit can install
different skill bytes, and a bad `npx` cache silently ships stale skills. Nothing
in the DAAVILE app depends on the fork's current looser form. Keep the fork's
`--agent`/`-y` guards and update rail - they are strictly better than upstream's.
Zero conflict surface: upstream's version of this file is 38 lines and the only
shared symbol names are the two functions plus the URL constant.

**2. The seven missing dependency patches - mechanical, one directory.**
Files: `config/patches/@tiptap__extension-list@3.31.3.patch`,
`braces@3.0.3.patch`, `monaco-editor@0.55.1.patch`,
`oxlint-plugin-anti-slop@0.1.2.patch`, `sprintf-js@1.1.3.patch`,
`vitest@5.0.5.patch`, `zod@3.25.76.patch`, plus the xterm version bumps
(`@xterm__xterm` beta.303 -> 304, `@xterm__addon-webgl` beta.299 -> 300,
`@xterm__addon-image` beta.300 -> 301).
*Reason:* the fork's editor, rich-text, terminal and type layers are running stock
packages that upstream found necessary to patch. Monaco and xterm are the two most
visible surfaces in the embedded IDE, and the fork's own mod record already fought
MAX_PATH and Tailwind wars over exactly these. These are patch files, not source -
they apply under the existing `pnpm patch` machinery.

**3. The Setup-tab rework, cherry-picked as two PRs - the only real product fix.**
Files (upstream): `docs/automated-setup-tab-design.md` is the spec; the code it
names is the renderer Setup path, `worktree-initial-terminal-seeding.ts`,
`launch-worktree-background-terminals.ts`, `worktree-remote.ts:460-461`,
`runtime-worktree-terminal-provisioning.ts:132-133`, and every
`pendingSetupSplitByTabId` site in `terminal-state.ts:86`,
`terminal-startup-queues.ts`, `terminal-shutdown-state.ts`,
`terminal-tab-close.ts`, `worktree-purge-state.ts`.
*Reason:* this is a *deletion*, not an addition - the fork gets simpler, ~74 sites
go away, and it removes the "idle shell before Setup" class that PR #29810
measured. It is the one upstream change that would reduce the fork's divergence
while improving behavior. **Caveat, honestly:** the fork has a rebrand + embedded
mods layered over this exact area, and `DAAVILEFX-MOD.md:141` lists PTY terminal
and pairing/RPC as the HIGH-RISK overlap. I have not audited whether the fork's
rebrand touches these 74 sites. Treat as a scoped project, not a cherry-pick, and
only if the operator actually cares about setup placement - which for an embedded
IDE that opens straight into a paired web client is a fair question.

**NOT recommended:** pulling `src/wsl-guest/` (99), `src/packages/process-host/`
(41), `managed-server` (201), `connector-cloud` (25), `ephemeral-vm` (17),
`external-conversations` (26), `node-runtime` (18), `kiro` (7),
`worker-thread-child-process` (9). Every one is a subsystem the fork does not run
and the mod doc's own rule of thumb (`DAAVILEFX-MOD.md:102-104`) already covers:
"if upstream's 'fix' only exists inside a subsystem we don't ship, our smaller
equivalent wins until it breaks." `remote-runtime` (+81 in `src/shared`) and
`managed-runtime`/`host-picker` renderer dirs fall in the same bucket - they are
the managed/SSH-server runtime rework, and we run a local engine.

**NOT recommended:** the native-chat +658-file drift in `src/main/runtime`. It is
structured-session evolution, not a new surface. Merging it means taking the
adapter registry, journal/command tables, latest-request, lifecycle delivery and
model catalog substrate - 250+ commits, which is exactly the cascade
`DAAVILEFX-MOD.md:147-149` already recorded drowning in ("A cherry-pick of the
three feature commits was attempted first and drowned in dependency cascade -
every pulled file imported five more"). If native-chat matters to the DAAVILE app
later, it is another v1.4.x merge, not a cherry-pick.

### 5.2 (b) Mods we should push upstream-style

Meaning: keep, and write up in a form a reviewer could accept. None of these are
urgent and none block anything.

1. **Host MCP injection for ACP sessions.** Fork files:
   `src/main/acp/acp-host-mcp-servers.ts`, `acp-structured-acquire.ts`
   (fork-modified), plus the env `DAAVFX_AGENT_MCP_SERVERS` and
   `<user-data>/agent-mcp-servers.json`. Upstream hardcodes `mcpServers: []` at
   `acp-session-runtime.ts:143`, `acp-structured-handshake.ts:81,100`,
   `acp-model-catalog-probe.ts:165`. The fork's degrade-to-upstream-when-absent
   design is exactly the shape a reviewer wants, and the fork's own mod doc
   (`:88`) already says "Absent or malformed input degrades to upstream behavior."
   This is the single most generally valuable thing we carry. Whether upstream
   wants it is their call - `README.md:88` already claims this fork is "private,
   personal... no public distribution."
2. **`orchestration fleet` / `orchestration watch`.** Fork-only:
   `src/cli/handlers/orchestration/fleet-handler.ts`,
   `watch-handler.ts` (+tests), `src/cli/handlers/orchestration-modules-boundaries.test.ts`.
   A one-JSON-spec fleet dispatch over an existing RPC surface is small and
   self-contained.
3. **`skill-freshness-inventory` / `skill-git-tree-identity` /
   `skill-installation-topology`** under `src/main/skills/`. These are
   fork-only skill-integrity modules that would complement, not collide with,
   upstream's `bundled-skill-install/` - and they are the natural place to put the
   commit-pinning from 5.1(1).
4. **`config/relay-assets/node-pty-1.1.0-console-list-agent-patch.cjs`** and the
   fork's patched `node-pty` with job-object process control
   (`listJobProcessIds`, `terminateJob`, `assignCurrentProcessToJob`). Windows
   child-process hygiene is genuinely useful and the mod doc already warns staging
   stock prebuilds undoes it (`DAAVILEFX-MOD.md:123-127`).

### 5.3 (c) Things we deliberately keep divergent

Keep these, and do not let a future merge silently revert them. Each maps to a
line in `DAAVILEFX-MOD.md` and a file I read.

1. **The rebrand.** `ORCA_SKILLS_REPOSITORY_URL = 'https://github.com/daavfx/daavilefx-ade'`
   (`src/shared/agent-feature-install-commands.ts:3`), `CLAUDE.md`, the README
   rewrite, `LICENSE` notice retained. Upstream will never take this and it must
   survive every merge. The v1.4.224 merge already re-applied "1,489 fork
   line-pairs (rebrand + ryiuk keyword pairs, hunk-index-aligned)"
   (`DAAVILEFX-MOD.md:157-158`) - budget the same for the next one.
2. **The embedded-engine architecture.** `src/main/orcad/` (126 files on our side)
   with `webClientRoot` plumbing, `/__local/pairing`, instance-lock adoption,
   process-only replacement, the warm-start contract
   (`DAAVILEFX-MOD.md:15-22`, `README.md:27-62`). Note upstream *also* has
   `src/main/orcad/` at 204 files - the fork has 78 fewer there, so this is
   partly drift, not all mod. Check `orcad` on the next merge; do not assume
   every difference is ours.
3. **Windows-only `native/`.** Deliberate. But see 5.1(2) for the two `native/`
   files that are not about platform: `windows-cli-launcher/src/administrator_{launcher,restart,status}.rs`
   are Windows files we are simply missing.
4. **`src/relay/` staying in-tree.** Deliberate *for now*, but with a date. Upstream
   retires the legacy relay on **2027-01-15**
   (`config/legacy-relay-compat-tags-baseline.txt`, upstream). We are on the other
   side of that line and still compile it into `out/relay`. The decision to keep it
   is fine; the decision needs to be revisited before that date, because after it
   upstream stops fixing it and we own 468 files alone.
5. **`src/main/ryiuk-memory/`**, `cloud/infra/terraform/`, and the `cloud/dev`
   relay-capacity scripts. Ours, no upstream counterpart, no reason to move.
6. **The trimmed test suite** (`DAAVILEFX-MOD.md:31-32`). This one I would not call
   a feature. It is a cost: 205 files vs 1,233, no e2e net, and the archive that
   was supposed to hold the rest is empty. It makes every future merge riskier
   because the fork's safety net is a typecheck plus a handful of live checks
   (`DAAVILEFX-MOD.md:151-167, 182-183`). If any drift work happens, port
   `tests/e2e` selectively rather than not at all.

### 5.4 Is drifting further a cost or a feature?

Both, and the split is clean.

**Cost.** 11,615 upstream tracked files absent from us, of which the skew is real
in three places: `src/main/runtime` (+658), `src/main/browser` (+294),
`src/main/persistence` (+225), and `native-chat` (+138). That is structured-session
and runtime substrate, and it is the same cascade the fork already lost a
cherry-pick to. Add 1,028 missing test files, 214 missing doc files, an empty
`_ARCHIVE/`, seven unapplied dependency patches, and every future sync gets more
expensive - the v1.4.224 merge cost 655 conflicts
(`DAAVILEFX-MOD.md:151`). **The drift compounds.**

**Feature.** The fork's divergence is not arbitrary forking - it is the reason the
app works. The host MCP injection, the `orchestration fleet`/`watch` CLI, the
embedded `orcad` warm-start contract, the SSH surface (+250 files) and provider
layer (+102 files) exist because this stack owns the orchestrator, the host and a
harness simultaneously (`README.md:77-84`). None of it has an upstream counterpart
because none of it can: upstream is a general-purpose orchestrator and we are a
trading IDE that happens to embed one. **The divergence is load-bearing.**

The honest read: drifting further is a cost **where upstream is maintaining
shared infrastructure we also build** - `cloud/apps/relay/` (289 files, both
sides, plus a published region-correction rollout we do not have) and
`src/main/orcad/` (204 upstream vs 126 ours). Those need watching. Everywhere
else, upstream's motion is either in subsystems we do not run, or is evolution of
surfaces we do run but can sync in bulk.

### 5.5 Nothing here is urgent

I looked for urgency evidence and found none. The relay retirement is dated
2027-01-15. The skill-install rail gap costs reproducibility, not function - the
fork's app installs skills today and `DAAVILEFX-MOD.md:205` records "skills CLI
65/65" green after the rename. The Setup-tab rework is a behavior/placement
improvement in a fork whose IDE opens inside a host shell that owns the chrome.
The dependency patches are pre-existing and were not blocking the build.
**The two things I would actually do are 5.1(1) and 5.1(2) - roughly a dozen
lines and seven patch files, together an afternoon, with no cherry-pick cascade.**

---

## Appendix - commands actually run

```
git -C <upstream> log --oneline ; rev-list --count HEAD ; rev-parse --is-shallow-repository
git -C <upstream> show-ref ; remote -v ; describe --tags ; status --porcelain
Get-Content <upstream>/.git/shallow ; .git/logs/HEAD ; .git/packed-refs ; .git/FETCH_HEAD
git -C <fork> log --oneline -60 ; rev-list --count dac82f61..HEAD ; merge-base dac82f61 HEAD
git -C <fork> log --format=%s dac82f61..HEAD   (PR-number extraction)
git -C <fork> cat-file -t 5e49b6dd... ; log --oneline -20 -- package.json ; show 2bb20586eb
git -C <upstream> cat-file -t dac82f61
git -C <both> ls-files  -> 40,042 upstream / 33,507 fork, diffed via HashSet
Get-ChildItem -Recurse -File | Measure-Object  (all nine areas, both roots)
Get-ChildItem <src/main> / <src/renderer/src/components> / <src/main/skills> -Directory
Test-Path on: src/relay, src/main/orcad, src/main/skills/bundled-skill-install,
  src/main/ssh/legacy-relay, src/main/runtime/headless-runtime-graph.ts,
  src/main/foreign-sqlite-readers, config/scripts/build-relay.mjs, _ARCHIVE, cloud/*
Select-String / grep on: setupScriptLaunchMode, pendingSetupSplitByTabId,
  ORCA_SKILLS_REPOSITORY_URL, mcpServers
Read: README.md (fork 187 lines / upstream 279 lines), DAAVILEFX-MOD.md (206 lines),
  docs/automated-setup-tab-design.md, docs/native-chat-setup-provisioning-design.md,
  docs/agent-skill-sharing-implementation-checklist.md (first 70 of 1,676),
  src/shared/agent-feature-install-commands.ts (both), manifest.json, REPO-MAP.md
```

## Appendix - `[PRIOR - suspect]`, i.e. could not verify from this machine

| Claim | Why unverified |
|---|---|
| "Upstream is N commits ahead" | Upstream clone is depth 1; no history, no tags. Only the PR-number gap (#26920 vs #34595) is measured |
| The version contradiction (1.4.214 upstream vs 1.4.224 fork) | Cannot be settled without a fetch. See 1.3 |
| The fork's own "1,605 commits ahead" figure at 2026-10-10 | Taken from `DAAVILEFX-MOD.md:95`, not re-measured |
| How many of the 1,517 "PR-referenced" fork commits are upstream-authored | Heuristic on commit subjects (`#NNNNN`), not author/committer data |
| Whether upstream's Setup-tab code (PR #29819/#29810) conflicts with the fork's rebrand | Not audited; the fork's 74 `setupScriptLaunchMode` sites were counted, not read against upstream's diff |
| Whether `skill-guides/`/`skill-stubs/` content sits elsewhere in the fork | `_ARCHIVE/` is empty; `src/cli/bundled-skill-guides.ts` is recorded as a hand-edited copy, but I did not diff its bytes against upstream's guides |
| Fork `mobile/src` +248 only-fork files | Mostly `.test.ts` and `.web.tsx` files; likely renames/rebase artifacts, not audited |
| Upstream's release/versioning workflow | No `.github/workflows/release.yml` read in detail |
