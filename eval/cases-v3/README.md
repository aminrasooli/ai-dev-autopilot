# v3 corpus

M3 hard-benchmark corpus (`docs/ROADMAP.md` §4). All cases live in the
single flat directory [`cases/`](cases/) — the same layout every other
corpus uses, so the whole toolchain runs against it unchanged:

```sh
bin/review-corpus --cases eval/cases-v3/cases
bin/review-eval --cases eval/cases-v3/cases --backend fake
```

This directory is a clearly separate, clearly versioned location — the
frozen v2 corpus at `../cases/` (fingerprint
`f31d46310988f61c4534344ad05a52a4385fd15159126a0be85aad532f045690`) is
never mixed into it and never mutated by it. Scope and the diff-only
vs. execution-oracle methodology fork are decided in
[`../../docs/M3_METHODOLOGY_DECISION.md`](../../docs/M3_METHODOLOGY_DECISION.md);
the taxonomy is in
[`../../docs/M3_DESIGN_BRIEF.md`](../../docs/M3_DESIGN_BRIEF.md).

> **Read [`ERRATA.md`](ERRATA.md) before citing this corpus or any M3
> number.** Its answer key is human-reviewed *with documented errata*,
> not error-free: one case has invalid ground truth and two more rest on
> evidence the reviewer never sees. The cases are frozen, so the
> corrections live in that file rather than in the case JSON.

## Freeze — M3 Hard Benchmark v3 (2026-08-23)

This corpus is **frozen** exactly as merged to `main` by PR #19, merge
commit `79f4032cc11eddf6d13d2424a6720e1031b2ce95`:

```
corpus:      eval/cases-v3/cases/  (37 cases — 29 defective / 8 clean)
fingerprint: 81daa0b7a48259184a91c48ab1dcf17c9d3ed4902fa891b5895db0f29fd79790
```

The fingerprint is computed by
`bin/review-corpus --cases eval/cases-v3/cases --json` (methodology:
`docs/M3_METHODOLOGY_DECISION.md`). The corpus was authored and
hardened **without observing any Claude Sonnet 5, Qwen 3.6 27B, or
DeepSeek R1 14B result against v3** — no target model saw any v3 case
before this freeze.

**Immutable after freeze.** No case may be edited, deleted, replaced,
or re-tuned in response to model results — including changing a clean
case because a model false-positives on it, or a defective case because
a model misses it — and the frozen corpus's history is never rewritten.
If a factual corpus error is ever discovered, the correction must be
disclosed and made under a **new** fingerprint (a new benchmark
identity per `docs/BENCHMARK_METHODOLOGY.md` §11a), with new
experiments; results against this fingerprint are never retro-edited.

## Preregistered measurement contract (X17–X19)

Defined before any target-model result exists; uses only the harness's
existing scoring semantics (`reviewer/evaluate.py` report summary — no
new scoring system). Per model: **3 runs × 37 cases = 111 observations**,
of which **29 × 3 = 87 defective observations** and **8 × 3 = 24 clean
observations**. The scorecard reports, per model:

- **Detection**: detected x/87 and %; missed x/87 and %.
- **Clean false positives**: x/24 and % — the raw x/24 count is always
  shown, because at n=24 a single clean-observation flip moves the
  rate by ~4 points.
- **Category correctness** and **severity correctness**: raw count + rate.
- **Errors**: technical execution errors stay visible as errors (the
  existing summary's `errors` field), never silently converted into
  quality misses.
- **Run-to-run consistency**: the existing report `consistency` block
  (always/sometimes/never detected, clean cases ever-false-positive,
  cases with errors).
- **Latency**: existing mean/min/max. Caveat, fixed in advance: hosted
  Sonnet latency and local RTX-6000 Ollama latency are different
  execution environments and are **not** an apples-to-apples
  infrastructure speed comparison.
- **Tokens and cost**, where honestly measurable: Sonnet's external
  cost is measured (`claude --output-format json`); for local models,
  "no external model API charge (local compute time is not free)" —
  never "free". Local wall-clock execution time reported where
  honestly measurable.

Subgroup analysis uses only the **pre-existing** dimensions: the
corpus's `difficulty` values (subtle / cross-file / moderate), its
ground-truth categories, and the taxonomy clusters listed in this
README. All sufficiently represented predefined groups are reported —
not a post-hoc selection of interesting ones. No leaderboard language,
no launch-grade claims. M2 and M3 are different corpora: a lower M3
score is not "the model got worse"; the preregistered question is
whether M3 reduced detection saturation and exposed differentiation.

Preregistered output paths (`eval/results/`, must not pre-exist;
checkpoints resume a genuinely interrupted run only, per the existing
checkpoint methodology):

```
claude-sonnet-5-m3hard-3runs.json   (+ .checkpoint.json)   X17
qwen3.6-27b-m3hard-3runs.json       (+ .checkpoint.json)   X18
deepseek-r1-14b-m3hard-3runs.json   (+ .checkpoint.json)   X19
```

## Schema note

All cases carry `benchmark_version: 2`: the schema additions M3 needed
(optional `difficulty` on clean cases, optional
`ground_truth.execution_validated` provenance) are non-scoring,
fingerprint-only changes per `docs/BENCHMARK_METHODOLOGY.md` §11a, so
no major schema version bump was warranted — "v3" names this corpus,
not a case-schema version.

## Tranche history

- **Tranche 1** — cases `t1-01` … `t1-15` (15 cases), merged in PR #18.
  Originally authored under `tranche-1/`; moved unchanged into
  `cases/` when tranche 2 landed, so the final corpus is one directory.
- **Tranche 2** — cases `t2-01` … `t2-22` (22 cases): fills the
  dimensions tranche 1 left thin (deeper authorization, state/cache,
  beyond-textbook concurrency, more hard clean controls) and broadens
  language coverage (java, javascript, go, rust, sql, typescript).

## Taxonomy coverage (both tranches)

- **Larger realistic diffs**: multi-hunk, multi-file diffs in the
  80–250 line envelope with one seeded defect buried among legitimate
  surrounding changes (`t1-01`–`t1-03`, `t2-01`–`t2-04`).
- **Deep cross-file reasoning**: the defect is only establishable by
  combining behavior across files — contracts, ordering, config, and
  call sites, not rename/mismatch pattern-matching (`t1-04`–`t1-06`,
  `t1-15`, `t2-05`–`t2-08`).
- **Deeper authorization**: correct at the point of the diff, wrong
  only in combination with a caller, config, ordering, or staleness
  elsewhere (`t1-07`, `t1-08`, `t2-09`–`t2-11`).
- **State/cache**: invalidation ordering, negative caching, mutable
  cached values, key aliasing, read-after-write (`t1-14`, `t1-15`,
  `t2-12`–`t2-14`).
- **Concurrency beyond textbook idioms**: multi-step interleavings,
  lifecycle/cancellation ordering, pool starvation (`t1-12`, `t1-13`,
  `t2-15`–`t2-17`).
- **Hard clean controls**: genuinely suspicious-looking but correct
  diffs, each carrying the (schema-optional) `difficulty` field
  (`t1-09`–`t1-11`, `t2-18`–`t2-22`).

## Offline execution validation

Ground truth for the concurrency and state/cache cases (`t1-12`–`t1-15`,
`t2-12`–`t2-17`) carries `ground_truth.execution_validated: true` plus a
`validation_note` and, where practical, a SHA-256 of the validation
artifact: a one-time, offline, author-side reproduction raised
confidence that each seeded bug (or seeded non-bug) actually manifests,
per the approved methodology. That validation never entered this
harness, CI, or any model-facing content; scripts and raw output are
preserved as private provenance outside this repository
(`docs/M3_METHODOLOGY_DECISION.md`, provenance amendment). A race not
reproducing in N runs is not proof of absence — stated once here, not
overclaimed per case.

## Status

`pilot`, `authored-realistic`, 100% `claude`-authored — same authorship
discipline and self-authorship caveat as v2
(`docs/BENCHMARK_METHODOLOGY.md` §10). Authorship diversification is M4
scope, not pulled forward here.
