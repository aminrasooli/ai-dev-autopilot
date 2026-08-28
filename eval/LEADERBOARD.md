# Leaderboard structure (design — no live leaderboard yet)

There is deliberately **no leaderboard here yet**. Publishing one from a
~54-case self-authored pilot would manufacture a ranking the data cannot
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

1. Benchmark v2 corpus reviewed and **declared `stable` in
   `eval/cases/README.md`** — **met** (JP, 2026-08-28; declared at
   corpus level, frozen fingerprint unchanged)
2. At least two models with `runs ≥ 3` full-corpus reports in
   `eval/results/` — **met** (three models, three runs, both tiers)
3. At least one submission from outside the project — *not met*
4. The self-authorship limitation printed on the leaderboard itself, not
   in a footnote — *not met; do this when the table first renders*

**On precondition 1.** It previously read "marked `stable`", which is not
executable. `status` lives in each case file and is inside the corpus
fingerprint, so editing it would move v2's fingerprint from
`f31d46310988f61c…` to `9adb85ab011f4a75f1…` and invalidate every M1 and
M2 result citing the frozen value. Corpus maturity is **declared at
corpus level, never edited into frozen cases** — see
`docs/BENCHMARK_METHODOLOGY.md` §11a and the assessment in
`eval/cases/README.md`.

Note that precondition 3 cannot be satisfied before launch: outside
submissions are what launching is *for*. The leaderboard is therefore
expected to go live after M5, not as part of it — which is why M5's
done-when asks for a leaderboard **page**, and this file is it.
