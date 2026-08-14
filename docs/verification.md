# Verification report

What AI Dev Autopilot claims, and what each claim is backed by. Nothing here is
asserted from reading configuration: every line corresponds to a check that
exercises the mechanism it describes.

Reference platform: Linux (Ubuntu 24.04), Claude Code 2.1.x, Codex CLI 0.146.x.
Re-run the suite on your own machine before relying on any of it — that is the
point of shipping the checks rather than the conclusions.

## How verification is layered

| Tool | Runs where | Answers |
| --- | --- | --- |
| `tests/*.test.sh` | inside the sandbox | do the behavioural contracts hold |
| `bin/doctor` | inside the sandbox | is the configuration deployed and current |

`bin/doctor` answers three ways, not two. A check whose subject lives outside
this repository — `~/.claude`, `~/.codex`, `/etc`, `$PATH` — has nothing to
inspect until `make sync` has run, so on an undeployed machine it reports
**PENDING** and doctor exits **3**: nothing here is violated, some controls are
simply not installed. A machine that HAS been synced and then drifted is a real
failure and still reports as one, so the category cannot be used to hide drift
by deleting a file. `tests/doctor-reporting.test.sh` pins both directions.
| `bin/host-check` | **outside** the sandbox | is the sandbox real |

A sandboxed process cannot observe host truth and must not pretend otherwise.
`bin/doctor` defers the checks it cannot honestly answer and names the command
that can; `bin/host-check` refuses to report at all if it detects it is itself
sandboxed. A result that cannot be obtained honestly is not reported.

## The contract suites

| Suite | Proves | Cost |
| --- | --- | --- |
| `approval.test.sh` | the delegated approval broker allows routine work and escalates everything else, clause by clause | model-free |
| `guard-portability.test.sh` | the framework self-protection rule and the hook paths `make sync` deploys both follow `AI_DEV_HOME`, so an installation outside `~/.ai-dev` keeps the ceiling and actually runs it; the ceiling denies rather than disappearing when it cannot parse its input or when the input is too large to screen inside its own hook timeout; and a line continuation does not split a command past the rules | model-free |
| `project-isolation.test.sh` | a hostile repository's skills, commands, agents, hooks, MCP servers and instruction files do not load into a session | starts real sessions |
| `settings-isolation.test.sh` | a hostile repository cannot widen the sandbox through settings files | model-free |
| | *(its two settings-scope assertions need `claude doctor` to print a report; where it cannot, they are reported UNMEASURED and the suite exits 3 rather than scoring silence)* | |
| `permission-posture.test.sh` | every spelling of the permission-bypass flag is refused, every flag that widens the session's scope or configuration is refused (including `--add-dir`, which grants tool access to another tree and loads its CLAUDE.md), the six safe modes still work, and the managed version floor is at least the version the control it protects needs | model-free |
| `codex-boundary.test.sh` | the Codex reviewer can read its workspace and can do nothing else, and both callers of `codex exec` carry that containment | model-free |
| `codex-preflight.test.sh` | login state is read by exit status, and "cannot determine" is never reported as "logged out" | model-free |
| `prompt-injection.test.sh` | classic injection payloads are refused deterministically | model-free |
| `bootstrap.test.sh` | the bootstrap skill's contract holds in a disposable repository | model-free |
| `doctor-reporting.test.sh` | doctor reports an uninstalled machine as pending and a drifted one as failed, so "not deployed here" cannot be used to hide drift | model-free |
| `hook-contract.test.sh` | the hooks emit exactly the decision shape Claude Code parses, no key outside it, and the installed build still contains every field name — the canary for a schema change that would otherwise degrade the framework in silence | model-free |

Run them all with `make test`.

### Project isolation is the load-bearing result

`tests/project-isolation.test.sh` starts real Claude Code sessions against
`tests/fixtures/hostile-project` and reads the CLI's own `system/init` event —
its account of the configuration it resolved — cross-checked with marker files
for every surface that can execute rather than merely be listed.

**Baseline.** Started without the launcher, that repository's skill, custom
command and subagent all register, its `.mcp.json` server registers *and its
process spawns*, and its `UserPromptSubmit` hook *executes*. The attack is real
and reaches code execution.

**Through `aidev`.** None of it: no skill, no command, no agent, no MCP
registration, no MCP process, no plugin, no output style, no hook, no status-line
command, and no read of the project's `CLAUDE.md`, `CLAUDE.local.md`,
`.claude/rules` or settings files. Both halves are re-established from scratch on
every run.

One flag delivers that — `--setting-sources user` — and its observed behaviour is
broader than its documented description. Because the whole boundary rests on it,
it is held as a contract test rather than an assumption: a release that narrows
it fails the test loudly instead of eroding the boundary in silence. **Re-run
this suite after every Claude Code upgrade.**

The test proves what is *loaded*, not that a model would disobey a hostile
instruction. A nested session cannot authenticate, so no model turn runs. That
is accepted deliberately: an instruction that never enters the context window
cannot be obeyed, and it is the stronger of the two properties.

### The Codex reviewer boundary

`tests/codex-boundary.test.sh` drives `codex sandbox` with the exact policy
`bin/codex-review` passes to `codex exec`, under an adversarial project-local
`.codex/config.toml` that tries to grant full access and redefine the reviewer
profile, plus a poisoned `AGENTS.md`. The reviewer can read the workspace it is
meant to review, and cannot write it, delete from it, read outside it, read
credential directories, reach the network, or see API keys — and the
project-local configuration could not widen any of it.

The mechanism: the whole permission profile is passed **inline on the command
line**, which is Codex's highest-precedence configuration layer, so a project can
neither select a wider profile nor redefine the one that was selected.

**Both callers are covered.** `bin/codex-review` is the visible reviewer;
`hooks/permission-broker.sh` is the other caller of `codex exec`, on a much
hotter path, adjudicating a command string it did not choose. The same
containment is asserted for it — strict config, ephemeral, project rules
ignored, network disabled, API-key variables stripped, no session history, hard
timeout — plus two things the reviewer does not need: it runs with `-C` pointed
at a fresh empty directory, so no project `AGENTS.md`, Codex configuration or
execpolicy is ever on the discovery path, and it skips Codex entirely when a
file-backed Codex credential is present.

Those assertions read the invocation **with comment lines stripped**. The block
above it documents every flag by name, so a check over the raw file would match
the prose describing the hardening and keep passing after the call itself was
gutted — the failure mode this project calls a test that claims more than it
proves. Each element has a verified negative control.

### The ceiling fails closed

`hooks/security-guard.sh` reads its subject out of the hook JSON with `jq`,
falling back to `python3`. With neither present there is no subject, so every
rule is skipped — a missing package silently removing the whole ceiling, which
is the fail-open shape this project refuses everywhere else. Absence of a parser
is therefore a decision in its own right: deny, and name the package that
restores the guard.

`tests/guard-portability.test.sh` section 10 stages a `PATH` containing
everything the guard uses *except* `jq` and `python3` — emptying `PATH` outright
would also remove `cat`, and the guard would never read stdin, passing the test
for the wrong reason. It asserts the simulation really has no parser, and
carries a baseline proving the same command is denied when one is present.

### A control that is registered is not yet a control that runs

Two ways for the ceiling to be configured and absent, both silent, both checked:

A **line continuation** is whitespace inside one command, but every rule in the
guard is a line-oriented `grep`. Matched unfolded, the verb and its target land
on different lines, every rule sees a fragment, and the guard reaches its final
`pass`. Section 11 pairs each payload with the identical command on a single
line, so a failure is unambiguously the continuation rather than the payload.

A **hook path that does not exist** does not error — it simply never runs. The
settings fragment therefore spells hub paths with `__AI_DEV_HOME__` rather than
`__HOME__/.ai-dev`, `make sync` reads the file back and refuses to leave a hook
registered at an unreadable path, and `bin/doctor` re-checks on every run.
Section 12 expands the shipped fragment against a hub with no `.ai-dev` in its
path and asserts every registered hook resolves there, with the negative control
that the `$HOME`-anchored spelling would not.

## Known limitations

- **Sandbox boundaries are not assumed.** AI-DEV is built defence-in-depth
  precisely because a sandbox may behave differently across versions and
  environments. `bin/doctor` reports a limitation it can neither fix nor confirm
  away as `KNOWN` — a category of its own, never a pass — and only after
  verifying in the same run that the compensating controls actually refused a
  write. A limitation whose compensation fails is a hard failure, not a footnote.
- **The `denyWrite` list is load-bearing**, not decorative. Keep it current and
  re-check it after every Claude Code upgrade.
- **A domain allowlist alone is not a control.** Without
  `sandbox.network.strictAllowlist`, hosts outside the allowlist only *prompt*,
  and a non-interactive sandboxed command has nothing to prompt with. The
  setting is read once, when the session's proxy is built, so it takes effect
  only for sessions started after it is written. `bin/host-check --network`
  answers this properly, from outside.
- **`excludedCommands` may not escape the sandbox** depending on how a session
  was started. When they do not, `host-check`, `codex-review` and `make sync`
  cannot see or change host state from inside the session; run them from a
  normal shell.
- **Unattended mode cannot confirm its own containment from inside.** Run
  `bin/host-check` from the launching shell *before* handing control to an
  agent, and refuse to start if it does not pass.

This project is an experimental prototype. It has not been independently
audited, and it should not be treated as an audited security boundary.

## Deliberately not built

- **MCP gateway** — `gateway/README.md` records the target shape and the six
  requirements any adopted gateway must meet. Nothing is installed.
- **Component registry** — not until several genuinely reusable components exist.
- **Nightly job framework** — policy only, in `core/engineering.md`. Generalise
  after one real example.
- **Kubernetes / microservices** — not because a project exists.

## Rejected alternatives

Recorded with the evidence in `.ai/decisions.md`. In brief:

- **`--safe-mode`** disables all customizations and keeps only managed-policy
  hooks — including switching off the AI-DEV PreToolUse guard, which is a user
  hook. It would trade a boundary measured as intact for the loss of the
  enforcement layer.
- **`--bare`** never reads OAuth or the keychain, so authentication would have to
  become an API key — a credential this framework denies by design.
- **`allowManagedHooksOnly`, `allowManagedPermissionRulesOnly`,
  `allowManagedDomainsOnly`** each weaken a control in order to lock it: they
  would respectively disable the security guard, remove the `ask` rules for
  `sudo`/`git push`/publish/deploy, and cut off the package-source allowlist.

Each would weaken a control in order to lock it, which is the trade
`core/orchestration.md` says never to accept.
