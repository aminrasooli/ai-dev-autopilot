# M3 methodology decision: diff-only vs. execution-based oracle

Status: **APPROVED**. This is the milestone-level methodology decision
referenced by `docs/M3_DESIGN_BRIEF.md` §7 (the single fork worth a
short Fable-tier session per `docs/ROADMAP.md` §3). It answers exactly
one question and nothing else: should M3's state/cache and concurrency
cases stay diff-only like v2, or introduce a lightweight execution-based
oracle for those two dimensions specifically. No files outside this
document were changed by the decision itself; no M3 cases are authored
and no infrastructure exists yet as of this writing.

Grounded in `docs/BENCHMARK_METHODOLOGY.md` §1–2, §6–7, §11a, §15,
`docs/M3_DESIGN_BRIEF.md`, `CURRENT-MILESTONE.md`'s M2 summary, and
`eval/results/M2-PILOT-SCORECARD.md`.

## The load-bearing distinction

The question conflates two different things execution could mean, and
the answer depends entirely on which one:

- **Execution as ground-truth construction** (offline, by the case
  author, once, before a case is ever scored) — never touches the
  harness, never touches the model.
- **Execution as part of scoring** (the harness or the model runs code
  as part of every benchmark invocation) — becomes a permanent
  infrastructure surface every reproducer needs.

Methodology §2 rejected the second kind for v2 ("requires per-language
sandboxed execution infrastructure. Deferred, not dismissed"). It never
addressed the first kind, because v2's ground truth was never uncertain
enough to need it. M3's concurrency/state-cache ambitions change that.

## Option evaluation

**A. Stay fully diff-only.**
Strengths: zero new infra, fully preserves reproducibility/cross-language
neutrality/identity, fastest to start authoring. Weaknesses: ground-truth
confidence for concurrency and cache-invalidation bugs rests entirely on
the author's static reasoning — exactly the two domains where expert
static reasoning about timing/interleaving is documented to be
unreliable. Methodological risk: a mislabeled "definitely racy" or
"definitely clean" concurrency case becomes undetectable noise, the same
failure mode methodology §2 already rejected LLM-judging for, just
relocated from scoring to authoring. Implementation burden: none.
Reproducibility: strongest, unaffected. M4/M5 credibility: neutral —
carries the same self-authored-ground-truth caveat v2 already states,
doesn't add or subtract trust.

**B. Execution-backed ground truth for selected state/cache and
concurrency cases; model input stays diff-only.**
Strengths: fixes exactly A's weakness, for exactly the two domains that
need it, without entering the harness's live path — comparable to a CTF
author validating an exploit before publishing the challenge. Preserves
reproducibility (a stranger reproducing scores never re-runs the
executor — they still just run `bin/review-eval` against a static case
with a fixed `ground_truth` field, identical to every v2 case today),
cross-language neutrality (the scored harness never compiles or runs
anything, for any language), and identity (the model never gets
execution access — still purely "read a diff, output structured
findings"). Weaknesses: real one-time author labor per case, and a race
detector *not* finding a race in N runs never proves there is none —
that limit must be stated honestly, not overclaimed, mirroring how §15
already states other limits. Methodological risk: low, contingent on
staying strictly offline/optional/author-side — risk rises sharply only
if scope creeps toward "the harness executes things." Implementation
burden: small, bounded, no new harness code path, no new submission
format. Reproducibility: unaffected for score reproduction. M4/M5
credibility: net positive — an optional `ground_truth` provenance flag
("execution-validated") is a genuine, cheap trust asset that previews
M4's credibility theme without pulling M4 scope forward.

**C. Split into static-review and execution-assisted tracks.**
Strengths: theoretically the most objective signal in the literature.
Weaknesses: a second permanent benchmark surface — new schema, new
harness path, new submission/reproduction instructions, forever-
maintained per-language toolchains. As the design brief already names,
this "inevitably becomes a sandbox/test-runner platform" (§4 of the
brief), directly the thing methodology §2 deferred and ROADMAP §8/§9
warn against. Reproducibility drops for real: concurrency tests are
famously flaky across OS/scheduler/hardware, so a per-run execution
oracle for races risks measuring harness flakiness, not model
competence — self-undermining for exactly the dimension it targets. If
a future version let the *model* execute code, that's a quiet identity
change into agentic/tool-using review, contradicting methodology §1's
explicit non-goals — far above this milestone's authority to decide.
Implementation burden: largest by far. Reproducibility: weakest. M4/M5
credibility: double-edged — high upside only if flawlessly maintained
forever, high downside (visible retraction, "doesn't reproduce on my
machine") otherwise, and not proportionate to what M2's evidence
actually shows is needed (see below).

## Why B, grounded in the M2 evidence

Sonnet's flat 1.00 recall and Qwen's 0.94–1.00 show detection is
saturated — but that saturation is a case-*design* problem (the
existing 6 cross-file cases hit 1.00 recall even for DeepSeek, meaning
they're shallow file-pair pattern-matching, not hard reasoning), not an
execution-verification gap. Deeper cross-file reasoning, larger
realistic diffs, deeper authorization, and harder clean controls are
all achievable diff-only through careful authoring — none of them need
execution. Concurrency and state/cache are the *only* two dimensions
where the weak link is the author's own confidence in the label, not
the model's diff-reading ability. That's a narrow, precisely-scoped
problem, and B is the narrowly-scoped fix. C would be building a
platform to solve a problem that only exists in 2 of 6 taxonomy
dimensions.

## M3 METHODOLOGY DECISION:

**Option B** — execution-backed ground-truth validation, scoped only to
state/cache and concurrency cases, author-side and offline; model input
and harness scoring remain diff-only for every dimension, no exceptions.

## WHY:

It is the only option that fixes M3's one real methodological weakness
(ground-truth confidence for concurrency/cache, where static author
reasoning is documented-unreliable) without building infrastructure,
without weakening reproducibility for anyone reproducing scores, without
creating cross-language unfairness in the scored harness, and without
changing the benchmark's identity as a diff-in/structured-findings-out
independent reviewer. It is also the most reversible non-trivial choice:
nothing about it is committed to the harness, so a future session can
extend it, formalize it, or quietly stop doing it without unwinding
anything. **This decision requires no ROADMAP gate change** (state/cache
and concurrency are already named in ROADMAP §4's M3 row; nothing about
the milestone table, §5 gates, or timing moves) **and it does not change
the public benchmark's identity** as an independent code reviewer
benchmark — the model-facing contract (diff in, structured findings out,
no tools, no execution) is unchanged from v2.

## DIFF-ONLY / EXECUTION POLICY:

Diff-only for every dimension as seen by the model and the harness,
always. For state/cache and concurrency cases specifically, the case
*author* may run a small, throwaway, per-language, offline script once
to raise confidence that a seeded bug genuinely manifests (or a clean
control genuinely doesn't) before committing the case. That validation
step is never part of `bin/review-eval`, never part of CI, and never
exposed to any model. Record it as an optional case-metadata flag (e.g.,
`ground_truth.execution_validated: true` plus a one-line note of how) —
a schema field addition only, no scoring effect, consistent with
methodology §11a's own versioning table. State plainly in the
taxonomy's methodology notes that a race not reproducing in N runs is
not proof of absence — an honest limitation, not overclaimed.

## REALISTIC DIFF RANGE:

80–250 lines, skewed toward 100–150 for most cases, with 200–250
reserved for a handful of stress cases — large enough to be meaningfully
distinct from v2's 6–35 line ceiling and to bury a defect in real
surrounding noise, but capped well short of whole-PR/whole-repo size so
it doesn't quietly reintroduce the "full project context" non-goal
methodology §1 explicitly excludes, and doesn't blow up local-model
latency/cost disproportionately (DeepSeek and Qwen already showed
multi-second-to-tens-of-seconds latency on 6–35 line diffs in M2).

## TARGET CORPUS SIZE:

An initial tranche of ~35–45 new v3 cases, not "double v2" — each case
at this size/difficulty costs materially more to author (and, for two
dimensions, to validate) than a v2 case did, so start smaller and
revisit after the first batch is authored and run, per ROADMAP §9
failure-mode-1 discipline (no infrastructure/scope ahead of demonstrated
need). Whether v3 physically carries v2's 54 cases forward in the same
directory or supersedes them as a cleanly separate version is a
versioning/implementation detail for the brief, not decided here — the
only fixed constraint is the frozen v2 corpus and its fingerprint are
never mutated.

## CLEAN-CONTROL DIFFICULTY:

Yes, add it. It's a small, backward-compatible schema addition
(fingerprint-only per §11a, not a major-version change on its own), it's
the only way to make "hard clean controls" — an explicit M3 taxonomy
item — machine-distinguishable from v2's original tier, and M2 already
shows the need is real (5 of 14 v2 clean cases produced genuine
false-positive confusion with no way today to say that was intentional).
Requires relaxing `reviewer/corpus.py`'s current validator rule ("clean
cases must not declare a difficulty") — an implementation task, not
decided further here.

## WHAT NOT TO BUILD:

No sandboxed execution environment inside `reviewer/`, no execution as
part of `bin/review-eval` or any scored run, no execution ever exposed
to a model under test, no new submission/reproduction format, no CI
dependency on any per-language runtime, no "execution-assisted track" as
a first-class benchmark surface, no durable `reviewer/exec/`-style
module — the validation scripts are one-time authoring scaffolding, not
a benchmark feature, and should not be committed as product
infrastructure.

## HANDOFF TO SONNET:

Once this recommendation is approved: author the diff-only-authorable
taxonomy items first (larger realistic diffs, deep cross-file reasoning,
deeper authorization, hard clean controls — no execution work needed),
then the concurrency/state-cache cases with their one-time offline
validation step, add the optional clean-difficulty schema field plus the
corresponding `reviewer/corpus.py` validator change, store all v3 cases
in a clearly separate, clearly versioned location, and never touch
`eval/cases/` or its frozen fingerprint. No Fable session is needed for
anything downstream of this decision — the remaining calls (exact case
count per dimension, exact wording) are reversible enough for direct
implementation.

## Provenance amendment (approved)

Applies to the one-time offline validation used in the DIFF-ONLY /
EXECUTION POLICY section above, for state/cache and concurrency cases:

- Validation scripts are **not** product infrastructure. They are not
  added to `reviewer/`, `bin/`, CI, or any part of the public benchmark
  runtime.
- The scripts and their results are **preserved, not deleted** — kept
  outside the public repository as private provenance evidence, so the
  validation work behind a case's ground truth remains inspectable
  later even though it never ships as code.
- Public case metadata may record:
  - `execution_validated: true`
  - a concise validation-method note (what was run, in what language,
    what it showed)
  - where practical, a SHA-256 of the preserved validation artifact, so
    a later audit can confirm a specific piece of private evidence
    matches what the public case claims, without the artifact itself
    being public
- The private storage location is never named in the public repository.
- Whether, and how, this provenance ever becomes externally publishable
  is an **M4 decision** (`docs/ROADMAP.md` §4: "Credibility and
  provenance"), not decided or pre-empted here.
