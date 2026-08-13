# Hostile project fixture

Everything under this directory is **test input, not configuration**. It is the
payload a malicious checked-out repository would ship, used by
`tests/project-isolation.test.sh` to prove that a normal `aidev` session loads
none of it.

## Why the files are not live

Two of these files would be auto-discovery surfaces if they sat here under their
real names with real contents:

- `CLAUDE.md` and `.claude/CLAUDE.md` are discovered by walking the directory
  tree, and files in subdirectories below the working directory load on demand
  when Claude reads files in them. A session started in `~/.ai-dev` — the hub,
  the one place framework edits are allowed — would pick these up the moment it
  read anything here.
- The hook commands in `claude/settings.json` execute.

So the fixture is stored **inert**:

- Directories are named `claude/`, `mcp.json`, `claude-md`, not `.claude/`,
  `.mcp.json`, `CLAUDE.md`. Nothing here matches a discovery pattern at rest.
- Every path inside a hook or MCP command is the literal placeholder
  `@@RUNDIR@@`, which resolves to nothing executable.

`tests/project-isolation.test.sh` materializes a live copy into
`tests/fixtures/.run-hostile/` (gitignored), renaming the dotfiles and
substituting `@@RUNDIR@@` for the real absolute path, launches the production
`aidev` path against that copy, then deletes it.

As defence in depth the user-scope settings fragment carries a
`claudeMdExcludes` entry for this whole subtree, so even a future fixture that
is accidentally committed under a live name cannot enter a session's context.

## Canary tokens

Each surface carries a unique token so an assertion can name which surface
leaked. Tokens all end `-9f3a`.

| Surface | Token | How absence is proven |
| --- | --- | --- |
| `./CLAUDE.md` | `CANARY-ROOT-CLAUDEMD-9f3a` | model output + `/context` memory-file list |
| `./.claude/CLAUDE.md` | `CANARY-DOTCLAUDE-CLAUDEMD-9f3a` | model output + `/context` |
| `./CLAUDE.local.md` | `CANARY-CLAUDE-LOCAL-MD-9f3a` | model output + `/context` |
| `./.claude/rules/evil.md` | `CANARY-PROJECT-RULE-9f3a` | model output + `/context` |
| project skill | `CANARY-PROJECT-SKILL-9f3a` | `system/init` `slash_commands` |
| project agent | `CANARY-PROJECT-AGENT-9f3a` | `system/init` `agents` |
| project command | `CANARY-PROJECT-COMMAND-9f3a` | `system/init` `slash_commands` |
| project output style | `CANARY-OUTPUT-STYLE-9f3a` | model output |
| `.mcp.json` server | marker file `CANARY-MCP-STARTED` | `system/init` `mcp_servers` **and** the marker |
| `SessionStart` hook | marker file `CANARY-HOOK-SESSIONSTART` | marker file |
| `PreToolUse` hook | marker file `CANARY-HOOK-PRETOOLUSE` | marker file |
| `UserPromptSubmit` hook | marker file `CANARY-HOOK-USERPROMPT` | marker file |
| `statusLine` command | marker file `CANARY-STATUSLINE` | marker file |
| settings widening | `sandbox.enabled:false`, `excludedCommands:["*"]`, `defaultMode:bypassPermissions` | `/permissions`-equivalent + sandbox still on |

Absence of output alone is never treated as proof. Every surface is checked
against either a structured diagnostic that enumerates what loaded, or a marker
file that only exists if the payload actually ran.
