# Report — Anthropic API credits integration (2026-11-13)

Org: **Amin's Individual Org** (Console). Next monthly credit: **2026-11-21**.
This report does not assume any of the $200 remains unused — see "Billing
visibility" below for why that can't be verified from here.

## Billing visibility — owner action required

There is **no supported way to read the Console org's current credit
balance from this session**:
- No Admin API key (`sk-ant-admin-...`) or `org:admin` OAuth token is
  configured anywhere this session could read (checked `~/.env*`,
  project env files reachable from this session — none set).
- The regular Messages API has no balance-read endpoint; usage/cost
  reporting lives under the beta Admin API (`client.beta.organization`)
  and requires that admin credential.
- Network egress to `api.anthropic.com` works (confirmed: unauthenticated
  request returned HTTP 401, not a network block), so once an admin
  credential exists, programmatic usage/cost checks are possible.

**Owner action:** log into the Console UI directly (console.anthropic.com)
under Amin's Individual Org to see current balance/usage, or generate an
Admin API key if you want this automated going forward (rotate/scope it
carefully — an Admin key can read org-wide usage and manage members/keys).

## What changed this session

One repo was actually modified: **`ai-dev-autopilot`**, on a new branch
`feature/anthropic-api-adapters`, committed but **not pushed** (see
"Publication" below). Everything else is guidance only — see "Why not
more repos" below.

New directory: `integrations/anthropic-api-kit/` —
- `anthropic_api_kit/` — the reusable adapter (config, pricing, budget,
  rate limiting, client wrapper). Uses the official `anthropic` Python SDK.
- `demos/jp_autopilot_demo.py` — end-to-end demo using the official
  **Claude Agent SDK** (`claude_agent_sdk`), read-only tool surface,
  two independent budget ceilings, writes a report file, touches nothing
  else.
- `tests/` — 22 unit tests, all passing, all network-free.
- `README.md`, `PER_PROJECT_INTEGRATION.md`, `.env.example` — onboarding
  docs; no secrets anywhere.

### Why not more repos

Two independent constraints, discovered mid-session:
1. **This sandboxed session's `~/code` and `~/projects` are mounted
   read-only.** Only `~/ops` and a scratch/tmp directory were writable.
   Code could only reach an existing repo by cloning it to scratch and
   pushing a branch over git — which only works for repos that (a) have a
   remote and (b) I judged safe to push to (see Publication below).
2. **Several target repos already have live attached sessions** (checked
   via the session list): `personal-trading-lab` (x2, one busy),
   `photo-macro-pregnancy-stage` (busy), `photo-macro-tracker-beta`,
   `bergamasco-site`, `jp-manager`. Writing into those trees from this
   session would risk exactly the collision `~/ops/SYSTEM.md` rule 8 warns
   against. `PER_PROJECT_INTEGRATION.md` has concrete, ready-to-apply
   guidance for each of those sessions to pick up instead of me touching
   their trees.

### Publication

The `feature/anthropic-api-adapters` branch is **committed locally in a
scratch clone, not pushed**. `ai-dev-autopilot` is a public repo
(`github.com/aminrasooli/ai-dev-autopilot`) with its own review step
(`make review` → `bin/codex-review`); pushing a new branch to a public
remote is a publication action I didn't want to take unilaterally without
you deciding on timing/review. To publish it yourself:

```
# from a non-sandboxed session with write access to ~/code/ai-dev-autopilot
cd ~/code/ai-dev-autopilot
git fetch <scratch-clone-path-or-just-recreate-the-diff>
git checkout -b feature/anthropic-api-adapters origin/main
# apply the same files (they're self-contained under integrations/anthropic-api-kit/)
git push -u origin feature/anthropic-api-adapters
```
Or tell me to push it myself and I will (git mutations are currently
allowed — outside the Mon-Fri 07:00-15:00 PT freeze window as of this
report).

## Per-project status

| Project | Current integration | What was implemented | API features used | Tests | Credits-eligible? | Missing creds/workspace | Est. cost | Remaining owner steps |
|---|---|---|---|---|---|---|---|---|
| **AI Dev Autopilot** | Claude Code CLI (subscription) for the autopilot loop itself; no API-billed path existed | `anthropic_api_kit` + Agent SDK demo, additive, committed to a feature branch | Messages API (`anthropic` SDK), Agent SDK `query()`/`ClaudeAgentOptions` (model, env, max_budget_usd, allowed/disallowed_tools) | 22/22 pass locally | Yes — scoped read-only review runs | `JPAUTOPILOT_ANTHROPIC_API_KEY` (project workspace + key not yet created) | ~$0.001–0.01 per demo run at `claude-haiku-4-5`, capped by `max_budget_usd=0.50` and the local ledger | Create Console project workspace "jp-autopilot" + scoped key; decide whether to push the branch |
| **JP Manager** | Claude Code CLI (subscription) under root-brokered service accounts — sealed deployment | Nothing — out of scope (privileged, root-owned, no sudo available, explicitly "no custom dashboard/scheduler") | n/a | n/a | Not under this session's authority to say — any API-billed role would be a privileged change to a reviewed deployment | n/a | n/a | JP's own decision whether Paperclip should ever gain an API-billed (vs. subscription) role; that's a DESIGN.md-level change |
| **CAL / PAL** (photo-macro-tracker family) | Unknown to this session — has its own live attached sessions; not independently re-verified here to avoid collision | Guidance only (`PER_PROJECT_INTEGRATION.md`) | n/a (not applied) | n/a | Likely yes, for non-sensitive description/summarization tasks only | Needs its own project workspace + key if adopted | Depends on usage volume | Health/pregnancy data-handling review required before any image/record touches the API (rule 10) — explicit JP sign-off needed per data flow |
| **Trading Lab** (personal-trading-lab) | Unknown to this session — two live attached sessions | Guidance only | n/a (not applied) | n/a | Yes, for critique/research only, never execution | Needs its own project workspace + key if adopted | Depends on usage volume | Confirm no output path reaches an order-placement system before wiring anything |
| **CSI** | **Not found.** No project named CSI (or an obvious variant) exists under `~/projects` or `~/code` per `~/ops/PROJECTS.md` | Nothing — can't integrate a project that doesn't exist in the registry | n/a | n/a | Unknown | n/a | n/a | Tell me the actual project path/name, or confirm it hasn't been created yet |
| **Bergamasco site** | Local-only repo (no git remote), live attached session, static Python pipeline | Guidance only | Would use the Messages API's `web_search` server tool for grounded Q&A (not wrapped by this kit) | n/a | Yes, for content drafting / grounded Q&A | Needs its own project workspace + key if adopted | Depends on usage volume | No remote means no scratch-clone-and-push path for me regardless of collision risk — that session must apply changes directly |

## Owner authorization checklist (Console, UI-only — cannot be done from any session)

1. Confirm current credit balance for Amin's Individual Org (console.anthropic.com → Usage/Billing).
2. Decide which projects get their own **workspace** inside the org (recommended: one per adopting project — `jp-autopilot`, and later `cal`, `tradinglab`, `bergamasco` if/when adopted).
3. Generate one **workspace-scoped** API key per adopting project. Never reuse one key across projects — that's exactly what `config.py`'s per-project env-var naming is built to prevent on the code side.
4. Set a **per-workspace spend limit** in the Console if available for the org tier, as a second ceiling above this kit's local budget — this kit's local ledger cannot see or enforce the Console's own caps, only its own.
5. Do **not** enable auto-reload / purchase additional credits (per your instruction 11) — confirm this is already off at the org level; this session has no way to check or change that setting.
6. Understand: unused monthly credit **expires** — it does not roll over (standard Anthropic Console behavior; if Amin's Individual Org's plan differs, the Console billing page will say so — verify there rather than trusting this line).

## What's genuinely safe to run today

Only the no-credentials path: `python demos/jp_autopilot_demo.py` prints
the blocked message and exits 0. Nothing in this session made a real API
call anywhere (confirmed: no key was ever available for it to use).
