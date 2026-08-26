# M4 private holdout — exact handoff

M4-D (`docs/ROADMAP.md` §4, `docs/M4_DESIGN_BRIEF.md` §D). Everything
this repository-scoped session could safely build is built:
`bin/review-corpus` already validates any external directory,
`bin/review-holdout` checks a holdout directory for contamination
signals, and `eval/results/HOLDOUT-RESULTS.md` is ready to receive an
aggregate-only row. **Creating the actual holdout directory, or touching
the maintainer's private machine-operations documentation, is out of
scope for this session** and was not attempted. This document is the
exact handoff so that step doesn't require re-deriving the design.

## What the maintainer needs to do

1. **Create the directory**, outside this repository, per
   `docs/BENCHMARK_METHODOLOGY.md` §11's storage-class rule: a private
   repository or a private project directory, never a subdirectory of
   this one. The methodology doc's own suggestion:
   `~/projects/reviewer-benchmark-holdout/`, registered wherever that
   machine tracks its projects.
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
   own backup, and that backup must not be a public remote." M0 already
   established an encrypted, restore-verified backup for this project
   (`CURRENT-MILESTONE.md`) — extend it, don't invent a new one.
6. **Run it** with the existing harness, no new plumbing:
   ```sh
   bin/review-eval --cases /path/to/reviewer-benchmark-holdout --backend claude --runs 3
   ```
7. **Publish only the aggregate row** in `eval/results/HOLDOUT-RESULTS.md`
   per that file's own header — never a case id, diff, or explanation.

## Minimum credible first holdout

Sizing is a credibility question, not an impressiveness one. A holdout
too small to survive one case flipping is not evidence; a holdout large
enough to look impressive but authored carelessly is worse than none.
The floor below is deliberately small enough to author honestly in one
sitting.

- **Case count: 8–12.** Below ~8, a single case changing a verdict moves
  a rate by more than 12 points and the number cannot carry an argument.
  Above ~12 the authoring effort starts inviting shortcuts (bulk
  generation, thin variations of one idea) that defeat the purpose. Start
  at the bottom of that band and grow it by rotation, not by a launch
  push.
- **Mix: roughly 2/3 defective, 1/3 clean.** Clean controls are not
  padding — the M3 evidence showed the leading reviewers detect
  essentially every defect while false-positiving on most hard clean
  diffs, so clean controls are where the discrimination actually lives.
  A holdout with no clean controls measures almost nothing the public
  corpora do not already measure.
- **Authorship: skew away from Claude, deliberately.** Per methodology
  §11, human-written and other-model-written cases first. This is the
  single most valuable property of the holdout: the public corpora are
  100% Claude-authored, so a Claude-authored private holdout reproduces
  the same self-authorship blind spot in a place nobody can audit. If
  the first tranche has to be Claude-authored to exist at all, record
  that honestly in the private directory's own notes and treat
  diversifying it as the first rotation.
- **Languages and categories: mirror the public corpora's spread, not
  their exact proportions.** At n≈10 no per-category rate is meaningful,
  so breadth exists to avoid a monoculture, not to support subgroup
  claims. Do not report per-category holdout numbers at this size.
- **Sourcing.** The two honest sources are the human-author packet
  (`docs/M4_HUMAN_AUTHOR_PACKET.md`) and the non-Claude authorship pilot
  (`docs/M4_DESIGN_BRIEF.md` §B). A holdout case never passes through
  `eval/proposals/` — it never enters this repository at all — but it
  should meet the same authoring bar. **External benchmark datasets are
  not automatically holdout material**: their licensing, their upstream
  source licensing, and whether a model provider has already ingested
  them are all separate questions, and a public dataset used privately
  is not a holdout in any meaningful sense.
- **Schema: identical schema-v2 JSON**, one file per case, filename stem
  equals `id`, no holdout-only fields — a holdout case must be
  promotable into a public corpus unchanged.

Commands, in order (all already exist; nothing new is needed):

```sh
bin/review-corpus  --cases <dir>                 # validate
bin/review-corpus  --cases <dir> --json          # fingerprint -> .sha256
bin/review-holdout check --cases <dir>           # contamination; must exit 0
bin/review-eval    --cases <dir> --backend claude --runs 3   # first run
```

`bin/review-holdout check` must exit 0 before any model ever sees the
corpus. It refuses any path inside this repository, flags a fingerprint
identical to a public corpus, and flags a fingerprint already named in
`eval/EXPERIMENTS.md`.

**What may return to public git**, as one row in
`eval/results/HOLDOUT-RESULTS.md` and nothing more: date, corpus name,
fingerprint, case count, run count, model, detected, clean false
positives, category correctness, severity correctness, errors, trust
level (L3), harness commit.

**What must NEVER return, in any form**: a case id, diff, title, tag or
ground-truth explanation; any absolute path, directory name, hostname or
machine detail; per-case results; any per-category or per-difficulty
split at this corpus size; and any number from a single run.

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
- Did not touch the maintainer's private machine-operations
  documentation or any file it governs.
- Did not author any holdout case content (that would itself need to
  come from the non-Claude/human sources listed above, not from this
  session acting as "Claude, invent some holdout cases").
- Did not invent a hosted service, database, or anything beyond the
  plain-files-plus-hashes design methodology §11 already specifies.
