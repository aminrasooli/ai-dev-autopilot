# CURRENT-MILESTONE

The single canonical statement of where this project is. Read this
before any other report or charter — per `docs/HANDOFF.md`, repository
reality wins over any document when they disagree, and this file is
where that reality is summarized. Superseded reports (`REPORT-PHASE2-*`,
`OVERNIGHT-REPORT-*`, `DEEP-EVIDENCE-REPORT-*`) stay in the worktree as
history; this file is what a fresh session reads first.

## Current milestone: M6 Traction gate (per `docs/ROADMAP.md` §2 and §4)

**M5 is COMPLETE.** Engineering landed on main 2026-08-29 (PRs #41–#47):
stable corpus declared, reproduction path verified by execution,
generated scorecard guarded against drift, submission path dry-run end
to end, licence decisions recorded, v3 errata admitted, leaderboard page
fixed in advance. **The launch itself — the permanently human-gated
external publication — was performed by JP on 2026-08-31: a LinkedIn
launch post** (recorded here on JP's own statement; external platforms
are not verifiable from this repository). That closes M5's last item.

**M6 is the current milestone: the traction gate, measured once, at its
scheduled time — 2026-09-21, exactly three weeks after the 2026-08-31
launch, per ROADMAP §5.** The gate's criteria are the ones already
written in `docs/ROADMAP.md` §5 and are not restated here so that this
file can never drift from them: what counts is defined there,
unchanged. Between now and 2026-09-21 the only traction-related work is
passive evidence collection (stars, forks, issues, PRs, outside
submissions as they arrive); per ROADMAP §9 failure mode 7, day-to-day
audience numbers are noise and the gate is measured once. **M7 does not
begin — not design, not implementation — until the M6 gate is measured
and passes.** Nothing below this line has been rewritten for M6; the
M4/M5 record that follows is history, kept accurate as of its closure.

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

### M3 — COMPLETE: hard benchmark v3

Scope, exactly as `docs/ROADMAP.md` §4 defines it: larger realistic
diffs, true cross-file reasoning, state/cache failures, authorization
failures, concurrency failures, hard clean controls; detection no
longer saturated. Status: **CLOSED.** Evidence merged by PR #20
(`ba5da0bd1a8d454a5cfdb2e93d9c816c18a81310`); the gate's literal
"detection no longer saturated" wording was not satisfied for the two
leading models (see the scorecard below) and was revised by PR #21
(`aca26bdb57fec22a0d81722001d45a3052d5c695`), a disclosed same-day
procedural waiver recorded in `docs/ROADMAP.md` §4's note under the
milestone table — not re-argued here. The methodology fork was
resolved in `docs/M3_METHODOLOGY_DECISION.md`; the corpus landed as
a separate versioned directory (PR #18 tranche 1, PR #19 tranche 2 —
merge commit `79f4032cc11eddf6d13d2424a6720e1031b2ce95`), never
touching the frozen v2 corpus above.

**Frozen v3 corpus (durable declaration):** `eval/cases-v3/cases/`,
37 cases (29 defective / 8 clean), fingerprint

```
81daa0b7a48259184a91c48ab1dcf17c9d3ed4902fa891b5895db0f29fd79790
```

computed by `bin/review-corpus --cases eval/cases-v3/cases --json`,
frozen 2026-08-23 as merged in PR #19 — authored and hardened without
observing any target-model (Sonnet 5 / Qwen 3.6 27B / DeepSeek R1 14b)
result against v3, and immutable after freeze per the freeze record in
`eval/cases-v3/README.md`. Experiments X17 (Sonnet), X18 (Qwen) and
X19 (DeepSeek) — 3 runs × 37 cases each against this exact fingerprint
— were preregistered as authoritative (commit `4a53b394`, pushed
2026-08-24T02:55:35Z), executed 2026-08-23 20:24–21:19 PDT, and
recorded afterward in `eval/EXPERIMENTS.md`, with the measurement
contract fixed in advance in `eval/cases-v3/README.md`.

**Authoritative M3 evidence** (full analysis:
`eval/results/M3-HARD-SCORECARD.md`; all three reports pass
`reviewer.verify`): Sonnet detected 85/87 defective observations
(0 misses, 2 errors) but false-positived on 21/24 clean observations;
Qwen 82/87 (0 misses, 5 defect-side errors) with 19/24 clean FPs;
DeepSeek-R1:14b collapsed to 12/87 detection (4/24 clean FPs, mostly
by silence). Category/severity correctness: Sonnet 0.93/0.88, Qwen
0.72/0.68, DeepSeek 0.04/0.04. **Gate reading:** detection for the two
leading models remains saturated (every completed defective
observation detected) — the "detection no longer saturated" criterion
is not yet demonstrated for leading models; differentiation instead
appeared in hard-clean-control precision, classification, and the
weakest model's detection collapse. **Resolved by PR #21:** the
criterion itself was revised — under a disclosed same-day procedural
waiver, recorded in `docs/ROADMAP.md` §4's note, not re-argued here —
to measure the headroom the evidence actually showed (clean-control
precision collapse) rather than a detection-rate floor that a
flag-everything reviewer trivially satisfies. The frozen corpus was
not touched; only the gate's wording and its human disposition
changed.

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

### M4 — IN PROGRESS: credibility and provenance

Four pillars (`docs/ROADMAP.md` §4): real historical bugs, non-Claude
authorship, human-written cases, private holdout live and rotating.
**All four pillars are closed — M4-A, M4-B, M4-C and M4-D — each on
admitted evidence at very small scale. M4 is complete in the literal
sense its done-when defines: one real populated case in each content
category plus a live rotating private holdout. It is emphatically not a
measurement — 4 real-bug reconstructions, 1 non-Claude-authored case, 2
human-written cases and a 12-case private holdout are existence proofs
that the provenance machinery works end to end, and admission is not
measurement.**

**M4-A real historical bugs — ADMITTED EVIDENCE (smallest pillar
genuinely closed).** Four transformed reconstructions of real
bug-fix commits are admitted at `eval/cases-provenance/cases/`
(fingerprint `125cf57223f16b0269981dbe13c9c46e78dd396009719212128f74820c1828c6`,
4 cases, all `provenance.type: mined-real-fix`,
`transformation: transformed`, all BSD-3-Clause sources):
`flask-ipv6-partition-host-port`, `werkzeug-external-url-boolean-logic`,
`click-pager-windows-error-reporting`, `apistar-staticfiles-resource-leak`.
Path: candidate queue (`eval/realbug-queue/`) → proposal
(`eval/proposals/cases/`, PR #24) → independent adjudication against the
live upstream commits → admission. Three of the four required a
correction before admission and one earlier reconstruction was rejected
outright and rewritten; `reviewer_notes` on each proposal records what
was found. **Admission is not measurement** — no model has been run
against this corpus and no experiment is registered for its fingerprint.
Four cases cannot move an aggregate metric and must not be cited as if
they could (`eval/cases-provenance/README.md` states the limits).

**M4-B non-Claude authorship — ADMITTED EVIDENCE, PILLAR CLOSED.**
Two pilots have now run live: 9 attempts total, 1 survivor. Pilot 2
(preregistered, `eval/authorship-pilot/PREREGISTRATION-PILOT-2.md`) moved
unified-diff construction from the model to the harness — the model now
writes complete before/after source and `difflib` serializes it — and
produced `eval/proposals/cases/qwen-pilot-python-1787723479.json`, a
genuine qwen3.6:27b-authored resource-leak case. Checked against all nine
preregistered criteria (`eval/authorship-pilot/ADJUDICATION-PILOT-2.md`,
READY-CANDIDATE) and admitted 2026-08-27 to
`eval/cases-provenance/cases/` with one human correction — `difficulty`
set to `obvious-local`, since the model was never asked to judge it and
the seeded defect (`pass # TODO: remove this file`) is a self-announcing
tell. All other qwen3.6:27b-authored content is unchanged. **This one
case is a process/provenance demonstration, not a measurement, and
supports no general claim about qwen3.6:27b's authoring quality** — but
JP's human decision is that one genuinely non-Claude-authored admitted
case is sufficient to close the literal M4-B provenance pillar. No
further authorship pilot is planned. Pilot 2's other three attempts: one
truncated output, and two DeepSeek attempts with inverted ground truth
(authored "before = buggy, after = fixed" then labelled the change
defective) — rejected, not repaired. Detail:
`eval/authorship-pilot/ADJUDICATION-PILOT-2.md`.

**Pilot 1 (superseded interface, records kept):**
No longer blocked: both `qwen3.6:27b` and `deepseek-r1:14b` were reached
and **5 real attempts** are recorded in
`eval/authorship-pilot/attempts/` (4 planned + the 1 permitted re-ask).
**0 survived adjudication**, so `eval/proposals/` still has never
received a model-authored proposal and no non-Claude case exists
anywhere in this repository. Two attempts were schema-`ready` and both
were still rejected on reading — their post-diff files do not parse
(Python `IndentationError`, unclosed JavaScript arrow function); the
other three failed schema validation, three of those on `severity`
alone. Nothing was repaired: fixing a model's output and keeping its
authorship label is the failure mode the pipeline exists to prevent.
Per-attempt reasoning: `eval/authorship-pilot/ADJUDICATION.md`.
**A live pilot is not authored content** — B is still unmet.

**M4-C human-written cases — ADMITTED EVIDENCE, 2 cases.** Two cases
carry `provenance.human_authored: true` with `author_family: human` and
no `author_model`: `maintainer-upload-dir-override-ignored` and
`maintainer-api-key-fragment-logging`. Both reverse real fixes the maintainer authored himself — authorship verified locally before admission using Git author/committer metadata, absence of AI co-author trailers, and line-level blame. Source identifiers are not included in the public corpus.
Both sides of each diff are his verbatim code; the only work applied was
selecting a self-contained slice of it, generating the diff with
`difflib`, and assigning classification metadata. Tranche size is
**2 by JP's decision** (the roadmap says "human-written cases", plural,
with no count; the packet's 3-5 is explicitly a floor to react to, not
a target).

The distinction the schema enforces was applied, not waved through: a
third proposed case was **rejected** because the code implementing it
was written by tooling (`AI Dev Autopilot`, with a Claude co-author
trailer) rather than by JP. A concept JP supplies while tooling writes
the diff is `human_authored: false` (human-reviewed), not human-written,
and does not satisfy this pillar. Two genuine cases is small-scale
admitted evidence, not a measurement.

**M4-D private holdout — REAL: live, validated and rotating.**
A private holdout now exists outside this repository, in the storage
class §11 requires; its location, contents and fingerprint stay private
and are deliberately not recorded here. Aggregate-safe state: 12 cases,
two thirds defective with clean controls, validated by
`bin/review-corpus` with no warnings, contamination-checked by
`bin/review-holdout check` (clean), and a completed first run of 3 runs
per case whose report fingerprint matches the corpus on disk. Rotation
is initialised at generation 1 with checkable triggers and a logged
baseline, not merely described.

Two limitations are recorded rather than glossed. The first tranche is
**Claude-authored reconstruction** of real, license-checked upstream
defects — the defect mechanisms are upstream-human, the reconstruction
prose is not — so it reproduces the same self-authorship caveat as the
public corpora, and diversifying authorship is its first rotation
trigger. And at 12 cases the result is directional only: it supports no
rate, no per-category claim and no model comparison. `eval/results/HOLDOUT-RESULTS.md`
stays empty until a row is published under §11's aggregate-only rules.
Handoff: `docs/M4_PRIVATE_HOLDOUT_HANDOFF.md`.

## Canonical branch

**`main`**. PR #12, #14, #16, #18, #19, #20, #21, #22 and #24 merged;
there is no separate feature branch to work from. Any future session or
scheduler starts from a fresh clone or worktree of `origin/main`.

## Stable base

**`origin/main`** @ `b9c7346700dfaa35332a68e8154bb61615287c6f` (PR #48
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
- M4 scope creep: no real-bug case is admitted into a scored corpus
  merely because it exists on a public host and has a permissive
  license (see `docs/M4_DESIGN_BRIEF.md`) — every candidate goes
  through the candidate queue, then a proposal, then a human decision,
  never straight into `eval/cases*`
- Treating the four admitted M4-A cases as a measurement, a per-category
  claim, or evidence about real-world bugs in general — they are a
  process demonstration and the corpus README says so
- Mining/scraping infrastructure beyond a bounded candidate queue
- Execution-based oracles / sandboxed test running for M3-lineage cases
  unless a human has explicitly decided that fork (see
  `docs/M3_DESIGN_BRIEF.md` — the diff-only-vs-execution question is
  unresolved by design)
- External publication of any kind: permanently a human gate, never an
  agent action (the 2026-08-31 launch was performed by JP; follow-up
  posts, comment replies, and channel posts remain human-only)
- Leaderboard activation before genuine outside submissions exist
- Measuring the M6 gate before its scheduled date (2026-09-21), or
  treating day-to-day star/view counts as the measurement (ROADMAP §9
  failure mode 7)
- Any M7+ work (routing, model selection, agent teams) before the M6
  gate is measured and passes — including "design work" for it

These remain North Star destinations, not current backlog. Do not build
them because a stale branch or scheduler run once pointed that way.

## Next human gate (M0 through M5 complete)

One gate stands: **the M6 traction gate measurement on 2026-09-21**,
three weeks after the 2026-08-31 launch, against the criteria exactly
as written in `docs/ROADMAP.md` §5. The measurement itself and the
go/no-go decision are JP's; agents may assemble the public evidence
into a gate report but may not declare the gate passed or start M7.
Publication of any drafted material remains a human gate per ROADMAP §3
regardless of how this list evolves.

## Next autonomous work

M6-scope maintenance only, and only when a concrete need exists: fixing
an actual reproducible defect or reproduction/onboarding failure,
verifying an incoming outside benchmark submission, preparing local
review notes on incoming PRs (never posting responses — drafts are for
JP), collecting public traction evidence, and keeping reproducibility
infrastructure working. No invented work: a day with nothing genuinely
needed produces no PR. On or after 2026-09-21, autonomous work may
prepare the M6 gate report from public evidence and must then stop at
the gate. M7 is out of scope in every form until the gate is measured
and passes.

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
