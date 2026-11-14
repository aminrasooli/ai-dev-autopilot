# Per-project integration guidance

This kit is generic and vendor-neutral by design (no personal values are
hardcoded). The notes below are how another project *would* adopt it —
written as guidance, not applied as code anywhere else, for two reasons:

1. **Write-scope collision.** Several target projects already have their
   own active development sessions and, in at least one case, an existing
   in-progress Anthropic integration. Writing into those trees from an
   unrelated session risks exactly the kind of collision a one-writer-at-
   a-time policy exists to prevent — and risks duplicating work instead of
   reusing it.
2. **This session's filesystem access was scoped to one repo** that both
   had a reachable git remote and no other active session attached. Other
   target projects weren't reachable from here at all.

## A privileged orchestration system

One target project already runs a privileged, root-owned autonomous-agent
orchestration layer (service accounts, no interactive shell, no sudo for
the agent roles themselves) that is explicitly a sealed, reviewed
deployment with its own owner-gated change process. Nothing in this kit
should be wired into a system like that without going through its own
process — that is a privileged, infrastructure-level change, not an
application-level integration, and well outside what an unprivileged
session can or should do.

## This repo (AI Dev Autopilot)

Done — see `demos/jp_autopilot_demo.py`. A vendor-neutral, read-only,
budget-gated Agent SDK demo lives alongside the existing Claude Code/Codex/
Qwen adapters. It is additive: nothing about the existing subscription-based
CLI flows changes.

## Projects with their own active sessions / existing integrations

At least one other project already has its own mature, actively-developed
Anthropic integration (its own provider runtime, budget tracking, and
model config). At least one more already has a live, configured API key
and its own provider wiring. In both cases, the right move is for that
project's own session to extend what it already has — not for this one to
introduce a second, parallel implementation. If this kit's pricing table
or budget-cycle math is useful as a reference, that project's own session
should read this repo rather than have this session write into theirs.

## General guidance for any new adopting project

```python
from anthropic_api_kit import load_config, ApiAdapter, BudgetExhausted
config = load_config("<project-prefix>", ledger_dir="./var")
```

- Use `difficulty="routine"` for the common case; reserve `"hard"` for
  genuinely difficult requests — it's the expensive tier.
- Never route sensitive personal data (health, pregnancy, financial
  records, identifiable imagery) through any API-billed path without an
  explicit, separately authorized review of that specific data flow.
- `ApiAdapter.complete()` has no tool-use or execution capability — it
  cannot place trades, modify files, or take any action on its own. Any
  project wiring its output into an execution path (orders, deployments,
  merges) must add its own explicit human-approval gate before that step;
  this kit intentionally does not provide one, because it does not need one.
- For grounded Q&A / research use cases, use the Anthropic SDK's own
  `web_search` server tool directly rather than this kit — this kit
  intentionally stays scoped to the plain single-call case.
