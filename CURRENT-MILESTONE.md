# CURRENT-MILESTONE

The single canonical statement of where this project is. Read this
before any other report or charter — per `docs/HANDOFF.md`, repository
reality wins over any document when they disagree, and this file is
where that reality is summarized. Superseded reports (`REPORT-PHASE2-*`,
`OVERNIGHT-REPORT-*`, `DEEP-EVIDENCE-REPORT-*`) stay in the worktree as
history; this file is what a fresh session reads first.

## Current milestone: M1 Benchmark v2 frozen (per `docs/ROADMAP.md` §2 and §4)

`docs/ROADMAP.md` is the canonical public governing strategy and owns
milestone numbering; this section summarizes status against it and must
not invent a competing numbering scheme.

### M0 — COMPLETE

All four exit criteria (ROADMAP §4) are met:

- Ground truth reviewed by JP's own eyes (D1–D5, detailed below).
- PR #12 merged by JP: `98791f105d88cd92d0ac05f0162bc769f370e8c9`.
- B0 encrypted backup completed (encrypted, off-machine, restore-tested
  Restic backup; independently restore-verified from a second machine).
- Nightly scheduler re-enabled and active.

Human ground-truth decisions D1–D5 were answered 2026-08-21: D1=keep
(case 30, version-pinned), **D2=delete** (cases 25 and 57 — two clean
controls that kept drawing legitimate objections even after rewriting),
**D3=delete** (case 10 — its label depended on unstated authorial intent
no accepted-category alternative could resolve), D4=endorse all 12
accepted-category alternatives, D5=run baselines now, **explicitly as
v2-pilot evidence, not launch-grade leaderboard results**. Full detail:
`CONVERGENCE-REPORT-2026-08-21.md` §13 (worktree-local; not part of this
repository).

### M1 — IN PROGRESS: answer key frozen; repeat runs and reproducibility outstanding

**Frozen answer key (durable declaration):** as of this file, the
approved corpus is frozen at **54 cases** (40 defective / 14 clean / 6
cross-file), corpus fingerprint:

```
f31d46310988f61c4534344ad05a52a4385fd15159126a0be85aad532f045690
```

This fingerprint is computed by `bin/review-corpus --json` from
`eval/cases/` exactly as merged in PR #12; it has not changed since.
`eval/cases/` itself is not touched by this update.

M1 remaining gates (not yet satisfied by committed evidence):

- **Repeat runs against this fingerprint.** The existing committed
  reports in `eval/results/provisional/` (3-run, 5-run, 7-run, 10-run)
  all predate the ground-truth gate and carry a different fingerprint
  (57-case corpus, or smaller subsets) — they do **not** satisfy this
  gate.
- **Fresh-clone reproducibility evidence.** No committed artifact yet
  demonstrates a repeat run from a genuinely fresh clone against the
  frozen fingerprint above.

Single next M1 action for the autonomous worker: from a genuinely fresh
clone of `origin/main`, run the smallest roadmap-compliant repeat
evaluation (`bin/review-eval --runs 3` or `5`) against the frozen
54-case corpus above, and commit the resulting report under
`eval/results/` — this closes both remaining gates at once.

## Canonical branch

**`main`**. PR #12 merged; there is no separate feature branch to work
from. Any future session or scheduler starts from a fresh clone or
worktree of `origin/main`.

## Stable base

**`origin/main`** @ `98791f105d88cd92d0ac05f0162bc769f370e8c9` (PR #12
merge commit). Verify with `git fetch origin main` before trusting this
line — reality wins if it has moved.

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

## Next human gate (M0 is complete; nothing above is blocking)

1. Real-bug A-tier candidate approval (`REAL-BUG-ADMISSION-PACKET.md`) —
   optional, not blocking M1
2. Review/merge of the M1 repeat-run + fresh-clone-reproducibility
   result, once the autonomous worker (or a future session) produces it

## Next autonomous work after M1

M2 (ROADMAP §4): cross-model pilot — Sonnet vs Qwen vs DeepSeek on the
frozen corpus, 3 repetitions, honest cost/latency/quality scorecard,
clearly labeled a pilot — once the local GPU job is diagnosed and
produces output, and only after M1's repeat-run and reproducibility
gates above are actually closed. Also: real-bug case admission (10
A-tier candidates ready, `REAL-BUG-ADMISSION-PACKET.md`); non-Claude
case proposals via `LOCAL-MODEL-JOBS.md`.

## Instructions for a future session with zero chat history

1. Read this file.
2. Read `docs/ROADMAP.md` — the public governing strategy, owner of
   milestone numbering and gates — then `docs/NORTH_STAR.md` and
   `docs/HANDOFF.md`.
3. `git fetch origin`; verify this file's claims about branch/PR state
   are still true — if not, trust git/GitHub over this file and update
   it.
4. Check for open PRs relevant to the current milestone
   (`gh pr list --repo aminrasooli/ai-dev-autopilot --state open`).
5. Do not start work on any branch other than the canonical one above
   unless this file has been updated to name a new one.
6. Do not treat an old scheduler-produced branch as current direction
   merely because it exists — check whether it predates this file.
7. Before adding any strategy/planning artifact to this repo, classify
   it PUBLIC / PRIVATE-COMMERCIAL / PRIVATE-SECURITY-OPS per
   `docs/HANDOFF.md` — the public roadmap is `docs/ROADMAP.md`; nothing
   about monetization, incorporation, or commercial timing belongs here.
