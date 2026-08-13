<!-- TEMPLATE. `bin/ai-dev sync` expands __AI_DEV_HOME__ to this hub's own path
     and writes the result to ~/.claude/CLAUDE.md. The imports below must be
     absolute and must name THIS hub: spelled `~/.ai-dev/core/...` they resolve
     to nothing for a hub cloned anywhere else, and an import that resolves to
     nothing is not an error — the policy is simply absent. Edit core/, and
     this template, never the expanded copy. -->

# AI-DEV

`__AI_DEV_HOME__` is the single source of truth for how I work. This file is the
Claude Code adapter: it is a pointer, not a copy. Edit the core files, never
this one.

@__AI_DEV_HOME__/core/engineering.md
@__AI_DEV_HOME__/core/autonomy.md
@__AI_DEV_HOME__/core/security.md
@__AI_DEV_HOME__/core/orchestration.md

## Claude-specific

- Sandboxed Bash, auto permission mode, and the AI-DEV PreToolUse guard are
  configured in `~/.claude/settings.json` and enforced again in
  `/etc/claude-code/managed-settings.d/20-ai-dev-security.json`. Do not
  edit either by hand — change `__AI_DEV_HOME__/adapters/claude/` and run
  `make -C __AI_DEV_HOME__ sync`.
- A blocked command means the guard fired. Read the reason, then either take a
  different route or ask the human. Do not look for a way around it, do not
  retry with `dangerouslyDisableSandbox`, and do not suggest turning the guard
  off.
- Modifying `__AI_DEV_HOME__` itself is only allowed from a session started in
  `__AI_DEV_HOME__`. From any other project, the framework is read-only.
- Skills live in `__AI_DEV_HOME__/skills` and are exposed through symlinks in
  `~/.claude/skills`. Add skills to the hub, then `make -C __AI_DEV_HOME__ sync`.
