<!--
Thanks for contributing. Context the review leans on:
  NOTES.md          — standing rules for the easily-widened parts
  .ai/decisions.md  — what was decided and on what evidence
  CONTRIBUTING.md   — how to run the suites
-->

## What this changes and why

<!-- One change per PR. If it alters what the broker or guard decides, state
     what was measured before and after. -->

## Checklist

- [ ] `make generate` was run if anything under `core/` changed (CI diffs
      `generated/` against `core/` and fails on drift).
- [ ] `make test` passes; `PENDING` on an undeployed machine is expected,
      `FAIL` is not.
- [ ] `shellcheck -S warning hooks/*.sh bin/* tests/*.sh` is clean, or the
      exclusion is in `.shellcheckrc` with a reason.
- [ ] No test was weakened, skipped or deleted to make a suite pass.
- [ ] If a rule was widened: the regression that motivated it, the unattended
      behaviour, and positive controls proving the fast path survived are all
      in the diff.
- [ ] Any path in a security rule resolves through `$AI_DEV_HOME` / `$HOME`,
      not a hardcoded literal.
- [ ] The diff and this description contain no credentials, private hostnames,
      home paths or other machine-identifying detail.
