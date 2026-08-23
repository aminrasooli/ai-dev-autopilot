# Local Reviewer Benchmark

A reproducible benchmark for AI code reviewers: versioned cases with known
ground truth in `cases/`, machine-readable results in `results/`, scoring
harness in `../reviewer/`. Methodology — including what this benchmark
does and does not measure, and its stated limitations — lives in
[`docs/BENCHMARK_METHODOLOGY.md`](../docs/BENCHMARK_METHODOLOGY.md).
Read that before citing any number from here.

Status: **v2 pilot** — 53 self-authored cases. Not an independent
benchmark; results are reproducible evidence, not rankings.

M3 hard-benchmark work (`docs/ROADMAP.md` §4) lives separately in
[`cases-v3/`](cases-v3/), starting with
[`cases-v3/tranche-1/`](cases-v3/tranche-1/) — never mixed into
`cases/`, so the frozen v2 fingerprint above never moves.

## Run it

```sh
bin/review-corpus                      # validate the corpus (offline)
bin/review-eval --backend fake         # oracle self-test (offline, CI)
bin/review-eval --backend ollama --model qwen3.6:27b --runs 3 \
    --out eval/results/my-qwen-report.json
bin/review-eval --backend claude --model claude-sonnet-5 --runs 3 \
    --out eval/results/my-claude-report.json
bin/review-eval --compare a.json b.json
```

- `--runs N` evaluates every case N independent times and reports
  consistency as well as point scores; sampling models vary run to run,
  so N≥3 is recommended for any number you intend to quote.
- The Ollama backend only ever speaks to a loopback endpoint (local
  review stays local); the Claude backend runs `claude -p` isolated from
  your repository and settings. No backend gets a different prompt.
- Progress streams to stderr per run; every model call has a finite
  timeout, and failed runs are recorded as errors and skipped past, never
  retried silently.
- `--cases DIR` points the harness at any schema-valid corpus directory —
  including a private holdout that never appears in this repository.

## Contribute cases

Cases are one JSON file each in `cases/`, schema v2 (see the methodology
§4). In short: declare `language`, `provenance` (who/what authored it),
`affected_files`, a unified `diff`, and `ground_truth` with category,
severity range and a one-sentence explanation — or `defect: false` for a
clean control. Then:

```sh
bin/review-corpus        # must pass
bin/review-eval --backend fake   # oracle must stay perfect
```

Clean controls, non-Python languages, cross-file cases, and cases NOT
authored by a Claude model are the most valuable contributions — the
corpus is currently 100% Claude-authored and says so in every case's
provenance. Do not contribute cases copied from proprietary benchmarks or
from code you cannot license.

## Submit results

See [`SUBMIT.md`](SUBMIT.md).
