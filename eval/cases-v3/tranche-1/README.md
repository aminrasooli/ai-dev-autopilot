# v3 tranche-1

M3 hard-benchmark corpus (`docs/ROADMAP.md` §4), first tranche. A
clearly separate, clearly versioned location — never mixed into the
frozen v2 corpus at `../../cases/` (fingerprint
`f31d46310988f61c4534344ad05a52a4385fd15159126a0be85aad532f045690`,
untouched by this directory's existence). Scope and the diff-only vs.
execution-oracle methodology fork are decided in
[`../../../docs/M3_METHODOLOGY_DECISION.md`](../../../docs/M3_METHODOLOGY_DECISION.md);
the taxonomy this tranche implements is in
[`../../../docs/M3_DESIGN_BRIEF.md`](../../../docs/M3_DESIGN_BRIEF.md).

15 cases, `benchmark_version: 2` (the schema additions this tranche
needed — optional `difficulty` on clean cases, optional
`ground_truth.execution_validated` provenance — are non-scoring
fingerprint-only changes per `docs/BENCHMARK_METHODOLOGY.md` §11a, so
no major-version bump was needed; "v3" names this corpus tranche, not
a case-schema major version). Run it exactly like any other corpus
directory:

```sh
bin/review-corpus --cases eval/cases-v3/tranche-1
bin/review-eval --cases eval/cases-v3/tranche-1 --backend fake
```

## Taxonomy coverage

- **Larger realistic diffs** (`t1-01`–`t1-03`): 80–250 lines, one
  seeded defect buried among legitimate surrounding changes.
- **Deep cross-file reasoning** (`t1-04`–`t1-06`, `t1-15`): the defect
  requires combining behavior across files that are not an obvious
  rename/mismatch pair.
- **Deeper authorization** (`t1-07`, `t1-08`): correct at the point of
  the diff, wrong only combined with ordering/caching/config
  elsewhere.
- **Hard clean controls** (`t1-09`–`t1-11`): genuinely
  suspicious-looking, correct diffs; `difficulty` is set on these
  (schema addition, see above).
- **Concurrency / state-cache** (`t1-12`–`t1-15`): ground truth for
  these four carries `ground_truth.execution_validated: true` plus a
  `validation_note` — a one-time, offline, author-side simulation
  raised confidence the seeded bug (or seeded non-bug) actually
  manifests, per the approved methodology. That validation never
  entered this harness, CI, or any model-facing content; scripts and
  raw output are preserved as private provenance outside this
  repository, not published (`docs/M3_METHODOLOGY_DECISION.md`,
  provenance amendment). A race not reproducing in N runs is not proof
  of absence — stated once here for all four, not overclaimed per
  case.

## Status

`pilot`, `authored-realistic`, 100% `claude`-authored — same
authorship discipline and self-authorship caveat as v2
(`docs/BENCHMARK_METHODOLOGY.md` §10). Authorship diversification is
M4 scope, not pulled forward here.
