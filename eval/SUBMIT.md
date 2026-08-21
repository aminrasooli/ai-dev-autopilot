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
   | harness commit | `git rev-parse HEAD` output |
   | corpus | `eval/cases @ same commit` or named holdout |
   | runs per case | `3` |
   | reproduction command | the full `bin/review-eval ...` line |

3. **Cost honesty**: report dollars only if your tooling measured them.
   Local execution is reported as "no external model API charge" — it is
   not called *free*, because your hardware and electricity are not.

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
