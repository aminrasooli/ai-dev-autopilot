# Leaderboard structure (design — no live leaderboard yet)

There is deliberately **no leaderboard here yet**. Publishing one from a
~57-case self-authored pilot would manufacture a ranking the data cannot
support. This file fixes the structure *in advance*, so that when enough
reproducible submissions exist, the table's shape was decided before
anyone's score was known — not after.

## Row = one (model, runtime, benchmark version) triple

One row per unique combination; conflicting submissions for the same
triple are listed as separate rows, never averaged into agreement.

| column | source | notes |
|---|---|---|
| model | submission metadata | exact identifier, e.g. `qwen3.6:27b` |
| quantization | submission metadata | local models; `n/a` for hosted |
| runtime / backend | report | `ollama`, `claude`, … |
| benchmark version | report `corpus.benchmark_version` | rows are only comparable within a version |
| corpus sha256 | report `corpus.sha256` | proves *which* corpus, incl. holdouts |
| runs per case | report | rows with `runs < 3` are marked anecdotal |
| defect detection | report summary | detected/defective runs |
| clean false-positive rate | report summary | FP runs / clean runs |
| category correct | report summary | with the taxonomy-strictness caveat |
| severity correct | report summary | |
| consistency | report consistency block | always/sometimes/never detected |
| errors / malformed | report summary | never folded into misses |
| mean latency (s) | report summary | hardware-dependent for local models |
| hardware | submission metadata | required for local models |
| external API cost | report summary | measured only; local = "no external model API charge" (not "free") |
| verification | maintainer-assigned | see below |

## Verification levels

- **self-reported** — a syntactically valid submission with complete
  metadata; taken at face value, labeled as such.
- **reproduced** — a maintainer or independent third party re-ran the
  stated reproduction command against the stated corpus fingerprint and
  obtained materially consistent results (exact equality is not expected
  from nondeterministic models; detection/FP counts within the
  submission's own run-to-run spread is the bar).
- **holdout-confirmed** — the model was additionally run against a
  private holdout corpus (aggregate scores only; contents unpublished).

No cryptographic attestation is planned at this stage; the verification
column plus raw-report review is the trust mechanism, and its limits are
acknowledged.

## Preconditions for going live

1. Benchmark v2 corpus reviewed and marked `stable` (currently `pilot`)
2. At least two models with `runs ≥ 3` full-corpus reports in
   `eval/results/`
3. At least one submission from outside the project
4. The self-authorship limitation printed on the leaderboard itself, not
   in a footnote
