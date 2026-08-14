# Decisions

Why the load-bearing parts of AI Dev Autopilot are shaped the way they are, the
alternatives that were considered and rejected, and the uncertainty that remains.

Organised by topic. Each entry states the problem, the options, what was chosen,
what evidence supports it, and what could invalidate it. Where a decision is
pinned by a test, the test is named — a decision that is only written down is an
intention, and a decision with a regression behind it is a contract.

---

# Session isolation

## Settings scope: `--setting-sources user`, not `--safe-mode` or `--bare`

**Problem.** A cloned repository must not be able to supply instructions,
skills, agents, commands, hooks, MCP integrations, output styles or security
policy to a session started inside it. It may supply source code and ordinary
project files, and those are data.

**Options.**

- **A. `--setting-sources user`** — select the user scope and nothing else, then
  add only the controls behavioural evidence shows are missing.
- **B. `--safe-mode`** — disable all customizations, then rebuild the AI-DEV
  security guard in managed policy and restore trusted functionality explicitly.
- **C. `--bare`.**

**Evidence.** `tests/project-isolation.test.sh` measures this rather than
inferring it, reading Claude Code's own `system/init` event instead of trusting
silence:

- Without the flag, a hostile repository's skill, custom command and subagent
  are all registered; its `.mcp.json` server is registered *and its process
  spawned*; its `UserPromptSubmit` hook *executes*. The attack is real and
  reaches code execution.
- With the flag, none of it: no skill, no command, no agent, no MCP
  registration, no MCP process, no plugin, no output style, no hook, no status
  line, and no read of the project's `CLAUDE.md`, `CLAUDE.local.md`,
  `.claude/rules` or settings files.

So the flag is broader than its name and broader than its documentation, which
corroborates it only in places — project rules "are skipped if you exclude
`project`", project `.mcp.json` can be excluded "entirely with
`--setting-sources`" — without ever stating the full extent.

Option B's cost is concrete: `--safe-mode` disables *all* customizations and
keeps only managed-policy hooks. The AI-DEV PreToolUse guard is a **user** hook,
so safe mode switches off the enforcement layer, and B only returns to level once
that layer has been rebuilt in managed policy. Option C is excluded outright:
`--bare` never reads OAuth or the keychain, so authentication would have to
become an API key — a credential this framework denies by design.

**Decision: A.**

**Confidence: high for the measured version, deliberately low for the next.** The
whole boundary rests on one flag whose documented description is narrower than
its observed behaviour, which is exactly the kind of thing a release can quietly
change. Mitigated by holding it as a contract test that fails loudly rather than
as an assumption. **Re-run after every Claude Code upgrade.**

**Known uncertainty.** The test proves what is *loaded*. It cannot also prove a
model would disobey a hostile instruction, because a nested session cannot
authenticate and no model turn runs. Accepted: an instruction that never enters
the context window cannot be obeyed, and that was always the stronger of the two
properties.

**Links.** `bin/aidev` · `tests/project-isolation.test.sh` ·
`tests/fixtures/hostile-project/README.md`

## An unverified isolation boundary blocks activation

**Problem.** `bin/activate-approval-broker` switches on a component whose job is
to answer permission dialogs without asking anyone. What must be true before that
is allowed?

**Decision.** `tests/project-isolation.test.sh` is **mandatory** in the
activation suite. Absent, or exiting 3 because it could not establish its
baseline, fails activation with nothing synced. Other suites may still skip on a
missing local dependency.

**Why exit 3 is a failure for this suite specifically.** For other suites it
means "a dependency for measuring this is unavailable". For this one it means
"the attack could not be shown to work", and a test that never sees the attack
land cannot tell isolation from a broken probe. Switching on a component that
says "yes" on a human's behalf, on top of a boundary in that state, is the wrong
order.

**Confidence: high.** Verified against a shadow hub in all three states —
missing, exit 3, and passing — and in the first two the run stops before
`make sync`.

**Links.** `bin/activate-approval-broker` · `tests/project-isolation.test.sh` ·
`tests/approval.test.sh`

---

# Permission posture

## Bypass mode is blocked in managed policy, not only in the launcher

**Problem.** A launcher can refuse `--permission-mode bypassPermissions`, but
only for people who use the launcher. Anyone typing `claude` walks around it.

**Options.**

- **A. Blacklist the dangerous values in the launcher.**
- **B. Allowlist the safe modes in the launcher.**
- **C. Enforce it in managed settings**, where no other scope can override it.

**Evidence.** Claude Code documents
`permissions.disableBypassPermissionsMode: "disable"` and notes these controls
are *"most useful in managed settings where they can't be overridden"*. Of the
full mode set, only `bypassPermissions` widens the posture: `dontAsk`
**auto-denies** unless pre-approved, so it is stricter than the default, not
looser.

**Decision: C, with B in front of it.** C is the control — it applies to bare
`claude`, to every settings scope, to both flag spellings and to the Shift+Tab
cycle. B makes the launcher fail fast with a reason a human can act on, and being
an allowlist it refuses unknown future modes instead of forwarding them. A is
rejected on principle: a blacklist on one entry point is the shape of the bug,
not a fix for it.

The launcher additionally refuses `--settings`, `--agents`, `--mcp-config`,
`--plugin-dir` and `--plugin-url`, which inject configuration that
`--setting-sources` does not govern.

**Confidence: high.** `tests/permission-posture.test.sh` covers every spelling,
confirms the six safe modes still work, and checks the managed layer separately
so a control defined in the hub but not deployed on the machine reports its own
status instead of passing.

**Links.** `bin/aidev` · `adapters/claude/managed-settings.json` ·
`tests/permission-posture.test.sh`

## A build that would ignore a control refuses to start

**Problem.** `sandbox.network.strictAllowlist` is what makes the domain
allowlist a control rather than a suggestion: without it an off-allowlist host
merely *prompts*, and a non-interactive sandboxed command has nothing to prompt
with, so only the explicit `deniedDomains` entries are refused. It is honoured
from Claude Code 2.1.219. On anything older the key parses, is discarded, and
the network posture reverts — with no warning, no log line, and a settings file
that still reads `strictAllowlist: true`.

That is not a hypothetical. `claude` auto-updates, but it also downgrades
(`--version` pinning, a distribution package, a machine that never upgraded, a
CI image built months ago), and the whole framework is designed to be deployed
onto machines other than the author's.

**Options.**

- **A. Check the version in `bin/aidev`.** A check on one entry point; `claude`
  typed directly walks around it, which is the shape this project already
  rejected for bypass mode.
- **B. Check it in `bin/doctor`.** Reports, but does not enforce, and only when
  somebody runs it.
- **C. `requiredMinimumVersion` in managed policy.** Claude Code exits at
  startup, before the session exists.

**Decision: C, with B alongside it.** The mechanism was verified against the
2.1.232 binary rather than taken from the documentation, which does not describe
it beyond noting it fails open on an invalid value: the check reads
`policySettings` only, compares with semver, writes the message to stderr and
calls `process.exit(1)`. Crucially, `update`, `install` and `doctor` are exempt,
so a machine pinned below the floor can still upgrade its way out — which is
what makes a hard version gate safe to ship. B stays because the floor is only
deployed by `make manage`, and a floor defined in the hub but absent from
`/etc` protects nothing; doctor checks the *running* build either way.

Not chosen: `requiredMaximumVersion`. Pinning an upper bound would block the
upgrades this project explicitly asks people to make, and the correct response
to a new release is to re-run `project-isolation.test.sh`, not to refuse it.

**Confidence: high.** `tests/permission-posture.test.sh` section 7 pins the
number to its reason rather than to itself: it asserts the declared floor is at
least the version `strictAllowlist` needs, and carries a positive control that
the hub still deploys `strictAllowlist` at all — without which the floor would
be pinning nothing. It also reports, rather than asserts, whether the installed
build satisfies the floor, because that is an operator fact and not a contract.

**Links.** `adapters/claude/managed-settings.json` ·
`tests/permission-posture.test.sh` · `bin/doctor`

## `--add-dir` is refused at the front door, not only one level down

**Problem.** `bin/aidev` refused five configuration-injection flags and passed
`--add-dir` straight through. It does two things, and both are the launcher's
subject:

- It grants tool access to another directory. With
  `sandbox.autoAllowBashIfSandboxed`, a sandboxed command writing inside an
  allowed directory is approved with **no dialog** — so the flag widens the set
  of paths that change without anyone being asked, which is the single property
  the posture exists to control.
- Claude Code's own `--bare` help names it as the way to supply additional
  "CLAUDE.md dirs", so it loads instructions from a tree that went through none
  of the vetting `--setting-sources user` performs.

`hooks/permission-broker.sh` (`claude_ok`) already refuses to hand `--add-dir`
to a *nested* claude session. So the judgement was made; it was simply absent
from the entry point where a human types it — a control enforced one level down
and not at the front door, which is a control with a documented way round it.

**Options.**

- **A. Pass it through**, on the grounds that the broker still contains the
  consequences. It partly does — `in_ws` is anchored on the git root, so an
  added directory fails `ws_ok` and escalates — but the sandbox's own auto-allow
  path does not go through the broker, so this is a claim about one layer while
  the widening happens in another.
- **B. Accept it with a loud warning**, as `--trust-project` does.
  `--trust-project` earns that treatment by being a flag this project invented
  whose entire meaning is "I accept the consequences". `--add-dir` is a Claude
  Code flag whose consequences are not on its label.
- **C. Refuse it**, consistently with the other five, and name both effects.

**Decision: C.** The message states what it would do and offers the two real
alternatives: start the session from a directory containing both trees, or run
`claude --add-dir` directly and own it. That is the same shape as the refusal
for `--settings`, and it keeps the escape hatch outside the launcher rather than
inside it.

**Confidence: high for the refusal, medium for the completeness of the list.**
`tests/permission-posture.test.sh` section 5 pins both spellings and the
multi-value form, with a positive control that an ordinary passthrough flag is
still forwarded — without which the assertions would also pass for a launcher
that had started refusing everything. The list itself is enumerated from
`claude --help` on the installed version, so a flag added by a future release is
passed through until someone reads the changelog. That is the standing weakness
of an entry-point denylist, and the reason the managed floor, not the launcher,
is where the load-bearing refusals live.

**Links.** `bin/aidev` · `hooks/permission-broker.sh` ·
`tests/permission-posture.test.sh`

## Open: move the PreToolUse guard into managed policy

**Not done. Recorded so it is not lost.**

The security guard is registered in the **user** settings fragment. That covers
the launcher and bare `claude`, but not `claude --setting-sources project`, which
drops user hooks, and not `--safe-mode`, which keeps only managed hooks.
Registering the guard in managed policy would close both.

Deferred because it cannot be done safely in one step: hooks merge across scopes,
so registering it in both places risks double invocation, and registering it
*only* in managed leaves a window with no guard between the source change and the
privileged deploy. It needs a synced deploy plus a test of the merged behaviour,
in that order.

**Links.** `adapters/claude/settings.fragment.json` · `hooks/security-guard.sh`

---

# Delegated approval

## The broker is a PermissionRequest hook, not an extension of the guard

**Problem.** Without delegation the human becomes the routine approval engine —
dialogs for `git status`, for reading a file, for writing a test fixture, for
`chmod +x` followed by running the test it just made executable. A human clicking
"allow" forty times an hour is not reviewing anything.

**Options.**

- **A. Extend the PreToolUse guard** to emit `allow` for routine work.
- **B. A separate PermissionRequest hook.**

**Evidence.** `PermissionRequest` fires only when Claude Code is about to raise a
permission dialog, and may answer on the user's behalf via
`hookSpecificOutput.decision.behavior`. It also carries `addPermissionRule`, a
documented mechanism for batching same-shaped approvals. PreToolUse, by contrast,
fires for every tool call, before the permission check.

**Decision: B.** A is the smaller diff and the worse design. Folding "say yes"
into the file whose entire job is "say no" makes the precedence argument a matter
of reading control flow carefully. B makes it structural: a PreToolUse deny
blocks the call, so no dialog is raised, so PermissionRequest never fires, so
neither the broker nor Codex ever sees the request.
`bin/activate-approval-broker` enforces the separation mechanically — it greps
the guard for any reference to the broker and refuses to activate if it finds
one.

**The classifier must prove a positive.** Count clauses, count recognised
clauses, require equality and non-zero. The inverse design — assume "ok" and try
to falsify it clause by clause — fails **open**: any parsing degradation leaves
the flag set and the command is allowed. A silencer that fails open is worse than
none, because the human stops watching precisely because it exists. That
inversion is pinned by its own regression section, together with the related hole
that allowlisting a wrapper such as `timeout` would open — wrappers are stripped
and the wrapped command classified instead.

Codex is advisory and reached only for gray cases that already cleared the
critical and obfuscation screens. Fixed rubric, command fenced and labelled
untrusted data, two permitted tokens, hard timeout, and every failure mode —
unavailable, timeout, empty output, off-rubric answer — resolving to ESCALATE.
ESCALATE means "show the human the dialog" interactively and "deny and queue"
unattended.

**Links.** `hooks/permission-broker.sh` · `hooks/security-guard.sh` ·
`tests/approval.test.sh` · `bin/activate-approval-broker`

## Classify what a command does, not the name it starts with

**Problem.** An allowlist of leading executables is not a classification of
behaviour. `python3` names an interpreter; `python3 -c '<anything>'` is an
arbitrary program. `<repo>/../important-file` is not inside `<repo>`.
`printf x > .github/workflows/ci.yml` is not "printf".

**Options.**

- **A. Patch each example** — deny `-c`, special-case `..`, add one path to the
  edit-tool check.
- **B. Restate every class in terms of behaviour**, and check arguments against
  the behaviour the class is permitted.
- **C. Delegate more to Codex** — send anything not trivially recognised to the
  adjudicator instead of growing the deterministic layer.

**Evidence.** A per-example patch fixes the examples and nothing else. A
name-based classifier also approves `node --require /tmp/evil.js app.js`,
`python3 -m pip install`, `xargs rm -rf`, `make CC=/tmp/evil test`, a symlinked
directory inside the repository, and `rm -rf .` — none of which appear on
anybody's list of examples. The assertion set for this class fails against a
name-based classifier and passes against a behaviour-based one.

C is rejected on layering: Codex is advisory and its output is untrusted model
output (`core/security.md`). Widening what reaches it moves decisions from a
tested deterministic layer into one whose failure modes are "unavailable,
timeout, empty, persuaded". The deterministic layer must get *better*, not
smaller.

**Decision: B.** Classes state what they may do — read, write, destroy, run an
interpreter, reach a network — and arguments are checked against that. Notable
sub-decisions, each trading convenience for a property:

- **An interpreter's script must be inside the git repository**, not merely
  inside the workspace. `$TMPDIR` and the session scratchpad are workspace for
  *writing*; they are not a place code should be executed from without a human,
  because a script there is untracked, undiffable, and typically something the
  agent just generated. **Superseded** — see *The broad local-dev fallback*
  below. `interp_ok` remains in the broker, unwired, as the statement of this
  option.
- **`make` and `npm run` targets come from a fixed list.** The alternative —
  reading the repository's own `Makefile`/`package.json` to decide — makes the
  repository the policy author, which is the exact inversion `core/security.md`
  refuses everywhere else. **Partly superseded** — `make` still works this way
  and is enforced by `make_ok`; the package-manager half is not, and `pkg_ok`
  and `sub_ok` are unwired. See below.
- **`WebSearch` always escalates.** It has no destination that can be compared
  against `sandbox.network.allowedDomains`, and its results are
  attacker-influenced input. There is no version of "check the policy" for it.
- **Unresolvable is not allowed.** A path that cannot be canonicalized, a
  redirection target containing `$`, a quote or a backtick, an empty network
  policy — each returns not-allowed rather than a guess.

**Confidence: high for the classes named; medium for coverage.** An allowlist of
behaviours is still an allowlist. A command class nobody has modelled escalates
rather than being wrong, which is the correct failure, but it does mean the
usability of this layer improves only when someone adds a class deliberately.

**Links.** `hooks/permission-broker.sh` · `tests/approval.test.sh`

## Arguments decide, not the first word and not the verb

**Problem.** Reading *some* arguments is the same mistake one level deeper.
Three shapes make the point:

1. A programmable tool in a generic read allowlist is approved on its operands
   while `awk 'BEGIN { system("touch /tmp/pwned") }'` runs an arbitrary command.
2. Discarding every option-shaped token, on the assumption that a path does not
   start with `-`, approves `cp --target-directory=/tmp/outside f.txt` on the
   innocent operand left over.
3. Ignoring everything after an allowlisted git verb lets `git apply
   attack.patch` write a CI workflow file.

**Decision.**

- **Programmable tools are not read tools.** `awk`/`gawk`/`mawk`/`nawk` and
  `busybox` are named in an explicit reject list, where a future addition to a
  family list cannot resurrect them. `sed` keeps its capability but its SCRIPT is
  classified — one safe shape per command, so the `e` command, the `s///e` flag
  and `w FILE` have no way to match — and `-i` is detected in its own pass,
  because a trailing `-i` would otherwise be seen after the operands had already
  been checked as reads.
- **Every command reaching a family classifier declares its own argument
  grammar** (`opt_spec`), and `argv_ok` canonicalises the path in every form the
  shell accepts: `--opt=PATH`, `--opt PATH`, `-tPATH`, `-t PATH`. An option the
  grammar does not declare is unhandled, and unhandled escalates. Development
  tools' plugin and config options (`pytest -p`, `mypy --config-file`,
  `gcc -fplugin=`) are simply not declared, which is how they escalate.

**Why a grammar per command rather than a denylist of dangerous options.** A
denylist of `--output`-shaped names fails open on the first tool whose write
option is spelled differently. The cost is real and accepted: an unmodelled flag
costs one dialog, where an unmodelled `--output` costs a file.

**Known uncertainty.** The option specs cover the flags in common use, so an
unusual-but-legitimate flag escalates where a looser design would have skipped
it.

**Links.** `hooks/permission-broker.sh` · `tests/approval.test.sh`

## A git verb list is not a grammar

**Problem.** Splitting git verbs by what they can write, then screening their
arguments with one shared option denylist, is too coarse in both directions.
`branch` and `remote` are not verbs, they are dispatchers: `git branch -D
feature` deletes a ref, `git branch new-name` creates one, and `git remote
set-url origin URL` rewrites `.git/config`. And a shared denylist misses
`git commit -F /path/to/secret`, which reads an arbitrary file into repository
history, and `git add --pathspec-from-file=/tmp/list`, whose affected paths the
hook never sees.

**Options.**

- **A. Extend the shared denylist** with the missing option names.
- **B. Per-verb argument grammars**, reusing the `opt_spec`/`argv_ok` machinery.
- **C. Drop the mutating verbs entirely** — approve only `status`, `diff`, `log`
  and `show`.

**Decision: B.** A is the shape of the bug: a denylist of names nobody has
thought of yet is empty by definition. C would send `git add` and `git commit` —
the two most frequent commands in this workflow — back to the human on every
call, which is precisely the cost the broker exists to remove.

Each verb declares what it accepts, and an option outside that declaration
escalates:

- `branch` passes only in listing form, and an operand is a pattern only under
  `--list`, so `git branch new-name` has nowhere to land. `remote` dispatches on
  its subcommand: bare, `-v` and `get-url` pass; `add`, `rename`, `remove`,
  `set-url`, `set-head`, `set-branches` and `prune` write, and `show`/`update`
  reach the network.
- Everything that reads an external file (`-F`, `--template`,
  `--pathspec-from-file`), reuses another object's message (`-C`, `-c`), signs
  (`-S`, `-s`, `-u`), forces, deletes or opens an editor is absent by
  construction rather than denied by name.
- Operands get policies of their own: `pathspec` (a provable path inside the
  workspace, no magic and no glob), `refname` (a name that cannot be a URL, a
  path escape or revision syntax — this is what stops `git fetch
  https://host/repo`), `pattern` and `noop`. An unknown policy returns 1, so a
  typo cannot become a permit.
- **`git tag` creation escalates.** A tag is the artifact releases are cut from,
  and its creation options are the dangerous ones; listing is what is approved.
- **`git commit` escalates when the repository has a commit hook installed or
  sets `core.hooksPath`.** The hook is an arbitrary program whose intent this
  file cannot read. Writing one already escalates, but a hook can arrive with a
  clone, so presence is checked rather than assumed. `-C <dir>` retargets that
  check, because it retargets the command.
- **`git init --template=<dir>`** copies that directory's hooks into
  `.git/hooks`, where every later commit executes them. The option is simply not
  declared.

**Known uncertainty.** The grammars cover the flags in common use, so a
legitimate but unusual one (`git fetch --depth=1`, `git commit --no-verify`)
costs one dialog. `git add -A` and `-u` remain approvable although their affected
set is not stated on the command line: they stage what the repository already
contains and can add nothing from outside it, whereas a supplied pathspec is a
path the caller chose and must be proven.

**Links.** `hooks/permission-broker.sh` · `tests/approval.test.sh`

## Git transport is demoted, not parsed

**Problem.** Repository-local configuration is an execution channel for
transport. `.git/config` can set `remote.origin.url` to `ext::<command>`, and
`url.<base>.insteadOf` can rewrite an ordinary-looking remote into that same
channel. Either way `git fetch origin` — an argv containing nothing but a verb
and a remote name — executes a program the repository chose.

**Options.**

- **A. Prove the URLs non-executable.** Read `remote.*.url`, `remote.*.pushurl`,
  `url.*.insteadof` and `url.*.pushinsteadof`, resolve rewrites, classify the
  resulting scheme.
- **B. Demote the class.** Any git operation that may invoke a transport
  escalates. Leave the keys unparsed on purpose.

**Decision: B.** A is a race between a parser here and git's own URL grammar,
which git owns and can extend. The transport is decided by a *value*, and the
values are open-ended (`ext::`, `remote-<helper>`, `core.gitProxy`,
`remote.*.uploadPack`, a submodule URL, whatever ships next). Escalating the four
keys instead of the operation would also escalate `git status` in every
repository that has a remote, trading the entire local fast path for the same
coverage B gets for free.

Evidence that B is affordable: the transport class is a handful of prompts a
week, while everything run all day — status, diff, log, show, add, commit,
`switch -c`, branch and remote inspection — is untouched.

**What it means concretely.** `clone`, `fetch`, `pull`, `ls-remote`, `submodule`
(any form), `remote update|show|prune`, `archive --remote` and the transport
plumbing verbs escalate. `git push` was already human-only. The screen sits
**above** Codex with the critical set, because network egress is behind the
mechanical security boundary: escalation exits before Codex is consulted, so no
Codex verdict — however permissive — can turn a transport operation into an
allow.

**Known uncertainty.** A legitimate `git fetch` costs one dialog, and
`git submodule status` escalates although it is local. That is the demotion
working as specified, not an oversight.

**Standing rule**, recorded in `core/autonomy.md` and `NOTES.md`: new classifier
doubt defaults to escalation; deterministic rules are added only when a safe
operation becomes materially frequent. Rules for certainty. Codex for judgment.
Human for consequences.

**Links.** `hooks/permission-broker.sh` · `tests/approval.test.sh` ·
`core/autonomy.md` · `NOTES.md`

---

# Framework self-protection

## The deployed configuration resolves the hub too

**Problem.** The rule above is about the guard's own rules. One layer up, the
same mistake is available in the file that decides whether the guard runs at
all. `make sync` merges `adapters/claude/settings.fragment.json` into
`~/.claude/settings.json`, and the fragment has to carry absolute paths it
cannot know at rest. Spelled with a single placeholder — `__HOME__`, expanded to
`$HOME` — a hub path has to be written `__HOME__/.ai-dev/hooks/...`, which is
correct only when the hub is at exactly `~/.ai-dev`.

Anywhere else, and `make` itself defaults the hub to the checkout the `Makefile`
lives in, so a clone under `~/code` is the ordinary case rather than the exotic
one, that expansion names a directory that does not exist. A hook registered at
a path that does not exist does not fail: it never runs. The session starts, the
settings look right, `sandbox.enabled` is true, and there is no PreToolUse
ceiling. This is the worst failure mode a control can have — present in review,
absent in operation — arrived at by cloning to a normal place.

**Options.**

- **A. Document it.** Tell people to edit the fragment before syncing.
- **B. Refuse to sync** unless the hub is at the default location.
- **C. A second placeholder.** `__AI_DEV_HOME__` for hub paths, `__HOME__` for
  home paths, both expanded by `sync`.

**Decision: C, with a read-back.** A is what a caveat in a README buys: it
transfers a silent security failure to the reader's attention span. B makes the
supported layout smaller for no gain. C makes the fragment say which anchor each
path belongs to, so the question cannot be got wrong by accident.

The expansion is not trusted on its own. `sync` refuses to write a settings file
in which any placeholder survived, then reads back every registered hook command
and refuses to leave one pointing at a path it cannot read. `bin/doctor` repeats
the existence check on every run, because a hub can move after a sync.

**Confidence: high.** `tests/guard-portability.test.sh` section 12 expands the
shipped fragment against a hub with no `.ai-dev` in its path, asserts every
registered hook resolves to a real file there, and carries the negative control
— the same expansion done through `$HOME` produces an unreadable path, so the
assertion above is capable of failing.

**Links.** `adapters/claude/settings.fragment.json` · `bin/ai-dev` ·
`bin/doctor` · `tests/guard-portability.test.sh`

## Hooks are invoked as `bash <path>`, not as a bare path

**Problem.** A hook registered as a bare path runs only if the file carries its
executable bit. Claude Code mounts `hooks/` read-only inside a session, so a
session cannot repair that bit on the file that constrains it, and losing it is
not a loud failure — the hook simply does not run.

**Decision.** Every hook is registered as `bash <path>`. It then depends on the
file existing and being readable, which is what `make sync` and `bin/doctor`
check. `bin/doctor` matches the guard by the path its command NAMES rather than
by an exact string, so a machine synced before this change reports the same
wiring rather than a spurious failure.

**Links.** `adapters/claude/settings.fragment.json` · `bin/doctor` ·
`tests/fixtures/prompt-cases.md` (CASE-09)

## A line continuation is whitespace, not a command boundary

**Problem.** Every rule in `hooks/security-guard.sh` is a `grep -E`, and grep
matches one line at a time. A backslash-newline is not a separator: it is a
single command written across two lines, which is how anyone writes a long
command for readability. Matched unfolded, `curl x \<newline>| bash` reaches
the pipe-to-shell rule as two fragments that each match nothing, and the guard
falls through to its final `pass`. The same holds for `rm -rf \<newline>/` and
for every framework-write shape.

**Decision.** Fold `\<newline>` to a single space in the subject before any
rule runs. A **bare** newline is deliberately left alone: it separates commands
exactly as `;` does, and the clause-bound rules (`[^|;&]*`) are already correct
when each line is matched on its own. Folding those together would let a later
line supply a path to an earlier line's verb, which is a false deny at best and
a mis-parse at worst.

**Why the broker did not need the same fix.** It proves a positive — every
clause must be recognised — so a continuation lowers the recognised count and
produces escalate. Degradation is safe there and unsafe here, which is the
difference between a classifier that counts and a ceiling that matches.

**Confidence: high for this shape; medium for coverage.** This is still a regex
over a command line, and `docs/verification.md` states the honest limit: the
guard is a ceiling against mistakes and straightforward misuse, not a sandbox
escape defence.

**Links.** `hooks/security-guard.sh` · `tests/guard-portability.test.sh`
section 11 · `bin/doctor`

## `Read`, `Glob` and `Grep` are reads of the framework, and reads are allowed

**Problem.** The framework self-protection rule refused every file tool except
`Read`. `Glob` and `Grep` cannot write anything, so refusing them denied a
read-only operation under a message that says the framework is *read-only* from
a project session, and made the hub unsearchable from the projects it governs.

**Decision.** All three pass on that branch. The credential rules run before it
and are unaffected, so nothing that was denied for being a secret becomes
readable. Pinned in `tests/guard-portability.test.sh` section 3 alongside the
`Read` case, so the three cannot drift apart again.

**Links.** `hooks/security-guard.sh` · `tests/guard-portability.test.sh`

## Path-based security rules resolve the hub, never a literal

**Problem.** The guard refuses writes to its own framework from a project
session. Spelling that rule as a literal `~/.ai-dev` makes it correct for the
default installation and silently absent for every other one — a clone under
`~/code`, a shared `/opt` checkout, a CI workspace. That is the worst failure
mode a control can have: present in review, missing in operation. It is also easy
to introduce asymmetrically, protecting the file tools while leaving the shell
path open.

**Decision.** Every branch resolves the hub from `$AI_DEV_HOME`, and
`$AI_DEV_HOME` / `${AI_DEV_HOME}` are normalised in the subject alongside `$HOME`
and `~` so the same operation cannot reach a different verdict by being spelled
differently. The default location stays matched as well, so a command aimed at
`~/.ai-dev` is still refused when the hub is elsewhere — the two patterns are
independent, and neither depends on the other being true.

**Confidence: high.** `tests/guard-portability.test.sh` installs a hub at a path
with no `.ai-dev` in it, runs the shipped guard from there, and asserts the rule
in both directions — every write form denied, `Read` still allowed, and positive
controls proving ordinary project files and in-hub sessions are untouched. A
literal-path rule fails roughly half of that suite.

**Known uncertainty.** Containment here is a path match, not a canonicalization
pass; the broker owns path canonicalization. A relative path that resolves into
the hub from an unusual working directory is not matched by this rule, and is
caught by the layers that do canonicalize.

**Links.** `hooks/security-guard.sh` · `tests/guard-portability.test.sh` ·
`NOTES.md`

---

# The independent reviewer

## Read `codex login status` by exit code, never by wording

**Problem.** A preflight of the form `codex login status | grep -qi 'chatgpt'`
reads a human-readable string as if it were an API. Wording changes; the grep
misses; a review gate is blocked against a perfectly healthy reviewer.

**Decision.** Read the documented exit status. Never inspect stdout. Split
non-zero into two outcomes — *logged out* (the human runs `codex login`) and
*cannot determine* (the keyring is unreachable, which is the normal and expected
result inside the sandbox, where the D-Bus socket is blocked by design).
Collapsing those two sends the human to fix a login that is not broken.

**Confidence: high.** `tests/codex-preflight.test.sh` pins all of it, including
that exit 0 wins over a stdout that literally reads "Not logged in".

**Links.** `bin/codex-review` · `tests/codex-preflight.test.sh`

## The reviewer's permission profile is passed inline, not by name

**Problem.** A named Codex profile can be redefined by a project-local
`.codex/config.toml`, so a repository under review could widen the sandbox that
reviews it.

**Decision.** The whole permission profile is passed inline on the command line.
`-c` is Codex's highest-precedence configuration layer, so a project can neither
select a wider profile nor redefine the one that was selected. The reviewer runs
ephemeral, read-only, offline, keyless and time-bounded, and is built from
scratch rather than extending `:read-only`, which still permits reading the whole
machine.

**Confidence: high.** `tests/codex-boundary.test.sh` drives the exact policy
under an adversarial project-local config that sets full access and redefines the
profile, plus a poisoned `AGENTS.md`. The reviewer can read its workspace and can
do nothing else.

**Links.** `bin/codex-review` · `adapters/codex/config.toml` ·
`tests/codex-boundary.test.sh`

## The broad local-dev fallback supersedes the interpreter and package classes

**Problem.** Classifying every clause fail-closed is correct and, applied to
ordinary engineering, unusable. A classifier that escalates `npm install`,
`pip install`, `cargo build`, `docker compose up`, `python3 -c 'print(1)'` and
`bash $TMPDIR/scratch.sh` turns the human back into the routine approval engine
— the exact failure this framework exists to remove. The stricter reading of the
interpreter and package classes (above) produced precisely that.

**Options.**

- **A. Keep the strict classes** and accept the dialog rate.
- **B. Widen the strict classes** case by case as each one becomes annoying.
- **C. Invert the default for the residue**: after the critical set, the
  programmable-tool grammars and the sensitive-path screen have all had their
  say, treat what remains as ordinary local development and allow it.

**Evidence.** The containment these classes were duplicating already exists one
layer down and is enforced by the OS rather than by a regex: the sandbox
restricts writes to the workspace and network to an allowlist, and the PreToolUse
guard hard-denies the catastrophic set. `python3 -c` inside that box cannot write
outside the workspace, cannot reach an unlisted host, and cannot read a
credential path. What the strict class actually bought was a dialog, not a
property. B is A with extra steps: each widening is another special case in a
file whose whole argument is that it has no special cases.

**Decision: C.** `broad_safe_ok` allows a clause that reaches it, having refused
by name the shapes where argv genuinely does not say what runs (`eval`, `exec`,
`source`, `awk`, `xargs`, `env`, `sudo`, direct-egress binaries, `git`, and every
family that has a strict grammar above), plus any operand naming a sensitive
path. Inline interpreter code, `/tmp` scripts and package-manager commands are
ordinary local development.

This is a deliberate reduction in what the *broker* proves, resting on what the
sandbox and the guard enforce. It is not a claim that `python3 -c` is harmless in
general; it is a claim that it is contained here.

**What did not change.** Section 1 still matches the raw command text, so
`python3 -c 'os.system("sudo ...")'` still escalates on the sudo screen. Anything
behind the mechanical boundary — privilege, credentials, publication, deployment,
destruction, egress — is still above Codex and cannot be reached by this path.

**Confidence: medium-high.** High that the layering is sound; medium that the
line is in the right place, because it depends on the sandbox being correctly
configured. If `bin/doctor` reports the sandbox is off, this fallback is the
first thing that becomes too generous — which is why doctor treats a stale or
absent sandbox as a failure rather than a warning.

**Cost, recorded honestly.** `interp_ok`, `pkg_ok` and `sub_ok` are kept in the
broker but unwired, and are labelled as such. They are the clearest statement of
the option not taken. Re-wiring any of them means adding a case to `seg_ok` and
flipping the assertions in `tests/approval.test.sh` section 8, which pin the
permissive behaviour deliberately.

**Links.** `hooks/permission-broker.sh` (BROAD LOCAL-DEV FALLBACK) ·
`tests/approval.test.sh` section 8

## The adjudicator gets the reviewer's boundary

**Problem.** `bin/codex-review` is hardened against a hostile repository —
inline profile, no network, no keys, ephemeral, `--ignore-rules`,
`--strict-config`. `hooks/permission-broker.sh` is the *other* caller of
`codex exec`, on a much hotter path, and the obvious way to write that call is
bare: no strict config, no ephemerality, project execpolicy rules loaded,
network at the default, API-key variables inherited, and the working directory
set to the untrusted project, so that project's Codex configuration and
`AGENTS.md` sit on the discovery path.

**Evidence.** `core/security.md` states that the Codex API-key variables are
never passed to the reviewer, and a bare call passes them. The same file's whole
argument is that a cloned repository must not supply policy; an adjudicator
reading the repository's Codex configuration is that inversion, one layer over.
Hardening one caller and not the other states the property in the file that is
read and abandons it in the file that runs.

**Decision.** The broker's Codex call carries the same containment as
`bin/codex-review`, applied inline, plus two additions the reviewer does not
need: it runs with `-C` pointed at a fresh empty directory so no project
configuration is ever discovered, and it skips Codex entirely when the
file-backed Codex credential exists. Every failure mode of the hardening
(unknown flag, rejected key, timeout) yields an empty verdict, which is not
`ALLOW`, which escalates.

**Confidence: high.** `tests/codex-boundary.test.sh` asserts each element of the
hardening against the invocation with comments stripped, so the assertions cannot
pass on the prose that describes them; each element has a verified negative
control.

**Links.** `hooks/permission-broker.sh` section 6 · `bin/codex-review` ·
`tests/codex-boundary.test.sh`

## A ceiling that cannot parse its input denies

**Problem.** `hooks/security-guard.sh` reads its subject out of the hook JSON
using `jq`, falling back to `python3`. With neither installed there is no
subject: every rule tests an empty string, matches nothing, and the guard
reaches its final `pass`. Left there, a missing package silently removes the
entire ceiling — including the catastrophic-`rm`, credential-read and
`curl|bash` denials — with nothing anywhere saying so.

**Evidence.** This is the fail-open shape the framework refuses everywhere else:
`NOTES.md` states it as the standing rule for classifier changes, and
`hooks/permission-broker.sh` fails closed in exactly this situation. A control
that disappears when a package is absent is worse than no control, because the
posture is believed to be in force.

**Decision.** Absence of a parser is itself a decision: deny, naming the package
that restores the guard. An unparseable *payload* still passes — that is Claude
Code sending a shape this hook does not model, not a broken installation.

**Confidence: high.** `tests/guard-portability.test.sh` section 10 stages a PATH
holding everything the guard uses except `jq` and `python3`, asserts the
simulation really has no parser, and carries a baseline showing the same command
is denied when a parser is present.

**Links.** `hooks/security-guard.sh` · `tests/guard-portability.test.sh`

## A ceiling with a deadline bounds its own work

**Problem.** Claude Code's hook contract states it plainly: *"A command, http, or
mcp_tool hook that reaches its timeout is canceled: Claude Code discards the
hook's output, and the hook renders no decision. [...] A timed-out command hook
doesn't block the tool call. The call continues through the normal permission
flow, so don't count on a stalled hook to act as a gate."*

Every rule in `hooks/security-guard.sh` is a `grep -E` over the whole subject, so
its cost is linear in the length of a command chosen by the thing being
constrained. Measured on the development machine: **13.3 seconds** for a 2 MiB
command that matches no rule, against a registered timeout of **10**. Being slow
is therefore not a latency problem, it is the ceiling ceasing to exist — and in
auto mode with `autoAllowBashIfSandboxed` the tool call that outran the guard is
auto-approved with no dialog, so `PermissionRequest` never fires and the broker
does not see it either. Both layers disappear together, silently, to an input
whose only unusual property is its size.

**Options.**

- **A. Make the rules faster.** A faster ceiling is still a ceiling with a
  deadline; the next rule added spends the margin back, invisibly.
- **B. Raise the hook timeout.** Moves the cliff without removing it, and buys
  the move by making a stalled session the new failure.
- **C. Truncate the subject and scan the first N bytes.** Fail-open by
  construction: the payload goes after the cut.
- **D. Refuse an input large enough for the deadline to matter.**

**Decision: D.** Two ceilings — 1 MiB of hook payload and 64 KiB of subject —
each checked with a bash string length before any scan, so the refusal costs
microseconds however large the input is. Above either one the guard denies,
naming its own rule (`oversize-payload`, `oversize-subject`). That is the same
answer, for the same reason, as the missing parser above: *"I cannot screen
this"* is not *"this is fine"*. A denied command is recoverable — write the blob
to a file and operate on the file — an unscreened one is not.

The limits turn every measurement into a bound rather than a hope: 64 KiB of
subject costs ~0.7 s and 1 MiB of payload ~0.6 s, so the guard's worst case sits
an order of magnitude inside its timeout, and stays there when a rule is added.
They are generous against what a model actually writes on one command line —
64 KiB is roughly sixteen thousand tokens of it.

`hooks/permission-broker.sh` applies the identical limits from the identical
variables, so the two layers cannot drift into disagreeing about what is
screenable. Its answer is `escalate` rather than deny, because that is its answer
to everything it cannot classify. Its failure direction was already safe — no
decision means Claude Code asks the human — but `AI_DEV_OVERNIGHT=1` exists
precisely because there is no human to ask, and a cancelled broker raises a
dialog nobody will answer instead of denying and queueing.

**Confidence: high for the bound, medium for the constants.**
`tests/guard-portability.test.sh` section 13 proves the attack before the
defence: it runs the same payload with the bound lifted and with it in force, in
the same run on the same machine, and requires the unbounded scan to cost several
times more — a ratio rather than a number of seconds, so the claim survives a
faster or slower machine. It then asserts the worst *admitted* case still answers
inside the budget, both rule ids by name, the broker's escalate and its
unattended deny, and positive controls that ordinary commands are still silent
and catastrophic ones still denied. `bin/doctor` re-measures on the machine it is
run on, against the timeout actually registered in the deployed settings rather
than the one in the hub, because that is the budget the guard will really be
given. The constants are a judgement about command sizes, and the doctor check is
what will report if either side of that judgement stops holding.

**Links.** `hooks/security-guard.sh` · `hooks/permission-broker.sh` ·
`tests/guard-portability.test.sh` · `bin/doctor`

## The decision shape is a contract with Claude Code, and it is tested as one

**Problem.** Every suite in this repository drove a hook and asserted what the
hook *decided*. None asserted that Claude Code would act on the decision. Those
are different claims, and only the second one is the product.

Both directions of that gap fail silently. An `allow` Claude Code cannot parse
is not a deny — it is *no decision*, so every routine command starts prompting
again and the framework degrades into the approval fatigue it exists to solve,
with 815 assertions still green. And a key outside the schema is not an error:
it is dropped with one line in a debug log nobody reads.

The second failure was already present. The broker's allow path carried an
optional `addPermissionRule` object. The string does not appear anywhere in the
2.1.232 executable. No caller ever passed it, so it was a loaded trap rather
than a live bug — the first use would have produced an accepted allow with the
rule silently discarded.

**Evidence.** The schema was read out of the installed binary rather than from
the documentation, which describes neither shape completely:

```
decision: { behavior: "allow", updatedInput?, updatedPermissions? }
        | { behavior: "deny",  message?, interrupt? }
```

which confirmed the emitted shapes are correct, identified `addPermissionRule`
as outside them, and showed that `deny` accepts a `message` the broker was not
sending. It computed one for the audit log and then emitted a bare deny, leaving
the model unable to distinguish "this needs a human tonight" from "this tool is
broken" — the first is a reason to take a different route, the second is a
reason to retry all night, and an unattended run is where that costs something.

**Decision.** Remove `addPermissionRule` rather than repair it —
`updatedPermissions` is the current mechanism and should arrive with a test when
something needs it, not sit around as a shape that looks supported. Send the
reason in `deny.message`. Add `tests/hook-contract.test.sh`, which pins the
emitted shapes, asserts no decision object carries a key outside its schema, and
greps the installed executable for every field name the hooks are built from.

**Confidence: high for what it claims; the claim is deliberately narrow.** The
binary search proves the *vocabulary* still exists, not that the CLI honours the
decision — only a live session proves behaviour, and `project-isolation.test.sh`
is the suite that starts real sessions. It carries an invented field name as a
control that the search can tell present from absent, and it was mutation-checked
in both directions: reintroducing `addPermissionRule` and renaming
`permissionDecision` each make it fail. What it cannot catch is a build that
keeps every name and changes their meaning.

**Links.** `hooks/permission-broker.sh` · `hooks/security-guard.sh` ·
`tests/hook-contract.test.sh`

## `cd` into the hub is a write to the hub

**Problem.** The framework self-protection rule binds a mutating verb to a hub
path inside a single clause (`[^|;&]*` stops at the separator). `cd <hub> && rm
core/x` names the hub in one clause and mutates it in the next, so neither clause
matches on its own and the rule is one `&&` away from being bypassed. The
file-tool branch has a mirror-image failure available to it: comparing the raw
`file_path` rather than the normalised one leaves `$AI_DEV_HOME/core/x` and
`~/.ai-dev/core/x` resolving to nothing, so they fall through. Both are the same
mistake — a rule spelled differently from the rest of the file.

**Decision.** Both branches resolve the hub the way the rest of the file does. A
hub-targeted `cd` anywhere in the command, paired with a mutating verb or a
*relative* redirection anywhere in it, is a framework write. An absolute
redirection is deliberately excluded: `cd <hub> && grep -r x . > /tmp/out` reads
the hub and writes elsewhere, which any project may do.

**Confidence: high for the shapes named; medium for coverage.** This is still a
regex over a command line, and the honest limit is stated in
`docs/verification.md`: the guard is a ceiling against mistakes and
straightforward misuse, not a sandbox escape defence. `tests/guard-portability.test.sh`
sections 8 and 9 pin both directions, including the negative cases that must stay
silent.

**Links.** `hooks/security-guard.sh` · `tests/guard-portability.test.sh`
