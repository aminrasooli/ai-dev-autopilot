# Personal engineering-manager trial — ledger

Maintained automatically from the controller digest. Delivered by the
self-repair PR alongside `automation/REPAIR-CHARTER.md`.

**Decision start:** 2026-09-20 (America/Los_Angeles)
**First-week checkpoint:** 2026-09-27 · **Trial end:** 2026-10-18
**Actual execution start (first setup command of this kickoff):** 2026-09-20T16:55 PT

The clock starts at the decision date and is **not** restarted by setup,
failure, repair or a later installation. Setup cost stays in the trial total
even when it precedes any reliability interval.

## Rules this ledger is kept under

- Unknown operator minutes or usage are **UNKNOWN**, never 0 and never estimated
  into a number. Dollar spend is **never** inferred from subscription percentages.
- Events are collected automatically through the existing controller digest;
  JP maintains no spreadsheet. Owner estimates are labelled as estimates.
- Documentation and ledger changes are **required deliverables** but are **not
  autonomous deliveries**, and are never produced to manufacture daily activity.
- A **useful delivery** requires the full path with no manual prompt transfer:
  queue → implementation → independent review of the exact commit → required
  checks → permitted merge → post-merge verification → digest.
- A **human merge is not an autonomous delivery.** The controller now records
  `merged_by` and labels each as `autonomous` or `human-merge`.
- The initial goal brief is an operator touch. Carrying any prompt or result
  between agents by hand is a manual transfer.
- Raw host logs and detailed security inventories stay private; only aggregates here.
- **An automatic repair is still a controller repair.** It resets the
  reliability interval exactly as a manual one would. It counts as zero
  operator minutes and zero prompt transfers **only** when no human touched
  it — a human who merges the repair PR is an operator touch for that day.
- Each day records repair-session **runtime, cause and outcome**, from
  `state/repair-attempts.json` and the digest. A repair that was attempted
  and failed is recorded as a failed recovery, not omitted.

| date | operator touches | operator minutes (source) | manual prompt transfers | useful accepted deliveries (evidence) | regressions | failed recoveries | blocked work | measured usage (source/model) |
|---|---|---|---|---|---|---|---|---|
| 2026-09-20 | 3 (kickoff brief; continuation brief; self-repair brief) | UNKNOWN (not instrumented) | 3 (all three briefs — the last such relay: goal intake is now GitHub issues) | **0 autonomous.** PR #52 merged, but **by aminrasooli — human merge, not an autonomous delivery** | 0 | 3 tasks wrongly retired by a misclassified capacity pause (now refunded) | auto-merge enablement blocked: separation not OS-enforced, controller authenticates as the owner | UNKNOWN (no per-project meter). Two Claude session-limit pauses observed ~07:00 and ~07:30 PT |

### Notes for 2026-09-20

- `doctor-bootstrap-pending` did produce PR #52 and it landed — but a human
  merged it, so it is recorded as a human merge and counted as **zero**
  autonomous deliveries.
- `quickstart-audit`, `review-pr50` and `doctor-bootstrap-pending` were each
  marked `blocked` after two attempts. Root cause: the worker hit a Claude
  **session limit**, which the controller's quota matcher did not recognise, so
  a capacity pause was misclassified as a task defect. Fixed; attempts refunded.
- `review-pr50` is superseded: PR #50 is already merged, so reviewing it is no
  longer useful. The entry is kept with a supersession note.

### Repair sessions

| date | signature | cause | runtime | outcome |
|---|---|---|---|---|
| 2026-09-20 | — | none triggered: the self-repair loop is not installed yet | — | — |

## Reliability interval

Requires **7 consecutive days** of useful operation with **zero** manual prompt
transport and **zero** controller repair, inside the four-week trial. **Not
started** — today involved controller repair. Workload and idle days are
reported so empty cycles cannot establish reliability. Extensions are not automatic.

## Baseline

No measured pre-trial operator-time baseline exists. An absent baseline
**cannot establish improvement**; any later claim of reduced operator time must
name the measured baseline it is compared against.
