# Architecture

How the pieces fit, and which layer is load-bearing for what.

## The four layers

```
  managed policy      /etc/claude-code/managed-settings.d/20-ai-dev-security.json
    │                 sandbox floor · credential denies · disableBypassPermissionsMode
    │                 no other scope can override it; applies to bare `claude`
    ▼
  user settings       ~/.claude/settings.json  (merged from adapters/claude/settings.fragment.json)
    │                 PreToolUse security guard · network allowlist · denyWrite
    │                 permission asks · env scrub · claudeMdExcludes
    ▼
  launcher            bin/aidev
    │                 --setting-sources user · --permission-mode auto
    │                 permission-mode allowlist · config-injection refusals
    ▼
  the session         project source is DATA; project configuration is not loaded
```

Each layer catches something the one below it cannot:

- **Managed policy** is the only layer that survives someone typing `claude`
  instead of `aidev`, or passing `--setting-sources project`.
- **User settings** carry the guard and the compensating controls that have no
  managed equivalent (`excludedCommands` has no managed-only lockdown, which is
  the whole reason project settings are excluded rather than constrained).
- **The launcher** is a fast, legible failure with a reason attached. It is not
  relied on as a control.

## The two hooks

They fire at different moments and have opposite jobs. Keeping them in separate
files is what makes the precedence claim checkable rather than argued.

```
  tool call
     │
     ▼
  PreToolUse ─ hooks/security-guard.sh ─────── the hard ceiling
     │   deny ──> blocked. No dialog. PermissionRequest never fires.
     │            Codex never sees it. This is the whole precedence argument.
     │   ask  ──> a dialog would be raised
     │   pass ──> normal permission flow
     ▼
  (does this need a permission decision?)
     │ no ──> runs
     ▼ yes
  PermissionRequest ─ hooks/permission-broker.sh ─ the broker
     │   critical set        ──> escalate (never allow)
     │   deterministic routine ──> allow  (+ addPermissionRule to batch)
     │   gray, pre-qualified ──> Codex, advisory, fixed rubric, hard timeout
     │   anything else       ──> escalate
     ▼
  escalate = interactive: emit nothing, the human sees the dialog
             overnight  : deny + queue in var/pending-approvals.log
```

The classifier proves a positive: every clause of a command must be recognised,
counted, and the counts must match. Every degradation lowers the recognised
count and produces escalate. This is a deliberate inversion of the shape that
sets a flag to "ok" and tries to falsify it, which allows `eval "$X"` whenever a
parse slips.

Audit: `var/permission-audit.log` records timestamp, tool, input hash,
deterministic classification, whether Codex was consulted, its verdict, the
final decision and the reason. Command text is written only to
`var/pending-approvals.log`, which exists so a human can review what was refused
overnight.

## The project-isolation boundary

The security property, stated so it can be tested:

> An untrusted checked-out repository may supply source code and ordinary
> project files for Claude to inspect. It must not supply instructions, skills,
> agents, commands, hooks, MCP integrations, output styles, or security policy.

**One flag delivers it**: `--setting-sources user`. Measured on Claude Code
2.1.x (`tests/project-isolation.test.sh`, reading the `system/init` event):

| Class | plain `claude` | through `aidev` |
| --- | --- | --- |
| project skill | registered | not registered |
| project custom command | registered | not registered |
| project subagent | registered | not registered |
| project `.mcp.json` | registered **and process spawned** | neither |
| project hooks | `UserPromptSubmit` **executed** | none executed |
| status-line command | — | not executed |
| plugins / output style | — | none / `default` |
| `CLAUDE.md`, `CLAUDE.local.md`, `.claude/rules` | read | not read |
| `.claude/settings*.json` | read | not read |

This is the load-bearing fact of the whole design, and it is broader than the
flag's documented description. It is therefore held as a **contract test, not an
assumption**: if a release narrows the flag to settings files only, the test
fails rather than the boundary eroding quietly. Re-run on every upgrade.

Rejected alternatives and why: see `.ai/decisions.md`
(`--safe-mode` disables our own guard; `--bare` abandons OAuth).

## Defence in depth for the test fixture

`tests/fixtures/hostile-project/` holds a live attack payload *inside* the
framework repository, which is the one repository allowed to edit its own
enforcement floor. Three independent things stop it acting:

1. **Stored inert** — directories are `claude/` and `mcp.json`, not `.claude/`
   and `.mcp.json`; no filename matches a discovery pattern at rest.
2. **Placeholders** — every path inside a hook or MCP command is `@@RUNDIR@@`,
   which resolves to nothing executable. The live copy is materialized into a
   gitignored directory only while the test runs, and deleted on exit.
3. **`claudeMdExcludes`** in the user fragment covers the whole subtree, so even
   a fixture accidentally committed under a live name cannot enter context.

## Verification layers

| Tool | Runs where | Answers |
| --- | --- | --- |
| `tests/*.test.sh` | inside the sandbox | do the contracts hold |
| `bin/doctor` | inside the sandbox | is configuration deployed and current |
| `bin/host-check` | **outside** the sandbox | is the sandbox real |

`host-check` is the only probe that can check the sandbox from outside it, and it
refuses to run when it detects it is inside — a result it cannot obtain honestly
is not one it will report. It has to be invoked as its own top-level command,
matching an entry in `sandbox.excludedCommands`, or simply run from a normal
shell. Unattended mode depends on it: a run that cannot execute `host-check`
cannot confirm its own containment, so it should be run before handing control
to an agent rather than from inside the session.

Doctor reports three states, not two: `PASS`, `FAIL`, and `KNOWN` for a
limitation it can neither fix nor confirm away, but for which a compensating
control was verified in the same run. `KNOWN` is never counted as a pass, and
the compensating half has to be re-earned on every run.
