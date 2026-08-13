# Changelog

Notable changes to AI Dev Autopilot. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

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
