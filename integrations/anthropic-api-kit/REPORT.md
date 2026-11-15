# Status report — anthropic-api-kit

## Billing visibility — owner action required

There is no supported way to read a Console organization's current credit
balance from inside this kit or this demo:
- No code path here holds or wants an Admin API key
  (`sk-ant-admin-...`) or an `org:admin` OAuth token — regular API keys
  cannot read organization-level balance/usage.
- The Messages API itself has no balance-read endpoint; usage/cost
  reporting lives under the beta Admin API (`client.beta.organization`)
  and needs that admin credential.

**Owner action:** check current balance/usage directly in the Console UI
(console.anthropic.com), or generate a scoped Admin API key if you want
this automated later (an Admin key can read org-wide usage and manage
members/keys — scope and rotate it carefully; this kit never uses one).

## What's here

- `anthropic_api_kit/` — reusable, project-scoped adapter around the
  official `anthropic` SDK: per-project credential scoping (the API key
  env var name is always `<PREFIX>_ANTHROPIC_API_KEY`, never a bare
  `ANTHROPIC_API_KEY`), a static pricing table + cost estimator, a local
  monthly-cycle budget ledger with a pre-call pessimistic gate, an
  in-process rate limiter, SDK-native retries/timeout.
- `demos/jp_autopilot_demo.py` — end-to-end demo on the official
  **Claude Agent SDK**. Two run modes:
  - `--smoke-test`: one minimal, bounded-cost real call through the plain
    Messages API (not the Agent SDK) — the "did the key actually work"
    check. Prints the real response and real token-accounted cost, or the
    exact error; never claims success without having made the call.
  - default: a read-only (Read/Grep/Glob only — Bash/Edit/Write/
    NotebookEdit disallowed), two-ceiling budget-gated autonomous code
    review that writes a report file and touches nothing else.
- `tests/` — 24 unit tests, all passing, all network-free (including a
  test that the Agent-SDK subprocess env never leaks a fallback
  credential — see "Auth-fallback hardening" below).
- `PER_PROJECT_INTEGRATION.md` — generic adoption guidance for other
  projects (not applied anywhere outside this repo this session).

## Auth-fallback hardening

The Claude Agent SDK spawns the Claude Code CLI as a subprocess that
**inherits this process's full environment** and then applies
`ClaudeAgentOptions.env` on top (confirmed by reading the installed
`claude_agent_sdk` package's `subprocess_cli.py` — it merges, it does not
replace). The documented credential resolution order is
`ANTHROPIC_API_KEY` → `ANTHROPIC_AUTH_TOKEN` → active OAuth profile →
Workload Identity Federation → default profile on disk.

Setting `ANTHROPIC_API_KEY` should already win regardless of what else is
inherited (it's first in that order), but the demo does not rely on that
alone: `_locked_down_env()` also blanks `ANTHROPIC_AUTH_TOKEN` and every
documented WIF variable in the child process's env, so there is no second
credential for the CLI to silently fall back to if the project-scoped key
is ever rejected or exhausted. A rejected/exhausted key produces a visible
error (`result.is_error` is checked and reported); the demo never retries
past it and never falls back to a different credential or model tier on
its own.

Precedence alone was judged insufficient (2026-11-14): with the default
`~/.claude` config dir and no API key, the bundled CLI (2.1.325) reports
`authMethod: claude.ai` — i.e. it would bill the owner's Claude
subscription. So the demo now also isolates the CLI structurally:

- `CLAUDE_CONFIG_DIR` points at a fresh, empty per-run temp dir, so
  `~/.claude/.credentials.json` (the subscription login) is unreachable.
  Verified offline: under that dir with no key, `claude auth status`
  reports `loggedIn: false, authMethod: none`; with a key, `api_key`.
- `CLAUDE_CODE_OAUTH_TOKEN` and `CLAUDE_CODE_USE_BEDROCK/VERTEX/FOUNDRY`
  are blanked; `ANTHROPIC_BASE_URL` is pinned to `https://api.anthropic.com`.
- `setting_sources=[]`: no user/project settings are loaded, so a reviewed
  repo's `.claude/settings.json` cannot inject `env` or an `apiKeyHelper`.

The plain Messages API path (`ApiAdapter`, used by `--smoke-test`) sends
only the explicit project key — verified that an inherited
`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN` or `ANTHROPIC_PROFILE` is never
sent instead of or alongside it. The SDK *does* honor an inherited
`ANTHROPIC_BASE_URL`, which would have sent the key to another host, so
`base_url` is now pinned in `client.py` (test:
`test_only_project_key_is_sent_and_host_is_pinned`).

## Cost-estimate accuracy

Pricing in `anthropic_api_kit/pricing.py` is a static table dated in
`PRICING_LAST_VERIFIED`. It is deliberately a hard lookup (`KeyError` on
an unlisted model) rather than a guess, so a new model never gets silently
mis-priced. Re-verify against the current Claude API pricing page before
trusting it for a new model or a long time after `PRICING_LAST_VERIFIED`.

## Owner setup checklist (Console UI — cannot be done from any coding session)

1. In the Console, under your organization, create (or reuse) a workspace
   for this integration.
2. Generate one **workspace-scoped** API key for it. Never reuse one key
   across projects — the per-project env-var naming in `config.py` exists
   specifically so that mistake can't happen silently on the code side.
3. Set a per-workspace spend limit in the Console if your plan supports
   one, as a second ceiling above this kit's own local budget ledger —
   this kit cannot see or enforce the Console's own caps, only its own.
4. Confirm auto-reload / additional credit purchase is off at the org
   level, if that applies to your plan — this kit has no way to check or
   change that setting.
5. Unused monthly credit typically does not roll over on the standard
   Anthropic Console plan; verify your plan's actual behavior on the
   Console billing page rather than assuming.

## What's genuinely verified

- The no-credentials path: both `demos/jp_autopilot_demo.py` and
  `demos/jp_autopilot_demo.py --smoke-test` print a `[blocked]` message
  and exit 0 with no API key configured — confirmed by running them, not
  just reading the code.
- **2026-11-14, real smoke test succeeded** (one call, SDK retries set to
  0): `claude-haiku-4-5` → served by `claude-haiku-4-5-20251001`, reply
  `OK.`, `stop_reason=end_turn`, usage 15 input / 5 output tokens,
  `service_tier=standard`, estimated cost **$0.00004**, recorded in the
  local ledger. The key used is a real `sk-ant-` API key; the earlier
  failure was a Console workspace ID stored in place of a key.
- Earlier run: one real `--smoke-test` call against the then-configured
  value returned **HTTP 401, `Invalid bearer token`**. A 401 is rejected
  before reaching a model, so **zero tokens were consumed and nothing was
  billed**. This exposed a real bug (fixed): the adapter's exception
  handling didn't have a 401-specific branch, so it surfaced as a raw,
  uncaught SDK exception instead of a clean error — `client.py` now maps
  `anthropic.AuthenticationError` to a dedicated `InvalidCredentialError`,
  distinct from `CreditsExhaustedError`, with tests covering both the
  mapping and that nothing gets recorded to the budget ledger for a
  rejected call.
- Not yet exercised against the real API: the full Agent SDK review mode
  (owner-initiated only; capped at $0.50 per run by `max_budget_usd`).
