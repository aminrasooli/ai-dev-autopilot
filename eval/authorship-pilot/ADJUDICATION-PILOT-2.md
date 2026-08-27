# Second authorship pilot — adjudication

Preregistered in [`PREREGISTRATION-PILOT-2.md`](PREREGISTRATION-PILOT-2.md)
before `reviewer.authorpilot` was changed and before any output was seen.
Raw records: [`attempts-pilot2/`](attempts-pilot2/). Pilot 1 lives in
[`attempts/`](attempts/) and [`ADJUDICATION.md`](ADJUDICATION.md) and is
untouched.

**4 attempts, exactly as preregistered. 3 schema+syntax valid. 1 survived
adjudication.**

| attempt | model | requested | tool status | adjudication |
|---|---|---|---|---|
| `qwen-pilot-python-1787723479` | qwen3.6:27b | python / resource-leak | ready | **READY-CANDIDATE** |
| `qwen-pilot-javascript-1787723990` | qwen3.6:27b | javascript / logic-error | rejected-malformed | REJECTED-MALFORMED |
| `deepseek-pilot-python-1787724314` | deepseek-r1:14b | python / concurrency | ready | REJECTED-SEMANTICS |
| `deepseek-pilot-javascript-1787724466` | deepseek-r1:14b | javascript / contract-mismatch | ready | REJECTED-SEMANTICS |

Surviving proposal: **1** —
`eval/proposals/cases/qwen-pilot-python-1787723479.json`. It is a
**proposal, not an admitted case**; nothing was written into `eval/cases*`.

## Did the interface change work? Mechanically, yes

Comparing like with like, on the mechanical criteria the interface change
targeted:

| | pilot 1 (n=5) | pilot 2 (n=4) |
|---|---|---|
| schema-valid | 2/5 | 3/4 |
| authored source syntactically valid | 0/5 verified | 3/4 verified |
| diff coherent and applies cleanly | 0/5 | 3/4 |
| survives full adjudication | 0/5 | **1/4** |

The three `severity` malformations and the two byte-identical `-`/`+`
pairs that dominated pilot 1 did not recur once. n is far too small for a
rate; the claim is only that the specific failure modes the change
targeted stopped appearing.

**A new failure mode appeared, and it is the interesting one:** two of the
three mechanically-valid attempts have **inverted ground truth**. See
below. Removing the mechanical burden did not make the models better at
the semantic contract — it made the semantic errors visible, because they
were no longer hidden behind a malformed diff.

---

## `qwen-pilot-python-1787723479` — READY-CANDIDATE (survived)

A temp-file handler whose `finally:` block has `os.unlink(path)` replaced
with `pass # TODO: remove this file`, leaking every temporary file it
creates.

Checked against all nine preregistered criteria:

1. **Non-Claude authored** — ✓ qwen3.6:27b wrote `before`, `after`,
   `defect`, `category`, `severity`, `explanation`, `title`, `file_path`.
   The harness produced only the unified diff and `affected_files`.
2. **Syntax valid** — ✓ both `before` and `after` parse (`ast.parse`).
3. **Meaningful difference** — ✓ `os.unlink(path)` → `pass`.
4. **Diff coherent** — ✓ verified beyond generation: the harness diff was
   applied with `patch -p1` to the model's own `before` source and the
   result is byte-identical to the model's own `after` source.
5. **Claimed status true** — ✓ the change genuinely introduces a resource
   leak; the temp file is now never removed.
6. **Category and severity defensible** — ✓ `resource-leak` is exactly
   right. `["low","medium"]` is on the lenient side for unbounded temp-file
   accumulation but is defensible.
7. **Explanation agrees with the code** — mostly. See caveat 2.
8. **Schema validates** — ✓ `bin/review-propose validate-cases` passes with
   no warning on this file.
9. **No material Claude repair** — ✓ `claude_touched: false`; nothing in
   the model's output was edited.

**Two caveats a human must weigh before any admission** (neither is
disqualifying at proposal stage, and neither was fixed):

1. **The defect is very obvious.** `pass # TODO: remove this file` is a
   self-announcing tell; any reviewer will catch it. The harness defaulted
   `difficulty` to `moderate`; honest labelling is closer to
   `obvious-local`. The provenance notes already state that `difficulty`
   was defaulted by the harness and not judged by the model, and that a
   human must set it before admission.
2. **The explanation is slightly narrower than the code.** It says the
   `finally` block "now does nothing when an exception occurs" — it does
   nothing on *every* path, not only the exception path. The mechanism
   described is correct; the scope is understated. Not corrected, because
   the explanation is model-authored content.

Also noted, and **not** a second seeded defect: `path` is assigned inside
the `try` but read in the `finally`, so if `tempfile.mkstemp` itself
raised, the `finally` would hit `NameError`. That flaw is present
identically in `before` and `after`, so the *change* does not introduce
it. It is a wart in the surrounding code the model wrote, not a hidden
second defect in the diff.

---

## `qwen-pilot-javascript-1787723990` — REJECTED-MALFORMED

`ValueError: model output missing boolean 'defect'`.

The raw output is **valid JSON containing only 4 of the 9 required keys**
(`title`, `language`, `file_path`, `before`). Generation stopped partway
through the `before` array; `after`, `defect`, `category`, `severity` and
`explanation` were never written.

Root cause, and a genuine cost of this interface: Ollama was called with
`format: json`, whose grammar constraint forces syntactically valid JSON
**even when generation is truncated** — so a cut-off response arrives
looking well-formed rather than obviously broken. The daemon ran at the
default `num_ctx` of 4096, and pilot 2 asks for two complete files where
pilot 1 asked for one short hunk, roughly doubling the payload.

**This consumed the attempt and was not retried.** The preregistration
allows a retry only for a transport failure *before* a model response; the
model responded, so this is an attempt outcome. Raising `num_ctx` is an
obvious next lever and was deliberately **not** pulled today — that would
be tuning mid-experiment.

---

## `deepseek-pilot-python-1787724314` — REJECTED-SEMANTICS

Schema-valid, syntax-valid (both versions parse), diff coherent. Rejected
on ground truth.

The diff **adds** `with self.lock:` around `get_count`'s body — that is a
*fix* for a race condition. The model labelled it `defect: true`, and its
own explanation says so out loud: *"The original code exposed a race
condition… The fixed version ensures thread safety."*

The benchmark's contract is that `defect: true` means **the change under
review introduces a defect**. Here the change removes one. A reviewer shown
this diff would correctly say "this is a proper fix" and be scored **wrong**
against inverted ground truth — a case that actively punishes correct
review.

Not repaired. Swapping `before` and `after` would take one line and would
produce a usable case, and it is exactly the edit that must not happen: it
inverts the model's own stated judgment while keeping
`author_family: deepseek` (`docs/ROADMAP.md` §9 failure mode 3,
`docs/M4_DESIGN_BRIEF.md` §B). The honest outcomes are reject, re-ask, or
relabel `mixed`.

---

## `deepseek-pilot-javascript-1787724466` — REJECTED-SEMANTICS

The identical failure, independently: `numbers.reduce((acc, curr) => acc + curr)`
→ `numbers.reduce((acc, curr) => acc + curr, 0)`. Adding the initial value
is the **fix** for `reduce` on an empty array; the model labelled it
`defect: true` and its explanation again states plainly that *"The after
version fixes this."*

Same disposition, same reason: not repaired.

---

## The finding worth carrying forward

**DeepSeek inverted the ground-truth polarity on both of its attempts**,
consistently authoring "before = buggy, after = fixed" and then labelling
the change defective. Qwen did not make this error on the attempt that
completed.

The authoring prompt does state the contract — *"Either the change
introduces exactly one defect, or it is a clean change with no defect at
all"* — so this is not simply an under-specified prompt. But it is a
predictable misreading: "author a case with a defect in it" reads naturally
as "show me a bug and its fix", which is the shape of most training data
about code review.

The obvious next levers are a more explicit prompt (*"the AFTER version must
be the buggy one"*) and a larger `num_ctx`. **Neither was applied today.**
The preregistration fixed one interface change and one pilot; a third
iteration chosen after seeing these results would be exactly the post-hoc
tuning this preregistration exists to prevent. Whether to spend another
iteration is a human decision.

## Self-authorship rule

Unchanged and now load-bearing for the first time, because a Qwen-authored
proposal exists: **Qwen must never be scored as a reviewer against
Qwen-authored cases**, and DeepSeek never against DeepSeek-authored ones
(`docs/BENCHMARK_METHODOLOGY.md` §10, `docs/M4_DESIGN_BRIEF.md` §B). The
surviving proposal is not in any scored corpus, so nothing is at risk yet;
this becomes an active constraint the moment a human admits it.

## What this does NOT establish

One surviving case is not Pillar B. M4-B asks for a corpus of non-Claude
authored cases; there is one proposal, unadmitted, from n=4. No benchmark
headline, no per-model authoring rate, and no claim that either model
"can" or "cannot" author benchmark cases follows from nine total attempts
across two interfaces on CPU-only hardware.
