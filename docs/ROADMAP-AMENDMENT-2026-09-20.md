# Proposed amendment — personal engineering-manager track

**Status: PROPOSED. Not adopted.** Lands as `docs/ROADMAP-AMENDMENT-2026-09-20.md`
plus the narrow edits listed in §6 below. Policy and authorization changes stay
at JP's merge gate; no owner signature is implied and no adoption procedure is
waived. One owner decision remains, stated once in §7.

Decision date 2026-09-20 (America/Los_Angeles).

---

## 1. Two tracks, deliberately separate

The **product track** is unchanged. M6 is measured on **2026-09-21** against the
existing §5 criteria, by the normal owner decision process. Its result history,
date and criteria are preserved exactly. Evidence is prepared when due; no
verdict is pre-recorded here.

- A first **MISS** triggers the one repositioning and relaunch.
- A second **MISS** parks the platform ambition; the benchmark remains a
  standalone asset.
- The bounded benchmark drumbeat continues under its existing access, licensing,
  hardware and budget conditions. Nothing here enlarges them.

The **personal track** is a **four-week experiment on `ai-dev-autopilot` only**,
running 2026-09-20 → 2026-10-18, **independent of product traction**. Its purpose
is useful verified delivery with fewer operator interventions. It does not
reorder, accelerate or gate the product milestones, and product sequencing
remains intact. Scope, resource limits, quality and authority controls continue
to apply throughout.

Personal milestones are written **M7p–M10p** to keep them textually distinct from
product M7–M10, which remain blocked behind the M6 gate.

## 2. M7p — routing by demonstrated competence

Route each task to a model by **demonstrated competence for that specific task
class**, plus availability, privacy, cost and risk.

Implementation, planning, research and review are evaluated **separately**. A
model competent at one is not thereby competent at another.

**Reviewer benchmark results do not establish general coding or planning
competence.** The existing v2/v3 corpora measure code review. Citing them as
evidence for a routing decision about implementation or planning is a category
error and is not permitted.

Promotion of any additional model requires task-specific evidence. Until such
evidence exists, the currently verified roles stand: **Sonnet implements, Fable
reviews.**

## 3. M8p — machine-readable handoffs

Planner, builder and reviewer are separate roles exchanging **machine-readable
task and result handoffs**, with **zero manual prompt transfer**. Carrying any
prompt or result between agents by hand is a manual transfer and is recorded as
such in the ledger.

This **reuses the current engine**. The deliverable is *project configuration*,
not a cloned controller. Creating a second controller or scheduler is out of
scope, as it has been throughout.

## 4. M9p — durability

Durable state, bounded retries, quota handling, recovery, scoped permissions and
batched exceptions.

**Minimum authority enforcement precedes the first automatic action.** M9p
develops the broader capability, but the minimum set is a precondition, not a
deliverable to be completed later. As of 2026-09-20 that minimum is **not met**
(see the private control inventory), which is why automatic merging is disabled
by default.

## 5. M10p — goal to delivery

A goal plus acceptance criteria become a finite backlog, independently reviewed
changes, verified delivery within authorization, and a concise report.

**A milestone is not complete merely because a maintenance PR merged or a design
document exists.** Completion requires milestone-specific evidence.

Operating rhythm: plan per goal, reconsider on relevant events, execute between
those decisions. A scheduler may dispatch work and report progress **without
repeatedly redesigning the architecture**.

## 6. Supersession note — exactly which present-tense rules change

These are the only present-tense rules altered. Each is narrowed, none deleted,
and every historical decision is preserved.

| Document | Present-tense rule today | Change |
|---|---|---|
| `docs/ROADMAP.md` §3 (human gates) | "merge to main … NEVER automate" | Narrowed by the 2026-09-20 limited authorization: routine maintenance merges within `docs/AUTOMERGE_POLICY.md` scope may be performed by the trusted controller. Every other merge stays human-only. The prohibition is **rewritten in place**, not left standing next to an appended permission. |
| `CURRENT-MILESTONE.md` "What is forbidden right now" | "External publication … permanently a human gate" | Unchanged. Publication remains human-only; only *merge* is narrowed. Stated explicitly so the two are not conflated. |
| `CURRENT-MILESTONE.md` "Next human gate" | implies merge is the gate | Adds that routine maintenance merges inside the policy scope are no longer a human gate, while M6 measurement and every protected path still are. |
| `docs/NORTH_STAR.md` | "Human Operator Touches" model | Adds that the personal track measures operator touches against the ledger's definition; no change to the model itself. |
| `docs/HANDOFF.md` | report/worktree conventions | Adds that the automation worktree routes operational artifacts to `.claude-travel/DRAFTS/`, which the root-report convention does not cover. |

**Not changed, explicitly:** M6 criteria, date and result history; the M3
supersession record and its disclosed waiver; §11 private-holdout references,
which are **not** reinterpreted here; frozen corpora and answer keys; recorded
benchmark results; spending, privileged-operation and publication gates.

## 7. The one remaining owner decision

Adopt this amendment as written, or amend it. It is proposed until JP merges it.
No other decision is requested by this document.
