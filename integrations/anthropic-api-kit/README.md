# anthropic-api-kit

A small, reusable, **project-scoped** adapter for calling the Anthropic Claude
API directly — separate from the Claude Code subscription used by this
machine's interactive sessions. It exists so individual applications (an
autopilot run, a photo-analysis service, a research pipeline) can spend a
little of a project's own monthly API credit allotment, safely, without:

- ever reading another project's credential,
- ever retrying past a real credit-exhaustion response,
- ever exceeding a locally-enforced monthly budget,
- or ever taking a destructive action with what the model returns.

This is a library, not a service: no new port, no new daemon. Every caller
imports it into its own process and supplies its own config.

## What's here

| Path | What |
|---|---|
| `anthropic_api_kit/config.py` | Per-project config: API key env var is always `<PREFIX>_ANTHROPIC_API_KEY`, never a bare `ANTHROPIC_API_KEY` |
| `anthropic_api_kit/pricing.py` | Static per-model USD/MTok pricing table + cost estimator |
| `anthropic_api_kit/budget.py` | Local JSONL usage ledger + monthly-cycle budget gate (pre-call, pessimistic) |
| `anthropic_api_kit/ratelimit.py` | In-process sliding-window call limiter (courtesy ceiling, not a substitute for Anthropic's own limits) |
| `anthropic_api_kit/client.py` | `ApiAdapter` — wraps `anthropic.Anthropic`, model-tier selection, SDK-native retries/timeout, usage logging |
| `demos/jp_autopilot_demo.py` | End-to-end demo using the **Claude Agent SDK** (`claude_agent_sdk`) — read-only, three-tool, budget-gated autonomous review |
| `tests/` | Unit tests (pricing, budget cycle math, config scoping, rate limiter, client budget-gate, demo graceful-exit) — all network-free except the demo path, which is gated by a configured key |

## Why a monthly-cycle budget, not a calendar-month one

The Console credit grant lands on a fixed day of the month, not necessarily
the 1st — `budget.py`'s `_cycle_start()` defaults `anchor_day` to 21, but
every caller should set it to match their own org's actual grant day, so
"spent this cycle" means "spent since the credits most recently landed,"
not "spent since the 1st of the month."

## What this kit does NOT do

- It does not read or report your Anthropic Console **account balance**.
  There is no supported API for that without an **Admin API key**
  (`sk-ant-admin-...`) or an `org:admin` OAuth token — see `REPORT.md`.
  Local budget tracking here is a independent, conservative local cap; it
  has no visibility into the real org-level balance.
- It does not auto-reload credits or purchase more. Hitting the local cap
  (or Anthropic itself reporting credits exhausted) always raises and stops
  — callers are expected to fall back to deterministic behavior.
- It does not centralize credentials. Nothing here can hold more than one
  project's key at a time; there is no shared keystore.

## Quick start for a new project

1. Pick a short, uppercase-able project prefix (e.g. `CAL`, `TRADINGLAB`).
2. In the Console (owner action — see `REPORT.md`), create (or confirm) a
   project workspace and generate a key scoped to it.
3. In *your own project's* `.env` (never this repo's), set:
   ```
   <PREFIX>_ANTHROPIC_API_KEY=sk-ant-...
   <PREFIX>_MONTHLY_BUDGET_USD=<your cap, well under your org's monthly credit grant>
   ```
4. In your code:
   ```python
   from anthropic_api_kit import load_config, ApiAdapter, BudgetExhausted

   config = load_config("cal", ledger_dir="./var")  # ledger stays in YOUR project
   adapter = ApiAdapter(config)

   try:
       response = adapter.complete("Summarize these macros...", difficulty="routine")
   except BudgetExhausted:
       # fall back to the existing deterministic path — never crash the caller
       ...
   ```
5. Run `pytest` here once to confirm the kit itself is healthy before wiring
   it into your app; your app should also get its own test for the fallback
   path (budget exhausted -> deterministic behavior), since that's the path
   that will actually run once the monthly credit is spent down.

## Running the JP Autopilot demo

```
cd integrations/anthropic-api-kit
python3 -m venv .venv && .venv/bin/pip install -e ".[agent-sdk,dev]"
JPAUTOPILOT_ANTHROPIC_API_KEY=sk-ant-... .venv/bin/python demos/jp_autopilot_demo.py
```

Without the key set, it prints what it would do and exits 0 — no network
call is made. See `demos/jp_autopilot_demo.py`'s module docstring for the
exact safety surface (read-only tools, two independent budget ceilings, no
git/bash/file-write access for the agent).
