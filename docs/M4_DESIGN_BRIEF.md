# M4 design brief — credibility and provenance

Status: **design + first implementation.** Turns `docs/ROADMAP.md` §4's
M4 row (real historical bugs, non-Claude authorship, human-written cases,
private holdout) into a bounded plan. Scope discipline per ROADMAP §9
failure mode 1: this is credibility work on the existing benchmark, not a
platform. No routing, no agent teams, no dashboard, no new hosted
service, no M5 launch prep.

Grounded in `docs/BENCHMARK_METHODOLOGY.md` §3 (provenance classes), §10
(contamination/self-authorship), §11 (private holdout design — already
specified, mostly unbuilt), `eval/proposals/README.md` (the case-proposal
intake that already exists), and `docs/M4_PROVENANCE_GAP_AUDIT.md` (what
today's corpora actually have versus what M4 needs).

**What M4 does not need to build from scratch.** Two of the four M4
pillars already have real infrastructure:

- The provenance schema (`provenance.type`, `provenance.author_family`,
  `provenance.reference`) has existed since v2. This session extends it
  (see `docs/M4_PROVENANCE_GAP_AUDIT.md` and
  `docs/BENCHMARK_METHODOLOGY.md` §4) rather than replacing it.
- The non-Claude-authorship intake path — `eval/proposals/`, validated by
  `reviewer.propose` — already exists, already requires `author_family`
  and an exact `generator` string, and already enforces "a model may
  propose, but never write into the scored corpus." M4-B below uses this
  path; it does not invent a new one.

## A. Real historical bugs (license-checked)

**Goal:** a small number of high-confidence, license-clean, real bug-fix
commits, reconstructed as reversed diffs, never admitted automatically.

**Pipeline (implemented this session):** `reviewer/realbug.py` /
`bin/review-realbug`, a **candidate queue, not an admission path**. It
never writes to `eval/cases*`. Per candidate it records: repository,
bug-fix commit, parent commit, language, changed files, approximate diff
size, issue/PR reference (if any), repository license, a confidence score
that the commit is genuinely a bug fix (not a refactor/feature/revert),
whether the code can legally/safely be incorporated, and a recommended
treatment — `verbatim`, `transformed`, `synthetic-reconstruction`, or
`reject`. Schema, validation rules and CLI: `reviewer/realbug.py`
(`bin/review-realbug validate|summary`).

**Acceptance evidence, defined now so nothing is admitted on vibes:**

1. **License compatibility is necessary, not sufficient.** Only
   repositories under licenses that permit redistribution of excerpts
   (MIT, BSD-2/3-Clause, Apache-2.0, ISC, 0BSD and similar — checked
   per repository, never assumed from a package registry badge or a
   README claim) are eligible at all. Copyleft (GPL/AGPL) and
   unlicensed/all-rights-reserved repositories are rejected outright,
   regardless of how good the bug is — the benchmark cannot absorb a
   license-compatibility argument for a single case.
2. **The commit must be plausibly a pure bug fix.** Author confidence,
   not automation, decides this — a commit that also refactors, renames,
   or adds features alongside the fix is a poor candidate (the "true"
   defect is entangled with unrelated change) and should generally be
   `reject`ed or heavily `transformed` to isolate the fix.
3. **Leakage prevention (methodology §3, already specified, restated
   here as the acceptance bar):** the case carries the *reversed* diff
   only. The commit message, PR discussion, issue title, and CVE text —
   all of which frequently state the answer outright — are never copied
   into the case. Identifiers that give the defect away
   (`fix_race_in_flush`) are renamed.
4. **Minimize copyright exposure by default.** `transformed` (rewritten
   with the same defect mechanism, different surrounding code/names) is
   preferred over `verbatim`. `verbatim` is reserved for short, clearly
   fair-use-scale excerpts under an explicitly permissive license, with
   `source_license` recorded. Both are gated on a known-permissive
   license by `reviewer.corpus.validate_case`, not just by this
   paragraph. `synthetic-reconstruction` (the mechanism observed, the
   code rewritten from scratch, nothing derived) is preferred whenever
   the license is ambiguous or copyleft but the *pattern* is still worth
   capturing, and is the one treatment that gate exempts.

   Two honest ways to record a synthetic reconstruction, and the
   difference is a real one:
   - **`mined-real-fix` + `transformation: synthetic-reconstruction`** —
     the defect came from an identified commit and the case says so.
     The source fields are required and the attribution stands even
     though no code was copied. Prefer this when you know the source;
     crediting it is more truthful than not.
   - **`authored-realistic`, no source fields** — the case was written
     from a *category* of bug rather than one identified commit. This is
     not a real-bug case, must not be counted as one, and carries no
     `transformation`.
5. **No mass scraping.** Each candidate is hand-entered into the queue
   (or entered by a bounded, human-reviewed script run against a named,
   chosen repository — never an open-ended crawl). The queue tool has no
   "search GitHub and import everything matching X" mode, and none
   should be added.

**A-tier candidate queue (this session):** a small, bounded seed list —
see `eval/realbug-queue/` — evaluated for process, not volume. Every
candidate needs a human decision before it becomes a proposal (via
`eval/proposals/`, format below) and, separately, before a proposal
becomes a case. Nothing in the seed queue is pre-approved.

## B. Non-Claude authorship

**Goal:** candidate cases whose defect content, category, and severity
judgment were generated by a model other than Claude, with provenance
that survives contact with Claude.

**Mechanism: reuse `eval/proposals/` exactly as specified**, with the M4
schema fields layered on top:

- `proposal.author_family` and the embedded `case.provenance.author_family`
  must match (already enforced by `reviewer.propose`).
- `proposal.generator` and `case.provenance.author_model` both record the
  exact model identifier (e.g. `qwen3.6:27b`, `deepseek-r1:14b`) — the
  proposal-level field is pre-existing; `author_model` makes the same
  fact survive into the case itself once admitted, so it is not lost the
  moment a proposal graduates.
- **Claude may validate schema/formatting on a proposal — never rewrite
  its defect content and keep calling it non-Claude-authored.** If a
  candidate needs substantial rewriting to become schema-valid or
  coherent, the correct outcomes are: (a) reject it, (b) send it back to
  the same model for another attempt, or (c) accept it but relabel
  `author_family: mixed` with a `provenance_notes` line stating what
  Claude changed and why. Silently fixing it and leaving `author_family`
  as the original model is the one outcome this pipeline exists to
  prevent (docs/ROADMAP.md §9 failure mode 3).
- **Author/evaluator conflict.** A model that authored a case and is
  later evaluated against the corpus containing it has the same
  self-authorship problem Claude already has (methodology §10) — mirrored,
  not new. Mitigation: (1) `author_family`/`author_model` make this
  slice-able in every future scorecard exactly like Claude's is today;
  (2) a model's own authored cases should be reported separately if that
  model is later benchmarked against a corpus that includes them, the
  same way this project already discloses Claude's self-authorship
  rather than hiding it; (3) the private holdout (§D) is the eventual
  answer for a fully independent read, not this tranche.

**Review rules for model-authored ground truth:** identical bar to
Claude-authored cases — schema validation (`reviewer.propose
validate-cases`), then human adjudication before anything moves into
`eval/cases*`. A model's stated `defect`/`category`/`severity` is a
*proposal*, never accepted as ground truth by virtue of confidence or
fluency.

**Pilot (this session):** a small set of candidate proposals generated by
locally-run Qwen3.6:27b and DeepSeek-R1:14b via the existing Ollama
backend, recorded with the exact model, prompt, timestamp, case concept,
expected defect, and whether Claude touched the output afterward. Not
added to the frozen public corpus. **Execution note:** this requires a
running local Ollama daemon with both models pulled; the sandboxed
environment this design brief was authored in has neither (no
`~/.ollama/models`, and the daemon cannot bind/write under this session's
filesystem sandbox) — the same host GPU M2/M3 already depended on. See
the decision packet for the exact handoff command.

## C. Human-written cases

**Goal:** a small, genuinely human-authored tranche, truthfully labeled,
at minimal cost to JP's time.

**Definition (schema-enforced, see `docs/BENCHMARK_METHODOLOGY.md` §4):**
`provenance.author_family: human` **requires** an explicit
`provenance.human_authored` boolean.

- `human_authored: true` — a human wrote the scenario, the diff (or
  dictated it precisely enough that no material judgment was made by
  tooling), and the category/severity/explanation. This is the only
  configuration allowed to be called "human-written."
- `human_authored: false` — a human supplied the concept and the ground
  truth *decision* (what the defect is, why it matters, what correct
  behavior looks like); tooling or Claude did the mechanical
  diff/JSON formatting. This is **human-reviewed**, not human-written,
  and must say so.

Claude-authored text can never be marked `human_authored: true` even if a
human approved it afterward — approval is `human-reviewed`, not
authorship. The validator cannot detect this by itself (it can't tell who
typed what); the discipline is: only set `human_authored: true` for a
case built from `docs/M4_HUMAN_AUTHOR_PACKET.md` submissions where JP
supplied the diff/code content himself, not just the concept.

**Human-author packet (this session):** `docs/M4_HUMAN_AUTHOR_PACKET.md`
— a short per-case template asking only for scenario, intended defect,
why it matters, expected correct behavior, and optional language/domain.
Tooling (a small script, not built yet — see the packet's own "next
step") turns a filled packet into a schema-valid proposal with
`human_authored: false` by default, upgraded to `true` only when JP
explicitly supplies diff-level content rather than a concept.

**Minimum useful tranche:** not sized here — that's JP's call, batched in
the decision packet. A useful floor to react to: 3-5 cases is enough to
exercise the packet and tooling; it is not enough to move any aggregate
metric, and should not be reported as if it were.

## D. Private holdout

**Goal:** a corpus of cases that never enters this public repository,
runnable through the exact same harness, for the exact same reason v2/v3
are versioned and fingerprinted — public corpora decay (methodology §10).

**Already specified, mostly unbuilt:** `docs/BENCHMARK_METHODOLOGY.md`
§11 fully designs this (storage class, layout, versioning, authorship
skew, backups, rotation triggers, publishing rules, residual-leakage
honesty). M4's job is the minimum safe scaffold, not a redesign.

**What is safely buildable from inside this repository (this session):**

- `bin/review-eval --cases DIR` already accepts any schema-valid
  directory — no new harness code needed; this was true since v2 and is
  the entire point of §11's design (reused, not rebuilt).
- A **fingerprint-only public record**: this repo may state that a
  holdout exists, its `benchmark_version`, its human-readable name, its
  `sha256` fingerprint, and aggregate stats (case count,
  language/category distribution) once results are ever published — never
  the cases, never an absolute path, never which machine holds it. A
  holdout now exists outside this repository, but **no such record has
  been published**: §11's aggregate-only rules keep
  `eval/results/HOLDOUT-RESULTS.md` empty until a row is approved for
  publication. It was created with the publishing-rules header only, in
  the session that wrote this brief, so a future result has somewhere to
  go.
- A **contamination-check helper**: `reviewer/holdout.py` computes and
  compares a holdout directory's fingerprint against the public corpora's
  fingerprints and against each other, and can assert "this fingerprint
  has never been referenced in `eval/EXPERIMENTS.md`" — a cheap check
  that a holdout hasn't accidentally been reused as a public run.
- A rotation policy, restated concretely from methodology §11 rather than
  redesigned: rotate on score-tracking-too-closely, accidental public
  quoting, or a fixed cadence once the benchmark has outside users — see
  `docs/M4_PRIVATE_HOLDOUT_HANDOFF.md`.

**Hard stop at this session's boundary:** creating the actual private
directory, populating it with cases, or touching the maintainer's
private machine-operations documentation is explicitly out of scope for
this session and is not attempted. The exact handoff — what JP needs to create, where, and
how to point the harness at it — is `docs/M4_PRIVATE_HOLDOUT_HANDOFF.md`.

## What M4 explicitly does not build

- No general benchmark platform, contribution portal, or web UI.
- No automatic admission of any candidate (real-bug, model-authored, or
  human) into `eval/cases*` — every path above ends at a human decision.
- No mass repository scraping for real bugs.
- No evaluation of Qwen/DeepSeek as reviewers of their own authored
  cases in this session (task instructions §6) — that is a future,
  separately-designed pilot, not part of this brief's scope.
- No private holdout content committed publicly, no hosted service, no
  new database.
- No M5 (public launch) prep — the leaderboard stays inactive; nothing
  here changes its preconditions.
