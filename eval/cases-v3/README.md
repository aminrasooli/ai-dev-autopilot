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
