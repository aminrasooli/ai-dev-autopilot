# CURRENT-MILESTONE

The single canonical statement of where this project is. Read this
before any other report or charter — per `docs/HANDOFF.md`, repository
reality wins over any document when they disagree, and this file is
where that reality is summarized. Superseded reports (`REPORT-PHASE2-*`,
`OVERNIGHT-REPORT-*`, `DEEP-EVIDENCE-REPORT-*`) stay in the worktree as
history; this file is what a fresh session reads first.

## Current milestone: M2 Cross-model pilot (per `docs/ROADMAP.md` §2 and §4)

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

### M1 — COMPLETE

All three exit criteria (ROADMAP §4: answer key frozen; repeat runs;
reproducible from a fresh clone) are met.

**Frozen answer key (durable declaration):** the approved corpus is
frozen at **54 cases** (40 defective / 14 clean / 6 cross-file), corpus
fingerprint:

```
f31d46310988f61c4534344ad05a52a4385fd15159126a0be85aad532f045690
```

This fingerprint is computed by `bin/review-corpus --json` from
`eval/cases/` exactly as merged in PR #12; it has not changed since,
including through PR #14 below — `eval/cases/` itself was not touched.

**Repeat runs against this fingerprint, and fresh-clone reproducibility:**
both closed together by PR #14, "Add M1 fresh-clone repeat-run evidence
against the frozen 54-case corpus" (`evidence/m1-fresh-clone-repeat-run`
→ `main`), merged 2026-08-22, merge commit
`f0a824abe1fe245ce1c91ba6fdec1eddc3d48795`. Evidence: a genuinely fresh
`git clone` of `origin/main` at `485912b5`, 3 runs across all 54 cases,
corpus fingerprint in the report verified matching the frozen fingerprint
above, committed at
`eval/results/provisional/claude-sonnet-5-m1-frozen54-3runs-freshclone.json`
and registered as experiment X13 in `eval/EXPERIMENTS.md` ($2.213189,
162 calls, 0 errors). Still labeled `provisional` per `EXPERIMENTS.md`'s
own rule 1 (the row was added after the run completed), which is a
recordkeeping label, not a gap in the M1 evidence itself.

### M2 — IN PROGRESS: cross-model pilot

Scope, exactly as `docs/ROADMAP.md` §4 defines it: Sonnet vs Qwen vs
DeepSeek on the frozen 54-case corpus above, 3 repetitions, an honest
cost + latency + quality scorecard, clearly labeled a pilot — nothing
more (no leaderboard framing, no launch-grade claims; see ROADMAP §5
M5 launch gate and §6 message rules for why the pilot label matters).

Status: not started. No M2 benchmark runs have been executed against
this milestone yet. Prerequisite named in ROADMAP §2 and this file's
prior revisions: the local GPU job needs to be diagnosed and producing
output before the Qwen/DeepSeek legs can run (`LOCAL-MODEL-JOBS.md`
tracks this). The Sonnet leg reuses the same harness already proven by
X13 above.

## Canonical branch

**`main`**. PR #12 and PR #14 merged; there is no separate feature
branch to work from. Any future session or scheduler starts from a
fresh clone or worktree of `origin/main`.

## Stable base

**`origin/main`** @ `f0a824abe1fe245ce1c91ba6fdec1eddc3d48795` (PR #14
merge commit, the current tip of `origin/main` as of this file). Verify
with `git fetch origin main` before trusting this line — reality wins
if it has moved.

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

## Next human gate (M0 and M1 are complete; nothing above is blocking)

1. Real-bug A-tier candidate approval (`REAL-BUG-ADMISSION-PACKET.md`) —
   optional, not blocking M2
2. Authorization to begin M2 pilot runs (spend above the authorized
   threshold and any local-GPU diagnosis work are gated per ROADMAP §3)

## Next autonomous work

Diagnose the local GPU job so it produces output (`LOCAL-MODEL-JOBS.md`)
— this unblocks the Qwen/DeepSeek legs of the M2 pilot described above.
Also available, not blocking M2: real-bug case admission (10 A-tier
candidates ready, `REAL-BUG-ADMISSION-PACKET.md`); non-Claude case
proposals via `LOCAL-MODEL-JOBS.md`.

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
