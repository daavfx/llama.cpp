# AUDIT.md - what the backend actually is, and why it has no isolation

Date: 2026-10-26. Every fact below was read off disk in this session.
`[PRIOR - suspect]` marks anything not directly verified.

## 1. The real structure (verified, `C:\Users\neto_\.config\opencode`)

```
opencode.jsonc        15 KB   providers, models, mcp block, autoupdate
agents/*.md          9 files 6 built-in (09-18) + 3 daavile (10-26)
skills/<name>/       7 skills, each with core/ + chunks/ + index/
package.json          0 KB
node_modules/                (the plugin host)
```

The agent contract is one `.md` per agent with three frontmatter fields and a
prose body (`agents/daavile-operator.md:1-4`): `description`, `mode:
subagent|all`. Skills are per-folder with `core/{RAG_PROMPT,SKILLS}.md`,
`chunks/<category>/<file>.md`, `index/{manifest.json,retrieval_rules.md}`,
plus `agents/*.json` descriptors (verified: `skills/novel/agents/
opencode_agent.json` - name, layer, rag_root, chunks_root, safety_ceiling,
hard_rules, scoring formula, citation format).

The 15 KB config holds 20+ providers/models (the local llama.cpp fleet at
ports 8091-8102, cloud routes) and 8 MCP servers in one flat `mcp` block
(tradingview, obscura, command-deck, quantum-dashboard, mt5-tester, amn-gate,
ryiuk-mcp, ...). There is NO permission block and NO agent-scoped MCP or
tool declarations anywhere in the config (verified by scan: the only
structural keys are provider/model/mcp).

## 2. The isolation problem (the operator's complaint, confirmed)

There is exactly one namespace. Verified consequences:

- **Every agent reads every agent's `.md`** (`agents/` is a flat directory;
  `read`/`glob`/`grep` see the whole workspace, including `~/.config`).
- **Every agent reads every skill's prose and scripts** - skills are plain
  files with no boundary marker.
- **Every agent reads the config** (15 KB of provider keys shape, MCP paths).
- **No agent-private state exists.** The only real isolation is the session
  history in the SQLite DB (`~/.local/share/opencode/opencode.db`), which
  agents cannot query directly - so the one isolated artifact is the one
  agents cannot mine, and the least valuable one.
- **The daavile souls (operator doctrine, trading doctrine, auditor
  contract) sit in the same flat namespace as the stock agents** - a
  `debugger` persona technically can read the operator's watchdog laws.
  `[PRIOR - suspect]` on intent; verified on structure: nothing prevents it.

Net: the system has one brain, nobody can have a private thought, and the
operator's carefully separated doctrines (souls) are world-readable files
next to generic tooling personas.

## 3. What opencode genuinely does well (keep the base, per the operator)

- The TUI + session ergonomics + the provider routing (20+ models behind one
  `model` string).
- The MCP fan-out (8 servers registered in one place).
- The daavile souls already shipped (`daavile-operator.md` 5 KB, 10-26) -
  the doctrine exists and works; it is just homeless.

## 4. What we already own that this design consumes (receipts)

| Asset | Path | State |
|---|---|---|
| OptChat worlds + universe | `packages/compaction/optchat/` | shipped, compaction fired 10-25, store on disk |
| The native wire (ws-jsonrpc) | `src-tauri/src/bin/daavile-wire.rs` (app) | built, 9/9 tests, live |
| Discovery table | `~/.daavfx/services.json` | publishing |
| The gateway + wire client | harness `scripts/daavfx/` | live |
| The novel RAG layer | `docs/daavfx/skills/novel/` + the config copy | 11 skills, chunk categories, citations |
| The app's persona registry | `src/components/agent/AgentSessionContext.tsx` | localStorage + Studio UI |
| The INFLIGHT ledgers | every repo | the durable research record |

## 5. The three structural gaps a new backend must close

1. **Isolation**: no per-vault, per-agent, or per-surface boundary exists
   today (verified above). The operator's model: each surface owns a vault;
   mini-vaults inside; a human section readable-but-never-writable by agents.
2. **Evolution**: skills are static markdown. The OptChat world tree
   (append-only leaves, merges, views, receipts) already implements exactly
   the "mutable documents" the operator wants; nothing connects it to the
   agent surface.
3. **Enforcement**: every rule today is prose. The operator's standard
   (and the app-lane precedent) is executable gates: a test that fails when
   an agent writes the human section, not a paragraph asking it not to.
