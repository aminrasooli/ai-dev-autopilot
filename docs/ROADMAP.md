# AI Dev Autopilot: THE PLAN

Version 1.1. Dated 2026-08-21. Owner: JP (aminrasooli).
Location of record: `docs/ROADMAP.md` on `main` of
`aminrasooli/ai-dev-autopilot`. The git copy wins over any pasted or
uploaded copy.

This is the public governing document: mission, milestones, gates,
operating model, go-to-market, open-source boundary, and the failure
modes this project guards against. A private strategy appendix exists
outside this repository and is referenced here only as "the private
appendix."

---

## 0. Instructions for any AI reading this document

When JP uploads or pastes this document, you must:

1. Read section 2 (current status) and advise WITHIN the current
   milestone only.
2. If JP, or you, propose work outside the current milestone, name it
   out loud as scope drift, cite the milestone table, and move the idea
   to the parking lot (section 10). Do not design it. Do not prompt it.
3. Never move a gate (section 5) inside a conversation. Gates change
   only by JP deliberately editing this document via PR, on a different
   day than the conversation that questioned them.
4. Actively check the named failure modes (section 9) against whatever
   is being discussed.
5. End strategy advice with three lines: current milestone, the single
   next action, and a drift check (in scope / out of scope).
6. This document overrides chat memory, prior conversations, and any
   advisor's earlier recommendations, including its own.

---

## 1. Mission and North Star

North Star: a vendor-neutral AI Engineering Manager. The human states
goals and constraints 1-3 times a day; the system plans, chooses
models by measured competence, cost, availability, privacy and risk,
builds, reviews, tests, measures outcomes, survives quota and provider
failures, hands work between agents through durable state, and brings
only consequential decisions to the human.

Product identity, one line: the human moves UP the hierarchy, not out
of it.

Near-term product (the wedge that earns the North Star): an open,
benchmarked, cross-vendor, local-capable INDEPENDENT code reviewer,
plus the public Local Reviewer Benchmark and leaderboard.

Thesis, one sentence: never let the same vendor grade its own homework.

Second product requirement, equal rank: minimize human operator
touches. Target 3 or fewer meaningful touches per day, while the human
gates in section 3 are preserved forever.

---

## 2. Current status (update this section at every milestone)

- Date: 2026-08-31
- Current milestone: **M6 Traction gate** (M0 through M5 are complete).
  JP launched publicly on LinkedIn on 2026-08-31 — the external
  publication that was M5's last, permanently human-gated item. Per the
  §5 M6 gate ("measured 3 weeks after M5 launch"), the measurement date
  is **2026-09-21**. The gate's criteria are the ones in §5, unchanged;
  it is measured once, at that time (§9, failure mode 7). M7 starts
  only if the measured gate passes.
- Done recently: all four M4 pillars are closed, each on admitted
  evidence at very small scale. Four transformed reconstructions of real
  historical bug fixes (license-checked, BSD-3-Clause sources) were
  adjudicated and admitted (M4-A). Separately, two live non-Claude
  authorship pilots ran (`qwen3.6:27b`, `deepseek-r1:14b`, CPU-only, 9
  attempts total); one qwen3.6:27b-authored resource-leak case survived
  adjudication against all nine preregistered criteria and was admitted
  — JP's human decision is that this one genuinely non-Claude-authored
  admitted case closes the literal M4-B provenance pillar. It is a
  process/provenance demonstration only, not a measurement, and supports
  no general claim about qwen3.6:27b's authoring quality; no further
  authorship pilot is planned. Both tranches live in the same new,
  separate provenance corpus, `eval/cases-provenance/cases/`, whose
  fingerprint at that point — before the M4-C tranche below — was
  `0bd3328b82427ffa6b856550914b6b5937c67ce3987a50c7c4ae2aad563d245f`.
  Neither frozen corpus moved (v2 `f31d4631…`, v3 `81daa0b7…`), no
  authoritative M2/M3 result changed, and no model has been evaluated
  against the new corpus — admission is not measurement.
  M4-D also closed: a private holdout now exists outside this
  repository, validated by `bin/review-corpus` and contamination-checked
  by `bin/review-holdout check`, with a completed first run at 3 runs
  per case and an initialised rotation state. Its contents, fingerprint
  and location stay private per §11; the corpus is 12 cases and its
  first tranche is Claude-authored reconstruction of real upstream
  defects, so diversifying authorship is registered as its first
  rotation trigger. Aggregate result is directional only at that size.
  M4-C also closed: two cases carry `human_authored: true` with
  `author_family: human` and no `author_model`. Both reverse real bug
  fixes JP wrote himself; authorship was verified locally before
  admission using Git author/committer metadata, absence of AI
  co-author trailers, and line-level blame. Source identifiers are not
  included in the public corpus. Both sides of each diff are his
  verbatim code, with only slice selection, `difflib` diff generation
  and classification applied. Tranche size 2 is JP's decision. A third
  proposed case was **rejected**: the code implementing it was written
  by tooling, and concept-by-human plus diff-by-tooling is
  `human_authored: false`, which does not satisfy this pillar. The
  provenance corpus is now 7 cases, fingerprint
  `ec3a4d7cb5095299982c6a61ad4b1b51b20dc1b0ed6f30f8f2cfc7420e61246c`
  (`claude=4, qwen=1, human=2`).
- M5 engineering landed 2026-08-29 as seven PRs (#41–#47): the
  "stable corpus" gate made executable with v2 declared stable at
  corpus level (frozen fingerprint untouched); the README reproduction
  path fixed so it actually does what it tells a stranger (the corpus
  command now prints the fingerprint, and the evidence table's
  assertion count was corrected against the measured total); a
  generated ground-truth review packet (`--review`) that renders and
  never decides; the licence decisions recorded with
  inbound = outbound and no CLA; the v3 answer-key errata admitting
  the corpus is human-reviewed *with documented errata*, not
  error-free; a drift guard pinning the committed scorecard to a fresh
  generation; and `harness.dirty` corrected to count tracked
  modifications only, so following SUBMIT.md's own instructions no
  longer brands a run unreproducible. Each fix came from *executing*
  the documented path, not reading it.
- M5 closed 2026-08-31: JP performed the launch himself (LinkedIn).
  External publication was and remains permanently a human gate; no
  agent performed or will perform any part of it. The leaderboard
  goes live only after outside submissions exist, which is what
  launching is for.
- Remaining for M6: wait for 2026-09-21 and measure the §5 criteria
  once. Until then: maintenance on concrete defects, verification of
  any outside submissions, and passive evidence collection only.
- Blockers: none in engineering. No model has been evaluated against
  the provenance corpus — admission is not measurement.

---

## 3. Operating model (how we work, every day)

- Touch metric: 3 or fewer human operator touches per day.
- Human gates that NEVER automate: merge to main, secrets and
  passphrases, sudo and security-sensitive changes, publishing
  externally, product-direction changes, spend above the authorized
  threshold. Reduce touch frequency by batching; never delete gates.
- Session hygiene: every autonomous block ends with a REPORT file
  written, work committed and pushed, then `/clear`. The next block
  starts from the report. Never keep one session alive for days;
  sessions hand off through files, not living memory (docs/HANDOFF.md).
- Model policy: Sonnet for 80-90 percent of hours (long blocks,
  implementation, benchmark runs, GitHub work). Fable only for
  milestone-level decisions, 15-40 minutes, then hand to Sonnet. Opus
  as escalation for genuinely hard debugging. At roughly 70-80 percent
  of a session window, stop feeding paid models and let local GPU jobs
  run until reset.
- Agents work inside written charters: verify reality first, bounded
  timeouts, batch human gates and keep working, stop early when done,
  end with a 90-second-readable report plus exact gate commands.

---

## 4. Milestones

| # | Milestone | Done when |
|---|-----------|-----------|
| M0 | Pre-flight (calendar gate: before travel) | Ground truth reviewed by JP's own eyes; PR #12 merged by JP; B0 encrypted backup completed; nightly scheduler re-enabled |
| M1 | Benchmark v2 frozen | Answer key frozen; repeat runs; reproducible from a fresh clone |
| M2 | Cross-model pilot | Sonnet vs Qwen vs DeepSeek on frozen corpus, 3 repetitions, honest cost + latency + quality scorecard, clearly labeled a pilot |
| M3 | Hard benchmark v3 | Large realistic diffs, true cross-file reasoning, state/cache, authorization, concurrency, hard clean controls; and the frozen corpus is demonstrably unsaturated: on the preregistered raw-count axes, no evaluated reviewer performs near-perfectly on defect detection and clean-control discrimination at the same time, and at least one evaluated reviewer materially outperforms both a flag-everything and an approve-everything strategy. Criterion revised 2026-08-24, after results, under a disclosed same-day procedural waiver — see the note below this table |
| M4 | Credibility and provenance | Real historical bugs (license-checked), cases authored by non-Claude models, human-written cases, private holdout live and rotating |
| M5 | Public launch | Stable corpus, reproducible runs, multi-dimensional scorecard (repeatability, cost, latency, precision, classification, hard tier), SUBMIT.md accepting outside results, leaderboard page |
| M6 | Traction gate | Numbers in section 5 measured; go/no-go for platform |
| M7 | Measured model selection | Evidence-based task-to-model routing from benchmark data (the router, earned) |
| M8 | Agent team execution | Planner / builder / reviewer roles across models, durable handoffs, measured touches |
| M9 | Continuity and authority | Quota failover, resumable execution, risk tiers, escalation policy |
| M10 | AI Engineering Manager | North Star realized |

Order is strict. No milestone starts before the previous one's gate.

**Note on the M3 criterion (revised 2026-08-24, after results, under a disclosed same-day procedural waiver).**

M3 originally read "...; detection no longer saturated." The
preregistered X17-X19 measurement did not satisfy that wording: the two
leading reviewers detected every defective observation they completed
(85/85 and 82/82). That literal failure stands, and is recorded in
`eval/results/M3-HARD-SCORECARD.md`.

The same evidence showed why the wording cannot work as written.
`detected` is defined as "at least one finding on a defective case", so
a reviewer's detection rate is bounded below by the rate at which it
raises findings on *clean* diffs -- a property of the reviewer, not of
case difficulty. Measured here that floor is 0.83-0.88 for the leading
reviewers, so no amount of additional defect subtlety could have moved
their detection rate, and a reviewer that flags every diff scores 100%
detection forever. Detection rate alone therefore cannot measure
whether a corpus is hard.

What the corpus did do is remove the saturation the milestone was
protecting against. Against the same three reviewers, the strongest
held detection at 1.00 while its correct-approval rate on clean
controls fell from 0.79 on the v2 corpus to 0.13 here (3 of 24 clean
observations), and the weakest reviewer's detection fell from 0.82 to
0.14. The revised criterion measures that headroom directly, on the
same preregistered axes, and cannot be met by a flag-everything or an
approve-everything reviewer. If a future reviewer ever does score
near-perfectly on both axes at once, this corpus version is saturated
and a new version is required -- that is the criterion's own retirement
condition.

The replacement criterion was **not** preregistered. It was adopted
after the results, deliberately and on the record. The gate was
questioned on 2026-08-23/24.

Section 0 rule 3 and section 9 failure mode 2 require gate changes to
land by deliberate PR edit on a different day than the conversation
that questioned them, specifically to prevent a gate being rationalized
away in the same sitting as a disappointing result. JP explicitly
waived that specific requirement for this one decision, choosing on
2026-08-24 -- the same day the gate was questioned -- to proceed rather
than wait. This note discloses that waiver rather than concealing it.
The waiver is procedural only: it does not change the substantive
criterion above beyond what independent review already produced, it
does not amend rule 3 or failure mode 2 for any future gate decision,
and no frozen case, raw report, registry row or scoring rule was
changed because of it.

---

## 5. Gates (pre-committed so they cannot quietly move)

- M0 calendar gate: complete before the flight. Without the nightly
  scheduler on, the low-touch operating model does not exist.
- M5 launch gate: a stranger can reproduce the headline result from
  the README alone, AND the corpus is demonstrably unsaturated by the
  revised M3 criterion (M3 done -- criterion revised 2026-08-24 after
  results, under a disclosed same-day procedural waiver, per the note
  under the milestone table), AND ground truth was human-reviewed.
- M6 traction gate, measured 3 weeks after M5 launch, priority order:
  1. At least 1 independent reproduction or result submission from a
     stranger (worth more than everything else combined).
  2. At least 2 issues or PRs from people JP has never spoken to.
  3. Roughly 100+ stars from real accounts.
  Pass: continue to M7+. Miss: rework positioning ONCE, relaunch.
  Miss twice: park the platform ambition without shame; the benchmark
  remains a standalone asset.
- License gate (unresolved, decide before M5): candidates include
  AGPL-3.0 and Apache-2.0/MIT. The analysis (adoption versus
  protection, contributor-agreement implications) has not been done
  yet and is scheduled before launch. Until decided, this remains an
  open question, not a default.
- Additional commercial and ownership gates exist in the private
  appendix and bind equally.

---

## 6. Go-to-market

### Who we target (in order)

1. Developers running local LLMs: r/LocalLLaMA is the core audience;
   they want proof local models are good enough. The leaderboard is
   built for them.
2. AI engineering leaders and practitioners: LinkedIn.
3. Builders and early adopters: Hacker News.
4. Engineering teams with strict privacy or on-prem requirements.
5. Persian-language tech audience.

### Message rules

- Advertise the RESULT, not the repo. Numbers travel, links do not.
- The thesis line in every major post: never let the same vendor grade
  its own homework.
- Honest framing always: pilot results are labeled pilot; variance is
  reported; only corrected, repeat-run figures are citable.
- Voice: first person, plain language, no em dashes, no AI-sounding
  vocabulary, claims grounded in verifiable experience.

### Channel playbook by stage

- Now through M2 (build in public): LinkedIn progress posts, findings,
  screenshots. Small. No leaderboard hype. r/LocalLLaMA gets the M2
  pilot scorecard, clearly labeled a pilot.
- M4/M5 (the launch): LinkedIn long-form + technical blog +
  r/LocalLLaMA results post. Show HN exactly once, on a weekday
  morning US time, title is the claim not the tool name, and ONLY on a
  day JP can personally answer comments all day. Never from an
  airport.
- M6 onward: promote genuine outside results only.

### The content engine (repeatable, mostly automated)

- Every new open-weight model release: run it through the harness
  within 48 hours, publish the updated table.
- SUBMIT.md invites anyone to run their own model and submit results
  by PR; independent submissions are also the strongest traction
  evidence there is.
- Compounding small stuff: awesome-list submissions, README with the
  table and a 60-second GIF at the top, one-command install.
- Persian-language versions of major posts.
- Agents draft posts in the nightly pipeline; JP approves each one
  before anything is published. One touch per post.

---

## 7. Open-source boundary

The rule: open the machinery people need to trust, adopt, extend, and
reproduce. Keep the commercial operation layer private.

Public (open source): reviewer adapters (Claude, Qwen/Ollama,
DeepSeek, Codex, future models), benchmark harness and evaluator,
repeat-run and checkpoint tooling, public corpus and validator,
methodology docs, result schema, public leaderboard data, submission
workflow, handoff protocol, safety contracts, CLI.

Private (commercial layer): private holdout corpus and its rotation
strategy, unpublished adversarial cases, learned routing policies and
competence history (M7+), customer data, hosted control plane,
enterprise governance features, private evaluation packs.

Commitment: no hostile lock-in tricks and no crippled open source. The
open benchmark core is and remains free. Any commercial services are
built around it (hosted, certified, or private evaluations), never by
paywalling the public benchmark.

---

## 8. Build versus reuse rule

Before building any substantial infrastructure, inspect mature open
source. Build only when our differentiated requirement is not served.

- Coding agent: never build (Claude Code, OpenHands, Aider exist).
- Stateful agent graph: evaluate LangGraph before building.
- Provider gateway: evaluate LiteLLM before writing many adapters.
- Routing algorithms: study RouteLLM at M7 before inventing theory.
- Benchmark methodology: borrow from SWE-bench and related work.

Our differentiation, the only things worth building: measured
engineering competence, safe autonomy, human-touch reduction,
evidence-based delegation, durable handoff, and the manager layer.

---

## 9. Failure modes we guard against (named, real, documented)

1. Infrastructure before demand. The documented pattern: the platform
   vision regrew three separate times before the wedge shipped once.
   Rule: current milestone only; everything else goes to the parking
   lot. Advisors must name drift out loud (section 0).
2. Moving gates mid-conversation. Gates change only by deliberate PR
   edit to this file on a different day.
3. Vendor self-grading. Claude may not approve ground truth Claude
   wrote; human eyes on the answer key; the holdout stays private;
   writer, reviewer, and merger are never the same party.
4. Number inflation. Publish only corrected, repeat-run figures with
   variance. Single-run numbers are never citable.
5. Context bloat. Days-old sessions burn quota and degrade quality.
   REPORT, commit, `/clear`, every block.
6. Advisor-loop amplification. When advisors converge, polling stops
   and execution starts.
7. Anxiety metrics. Competitor watch weekly, not daily. Day-to-day
   stars and view counts are noise; the M6 gate is the only audience
   number that matters, measured once, at its scheduled time.
8. Autonomy without gates. The touch target is met by batching, never
   by deleting human gates. Unattended merge rights on a repo that
   auto-executes nightly is a supply-chain hole, not a convenience.

---

## 10. Parking lot

New scope lands here via PR with a one-line rationale, and waits for
its milestone. Multi-seat team details live in docs/NORTH_STAR.md
deferred vision. Current parked items: safety/hardening product spin
(one-pager only), merge-automation beyond GitHub-native auto-merge
(read-only digest at most), mass case generation beyond the current
milestone's target.

---

End of THE PLAN. If a conversation contradicts this document, the
conversation is wrong until this document is deliberately changed.
