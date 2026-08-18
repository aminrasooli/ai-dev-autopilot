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

## The rule for splitting a command into clauses

The broker allows nothing as a whole. It splits the command, recognises every
clause individually, counts them, and allows only when the counts match. That
proof is worth exactly as much as the split is faithful, and a split is faithful
only if it agrees with the shell about two things:

- **Where a clause ends.** `&&`, `||`, `;`, `|` and `&`, plus an unquoted
  newline. `&` is the one that was missing, and missing it does not lose a
  clause — it turns the next command into *arguments of the previous one*, which
  is the shape that gets allowed rather than escalated. The exception is
  redirection, where `&` belongs to the operator: `&>file`, `2>&1`, `>&2`,
  `<&3`. Claude Code's own permission engine splits on the same set, so a
  disagreement here is also a disagreement with the layer whose dialogs this
  hook answers.
- **Where a clause begins.** The first word is the command only when it is a
  command. `(`, `{`, `!`, `if`, `then`, `elif`, `else`, `do`, `while`, `until`,
  a loop header and a `VAR=value` assignment all stand in front of it. Anything
  that dispatches on "the first word" — the family grammars, the curl screen,
  the refuse list in `broad_safe_ok` — is looking at the wrong word until they
  are stripped.

So `clause_head` answers three ways rather than two: a command remains, the
clause runs nothing (`fi`, `done`, a closing brace, a redirection on its own),
or it cannot be taken apart. The third is not a curiosity — `case x in a) rm -rf
~` carries a command with no separator in front of it, and a keyword whose
grammar is not modelled here escalates rather than being read as argv[0] with
harmless-looking operands.

Two consequences for anyone extending it:

- **A prefix that changes what a command IS must be screened where it is still
  visible.** The `LD_PRELOAD`/`PATH`/`GIT_CONFIG_*` screen used to sit in
  `broad_safe_ok`, one layer below the strip that removed the names it looked
  for, so it never ran at all. It lives in `seg_ok` now, above the dispatch, and
  applies to every clause whichever classifier it goes on to reach. Any new
  screen for a leading token belongs there for the same reason.
- **Adding a keyword to the "runs nothing" set is a claim, not a convenience.**
  It says the clause executes no command, so nothing in it is ever classified.
  Get that wrong and the clause disappears from the proof entirely.

`tests/approval.test.sh` section 16f drives a copy of the shipped broker with
the three corrections reverted and asserts the pre-fix `allow` for every payload
before asserting the fix, and it carries the positive controls — `2>&1`, `&>`,
a trailing `&`, a quoted ampersand, brace groups, subshells, loops and
conditionals over routine work — that keep the split from becoming a tax on
ordinary shell.

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

**The broker's own bound is a different quantity, and it needs its own ceiling.**
The two byte limits bound the guard because the guard's cost is one scan per
rule over the subject. The broker's cost is per *clause* — each is decomposed,
dispatched and canonicalised with its own subprocesses — so a command of many
short clauses sits far inside the byte ceiling while costing far more: measured
against the 20 s timeout the fragment registers for it, 400 clauses took 7.1 s
and a 64 KiB command of clauses took 43 s. `AI_DEV_MAX_CLAUSES` (default 64,
~1.2 s) caps the quantity that actually drives the cost. A cancelled broker is
less dangerous than a cancelled guard — no decision means Claude Code asks the
human — but not harmless: unattended there is no human, so a cancelled broker
raises a dialog for nobody instead of denying and queueing. Adding per-clause
work means re-measuring, the same as adding a guard rule does.

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
