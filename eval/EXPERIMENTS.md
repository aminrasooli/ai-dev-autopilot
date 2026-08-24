# Experiment registry

Every real-model invocation against this benchmark, registered. The
point is anti-cherry-picking: a run that happened appears here whether
or not its numbers were flattering, and **authoritative runs are
registered before they execute**, so "we only report the good ones"
is not available as a failure mode.

Status vocabulary:

- **disposable** — plumbing validation. Never quoted as a result.
- **provisional** — a real measurement taken *before* its corpus's
  ground truth was human-approved. Real evidence, not a result.
- **authoritative** — run against approved ground truth, registered in
  advance, quotable.
- **failed** — did not complete. Stays listed; failures are evidence too.

| id | date | status | model | backend | corpus | runs | cases | purpose | measured cost | output |
|---|---|---|---|---|---|---|---|---|---|---|
| X1 | 2026-08-19 | archived-v1 | claude-sonnet-5 | claude | v1 (20 cases) | 1 | 20 | first real Claude baseline (superseded; token accounting bug) | — | `archive-v1/claude-report.json` |
| X2 | 2026-08-19 | archived-v1 | qwen3.6:27b | ollama | v1 (20 cases) | 1 | 20 | first real Qwen baseline | no external model API charge | `archive-v1/qwen-report.json` |
| X3 | 2026-08-20 | disposable | claude-sonnet-5 | claude | v2 subset | 3 | 5 | validate repeat-run mechanics | $0.208785 | `archive-v1/claude-sonnet-5-pilot-subset-3runs-2026-08-20.json` |
| X4 | 2026-08-20 | disposable | claude-sonnet-5 | claude | v2 subset | 3 | 4 | quality-gate the new clean controls | $0.184629 | `archive-v1/claude-sonnet-5-clean-controls-3runs-2026-08-20.json` |
| X5 | 2026-08-20 | disposable | claude-sonnet-5 | claude | v2 subset (post-audit) | 3 | 8 | validate audit fixes + alternatives mechanism | $0.291306 | scratch (not committed) |
| X6 | 2026-08-20 | provisional | claude-sonnet-5 | claude | v2 pilot `56e4a32f…` | 3 | 57 | full-corpus variance evidence ahead of ground-truth approval | $1.453112 | `provisional/claude-sonnet-5-v2pilot-3runs-provisional.json` |
| X7 | 2026-08-20 | provisional | claude-sonnet-5 | claude | v2 pilot `56e4a32f…` (5 clean cases) | 7 | 5 | separate persistent false positives from sampling noise | $0.257192 | `provisional/claude-sonnet-5-cleanFP-stress-7runs-provisional.json` |
| X8 | 2026-08-20 | provisional | qwen3.6:27b | ollama | v2 pilot | 3 | 57 | local baseline, host night job | no external model API charge | pending |
| X9 | 2026-08-20 | provisional | deepseek-r1:14b | ollama | v2 pilot | 3 | 57 | second local model for context | no external model API charge | pending |

| X10 | 2026-08-21 | provisional | claude-sonnet-5 | claude | v2 pilot `56e4a32f…` | 5 | 57 | pre-registered: 5-run baseline matching the local models' run count | **$2.289898** (285 calls, 1 malformed) | `provisional/claude-sonnet-5-v2pilot-5runs-provisional.json` |
| X11 | 2026-08-21 | superseded | claude-sonnet-5 | claude | — | 5 | 16 | pre-registered, then SUPERSEDED by X10: the full 5-run corpus already covers all 16 clean cases at 5 runs (19/80 FP). Row kept rather than deleted — a registered experiment that became unnecessary is still part of the record. | not run | — |
| X12 | 2026-08-21 | provisional | claude-sonnet-5 | claude | v2 pilot `56e4a32f…` (12 hard-tier cases) | 10 | 12 | pre-registered by METADATA (all subtle+contextual+cross-file), not by prior outcome | **$1.009714** (120 calls, 0 errors) | `provisional/claude-sonnet-5-hardtier-10runs-provisional.json` |
| X13 | 2026-08-22 | provisional | claude-sonnet-5 | claude | v2 frozen `f31d4631…` (post-ground-truth, 54 cases) | 3 | 54 | M1 fresh-clone reproducibility evidence: run from a genuinely fresh `git clone` of `origin/main` at commit `485912b5`, not a working copy — against the frozen answer key, not the superseded 57-case pilot fingerprint X6/X7/X10 ran against. Row added after the run completed, so provisional per rule 1 even though ground truth is approved. | $2.213189 (162 calls, 0 errors) | `provisional/claude-sonnet-5-m1-frozen54-3runs-freshclone.json` |

| X14 | 2026-08-22 | authoritative | claude-sonnet-5 | claude | v2 frozen `f31d4631…` (54 cases) | 3 | 54 | M2 cross-model pilot (ROADMAP §4): Sonnet leg — Sonnet vs Qwen vs DeepSeek on the frozen corpus, 3 repetitions, clearly labeled a pilot. Pre-registered before execution per rule 1. | $1.435265 (162 calls, 1 error) | `claude-sonnet-5-m2pilot-3runs.json` |
| X15 | 2026-08-22 | authoritative | qwen3.6:27b | ollama | v2 frozen `f31d4631…` (54 cases) | 3 | 54 | M2 cross-model pilot (ROADMAP §4): Qwen leg, local via Ollama on the host GPU. Pre-registered before execution per rule 1. | no external model API charge (162 calls, 4 errors) | `qwen3.6-27b-m2pilot-3runs.json` |
| X16 | 2026-08-22 | authoritative | deepseek-r1:14b | ollama | v2 frozen `f31d4631…` (54 cases) | 3 | 54 | M2 cross-model pilot (ROADMAP §4): DeepSeek leg, local via Ollama on the host GPU. Pre-registered before execution per rule 1. | no external model API charge (162 calls, 6 errors) | `deepseek-r1-14b-m2pilot-3runs.json` |

| X17 | 2026-08-23 | authoritative | claude-sonnet-5 | claude | v3 frozen `81daa0b7a48259184a91c48ab1dcf17c9d3ed4902fa891b5895db0f29fd79790` (37 cases) | 3 | 37 | M3 hard benchmark (ROADMAP §4): Sonnet leg against the frozen v3 corpus, per the preregistered measurement contract in `eval/cases-v3/README.md`. Pre-registered before execution per rule 1 (commit `4a53b394`, pushed 2026-08-24T02:55:35Z); executed 2026-08-23 20:24–21:19 PDT; result recorded after completion. Detected 85/87, clean FP 21/24, 2 errors — see `M3-HARD-SCORECARD.md`. | $5.335879 (111 calls, 2 errors) | `claude-sonnet-5-m3hard-3runs.json` (sha256 `3ebc1973…2944ab`) |
| X18 | 2026-08-23 | authoritative | qwen3.6:27b | ollama | v3 frozen `81daa0b7a48259184a91c48ab1dcf17c9d3ed4902fa891b5895db0f29fd79790` (37 cases) | 3 | 37 | M3 hard benchmark (ROADMAP §4): Qwen leg, local via Ollama on the host GPU, same frozen fingerprint and contract as X17. Pre-registered before execution per rule 1 (commit `4a53b394`); executed 2026-08-23 20:24–21:09 PDT; result recorded after completion. Detected 82/87, clean FP 19/24, 6 errors — see `M3-HARD-SCORECARD.md`. | no external model API charge (local compute time is not free) (111 calls, 6 errors, 2491.6s local model execution) | `qwen3.6-27b-m3hard-3runs.json` (sha256 `03303361…3a94`) |
| X19 | 2026-08-23 | authoritative | deepseek-r1:14b | ollama | v3 frozen `81daa0b7a48259184a91c48ab1dcf17c9d3ed4902fa891b5895db0f29fd79790` (37 cases) | 3 | 37 | M3 hard benchmark (ROADMAP §4): DeepSeek leg, local via Ollama on the host GPU after X18 released it, same frozen fingerprint and contract as X17. Pre-registered before execution per rule 1 (commit `4a53b394`); executed 2026-08-23 21:09–21:13 PDT; result recorded after completion. Detected 12/87, clean FP 4/24, 2 errors — see `M3-HARD-SCORECARD.md`. | no external model API charge (local compute time is not free) (111 calls, 2 errors, 208.9s local model execution) | `deepseek-r1-14b-m3hard-3runs.json` (sha256 `b036f7b0…dd76`) |

## Registering a run

Before executing an authoritative run, add a row with status
`authoritative`, the corpus fingerprint you intend to use, and the
purpose. After it completes, fill in the measured cost and output path.
If it fails, change the status to `failed` and leave the row.

## Rules

1. **No unregistered authoritative runs.** A result whose row was added
   after the numbers were seen is provisional at best.
2. **No deletions.** Superseded rows are marked, not removed.
3. **No best-of-N.** Repeats of the same configuration are separate
   rows; conflicting outcomes stay visible.
4. **Costs are measured or absent.** Local runs record "no external
   model API charge" — never "free" (see §24 of the methodology on cost
   dimensions).
