# Open-source-before-build policy

**Public.** One rule, stated once so every future milestone can point at
it instead of re-deciding it: search and evaluate existing open-source
options before building substantial new infrastructure. Do not rebuild a
commodity layer merely to own it.

This is the detailed version of the summary in `docs/ROADMAP.md`. Where
`docs/ROADMAP.md` §8 names specific candidates to evaluate at a specific
milestone (LangGraph, LiteLLM, RouteLLM, SWE-bench), those are starting
points for the template below, not pre-made decisions — the template
still has to be applied, in writing, when that milestone actually
arrives.

## When this applies

Any milestone that would otherwise require building a nontrivial new
layer — not a function, a layer. Categories likely to come up as the
roadmap progresses:

- coding-agent runtime
- model/provider gateways
- long-running workflow/state-machine engines
- evaluation infrastructure
- model routing
- observability
- policy/authority engines

## The decision template

Answer these, in writing, when the milestone that needs the capability
actually arrives — not speculatively now:

1. **What capability is actually needed?** State it narrowly. A vague
   requirement makes every option look sufficient or insufficient at
   will.
2. **Is there a mature OSS implementation?** Search current options —
   the landscape a year from now will not match whatever was discussed
   in passing today.
3. **License?** Confirm it's compatible with how this project intends
   to be used and distributed, including any future commercial path
   described in the (private) commercial strategy.
4. **Maintenance/activity?** Recent commits, responsive maintainers,
   real usage — not just stars.
5. **Security posture?** Especially for anything that touches
   credentials, sandboxing, or model I/O.
6. **Does it satisfy our differentiated requirement,** or only the
   generic 80% of the problem? Most OSS infrastructure is built for the
   common case; this project's differentiators (loopback-only local
   review, no silent cloud fallback, deterministic scoring, audit-before-
   measurement ordering) may not be the common case.
7. **Integration cost vs. build cost?** Include the ongoing cost of
   tracking upstream, not just the initial integration.
8. **What lock-in does adopting it create?** Data formats, APIs,
   deployment assumptions.
9. **What's the extension path if we outgrow it?** Can it be forked,
   wrapped, or replaced later without a rewrite of everything built on
   top of it?

## Build our own only when

- existing OSS does not satisfy an important differentiated requirement,
- extending it would cost more than owning the narrow layer, or
- trust, security, or reproducibility specifically requires an
  implementation this project controls end to end.

## Record the decision

When a build-vs-reuse call is made, write it down — an architecture
decision record next to the code it justifies, not a chat transcript.
State which of the three conditions above applied and why the
alternative(s) considered didn't.

## What this policy explicitly rules out

Do not pre-select a specific project — an agent runtime, a model
gateway, a workflow engine, a routing library, or any other named
tool — today, merely because it came up in a conversation or a prior
brainstorm. Nothing named in an earlier discussion is pre-approved or
pre-rejected. When the relevant milestone arrives, this template gets
applied fresh, against whatever the current landscape actually is.
