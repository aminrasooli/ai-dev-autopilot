# M4 provenance gap audit

Status: **audit, not action.** What is actually known, per corpus, about
authorship, source, license, execution validation, human review, model
authorship and public/private status — and what specifically blocks a
truthful "M4 complete" claim today. Nothing here infers a fact that
isn't recorded somewhere verifiable; where the honest answer is "we
don't know," it says so.

Method: read every case file's `provenance`/`ground_truth` block
directly (`eval/cases/`, `eval/cases-v3/cases/`), cross-checked against
`docs/BENCHMARK_METHODOLOGY.md`, `CURRENT-MILESTONE.md`, and the PR
bodies for #12 (v2 freeze), #18/#19 (v3 tranches). No claim below rests
on inference from a case's *content* (e.g. "this diff looks
Claude-generated") — only on what a provenance field, a doc, or a PR
record actually states.

Legend: **VERIFIED** (directly confirmed in a case file, doc, or PR) ·
**UNKNOWN** (plausible but not recorded anywhere checkable) ·
**MISSING** (known to not exist) · **N/A** (doesn't apply to this class).

## v2 corpus (`eval/cases/`, 54 cases, fingerprint `f31d4631…045690`)

| dimension | status | detail |
|---|---|---|
| Authorship (author_family) | VERIFIED | all 54 cases `provenance.author_family: claude`, machine-checkable |
| Source type (provenance.type) | VERIFIED | all 54 `seeded-synthetic` — deliberately invented, not derived from a real fix |
| Source repository / commit | N/A | seeded-synthetic has no source commit by definition |
| License | N/A | no third-party source material incorporated |
| Execution validation | MISSING | schema field didn't exist until the M3 methodology change; 0 of 54 v2 cases carry it, and none need it (no concurrency/state-cache-class ground-truth uncertainty was ever flagged for v2) |
| Human review of ground truth | VERIFIED | `CURRENT-MILESTONE.md` M0 section: "Ground truth reviewed by JP's own eyes (D1–D5 ... )", 2026-08-21, with two cases deleted and one case's alternative categories endorsed as a direct result. Full detail lives in `CONVERGENCE-REPORT-2026-08-21.md`, described as worktree-local (not in this repository) — the *decision* and its outcome are verifiable here; the full deliberation transcript is not |
| Model authorship (self-authorship risk) | VERIFIED, unmitigated | 100% Claude-authored while Claude is an evaluated reviewer — `docs/BENCHMARK_METHODOLOGY.md` §10 states this plainly; no non-Claude-authored case exists in v2 |
| Public/private | VERIFIED | fully public, `eval/cases/`, on `main` |

## v3 corpus (`eval/cases-v3/cases/`, 37 cases, fingerprint `81daa0b7…9790`)

| dimension | status | detail |
|---|---|---|
| Authorship (author_family) | VERIFIED | all 37 cases `provenance.author_family: claude` |
| Source type (provenance.type) | VERIFIED | all 37 `authored-realistic` — synthetic, modeled on real bug patterns, not derived from an actual commit |
| Source repository / commit | N/A | authored-realistic has no source commit by definition |
| License | N/A | no third-party source material incorporated |
| Execution validation | VERIFIED (partial) | 10 of 37 cases (concurrency + state/cache) carry `ground_truth.execution_validated: true` plus a `validation_note`; the underlying scripts/output are preserved as **private** provenance outside this repository per the M3 methodology decision's provenance amendment — so the *claim* is public and machine-checkable, the *evidence* is not, by design. The other 27 cases carry no execution validation and don't claim to need it |
| Human review of ground truth | **UNKNOWN — this is the audit's headline gap** | `eval/results/M3-HARD-SCORECARD.md` states clean-control ground truth was "re-audited blind before the freeze" but does not name who performed that audit. Neither PR #18 nor PR #19's body, nor `eval/cases-v3/README.md`, records a JP-equivalent human review comparable to v2's documented D1–D5 decisions. This is not evidence of *no* review — it is the absence of a recorded one, which for a project this careful about disclosure is itself notable. Relevant because `docs/ROADMAP.md` §5's M5 launch gate explicitly requires "ground truth was human-reviewed" |
| Model authorship (self-authorship risk) | VERIFIED, unmitigated | 100% Claude-authored, same as v2; `eval/cases-v3/README.md`'s own Status line says so and defers diversification to M4 |
| Public/private | VERIFIED | fully public, `eval/cases-v3/cases/`, on `main` |

## `eval/proposals/` intake (0 proposals, 0 audits as of this session)

| dimension | status | detail |
|---|---|---|
| Mechanism exists | VERIFIED | `reviewer/propose.py` + `eval/proposals/README.md`, validated by `reviewer.propose validate-cases` / `validate-audits`; requires `author_family`, `generator` (exact model/person string), `rationale`; enforces the embedded case's `provenance.author_family` matches the proposal's |
| Content | MISSING | the directory is empty — mechanism built, never used. This session's non-Claude authorship pilot (`docs/M4_DESIGN_BRIEF.md` §B) is the first attempt to populate it, blocked in this session by lack of local-model execution access (see the decision packet) |

## Real historical bugs (`mined-real-fix`)

| dimension | status | detail |
|---|---|---|
| Any case of this type | MISSING | zero `mined-real-fix` cases exist anywhere in this repository as of this audit — `grep '"mined-real-fix"' eval/cases*/**.json` returns nothing |
| Schema readiness | VERIFIED (as of this session) | `reviewer/corpus.py` now requires `source_repository`, `source_commit`, `source_license`, `transformation` whenever `provenance.type: mined-real-fix` — see `docs/BENCHMARK_METHODOLOGY.md` §4. Before this session, only `provenance.reference` was required, which is not enough to answer a license question on its own |
| Candidate queue | MISSING before this session; VERIFIED (bounded, unadmitted) after | `eval/realbug-queue/` — see `docs/M4_DESIGN_BRIEF.md` §A. Nothing in it has been promoted to a proposal or a case |
| Previously referenced admission packet | MISSING | `CURRENT-MILESTONE.md` (pre-M4) referenced a file `REAL-BUG-ADMISSION-PACKET.md` that does not exist anywhere in this repository or its git history under that name. That reference has been corrected as part of this session's status sync; whatever it was meant to point to was never committed |

## Human-written cases

| dimension | status | detail |
|---|---|---|
| Any case with `human_authored: true` | MISSING | zero — the field did not exist before this session |
| Packet to make this cheap for JP | MISSING before this session; VERIFIED after | `docs/M4_HUMAN_AUTHOR_PACKET.md`, created this session |
| Schema support for the human-written/human-reviewed distinction | MISSING before this session; VERIFIED after | `provenance.human_authored`, required-if-present-family per `docs/BENCHMARK_METHODOLOGY.md` §4 |

## Private holdout

| dimension | status | detail |
|---|---|---|
| Design | VERIFIED | fully specified in `docs/BENCHMARK_METHODOLOGY.md` §11, since v2 — storage class, layout, versioning, authorship skew, backups, rotation triggers, publishing rules, residual-leakage honesty all written down |
| Existence | MISSING | no holdout directory exists anywhere JP or this session has visibility into; `docs/HANDOFF.md` and the maintainer's private machine-operations docs are out of this session's reach by instruction, not just by absence |
| Harness support | VERIFIED | `bin/review-eval --cases DIR` already works against any schema-valid directory; nothing holdout-specific needed in the scored path |
| Contamination-check tooling | MISSING before this session; VERIFIED after | `reviewer/holdout.py`, this session — compares a directory's fingerprint against every fingerprint named in `eval/EXPERIMENTS.md` and against the public corpora, so a holdout accidentally reused as a public run is machine-detectable |
| Public results record format | MISSING before this session; VERIFIED (empty scaffold) after | `eval/results/HOLDOUT-RESULTS.md`, header only, per `docs/M4_DESIGN_BRIEF.md` §D |

## What prevents "M4 complete" today

In priority order, grounded only in the rows above:

1. **Zero non-Claude-authored cases exist anywhere**, including in the
   intake mechanism that has existed since before this session. This is
   the single largest credibility gap M4 names, and it is currently
   MISSING content, not missing mechanism.
2. **Zero human-written cases exist.** Same shape as #1: the schema and
   packet exist as of this session, the content does not.
3. **Zero real-bug (`mined-real-fix`) cases exist**, and the schema
   fields needed to make one license-defensible did not exist before
   this session.
4. **No private holdout exists.** Design has been complete since v2;
   nothing has been built or populated.
5. **v3's ground-truth human review is UNKNOWN, not VERIFIED**, unlike
   v2's. This is not strictly an M4 blocker (M4 is about authorship
   diversity, not re-litigating M3's gate), but it is a real gap the
   M5 launch gate will need closed, and it costs nothing to name now
   rather than discover at M5.

None of these are close to done. M4 "complete" requires at minimum one
real populated case in each of the three missing content categories
(real-bug, non-Claude-authored, human-written) plus a live rotating
private holdout — this audit's job was to establish that baseline
honestly, not to shorten the distance to it.
