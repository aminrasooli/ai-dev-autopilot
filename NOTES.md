# Design notes for contributors

Policy lives in `core/`. Decisions and their evidence live in `.ai/decisions.md`.
This file holds the standing rules for changing the parts of the framework that
are easy to widen by accident.

## The rule for classifier changes

The classifier is `hooks/permission-broker.sh`. Every change to it is measured
against one rule:

> New classifier doubt defaults to escalation. Deterministic rules are added
> only when a safe operation becomes materially frequent.
>
> Rules for certainty. Codex for judgment. Human for consequences.

In practice:

- A deterministic rule is a claim that an operation is *provably* safe from its
  arguments alone. If the proof needs a parser that races something the tool
  itself owns — git's URL grammar, a shell's quoting, a config file's include
  chain — there is no proof, and the class is demoted rather than parsed. The
  git transport class was demoted for exactly this reason: `git fetch origin`
  runs whatever `remote.*.url` and `url.*.insteadOf` say it runs, and none of
  that appears in the argv.
- Frequency, not elegance, is the reason to add a rule. One dialog a week is
  cheaper than a parser nobody re-reads.
- Anything behind the mechanical security boundary — network egress, privilege,
  credentials, publication, destruction — escalates above Codex, so no Codex
  verdict can turn it into an allow. Do not move a screen below section 6 of the
  broker to make it "smarter".
- Every widening and every demotion arrives with regressions in
  `tests/approval.test.sh`: the exact example that motivated it, the unattended
  behaviour, and the positive controls proving the fast path survived.

## The rule for path-based security rules

A security rule that names a path must resolve it the way the rest of the
framework does — `$AI_DEV_HOME` for the hub, `$HOME` for the user — never as a
hardcoded literal. A rule written as `~/.ai-dev` is correct only for the default
installation and silently absent everywhere else, which is the worst failure mode
a control can have: present in review, missing in operation.

The same rule applies one layer up, to the configuration that decides whether a
control runs at all. `adapters/claude/settings.fragment.json` carries two
placeholders — `__AI_DEV_HOME__` for anything inside the hub, `__HOME__` for
anything in the user's home — and they are not interchangeable. A hub path
written as `__HOME__/.ai-dev/...` resolves to a directory that does not exist for
anyone who cloned somewhere else, and a hook registered at a path that does not
exist does not error: it never runs, and the enforcement layer is gone with
nothing reporting it. `bin/ai-dev sync` refuses to write a settings file with a
surviving placeholder or an unreadable hook command, and `bin/doctor` re-checks
existence on every run.

`tests/guard-portability.test.sh` pins both by installing a hub somewhere else
entirely: section 1–9 assert the guard's own rule holds in both directions, and
section 12 expands the shipped fragment against that hub and asserts every
registered hook resolves to a real file there. Extend it when you add another
path-based rule, or another path to the deployed configuration.

## The rule for tests

- A test that proves a boundary must also prove the attack is real. Every
  isolation test carries a baseline assertion that the payload *does* land
  without the control, so the test cannot quietly stop proving anything.
- Never weaken, skip or delete a failing test to make a suite pass. If a check
  cannot be answered in the environment it is running in, it defers by name and
  says which command answers it — it does not guess.
- `KNOWN` is not a pass. It is reserved for a limitation that cannot be fixed
  here, and only after the compensating control has been re-verified in the same
  run.
