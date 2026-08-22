# CURRENT-MILESTONE

The single canonical statement of where this project is. Read this
before any other report or charter — per `docs/HANDOFF.md`, repository
reality wins over any document when they disagree, and this file is
where that reality is summarized. Superseded reports (`REPORT-PHASE2-*`,
`OVERNIGHT-REPORT-*`, `DEEP-EVIDENCE-REPORT-*`) stay in the worktree as
history; this file is what a fresh session reads first.

## Current milestone: M0 pre-flight (per `docs/ROADMAP.md` §2 and §4)

`docs/ROADMAP.md` is the canonical public governing strategy and owns
milestone numbering; this section summarizes status against it and must
not invent a competing numbering scheme.

M0's exit criteria (ROADMAP §4): ground truth reviewed by JP, PR #12
merged by JP, B0 encrypted backup completed, nightly scheduler
re-enabled. Status: **ground-truth review is done**, the other three are
not — M0 is not complete.

Human ground-truth decisions D1–D5 were answered 2026-08-21: D1=keep
(case 30, version-pinned), **D2=delete** (cases 25 and 57 — two clean
controls that kept drawing legitimate objections even after rewriting),
**D3=delete** (case 10 — its label depended on unstated authorial intent
no accepted-category alternative could resolve), D4=endorse all 12
accepted-category alternatives, D5=run baselines now, **explicitly as
v2-pilot evidence, not launch-grade leaderboard results**. Corpus is now
**54 cases (40 defective / 14 clean / 6 cross-file)**, fingerprint
recomputed post-deletion. Full detail: `CONVERGENCE-REPORT-2026-08-21.md`
§13.

M1 (benchmark v2 frozen — answer key frozen, repeat runs, reproducible
from a fresh clone) is, per ROADMAP §2, nearly complete in parallel with
M0; it is not the same thing as the ground-truth gate above.

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

## Next human gate (completes M0, per ROADMAP §4)

1. **PR #12 merge authorization** — ground-truth changes are committed
   (`034746f`), tested, and the PR description reflects the resolved
   54-case corpus; ready whenever the human decides to merge
2. **B0 backup/passphrase work** — ops track, `~/ops/BACKUPS.md`,
   untouched by this product work
3. **Nightly scheduler re-enable** — required for the low-touch
   operating model (ROADMAP §5 M0 calendar gate); blocked on 1 and 2
4. Real-bug A-tier candidate approval (`REAL-BUG-ADMISSION-PACKET.md`) —
   optional, not blocking M0

## Next autonomous work after M0/M1

M2 (ROADMAP §4): cross-model pilot — Sonnet vs Qwen vs DeepSeek on the
frozen corpus, 3 repetitions, honest cost/latency/quality scorecard,
clearly labeled a pilot — once the local GPU job is diagnosed and
produces output. Also: real-bug case admission (10 A-tier candidates
ready, `REAL-BUG-ADMISSION-PACKET.md`); non-Claude case proposals via
`LOCAL-MODEL-JOBS.md`.

## Instructions for a future session with zero chat history

1. Read this file.
2. Read `docs/ROADMAP.md` — the public governing strategy, owner of
   milestone numbering and gates — then `docs/NORTH_STAR.md` and
   `docs/HANDOFF.md`.
3. `git fetch origin`; verify this file's claims about branch/PR state
   are still true — if not, trust git/GitHub over this file and update
   it.
4. Check `gh pr view 12` for current status.
5. Do not start work on any branch other than the canonical one above
   unless this file has been updated to name a new one.
6. Do not treat an old scheduler-produced branch as current direction
   merely because it exists — check whether it predates this file.
7. Before adding any strategy/planning artifact to this repo, classify
   it PUBLIC / PRIVATE-COMMERCIAL / PRIVATE-SECURITY-OPS per
   `docs/HANDOFF.md` — the public roadmap is `docs/ROADMAP.md`; nothing
   about monetization, incorporation, or commercial timing belongs here.
