# Non-Claude authorship pilot — adjudication log

M4-B (`docs/ROADMAP.md` §4, `docs/M4_DESIGN_BRIEF.md` §B). One entry per
attempt in [`attempts/`](attempts/). `reviewer.authorpilot` decides only
whether an attempt is *schema-valid*; whether it is a **usable case** is
a separate, human-readable judgment, and that judgment is this file.

A `ready` status in an attempt record therefore means "the JSON validated",
not "this is a good case". Two of the attempts below are `ready` and both
are rejected here — that gap is the reason this file exists.

## What each attempt was checked against

Every `ready` attempt was independently checked for: actual authored
language vs. requested; unified-diff coherence (hunk headers, markers,
whether the post-diff file parses); whether the claimed defect really
exists; category correctness; severity defensibility; explanation
accuracy; `affected_files` accuracy; a hidden second defect; and answer
leakage.

**Answer leakage was checked once, for the class, and is not a live
risk:** `reviewer.prompt.build_review_prompt(diff_text, context)` is
handed the diff only. A case's `title`, `ground_truth.explanation`,
`category` and `severity` never reach a reviewer, so a self-describing
title like "File handle not closed in write_log function" cannot leak an
answer through the scoring path. It is still a documentation smell, not a
scoring defect.

## Attempts

| attempt | model | requested | tool status | adjudication |
|---|---|---|---|---|
| `qwen-pilot-python-1787717340` | qwen3.6:27b | python / resource-leak | ready | **rejected** |
| `qwen-pilot-go-1787717692` | qwen3.6:27b | go / logic-error | rejected-invalid-schema | **rejected** |
| `deepseek-pilot-python-1787717951` | deepseek-r1:14b | python / concurrency | rejected-invalid-schema | **rejected** |
| `deepseek-pilot-javascript-1787718044` | deepseek-r1:14b | javascript / contract-mismatch | ready | **rejected** |
| `qwen-pilot-go-1787718214` | qwen3.6:27b | go / logic-error (re-ask) | rejected-invalid-schema | **rejected** |

Surviving proposals: **0**. Nothing was copied into `eval/proposals/cases/`.

Five attempts, not four: the fifth is the single permitted re-ask of the
same model after the first four all failed for model-output reasons. It
was spent on Qwen/Go, the attempt that had come closest. No further
attempts were run — a pilot that keeps re-rolling until something passes
is selecting for luck, and the resulting case would carry a survivorship
bias nothing downstream could see.

---

### `qwen-pilot-python-1787717340` — rejected

Tool status `ready`; the JSON validated against the case schema. Rejected
on adjudication for three independent reasons.

1. **The post-diff file is not valid Python.** The diff replaces
   `with open(filename, 'a') as f:` with `f = open(filename, 'a')` but
   leaves the following `f.write(...)` line at its original, deeper
   indentation. Reconstructed and parsed: `SyntaxError: unexpected
   indent`. A reviewer shown this diff would correctly report a syntax
   error, not the seeded resource leak, so the case cannot measure what
   its ground truth claims to measure.
2. **The unified diff is malformed.** Context lines carry no leading-space
   marker, so context is indistinguishable from indentation. Both hunk
   headers are wrong: `@@ -12,7 +12,7 @@` describes 6 old / 6 new actual
   lines, and `@@ -20,6 +20,7 @@` describes 4 old / 5 new.
3. **An undeclared second change.** The second hunk adds `return result`
   to `process_data`, unrelated to the stated resource leak and unmentioned
   in the explanation. The corpus is single-seeded-defect by construction.

What was *right*: the language matched, the intended defect is a real
resource leak, `affected_files` matches the diff paths, and
`resource-leak` / `["medium","medium"]` are both defensible for the
defect the model intended.

### `qwen-pilot-go-1787717692` — rejected

Tool status `rejected-invalid-schema`:
`ground_truth.severity must be [min, max] from the scale`. The model
emitted `["critical", "high"]` — the scale reversed.

Substantively this was the **strongest** of the five attempts: coherent
Go, a genuinely real off-by-one (`items[len(items)]` instead of
`items[len(items)-1]`, a real index-out-of-range panic), correct
`logic-error` category, and an accurate explanation.

It is still rejected, and deliberately not repaired. Swapping two severity
strings is a two-character edit — and it is exactly the edit that must not
happen. `provenance.provenance_notes` on a pilot case asserts that
"category, severity and explanation are the model's own, unmodified".
Reversing the severity and keeping `author_family: qwen` would make that
sentence false (`docs/ROADMAP.md` §9 failure mode 3). The honest options
are to re-ask the model or to relabel the case `mixed` — a re-ask was
used; see below.

### `deepseek-pilot-python-1787717951` — rejected

Tool status `rejected-invalid-schema`: `ground_truth.explanation must be
non-empty` — the model omitted the field entirely.

Independently worthless even had the field been present:

- **The diff is a no-op.** Its only changed pair is
  `-def process_data(data):` / `+def process_data(data):` — byte-identical.
- **The claimed defect does not exist.** The title claims an infinite loop
  from a missing increment; the code shown contains `i += 1`.
- **The category is wrong.** `concurrency` was the requested hint and the
  model echoed it, but an infinite loop in straight-line code is not a
  concurrency defect. This is hint-following, not authoring.

### `deepseek-pilot-javascript-1787718044` — rejected

Tool status `ready`; the JSON validated. Rejected on adjudication.

1. **The post-diff file is not valid JavaScript.** The added arrow
   function `const sanitizeInput = (input) => {` is never closed; the
   pre-existing `function processUserInput(input) {` is a *context* line
   sitting inside that unterminated body. `node --check` on the
   reconstructed result: `SyntaxError: Unexpected end of input`.
2. **The hunk header is wrong.** `@@ -1,4 +1,6 @@` against an actual 2 old
   / 4 new lines.
3. **Title and ground truth contradict each other.** The title claims
   "potential security vulnerabilities" from incorrect input handling; the
   explanation claims the opposite failure — *over*-sanitization causing
   data loss. A case whose own two descriptions disagree has no usable
   ground truth. (Only the explanation is scored, but the disagreement is
   evidence the model did not hold one scenario in mind.)

`affected_files` matched, severity ordering was valid, and the
over-sanitization observation is a real class of bug — it is the diff, not
the idea, that fails.

### `qwen-pilot-go-1787718214` — rejected (the re-ask)

Tool status `rejected-invalid-schema`: `ground_truth.severity must be
[min, max] from the scale`. The model emitted `["medium"]` — a
one-element list this time, having emitted a reversed two-element list on
the first Go attempt. Two different malformations of the same field in
two attempts.

Substantively weaker than the attempt it was re-asking, not stronger:

- **A no-op change pair.** The first hunk's
  `-return src[len(src)-n:]` / `+return src[len(src)-n:]` is
  byte-identical on both sides.
- **The explanation contradicts the function's own name.** It states that
  callers expect a *prefix* and that returning the last N elements is the
  bug — inside a function named `LastN`. Which behavior is correct is
  unresolvable from the case itself, so there is no usable ground truth.

This exhausted the re-ask allowance. The result is recorded as zero.

## Cross-cutting observation (not a headline metric)

Five attempts is far too small a sample for any claim about either model,
and none is made here. The one pattern worth recording for whoever runs
the next tranche: **most failures were mechanical, not conceptual.**
Several attempts had a coherent, real defect idea and failed on diff
construction (indentation, unclosed brace, wrong hunk counts, a
byte-identical `-`/`+` pair) or on one schema detail — `severity` alone
accounted for three rejections across two models, malformed a different
way each time.

That suggests the authoring prompt, not the models, is the next thing to
change — it asks for a hand-built unified diff, which is the part these
models are worst at. Deriving the diff from a before/after pair the model
writes instead would remove most of these failure modes. That is a change
to `reviewer.authorpilot`'s prompt, out of scope for this run, and it must
not be made by hand-fixing an existing attempt.

## Self-authorship rule

Per `docs/BENCHMARK_METHODOLOGY.md`, a model is never scored as a reviewer
against cases it authored: Qwen must not be evaluated against
Qwen-authored cases, DeepSeek not against DeepSeek-authored cases. No case
here reached a corpus, so the rule is not yet load-bearing — it becomes so
the moment one does.
