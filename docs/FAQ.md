# FAQ

Every answer here is backed by something checkable in this repository — a
README section, a test, or a script. If an answer here and the file it cites
ever disagree, the file wins.

**What is this, in one sentence?**
A guard and permission broker that lets Claude Code (and optionally Codex or a
local model) run routine development commands without asking, while stopping
for a human on anything consequential — see the top of
[README.md](../README.md) and the allow/stop table right under it.

**What is this *not*?**
Not a coding agent itself, not a router that picks which model does a task,
and not the "AI Engineering Manager" described in
[docs/NORTH_STAR.md](NORTH_STAR.md) — that is the long-term direction, and
`README.md`'s "Why it's built this way" section says plainly that none of it
is built yet.

**What do I need to run it?**
Linux (developed and tested on Ubuntu 24.04), Claude Code on a plan that
supports sandboxing, `bash` 5+, `git`, `jq`, `python3`, and `bubblewrap` +
`socat` for the OS sandbox. Full list: README's
[Requirements](../README.md#requirements) section.

**Why does it ask for `sudo`?**
Only `make deps` (installing `bubblewrap`/`socat`) and `make manage`
(deploying the managed enforcement floor to
`/etc/claude-code/managed-settings.d/`) use `sudo`, and `bin/ai-dev` prints
that before running either. `make sync` — the one you need to try the project
— never does. See `do_manage()` in [`bin/ai-dev`](../bin/ai-dev).

**What does `make sync` actually change on my machine?**
`~/.claude/CLAUDE.md`, a merge into `~/.claude/settings.json`,
`~/.claude/skills/*` (symlinks), `~/.codex/*` if Codex is installed, a systemd
user unit for Remote Control, and an `aidev` launcher on your `PATH`. Every
file it overwrites is backed up first to `~/.ai-dev-backups/<timestamp>/`. See
`do_sync()` and the `sync_*` functions in [`bin/ai-dev`](../bin/ai-dev), and
[tests/unsync.test.sh](../tests/unsync.test.sh), which asserts this list by
syncing a scratch home and checking what exists afterward.

**What does `make manage` add that `make sync` doesn't?**
A managed-settings file at `/etc/claude-code/managed-settings.d/`: a sandbox
floor, credential denies, and a bypass-mode lock that no project or user
setting can override — see the "Architecture" section of
[README.md](../README.md#architecture). It needs `sudo` because it writes
outside your home directory.

**How do I remove it?**
[README.md's "Remove it"](../README.md#remove-it) section: `make unmanage`
(if you ran `make manage`), `make unsync` (undoes `make sync`), then
`rm -rf ~/.ai-dev`.

**Something's wrong — Claude Code won't start, or a hook misbehaves. Now what?**
[README.md's "If something goes wrong"](../README.md#if-something-goes-wrong)
section covers a broken `settings.json`, a hook that blocks something it
shouldn't, and rolling back to the previous release.

**What do "blocked", "asked" and "allowed" actually look like?**
[README.md's "Try it in five minutes"](../README.md#try-it-in-five-minutes)
section shows the exact message for each of the three outcomes, with the
commands that produce them.

**Does it send my data anywhere?**
No telemetry of its own. `sandbox.network.strictAllowlist` restricts a
sandboxed session's own network egress to an explicit domain allowlist — see
the "What is configured, and countable" list in
[README.md](../README.md#what-makes-it-different). Remote Control, if you
enable it, honors the same `DISABLE_TELEMETRY`/`DO_NOT_TRACK` environment
variables Claude Code does — see
[docs/remote-control.md](remote-control.md).

**How is this tested?**
Every claim in README's "Evidence" section is backed by a test suite that
runs with `make test`, on a machine where neither Claude Code nor Codex is
installed — see the suite table there and
[docs/verification.md](verification.md) for how the three verification layers
(`tests/*.test.sh`, `bin/doctor`, `bin/host-check`) divide the work.

**How do I report a bypass versus a bug?**
A bug is something documented that doesn't hold — open a regular issue with
the **Bug report** template. A bypass — getting past something the
[Hard human boundaries](../README.md#hard-human-boundaries) table says is
human-only — is a security report: report it privately, per
[SECURITY.md](../SECURITY.md). [SUPPORT.md](../SUPPORT.md) lays out both
paths.

**Does this work with anything besides Claude Code?**
Yes: Codex CLI is an optional independent reviewer by default, a local
open-weight model through Ollama or Claude Code itself can take that role
instead (see "The Local Reviewer Benchmark" in README), and `generated/AGENTS.md`
is read by any AGENTS.md-aware agent, including an experimental Qwen Code
adapter — see [`adapters/qwen/README.md`](../adapters/qwen/README.md).

**What happens if I use `--dangerously-skip-permissions` or a similar flag?**
It's refused, in every spelling, by `bin/aidev` and by the managed floor (so it
is refused even for bare `claude`, not only through the launcher) — see
"Why not `--dangerously-skip-permissions`?" in README and
[`tests/permission-posture.test.sh`](../tests/permission-posture.test.sh).

**Is this audited, or safe to treat as a hard security boundary?**
No. It's an experimental prototype that has not been independently audited —
see README's [Security limitations](../README.md#security-limitations)
section for what it does and does not claim.
