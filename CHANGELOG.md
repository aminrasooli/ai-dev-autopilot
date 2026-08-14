# Changelog

Notable changes to AI Dev Autopilot. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security

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
