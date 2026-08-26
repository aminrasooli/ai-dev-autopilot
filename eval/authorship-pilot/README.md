# Non-Claude authorship pilot — attempt log

M4-B (`docs/ROADMAP.md` §4, `docs/M4_DESIGN_BRIEF.md` §B). Attempt
records from `reviewer.authorpilot` land in `attempts/` here — one JSON
file per run, whether the model's output was usable or not. This
directory is a **pilot log, not intake**: a `ready` attempt's `proposal`
field is something a human copies into `eval/proposals/cases/`
deliberately, never something a script moves there automatically.

## Status: the pilot has now run live — 5 attempts, 0 usable cases

An earlier session recorded this pilot as blocked, because `ollama serve`
could not start in that session's environment. That is no longer the
situation and this section supersedes it: both models were reached, and
`attempts/` now holds real records.

| model | requested | tool status | adjudication |
|---|---|---|---|
| qwen3.6:27b | python / resource-leak | ready | rejected |
| qwen3.6:27b | go / logic-error | rejected-invalid-schema | rejected |
| deepseek-r1:14b | python / concurrency | rejected-invalid-schema | rejected |
| deepseek-r1:14b | javascript / contract-mismatch | ready | rejected |
| qwen3.6:27b | go / logic-error (re-ask) | see `attempts/` | see [`ADJUDICATION.md`](ADJUDICATION.md) |

**Proposals produced: 0.** Nothing was copied into `eval/proposals/cases/`,
so M4-B still has no admitted content — the pilot is live, the pillar is
not. Per-attempt reasoning is in [`ADJUDICATION.md`](ADJUDICATION.md).

Two of these attempts carry tool status `ready`. That means only that the
model's JSON validated against the case schema; both were still rejected
on reading, because their post-diff files do not parse (a Python
`IndentationError` and an unclosed JavaScript arrow function). **A `ready`
attempt is not a usable case**, and the gap between those two statements is
why `ADJUDICATION.md` exists alongside the raw records.

Nothing here was repaired. One attempt failed on a two-character schema
detail (severity emitted as `["critical","high"]` instead of
`[min, max]`) and was still rejected rather than fixed: editing a model's
output while keeping its authorship label is precisely the failure mode
this pipeline exists to prevent (`docs/ROADMAP.md` §9 failure mode 3). The
honest response to a failed attempt is to re-ask the model, which is what
the fifth row is.

### Execution environment for these attempts

Local, via Ollama, `qwen3.6:27b` (Q4_K_M) and `deepseek-r1:14b` (Q4_K_M),
both already present on the host — this tool never downloads a model.
Unlike the M2/M3 reviewer legs (`eval/EXPERIMENTS.md` X15/X16/X18/X19,
"local via Ollama on the host GPU"), **these attempts ran CPU-only**;
Ollama reported `total_vram="0 B"` and scheduled to CPU. That affects
latency only, not output, and no timing number from this pilot should be
compared against the X15–X19 GPU figures.

## Exact handoff to run the pilot for real

From a session/host with a running local Ollama daemon and both models
pulled (`ollama pull qwen3.6:27b`, `ollama pull deepseek-r1:14b` — this
tool never pulls a model itself):

```sh
bin/review-authorpilot run --model qwen3.6:27b --author-family qwen \
  --language python --category resource-leak \
  --out-dir eval/authorship-pilot/attempts
bin/review-authorpilot run --model deepseek-r1:14b --author-family deepseek \
  --language python --category concurrency \
  --out-dir eval/authorship-pilot/attempts
```

Repeat with different `--language`/`--category` pairs for a handful of
attempts per model (docs/M4_DESIGN_BRIEF.md §B calls for "a small pilot
candidate set," not volume). Then, for each `ready` attempt: read the
`proposal` field, decide whether it's worth pursuing, and if so copy
just that object into a new file under `eval/proposals/cases/` (its
`proposal_id` becomes the filename stem) and validate with:

```sh
bin/review-propose validate-cases eval/proposals/cases
```

**Copying is the whole point of that step.** A `ready` attempt is a
model's proposal, not an admission: it reaches `eval/proposals/cases/`
only because a human decided it was worth reviewing, and it reaches
`eval/cases*` only after a second, separate human decision. If the
attempt needs material rewriting to be usable, the honest outcomes are
to reject it, ask the same model again, or relabel it
`author_family: mixed` with a `provenance_notes` line saying what
changed — never to fix it quietly and keep the original authorship
label.
