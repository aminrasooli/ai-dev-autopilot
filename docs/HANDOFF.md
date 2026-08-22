# Agent handoff contract

The operating model in `docs/NORTH_STAR.md` ("the human moves up the
hierarchy") needs exactly one mechanism to work: when an agent finishes
a block of work, it leaves enough durable, machine-readable state that
the *next* agent — same model or a different one — can continue without
the human relaying context between chats and terminals.

This is a convention, not a runtime. There is no daemon, no orchestrator,
no message queue. The filesystem, git, and GitHub are the shared memory.

## The three artifacts

| artifact | written by | contains |
|---|---|---|
| **charter** | the human (or an agent drafting for approval) | scope, constraints, authorized spend, explicit non-goals, human-only gates for the block |
| **report** | the finishing agent | what changed, verification evidence, git state, real-model runs with measured cost, blockers, the batched human-gate list, ONE recommended next action |
| **repository reality** | git/GitHub | branches, commits, PRs, CI status, test results — the ground truth both of the above must be checked against |

Naming: reports are `REPORT-<phase-or-topic>-<YYYY-MM-DD>.md` in the
worktree root, uncommitted by default (they are operational artifacts,
not product documentation; a report is committed only if it becomes
durable documentation). Charters live wherever the human issues them;
if an agent drafts one it goes next to the report it emerged from.

## The continuation protocol

An agent starting a block MUST, in order:

1. read the current charter (scope and authority);
2. read the most recent report(s) in the worktree root;
3. **verify repository reality directly** — `git status`, branches,
   PR/CI state via the GitHub API — and trust it over both documents
   when they disagree;
4. continue the work, batching any human-only gates it hits;
5. finish by writing its own report, ending with exactly one
   recommended next action.

Rule 3 is the load-bearing one: reports and charters go stale the moment
someone merges, reruns, or edits outside the block. Reality wins,
always. (This repository has already lived the counterexample: a PR
reported as merged three times while the API said otherwise. Verify.)

## Human-gate batching

An agent that hits a human-only gate — merge, secrets, sudo/system
changes, publication, spend beyond the charter's authorization,
consequential direction changes — records it and moves to independent
work. Gates surface once, together, in the report's HUMAN GATE BATCH
section, each with: the exact command or UI action, why it is needed,
the risk, and the estimated human time. The human should be able to
clear the whole batch in one sitting.

## Recording operator touches

To make the ≤3-touches-per-day target measurable without building
analytics: each report includes a `touches` line counting the meaningful
human interactions the block consumed (per the NORTH_STAR definition —
charters, decisions, merge/secret/privileged/publication actions;
not notifications or agent-to-agent handoffs). A dated one-line-per-day
tally derived from reports is enough; no tooling is required and no
historical numbers may be invented retroactively.

## Public/private classification, before anything reaches this repo

Before adding any strategy, planning, or data artifact to this public
repository, classify it first:

- **PUBLIC** — may enter `ai-dev-autopilot`: product direction,
  methodology, roadmap, benchmark cases and results, technical
  documentation, anything a user or contributor needs to inspect or
  trust.
- **PRIVATE-COMMERCIAL** — must never enter this repository: monetization
  triggers, incorporation timing, investor/acquisition posture, pricing,
  competitive positioning, anything that reads as a business plan rather
  than an engineering artifact. Lives in the maintainer's private
  operational repository instead.
- **PRIVATE-SECURITY/OPS** — must never enter this repository: machine
  topology, credentials, private infrastructure, backup/restore
  procedures, anything already governed by the private ops runbook this
  project's `CLAUDE.md` points at.

An agent must never move a private artifact into this public repository
because it is convenient, because a report references it, or because a
future reader "would probably want to see it." When in doubt, the
artifact stays private and the gap is named in a report rather than
resolved by publishing something.

## What this deliberately is not

Not an agent framework, message bus, scheduler, or state machine. If two
artifacts and a verification rule stop being enough, the *symptom* will
be humans relaying context again — fix that by improving the reports,
not by building an orchestrator this repository's North Star has
explicitly deferred.
