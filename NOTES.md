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

## The rule for matching a command

Both hooks decide by matching a command string, and the string they are handed
is not the string the shell runs. The shell performs quote removal, escape
removal and line-continuation joining as part of word expansion, so `su""do`,
`"sudo"`, `su\do` and `su\<newline>do` are one word by the time anything is
looked up.

So every rule is matched against **two views**, and a match in either counts:

- `$NORM` — the command as written, with `~`, `$HOME` and `$AI_DEV_HOME`
  resolved.
- `$QNORM` — the same command after `shellwords`, i.e. as the shell will run it.

Two consequences for anyone adding a rule:

- **Write the rule for the plain spelling.** The second view is what makes it
  hold for the spliced ones; a rule that tries to anticipate quoting itself is
  the shape of the bug, not a fix for it.
- **Matching either view can only add a decision.** That is what makes this safe
  to extend, and it is the reason the views are ORed rather than the haystack
  being replaced. Do not "simplify" it into a single stripped subject: rules
  bound to a clause (`[^|;&]*`) would then see separators that were quoted data.

`shellwords` is deliberately scoped. A quoted run with **no whitespace** in it
is collapsed, because its only effect is to splice; a quoted run that contains
whitespace is one argument whose interior is data and is left alone. That scope
is what keeps `echo "sudo is required"` from raising a dialog, and it is
asserted by positive controls rather than assumed. What is **not** modelled, and
should not be added without a measurement: ANSI-C `$'...'` escapes, substring
expansions and variable indirection — the shell decodes those from values, and
this layer matches punctuation.

In `hooks/permission-broker.sh` the same reading applies one level down, at the
token level, where it is unambiguous: `unword` for the name a clause dispatches
on, and inside `canon` for every path a containment decision rests on. A path
policy that reasons about `<cwd>/"$HOME"` is not reasoning about anything.

## The rule for the guard's work budget

`hooks/security-guard.sh` runs as a `PreToolUse` command hook, and Claude Code
cancels a command hook that reaches its timeout: the output is discarded, the
hook renders **no decision**, and the tool call continues through the normal
permission flow. A guard that is merely slow is therefore not a guard that denies
late. It is no guard at all, and nothing on screen says so.

So the guard is bounded rather than trusted to be quick:

- Every rule is a scan of the whole subject, so a new rule is a new pass over it.
  Adding rules costs time linearly, and the time is spent against a fixed
  deadline. Measure, do not assume.
- The two ceilings — `AI_DEV_MAX_INPUT_BYTES` and `AI_DEV_MAX_SUBJECT_BYTES` —
  are what turn "how long does this take?" into a bound. They are checked with a
  bash string length before any scan, so they are free. Do not move the check
  below the first substitution: bash parameter substitution on a long string is
  itself superlinear.
- Raising either ceiling is a change to the security posture and needs the
  measurement to go with it. `bin/doctor` (`guard:workbound`) re-measures on the
  machine it runs on, against the timeout registered in the *deployed* settings,
  and fails if the worst admitted case exceeds half the budget.
- The broker reads the same two variables. Keep them in step; two layers that
  disagree about what is screenable is a gap in the shape of an argument.

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
- `PENDING` is not a pass either, and it is not a failure. It means the check's
  subject is not installed on this machine, which is true of every check that
  inspects `~/.claude`, `~/.codex`, `/etc` or `$PATH` before `make sync` has run.
  The line is one question — has this hub ever been synced here? — and a machine
  that HAS been synced and then drifted stays a failure. Adding a check outside
  the repository means routing its failure through `needs_sync` (or `needs_setup`,
  where something other than `sync` installs it) and extending
  `tests/doctor-reporting.test.sh`. A category that could be reached by deleting a
  file would be a way to make findings disappear.
