# Results directory

Raw machine-readable reports, exactly as the harness wrote them. Reports
are evidence: they are added, never edited, and never deleted to make a
picture tidier.

## Layout

```
eval/results/
  archive-v1/     reports from the 20-case v1 corpus (historical)
  <model>-<corpus>-<runs>-<date>.json   v2 reports
```

**`archive-v1/` is not deprecated data — it is the record of what was
actually measured then.** Those reports ran against a different corpus
(20 cases, 14-category taxonomy) and are not comparable to v2 numbers.
They are kept unmodified precisely so the v1→v2 story stays checkable,
including the run-to-run false-positive variance that motivated repeat
runs in the first place.

## Rules

- **Every report names its own corpus.** v2 reports carry
  `corpus.sha256`, `corpus.benchmark_version` and `prompt_contract`;
  comparisons are only valid within matching values.
- **Never rewrite a historical report** to look as though it ran against
  a newer corpus. If a corpus changes, the old numbers stay attached to
  the old corpus.
- **Conflicting repeats are both kept.** No "best of N".
- **Provisional ≠ authoritative.** A report produced before its corpus's
  ground truth was human-approved is labelled provisional in
  `EXPERIMENTS.md` and must not be quoted as a result.
- **Overwriting is refused by default.** `bin/review-eval --out` will not
  replace an existing file without `--overwrite`.

## Checking a report

```sh
python3 -m reviewer.verify eval/results/<report>.json      # internal consistency
python3 -m reviewer.analyze eval/results/<report>.json     # variance + slices
```

`verify` recomputes the summary from the raw runs and fails on any
disagreement. It proves internal consistency, not honesty — see
`docs/BENCHMARK_METHODOLOGY.md` §11b for what the trust levels do and
do not mean.
