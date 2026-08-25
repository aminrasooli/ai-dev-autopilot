# Real-bug candidate queue

M4 (`docs/ROADMAP.md` §4, `docs/M4_DESIGN_BRIEF.md` §A). Each `.json`
file here is one hand-entered candidate real bug-fix commit — repository,
commit, license, confidence, and a recommended treatment. Validated by:

```sh
bin/review-realbug validate eval/realbug-queue
bin/review-realbug summary  eval/realbug-queue
```

**This is a queue, not the benchmark.** Nothing here is scored, nothing
here is in `eval/cases*`, and a candidate's presence is not an
endorsement — `status: candidate` means "logged for human review," never
"approved." A candidate only moves forward by:

1. A human reads the candidate file and the actual commit diff.
2. If accepted for further work, it becomes a `case proposal` in
   `eval/proposals/cases/` (`eval/proposals/README.md`) with
   `provenance.type: mined-real-fix` and the licensing fields
   (`source_repository`, `source_commit`, `source_license`,
   `transformation`) carried over — see `docs/BENCHMARK_METHODOLOGY.md`
   §4.
3. A second human decision moves the proposal into `eval/cases*`.

No mass import. Every candidate below was found by a manual, scoped `gh
search commits` query against a small number of well-known,
clearly-licensed repositories, then hand-verified (parent commit, files
changed, diff stats) via `gh api repos/<owner>/<repo>/commits/<sha>` —
not scraped, not auto-admitted. `found_by` on each candidate names the
query used, so the process is auditable.

## Current queue (5 candidates, 0 promoted)

| id | repo | license | recommended treatment | why |
|---|---|---|---|---|
| `flask-ipv6-partition-2025` | pallets/flask | BSD-3-Clause | transformed | logic-error, IPv6 host parsing |
| `werkzeug-external-url-boolean-logic` | pallets/werkzeug | BSD-3-Clause | transformed | logic-error, inverted boolean condition |
| `click-pager-windows-error-reporting` | pallets/click | BSD-3-Clause | transformed | error-handling, platform-specific |
| `apistar-staticfiles-resource-leak` | encode/apistar | BSD-3-Clause | transformed | resource-leak, fills a real gap (v2 has only 2 resource-leak cases) |
| `git-dir-off-by-one-reject-demo` | git/git | GPL-2.0-only | reject | **deliberately rejected** — demonstrates the license gate actually blocks a candidate, not just accepts everything found |

The last row exists on purpose: a queue that only ever contains
`accept`-shaped candidates hasn't demonstrated it can say no. GPL-2.0 is
not compatible with this project's redistribution needs at the
confidence/effort this project wants to spend proving otherwise, so the
candidate is logged and rejected rather than silently skipped — the
rejection is itself useful process evidence.
