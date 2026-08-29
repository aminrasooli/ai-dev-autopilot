# M5 license gate — decision brief

## DECISION — JP, 2026-08-28: **remain MIT for launch. No licence change.**

Option A in §4. The repository ships MIT today and continues to; nothing
about `LICENSE` changes for M5. This closes the `docs/ROADMAP.md` §5
licence gate.

The two follow-on questions in §5 and §6 below were also decided,
2026-08-28:

**Contribution licensing — DECIDED: inbound = outbound, no CLA.**
Contributions are accepted under the licence applicable to the project
and to the files they modify; contributors keep their copyright; there is
no CLA and no DCO sign-off. Written into `CONTRIBUTING.md` and
`eval/SUBMIT.md`, the latter making explicit that a submitted result file
is a contribution like any other.

**Data licence — DECIDED: deferred.** No separate corpus/results data
licence will be added before launch merely for completeness. **Flagged
for reconsideration before any third-party corpus or data contribution is
accepted** — that trigger is now recorded in both `CONTRIBUTING.md` and
`eval/SUBMIT.md`, which tell anyone proposing cases or datasets to open
an issue first, so the question surfaces at the moment it starts to
matter rather than being rediscovered afterwards.

**`docs/ROADMAP.md` §5 is deliberately NOT edited.** Its licence-gate
text still says the question "remains an open question, not a default" —
inaccurate before this decision and out of date after it. Per §0 rule 3,
gate text changes are JP's to make on a separate day. Left for him.

The analysis that led to the decision is preserved below unchanged.

---

Status: **analysis for JP. The decision is recorded above.** `docs/ROADMAP.md` §5 names
a license gate, says "the analysis (adoption versus protection,
contributor-agreement implications) has not been done yet and is
scheduled before launch", and reserves the decision. This is that
analysis. The choice remains JP's, and it is a product-direction call
that also depends on the private appendix, which this document has not
seen.

**Not legal advice.** Everything here is the practical, checkable state
of the repository plus the ordinary trade-offs between these licenses.
Anything with real money attached deserves a lawyer.

## 1. The first finding: it is already decided in practice

`docs/ROADMAP.md` §5 says: *"Until decided, this remains an open
question, not a default."* **That is not accurate.** The repository has
shipped a verbatim MIT `LICENSE` since its first commit —
`fb61025`, 2026-08-12, "Initial public release" — the repository is
**public**, and GitHub detects and displays the license as MIT.

Consequences that constrain the decision:

- Every published commit has been offered to the world under MIT. Anyone
  who has cloned it holds a perpetual MIT grant **to the versions they
  received**. That cannot be withdrawn later.
- A future relicense therefore applies to *future* versions only. It
  cannot claw back what M0–M5 already published, including the corpus
  and every result file.
- So the live question is not "MIT or AGPL" from a blank slate. It is
  "keep MIT, or move future versions to something else, knowing
  everything published so far stays MIT."

**This brief does not correct the roadmap.** `docs/ROADMAP.md` §0 rule 3
reserves gate text to JP, edited deliberately and on a different day than
the conversation that questioned it. The "not a default" wording sits
inside the licence gate, so it is flagged here and left for him.

## 2. The second finding: relicensing is unilateral, which is unusual

The roadmap anticipates "contributor-agreement implications". In this
repository there are effectively none:

| fact | value |
|---|---|
| distinct commit authors, whole history | 2 — `aminrasooli` (122) and `AI Dev Autopilot` (18), the maintainer's own automation account |
| outside human contributors | **zero** |
| PR authors, all PRs ever | `aminrasooli` only |
| CLA or DCO | none |

There is no third-party human copyright to chase, so relicensing future
versions is a clean unilateral decision today. **That window closes the
moment the first outside PR is merged** — which is precisely what M5
launch and the M6 traction gate are designed to cause. If a license
change is ever wanted, it is cheapest *before* launch, and the cost rises
permanently after.

(Claude-generated content is co-authored on 80 commits. The copyright
status of model output is genuinely unsettled; that argues for *fewer*
moving parts, not more.)

## 3. What is actually being protected

The strategic asset, per `docs/ROADMAP.md` §1, is not the harness code —
it is the benchmark, the leaderboard, and the position *"never let the
same vendor grade its own homework."* The code is a few thousand lines of
Python and bash that a competent team could rewrite in a week. The corpus,
the frozen fingerprints, the provenance discipline and the published
results are the part that took months and is hard to copy.

A copyleft license protects **code** from being taken proprietary. It
does not protect a benchmark's authority, which comes from being cited,
reproduced and trusted. That asymmetry is the core of this decision.

## 4. Options

### A. Keep MIT (status quo, zero action)

- Maximum adoption. Many companies have blanket bans on AGPL; a
  benchmark that corporate engineers cannot run is a benchmark that does
  not get submissions.
- Directly serves the M6 traction gate, whose top-priority metric is *one
  independent reproduction or submission from a stranger*.
- No migration risk, no contributor friction, no relicensing story to
  explain at launch.
- Cost: a vendor could fork the harness into a closed product. They could
  not, however, take the benchmark's credibility, which is the actual moat.

### B. Apache-2.0

- Practically as permissive as MIT for adopters; still corporate-safe.
- Adds an **explicit patent grant** and patent-retaliation termination,
  which MIT lacks. For a project actively soliciting outside
  contributions — exactly what M5 does — this is the concrete difference,
  and it protects contributors and users alike.
- Adds a NOTICE mechanism and clearer attribution requirements.
- Cost: slightly more ceremony; relicensing from MIT is trivial for the
  sole copyright holder, but the already-published MIT versions remain MIT.

### C. AGPL-3.0

- Strongest protection against a cloud vendor running a hosted version
  without contributing back.
- But consider whether the trigger actually fires here: the network
  copyleft applies to *users interacting over a network with a modified
  version*. The normal use of this project is running a benchmark
  locally and publishing a result file. A vendor's most likely
  appropriation — reading the corpus and citing the methodology — is not
  a distribution event at all, so AGPL would not reach it.
- Cost is concrete and immediate: it excludes a large share of the very
  corporate engineers M6 needs, and it is the single most common reason
  a benchmark gets quietly reimplemented instead of adopted.

## 5. The separate question nobody has asked yet

**The corpus has no data license.** `LICENSE` is a software license, and
it is the only one in the repository. But `eval/cases/`,
`eval/cases-v3/` and `eval/results/` are *data*, and a benchmark exists
to be reused, quoted and built upon.

Today a third party wanting to cite the corpus, redistribute a subset, or
build a derived benchmark has to reason about whether an MIT grant on
"the Software" covers JSON case files. It probably does, but "probably"
is a poor foundation for the one asset that is supposed to be
authoritative.

Many benchmarks split this deliberately — a software license for the
harness, a data licence such as CC-BY-4.0 for the cases and results, so
attribution survives redistribution. This interacts with provenance:
`docs/BENCHMARK_METHODOLOGY.md` already gates admitted cases on a
known-permissive `source_license`, and the M4-A cases are transformed
reconstructions of BSD-3-Clause sources, so upstream terms are already
tracked per case. **This is worth deciding at the same time**, and it is
independent of the A/B/C choice above.

## 6. Also missing regardless of the choice

`CONTRIBUTING.md` does not state inbound=outbound — that contributions
are offered under the project's license. For a public repo GitHub's terms
supply a default, but stating it explicitly is what makes a submission
unambiguous, and M5 is the milestone that starts inviting submissions.
`eval/SUBMIT.md` has the same gap for submitted **result files**, which
are contributions too.

## 7. What is blocking

Nothing technical. This is a judgement about adoption versus protection,
weighed against the business model in the private appendix, and it is
JP's alone. Three things are worth deciding together:

1. the code license (keep MIT / move to Apache-2.0 / move to AGPL-3.0);
2. whether the corpus and results get their own data license;
3. an explicit inbound=outbound line in `CONTRIBUTING.md` and
   `eval/SUBMIT.md`.

The only time-sensitive part is that option B or C is dramatically
cheaper before the first outside contribution than after.
