# M4 private holdout — exact handoff

M4-D (`docs/ROADMAP.md` §4, `docs/M4_DESIGN_BRIEF.md` §D). Everything
this repository-scoped session could safely build is built:
`bin/review-corpus` already validates any external directory,
`bin/review-holdout` checks a holdout directory for contamination
signals, and `eval/results/HOLDOUT-RESULTS.md` is ready to receive an
aggregate-only row. **Creating the actual holdout directory, or touching
anything under `~/ops`, is out of scope for this session** (task
instructions §8) and was not attempted. This document is the exact
handoff so that step doesn't require re-deriving the design.

## What JP (or a session with `~/ops` access) needs to do

1. **Create the directory**, outside this repository, per
   `docs/BENCHMARK_METHODOLOGY.md` §11's storage-class rule: a private
   repository or a private project directory, never a subdirectory of
   `ai-team-runtime-v0`. The methodology doc's own suggestion:
   `~/projects/reviewer-benchmark-holdout/`, registered per this
   machine's project registry conventions (`~/ops/PROJECTS.md` — see
   this machine's own `CLAUDE.md` rule 2 about the project registry).
2. **Populate it** with schema-v2 case JSON files, same layout as
   `eval/cases/` — one file per case, filename stem equals `id`.
   Authorship should skew *away* from Claude (methodology §11:
   "human-written and other-model-written cases first") since the
   holdout's whole purpose is catching what the public, Claude-authored
   corpus can't. The human-author packet
   (`docs/M4_HUMAN_AUTHOR_PACKET.md`) and the non-Claude authorship
   pilot (`docs/M4_DESIGN_BRIEF.md` §B, currently blocked on host GPU
   access) are the two natural sources — a holdout case never needs to
   go through `eval/proposals/` first, since it never enters this repo
   at all, but running it through the same authoring discipline keeps
   the provenance honest.
3. **Validate it** with the existing tooling, unchanged:
   ```sh
   bin/review-corpus --cases /path/to/reviewer-benchmark-holdout
   ```
4. **Check it for contamination** before ever running a model against
   it:
   ```sh
   bin/review-holdout check --cases /path/to/reviewer-benchmark-holdout
   ```
   A non-zero exit means stop — either the holdout is byte-identical to
   a public corpus (not actually holding anything back) or its
   fingerprint is already named in `eval/EXPERIMENTS.md` (may have
   already been run and treated as public).
5. **Back it up separately.** Per methodology §11: "the holdout is the
   one corpus that cannot be regenerated from git history; it needs its
   own backup, and that backup must not be a public remote." This
   machine's `CLAUDE.md` already names a backup discipline (B0 encrypted
   Restic backup, per `docs/CURRENT-MILESTONE.md`'s M0 section) — extend
   that, don't invent a new one.
6. **Run it** with the existing harness, no new plumbing:
   ```sh
   bin/review-eval --cases /path/to/reviewer-benchmark-holdout --backend claude --runs 3
   ```
7. **Publish only the aggregate row** in `eval/results/HOLDOUT-RESULTS.md`
   per that file's own header — never a case id, diff, or explanation.

## Rotation

Per methodology §11's "Rotation triggers": rotate (add fresh cases,
retire old ones) if aggregate holdout scores start tracking public-corpus
scores too closely, if any case is ever quoted publicly by accident, or
on a fixed cadence once the benchmark has outside users (not yet — M6
territory). A rotated-out case is never quietly deleted from the private
directory's own history; it is marked retired there (private history,
private discipline — this repo has no visibility into it and shouldn't).

## What this session deliberately did not do

- Did not create `~/projects/reviewer-benchmark-holdout/` or any
  directory outside this repository.
- Did not touch `~/ops` or any file it governs.
- Did not author any holdout case content (that would itself need to
  come from the non-Claude/human sources listed above, not from this
  session acting as "Claude, invent some holdout cases").
- Did not invent a hosted service, database, or anything beyond the
  plain-files-plus-hashes design methodology §11 already specifies.
