# Provenance corpus

M4 credibility evidence (`docs/ROADMAP.md` §4, `docs/M4_DESIGN_BRIEF.md`).
All cases live in the single flat directory [`cases/`](cases/) — the same
layout every other corpus uses, so the whole toolchain runs against it
unchanged:

```sh
bin/review-corpus --cases eval/cases-provenance/cases
bin/review-eval   --cases eval/cases-provenance/cases --backend fake
```

## What this corpus is

Cases whose **provenance** is the point: material this project did not
invent from nothing. The frozen v2 and v3 corpora are 100%
Claude-authored, seeded or authored-realistic, and say so
(`docs/BENCHMARK_METHODOLOGY.md` §10). That is the benchmark's single
largest credibility gap. This directory is where cases with a different
origin land after human adjudication.

Today it contains three tranches — **real historical bugs (M4-A)**,
**non-Claude authorship (M4-B)** and **human-written (M4-C)** — sliced
apart by `provenance.author_family` / `provenance.type` rather than by
directory, the way every future tranche will be.

## Relationship to the frozen corpora

This is a **separate, additional** corpus. It does not touch, extend, or
re-open either frozen corpus:

| corpus | path | fingerprint | status |
|---|---|---|---|
| v2 | `../cases/` | `f31d46310988f61c4534344ad05a52a4385fd15159126a0be85aad532f045690` | frozen, unchanged |
| v3 | `../cases-v3/cases/` | `81daa0b7a48259184a91c48ab1dcf17c9d3ed4902fa891b5895db0f29fd79790` | frozen, unchanged |
| provenance | `cases/` | `991ed01a6cea12195b0b8515e0c4f66bef5bc630def3ba41b9d9c5ee2422b5fc` | this corpus, **not frozen** |

Both frozen fingerprints are pinned by
`reviewer/tests/test_corpus.py::test_frozen_corpus_fingerprints_are_exact`,
so a single edited byte in either fails the suite rather than being
discovered when a published result is cited. No authoritative M1, M2 or
M3 result is affected by anything here.

This corpus is **not** frozen: it is expected to grow as the remaining
M4 pillars land, and its fingerprint above describes its current
contents only. It is deliberately not pinned by a test for that reason.
Any result ever run against it must record the fingerprint it actually
ran against — that is what makes two runs comparable
(`docs/BENCHMARK_METHODOLOGY.md` §11a). It becomes frozen only if and
when a freeze is declared here, the way v2 and v3 declare theirs.

## Schema and versioning note

All cases carry `benchmark_version: 2`, exactly like v3's cases do.
Adding cases changes a corpus **fingerprint**, not the schema version:
per `docs/BENCHMARK_METHODOLOGY.md` §11a, a version bump is reserved for
changes that invalidate previous results (a flipped label, a changed
category or severity, a new scoring algorithm, a changed prompt
contract). None of those happened. Scoring semantics, the category and
severity vocabularies, and the review prompt are untouched, and the
harness runs this corpus through the same `--cases DIR` path every other
corpus uses — there is no M4-only scoring path and no forked evaluator.

"M4" is a roadmap milestone. It is deliberately **not** a
`benchmark_version: 4`, and this directory is deliberately not named
`cases-v4`, so that a milestone number is never mistaken for a schema
version.

## Current contents — real historical bugs (M4-A)

4 cases, all defective, all `python`.

| id | source | license | category | difficulty |
|---|---|---|---|---|
| `flask-ipv6-partition-host-port` | pallets/flask | BSD-3-Clause | logic-error | moderate |
| `werkzeug-external-url-boolean-logic` | pallets/werkzeug | BSD-3-Clause | logic-error | subtle |
| `click-pager-windows-error-reporting` | pallets/click | BSD-3-Clause | error-handling | subtle |
| `apistar-staticfiles-resource-leak` | encode/apistar | BSD-3-Clause | resource-leak | moderate |

Distributions, as reported by `bin/review-corpus --json`:

- **Authorship**: `claude` = 4 (`author_model: claude-sonnet-5`). The
  reconstructions were written by Claude; only their *defect mechanisms*
  are historical. This tranche diversifies **provenance**, not
  authorship — M4-B is the pillar that diversifies authorship.
- **Provenance type**: `mined-real-fix` = 4.
- **Source license**: BSD-3-Clause = 4.
- **Transformation**: `transformed` = 4.

## Current contents — non-Claude authorship (M4-B)

1 case, defective, `python`.

| id | generator | category | difficulty |
|---|---|---|---|
| `qwen-pilot-python-1787723479` | qwen3.6:27b | resource-leak | obvious-local |

`provenance.type: seeded-synthetic`, `provenance.author_family: qwen`.
qwen3.6:27b wrote the complete before/after source, the defect, the
category, the severity and the explanation; the harness contributed only
the deterministic unified diff (`difflib`) and `affected_files`
restating the model's own `file_path`. Full survival record against all
nine preregistered criteria: `eval/authorship-pilot/ADJUDICATION-PILOT-2.md`
(`qwen-pilot-python-1787723479` — READY-CANDIDATE). The only field
changed before admission was `difficulty`, from the harness-defaulted
`moderate` to `obvious-local` — the model was never asked to judge
difficulty, and adjudication's own read of the defect (`pass # TODO:
remove this file`) called it a self-announcing tell.

## Transformation and licensing policy

Every case here is a **transformed reconstruction of a real historical
fix, not a verbatim copy of upstream source.** The defect mechanism is
reproduced; function names, file paths, and surrounding code are
invented. No upstream source line, comment, test, commit message, PR
title, or issue text is copied into a case — those routinely state the
answer outright, so keeping them out is a leakage rule as much as a
licensing one (`docs/M4_DESIGN_BRIEF.md` §A rules 3 and 4).

The licensing gate is enforced by the validator that actually admits
cases (`reviewer.corpus.validate_case`), not only by the advisory queue:
`transformation: verbatim` or `transformed` requires a known-permissive
`source_license`, and `mined-real-fix` requires `source_repository`,
`source_commit`, `source_license` and `transformation` to all be
present. A copyleft source can therefore only ever reach a scored corpus
as `synthetic-reconstruction`, which derives no code. See
`reviewer/tests/test_corpus.py` for the adversarial cases that hold this
closed.

Each case's `provenance` carries the exact upstream repository, commit
and license, so attribution survives even though no code was copied.

## How these were admitted

**M4-A:** `eval/realbug-queue/` (candidate) → `eval/proposals/cases/`
(proposal, PR #24) → human decision → here. Both hops are human
decisions by design; nothing is auto-admitted. The proposals are kept as
historical intake evidence with `status: accepted` and `reviewer_notes`
recording what adjudication found and what was corrected before
admission — three of the four needed a correction, and one earlier
reconstruction was rejected outright and rewritten. That trail is
deliberately not deleted now that the cases exist.

**M4-B:** `eval/authorship-pilot/` (live model attempt) →
`eval/proposals/cases/` (proposal) → adjudication against nine
preregistered criteria (`ADJUDICATION-PILOT-2.md`) → human decision →
here. Same two human-decision hops, different intake: the candidate is a
live model generation rather than a mined commit. The proposal is kept
the same way, `status: accepted` with `reviewer_notes` recording the one
correction made (`difficulty`) and confirming everything else is
unchanged model output.

## Limitations — read before citing anything from here

- **Four cases (M4-A) and one case (M4-B) are a process demonstration,
  not a measurement.** Neither tranche is large enough to move an
  aggregate metric, support a per-category claim, or characterise "real
  bugs" or "non-Claude authorship" in general. They prove the respective
  pipelines produce admissible, truthfully-labelled cases. Nothing more
  should be claimed from either.
- **No model has been evaluated against this corpus.** No preregistered
  experiment exists for it; there are no results in `eval/results/` for
  this fingerprint, and admission is not measurement.
- **M4-A: all four are Python, all four are defective, all four are
  BSD-3-Clause Pallets-ecosystem or encode-ecosystem projects.** There
  are no clean controls here and no language diversity. Its category mix
  is a consequence of which commits were hand-picked, not a sample of
  anything. **Still Claude-authored reconstructions** — the
  self-authorship caveat in `docs/BENCHMARK_METHODOLOGY.md` §10 applies
  to this tranche exactly as it does to v2 and v3.
- **M4-B: one case, one author family, one language, obvious difficulty,
  defective only.** It diversifies authorship on a single axis and says
  nothing about qwen3.6:27b's authoring ability in general, nor about
  any other open-weight model, nor about non-Claude authorship
  reliability — of the pilot's 9 live attempts across two models, this
  is the only one that survived. **JP's human decision is that this one
  genuinely non-Claude-authored admitted case is nonetheless sufficient
  to close the literal M4-B provenance pillar**, precisely because the
  pillar's question is provenance ("does an admissible non-Claude-authored
  case exist"), not a quality measurement of qwen3.6:27b. No further
  authorship pilot is planned.
- **M4 is complete: A, B, C and D are all closed.** Each closed on
  admitted evidence at very small scale, supporting no general or
  quality claim. M4-C landed 2 human-written cases (below) and M4-D is a
  live rotating private holdout kept outside this repository. **M4 has
  no remaining literal blocker.** Nothing here has been measured: no
  model has been run against this corpus, and admission is not
  measurement.

## Current contents — human-written (M4-C)

2 cases, both defective, both `python`.

| id | category | severity | difficulty |
|---|---|---|---|
| `maintainer-upload-dir-override-ignored` | contract-mismatch | medium-high | moderate |
| `maintainer-api-key-fragment-logging` | sensitive-logging | medium-high | moderate |

`provenance.type: authored-realistic`, `provenance.author_family:
human`, `provenance.human_authored: true`, **no** `author_model` — the
schema refuses to let those last two coexist, which is what makes the
claim checkable rather than asserted.

Both are derived from real fixes the maintainer authored himself — authorship verified locally before admission using Git author/committer metadata, absence of AI co-author trailers, and line-level blame. Source identifiers are not included in the public corpus. Both sides of each diff
are his verbatim code; the only work applied was selecting a
self-contained slice of it, generating the unified diff with `difflib`,
and assigning category/severity/difficulty. No code was invented,
renamed or altered.

No `source_repository`/`transformation` record is claimed: that
machinery exists for incorporating third-party code, and no third-party
code is incorporated here. **This corpus deliberately records no source
identifiers — no repository name, commit hash, commit date or internal
path.** M4-C is a claim about *who authored the case content*, not about
identifying where it came from, so the public record carries only what
that claim rests on: `human_authored: true`, `author_family: human`, no
`author_model`, no AI co-author trailer, and line-level authorship
verified locally before admission.

**The bar was enforced, not stretched to reach the count.** A third
proposed case was rejected: the code implementing it was written by
tooling (`AI Dev Autopilot`, with a Claude co-author trailer), and
`docs/BENCHMARK_METHODOLOGY.md` §4 makes concept-by-human plus
diff-by-tooling `human_authored: false` (human-reviewed), which does not
satisfy this pillar. Tranche size 2 is the maintainer's decision; the
roadmap says "human-written cases" with no count.

Two cases is a process demonstration, not a measurement. No model has
been run against them.
