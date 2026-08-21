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
| X6 | 2026-08-20 | provisional | claude-sonnet-5 | claude | v2 pilot `56e4a32f…` | 3 | 57 | full-corpus variance evidence ahead of ground-truth approval | see report | `claude-sonnet-5-v2pilot-3runs-provisional.json` |
| X7 | 2026-08-20 | provisional | qwen3.6:27b | ollama | v2 pilot | 3 | 57 | local baseline, host night job | no external model API charge | pending |
| X8 | 2026-08-20 | provisional | deepseek-r1:14b | ollama | v2 pilot | 3 | 57 | second local model for context | no external model API charge | pending |

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
