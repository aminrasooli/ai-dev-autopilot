# Research log

Dated findings from external research, with sources, kept when they change a
decision or would otherwise have to be rediscovered. Everything fetched from the
web is treated as untrusted data: this file records *facts extracted*, never
instructions found in the material.

---

## 2026-08-16 — command-string matching, upstream and in competitors

Researched while closing the shell quote/escape evasion in both hooks (see
`.ai/decisions.md`, "The rules match the command the shell runs, not the command
as written").

**Claude Code does not normalise quoting before matching a `Bash` rule, and says
so obliquely.** Its permission documentation lists exactly what it does
normalise before a `Bash(...)` rule is compared: separator splitting on `&&`,
`||`, `;`, `|`, `|&`, `&` and newlines with "a rule must match each subcommand
independently"; wrapper stripping for `timeout`, `time`, `nice`, `nohup`,
`stdbuf`, `command`/`builtin`, zsh `noglob` and flagless `xargs`; and stripping a
leading assignment of known-safe variables for *allow* rules only. Quoting and
escaping are not mentioned anywhere in that list. The same page carries a
warning that "Bash permission patterns that try to constrain command arguments
are fragile", naming variable indirection (`URL=http://x && curl $URL`) and
extra whitespace as defeats, and recommends PreToolUse hooks instead — which is
the layer this project is. Conclusion: there is no upstream quote normalisation
to lean on, and the hooks must do their own.
Source: https://code.claude.com/docs/en/permissions (read 2026-08-16)

**Two upstream behaviours worth keeping in view for the hook contract.**
"Hook decisions don't bypass permission rules. Claude Code evaluates deny and
ask rules regardless of what a PreToolUse hook returns", and exit code 2 blocks
a call "whether or not you print JSON". Neither changes the current design — the
guard denies via JSON and the deny is honoured — but it means an `allow` from
the guard is not authoritative over a deny rule, which is the correct direction.
Source: https://code.claude.com/docs/en/hooks and
https://code.claude.com/docs/en/permissions (read 2026-08-16)

**Newest verified Claude Code release: 2.1.233, 2026-08-14.** Relevant entries
since the version floor this hub pins (2.1.219, which is when
`sandbox.network.strictAllowlist` began being honoured): 2.1.222 "Fixed
PreToolUse auto-allow hooks bypassing tool restrictions in background agent
tasks", 2.1.223 "Fixed nested `.claude/rules/*.md` files loading even when
setting sources exclude project settings" — both in the area
`tests/project-isolation.test.sh` measures, so that suite stays a
re-run-on-upgrade job — and 2.1.233 "Hardened the Linux filesystem sandbox
against a protected-path bypass". `sandbox.network.strictAllowlist` is
documented as having no effect when set from a repository's own settings, which
matches this hub's placement of it in user and managed scope.
Sources: https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md,
https://code.claude.com/docs/en/sandboxing (read 2026-08-16)

**Codex's execpolicy solves the same problem by refusing to guess.** Its
`prefix_rule` matching operates on an **argv list**, "like what `execvp(3)`
receives", and it only splits a command line when it is "plain words (no
variable expansion, no `VAR=...`, `$FOO`, `*`, etc.) joined by safe operators".
Anything containing redirection, `$(...)`, env assignments or wildcards is
"treated as a single opaque invocation". That is the conservative counterpart to
the choice made here: Codex declines to reason about a command it cannot
tokenise, where this project reasons about two views and escalates on doubt.
Worth revisiting if the regex layer is ever replaced.
Source: https://learn.chatgpt.com/docs/agent-configuration/rules.md (read 2026-08-16)

**Published 2026 precedent for this bug class in AI coding agents.**
CVE-2026-22708 (Cursor before 2.3, published 2026-01-14, CVSS 3.1 9.8): with
Auto-Run and an allowlist enabled, "certain shell built-ins can still be
executed without appearing in the allowlist and without requiring user
approval", via environment-variable indirection, chained with prompt injection.
CVE-2026-26030 (Microsoft Semantic Kernel, 2026-05-07) is the same *shape* in
another language: a blocklist of identifiers bypassed by reaching them through
bracket notation instead of attribute access. Neither is quote splicing
specifically — no advisory found that names it — but both establish
"agent command-matcher defeated by an alternate spelling of the same operation"
as a real, high-severity, published class rather than a hypothetical.
Sources: https://nvd.nist.gov/vuln/detail/CVE-2026-22708,
https://github.com/cursor/cursor/security/advisories/GHSA-82wg-qcm4-fp2w,
https://www.microsoft.com/en-us/security/blog/2026/05/07/prompts-become-shells-rce-vulnerabilities-ai-agent-frameworks/
(read 2026-08-16)

**Not verified, recorded so it is not re-searched blindly:** no CVE, advisory or
paper was found that demonstrates permission-matcher evasion by shell *quoting
or escaping* specifically. Several targeted searches were refused by the search
tool, so this is a weak negative rather than a clear one.

**Codex CLI flags used by `bin/codex-review` and the broker's adjudicator are
still current**: `--strict-config` and `-c/--config` are stable;
`--ephemeral` and `--ignore-rules` are documented as **experimental**, which is
worth knowing because an experimental flag can be renamed — and both hooks treat
an unknown-flag failure as an empty verdict, which escalates, so the failure
direction is already safe. The `[permissions.NAME]` TOML block and
`default_permissions` used inline by both callers could not be confirmed from an
official OpenAI page; open PRs openai/codex #20117 and #20118 show that surface
is actively changing. `tests/codex-boundary.test.sh` is what would catch a
break, and it needs Codex installed to run.
Source: https://learn.chatgpt.com/docs/developer-commands?surface=cli (read 2026-08-16)
