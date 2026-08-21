# Roadmap

**Public.** This document is the credible, honest path from what exists
today toward the destination recorded in `docs/NORTH_STAR.md`. It is not
a schedule and it is not a pitch — dates are never promised, and
platform work after external traction validates the idea is explicitly
conditional on that traction actually showing up.

Each milestone states an objective, its current status, what would count
as done, what is deliberately *not* built at that stage, and how much of
it is safe to talk about publicly. If a milestone's status says
"not started," nothing below it should be read as available today.

## M0 — Repository / operational readiness

**Objective:** one coherent history, one active branch, durable handoff
between sessions and agents.
**Status:** in progress (`CURRENT-MILESTONE.md` tracks it live).
**Exit criterion:** no stranded branches, no duplicate work streams, a
canonical handoff document a fresh session can act on with zero prior
context.
**Not built:** any of M1+.
**Communication:** internal only.

## M1 — Reviewer Benchmark v2

**Objective:** a versioned, schema-validated corpus with human-approved
ground truth; repeat-run evaluation; report integrity verification.
**Status:** ground-truth gate resolved 2026-08-21 (54 cases). PR open,
not yet merged.
**Exit criterion:** PR merged to `main`.
**Not built:** any real cross-model comparison beyond single-backend
pilot evidence; a public leaderboard.
**Communication:** Stage A (build in public) once merged — see below.

## M2 — Cross-model v2 pilot evidence

**Objective:** the same 54-case corpus run against multiple backends
(Claude, at least one local model through Ollama) at repeat-run depth,
with variance and classification analysis.
**Status:** not started (blocked on a working local-model run; the first
attempt produced no usable output and needs diagnosis).
**Exit criterion:** at least two backends with `--runs >= 3` reports,
compared honestly, saturation/discrimination findings documented.
**Not built:** any claim that this ranks models in general; a corpus
that could support such a claim.
**Communication:** Stage A/B.

## M3 — Harder, realistic Benchmark v3

**Objective:** fix the structural cause of detection saturation found in
M2 — bigger diffs, more context, cases that require actual reasoning
rather than four-line changes.
**Status:** not started. Diagnostic tooling exists (`reviewer/diagnose.py`);
`HARD-CASE-QUEUE.md` records where the current corpus is thin.
**Exit criterion:** a corpus where recall is no longer saturated across
difficulty tiers for a frontier model.
**Not built:** provenance diversification (M4).
**Communication:** Stage B.

## M4 — Provenance diversification, real historical bugs, private holdout

**Objective:** reduce self-authorship bias. Mined real bugs (candidates
researched and queued, `REAL-BUG-ADMISSION-PACKET.md`, none admitted
yet), non-Claude-authored cases, and a private holdout corpus that never
enters this repository.
**Status:** design complete, nothing admitted or created.
**Exit criterion:** at least one case from each of: mined-real-fix,
non-Claude authorship, and a private holdout that exists and is
runnable.
**Not built:** public disclosure of holdout contents, ever.
**Communication:** Stage B/C — the holdout's *existence* and
*methodology* can be discussed; its contents never can.

## M5 — Public benchmark launch

**Objective:** the benchmark stands as a credible, reproducible public
artifact.
**Status:** not started. Gated on M3 and M4.
**Exit criterion:** harder v3 corpus, provenance diversification,
holdout architecture live, clean contribution path, multi-model evidence
that isn't single-backend pilot data.
**Not built:** any commercial product.
**Communication:** Stage C.

## M6 — External reproduction / traction gate

**Objective:** find out whether anyone besides the maintainer finds this
useful enough to act on.
**Status:** not started.
**Exit criterion (precommitted, `eval/EXPERIMENTS.md` intent):** roughly
100+ real-account GitHub stars, 2+ substantive outside issues/PRs, and
— the signal that actually matters — **at least one independent
reproduction**: someone outside this project runs the harness against a
model we didn't, and submits a result we can verify.
**Explicitly:** stars are not the success criterion. A single independent
reproduction is worth more than all of them combined, because it is the
only signal that costs an outsider real effort.
**Not built:** anything past M6 is conditional on this milestone
actually being met, not on elapsed time or effort invested.
**Communication:** Stage C, transitioning toward D only with real
evidence.

## M7 — Evidence-based model selection

**Objective:** use accumulated benchmark evidence to inform which
reviewer/model to use for a given task — a recommendation a human still
approves, not an automatic decision.
**Status:** not started. Explicitly gated on M6.
**Not built:** automated routing (see M8).

## M8 — Planner / Builder / Reviewer role specialization

**Objective:** distinct roles with distinct authority, each potentially
backed by a different runtime/model, without collapsing back into one
generic agent doing everything.
**Status:** not started. This is the first step that starts to resemble
the deferred "AI Team Runtime" architecture explicitly ruled out for the
current phase — it does not become in-scope merely because earlier
milestones shipped.

## M9 — Continuity, authority, risk

**Objective:** work surviving provider/session limits, and a
deterministic policy for which actions a role may take without human
sign-off, replacing today's fixed hard-boundary list.
**Status:** not started.

## M10 — AI Engineering Manager (North Star)

**Objective:** the full vendor-neutral control plane described in
`docs/NORTH_STAR.md` — task-aware model/runtime selection, cost/privacy/
risk-aware routing, quality thresholds, outcome-based competence
tracking.
**Status:** not started. This is the destination the whole roadmap
points at, not a near-term deliverable.

---

## Communication stages

Which milestones license which kind of public statement — kept separate
from the milestones themselves because a milestone can complete without
anyone having decided to talk about it yet.

### Stage A — Build in public (M1–M3)

**Allowed:** technical progress notes, lessons learned, transparent
pilot findings, methodology discussion.
**Not allowed:** claiming a best model, a universal ranking, a
production AI Engineering Manager, or that autonomous engineering is
"solved."

### Stage B — Technical pilot distribution (M2–M4)

**Allowed:** a technical write-up, an r/LocalLLaMA pilot discussion,
inviting independent reproduction and benchmark contributions. Every
result is labeled **pilot evidence**, never a conclusion.

### Stage C — Benchmark launch (M5)

Only after M3 and M4 are actually done: harder corpus, provenance
diversification, holdout live, clean contribution path, credible
multi-model evidence. Candidate channels: a write-up, r/LocalLLaMA, other
relevant developer communities. A Show HN–style launch should only
happen when the maintainer can be present to answer questions for most
of that day — this document does not encode *when* that is, only that
presence is the precondition.

### Stage D — Commercial product story (M6+)

Only after M6's external-usage evidence exists. Nothing about commercial
strategy belongs in this file or this repository — see the
public/private boundary section below.

---

## Open-source-before-build

Before implementing substantial new infrastructure (coding-agent
runtime, model/provider gateways, workflow engines, evaluation
infrastructure, routing, observability, policy engines), search and
evaluate existing OSS first — do not rebuild a commodity layer merely to
own it, and do not pre-select a specific project today merely because it
came up in conversation. Full policy and decision template:
[`docs/OPEN_SOURCE_POLICY.md`](OPEN_SOURCE_POLICY.md).

---

## Open-core boundary (default, subject to change)

A high-level expectation, not a promise about any specific future
release.

**Expected to stay open/core:**
reviewer interfaces and adapters · the benchmark harness · public
benchmark cases · methodology · the public evaluation/result schema ·
reproducibility tooling · contribution and result-submission paths · the
basic handoff protocol · safety contracts a user needs to be able to
inspect and trust · interoperability surfaces.

**Candidates for private/commercial, if and when a product forms:**
private holdout contents · customer-specific evaluation sets ·
production competence history · learned routing policies ·
organization-specific memory · customer telemetry · proprietary
evaluation intelligence · hosted fleet/control-plane operations ·
enterprise administration · SSO/RBAC integration · organization-specific
governance rules · SLA/support tooling.

This is a default boundary, not a commitment that every item on the
second list will end up proprietary, and not a claim that anything on
the first list is somehow at risk. It exists so that implementation
detail likely to matter for a future differentiated product isn't
casually given away before there's evidence a product is warranted —
without withholding anything that would compromise reproducibility,
safety review, or the whole point of building this in public today.
