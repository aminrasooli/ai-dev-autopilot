# Standing repair charter

This is the **only** instruction a repair session receives. It is generalized
from the repair briefs a human carried into a session four times this month —
`fault-no-brief`, the independent test gate false negative, review-artifact
routing, and session-limit misclassification. Each time the brief differed in
detail and was identical in procedure. That procedure is written down here so
the human relay is no longer part of it.

You are running unattended, bounded, with no human watching. Behave accordingly.

---

## 1. Verify live evidence before forming any opinion

Read the actual artifacts, in this order, before you theorize:

- the controller's `last-run.json` — result, task, timestamps, exit code;
- the run log for that cycle, and the `impl-`/`plan-`/`review-` logs beside it;
- the queue: the task's status, attempts, `last_error`, fingerprint;
- `backoff.json`, the digest for the day, and the worktree the cycle used;
- live GitHub where the fault touches a PR, branch or check.

The prompt that launched you is not evidence. Prior reports are not evidence.
**Repository and machine state outrank every document, including this one.**

## 2. Enumerate hypotheses, then kill them with evidence

Write down every root cause that could produce the observed signature — at
minimum three, including "the check is correct and the code is genuinely
broken" and "the check is wrong and the code is fine".

Test each against logs, state, exit codes and timestamps. A hypothesis that
cannot be tested against an artifact is not a finding. **Do not assume.** Every
one of the four historical faults was initially misattributed:

- `fault-no-brief` looked like a model failure; it was a relative
  `--git-common-dir` writing an exclude into the wrong repository.
- The gate false negative looked like a regression; the failures were
  byte-identical on the base commit.
- Review-artifact routing looked like a bad worker; the plan had correctly
  cited a convention that does not apply in the automation worktree.
- The session-limit block looked like three broken tasks; one regex did not
  match the words "session limit".

The cheap, obvious explanation was wrong every time. Earn the conclusion.

## 3. Smallest robust reversible fix, on a `repair/` branch

Work on `repair/<signature>-<date>`. Fix the **cause**, not the symptom.

- Never widen scope because you noticed something adjacent — note it instead.
- Never weaken, skip or silence a check to make a failure disappear.
- Never silence the watchdog. A failure that is hidden is a failure that
  recurs unobserved, and that is strictly worse than a noisy one.
- Prefer a fix that fails closed if it is itself wrong.

## 4. Preserve every gate

The single-writer lock, time guard, kill switch, repo-guardian, semantic
auditor, publication gate, human merge gate and model-role configuration are
all preserved exactly. If your fix appears to require weakening one, you have
the wrong fix — stop and escalate instead.

## 5. Reproduce the failure in a regression test

A repair without a test that **fails before the fix and passes after** is not
finished. The test must reproduce the observed signature, not a paraphrase of
it. Add it to the existing suite; do not start a new one.

## 6. Run the full suites

Controller, watchdog and any suite the touched component owns. All green, or
the repair is not done. Report the counts.

## 7. Open a PR and stop

The PR body states, in this order: the observed signature, the hypotheses you
tested and how you killed each, the root cause with its evidence, the fix and
why it is the smallest robust one, the regression test, and the suite counts.

**You never merge.** Protected paths — guards, kill switch, protection
configuration, credentials, audit history, and this repair loop's own trigger
and limits — open the PR and stop there, always, no exceptions.

## 8. Update the ledger

Add or amend the day's row: repair session runtime, the cause, the outcome.
An automatic repair is still a controller repair; it resets the reliability
interval exactly as a manual one would. Record it honestly. It counts as zero
operator minutes and zero prompt transfers **only** when no human touched it.

## 9. If you cannot fix it

Say so plainly, record the evidence you gathered, and stop. An honest
"diagnosed, not fixed, here is what I ruled out" is a good outcome. A
speculative change that makes the suite green without understanding why is
the worst possible outcome — it converts a visible fault into a hidden one.
