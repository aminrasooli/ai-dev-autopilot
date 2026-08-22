# North Star — FUTURE / NOT IMPLEMENTED

This document records a longer-term vision that is **not part of this
repository today**. It exists so that ideas raised while building the
pluggable reviewer (`reviewer/`) have a home other than the production
tree. Nothing below should be inferred as planned, scheduled, or even
agreed to — it is a parking lot, not a roadmap.

Git remembers committed work. This file remembers the vision. The
production tree should stay small.

## What's actually implemented today

A single, narrow wedge: an independent code reviewer that can run against
Codex (default, unchanged) or a local model through Ollama, selected by
configuration, with a shared prompt/output contract and a versioned
seeded-defect benchmark (`eval/`, methodology in
`docs/BENCHMARK_METHODOLOGY.md`) that scores every backend identically.
See `reviewer/`.

## The human moves up the hierarchy (operating-model requirement)

Unlike the deferred architecture below, this section is a standing
*product requirement* that already governs how work on this repository
is run: the human operator sets direction, and stops being the message
bus.

The intended operating model:

- The human gives direction roughly **1–3 times per day** — charters,
  consequential decisions, gate authorizations — not continuous
  supervision.
- Agents execute, test, review, retry, and hand work to each other
  through **persistent, machine-readable artifacts** (charters, reports,
  git state), never by the human copying output between terminals,
  chats, or reviewers. The handoff contract lives in
  [`docs/HANDOFF.md`](HANDOFF.md).
- Human-only gates are **batched**, not scattered: an autonomous block
  finishes with one consolidated list of everything that needs a human,
  each item carrying the exact action, the reason, and the risk.
- Routine implementation, testing, review, and retries proceed
  autonomously *within an approved charter's scope*.

**Metric: Human Operator Touches per day.** A touch is a meaningful
human interaction that the system required in order to proceed:

- counts: a new direction/charter, a consequential architecture or
  product decision, a merge authorization, a secret/passphrase action, a
  privileged system action, a publication authorization
- does not count: passive status notifications, agent-to-agent handoffs
  through artifacts, CI runs, internal retries, agents reading prior
  reports/state

Target: **≤3 meaningful touches per day.** Current baseline: not yet
measured — no historical numbers are claimed; measurement starts when
the recording convention in `docs/HANDOFF.md` is actually used.

The governing principle: **reduce touch frequency, never remove
accountability.** Gates that stay human — merge to main, secrets,
privileged system changes, external publication, unusual spend,
direction changes — are kept *because* everything routine no longer
needs a human, which is what makes the remaining touches meaningful.

## Deferred vision

- **Multi-seat team.** A strategist seat (plans, doesn't touch code), a
  builder seat (writes code), and a supervisor seat (routes, escalates)
  as distinct roles with distinct authority, rather than one agent doing
  everything.
- **Roles separate from runtimes separate from models.** "Builder" as a
  role that could be filled by different agent runtimes (Claude Code
  today, something else tomorrow), each of which could be backed by
  different models, without the role's contract changing.
- **Replaceable agent runtimes.** Claude Code is currently the only
  runtime that does the actual coding work. A future version might treat
  the coding runtime itself as pluggable, the way the reviewer is now.
- **Cost-aware routing.** Today cost is only measured (latency, tokens,
  and an honestly-labeled external-cost string), never used to make
  decisions. A future router could pick QUALITY / BALANCED /
  COST_OPTIMIZED policies and route work accordingly.
- **Full offline mode.** Today only the reviewer stage can be proven to
  stay local when configured for Ollama ("local review stays local" —
  not a claim about the rest of the workflow, which still talks to
  Anthropic). A real offline mode would need every stage, not just
  review, to have a local path and a policy that refuses network egress
  outright.
- **Action-class authority engine.** A deterministic policy that decides,
  per class of action (file edit, shell command, network call, deploy),
  which seat or runtime is allowed to take it without human sign-off.
- **Model discovery and benchmark-before-promotion.** Automatically
  finding what models are available locally or remotely, benchmarking
  them against the seeded-defect harness (or successors to it), and only
  promoting a model to default use once it clears a bar — never
  auto-selected without a human looking at the numbers first.
- **Quality / cost / privacy policies as first-class config.** Letting a
  user declare "never send this repo's diffs off-box" or "optimize for
  cheapest reviewer that still catches criticals" as policy, rather than
  each script hardcoding a choice.
- **Locally hosted teams.** Running more than just the reviewer against
  local models — builder and strategist roles backed by local models too,
  for users who want the whole loop on-box.
- **Additional providers.** Other cloud reviewers or coding backends
  beyond Codex, and other local runtimes beyond Ollama, added the same
  way Ollama was added here: as a config-selected implementation of an
  existing interface, never as a special case baked into the core.

## Why this file exists

Scope creep re-enters through good ideas raised mid-implementation. This
file is where those ideas go instead of into the reviewer wedge's PR.
Anything here that becomes real work should get its own scoped proposal
and its own PR — not be built opportunistically because the code was
already open.
