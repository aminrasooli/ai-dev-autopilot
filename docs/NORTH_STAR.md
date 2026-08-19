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
configuration, with a shared prompt/output contract and a seeded-defect
evaluation harness that scores both identically. See `reviewer/`.

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
