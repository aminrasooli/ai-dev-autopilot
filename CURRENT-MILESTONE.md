# CURRENT-MILESTONE

The single canonical statement of where this project is. Read this
before any other report or charter — per `docs/HANDOFF.md`, repository
reality wins over any document when they disagree, and this file is
where that reality is summarized. Superseded reports (`REPORT-PHASE2-*`,
`OVERNIGHT-REPORT-*`, `DEEP-EVIDENCE-REPORT-*`) stay in the worktree as
history; this file is what a fresh session reads first.

## Current milestone: M3 Hard benchmark v3 (per `docs/ROADMAP.md` §2 and §4)

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
including through PR #14 and PR #16 below — `eval/cases/` itself was
never touched by either.

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

### M2 — COMPLETE: cross-model pilot

Scope, exactly as `docs/ROADMAP.md` §4 defines it (Sonnet vs Qwen vs
DeepSeek on the frozen 54-case corpus, 3 repetitions, an honest cost +
latency + quality scorecard, clearly labeled a pilot), closed by PR #16,
"Preregister M2 cross-model pilot" (`m2/preregister-cross-model-pilot`
→ `main`), merged 2026-08-23, merge commit
`85a265706f478a7b0d3c5e40e7b17c293dd66b4e`.

**Anti-cherry-picking chronology, verifiable in git history:** X14/X15/X16
were registered as `authoritative` in `eval/EXPERIMENTS.md` at commit
`b75049f5bbc1475b2bfc0463b681951664ec5905` (2026-08-22 14:26:30 PDT,
pushed and opened as PR #16 at 14:26:32 PDT) — before the benchmark batch
began on the host at approximately 14:32 PDT. Results were added in a
second commit (`c679d9891...`) on the same PR after all three runs
completed and were verified; PR #16 was merged as one unit. No result
was seen before its row was registered.

**Evidence, all three against the frozen fingerprint above, 3 runs ×
54 cases = 162 calls each, verified internally consistent by
`python3 -m reviewer.verify`:** full scorecard at
`eval/results/M2-PILOT-SCORECARD.md`, raw reports at
`eval/results/claude-sonnet-5-m2pilot-3runs.json`,
`eval/results/qwen3.6-27b-m2pilot-3runs.json`,
`eval/results/deepseek-r1-14b-m2pilot-3runs.json`.

| model | defect recall | clean FP rate | category correct | severity correct | errors | cost |
|---|---|---|---|---|---|---|
| claude-sonnet-5 | 1.00 [0.97–1.00] | 0.21 | 0.85 | 0.82 | 1/162 | $1.435265 |
| qwen3.6:27b | 0.99 [0.95–1.00] | 0.26 | 0.76 | 0.65 | 4/162 | no external model API charge |
| deepseek-r1:14b | 0.82 [0.73–0.88] | 0.10 | 0.34 | 0.26 | 6/162 | no external model API charge |

Read together, not ranked (no composite score exists in this harness):
Qwen's defect recall (0.99) is close behind Sonnet's (1.00), with no
external model API charge — but Sonnet is materially stronger on
category/severity classification, and Qwen has a somewhat higher
clean-case false-positive rate. DeepSeek is materially weaker on
classification in this benchmark. This is **pilot** evidence — one
self-authored 54-case corpus, one run set, three repetitions — not a
statement about these models' general coding ability, and not the
public leaderboard (`eval/LEADERBOARD.md` stays inactive until its own
preconditions are met: corpus `stable` status, ≥2 models at runs≥3,
outside submission).

### M3 — CURRENT: hard benchmark v3

Scope, exactly as `docs/ROADMAP.md` §4 defines it: larger realistic
diffs, true cross-file reasoning, state/cache failures, authorization
failures, concurrency failures, hard clean controls; detection no
longer saturated. Status: **design/gap-analysis phase only** — no v3
cases authored, no infrastructure built, the frozen v2 corpus above is
untouched. M3 must land as a new benchmark version/boundary, never as a
mutation of the frozen 54-case v2 corpus.

Gap analysis (grounded in the M2 evidence above and a direct inventory
of `eval/cases/`) and a proposed hard-case taxonomy live at
`docs/M3_DESIGN_BRIEF.md`. Headline finding: recall is already
saturated for the two strongest models — Sonnet is a flat 1.00 across
every difficulty tier and file-span in M2, Qwen 0.94–1.00 — while
classification correctness (category/severity) is not, and neither is
recall for the weakest model (DeepSeek 0.68–0.85 by tier). The existing
6 cross-file cases score 1.00 recall even for DeepSeek, meaning they
test file-pair consistency-checking rather than the "true cross-file
reasoning" ROADMAP asks for. `state/cache failures` has essentially one
thin case today (`02-subtle-cache-key`). None of the 54 diffs exceed 35
lines — "larger realistic diffs" is a fully open gap. Full detail,
including which decisions are methodology calls versus implementation
work, in the design brief.

## Canonical branch

**`main`**. PR #12, #14 and #16 merged; there is no separate feature
branch to work from. Any future session or scheduler starts from a
fresh clone or worktree of `origin/main`.

## Stable base

**`origin/main`** @ `85a265706f478a7b0d3c5e40e7b17c293dd66b4e` (PR #16
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
integrity verification, an N-way comparator, real evidence across M1 and
M2 (see above), and the Human Operator Touches operating model
(`docs/NORTH_STAR.md`).

## What is forbidden right now

- Generic model routing or automatic model selection
- Strategist/builder/supervisor orchestration, an "AI Team Runtime"
- A control plane, dashboard, or SaaS layer
- An authority/risk/competence-ledger engine
- Any of the above resurrected under a different name because old code
  or an old prompt already built toward it
- M3 scope creep: authorship diversification (non-Claude-authored
  cases) is M4's job, not M3's — do not pull it forward
- Execution-based oracles / sandboxed test running for M3 unless a
  human has explicitly decided that fork (see `docs/M3_DESIGN_BRIEF.md`
  — the diff-only-vs-execution question is unresolved by design)

These remain North Star destinations, not current backlog. Do not build
them because a stale branch or scheduler run once pointed that way.

## Next human gate (M0, M1 and M2 are complete; nothing above is blocking)

1. Real-bug A-tier candidate approval (`REAL-BUG-ADMISSION-PACKET.md`) —
   optional, not blocking M3
2. Review the M2 pilot evidence and communication drafts prepared
   alongside this update — none are published; publication is a human
   gate per ROADMAP §3
3. Decide the one open M3 methodology fork named in
   `docs/M3_DESIGN_BRIEF.md` (diff-only vs. execution-based oracle for
   state/cache and concurrency cases) — recommended as a short Fable
   milestone-decision session per ROADMAP §3, before any M3 case
   authoring starts

## Next autonomous work

M3 only, once the methodology fork in gate 3 above is resolved: author
the hard-case taxonomy proposed in `docs/M3_DESIGN_BRIEF.md` as a new
`benchmark_version: 3` corpus (or a clearly-versioned extension
directory), starting from the taxonomy's highest-confidence items
(larger realistic diffs; deeper cross-file, authorization and
concurrency cases; a labeled hard-clean-control tier building on the
5 v2 clean cases that already show real false-positive confusion).
Nothing outside M3 scope (no routing, no agent teams, no M4+ work).

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
