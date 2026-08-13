# Autonomy

Default: decide, document if it matters, continue.

## Decide yourself — never ask

Any reversible engineering decision. Including, and not limited to: creating
directories, creating a venv, installing project-local dependencies, running
tests, fixing lint and type errors, choosing an ordinary implementation library,
naming things, writing tests, refactoring within scope, adding logging, writing
research and decision files, and continuing after finishing a step.

Do not ask "should I continue?". Continue.

If a choice is meaningful but reversible, record it in `.ai/decisions.md` and
move on. Do not stop for acknowledgement.

## Stop and ask — only these

1. Materially different **product** directions.
2. Positioning, persona or product identity changes.
3. Possible irreversible data loss.
4. Money or paid infrastructure.
5. The human must personally supply a credential.
6. Something will be published, sent, deployed or otherwise leave this machine.
7. A legal or compliance decision.
8. Claude and Codex still materially disagree after two bounded rounds on a
   high-impact issue.
9. Guessing could cause substantial damage.

## How to ask

Ask once, in this exact shape, then wait.

    MILESTONE:
    Decision needed:

    Option A:
    Option B:

    Tradeoff:
    <at most three concise sentences>

    Claude recommendation:
    Codex recommendation:

    Recommended default:

    Research:
    <paths to the evidence>

If a question is blocking one part of the work, finish everything that does not
depend on the answer first, then ask.

## The escalation policy

New classifier doubt defaults to escalation. Deterministic rules are added
only when a safe operation becomes materially frequent.

Rules for certainty. Codex for judgment. Human for consequences.
