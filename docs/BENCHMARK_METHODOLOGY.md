# Local Reviewer Benchmark — Methodology (v2, pilot)

This document defines how the reviewer benchmark in `eval/` is constructed,
scored, versioned and limited. It is the authority the corpus and the
harness are held to; when the code and this document disagree, one of them
has a bug.

Status: **v2 pilot**. The corpus is ~50 cases and self-authored. Results
from it are evidence, not rankings. See [Limitations](#limitations).

## 1. Purpose

One question, deliberately narrow: **how well does a given model, acting as
an independent reviewer under a fixed contract, detect seeded defects in
small diffs — and how often does it invent problems in clean ones?**

The benchmark exists to compare *reviewers* (cloud models, local
open-weight models through Ollama, and future backends) on identical
input, with deterministic scoring and honestly measured cost. It is the
first standalone measurement primitive of this repository: useful on its
own, and a prerequisite for any future competence-based selection of
models (see `docs/NORTH_STAR.md` — a destination, not this document's
scope).

### What is measured

- Defect detection on small unified diffs (single- and multi-file)
- False-positive behaviour on clean diffs
- Classification quality: category and severity against ground truth
- Consistency across repeated runs of the same case
- Latency, token usage where reported, and honestly measurable cost

### What is explicitly NOT measured

- Whole-repository review (the reviewer sees only the diff and the shared
  prompt — no project context, no file system, no tools)
- Fix quality, patch generation, or comment helpfulness to a human
- Interactive/agentic review workflows
- General coding or reasoning ability
- Anything about models the harness cannot run under identical semantics

## 2. Prior work, and what we took from it

We studied current code-review evaluation methodology and borrowed
selectively. What we adopted, and what we deliberately did differently:

**Adopted**

- *Structured ground truth with hit-based scoring* (SWR-Bench,
  [arXiv:2509.01494](https://arxiv.org/abs/2509.01494)): every defect case
  carries machine-checkable expected category and severity; scoring is a
  deterministic function of the reviewer's structured output. We go one
  step further than most: no LLM-as-judge anywhere in the scoring path.
  Judge models add ~90%-agreement noise and prompt-sensitivity that a
  fixed vocabulary plus strict JSON contract removes entirely — at the
  admitted price of a coarser notion of "correct" (see §6).
- *Precision/recall framing with clean controls* (Martian Code Review
  Bench, [codereview.withmartian.com](https://codereview.withmartian.com/)):
  false-positive behaviour is measured on genuinely clean diffs, not
  inferred. Martian's offline track — 50 curated PRs — also calibrates
  what a credible *pilot* scale looks like; its leaderboard churn (several
  vendors have claimed #1 at different times) is direct evidence that
  small score deltas are not stable rankings, which informs how we report.
- *Open pipeline* (Martian): cases, scoring code, prompts and raw reports
  are all in this public repository; anyone can re-run and audit.
- *Contamination realism* (SWE-MERA,
  [arXiv:2507.11059](https://arxiv.org/abs/2507.11059); CodeReviewQA,
  [arXiv:2503.16167](https://arxiv.org/pdf/2503.16167)): static public
  benchmarks leak into training data quickly, and cases mined from popular
  repositories may already be memorized. We adopt versioned corpora,
  machine-readable provenance, and a private holdout design (§10–11).
- *Repeated-run aggregation* (SWR-Bench's multi-review aggregation;
  standard practice for nondeterministic systems): single runs of a
  sampling model are anecdotes. The harness supports N independent runs
  per case and reports consistency, not just point scores (§8). Our own
  Phase 1 data forced this: the same Sonnet 5 run produced 0/5 false
  positives once and 1/5 on a rerun, same corpus, same prompt.

**Rejected (for now), with reasons**

- *LLM-as-judge scoring* (DeepCRCEval, SWR-Bench): reintroduces the
  nondeterminism and bias the fixed contract exists to remove. Cost:
  our "category correct" is stricter and blunter than semantic judgment.
- *Execution-based oracles* (Code Review Agent Benchmark,
  [arXiv:2603.23448](https://arxiv.org/html/2603.23448v2) — apply the
  review, run the tests): the most objective signal in the literature,
  but requires per-language sandboxed execution infrastructure. Deferred,
  not dismissed.
- *Full-project context* (SWR-Bench's PR-centric design): deliberately
  out of scope for v2. Diff-only review is a smaller, reproducible
  question; cross-file cases (§5) restore a bounded slice of it.
- *Text-similarity metrics* (BLEU and friends): rejected outright, in
  line with the entire recent literature.

## 3. Corpus composition: five provenance classes

Every case declares `provenance.type` — one of five classes, each present
for a different reason:

1. **`seeded-synthetic`** — a defect deliberately written into a plausible
   small diff. Cheap, precise ground truth, contamination-resistant
   (never published before this repo), but stylized: real bugs are
   rarely this clean. All 20 v1 cases and most v2 pilot cases are this.
2. **`authored-realistic`** — synthetic, but modeled on a real bug pattern
   the author has seen in production code, with realistic surrounding
   noise. Harder than seeded; same authorship caveat.
3. **`mined-real-fix`** — reconstructed from a real public bug-fix commit
   (reversed: the diff re-introduces the fixed bug), with
   `provenance.reference` recording the source where licensing permits.
   Most realistic; highest contamination risk (the fix is public and
   likely in training data); planned, none in the pilot yet.

   The ingestion pipeline for this class, defined before any mining
   happens so cases can't be laundered in casually:

   - **Licensing**: only fixes from repositories under licenses
     permitting redistribution of excerpts (MIT/BSD/Apache-2.0 and
     similar); `provenance.reference` records the commit URL; the
     license is checked per source repository, not assumed.
   - **Leakage prevention**: the case carries the *reversed* diff only —
     never the fix commit message, PR discussion, CVE text, or issue
     title, all of which frequently state the answer outright.
     Identifiers may be renamed when the original names give the defect
     away (`fix_race_in_flush` tells the reviewer what to find).
   - **Selection discipline**: no mass scraping. Each mined case is
     hand-verified to be self-contained at diff scale, and the validator
     enforces the same schema, secret and privacy rules as authored
     cases.
   - **Honest scoring context**: mined cases are the most likely to be
     memorized (SWE-MERA's core finding), so per-provenance score slices
     are reported — a model that beats its seeded-synthetic score only
     on mined cases is exhibiting recall, not review.
4. **`mutation`** — mechanical transformation of a clean case (operator
   flip, boundary shift). Useful for scale and for probing consistency;
   risk of near-duplicate padding, so the validator flags duplicates and
   mutations are capped as a fraction of the corpus.
5. **Clean controls** (`defect: false`, any provenance) — diffs with no
   defect, in the same languages and styles as the defective ones. These
   make precision measurable. Target: ≥20% of the corpus.

A sixth tier — **private holdout** cases — uses the same schema but never
appears in this repository (§11).

## 4. Case schema v2

One JSON file per case in `eval/cases/`. Machine-validated by
`python3 -m reviewer.corpus` (§12). Fields:

| field | type | required | meaning |
|---|---|---|---|
| `benchmark_version` | int | yes | `2` for this corpus |
| `id` | string | yes | unique, kebab-case, filename stem |
| `title` | string | yes | one human-readable line |
| `language` | string | yes | from the language enum (§5) |
| `status` | string | yes | `pilot` or `stable` |
| `diff` | string or list | yes | unified diff; list-of-lines joins with `\n` |
| `affected_files` | list | yes | file paths appearing in the diff |
| `provenance` | object | yes | `{type, author_family, reference?}` |
| `ground_truth` | object | yes | see below |
| `tags` | list | no | free-form, e.g. `["cross-file"]` |

`provenance.author_family` ∈ `claude`, `qwen`, `deepseek`, `human`,
`mixed`, `other` — who/what authored the case, machine-readable so
self-authorship bias (§10) can be sliced in analysis. `provenance.reference`
is required for `mined-real-fix` (commit URL or equivalent) and must
never point at private infrastructure.

**M4 provenance fields (`docs/M4_DESIGN_BRIEF.md`, docs/ROADMAP.md §4),
all optional and fingerprint-only per §11a** — existing v2/v3 cases carry
none of them and remain valid unchanged:

| field | type | required when | meaning |
|---|---|---|---|
| `source_repository` | string | `provenance.type = mined-real-fix` | the repository the fix was mined from |
| `source_commit` | string | `provenance.type = mined-real-fix` | the specific bug-fix commit |
| `source_license` | string | `provenance.type = mined-real-fix` | the source repository's license at the commit used |
| `transformation` | enum: `verbatim`, `transformed`, `synthetic-reconstruction` | `provenance.type = mined-real-fix`; rejected otherwise | how much of the original code survives into the case |
| `author_model` | string | never required | exact model identifier (e.g. `qwen3.6:27b`), refining the coarse `author_family` bucket; must agree with `author_family` when that family names a model lineage |
| `human_authored` | bool | `author_family = human` (must be explicit) | `true` only when a human wrote the case content itself; `false` marks a human-*reviewed* case (concept/decision by a human, mechanical formatting by tooling) — never inferred, always stated |
| `provenance_notes` | string | never required | free-form provenance context that doesn't fit another field |

`human_authored` is the schema's answer to "human-written vs.
human-reviewed" (M4-C): a case can only claim to be human-written if this
field is explicitly `true`, and the validator refuses to leave it
unstated for any `author_family: human` case — silence is not allowed to
read as a claim.

**Contradictions the validator rejects outright**, because each would
let a published claim be false while the corpus validated clean:

- `human_authored: true` together with an `author_model`. A case a model
  wrote is human-*reviewed* at best; the two claims cannot both hold.
- `author_family` disagreeing with `author_model` — e.g. family `qwen`
  naming `claude-sonnet-5`. Families that name a model lineage
  (`claude`, `qwen`, `deepseek`) must match the model string. `mixed`
  and `other` carry no such rule, because ambiguity is what they mean:
  `mixed` plus a `provenance_notes` line saying who changed what is the
  correct label when a case passed through more than one author.
- `transformation: verbatim` or `transformed` under a `source_license`
  outside the permissive allowlist (MIT, BSD-2/3-Clause, Apache-2.0,
  ISC, 0BSD, Unlicense — `reviewer.corpus.PERMISSIVE_LICENSES`, shared
  with the real-bug queue so the two cannot drift). An unrecognized
  license string is treated as non-permissive, not assumed benign.
  `synthetic-reconstruction` is exempt: it derives no code.
- A `source_commit` that isn't a 7-40 character hex sha. A commit nobody
  can look up is not provenance.
- `source_repository` or `source_commit` with no `source_license` — a
  source attribution the project cannot stand behind.

`ground_truth` for defective cases:
`{defect: true, category, severity: [min, max], explanation}` — category
from the taxonomy, severity an ordered pair from the scale, explanation a
non-empty human sentence. Clean cases: `{defect: false, explanation}` and
the validator rejects any contradictory defect fields.

v1→v2: the 20 Phase 1 cases were migrated in place (fields added; diffs
and ground truth unchanged), so v1 results remain comparable at the
case level, though not at the corpus level. One migrated case
(`10-missing-regression-test`) was later removed by human ground-truth
review: its label depended on unstated authorial intent (a boundary fix
either "needs a test" or "is a regression", undecidable from the diff
alone) and no accepted-category alternative could make that ambiguity
disappear rather than merely score around it. Historical v1 reports
that included it remain unmodified, per the versioning policy below —
they document what was measured against the corpus as it existed then.

## 5. Taxonomies

**Severity** (unchanged from v1): `low`, `medium`, `high`, `critical`.
Ground truth is a range, because reasonable reviewers disagree by one
step; a range that spans the whole scale would be vacuous and the
validator warns on it.

**Languages** (pilot enum): `python`, `shell`, `sql`, `javascript`,
`typescript`, `go`, `java`, `rust`, `config`, `docs`. The last two cover
dependency manifests and documentation-only diffs. Additions require a
methodology PR, not just a case PR.

**Categories** — v1's 14 plus 9 added for v2:

v1: `logic-error`, `missing-validation`, `shell-quoting`,
`command-injection`, `path-traversal`, `sensitive-logging`,
`insecure-network`, `dependency-risk`, `test-gap`, `misleading-test`,
`destructive-operation`, `permission-widening`, `secret-exposure`,
`other`.

v2 additions: `sql-injection`, `auth-bypass` (authentication and
authorization mistakes), `concurrency` (races, unsynchronized shared
state, TOCTOU), `resource-leak` (lifecycle: unclosed handles, unbounded
growth, missing cleanup), `api-misuse` (violating a library/API contract),
`error-handling` (swallowed, shadowed or mis-propagated errors),
`unsafe-default` (a default value or fallback that is wrong or dangerous),
`data-corruption` (silent wrong data: truncation, precision loss, lossy
migration), `contract-mismatch` (cross-file disagreement: caller/callee,
config/code, schema/model).

Tradeoff, stated: 23 categories make "category correct" a harder, more
informative signal than 14 did, and make v2 category scores
*not comparable* to v1 scores — the prompt vocabulary changed for every
backend equally. The whole corpus is version-stamped for exactly this
reason.

`test-gap` remains in the prompt vocabulary but, since the removal of
`10-missing-regression-test` (§4), no case's ground truth uses it as a
primary category. A model reporting `test-gap` can therefore only ever
score as a false positive (clean case) or an unmatched finding (defective
case) — never as correct. This is a deliberate consequence of the
ground-truth decision, not an oversight: real evidence
(`eval/results/provisional/`) showed reviewers applying `test-gap` to
clean diffs literally, and removing the one case that rewarded the same
behaviour as a genuine defect resolves that tension without touching the
vocabulary a reviewer is prompted with.

## 6. Scoring

Unchanged in kind from v1, per run:

- **detected** — defect case, ≥1 finding of any category
- **miss** — defect case, zero findings
- **false positive** — clean case, ≥1 finding
- **category correct** — detected, and some finding uses the ground-truth
  category
- **severity correct** — a category-correct finding's severity falls in
  the ground-truth range
- **error** — the backend raised (unavailable / malformed output / timeout);
  counted separately, never as a pass or a miss

Known bluntness, accepted deliberately: a reviewer that finds the real
bug but files it under a neighbouring category scores detected-but-
category-wrong; a semantically perfect finding phrased outside the JSON
contract scores as an error. Both are visible in the raw reports, and the
strictness is the price of scoring without a judge model. The oracle
backend (`--backend fake`) replays ground truth through the full pipeline
and must score 100% — that is CI's proof that the harness itself is sound.

## 7. Prompt equivalence and model isolation

- **One prompt.** Every backend receives byte-identical prompt text for a
  given case (`reviewer/prompt.py`). No per-model tuning, system-prompt
  adjustments, or output-format concessions — if a model needs a
  different prompt to perform, that IS a result, not a nuisance to
  engineer away.
- **No context leakage.** Backends must not expose the repository, the
  machine, or any conversation state to the model. The Claude backend
  runs `claude -p` in a disposable directory with a replaced system
  prompt, tools disabled and settings sources emptied; the Ollama backend
  speaks only to a loopback endpoint. New backends must document their
  isolation before results are accepted.
- **Local stays local.** The Ollama backend refuses non-loopback
  endpoints at construction and has no fallback path to any remote
  service. The precise privacy claim is "local review stays local" —
  never "the whole workflow is local."
- **Provider-default sampling.** The harness sets no temperature, top-p,
  seed or other sampling parameters on any backend — every model runs
  with its provider's defaults, so there are no hidden per-model knobs to
  tune a score with. Any submitted result whose runtime deviated from
  provider defaults must say so in its metadata (see `eval/SUBMIT.md`),
  and results with undisclosed sampling settings are not comparable.

## 8. Repeated runs and statistics

Sampling models are nondeterministic; one run per case is an anecdote.
The harness's `--runs N` executes each case N independent times (fresh
call, no shared state) and preserves **every** raw run.

Reported at three levels:

1. **Run level** — the v1 counters (detected, missed, false positives,
   category/severity correct, errors) computed over all N×cases runs.
   With `--runs 1` this is exactly the v1 report, unchanged.
2. **Case level** — per case: runs detected, runs with false positives,
   runs errored; a clean case that alarms in 1 of 3 runs is reported as
   exactly that, never flattened into a binary.
3. **Consistency level** — corpus-wide: cases always/sometimes/never
   detected; clean cases that ever produced a false positive; latency
   mean and min–max; cost summed across all runs.

What we deliberately do NOT report: p-values or significance claims.
At pilot scale (~50 cases, N≤5 runs) they would be theater. The honest
statistical claim available at this scale is descriptive: point rates,
ranges, and consistency fractions, with the run count always printed
beside them. Formal uncertainty quantification becomes worth doing when
the corpus reaches several hundred cases.

## 9. Timeouts, errors and progress

- Every model call has a finite timeout (Ollama default 300s, Claude
  default 600s, both configurable). A timeout is a per-run **error**,
  typed and recorded — never a hang, never a miss.
- A failed run does not abort the benchmark: the harness records the
  error and continues to the next run/case. External-service failures are
  thereby visible as errors, and are never conflated with model quality.
- There are no automatic retries anywhere in the harness. A paid call
  that failed is a recorded failure, not a silent re-spend.
- Progress is streamed to stderr per run — case index, run number,
  elapsed wall-clock, outcome — so a multi-hour real-model run is never
  indistinguishable from a hang.

## 10. Contamination and self-authorship

Two distinct risks, honestly stated:

**Training contamination.** Anything in this public repository —
including every pilot case — may enter future model training sets. From
then on, high scores may partly measure memorization. Mitigations:
corpus versioning (results always name the corpus version), timestamped
provenance, planned periodic addition of fresh cases, and the private
holdout (§11) as the uncontaminated reference. Following SWE-MERA's
evidence, we treat any public static corpus as contaminated-eventually by
default.

**Self-authorship.** The pilot corpus was authored with Claude's
assistance, and Claude models are among the systems evaluated. A model
family may be systematically better at finding the kinds of bugs it
tends to write, or bugs written in its own style. This is a real
credibility problem and no amount of process fully removes it.
Mitigations, in order of value:

1. `provenance.author_family` on every case, so scores can be sliced by
   authorship and the bias measured rather than assumed away
2. A published plan to diversify: mined real fixes, human-authored cases,
   cases authored by other model families (e.g. Qwen), and the community
   contribution path (§13)
3. The private holdout, which can be authored by humans or other models
   without ever entering this repo
4. Plain labeling: **this benchmark is not independent.** We built it, we
   run it, and we say so. Results are reproducible evidence, not an
   impartial ranking.

## 11. Private holdout design

Public static corpora decay (§10), so the benchmark is designed to run
against cases it has never published:

- The harness takes `--cases DIR` — any directory of schema-valid case
  files. Nothing in the public repo needs to know a holdout's contents;
  the runner, validator, scoring and reports work identically on it.
- The holdout lives **outside this repository** — never in git history,
  PRs, issues, or docs. Proposed location on the maintainer's machine:
  a sibling project directory (e.g. `~/projects/reviewer-benchmark-holdout/`,
  registered per the machine's project registry conventions), plain
  case-JSON files, no secrets, no machine topology. Creating and
  registering it is a human step, deliberately not automated here.
- Published holdout results must state: corpus name, case count,
  language/category distribution (aggregate only), harness commit, and
  that the cases are unpublished. Individual holdout cases are never
  quoted in public results.
- Rotation: once a holdout case is ever published (e.g. promoted into the
  public corpus), it is holdout no longer and is marked as such.

### Holdout operating spec

- **Storage class**: a private repository or a private project directory
  outside the public tree — never a subdirectory of this repo, and never
  referenced by an absolute path in public documentation. Public docs use
  `--cases <path-to-private-corpus>` and nothing more.
- **Layout**: identical to `eval/cases/` — one schema-v2 JSON per case,
  validated by the same `bin/review-corpus`. No holdout-only fields; a
  holdout case must be promotable into the public corpus unchanged.
- **Versioning**: the holdout carries its own `benchmark_version` and is
  identified in results solely by `corpus.sha256` plus a human-readable
  name (e.g. "holdout-a"). Two holdout runs are comparable only if the
  fingerprints match.
- **Authorship**: holdout cases should skew *away* from the public
  corpus's authorship — human-written and other-model-written cases
  first, since the holdout's purpose is to detect exactly the
  memorization and self-authorship effects the public corpus cannot.
- **Backups**: the holdout is the one corpus that cannot be regenerated
  from git history; it needs its own backup, and that backup must not be
  a public remote.
- **Rotation triggers**: publish nothing case-specific, but rotate (add
  fresh cases and retire old ones) if aggregate holdout scores start
  tracking public-corpus scores too closely, if any case is quoted
  publicly, or on a fixed cadence once the benchmark has outside users.
- **Publishing holdout results**: aggregate numbers only — counts,
  rates, per-difficulty and per-category splits, corpus fingerprint and
  case count. Never a case id, diff, title or ground-truth explanation.
- **Residual leakage**: a determined reader can still infer corpus
  *shape* from aggregate category/difficulty distributions, and any
  model provider that receives holdout diffs at inference time has seen
  them. The holdout reduces contamination; it does not eliminate it, and
  a provider-side retention policy is outside our control.

## 11a. Benchmark versioning

Results are only comparable within a version. Every report already
records `corpus.benchmark_version` and `corpus.sha256`; the version
tells you *whether* two runs are comparable, the fingerprint tells you
whether they ran on the identical bytes.

| change | version effect |
|---|---|
| case added or removed | fingerprint changes; version unchanged if scoring semantics are untouched — but cross-run comparisons must say the corpus differed |
| clean/defective label flipped | **major**: previously-correct results become wrong |
| primary category changed | **major** |
| accepted alternative added or removed | **major** — it redefines category correctness |
| severity range changed | **major** |
| scoring algorithm changed | **major** |
| review prompt contract changed | **major** — every backend's input changed |
| schema field added, no scoring effect | fingerprint only |
| difficulty or provenance metadata corrected | fingerprint only |

A major change increments `benchmark_version` and invalidates
cross-version leaderboard rows; historical reports are never rewritten
to match a new version — they keep the version and fingerprint they
actually ran against, and stale rows are labelled, not deleted.

## 11b. Result trust levels

Submissions are not all equally verifiable, and pretending otherwise
would be the easiest way to make the leaderboard worthless:

- **L0 — self-reported**: a valid report with complete metadata. Taken
  at face value; labelled as such.
- **L1 — reproducible**: L0 plus a corpus fingerprint matching a
  published corpus, a harness commit, and a reproduction command that a
  reader could run.
- **L2 — reproduced**: someone other than the submitter re-ran L1 and
  got materially consistent results — "consistent" meaning inside the
  submission's own run-to-run spread, since exact equality from
  nondeterministic models is not a sane bar.
- **L3 — holdout-confirmed**: additionally run against a private holdout,
  aggregate scores only.

No cryptographic attestation. A determined faker can produce a
plausible L0/L1 report; L2 is the first level that costs an independent
party real work, which is why it is the level that matters.

## 12. Validation

`python3 -m reviewer.corpus [--cases DIR] [--summary]` validates the
corpus and prints a distribution report. It enforces: parseable JSON,
unique IDs matching filenames, schema-v2 required fields, enum membership
(language, category, severity, provenance, status), ordered severity
ranges, defect/clean ground-truth consistency, affected-files consistency
with the diff, near-duplicate detection (normalized diff hashing), no
secret-shaped strings, no `/home/` paths or machine-specific content.
CI runs it offline — no GPU, no Ollama, no paid API, no network.

## 13. Contribution and result submission

The benchmark is an open artifact inside ai-dev-autopilot: cases, harness,
scoring and raw reports are public, and third parties are meant to run it
and submit results. `eval/README.md` covers running it; `eval/SUBMIT.md`
defines the result-submission format (exact model identifier,
quantization for local models, hardware, harness commit, corpus version,
run count, full machine-readable report, reproduction command). Case
contributions follow the same PR rules as the rest of the repository,
plus schema validation and provenance declaration.

## 14. Traction gate (precommitment)

Before any expansion toward the North Star architecture (routing,
competence ledgers, multi-seat orchestration), the benchmark itself must
earn attention. Proposed gate, ~3 weeks after public launch:

- ~100+ GitHub stars from real accounts
- ≥2 substantive issues or PRs from people outside the project
- ≥1 independent person runs the harness on another model/runtime and
  submits a reproducible result

Critique of our own gate, recorded now so it can't be quietly reweighted
later: star counts are gameable and mostly measure marketing reach, not
usefulness; three weeks is arbitrary; and a single external reproduction
is worth more than the other two signals combined, because it is the only
one that exercises the actual artifact. If the gate is missed, the answer
is a better benchmark or better distribution — not building the control
plane anyway.

## 15. Limitations

Stated plainly, current as of the v2 pilot:

1. **Self-authored** — see §10; not an independent benchmark.
2. **Small** — ~50 cases; differences of a few cases are noise. Phase 1
   already demonstrated run-to-run variance larger than some inter-model
   gaps.
3. **Synthetic** — no mined-real-fix cases yet; seeded bugs are cleaner
   than real ones and may be systematically easier.
4. **Diff-only** — reviewers see no project context; models that excel
   with full-repo context are underestimated by design.
5. **Category strictness** — deterministic vocabulary scoring counts
   near-miss classifications as wrong (§6).
6. **One machine** — local-model latency/throughput numbers reflect one
   GPU (RTX 6000, 24GB) and one quantization; they are not general.
7. **Public since birth** — every public case must be presumed to enter
   training data eventually; longitudinal comparisons need the holdout.
8. **Two backends measured so far** — Qwen3.6:27b and Claude Sonnet 5;
   Codex exists as a backend but is not part of current runs.

None of these are footnotes; several (1, 2, 3) are the difference between
"evidence" and "leaderboard truth." Reports generated by this harness
should link here.
