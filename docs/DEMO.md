# Demo

A real capture of the ["Try it in five minutes"](../README.md#try-it-in-five-minutes)
path, run on a disposable Ubuntu 24.04 VM with a scratch `$HOME` (per the
project's own test convention — see `tests/unsync.test.sh`), so none of it
touched the machine's real configuration.

## 1. Install

```bash
TH=$(mktemp -d)
git clone https://github.com/aminrasooli/ai-dev-autopilot.git "$TH/.ai-dev"
HOME="$TH" make -C "$TH/.ai-dev" sync
```

Real output (abridged — full file tree matches the list in README's
"Try it in five minutes"):

```
claude
  write $TH/.claude/CLAUDE.md (expanded from adapters/claude/CLAUDE.md)
  ok    every CLAUDE.md import resolves
  link  $TH/.claude/skills/codex-council -> .../skills/codex-council
  link  $TH/.claude/skills/project-bootstrap -> .../skills/project-bootstrap
  merge $TH/.claude/settings.json (hub-owned keys applied, your preferences kept)
  ok    every registered hook resolves to a readable script
...
launcher
  link  $TH/bin/aidev -> $TH/.ai-dev/bin/aidev

done
  backups: $TH/.ai-dev-backups/20261017-232327
```

## 2. The three decisions

The `claude` CLI needs its own authenticated, interactive terminal session, so
it cannot be driven non-interactively inside this capture. Instead, this sends
each hook the exact PreToolUse/PermissionRequest JSON that Claude Code sends,
to the exact scripts `make sync` just installed — the real artifacts, not a
paraphrase of what they do. Anyone can reproduce this:

```bash
GUARD="$TH/.ai-dev/hooks/security-guard.sh"
BROKER="$TH/.ai-dev/hooks/permission-broker.sh"
cd "$TH" && mkdir project && cd project && git init -q .

# 1. routine work: allowed
jq -nc --arg cwd "$PWD" '{hook_event_name:"PreToolUse",tool_name:"Bash",cwd:$cwd,tool_input:{command:"ls"}}' \
  | HOME="$TH" bash "$GUARD"              # (no output: PreToolUse passes)
jq -nc --arg cwd "$PWD" '{hook_event_name:"PermissionRequest",tool_name:"Bash",cwd:$cwd,tool_input:{command:"ls"}}' \
  | HOME="$TH" bash "$BROKER"

# 2. credentials: blocked
jq -nc --arg cwd "$PWD" '{hook_event_name:"PreToolUse",tool_name:"Bash",cwd:$cwd,tool_input:{command:"cat ~/.ssh/id_rsa"}}' \
  | HOME="$TH" bash "$GUARD"

# 3. privilege escalation: stopped for a human
jq -nc --arg cwd "$PWD" '{hook_event_name:"PreToolUse",tool_name:"Bash",cwd:$cwd,tool_input:{command:"sudo whoami"}}' \
  | HOME="$TH" bash "$GUARD"
```

Real output:

```
$ # 1. ls — PreToolUse: no output (pass); PermissionRequest:
{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow"}}}

$ # 2. cat ~/.ssh/id_rsa
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"[cred-path] Blocked: this path holds credentials, keys, browser profiles or a password store. AI-DEV never reads it. If the human needs it, they do it themselves."}}

$ # 3. sudo whoami
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"[sudo] Elevated privileges. Confirm this is what you want."}}
```

Inside an actual Claude Code session these decision objects are what turns
into, respectively: the command simply running, a refusal message in the
transcript, and a permission dialog that waits for a human to approve or
deny.

## What this does and doesn't show

This proves the decision-making artifacts — the exact scripts and the exact
JSON shape Claude Code's hook contract defines — produce the three decisions
README promises, from a hub that was just cloned and synced into a scratch
home. It does not capture `claude`'s own rendering of a blocked message or a
permission dialog, since that needs an interactive terminal; `tests/hook-contract.test.sh`
is what pins that the decision shape above is exactly what the installed
Claude Code build parses.
