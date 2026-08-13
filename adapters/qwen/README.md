# Qwen Code adapter — documented, not installed

Nothing here installs Qwen Code. `bin/ai-dev sync` detects the `qwen` binary and
skips this adapter when it is absent, so the adapter is inert unless you have
installed Qwen Code yourself.

    $ command -v qwen    # empty output means the adapter is skipped

## If you install it later

Install it yourself (`npm install -g @qwen-code/qwen-code` at the time of
writing — check the current official instructions first), then run:

    make -C ~/.ai-dev sync

`ai-dev sync` will link the generated policy into `~/.qwen/`.

## What the adapter does

Qwen Code is a Gemini-CLI derivative and reads a project/user context file. The
sync step links `~/.ai-dev/generated/AGENTS.md` — the same file Codex reads,
generated from `core/` — into `~/.qwen/`.

**Verify the filename against the current Qwen Code documentation before
trusting it.** Qwen Code has used `QWEN.md` as its context filename and supports
`AGENTS.md`-style discovery depending on version and the `contextFileName`
setting in `~/.qwen/settings.json`. If your version wants `QWEN.md`, add a second
symlink rather than a copy:

    ln -s ~/.ai-dev/generated/AGENTS.md ~/.qwen/QWEN.md

and add the check to `bin/doctor` so drift is caught.

## Boundaries that apply to Qwen too

Qwen Code has its own approval and sandbox settings, and they are **not**
covered by Claude Code's managed settings or by the PreToolUse guard. Before
using it for real work:

1. Confirm its approval mode is not auto-approving shell commands.
2. Confirm its sandbox setting, and enable it.
3. Confirm no credential environment variables are inherited by its subprocesses.
4. Add a `doctor` check for each of those, so they are contracts and not
   intentions.

Until those checks exist, treat Qwen Code as an experiment, not a third agent
with equal standing.
