# M3 design brief — hard benchmark v3

Status: **design/gap-analysis only.** No v3 cases exist, no
infrastructure has been built, and the frozen v2 corpus (`eval/cases/`,
fingerprint `f31d46310988f61c4534344ad05a52a4385fd15159126a0be85aad532f045690`)
is untouched by this document. Per `docs/ROADMAP.md` §4, M3 is "Hard
benchmark v3": larger realistic diffs, true cross-file reasoning,
state/cache failures, authorization failures, concurrency failures, hard
clean controls; detection no longer saturated. This brief inventories
what v2 already tests, quantifies where M2 detection saturated, and
proposes a taxonomy for what v3 needs to add — nothing more. M3 must land
as a new benchmark version/boundary; it never mutates the frozen v2
corpus (ROADMAP §9 failure mode 4, number inflation, applies equally to
silently changing what "the corpus" means under an existing fingerprint).

## 1. What v2 already tests (direct inventory, not estimate)

54 cases, 40 defective / 14 clean, all diffs 6–35 lines (max is a clean
4-file refactor, `53-xfile-clean-helper-move`). No diff in the corpus
approaches the size of a realistic PR.

| dimension | v2 coverage today | depth |
|---|---|---|
| cross-file | 6 cases (`49`–`53`, tag `true-cross-file`), 2–4 files, 14–35 lines | shallow: file-pair consistency checks (swapped args, renamed config key, weaker decorator) — see §2 |
| concurrency | 3 cases (`22`, `30`, `36`) | shallow: one textbook idiom each (read-modify-write race, loop-var capture, double-checked-locking without volatile), single function |
| authorization | 4 cases (`26`, `41`, `42`, `52`), category `auth-bypass` | shallow: each is a single obvious or moderate local diff except `52` (cross-file, still small) |
| state/cache | 1 case (`02-subtle-cache-key`) | thin: a single cache-key string bug, no TTL/invalidation/consistency reasoning |
| destructive/data operations | 2 cases (`12`, `39`) | shallow, single-file |
| clean controls | 14 cases, all `defect: false` | already produces real confusion (see §2) despite being the "easy" tier by construction |
| larger realistic diffs | **0 cases** | not represented at any size beyond 35 lines |

## 2. Where M2 detection actually saturated (from `eval/results/M2-PILOT-SCORECARD.md`)

Recall by difficulty tier, this pilot, 3 runs/case:

| tier | Sonnet | Qwen | DeepSeek |
|---|---|---|---|
| obvious-local | 1.00 | 1.00 | 0.85 |
| moderate | 1.00 | 1.00 | 0.78 |
| subtle | 1.00 | 0.94 | 0.68 |
| cross-file | 1.00 | 1.00 | 1.00 |

Two conclusions, both load-bearing for what v3 must fix:

1. **The strongest model (Sonnet) is flat 1.00 across every tier and
   file-span.** There is no recall headroom left to differentiate a
   frontier model on this corpus. Classification is a different story —
   category correct 0.85, severity correct 0.82 — so the saturated axis
   is detection, not review quality overall.
2. **Cross-file recall is 1.00 even for the weakest model (DeepSeek),
   while DeepSeek's non-cross-file recall drops to 0.68–0.85.** If the
   6 cross-file cases were genuinely harder than the rest of the corpus,
   the weakest model should show it there first. It doesn't. This is
   direct evidence that today's cross-file cases test "spot the
   inconsistency between two adjacent files" (a pattern-match a model
   already good at diffs can do without synthesizing cross-file
   *behavior*), not the "true cross-file reasoning" ROADMAP asks for.

Separately, `47-py-mktemp-race` produced a `MalformedResponse` error
(out-of-vocabulary category, something race-flavored) on all 3 Qwen runs
and 1 DeepSeek run — both models reached for a race/concurrency label
that isn't in the fixed vocabulary rather than the ground-truth
`concurrency` category. Suggestive of a real gap in the taxonomy's
concurrency granularity, worth a look at prompt-contract level, but that
is a v2 maintenance question, not new M3 scope, and is not touched here.

## 3. Gap analysis against ROADMAP's M3 checklist

| ROADMAP M3 item | current coverage | verdict |
|---|---|---|
| larger realistic diffs | none | **fully open** |
| true cross-file reasoning | 6 shallow cases, saturated (§2) | **present in name, missing in difficulty** |
| state/cache failures | 1 thin case | **mostly missing** |
| authorization failures | 4 cases, all shallow | **breadth adequate, depth missing** |
| concurrency failures | 3 textbook-idiom cases | **breadth adequate, depth missing** |
| hard clean controls | 14 clean cases, no difficulty axis at all (schema forbids it — see §5) | **the "hard" tier doesn't exist as a concept yet** |
| detection no longer saturated | — | direct consequence of the six rows above, not an independent thing to build |

Note on clean controls: they are not blank ground. 5 of the 14 already
produced false positives somewhere across the M2 pilot's three models —
`18-clean-test-added`, `48-py-clean-logging-added`,
`53-xfile-clean-helper-move`, `54-clean-dependency-bump`,
`55-clean-dead-code-removed`. These are refactor/dependency/logging
patterns that already read as suspicious to a reviewer despite being
correct. That is the seed for a genuine hard-clean-control tier, not a
reason to write new ones from nothing.

## 4. Proposed hard-case taxonomy (draft, not authored)

Six categories, sized to roughly double the corpus (v2 is 54 cases; a
v3 addition in the 40–60 range keeps authoring effort and per-run cost
proportionate — see §5 for why this is a methodology call, not a fixed
number here):

1. **Larger realistic diffs (new).** Multi-hunk, multi-function diffs in
   the 80–250 line range, modeled on real PR shapes (still
   `seeded-synthetic` or `authored-realistic` per
   `docs/BENCHMARK_METHODOLOGY.md` §3 — mined-real-fix stays future
   work, unchanged from v2's plan). One seeded defect each, buried among
   legitimate unrelated changes in the same diff — the realism axis is
   "can the model find the bug inside noise," not "is the bug itself
   more exotic."
2. **Deep cross-file reasoning.** Cases where the defect is only visible
   by combining information from 2+ files that do NOT sit next to each
   other in an obvious rename/mismatch pattern — e.g., a config default
   defined in one file silently changing the meaning of a check three
   call-frames away in another, or a schema/migration file whose change
   only breaks an ORM model file's assumption under a specific code
   path. Target: cases where a model must trace behavior, not diff two
   files against each other.
3. **State/cache failures (near-empty today).** Stale-read after
   invalidation, TTL/expiry races, cache key collisions under
   concurrent writers, read-after-write inconsistency. This is the
   category most likely to force the diff-only-vs-execution-oracle
   decision in §6 — some of these are hard to make convincing as a
   static diff without showing an execution trace.
4. **Deeper authorization failures.** Not "missing an auth check" (v2
   already covers that shallowly) but authorization that is *correct at
   the point of the diff* and wrong only in combination with a caller,
   a config flag, or an ordering assumption elsewhere — i.e., overlaps
   with #2 by design; some cross-file cases should be authored from the
   authorization angle specifically.
5. **Concurrency beyond textbook idioms.** Interleavings across async
   boundaries, ordering assumptions between two functions that are each
   individually correct, resource contention that only manifests under
   specific timing — harder to author convincingly diff-only (see §6).
6. **Hard clean controls.** Extend exactly the five already-confusing
   v2 patterns (refactor, dependency bump, dead-code removal, logging
   addition, cross-file helper move) at greater scale and with sharper
   near-miss framing — e.g., a dependency bump that changes a
   *transitive* default behavior (genuinely worth flagging) sitting
   next to one that doesn't (a clean control), so the model must reason
   about the actual change, not pattern-match "dependency bump = risk."

## 5. Methodology decisions vs. implementation decisions

Kept separate deliberately — the first list needs human (or Fable)
judgment because it trades off cost, realism, and reversibility; the
second is mechanical once the first is settled and Sonnet can do it
directly.

**Methodology decisions (need sign-off before case authoring starts):**

- **Diff-only vs. execution-based oracle for state/cache and concurrency
  cases (#3, #5 above).** `docs/BENCHMARK_METHODOLOGY.md` §2 rejected
  execution-based oracles for v2 as infrastructure-heavy and explicitly
  "deferred, not dismissed." Some state/cache and concurrency bugs are
  hard to make convincingly diff-only; but building sandboxed
  per-language execution is real new infrastructure, cuts against
  ROADMAP §8's build-vs-reuse discipline, and is expensive to reverse
  once cases are authored around it either way. **This is the single
  highest-leverage open fork in this brief** — see §7.
- **Target diff size for "larger realistic diffs."** 80–250 lines is
  this brief's draft guess, not a decided number. Bigger diffs mean
  slower and more expensive calls, especially for the local models this
  benchmark exists partly to showcase (DeepSeek's mean latency was
  already 2.5s on 6–35 line diffs in M2) — a real tension with ROADMAP's
  low-touch, honest-cost framing, not a free realism upgrade.
- **Corpus size / quotas per category.** The "roughly double" sizing in
  §4 is a guess to keep authoring effort and per-run cost proportionate,
  not a commitment.
- **Whether clean cases get a difficulty axis.** The validator currently
  *forbids* declaring `difficulty` on a clean case
  (`reviewer/corpus.py`: "clean cases must not declare a difficulty").
  A hard-clean-control tier (taxonomy #6) needs some way to mark
  difficulty for clean cases too — a schema decision that touches
  `docs/BENCHMARK_METHODOLOGY.md`'s case-schema section, not just case
  content.
- **Authorship mix for v3.** ROADMAP §4 puts "cases authored by
  non-Claude models" and "human-written cases" under **M4**
  (credibility and provenance), not M3. Recommendation: v3 stays
  `seeded-synthetic`/`authored-realistic`, same authorship discipline as
  v2 (`docs/BENCHMARK_METHODOLOGY.md` §3), and authorship diversification
  is explicitly left to M4 — naming this out loud per ROADMAP §0 so it
  isn't quietly pulled forward.

**Implementation decisions (mechanical, no new sign-off needed once the
above is resolved):**

- Writing new case JSON files against the existing schema v2 (or a
  bumped `benchmark_version` if a methodology decision above requires
  one — e.g., the clean-difficulty schema change).
- Extending `reviewer/corpus.py`'s validator for any accepted schema
  change (e.g., allowing `difficulty` on clean cases if approved).
- Storing v3 cases in a clearly separate, clearly versioned location
  (new directory, not mixed into `eval/cases/`) so the frozen v2
  fingerprint never moves.
- Pointing the harness at the new corpus: no new plumbing needed —
  `bin/review-eval --cases DIR` and the whole verify/analyze/compare/
  leaderboard toolchain already work against any schema-valid directory
  (this is exactly the private-holdout design in
  `docs/BENCHMARK_METHODOLOGY.md` §11, reused rather than rebuilt).

## 6. What this brief explicitly does not propose

Per this task's own scope and ROADMAP §9 failure mode 1 (infrastructure
before demand): no routing, no agent-team orchestration, no continuity/
authority engine, no dashboard, no SaaS layer, no M4+ work. Also no new
comparison/reporting mechanism — `reviewer.verify`/`compare`/`analyze`/
`leaderboard` already generalize to any corpus directory and should be
reused unchanged for v3 once cases exist.

## 7. Recommended Fable question

Per ROADMAP §3 ("Fable only for milestone-level decisions, 15–40
minutes, then hand to Sonnet"), this brief surfaces exactly one question
worth that session — the one fork in §5 that is expensive to reverse and
determines whether M3 needs new infrastructure at all:

> **Should M3's state/cache and concurrency cases stay diff-only
> (like v2), or does the benchmark need a lightweight execution-based
> oracle for those two dimensions specifically — given that v2 explicitly
> deferred (not dismissed) execution-based scoring, and that decision is
> expensive to reverse once cases are authored around whichever answer
> is chosen?**

Everything else in §5 (diff-size target, corpus quotas, the
clean-difficulty schema change) is a smaller, reversible-enough call
that can be made inline by whoever authors the taxonomy — recommend
Sonnet remains the implementation default for those, per ROADMAP §3.
