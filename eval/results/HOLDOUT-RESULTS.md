# Private holdout results

Status: **scaffold, still empty — deliberately.** A private holdout now
exists outside this repository and has been run once
(`docs/M4_PROVENANCE_GAP_AUDIT.md` §"Private holdout"). This file stays
empty regardless: under `docs/BENCHMARK_METHODOLOGY.md` §11 a row is
published only when one is explicitly approved for publication, and
none has been. Its emptiness is now a publishing decision, not an
absence of data.

## What may go in this file, once a row is approved for publication

Per `docs/BENCHMARK_METHODOLOGY.md` §11 ("Publishing holdout results"):
**aggregate numbers only** — counts, rates, per-difficulty and
per-category splits, corpus fingerprint, case count, harness commit,
and the fact that the cases are unpublished. A results row must state
its trust level per §11b (holdout runs are L3 — "holdout-confirmed" —
by definition, since the corpus itself is not reproducible by a third
party).

## What must never go in this file

- Any individual case id, diff, title, or ground-truth explanation.
- Any absolute path, hostname, or other detail that could locate the
  holdout on disk.
- A result computed against a holdout whose fingerprint has not passed
  `bin/review-holdout check` (docs/M4_DESIGN_BRIEF.md §D) — i.e. one
  that collides with a public corpus fingerprint or is already named in
  `eval/EXPERIMENTS.md` or in this file.

## Row format, once a real run exists

```
| date | corpus name | fingerprint | cases | runs | model | detected | clean FP | category | severity | errors | trust | harness commit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
```

Three of those columns are not decoration:

- **`runs`** — `docs/ROADMAP.md` §9 failure mode 4 is explicit: "Publish
  only corrected, repeat-run figures with variance. Single-run numbers
  are never citable." A holdout row with `runs: 1` is therefore not a
  citable result, and a row format with no run count at all would have
  let one be published without anyone noticing. Use `--runs 3` or more,
  the same floor every public corpus run uses.
- **`errors`** — the existing report summary reports technical execution
  errors separately from quality misses, and that separation must
  survive into the published row. An error silently folded into "missed"
  overstates a model's failure to *find* something; folded into
  "detected" it overstates success.
- **`trust`** — the file header requires a trust level per
  `docs/BENCHMARK_METHODOLOGY.md` §11b, so the row has somewhere to put
  it. Holdout runs are **L3** by definition: the corpus is not
  reproducible by a third party, which is simultaneously the holdout's
  entire value and the reason no one else can check the number.

Nothing is added below this line until a real, contamination-checked
holdout run happens. See `docs/M4_PRIVATE_HOLDOUT_HANDOFF.md` for the
exact steps and where this session's responsibility stops.
