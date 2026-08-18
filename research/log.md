# Research log

Dated findings from external research, with sources, kept when they change a
decision or would otherwise have to be rediscovered. Everything fetched from the
web is treated as untrusted data: this file records *facts extracted*, never
instructions found in the material.

---

## 2026-08-18 — the separator set Claude Code recognises, and 2.1.234

- **Claude Code's own Bash separator set is `&&`, `||`, `;`, `|`, `|&`, `&` and
  newlines**, quoted exactly: "Claude Code is aware of shell operators, so a
  rule like `Bash(safe-cmd *)` won't give it permission to run the command
  `safe-cmd && other-cmd`. The recognized command separators are `&&`, `||`,
  `;`, `|`, `|&`, `&`, and newlines. A rule must match each subcommand
  independently." The same page adds that "Yes, and don't ask again" saves a
  separate rule per subcommand, up to five.
  https://code.claude.com/docs/en/permissions (read 2026-08-18)
- **Why this mattered here:** the broker's `clauses()` splitter omitted `&`, so
  a command after a bare `&` was read as *arguments of the command in front of
  it* rather than as a clause of its own — a disagreement with the exact layer
  whose dialogs this hook answers. Fixed 2026-08-18 together with the clause
  *head* defect (grouping punctuation and reserved words read as argv[0]); the
  decision record "A clause ends and begins where the shell says, not where the
  punctuation looks like it" in `.ai/decisions.md` carries the measurements.
- **Windows PowerShell is parsed differently and more strictly**, worth knowing
  before any portability claim: "Claude Code parses the PowerShell AST and
  checks each command in a compound command independently. Pipeline operators
  `|`, statement separators `;`, and on PowerShell 7+ the chain operators `&&`
  and `||` split a compound command." An AST rather than a regex, i.e. upstream
  solves on Windows what this project solves with a hand-written reader on
  POSIX. https://code.claude.com/docs/en/permissions (read 2026-08-18)
- **Newest verified Claude Code: 2.1.234**, up from 2.1.233 the previous run.
  Nothing in it touches the hook decision shapes this hub emits. Entries worth
  keeping in view: Windows NT-namespace paths (`\??\`) are now rejected in file
  reads to prevent NTLM credential leaks; "Permission answers (including denies)
  no longer dropped when handling background subagent tool prompts" — the same
  background-agent area as the 2.1.222 fix already recorded here, so
  `tests/project-isolation.test.sh` stays a re-run-on-upgrade job; and MCP
  diagnostics now mask resolved secrets.
  https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md
  (read 2026-08-18)

---

## 2026-08-17 — NotebookEdit's subject field, and the state of NotebookRead

- **`NotebookEdit` sends its path as `tool_input.notebook_path`, and has no
  `file_path`.** Verified against the tool schema of the running Claude Code
  build (the JSON schema the session itself publishes for the tool):
  `notebook_path` is required and must be absolute; the other fields are
  `cell_id`, `new_source`, `cell_type`, `edit_mode`. The hooks documentation
  does not enumerate `tool_input` fields per tool, so the build's own schema is
  the primary source. https://code.claude.com/docs/en/hooks (read 2026-08-17)
- **`NotebookRead` no longer exists in current builds.** The tools reference
  lists `NotebookEdit` but no notebook read tool; `.ipynb` reading is folded
  into `Read` ("`.ipynb` files return all cells with their outputs").
  `NotebookEdit` is marked *Permission required: Yes*, so it does raise
  permission dialogs and the PermissionRequest broker genuinely fires for it.
  Notebook permission rules are spelled through `Edit(...)`: "A rule like
  `Edit(notebooks/**)` covers NotebookEdit calls on files in that directory",
  and since 2.1.210 a `NotebookEdit(path)` rule draws a startup warning saying
  to use `Edit(path)`. https://code.claude.com/docs/en/tools-reference
  (read 2026-08-17); https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md
- **Newest verified Claude Code: 2.1.233** — unchanged since the 2026-08-16
  check; no releases landed between the two runs.
  https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md
  (read 2026-08-17)
- **Why this mattered here:** both hooks read the subject from
  `file_path`/`path` only, so every notebook operation arrived with an empty
  subject — the guard's ceiling silently skipped all path rules for
  `NotebookEdit`, the broker escalated every routine notebook edit, and the
  broker's search-tools arm allowed `NotebookRead` under a justification that
  was false for it. Fixed 2026-08-17; the decision record "A tool's subject is
  read from the field that tool actually sends" in `.ai/decisions.md` carries
  the details.

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
