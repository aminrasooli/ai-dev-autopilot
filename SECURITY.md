# Security policy

AI Dev Autopilot is an experimental prototype. It has not been independently
audited and should not be treated as an audited security boundary. Reports that
help close the gap between what it claims and what it does are very welcome.

## Reporting a vulnerability

Please report vulnerabilities privately through **GitHub Private Vulnerability
Reporting**, using the **Report a vulnerability** button on the repository's
Security tab.

If that button is not visible, the feature has not been enabled on the
repository yet. In that case please open an issue that says only that you have a
security report and are waiting for a private channel — **without any details** —
and wait for a maintainer to enable private reporting and follow up.

**Do not post vulnerability details publicly.** No details in issues, pull
requests, discussions, commit messages or comments until a fix is available and
a maintainer has agreed the report can be made public. That includes proof of
concept code, reproduction steps and the specific configuration or paths
involved.

## What to include

- What control is bypassed or weakened, and which file implements it.
- The smallest reproduction you have — a command, a settings fragment, a
  repository layout.
- What an attacker gains: the concrete outcome, not the category.
- The versions you observed it on, including the Claude Code version, since much
  of what this project asserts is measured against vendor behaviour that changes
  between releases.

Never include real credentials, tokens, private keys or personal data in a
report. If a finding involves a secret, describe its location and shape rather
than pasting the value.

## Scope

In scope:

- Any way to reach an allow for something the documented boundaries say is
  human-only: privilege, credentials, network egress, publication, deployment,
  destruction.
- Any way for a checked-out repository to influence the session that inspects it
  — configuration, instructions, hooks, skills, agents, commands or MCP servers.
- Any way to make the approval broker fail open rather than escalate.
- Any way to make the independent reviewer write, reach the network, or read
  outside its workspace.
- Verification that reports a result it cannot honestly observe.

Out of scope:

- Vulnerabilities in Claude Code, Codex CLI, bubblewrap or other upstream tools.
  Please report those to their own maintainers. If an upstream behaviour breaks
  an assumption this project relies on, that *is* in scope here — the assumption
  is ours.
- The absence of a control this project explicitly documents as not present. See
  the security limitations section of the README.
- Findings that require an attacker who already has the ability to run arbitrary
  code as your user outside a session.

## Expectations

This is a volunteer-maintained project with no service level agreement.
Acknowledgement and a first assessment will be provided as soon as a maintainer
is able. Reporters who would like credit in the release notes will be credited;
say so in the report, and say how you would like to be named.
