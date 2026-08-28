# Submitting benchmark results

Results are only comparable when the run is reproducible. A submission is
a pull request adding one report file plus one metadata block; the raw
report is the artifact, prose is optional.

## What to include

1. **The machine-readable report**, unedited, as
   `eval/results/<model-slug>-<date>.json` — the exact `--out` file the
   harness wrote. Do not trim the per-case runs; the raw runs are the
   point.
2. **Run metadata**, in the PR description (or a sibling `.meta.json`):

   | field | example |
   |---|---|
   | model identifier (exact) | `qwen3.6:27b` |
   | quantization (local models) | `Q4_K_M (Ollama default tag)` |
   | backend | `ollama` |
   | hardware | `RTX 6000, 24 GB VRAM` |
   | harness commit | **recorded automatically** in `harness.commit` |
   | corpus | `eval/cases @ same commit` or named holdout |
   | corpus fingerprint | the `corpus.sha256` in your report |
   | runs per case | `3` |
   | reproduction command | the full `bin/review-eval ...` line |

   `harness.commit` and `harness.dirty` are written by the harness
   itself, so you do not supply them — and `dirty: true` means the
   working tree was modified, which makes the run unreproducible from
   that commit. The invocation is deliberately **not** recorded: it
   contains `--cases <path>`, and a report that may be submitted must
   never carry a local path (`docs/BENCHMARK_METHODOLOGY.md` §11).

   The **fingerprint is the field that decides comparability** — a
   commit can contain more than one corpus, and a corpus can change
   without the path changing. Two rows are only comparable when their
   `corpus.sha256` matches (`docs/BENCHMARK_METHODOLOGY.md` §11a).

3. **Cost honesty**: report dollars only if your tooling measured them.
   Local execution is reported as "no external model API charge" — it is
   not called *free*, because your hardware and electricity are not.

## Check your own report first

```sh
python3 -m reviewer.verify eval/results/<your-report>.json
```

This recomputes every summary number from your report's own per-case
records and prints either `internally consistent` or the exact
discrepancy. It is offline, costs nothing, and takes a second. A report
that fails this will be sent back, so it is cheaper to run it yourself —
and it is the same check we run on our own published results.

## Rules

- Same prompt for every model — the harness enforces this; do not patch
  `reviewer/prompt.py` per model and submit the result.
- Do not submit results for a corpus you modified in the same PR.
- `--runs 3` minimum for results meant to be quoted; single-run reports
  are accepted but will be labeled as anecdotal.
- Say who you are in the PR (a pseudonymous handle is fine) and whether
  you have any stake in the model you benchmarked.

## What happens to submissions

Accepted reports stay in `eval/results/` as raw artifacts. Any summary
table built from them names the corpus version and links back to each raw
report; conflicting results for the same model/version are kept side by
side, not averaged into agreement.

## Licensing

**Inbound equals outbound.** A submitted report is a contribution: you
offer it under the license that already applies to this project — today
[MIT](../LICENSE) — and you keep your copyright. There is no CLA and no
sign-off requirement.

If you are proposing **cases or datasets** rather than a result file,
open an issue first: a separate data license for corpus and results is a
deliberately deferred question
(`docs/M5_LICENSE_DECISION_BRIEF.md`), and it will be settled before any
third-party corpus contribution is accepted.
