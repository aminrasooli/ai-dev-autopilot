# Second authorship pilot — preregistration

**Frozen 2026-08-25, before `reviewer.authorpilot` was modified and before
any second-pilot output was generated.** Nothing below was edited after a
model response was seen; the results section is deliberately absent and
lives in `ADJUDICATION.md`.

Not registered in `eval/EXPERIMENTS.md`: that table registers *scoring*
runs of a reviewer against a fingerprinted corpus (model, corpus
fingerprint, runs, cases, cost). An authoring pilot measures none of
those and has no corpus fingerprint to name, so forcing a row in would
misrepresent what it is. The preregistration discipline (`EXPERIMENTS.md`
§Rules 1–3: register before execution, no deletions, no best-of-N) is
applied here in full.

## Why a second pilot at all

The first pilot ran 5 live attempts and produced 0 usable cases
(`ADJUDICATION.md`). The audit of those 5 attempts found the failures were
overwhelmingly **mechanical, not conceptual** — see "First-pilot failure
classification" below. The bounded question this second pilot asks is
narrow:

> When the mechanical serialization burden is removed from the model, do
> these same two models produce usable cases?

It is not "can we get a passing case out of these models eventually."
That is why the attempt count is fixed in advance and there are no
output-driven retries.

## First-pilot failure classification (from the audit, before any change)

Per-attempt, deterministic checks where available (`ast.parse` for Python,
`node --check` for JavaScript; no Go toolchain exists on this host):

| attempt | model | req lang | schema | authored-source syntax | dominant failure |
|---|---|---|---|---|---|
| `qwen-pilot-python-1787717340` | qwen | python | valid | **after INVALID** (`unexpected indent`), before valid | C code syntax |
| `qwen-pilot-go-1787717692` | qwen | go | **invalid** (`severity` reversed) | not checkable (no Go toolchain) | E schema formatting |
| `deepseek-pilot-python-1787717951` | deepseek | python | **invalid** (`explanation` empty) | both valid | A idea + D no-op diff |
| `deepseek-pilot-javascript-1787718044` | deepseek | javascript | valid | parses once the hunk's truncated braces are supplied | D diff construction |
| `qwen-pilot-go-1787718214` | qwen | go | **invalid** (`severity` one-element) | not checkable | E schema + D no-op pair |

**Dominant failure: F (mixed), concentrated in D (diff construction) and E
(schema formatting).**

- **E alone caused 3 of 5 rejections**, all on the single `severity` field,
  malformed a different way each time (`["critical","high"]` reversed,
  `["medium"]` one-element, and `explanation` omitted entirely).
- **D affected 3 of 5**: two byte-identical `-`/`+` pairs, and one hunk that
  inserts an unclosed function above a context line.
- **C caused 1** (Qwen's Python `IndentationError` — a genuine failure to
  write valid code, caused by editing one line of a `with` block without
  re-indenting its body).
- **A caused 1** (DeepSeek Python: claimed a missing-increment infinite loop
  in code containing `i += 1`).

A correction to the earlier adjudication, found by this audit: DeepSeek's
JavaScript attempt was described as an unclosed arrow function, i.e. a
syntax failure. The fair reading is narrower — the emitted *hunk* is
truncated, and once its missing braces are supplied the source parses
(`node --check` exit 0). Its real defect is structural: the diff nests
`processUserInput` inside `sanitizeInput`, after a `return`. That is
**diff construction (D), not an inability to write JavaScript (C)**.

**What these 5 attempts do NOT establish.** Nothing about whether Qwen or
DeepSeek "can author code". n=5, one prompt, one interface, CPU-only. The
only safe claim is about *this interface*: under the first authoring
contract, these two models failed mechanically more often than
conceptually.

## Models

- `qwen3.6:27b` (Q4_K_M)
- `deepseek-r1:14b` (Q4_K_M)

Both already present at `/usr/share/ollama/.ollama/models`. **No downloads.**
If a model is absent at run time, its absence is recorded and the other
model proceeds.

## Attempt count — fixed

**Exactly 2 attempts per available model. 4 total. No output-driven retries.**

A transport failure *before a model response* (daemon unreachable, HTTP
error) may be retried once and does not consume the attempt. A malformed,
invalid, or semantically bad model *response* consumes the attempt. There
is no "one more try because it was close" — that is what happened in pilot
one, and re-rolling until something passes selects for luck and hides a
survivorship bias nothing downstream can see.

## Task pairs — fixed before generation

| model | attempt 1 | attempt 2 |
|---|---|---|
| qwen3.6:27b | python / resource-leak | **javascript / logic-error** |
| deepseek-r1:14b | python / concurrency | javascript / contract-mismatch |

**One deliberate substitution, made now and not after seeing a result:**
Qwen's second slot was go / logic-error in the first pilot and in the
default plan. **Go is replaced by JavaScript** because this host has no Go
toolchain — `go` and `gofmt` are both absent — so an authored Go source
could not be syntax-checked deterministically. The entire point of this
bounded change is to make authored source machine-checkable before a human
reads it; running an unverifiable language would defeat it. The category
(`logic-error`) is unchanged, so the substitution swaps only the language,
not the difficulty target. Installing a Go toolchain for a 2-attempt pilot
is out of scope.

Languages are therefore Python and JavaScript only — the two with
deterministic local checkers (`ast.parse`, `node --check`).

## Success criterion — a candidate counts only if ALL hold

1. Substantive content is genuinely non-Claude authored.
2. Authored source is syntactically valid (before **and** after).
3. Before and after differ **meaningfully** (not byte-identical, not
   whitespace-only).
4. The generated unified diff is coherent and applies to the authored
   before-source.
5. The claimed defective/clean status is actually true of the code.
6. Category and severity are defensible.
7. The explanation agrees with the code.
8. The proposal schema validates.
9. **No material Claude repair occurred.**

No quota forcing. If zero candidates survive, the result is zero.

## Prohibited during this pilot

- Changing the prompt, category, language, or model after seeing any
  second-pilot output.
- Any third interface iteration today.
- Repairing a failed attempt and counting it.
- Writing anything into `eval/cases*`. Proposals stop at
  `eval/proposals/cases/`; admission to a scored corpus is a human gate.
- Scoring Qwen as a reviewer against Qwen-authored cases, or DeepSeek
  against DeepSeek-authored cases.

## Decision rule — chosen before results

- **B-1 INTERFACE FIX WORKED** — ≥1 candidate survives all 9 criteria.
- **B-2 MIXED** — mechanical validity measurably improves (syntax/diff/schema
  failures drop) but no candidate survives semantic adjudication.
- **B-3 FAILED** — no material improvement in useful output.

B-2 and B-3 both mean: stop tuning, and take the literal Pillar-B
requirement back to a human for an explicit keep/change decision. Pillar B
is not removed because a pilot failed.
