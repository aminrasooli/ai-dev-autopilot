# Benchmark v2 corpus

The frozen 54-case corpus every authoritative M1 and M2 result ran
against. `eval/cases-v3/cases/` is the harder v3 corpus and
`eval/cases-provenance/cases/` is the M4 provenance corpus; this one is
neither, and it is not superseded by either — v3 is an *additional*
tier, not a replacement.

```sh
bin/review-corpus --cases eval/cases          # validate, print distribution
bin/review-eval   --cases eval/cases --backend fake --runs 3
```

## Freeze — durable declaration

**Frozen at 54 cases** (40 defective / 14 clean / 6 cross-file), as
merged in PR #12. Fingerprint:

```
f31d46310988f61c4534344ad05a52a4385fd15159126a0be85aad532f045690
```

**Immutable after freeze.** No case may be edited, deleted or replaced.
Every authoritative M1 and M2 result names this fingerprint, so a single
changed byte would silently invalidate published evidence rather than
being noticed at citation time. The constant is pinned by
`reviewer/tests/test_corpus.py::test_frozen_corpus_fingerprints_are_exact`,
which fails on any edit.

If this corpus ever genuinely needs to change, that is a **new corpus
with a new fingerprint and new experiments** — never an edit to this one.

## Composition

| property | value |
|---|---|
| cases | 54 (40 defective, 14 clean, 6 cross-file) |
| languages | python 27, go 5, java 4, javascript 4, rust 3, shell 3, typescript 3, config 2, sql 2, docs 1 |
| provenance | `seeded-synthetic` x54 |
| authorship | `claude` x54 |

**Self-authorship is this corpus's central limitation, not a footnote**
(`docs/BENCHMARK_METHODOLOGY.md` §10): it is 100% Claude-authored while
Claude is one of the models scored against it. M4 exists because of this;
see `eval/cases-provenance/` for the real-historical, non-Claude-authored
and human-written tranches that begin to address it.

## Maturity: `stable` — declared 2026-08-28 by JP

Per `docs/BENCHMARK_METHODOLOGY.md` §11a, corpus maturity is declared
**here, at corpus level** — it is never recorded by editing the `status`
field in the case files, because `status` is inside the fingerprint and
rewriting it across all 54 cases would move the fingerprint from
`f31d46310988f61c…` to `9adb85ab011f4a75f1…`, invalidating every M1 and
M2 result. The per-case `status: pilot` records what each case was
*authored as*, and is immutable like every other field.

### Assessment against the five `stable` criteria

Recorded so the declaration is a decision about evidence rather than a
feeling:

| # | criterion | status |
|---|---|---|
| 1 | fingerprint frozen and published | **met** — above, and in `CURRENT-MILESTONE.md` |
| 2 | ground truth human-reviewed, and the review recorded | **met** — JP's D1–D5 decisions, answered 2026-08-21, recorded in `CURRENT-MILESTONE.md` §M0 (two clean controls and one case deleted, twelve accepted-category alternatives endorsed) |
| 3 | at least one repeat-run result at `runs >= 3` against this exact fingerprint | **met** — X14/X15/X16, 3 runs x 54 cases each |
| 4 | reproduction from a fresh clone demonstrated | **met** — X13, run from a genuine `git clone` of `origin/main`, not a working copy |
| 5 | no outstanding correction | **met** — none open |

**All five are met, and JP declared this corpus `stable` on 2026-08-28.**

The declaration was made **here, at corpus level**, with an explicit
instruction not to edit individual case `status` fields or otherwise
disturb the frozen fingerprint. None were touched: every case file still
reads `status: pilot` — recording what it was *authored* as — and the
corpus still fingerprints to `f31d46310988f61c…`, unchanged. That is the
mechanism working as designed, not an inconsistency.

`stable` means this corpus is fit to anchor published comparisons. It
does **not** mean the corpus is large, diverse, or free of the
self-authorship limitation above — all three remain true and are stated
plainly.

It is also not sufficient on its own to switch the leaderboard on:
`eval/LEADERBOARD.md` lists three further preconditions, including at
least one submission from outside the project.
