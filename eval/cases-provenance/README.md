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

Today it contains exactly one tranche — **real historical bugs (M4-A)** —
because that is the only M4 pillar with admitted content so far. The
non-Claude-authored (M4-B) and human-written (M4-C) tranches do not
exist yet; when they do, they belong here alongside these, sliced apart
by `provenance.author_family` / `provenance.type` rather than by
directory.

## Relationship to the frozen corpora

This is a **separate, additional** corpus. It does not touch, extend, or
re-open either frozen corpus:

| corpus | path | fingerprint | status |
|---|---|---|---|
| v2 | `../cases/` | `f31d46310988f61c4534344ad05a52a4385fd15159126a0be85aad532f045690` | frozen, unchanged |
| v3 | `../cases-v3/cases/` | `81daa0b7a48259184a91c48ab1dcf17c9d3ed4902fa891b5895db0f29fd79790` | frozen, unchanged |
| provenance | `cases/` | `125cf57223f16b0269981dbe13c9c46e78dd396009719212128f74820c1828c6` | this corpus, **not frozen** |

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
  authorship — M4-B is the pillar that diversifies authorship, and it is
  not done.
- **Provenance type**: `mined-real-fix` = 4.
- **Source license**: BSD-3-Clause = 4.
- **Transformation**: `transformed` = 4.

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

`eval/realbug-queue/` (candidate) → `eval/proposals/cases/` (proposal,
PR #24) → human decision → here. Both hops are human decisions by
design; nothing is auto-admitted. The proposals are kept as historical
intake evidence with `status: accepted` and `reviewer_notes` recording
what adjudication found and what was corrected before admission — three
of the four needed a correction, and one earlier reconstruction was
rejected outright and rewritten. That trail is deliberately not deleted
now that the cases exist.

## Limitations — read before citing anything from here

- **Four cases is a process demonstration, not a measurement.** This
  tranche is far too small to move any aggregate metric, support a
  per-category claim, or characterise "real bugs" in general. It proves
  the pipeline produces admissible, license-clean, truthfully-labelled
  real-bug cases. Nothing more should be claimed from it.
- **No model has been evaluated against this corpus.** No preregistered
  experiment exists for it; there are no results in `eval/results/` for
  this fingerprint, and admission is not measurement.
- **All four are Python, all four are defective, all four are
  BSD-3-Clause Pallets-ecosystem or encode-ecosystem projects.** There
  are no clean controls here and no language diversity. Its category mix
  is a consequence of which commits were hand-picked, not a sample of
  anything.
- **Still Claude-authored reconstructions.** The self-authorship caveat
  in `docs/BENCHMARK_METHODOLOGY.md` §10 applies to this tranche exactly
  as it does to v2 and v3.
- **M4 is not complete.** Real historical bugs (M4-A) now have admitted
  evidence. Non-Claude authorship (M4-B), human-written cases (M4-C),
  and the live rotating private holdout (M4-D) do not.
