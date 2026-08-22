# M2 cross-model pilot — scorecard

**Status: PILOT.** Per `docs/ROADMAP.md` §4 (M2: "Sonnet vs Qwen vs
DeepSeek on frozen corpus, 3 repetitions, honest cost + latency + quality
scorecard, clearly labeled a pilot") and §6 message rules ("pilot results
are labeled pilot; variance is reported; only corrected, repeat-run
figures are citable"). This is **not** `eval/LEADERBOARD.md` — that file
is a design doc for a future public leaderboard and its own preconditions
for going live are not met yet (corpus status is `pilot`, not `stable`;
no outside submission exists). This is evidence, not a ranking, and not
launch-grade.

Registered in advance, before any run executed, per
`eval/EXPERIMENTS.md` rule 1 (anti-cherry-picking): X14 (Sonnet), X15
(Qwen), X16 (DeepSeek), all `status=authoritative` — approved ground
truth, registered before execution, quotable.

Corpus: 54 cases (40 defective / 14 clean / 6 cross-file), fingerprint
`f31d46310988f61c4534344ad05a52a4385fd15159126a0be85aad532f045690`
(the M1-frozen corpus; unchanged by this pilot). 3 independent runs per
case per model = 162 calls each. All three reports pass
`python3 -m reviewer.verify` (internal consistency: summary recomputed
from raw runs, matches exactly) and share an identical prompt contract
(`6a4e51f7014991b2`), so `reviewer.compare` treats them as directly
comparable.

Reproduce this table:

```sh
python3 -m reviewer.leaderboard \
  eval/results/claude-sonnet-5-m2pilot-3runs.json \
  eval/results/qwen3.6-27b-m2pilot-3runs.json \
  eval/results/deepseek-r1-14b-m2pilot-3runs.json \
  --level eval/results/claude-sonnet-5-m2pilot-3runs.json=L1-reproducible \
  --level eval/results/qwen3.6-27b-m2pilot-3runs.json=L1-reproducible \
  --level eval/results/deepseek-r1-14b-m2pilot-3runs.json=L1-reproducible
```

## Scorecard

Ordered by model identifier, **not** by score: there is no composite
ranking, because any single number would need invented weights. Read the
columns together — a reviewer that catches everything and cries wolf is
not strictly better than a quieter one that misses a subtle bug, and
which you want is your call.

| model | runtime | runs | defect recall | recall 95% CI | clean FP rate | FP 95% CI | category | severity | always/sometimes/never | cross-file recall | latency | errors | external cost | verification |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5 | claude | 3 | 1.00 | 0.97–1.00 | 0.21 | 0.12–0.36 | 0.85 | 0.82 | 40A/0S/0N | 1.00 | 5.3s (2.5–32.3) | 1 | $1.4353 | L1-reproducible |
| deepseek-r1:14b | ollama | 3 | 0.82 | 0.73–0.88 | 0.10 | 0.04–0.22 | 0.34 | 0.26 | 28A/8S/4N | 1.00 | 2.5s (0.8–7.3) | 6 | no external API charge | L1-reproducible |
| qwen3.6:27b | ollama | 3 | 0.99 | 0.95–1.00 | 0.26 | 0.15–0.41 | 0.76 | 0.65 | 38A/1S/1N | 1.00 | 9.5s (1.8–20.3) | 4 | no external API charge | L1-reproducible |

Corpus fingerprint: `f31d46310988…` · prompt contract: `6a4e51f7014991b2`.

Local runs (Qwen, DeepSeek) show *no external model API charge* — that is
**not** the same as free: both occupied the host's single RTX 6000 24GB
GPU for the stated latency, sequentially (Qwen then DeepSeek), and drew
power that is not metered here. Sonnet's cost is a real measured dollar
figure from the existing Claude Code subscription path (`claude -p
--output-format json`), not a separate pay-as-you-go API integration.

**Latency is not like-for-like.** All three ran under the harness's
provider-default sampling with no per-model tuning (`docs/BENCHMARK_METHODOLOGY.md`
§7), but Sonnet is a hosted cloud call and Qwen/DeepSeek share one local
GPU sequentially with each other — mean latency here measures three very
different execution environments, not three points on the same axis.

## Honest error accounting

Errors are never folded into misses or false positives (methodology §6,
§9). All errors below are `MalformedResponse` — an out-of-vocabulary
category string or (one case) a missing verdict — never a timeout or a
daemon-unavailable failure:

- **Sonnet (1 error / 162 calls):** `21-js-prototype-pollution` run 3 —
  category `security` is not in the taxonomy.
- **Qwen (4 errors / 162 calls):** `22-js-balance-read-modify-write` run
  3 (`race-condition`), and `47-py-mktemp-race` runs 1–3, all three
  (`race-condition`) — this one case errored on every Qwen run.
- **DeepSeek (6 errors / 162 calls):** `08-unsafe-binding` run 1
  (`security-problem`), `12-destructive-migration` run 2
  (`data-loss`), `13-permission-widening` run 2 (`security-problem`),
  `31-go-defer-in-loop` run 1 (verdict was `None`), `36-java-dcl-no-volatile`
  run 2 (`singleton-pattern`), `47-py-mktemp-race` run 2 (`file-handling`).

`47-py-mktemp-race` is the one case that errored across two different
models (all 3 Qwen runs, 1 DeepSeek run) — both invented a
`race`-flavored category outside the fixed vocabulary rather than mapping
to `concurrency`, the ground-truth category. Worth a closer look before
any future prompt-contract revision, not fixed here (out of M2 scope).

## Stability across runs (why 3 repetitions, not 1)

- **Sonnet:** all 40 defect cases always detected across all 3 runs; 3 of
  14 clean cases produced an occasional false positive
  (`18-clean-test-added`, `53-xfile-clean-helper-move`,
  `54-clean-dependency-bump`).
- **Qwen:** 38/40 defect cases always detected, 1 sometimes
  (`36-java-dcl-no-volatile`, 2/3), 1 never (the errored
  `47-py-mktemp-race`, all 3 runs malformed); 4 clean cases showed
  occasional or persistent false positives.
- **DeepSeek:** 28/40 defect cases always detected, 8 sometimes, 4 never
  — the most run-to-run variable of the three, consistent with its lower
  recall and category/severity correctness.

## What this pilot does and does not show

Per `docs/BENCHMARK_METHODOLOGY.md` §15 limitations (self-authored,
~54-case, synthetic, diff-only corpus; category-strictness scoring), plus
this pilot's own scope: this compares three models under one fixed
prompt contract on one small self-authored corpus, once, at 3 runs each.
It is real, registered-in-advance evidence — not a ranking, not a
statement about these models' general coding ability, and not the public
leaderboard (`eval/LEADERBOARD.md` stays inactive until its own
preconditions are met).
