# M3 hard benchmark — scorecard

> **Answer-key errata.** Read [`../cases-v3/ERRATA.md`](../cases-v3/ERRATA.md) alongside every number below. The v3 answer key is human-reviewed *with documented errata*
> (JP, 2026-08-28), not error-free: `t1-12` has **invalid** ground truth and `t2-06` rests on code the reviewer never sees.
> **No figure in this file changes** — the cases are frozen and every result cites that fingerprint. Excluding the affected cases moves any
> headline by **≤1.0 pp** and changes no ranking; the recomputed values are in the errata.


**Status: authoritative evidence for the M3 hard benchmark (v3 corpus).**
Not a leaderboard, not a ranking, not launch-grade: per `docs/ROADMAP.md`
§4 (M3) and §6 message rules, this is registered-in-advance evidence
about one self-authored 37-case corpus. `eval/LEADERBOARD.md` stays
inactive; its preconditions are unchanged.

## Frozen corpus and preregistration chronology

Corpus: `eval/cases-v3/cases/` — 37 cases (29 defective / 8 clean,
12 cross-file difficulty, 10 execution-validated), fingerprint

```
81daa0b7a48259184a91c48ab1dcf17c9d3ed4902fa891b5895db0f29fd79790
```

frozen as merged by PR #19 (`79f4032c`), with the freeze record, the
blind-authoring statement and this measurement contract fixed **before
any target-model result existed** (`eval/cases-v3/README.md`).
Chronology, verifiable on GitHub:

1. **Preregistered** — X17/X18/X19 registered `authoritative`,
   result pending, in commit `4a53b394` (PR #20 branch), pushed
   2026-08-24T02:55:35Z (19:55:35 PDT).
2. **Executed** — all three legs launched from the host at
   20:24:04 PDT 2026-08-23 (X17 hosted lane; X18→X19 strictly
   sequential on the local GPU). Completed 21:18:47 / 21:09:02 /
   21:12:43 PDT, all exit 0.
3. **Recorded** — results committed after completion; the
   preregistration commit is untouched.

Per model: 3 runs × 37 cases = 111 observations — **87 defective
observations** (29×3) and **24 clean observations** (8×3), denominators
fixed in the preregistered contract. All three reports pass
`python3 -m reviewer.verify` (summary recomputed from raw runs, exact
match) and share prompt contract `6a4e51f7014991b2`.

Reproduce the summary table:

```sh
python3 -m reviewer.leaderboard \
  eval/results/claude-sonnet-5-m3hard-3runs.json \
  eval/results/qwen3.6-27b-m3hard-3runs.json \
  eval/results/deepseek-r1-14b-m3hard-3runs.json
```

## Headline scorecard (preregistered raw denominators)

Ordered by model identifier, not by score. "det-of-ok" is the harness's
recall over completed (non-error) observations — the M2-comparable
figure; errors are never folded into misses or false positives.

| model | detected | missed | defect errors | clean FP | category | severity | errors (of 111) |
|---|---|---|---|---|---|---|---|
| claude-sonnet-5 | **85/87** (97.7%) | 0/87 (0%) | 2 | **21/24** (87.5%) | 79/85 (0.93) | 75/85 (0.88) | 2 |
| deepseek-r1:14b | **12/87** (13.8%) | 73/87 (83.9%) | 2 | **4/24** (16.7%) | 3/85 (0.04) | 3/85 (0.04) | 2 |
| qwen3.6:27b | **82/87** (94.3%) | 0/87 (0%) | 5 | **19/24** (79.2%) | 59/82 (0.72) | 56/82 (0.68) | 6 |

Read the detection and false-positive columns together: **every
completed defective observation was detected by Sonnet (85/85) and Qwen
(82/82)** — their non-detections are all malformed-response technical
errors, not misses — while both flagged most of the hard clean controls
(21/24 and 19/24 clean observations; Qwen's clean denominator of
completed observations is 23, one clean run errored, giving the 0.83
rate the leaderboard tool prints). DeepSeek shows the opposite shape:
it returned `approve` with zero findings on 93 of its 109 completed
calls, missing 73/87 defective observations — its low clean-FP count
(4/24) reflects that near-silence, not precision.

Secondary descriptive context (Wilson 95% CIs, post-run description,
not a preregistered metric): detection-of-ok — Sonnet 0.96–1.00, Qwen
0.96–1.00, DeepSeek 0.08–0.23; clean FP — Sonnet 0.69–0.96, Qwen
0.63–0.93, DeepSeek 0.07–0.36. At n=24 clean observations, **one
false-positive flip moves the clean FP rate by ~4.2 percentage
points** — quote the raw x/24, not the percentage alone.

## Stability across runs

| model | defect cases 3/3 · 2/3 · 1/3 · 0/3 | defect cases w/ errors | clean never-FP · 1/3 · 2/3 · 3/3 |
|---|---|---|---|
| claude-sonnet-5 | 27 · 0 · 0 · 0 | 2 (detected in all completed runs) | 1 · 0 · 0 · 7 |
| deepseek-r1:14b | 1 · 0 · 7 · 19 | 2 | 6 · 1 · 0 · 1 |
| qwen3.6:27b | 24 · 0 · 0 · 0 | 5 (detected in all completed runs) | 0 · 1 · 2 · 5 (1 clean case also errored once) |

Sonnet and Qwen are fully stable on detection (no
sometimes-detected case). Sonnet is also stable on its false
positives — 7 of 8 clean cases flagged in **all three** runs — meaning
its clean-control behavior is a consistent judgment, not sampling
noise. DeepSeek is dominated by stochastic scarcity: 19 defective
cases never detected, 7 detected in exactly one run of three.

## Predefined difficulty breakdown (labels frozen before results)

Detection of completed defective obs / clean FP; category, severity as
correct/completed-defective-obs. `moderate` is a single clean case —
raw counts only, sample too small for a rate.

| group (cases) | claude-sonnet-5 | qwen3.6:27b | deepseek-r1:14b |
|---|---|---|---|
| cross-file (12 def.) | det 35/35, cat 33/35, sev 31/35, 1 err | det 33/33, cat 26/33, sev 26/33, 3 err | det 9/35, cat 3/35, 1 err |
| subtle — defective (17) | det 50/50, cat 46/50, sev 44/50, 1 err | det 49/49, cat 33/49, sev 30/49, 3 err | det 3/50, cat 0/50, 1 err |
| subtle — clean (7) | FP 18/21 | FP 17/20 (1 err) | FP 4/21 |
| moderate — clean (1) | FP 3/3 | FP 2/3 | FP 0/3 |

DeepSeek detects cross-file cases (26%) more often than subtle
single-file ones (6%) — the reverse of the design's expectation; its
few detections cluster on the most structurally visible cases.

## Predefined category breakdown (ground-truth categories, all groups)

Detection of completed defective observations per ground-truth
category (n = cases). Categories with n=1 (api-misuse,
error-handling, resource-leak) are raw counts only.

| category (n cases) | claude-sonnet-5 | qwen3.6:27b | deepseek-r1:14b |
|---|---|---|---|
| auth-bypass (5) | 15/15 | 15/15 | 3/14 |
| concurrency (5) | 15/15 | 14/14 | 1/15 |
| contract-mismatch (4) | 11/11 | 10/10 | 5/12 |
| data-corruption (4) | 11/11 | 11/11 | 0/12 |
| logic-error (8) | 24/24 | 23/23 | 1/24 |
| api-misuse (1) | 3/3 | 3/3 | 1/3 |
| error-handling (1) | 3/3 | 3/3 | 0/3 |
| resource-leak (1) | 3/3 | 3/3 | 1/2 |
| (clean) FP (8) | 21/24 | 19/23 | 4/24 |

For the top two models no category de-saturated detection; the spread
is entirely in classification. Qwen's category correctness concentrates
its losses in state/cache-flavored cases (see below) and go-language
cases (4/9); Sonnet's category errors are few and adjacent
(e.g. `contract-mismatch` → `concurrency` on t2-06, twice).

## M3 taxonomy clusters (frozen in `eval/cases-v3/README.md`)

| cluster (cases) | claude-sonnet-5 | qwen3.6:27b | deepseek-r1:14b |
|---|---|---|---|
| larger-realistic-diffs (7) | det 21/21, cat 20/21 | det 20/20, cat 13/20 | det 2/20 |
| deep-cross-file (8) | det 22/22, cat 19/22, 2 err | det 21/21, cat 15/21, 3 err | det 6/24 |
| authorization (5) | det 15/15, cat 15/15 | det 15/15, cat 12/15 | det 3/14, 1 err |
| state-cache (5) | det 14/14, cat 12/14, 1 err | det 15/15, cat 8/15 | det 0/15 |
| concurrency (5) | det 15/15, cat 14/15 | det 14/14, cat 12/14, 1 err | det 1/15 |
| hard-clean-controls (8) | FP 21/24 | FP 19/23, 1 err | FP 4/24 |

Answers to the design questions: **misses** were created only for the
weakest model (DeepSeek, everywhere — worst on state/cache 0/15 and
concurrency 1/15). **Inconsistency** appears only in DeepSeek (7 cases
at 1/3) — Sonnet/Qwen have none. **False positives** come almost
entirely from the hard clean controls, exactly as designed — and at
much higher rates than v2's clean set. **Nothing remained easy** in the
classification dimension: even with perfect detection, Qwen's category
correctness drops to 53% on state-cache; Sonnet's severity drops to
77% on deep-cross-file. Execution-validated cases (10) vs rest:
detection identical for top-2 (29/29 and 29/29 vs 56/56 and 53/53);
DeepSeek 1/30 vs 11/55 — the execution-validated concurrency/state
cluster is where it detects least. (Public metadata only: the
`execution_validated` flag and note; validation artifacts stay private
per methodology.)

## Language breakdown (descriptive only; python-heavy corpus)

Defective-case detection (completed obs): python (24 cases) — Sonnet
55/55, Qwen 53/53, DeepSeek 8/57; go (4) — 9/9, 9/9, 2/7; typescript
(3) — 9/9, 9/9, 1/9; java (2, 1 defective) — 3/3, 3/3, 0/3; javascript
(2) — 6/6, 5/5, 0/6; rust (1) — 3/3, 3/3, 1/3; sql (1, clean) — FP 3/3,
3/3, 0/3. One-case slices are raw counts; no language-general claims.

## Error audit (10 technical errors across 333 calls)

All 10 are `MalformedResponse` — never a timeout, never a backend
outage, never folded into quality misses:

- **Sonnet (2/111):** t1-15 run 2 (finding with null category/severity),
  t2-05 run 1 (null verdict).
- **Qwen (6/111):** three null-verdict failures (t1-04 r3, t1-10 r1 —
  the one clean-case error, t1-13 r2) and three out-of-vocabulary
  categories: `security` (t1-06 r3), `data-loss-risk` (t2-02 r3),
  `race-condition` (t2-06 r2).
- **DeepSeek (2/111):** t1-02 r3 (null verdict), t2-11 r3
  (out-of-vocabulary `security-headers`).

No case errored across models or across more than one run — errors do
not cluster (contrast M2's `47-py-mktemp-race`). Out-of-vocabulary
inventions (`race-condition`, `security`) recur from M2; noted, not
fixed here (prompt-contract revision is out of M3 scope).

## Clean-control forensics (diagnostic only; frozen ground truth unchanged)

Every clean case that drew at least one false positive, with what the
models claimed. Ground-truth cleanliness was re-audited blind before
the freeze; nothing here relabels a case.

| clean case | sonnet | qwen | deepseek | typical claim |
|---|---|---|---|---|
| t1-09-httpkit-major-bump | 3/3 | 3/3 | 0/3 | sonnet: test-gap medium · qwen: api-misuse high |
| t1-10-auth-decorator-consolidation | 3/3 | 2/3 (1 err) | 1/3 | sonnet: **auth-bypass critical** · qwen: contract-mismatch high |
| t1-11-narrowed-except-clauses | 3/3 | 2/3 | 0/3 | logic-error critical/high |
| t2-18-go-excl-lockfile | 3/3 | 3/3 | 3/3 | sonnet: test-gap medium · qwen: concurrency high |
| t2-19-sql-online-migration | 3/3 | 3/3 | 0/3 | logic-error high/critical |
| t2-20-java-lockfree-counters | 0/3 | 1/3 | 0/3 | qwen: test-gap medium |
| t2-21-py-idempotent-capture-retry | 3/3 | 2/3 | 0/3 | logic-error high · qwen: dependency-risk high |
| t2-22-py-immutable-snapshot-routing | 3/3 | 3/3 | 0/3 | sonnet: test-gap low · qwen: missing-validation high |

Character of the false positives: a minority are advisory-hygiene
flags scored as FPs under the unchanged scoring semantics (Sonnet's
`test-gap medium/low` on t1-09, t2-18, t2-22); the majority are
substantive wrong defect claims at high/critical severity — most
notably Sonnet's 3/3 `auth-bypass critical` on t1-10, whose decorator
consolidation reproduces each handler's role set exactly. t2-18 (the
O_EXCL lockfile) fooled all three models in every completed run —
including otherwise-near-silent DeepSeek — making it the corpus's
single most deceptive clean control. These diffs were designed to look
suspicious while being correct; the design worked, at the cost of
showing that current reviewers (as configured here) cannot tell
suspicious-but-correct from wrong at this difficulty.

## Missed-defect forensics

Sonnet and Qwen missed **zero** defective observations they completed.
The only misses are DeepSeek's 73/87, spread over 26 of 29 defective
cases (19 never detected, 7 detected 1/3) — a blanket-approval
collapse (93 of its 109 completed calls returned `approve` with zero
findings, ~13 output tokens each), not a per-mechanism weakness. The
adversarial checks below rule out an infrastructure explanation.

## Detection vs classification quality

Detection no longer separates Sonnet from Qwen on this corpus —
classification does: with both at 100% detection-of-completed, Sonnet
leads category correctness 0.93 vs 0.72 and severity 0.88 vs 0.68.
Qwen's classification losses concentrate where mechanism identification
is hardest (state-cache 8/15 category-correct; go cases 4/9). Severity
under-rating tracks category confusion for both. DeepSeek's 12
detections include only 3 category-correct — when it does flag, the
mechanism is usually wrong (`missing-validation` for a deadlock,
`command-injection` for a handler leak).

## M2 → M3 (different corpora — not a model-regression comparison)

| | M2 (v2 frozen, X14–X16) | M3 (v3 frozen, X17–X19) |
|---|---|---|
| corpus | 54 cases (40 def / 14 clean) | 37 cases (29 def / 8 clean) |
| diff size | ≤35 lines | 80–219 lines, median 102 |
| clean controls | ordinary | hard (suspicious-but-correct, difficulty-labeled) |
| Sonnet: recall-of-ok / clean FP / cat / sev | 1.00 / 0.21 / 0.85 / 0.82 | 1.00 (85/87 raw) / **0.88 (21/24)** / 0.93 / 0.88 |
| Qwen: same | 0.99 / 0.26 / 0.76 / 0.65 | 1.00 (82/87 raw) / **0.83 (19/23; 19/24 preregistered)** / 0.72 / 0.68 |
| DeepSeek: same | 0.82 / 0.10 / 0.34 / 0.26 | **0.14 (12/87 raw)** / 0.17 (4/24) / 0.04 / 0.04 |
| errors | 1 / 4 / 6 of 162 | 2 / 6 / 2 of 111 |

The corpora differ by design; lower M3 numbers mean the corpus got
harder, not that a model "got worse." What M3 changed: it moved the
differentiation. In M2 the top two models were separated mainly by
classification; in M3 they are additionally — and dramatically —
stressed by clean-control precision, and the weakest model's detection
collapsed outright.

## Saturation conclusion (ROADMAP §4 M3: "detection no longer saturated")

**For the two leading models, detection remains saturated: not
demonstrated.** Sonnet and Qwen detected every defective observation
they completed (85/85, 82/82); their raw 85/87 and 82/87 shortfalls
are malformed-response errors, not misses. De-saturation did occur,
but elsewhere: (a) the weakest model's detection collapsed from 0.82
(M2) to 12/87 — the corpus now cleanly separates model tiers that v2
could not; (b) the hard clean controls de-saturated *precision*
(Sonnet 0.21→21/24, Qwen 0.26→19/24); (c) classification remains
unsaturated for all three. Every structural M3 goal (larger diffs,
deep cross-file, state/cache, authorization, concurrency, hard clean
controls) is represented and produced measurable stress — but the
specific gate wording "detection no longer saturated" is **not yet
demonstrated for leading models** on this corpus. The frozen corpus
stays frozen; whether the gate is satisfied by the observed
differentiation, or requires further (M4-scope, e.g. non-self-authored)
hardening, is a human roadmap decision, not made here.

## Cost, latency, execution environments (not like-for-like)

- **Sonnet (hosted):** measured external cost **$5.335879** for 111
  calls (`claude --output-format json`, subscription path; the only
  backend with an honest dollar figure). Mean latency 29.8s
  (4.5–90.7s); hosted lane wall-clock 54m43s.
- **Qwen (local):** no external model API charge (local compute time
  is not free) — 2491.6s (~41.5 min) measured model execution on the
  host's single RTX 6000, lane wall-clock 44m58s. Mean latency 23.8s.
- **DeepSeek (local):** no external model API charge (local compute
  time is not free) — 208.9s (~3.5 min) measured model execution,
  lane wall-clock 3m41s after Qwen released the GPU. Mean latency
  1.9s — fast because it produced ~13-token empty-approve responses,
  not because it did the same work faster.

Hosted-cloud latency and single-local-GPU latency are different
execution environments; these numbers are not an apples-to-apples
infrastructure comparison. Qwen and DeepSeek ran strictly
sequentially; Sonnet ran concurrently in its own hosted lane.

## Adversarial integrity checks performed

- All three reports: fingerprint exact, 37 unique cases, runs {1,2,3}
  per case, 111 observations, checkpoint identity (backend/model/
  corpus/prompt-contract) matching, `reviewer.verify` pass, no v2 case
  IDs, no alternate result paths, preregistration rows still "pending"
  until this commit.
- DeepSeek collapse cross-checked: correct model tag in report and
  checkpoint; input tokens scale with diff size (993–2476, no
  truncation ceiling); the same Ollama server ran Qwen to 82/87 on
  identical prompts; M2 used the same backend path at 0.82 recall.
  The collapse is model behavior on harder input, not harness failure.
- Headline numbers recomputed twice independently (raw-record analyzer
  vs `reviewer.leaderboard`), exact agreement.

## Limitations

Everything in `docs/BENCHMARK_METHODOLOGY.md` §15 applies: one
self-authored, 100%-Claude-authored corpus (self-authorship bias is
untested until M4's non-Claude cases and holdout), 37 cases, diff-only
review, category-strict scoring, 3 runs, one prompt contract, no
per-model tuning. The clean-control FP rates rest on 8 cases ×
3 runs; treat them as strong evidence of difficulty, not a precision
benchmark. DeepSeek-R1:14b results describe that specific quantized
local build under this structured-output contract, not the R1 family
generally.

## Result file provenance

| experiment | report | sha256 |
|---|---|---|
| X17 | `claude-sonnet-5-m3hard-3runs.json` | `3ebc197374d5d55f4f7813bfa0870595765a7175d5eea872f0adea79692944ab` |
| X18 | `qwen3.6-27b-m3hard-3runs.json` | `03303361f2dae985e7ada1b1206a127ccac35210beb504296fd3de4cf49b3a94` |
| X19 | `deepseek-r1-14b-m3hard-3runs.json` | `b036f7b08cc4e54499aa8e271f49d1cf2c43cf7e7ecb4fce8948b99f34afdd76` |

Corpus `81daa0b7…79790` · prompt contract `6a4e51f7014991b2` ·
preregistration commit `4a53b394` (2026-08-24T02:55:35Z) · executed
2026-08-23 20:24–21:19 PDT.
