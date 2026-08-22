# Case proposals and independent audits

Intake area for material this project did **not** author. Nothing here
is part of the scored benchmark: `eval/cases/` is the corpus, and cases
enter it only when a human moves them there.

Why this exists: the corpus is currently 100% Claude-authored while
Claude models are among those evaluated. That is the single biggest
credibility problem, and the only real fix is other authors. This
directory is the safe door for them.

## Two formats

**Case proposal** — one JSON file per proposal:

```json
{
  "proposal_id": "qwen-2026-08-a1",
  "author_family": "qwen",
  "generator": "qwen3.6:27b",
  "status": "proposed",
  "rationale": "corpus has one concurrency case in Java and none in Rust",
  "case": { "...": "a complete schema-v2 case object" }
}
```

The embedded `case` must satisfy the real corpus schema — a proposal
that could not become a case is not useful — and its
`provenance.author_family` must match the proposal's.

**Audit opinion** — an independent read of an *existing* case's answer
key, as `{"audits": [...]}`:

```json
{"case_id": "27-ts-nullish-to-or",
 "defect_opinion": "defect",
 "category_opinion": "logic-error",
 "severity_opinion": "medium",
 "confidence": 0.7,
 "disagrees_with_ground_truth": true,
 "suspected_fixture_flaw": false,
 "rationale": "the || coercion changes behaviour only for retries: 0"}
```

## Validate

```sh
python3 -m reviewer.propose validate-cases  eval/proposals/cases
python3 -m reviewer.propose validate-audits eval/proposals/audits/<file>.json
```

## Rules

1. **Proposals are not cases.** Admission is a human act: validate,
   adjudicate, then move the case into `eval/cases/` with its provenance
   intact.
2. **An audit opinion is evidence, never a verdict.** "Model X disagrees"
   is a reason for a human to look again — the model may simply be
   wrong. Ground truth is never changed automatically, and never in
   response to a model's score.
3. **Never point a model at the answer key it is auditing.** An audit
   asks for an independent read of the diff; supplying the current
   ground truth first would produce agreement, not evidence.
4. **Tag everything.** `author_family` and `generator` are required so
   authorship can be sliced in analysis rather than assumed away.
