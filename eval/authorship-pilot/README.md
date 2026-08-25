# Non-Claude authorship pilot — attempt log

M4-B (`docs/ROADMAP.md` §4, `docs/M4_DESIGN_BRIEF.md` §B). Attempt
records from `reviewer.authorpilot` land in `attempts/` here — one JSON
file per run, whether the model's output was usable or not. This
directory is a **pilot log, not intake**: a `ready` attempt's `proposal`
field is something a human copies into `eval/proposals/cases/`
deliberately, never something a script moves there automatically.

## Status as of this session: blocked, zero attempts run

`reviewer.authorpilot` and its test suite
(`reviewer/tests/test_authorpilot.py`, 14 tests, all passing against a
mocked transport) were built and verified this session. A live attempt
was tried and failed exactly as it should when infrastructure is
missing:

```
$ python3 -m reviewer.authorpilot run --model qwen3.6:27b --author-family qwen \
    --language python --category resource-leak --out-dir eval/authorship-pilot/attempts
error: could not reach model 'qwen3.6:27b' at http://127.0.0.1:11434:
cannot reach http://127.0.0.1:11434/api/generate: <urlopen error [Errno 111] Connection refused>
```

Root cause, checked directly: `ollama serve` cannot even start in this
session's environment (`mkdir ~/.ollama/models: read-only file
system`), and no models are pulled (`~/.ollama/models` does not exist).
This is the same host-GPU dependency M2 and M3's Qwen/DeepSeek legs
already had (`eval/EXPERIMENTS.md` X15/X16/X18/X19 all ran "local via
Ollama on the host GPU") — it is a real environment boundary in this
particular execution session, not a bug in the pilot tool.

**No attempt files exist in `attempts/` because no model was ever
reached.** Fabricating a plausible-looking Qwen/DeepSeek-authored case
to fill this directory would be exactly the failure this whole pipeline
exists to prevent (docs/ROADMAP.md §9 failure mode 3: Claude may not
silently author ground truth and relabel it as another author's) — so
nothing was fabricated, and this directory ships empty except for this
README.

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
`proposal_id` becomes the filename stem) and validate with
`bin/review-propose validate-cases eval/proposals/cases` — no such
`bin/review-propose` wrapper exists yet; use
`python3 -m reviewer.propose validate-cases eval/proposals/cases` until
one is added, which is a trivial follow-up in the same style as
`bin/review-corpus`/`bin/review-realbug`, not done in this session to
keep this session's file count proportionate to what it could actually
exercise.
