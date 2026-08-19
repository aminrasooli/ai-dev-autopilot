# Contributing

Contributions, testing, simplification and alternative implementations are all
welcome — so are issues that just report where the framework's claims and its
behaviour disagree.

## Before you start

Two files hold the context that pull requests here are reviewed against:

- [NOTES.md](NOTES.md) — the standing rules for the parts of the framework that
  are easy to widen by accident: the classifier, path-based security rules,
  command matching, work budgets, and what tests must prove.
- [.ai/decisions.md](.ai/decisions.md) — what was decided, on what evidence, and
  what was deliberately not done. If your idea was already considered, this is
  where you find out why it went the way it did.

The short version of the rules, from the [README](README.md#contributing):

1. Never weaken, skip or delete a test to make a suite pass.
2. Every widening arrives with regressions — the example that motivated it, the
   unattended behaviour, and positive controls proving the fast path survived.
3. A test that proves a boundary must also prove the attack is real.
4. Security rules resolve paths through `$AI_DEV_HOME` and `$HOME`, never as
   hardcoded literals.
5. New classifier doubt defaults to escalation. Deterministic rules are added
   only when a safe operation becomes materially frequent.
6. Edit `core/`, never `generated/AGENTS.md`.

## Working on the code

```sh
git clone https://github.com/aminrasooli/ai-dev-autopilot
cd ai-dev-autopilot
make test        # the full contract suite, no deployment required
```

The suite is designed to run on a machine where AI Dev Autopilot has never been
deployed: checks whose subject is not installed report `PENDING` or defer by
name, and that is a normal result, not a failure. `make sync` is **not** needed
to develop or test — it writes into `~/.claude` and `~/.codex`, so only run it
if you actually want the framework active on your machine.

Before opening a pull request:

```sh
make generate    # regenerates generated/ from core/ — CI fails if you forget
make test
shellcheck -S warning hooks/*.sh bin/* tests/*.sh
```

`shellcheck` exclusions live in [.shellcheckrc](.shellcheckrc), each with a
reason; add a new exclusion only with one.

## Pull requests

- Keep a PR to one change with its tests and its documentation. The repository
  history is written so each commit answers "why" on its own; aim for that.
- If you change what the broker or guard decides, say what was measured before
  and after — the test suite's baseline pattern (revert the fix, prove the old
  behaviour, then prove the new) is the house style for behaviour changes.
- CI runs the contract suite, a parse check, `shellcheck`, and a check that
  `generated/` is current with `core/` on every PR.

## Issues

Use the issue forms for bug reports and hardening proposals, or open a blank
issue if neither fits. Good bug reports name the file that misbehaved, the
smallest reproduction you have, and the Claude Code version — much of what this
project asserts is measured against vendor behaviour that changes between
releases.

## Security

**Do not report vulnerabilities in public issues.** Anything that reaches an
allow for a documented human-only boundary, makes the broker fail open, or lets
a checked-out repository influence the session that inspects it belongs in
[GitHub Private Vulnerability Reporting](SECURITY.md) — see
[SECURITY.md](SECURITY.md) for scope and what to include.
