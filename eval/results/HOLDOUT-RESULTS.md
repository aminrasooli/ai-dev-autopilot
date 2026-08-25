# Private holdout results

Status: **scaffold, empty.** No private holdout exists yet
(`docs/M4_PROVENANCE_GAP_AUDIT.md` §"Private holdout"). This file's
header is created now so a future holdout run has a place to go, under
the publishing rules already fixed in
`docs/BENCHMARK_METHODOLOGY.md` §11 — not decided here, only reserved.

## What may go in this file, once a holdout exists and is run

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
  `eval/EXPERIMENTS.md`.

## Row format, once a real run exists

```
| date | corpus name | fingerprint | cases | model | detected | clean FP | category | severity | harness commit |
|---|---|---|---|---|---|---|---|---|---|
```

Nothing is added below this line until a real, contamination-checked
holdout run happens. See `docs/M4_PRIVATE_HOLDOUT_HANDOFF.md` for the
exact steps and where this session's responsibility stops.
