# Remote Control — drive this workstation from another device

Remote Control connects claude.ai/code or the Claude mobile app to a Claude Code
session **running on this workstation**. Execution, the filesystem and MCP
servers stay local; the phone or second computer is only the interface. That is
the opposite of Claude Code on the web, which runs in the cloud.

`claude remote-control --help` returns the flag list only for an eligible
account, which is the quickest way to check whether yours is.

## Start one by hand

```bash
cd ~/projects/thing
~/.ai-dev/bin/ai-dev remote            # == claude remote-control --sandbox --spawn same-dir
```

Press space in the terminal for a QR code, or open the session from
claude.ai/code. Useful flags to pass through:

| Flag | Effect |
|---|---|
| `--name "thing"` | name the session in the claude.ai list |
| `--spawn worktree` | each on-demand session gets its own git worktree |
| `--spawn session` | serve exactly one session, reject the rest |
| `--capacity N` | cap concurrent sessions (default 32) |
| `-c` | resume the last session from this directory |

To turn an interactive session you are already in into a remote one, type
`/remote-control`.

## Start one at login

A systemd **user** unit template is installed at
`~/.config/systemd/user/ai-dev-remote@.service`. It is deliberately **not
enabled**: a permanently listening remote-control server is a standing surface,
so switching it on is your decision, not the framework's.

```bash
# enable for one project directory
systemctl --user enable --now \
  ai-dev-remote@$(systemd-escape -p "$HOME/projects/thing").service

systemctl --user status  ai-dev-remote@*.service
journalctl --user -u     'ai-dev-remote@*' -f

# turn it off
systemctl --user disable --now ai-dev-remote@$(systemd-escape -p "$HOME/projects/thing").service
```

It starts when you log in. It does **not** survive a logout unless you also run
`loginctl enable-linger "$USER"`, which is a separate decision — that makes the
server reachable whenever the machine is powered on, with nobody at the keyboard.

The unit caps memory at 8G and tasks at 512 so a runaway session cannot take the
workstation down.

## Requirements and constraints

- Pro, Max, Team or Enterprise plan; API-key auth is not supported.
- Not available on Bedrock, Vertex/Agent Platform, Foundry, or when
  `ANTHROPIC_BASE_URL` points somewhere other than `api.anthropic.com`.
- `DISABLE_TELEMETRY`, `DO_NOT_TRACK`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`
  and `DISABLE_GROWTHBOOK` each disable the feature-flag evaluation Remote
  Control depends on. Do not set them in `~/.claude/settings.json`.
- Start from a **project directory**. The startup trust dialog is never saved
  for the home directory.
- `disableRemoteControl` in settings turns the feature off entirely. It is not
  set here.

## Security

Remote sessions obey exactly the same boundaries as local ones: the sandbox, the
permission rules, and the PreToolUse guard all apply, because it is the same
local Claude Code process. `ai-dev remote` passes `--sandbox` explicitly rather
than relying on the default, which is off for server mode.

Anyone who can sign in to your claude.ai account can drive a running remote
session on this machine. That is the whole security boundary. Keep the account
on a strong second factor, and prefer starting the server by hand for a session
over leaving it enabled with lingering.
