# AI Dev Autopilot

## Autonomous coding without turning yourself into the message bus.

**An open, vendor-neutral path toward autonomous software engineering — the human gives direction, not constant approval.**

> Tested on Ubuntu 24.04 with Claude Code 2.1.x. Codex CLI is an optional independent reviewer; a local open-weight model through Ollama, or Claude Code itself, can serve the same role instead — see [The Local Reviewer Benchmark](#the-local-reviewer-benchmark).

Run coding agents for hours without turning yourself into a human permission button.

Routine engineering just runs:

**tests · builds · refactors · repo edits · searches · local Git · debugging · local dev servers · allowlisted package installs**

No constant **"Allow?" → "Yes" → "Allow?" → "Yes"** loop.

When an agent reaches something consequential, credentials, privilege escalation, destructive operations, arbitrary external egress, deployment, publication, or an unknown command shape, **the autonomy stops and a human takes over.**

> **Rules for certainty. An independent reviewer for judgment. Humans for consequences.**

```text
  ROUTINE WORK                              CONSEQUENCES
  ────────────                              ────────────
  edit code                       ─┐
  run tests                        │
  build                            │
  refactor                         ├──► RUN AUTOMATICALLY
  local git                        │
  debug                            │
  local dev servers                │
  allowlisted package installs    ─┘

  credentials                     ─┐
  sudo                             │
  destructive actions              │
  deployment                       ├──► STOP FOR A HUMAN
  publication                      │
  arbitrary external egress        │
  unknown behavior                ─┘
```

## Why this exists

Coding agents usually force you into one of two bad choices.

**Ask about everything.**  
The agent stops every few minutes and turns you into its approval engine. After enough prompts, the human stops reading and starts clicking.

**Ask about nothing.**  
Disable permissions and hope the same agent that edits your tests never reads credentials, executes an injected instruction, publishes something, or destroys the wrong files.

**AI Dev Autopilot is the third option.**

It gives agents broad freedom inside the development loop while keeping hard boundaries around consequences.

This is not another coding agent. **It is the control plane that lets coding agents become autonomous.**

### What this is today

A working foundation for autonomous coding, built to reduce how often a
human has to act as the message bus between coding agents, terminals and
reviewers:

- **safe autonomous coding boundaries** — the sandbox, guard and broker
  described below
- **a pluggable independent reviewer** (`bin/review`) — Codex by
  default, a local open-weight model through Ollama, or Claude Code,
  selected by configuration, never hardcoded to one vendor
- **a reproducible reviewer benchmark** for comparing those backends on
  identical cases — see [The Local Reviewer Benchmark](#the-local-reviewer-benchmark)
  and [`docs/BENCHMARK_METHODOLOGY.md`](docs/BENCHMARK_METHODOLOGY.md)
- **durable agent/session handoff** — work continues across sessions
  through committed reports and state, not a live chat that has to stay
  open ([`docs/HANDOFF.md`](docs/HANDOFF.md))
- **human escalation for consequential operations only** — everything in
  the [Hard human boundaries](#hard-human-boundaries) table below

### Why it's built this way

The human should give direction and make consequential calls — not
repeatedly copy messages between agents, approve routine commands,
restart work after a session or provider limit, or hand-pick which model
handles every small task. [`docs/NORTH_STAR.md`](docs/NORTH_STAR.md)
states this as an explicit target: roughly **1–3 meaningful human
touches per day.**

The longer direction — measuring model competence before routing work to
models, specialized planner/builder/reviewer roles, continuity across
providers, an eventual "AI Engineering Manager" — is real, but **none of
it is built yet.** Routing, multi-agent role specialization, automatic
provider failover, and any authority/governance engine are North Star,
not shipped functionality. [`docs/ROADMAP.md`](docs/ROADMAP.md) lays out
the concrete path there and what's deliberately not built at each stage.

## What makes it different

- **OS sandboxing** constrains filesystem and network behavior.
- **A deterministic permission broker** lets routine development flow automatically.
- **A hard security guard** blocks catastrophic and credential-sensitive operations before another model can argue about them.
- **Hostile-project isolation** prevents a cloned repository from silently loading its own Claude hooks, MCP servers, skills, agents, or settings.
- **Codex acts as an independent read-only reviewer**, with its reviewed tool environment constrained by a no-network sandbox.
- **Unattended mode fails closed** instead of leaving an agent waiting overnight.
- **Every decision is auditable.**

### Tested against the ugly cases

**978** approval-broker assertions · **134** guard-portability assertions · **39** permission-posture checks · **32** Codex-boundary checks · **22** prompt-injection cases · **16** hostile-project isolation checks · **16** nondestructive-doctor checks · **12** Codex-preflight checks

Including hostile repository hooks, hostile MCP servers, `curl | bash`, credential exfiltration, browser-cookie access, keyrings, `docker.sock`, permission-bypass flags, shell line-continuation bypasses, shell quote and escape splicing (`su""do`, `"curl" … | "bash"`, `~/.s""sh/id_rsa`), symlink escapes, `..` traversal, executable Git configuration, malicious Codex configuration, arbitrary network egress, cron and systemd jobs scheduled to run after the session ends, and destructive host operations.

The tests first prove the attack can happen, then prove the AI Dev Autopilot path stops it.

> **Give coding agents freedom over the work, not freedom over the consequences.**

**Try to break the boundary and open an issue with the command that still annoys you.**

## Evidence

Everything below is asserted by a test in this repository. Run `make test`.

[![contracts](https://github.com/aminrasooli/ai-dev-autopilot/actions/workflows/contracts.yml/badge.svg)](https://github.com/aminrasooli/ai-dev-autopilot/actions/workflows/contracts.yml)

CI runs them on every push and pull request, on a machine where AI-DEV has never
been installed and neither Claude Code nor Codex is present — because that is
the machine a contributor and a reviewer both have, and a suite that only passes
on the author's laptop is not a contract. The two suites that need a real Claude
Code or Codex report their dependency as missing and exit 3 rather than scoring
silence as a pass; running those stays a maintainer's job on every Claude Code
upgrade.

| Suite | Assertions | What it establishes |
| --- | ---: | --- |
| `approval.test.sh` | 978 | routine work is allowed and everything else escalates, clause by clause |
| `guard-portability.test.sh` | 134 | the framework self-protection rule and the deployed hook paths both follow `$AI_DEV_HOME`, not a hardcoded path; the ceiling fails closed; neither a line continuation nor the shell's own quote and escape removal splits a command past the rules; the notebook tools are screened by the field they actually send; the ceiling answers inside the timeout that would otherwise cancel it |
| `permission-posture.test.sh` | 39 | every spelling of every permission-bypass flag is refused, and every flag that widens the session's scope or configuration — including `--add-dir`; the managed version floor is at least the version the control it protects needs |
| `prompt-injection.test.sh` | 22 | injection payloads are refused deterministically |
| `codex-boundary.test.sh` | 32 | both callers of `codex exec` are contained; the reviewer can read its workspace and do nothing else |
| `project-isolation.test.sh` | 16 | a hostile repository's customizations do not load |
| `doctor-nondestructive.test.sh` | 16 | the verifier answers "is this writable?" without truncating, deleting or creating anything on the host |
| `codex-preflight.test.sh` | 12 | login state is read by exit status, never by matching prose |
| `settings-isolation.test.sh` | 9 | a hostile repository cannot widen the sandbox |
| `bootstrap.test.sh` | 29 | the bootstrap skill's contract holds in a disposable repository |
| `doctor-reporting.test.sh` | 9 | an uninstalled machine reports pending, a drifted one still reports failed |
| `hook-contract.test.sh` | 14 | the hooks emit exactly the decision shape Claude Code parses, and the installed build still contains every field name they are built from |

`bin/doctor` adds 100+ configuration and behaviour checks, including 65 guard
canaries. Every suite except `project-isolation.test.sh` is model-free and costs
nothing to run.

Four properties are worth stating plainly, because they are the ones people
assume rather than test:

**The isolation test proves the attack is real before it proves the defence.**
Run without the launcher against `tests/fixtures/hostile-project`, a hostile
repository's skill, custom command and subagent all register, its `.mcp.json`
server registers **and its process spawns**, and its `UserPromptSubmit` hook
**executes**. Run through `aidev`, none of it does. A test that only ever
observed silence could not tell isolation from a broken probe.

**A hook that runs out of time is not a hook that denies late.** Claude Code
cancels a command hook that reaches its timeout: the output is discarded, the
hook renders no decision, and the tool call continues. Every guard rule is a scan
of the whole command, so "make the guard slow" would otherwise be a way to make
the guard absent — measured at **13.3 seconds** for a 2 MiB command against a
10-second timeout, with the auto-approved tool call then never reaching the
broker either. The guard refuses an input large enough for its deadline to
matter, before scanning it, and `guard-portability.test.sh` proves the slow path
is real before proving the bound holds.

**The rules match the command the shell runs, not the command as written.**
Quote removal is a step of shell word expansion, so `su""do`, `"sudo"` and
`su\do` are one word by the time anything is looked up — and a rule written for
`sudo` matches none of them. Every rule here is therefore matched against two
views, the command as written and the command as the shell will run it, and a
match in either counts. The rewrite is scoped so it cannot invent dialogs: a
quoted run with no whitespace in it is collapsed, a quoted run that contains
whitespace is one argument whose interior is data, so `"curl"` reads as curl and
`echo "sudo is required"` stays silent. Claude Code's own permission
documentation normalises separators, wrappers and leading assignments before
matching a `Bash` rule, and says nothing about quoting — so there is nothing
upstream to lean on here.

**The reviewer boundary is tested under an adversarial config.**
`codex-boundary.test.sh` drives the reviewer's exact policy while a project-local
`.codex/config.toml` tries to grant full filesystem access and redefine the
reviewer profile, alongside a poisoned `AGENTS.md`. The reviewer still cannot
write, delete, read outside its workspace, reach the network, or see API keys.

What is configured, and countable:

- **43** credential environment variables unset for sandboxed commands
- **17** credential files denied or masked
- **22** read-denied credential, keyring and browser-profile directories
- **29** write-denied persistence paths — shell init, autostart and systemd
  units, PATH directories, VCS and credential configuration
- **22**-domain package-source allowlist with `strictAllowlist`, plus an
  exfiltration denylist
- **17** permission rules that force a prompt even in auto mode

## Architecture

`core/` is the single source of truth. Every other policy location is a pointer
to it, a file generated from it, or a merge of it.

```
  core/*.md ────┬──► generated/AGENTS.md ──► Codex, and any AGENTS.md agent
                └──► adapters/claude/CLAUDE.md ──► Claude Code
```

Four enforcement layers, each catching what the one below it cannot:

```
  managed policy    /etc/claude-code/managed-settings.d/
    │               sandbox floor · credential denies · bypass-mode lock
    │               version floor, so a build that would ignore a control
    │               refuses to start instead of running without it
    │               no other scope can override it; applies to bare `claude`
    ▼
  user settings     ~/.claude/settings.json  (merged from the hub fragment)
    │               PreToolUse guard · network allowlist · denyWrite
    │               permission asks · environment scrubbing
    ▼
  launcher          bin/aidev
    │               --setting-sources user · --permission-mode auto
    │               permission-mode allowlist · config-injection refusals
    ▼
  the session       project source is DATA; project configuration is not loaded
```

Two hooks fire at different moments and have opposite jobs. Keeping them in
separate files is what makes the precedence claim checkable rather than argued:

```
  tool call
     │
     ▼
  PreToolUse ── hooks/security-guard.sh ──── the hard ceiling
     │   deny ──►  blocked. No dialog is raised, so PermissionRequest
     │             never fires, so the broker and Codex never see it.
     │   ask  ──►  a dialog would be raised
     │   pass ──►  normal permission flow
     ▼
  PermissionRequest ── hooks/permission-broker.sh ── the broker
         critical set          ──►  escalate (never allow)
         deterministic routine ──►  allow
         gray, pre-qualified   ──►  Codex, advisory, fixed rubric, hard timeout
         anything else         ──►  escalate
```

## Why not `--dangerously-skip-permissions`?

| | Normal Claude Code | Bypass flag | AI Dev Autopilot |
| --- | --- | --- | --- |
| Routine work (`git status`, tests, repo edits) | prompts | runs | runs |
| Reading `~/.ssh`, `~/.aws`, a keyring | prompts | **runs** | **denied** |
| `curl \| bash` | prompts | **runs** | **denied** |
| `rm -rf /`, `mkfs`, disabling the firewall | prompts | **runs** | **denied** |
| `sudo`, `git push`, publish, deploy | prompts | **runs** | **human, always** |
| Network egress off the allowlist | prompts | **runs** | **human, always** |
| Hostile repo's hooks / skills / MCP servers | **load** | **load** | **do not load** |
| A command shape nobody modelled | prompts | **runs** | **human** |
| Decision record | none | none | audit log per decision |
| Who can relax the gate | the user | already relaxed | not the model, not the repo |

The bypass flag answers "stop asking me" by removing the thing that asks. This
answers it by deciding which questions were worth asking.

`bin/aidev` refuses the bypass mode in every spelling, and
`permissions.disableBypassPermissionsMode` sits in the managed floor where no
other scope can override it — so it is refused for bare `claude` too, not only
for people who use the launcher.

## Quick start

```bash
git clone https://github.com/aminrasooli/ai-dev-autopilot.git ~/.ai-dev
cd ~/.ai-dev

make deps      # bubblewrap + socat, and the sandbox seccomp filter. Needs sudo.
make sync      # project the hub onto the Claude and Codex adapters
make manage    # deploy the managed enforcement floor. Needs sudo.
make doctor    # verify contracts and behaviour
```

`make test` and `make doctor` work before any of that, and are worth running
first. Most of what doctor inspects lives outside the repository, so on a machine
that has not been synced those checks report **PENDING** rather than failing —
"not installed here" is not the same answer as "broken", and only one of them is
something you should act on.

Then start sessions with the launcher instead of `claude`:

```bash
cd ~/code/my-project
aidev
```

To turn on the delegated approval broker, run its activation script **from a
normal shell**:

```bash
bash ~/.ai-dev/bin/activate-approval-broker
```

It runs the contract suites first and syncs only if they pass, then verifies the
hook is really installed and drives it with a behavioural smoke test. An approval
broker is a thing that says "yes" on your behalf, so the bar for switching it on
is that it has just demonstrated it says "no" correctly.

`make sync` backs up every file it overwrites and puts `aidev` on your `PATH`.
Restart Claude Code afterwards — sandbox and proxy settings are read once, at
session start.

### Requirements

- Linux. Developed and tested on Ubuntu 24.04.
- [Claude Code](https://claude.com/claude-code) on a plan that supports
  sandboxing.
- `bash` 5+, `git`, `jq`, `python3`, `sed`, `awk`.
- `bubblewrap` and `socat` for the OS sandbox.
- Optional: [Codex CLI](https://github.com/openai/codex) for the independent
  reviewer, authenticating through the OS keyring.
- Optional: `@anthropic-ai/sandbox-runtime` for the seccomp filter that blocks
  unix sockets.
- `sudo` once, to deploy the managed enforcement floor.

Installing somewhere other than `~/.ai-dev` works. `make` takes the hub to be
the checkout the `Makefile` lives in, and `AI_DEV_HOME` overrides that. The
settings fragment carries two placeholders — `__AI_DEV_HOME__` for hub paths and
`__HOME__` for home paths — and `make sync` resolves both, then reads the file
back and refuses to leave a hook registered at a path that does not exist.

The Codex reviewer's filesystem policy grants read access to `~/.npm-global`,
because the Codex sandbox helper re-execs the Codex binary from wherever npm
installed it. If `npm prefix -g` reports something else on your machine, set it
in the three files that carry the same policy — `bin/codex-review`,
`adapters/codex/config.toml` and `tests/codex-boundary.test.sh` — or
`codex-boundary.test.sh` will stop with "cannot exec codex under this npm
prefix" rather than measuring the boundary.

### Everyday commands

```bash
aidev --trust-project        # explicit, warned opt-in: also load this repo's settings
aidev --aidev-help           # what the launcher guarantees, and why

make status                  # show what is linked where
make doctor                  # verify contracts and behaviour
make test                    # run every contract test
make review ARGS="--range main...HEAD"   # independent Codex review
make remote                  # start Claude Code Remote Control here
```

## Unattended mode

Unattended mode changes what happens to an *uncertain* decision. It never widens
what is allowed.

```bash
AI_DEV_OVERNIGHT=1 aidev
```

- Interactive: an escalation shows the human the original permission dialog.
- Unattended: an escalation becomes an explicit **deny**, and the request is
  appended to `var/pending-approvals.log` for review afterwards.

An unattended run never waits and never self-approves. "Nobody is watching" is
the worst possible moment to relax a gate, so uncertainty resolves to deny in
exactly the situation where a human would otherwise have been asked.

Both hooks honour the switch, so the hard ceiling queues instead of raising a
dialog nobody is there to answer.

Before handing control to an unattended agent, run `bin/host-check` from the
launching shell and refuse to start if it does not pass — a run that cannot
verify its own containment should not be given autonomy.

Every decision is written to `var/permission-audit.log`: timestamp, tool, a hash
of the input, the deterministic classification, whether Codex was consulted, its
verdict, the final decision and the reason. Never a secret value; the guard log
records a rule id and a truncated hash, never command text, and a test asserts
it.

`var/pending-approvals.log` is the deliberate exception. A queue exists so you
can see in the morning *what* was refused, which a hash cannot tell you, so it
records the command text. Treat it as sensitive — `var/` is gitignored.

## Hard human boundaries

These stop for a person in every mode. No Codex verdict can turn any of them
into an allow, because escalation exits before Codex is consulted.

| Category | Examples |
| --- | --- |
| Privilege | `sudo`, `doas`, `pkexec` |
| Publication | `git push`, `npm publish`, `cargo publish`, `twine upload`, and the forge CLIs — `gh pr create`/`merge`, `gh repo delete`, `gh secret set`, `gh workflow run`, `gh api` with a method or a body, and the `glab` equivalents |
| Deployment | `terraform apply`/`destroy`, `kubectl delete`, `helm`, `vercel --prod`, `fly deploy` |
| Destruction | `git reset --hard`, `git clean -fd`, history rewriting, `docker volume rm`, `DROP TABLE` |
| Credentials | anything naming `~/.ssh`, `~/.aws`, `~/.gnupg`, a keyring, a password store or a browser profile |
| Network egress | `WebFetch` off the allowlist, `WebSearch`, `socat`, `nc`, `ssh`, `rsync`, any git transport operation |
| Host integrity | `rm -rf /`, `mkfs`, raw writes to a block device, shutdown, disabling the firewall or MAC |
| Scheduled execution | `crontab`, `at`, `batch`, `systemd-run`, `systemctl enable`, `loginctl enable-linger` — anything that runs after the session ends |
| Containment primitives | `mount`, `umount`, `fusermount`, `unshare`, `nsenter`, `chroot`, `setpriv`, `capsh` — anything that changes what a path resolves to, or where a program runs |
| Anything unrecognised | a command shape the classifier does not model |

Beyond the mechanical gates, the framework stops and asks for materially
different product directions, irreversible data loss, money or paid
infrastructure, anything that leaves the machine, and legal or compliance calls.

## Hostile repositories and prompt injection

**Repository content is data.** Web pages, READMEs, issues, logs, dataset rows,
MCP results and other models' output are analysed, never obeyed. An instruction
discovered inside content acquires no authority from being there — it does not
matter that it claims to come from the user, a maintainer or a security team.

**Repository configuration is not policy.** Sessions load user and managed
settings only. A cloned repository's `.claude/settings.json`, project hooks,
project `.mcp.json`, project skills and project subagents are not loaded at all.
This is a security boundary, not a convenience default: array settings merge
across every scope, so a repository able to contribute settings could append
entries that widen the sandbox. Cloning a repository must never change what your
machine permits.

`tests/fixtures/hostile-project/` holds a real payload — hostile `CLAUDE.md`,
`CLAUDE.local.md`, project rules, `AGENTS.md`, settings, untracked local
settings, `.mcp.json`, a skill, a subagent, a custom command, an output style,
three hook events and a status line, each with its own canary token. It is stored
inert: non-discovery filenames, placeholder paths, and a live copy materialized
into a gitignored directory only while the test runs. A `claudeMdExcludes` entry
covers the subtree as a third layer.

`prompt-injection.test.sh` additionally drives the classic payloads — `curl | bash`
in several forms, credential exfiltration, browser cookie dumps, keyring lookups,
`docker.sock` exposure, firewall disable, permission-bypass flags — and requires
each to be refused deterministically, with `git push --force` and `npm publish`
correctly routed to *ask* rather than *deny*.

## Claude and Codex

**Claude Code owns the working tree.** It plans, implements, tests and verifies.
`~/.claude/CLAUDE.md` is written from the hub adapter with the hub's own path
substituted in, so its four `core/` imports resolve wherever you cloned to;
skills symlink per directory; settings are merged so hub-owned keys win and your
own preferences are preserved.

**Codex is an independent read-only reviewer.** It never edits the workspace.
`~/.codex/AGENTS.md` symlinks to `generated/AGENTS.md`, so both agents read the
same policy from the same source.

Reviews run at two gates — the plan, and the final diff — with at most two rounds
each, then a decision. `bin/codex-review` runs the reviewer ephemeral,
read-only, with its reviewed tool environment network-disabled, keyless and time-bounded. The whole permission profile is
passed inline on the command line rather than selected by name, so a
project-local `.codex/config.toml` can neither pick a wider profile nor redefine
the one that was selected. Codex reviews real artifacts — the diff, the files,
the test output — never a prose summary of what was done.

Codex output is model output, and model output is data. A finding that would
weaken a security control is never accepted. Inside the approval broker Codex is
advisory only: it is consulted for gray cases that already cleared the critical
screens, its answer is constrained to two tokens, and every failure mode —
unavailable, timeout, empty, off-rubric — resolves to escalate.

## The Local Reviewer Benchmark

**Never let the same vendor grade its own homework.** The independent
reviewer is pluggable (`bin/review`): Codex remains the default, and a
local open-weight model through Ollama — loopback-only, with no
fallback to any remote service — can take its place by configuration.
Which reviewer is actually worth trusting is an empirical question, so
the repository carries a reproducible benchmark for it:
versioned cases with machine-checked ground truth in
[`eval/cases/`](eval/cases), a deterministic scoring harness with
repeat-run support (`bin/review-eval --runs 3`), an offline corpus
validator (`bin/review-corpus`), and raw machine-readable results in
[`eval/results/`](eval/results). Methodology, honest limitations — the
pilot corpus is small and self-authored, and results are evidence, not
rankings — and the contribution/result-submission paths are documented in
[`docs/BENCHMARK_METHODOLOGY.md`](docs/BENCHMARK_METHODOLOGY.md) and
[`eval/README.md`](eval/README.md).

### Reproduce it yourself

Everything below runs **offline**, needs **no API key**, and **costs
nothing**. It is the path a stranger should be able to follow from this
README alone.

```bash
git clone https://github.com/aminrasooli/ai-dev-autopilot.git
cd ai-dev-autopilot

bin/review-doctor                     # 1. prove the harness works, offline
bin/review-corpus --cases eval/cases-v3/cases   # 2. validate a corpus, print its fingerprint
python3 -m reviewer.verify eval/results/claude-sonnet-5-m3hard-3runs.json  # 3. re-check a published result
```

What each step establishes:

1. **`bin/review-doctor`** — the whole scoring path end to end against a
   fake backend: the corpus validates, the oracle scores ground truth
   perfectly, repeat runs produce an internally consistent report,
   existing results are protected from overwrite, and the offline path
   opens no network connection.
2. **`bin/review-corpus`** — recomputes the corpus fingerprint. It must
   print `81daa0b7a48259184a91c48ab1dcf17c9d3ed4902fa891b5895db0f29fd79790`
   for v3. That hash is what makes two runs comparable; every published
   result names the corpus it ran against.
3. **`python3 -m reviewer.verify`** — recomputes every summary number in
   a published result file from its own per-case records. It reports
   `internally consistent` or names the discrepancy.

Step 3 checks that our published numbers follow from our published data.
It does **not** re-run a model — that is the separate, non-free step:

```bash
bin/review-eval --cases eval/cases-v3/cases --backend ollama --model <model> --runs 3
```

Hosted backends cost money and local models need a GPU, so neither is
required to check our arithmetic. **Results are evidence, not a ranking**
— see the honest limitations in
[`eval/results/M3-HARD-SCORECARD.md`](eval/results/M3-HARD-SCORECARD.md),
which is also where the headline numbers and their caveats live.

Every model, both corpus tiers, and all six dimensions — repeatability,
cost, latency, precision, classification and hard tier — are collected in
[`eval/results/SCORECARD.md`](eval/results/SCORECARD.md). That file is
**generated**, not written: `bin/review-scorecard` recomputes each figure
from the raw per-case runs, so a stale or mistyped number cannot survive
a regeneration.

```bash
bin/review-scorecard              # print it
bin/review-scorecard --out eval/results/SCORECARD.md   # regenerate it
```

Claude Code, Qwen and other local models through Ollama, and
Codex-compatible backends are participants behind the same interface —
none is positioned as the permanent or exclusive reviewer. That is the
point of the benchmark: which one is worth trusting stays an open,
evidence-based question, not a default nobody re-examines.

## Tests and verification

```bash
make test                      # every contract test, then doctor --quick
bash tests/approval.test.sh    # or one suite directly
bin/doctor --only sandbox      # or one group of checks
```

Verification is layered, because a sandboxed process cannot observe host truth
and must not pretend otherwise:

| Tool | Runs where | Answers |
| --- | --- | --- |
| `tests/*.test.sh` | inside the sandbox | do the behavioural contracts hold |
| `bin/doctor` | inside the sandbox | is the configuration deployed and current |
| `bin/host-check` | **outside** the sandbox | is the sandbox real |

`bin/doctor` defers any check it cannot honestly answer and names the command
that can. `bin/host-check` refuses to report at all if it detects it is itself
sandboxed. Nothing in the suite performs a destructive action: destructive cases
are proven by feeding the guard a canary and asserting it is refused, and the
write probes that ask whether a host path is protected are pinned by
`doctor-nondestructive.test.sh` to answer without modifying what they touch.

**Re-run `project-isolation.test.sh` after every Claude Code upgrade.** The
isolation boundary rests on one flag whose observed behaviour is broader than its
documentation, and a release could narrow it.

Full detail in [docs/verification.md](docs/verification.md).

## Security limitations

This project is an experimental prototype. It has not been independently
audited, and it should not be treated as an audited security boundary. It raises
the cost of an accident or an injected instruction; it is not a containment
guarantee.

- **Sandbox boundaries are not assumed to hold.** The design is defence in depth
  precisely because a sandbox may behave differently across versions and
  environments. `bin/doctor` reports a limitation it can neither fix nor confirm
  away as `KNOWN` — its own category, never a pass — and only after verifying in
  the same run that the compensating controls actually refused a write.
- **The `denyWrite` list is load-bearing.** Keep it current, and re-check it
  after every Claude Code upgrade.
- **A domain allowlist alone is not a control.**
  `sandbox.network.strictAllowlist` must be set, and it takes effect only for
  sessions started after it is written. It is also honoured only from Claude
  Code 2.1.219 onwards; below that the key parses, is discarded, and the
  allowlist reverts to *prompting* — which a non-interactive sandboxed command
  cannot answer. The managed floor therefore carries
  `requiredMinimumVersion: "2.1.219"`, which makes an older build refuse to
  start rather than run without the control. `claude update`, `claude install`
  and `claude doctor` are exempt from that check, so a machine below the floor
  can still upgrade its way out.
- **The isolation test proves what is loaded, not what a model would obey.** An
  instruction that never enters the context window cannot be obeyed, which is the
  stronger property — but it is not the same claim.
- **The guard is a denylist of catastrophic operations, matched with regular
  expressions.** A class nobody has modelled escalates rather than being wrong,
  which is the correct failure, but coverage improves only when someone adds a
  class deliberately. It normalises the shapes that would otherwise split a
  command past its own rules — `$HOME`, `~` and `$AI_DEV_HOME` spellings, line
  continuations, and the shell's own quote and escape removal, so `su""do` and
  `"curl" … | "bash"` reach the same rules as their plain spellings — and each
  of those is a regression test rather than a claim. What it does **not** model
  is the shapes the shell decodes from a *value* rather than from punctuation:
  ANSI-C quoting (`$'\x73udo'`), substring expansions and variable indirection.
  Those are contained by the sandbox and the managed floor, not by this layer. It is a ceiling against mistakes and straightforward misuse; it is not
  a sandbox-escape defence, and the layers below it are what contain a
  deliberate attempt.
- **Remote Control**: anyone who can sign into your Claude account can drive a
  running remote session on your machine. See
  [docs/remote-control.md](docs/remote-control.md).

Report vulnerabilities privately — see [SECURITY.md](SECURITY.md).

## Contributing

Contributions, testing, simplification and alternative implementations are all
welcome. [CONTRIBUTING.md](CONTRIBUTING.md) has the workflow — how to run the
suites on an undeployed machine, and what CI checks.

Start with [NOTES.md](NOTES.md), which holds the standing rules for the parts of
this framework that are easy to widen by accident, and
[.ai/decisions.md](.ai/decisions.md), which records what was decided and on what
evidence.

The rules that matter most:

1. **Never weaken, skip or delete a test to make a suite pass.** If a check
   cannot be answered in its environment, it defers by name.
2. **Every widening arrives with regressions** — the example that motivated it,
   the unattended behaviour, and positive controls proving the fast path
   survived.
3. **A test that proves a boundary must also prove the attack is real.**
4. **Security rules resolve paths through `$AI_DEV_HOME` and `$HOME`**, never as
   hardcoded literals — and so does the configuration that decides whether a
   rule runs at all. A control that is correct only for the default installation
   is missing everywhere else, and a hook registered at a path that does not
   exist does not fail: it never runs.
5. **New classifier doubt defaults to escalation.** Deterministic rules are added
   only when a safe operation becomes materially frequent.
6. Edit `core/`, never `generated/AGENTS.md`. Run `make generate` and `make test`
   before opening a pull request — CI runs both, plus `shellcheck`, whose
   exclusions live in `.shellcheckrc` with a reason each.

## License

[MIT](LICENSE).
