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

- Date: 2026-08-22
- Current milestone: M3 Hard benchmark v3 (M0, M1 and M2 are complete)
- Done recently: M2 cross-model pilot closed (PR #16, merge commit
  85a265706f478a7b0d3c5e40e7b17c293dd66b4e) — Sonnet, Qwen3.6:27b and
  DeepSeek-R1:14b run 3x each against the frozen 54-case corpus,
  pre-registered before execution. Sonnet 1.00 defect recall, Qwen 0.99
  with no external model API charge, DeepSeek 0.82; Sonnet materially
  stronger than Qwen on category/severity classification, DeepSeek
  materially weaker on classification. Detection is now saturated for
  the top two models across every difficulty tier — the open question
  is no longer "can it find the bug" but "can it classify it," plus
  whether the corpus itself is hard enough, which is M3's job.
- Single next action: resolve the one open M3 methodology fork
  (diff-only vs. execution-based oracle for state/cache and concurrency
  cases — see `docs/M3_DESIGN_BRIEF.md`), then begin authoring the M3
  hard-case taxonomy as a new benchmark version; the frozen v2 corpus
  is not touched.
- Blockers: none identified; the methodology fork above is a deliberate
  pause point, not a blocker.

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
| M3 | Hard benchmark v3 | Large realistic diffs, true cross-file reasoning, state/cache, authorization, concurrency, hard clean controls; detection no longer saturated |
| M4 | Credibility and provenance | Real historical bugs (license-checked), cases authored by non-Claude models, human-written cases, private holdout live and rotating |
| M5 | Public launch | Stable corpus, reproducible runs, multi-dimensional scorecard (repeatability, cost, latency, precision, classification, hard tier), SUBMIT.md accepting outside results, leaderboard page |
| M6 | Traction gate | Numbers in section 5 measured; go/no-go for platform |
| M7 | Measured model selection | Evidence-based task-to-model routing from benchmark data (the router, earned) |
| M8 | Agent team execution | Planner / builder / reviewer roles across models, durable handoffs, measured touches |
| M9 | Continuity and authority | Quota failover, resumable execution, risk tiers, escalation policy |
| M10 | AI Engineering Manager | North Star realized |

Order is strict. No milestone starts before the previous one's gate.

---

## 5. Gates (pre-committed so they cannot quietly move)

- M0 calendar gate: complete before the flight. Without the nightly
  scheduler on, the low-touch operating model does not exist.
- M5 launch gate: a stranger can reproduce the headline result from
  the README alone, AND the corpus is no longer detection-saturated
  (M3 done), AND ground truth was human-reviewed.
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
