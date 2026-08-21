# CURRENT-MILESTONE

The single canonical statement of where this project is. Read this
before any other report or charter — per `docs/HANDOFF.md`, repository
reality wins over any document when they disagree, and this file is
where that reality is summarized. Superseded reports (`REPORT-PHASE2-*`,
`OVERNIGHT-REPORT-*`, `DEEP-EVIDENCE-REPORT-*`) stay in the worktree as
history; this file is what a fresh session reads first.

## Current milestone: M0 / M1

Repository convergence (M0) and the Phase 2 ground-truth gate (M1).

## Canonical active branch

**`feature/reviewer-benchmark-v1`**, until PR #12 lands. Any future
session or scheduler must start here, not on any other branch — see
"forbidden" list below for why old branches are not candidates.

## Stable base

**`origin/main`** @ `f4ead71`. Confirmed to be the exact merge-base of
`feature/reviewer-benchmark-v1` and `origin/main` — the feature branch is
current with main; main has not advanced independently.

## What Phase 1 is

The reviewer foundation: a pluggable `ReviewerBackend` (Codex default,
Ollama local with the thinking-mode fix, Claude Code backend), cost/token
accounting, a deterministic fake/oracle backend, and the original 20-case
evaluation harness. **Confirmed present and unmodified in spirit** on the
current branch — verified by direct file inspection, not assumed.

## What Phase 2 is

The benchmark/evidence layer that **enhances** Phase 1, never replaces
it: schema v2, repeat runs with checkpoint/resume, a blind ground-truth
audit (committed before any model comparison), difficulty and
context-budget diagnostics, category/severity confusion analysis, report
integrity verification, an N-way comparator, real provisional evidence
($5.70 across three pre-registered Claude Sonnet 5 runs), and the
Human Operator Touches operating model (`docs/NORTH_STAR.md`).

## What is forbidden right now

- Generic model routing or automatic model selection
- Strategist/builder/supervisor orchestration, an "AI Team Runtime"
- A control plane, dashboard, or SaaS layer
- An authority/risk/competence-ledger engine
- Any of the above resurrected under a different name because old code
  or an old prompt already built toward it

These remain North Star destinations, not current backlog. Do not build
them because a stale branch or scheduler run once pointed that way.

## Next human gate

Three items, batched (detail: `CONVERGENCE-REPORT-2026-08-21.md` §13):

1. **Ground truth D1–D5** — `HUMAN-GROUND-TRUTH-REVIEW.md`
2. **PR #12 merge authorization** — after (1)
3. **B0 backup/passphrase work** — ops track, `~/ops/BACKUPS.md`, untouched by this product work

## Next autonomous work after M1

M2: real cross-model evidence (Qwen, DeepSeek) once the local GPU job
is diagnosed and produces output; real-bug case admission (10 A-tier
candidates ready, `REAL-BUG-ADMISSION-PACKET.md`); non-Claude case
proposals via `LOCAL-MODEL-JOBS.md`.

## Instructions for a future session with zero chat history

1. Read this file.
2. Read `docs/NORTH_STAR.md` and `docs/HANDOFF.md`.
3. `git fetch origin`; verify this file's claims about branch/PR state
   are still true — if not, trust git/GitHub over this file and update
   it.
4. Check `gh pr view 12` for current status.
5. Do not start work on any branch other than the canonical one above
   unless this file has been updated to name a new one.
6. Do not treat an old scheduler-produced branch as current direction
   merely because it exists — check whether it predates this file.
