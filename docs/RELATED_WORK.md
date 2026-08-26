# Related work — other AI code-review benchmarks

Status: **survey, current as of 2026-08-25.** This benchmark is not the
first, not the largest, and not alone. This document exists so that
claim can never quietly be made here, and so the reuse question
("should we run against someone else's benchmark instead of building
more of our own?") is answered from primary sources rather than
impressions.

Method: project repositories, LICENSE files via the GitHub API, papers,
and methodology docs were read directly. Marketing summaries were not
relied on where primary evidence existed. Where a fact could not be
established from a primary source it is marked UNKNOWN rather than
guessed.

## Survey

| project | what it benchmarks | scale | clean-control / FP treatment | raw model / tool / agent | local-model compatible | code license | data / upstream license caveat | relation to this benchmark | verdict |
|---|---|---|---|---|---|---|---|---|---|
| [Martian Code Review Bench](https://github.com/withmartian/code-review-benchmark) | commercial reviewer **products** on real merged PRs | 50 PRs, 173 golden comments, 5 repos, 5 languages; online track up to ~500 PRs/bot/day | **none** — zero PRs with zero golden comments; all non-matching output counted FP | products (26, incl. CodeRabbit, Greptile, Qodo, Cursor Bugbot) | no Ollama path; one Claude Code CLI script | MIT | golden comments are prose only (no diffs); **upstream repos include AGPL-3.0 (Grafana), GPL-2.0 (Discourse), source-available (Sentry)** | complementary: real defects, real products, no controlled prompt | **CITE** (narrow ADAPT) |
| [AACR-Bench](https://github.com/alibaba/aacr-bench) | raw LLMs **and** agent harnesses under 4 context regimes | 196 positive PRs / 1,506 comments + 155 "negative" / 639 comments; 50 repos, 10 languages | **none** — "negative" samples still carry 639 defect comments; FP measured only as noise on defect-bearing PRs | both | plausible — OpenAI-compatible `OCR_LLM_URL` | Apache-2.0 | stores PR URLs + commit SHAs + annotation prose, **no upstream code redistributed**; underlying repos include AGPL-3.0, GPL/LGPL, and a non-OSI source-available licence | closest reusable harness; ships an `is_ai_comment` authorship field | **ADAPT** (secondary CITE) |
| [SWR-Bench](https://arxiv.org/abs/2509.01494) | ACR tools and models on real PRs | **1,000 PRs: 500 Change + 500 Clean**; Python only | **yes — 500 Clean-PRs**, explicitly to measure false-positive rate; κ=0.66 human agreement | both, incl. open-weight Qwen2.5 7/14/32B, DeepSeek-R1/V3 | yes (models evaluated), but harness unavailable | **UNKNOWN — no artifact published** | moot; nothing published to copy | **prior art for clean controls** — predates ours | **CITE** |
| [ContextCRBench](https://github.com/kinesiatricssxilm14/ContextCRBench) | raw LLMs, 3 tasks, context-enriched | 67,910 entries; 1,080 evaluated; 90 repos, 9 languages | **none** — negative class is "PR not merged", which conflates defect with process | raw models incl. Qwen2.5-Coder, Codestral | yes, in scope | **none — no LICENSE file** (all rights reserved) | 1.56 GB archive stores `content_before`/`content_after` = **full upstream source files** (LGPL/AGPL/Apache) | largest context-enriched ACR benchmark | **CITE** |
| [Kodus CodeReviewBench](https://github.com/kodustech/codereviewbench) | raw models in one fixed agent loop | 30 PRs, 95 golden bugs, 5 repos, 5 languages, 12 models | **none** — every case contains bugs; precision/FP measured, but no defect-free corpus | raw models (via hosted APIs) | evaluated, but no local/Ollama path (their own ADR cites vendor ToS limits) | **none — no LICENSE file**; harness proprietary | goldens are prose only; upstream mixed incl. AGPL-3.0, GPL-2.0, source-available | **closest competitor** — same object, ~6 months old, active | **CITE** |

## What this means for us

**Nothing here is copied into `eval/cases*`, and nothing should be.**
Four of the five have an upstream-licensing problem that a permissive
harness licence does not fix: a benchmark's MIT or Apache-2.0 licence
covers its *annotations and scripts*, never the third-party source code
its cases point at. Two ship no licence at all. Our corpora are
self-authored precisely so this question never arises, and that property
is worth more than the case count we could gain by importing.

The safe interaction is the other direction: **run our reviewer against
their benchmark**, externally, copying nothing.

## Reuse decisions

- **AACR-Bench — ADAPT.** Apache-2.0, runnable by an individual, clones
  upstream repos at runtime rather than vendoring them, and its reviewer
  backend takes an OpenAI-compatible endpoint, so our local models could
  plausibly be pointed at it. Worth at most 1–2 days, and worth it for a
  cross-benchmark number, not for absorbing their corpus. Requires an
  Apache-2.0 notice and a citation. Does **not** replace our seeded
  defects, clean controls, prompt contract, or variance reporting — it
  has none of those.
- **Martian — CITE**, with one narrow ADAPT: their severity × category
  taxonomy and the idea of reporting at two strictness tiers are
  metadata-only and MIT-clean. Half a day at most.
- **Kodus — CITE**, and treat as a direct competitor rather than
  ignoring it. One reusable *lesson*, not code: they documented a scorer
  bug where cases with zero predictions scored precision 0 instead of
  null, which moved one model from 33.3% to 71.4% macro precision. We
  checked ours against that failure mode — our harness reports raw counts
  over fixed denominators (`defect_cases`, `clean_cases`) with no
  model-controlled precision denominator, and technical errors are
  excluded from scoring rather than folded into misses, so the bug class
  does not apply here. No change was needed; the check was worth running.
- **SWR-Bench — CITE only.** No artifact is published, so there is
  nothing to run or reuse. It is the strongest prior art for clean
  controls and should be cited whenever we describe ours.
- **ContextCRBench — CITE.** Unlicensed harness plus a multi-gigabyte
  archive of full upstream source files makes ingestion a non-starter.

## Two-track architecture: LATER

The proposal — keep our controlled diagnostic corpus (Track 1) and add
external validation by running our reviewer through a credible outside
benchmark (Track 2) — is sound and should happen, but not now:

- It genuinely improves credibility: an outside benchmark we did not
  author is the one thing our self-authored corpora structurally cannot
  provide, and it reduces the pressure to manufacture hundreds of cases.
- It is not free. AACR-Bench is the only realistic target and still
  costs 1–2 days of adapter work, plus judge-model spend.
- It is not M4. M4 is provenance and credibility *of our own cases*;
  external validation is a different axis and can be added later without
  destabilising anything frozen.

Decision: **LATER** — after M4's four pillars close, as a bounded piece
of work with its own gate. Not started here.

## Honest positioning

Five candidate claims were adversarially fact-checked and **all five are
refutable**; none may be used:

1. ~~first/early AI code-review benchmark~~ — the lineage runs back to
   Tufano et al. (ICSE 2021) and Microsoft's CodeReviewer (FSE 2022).
2. ~~nobody evaluates raw reviewer models~~ — SWR-Bench, ContextCRBench,
   Kodus, CodeFuse-CommitEval all do.
3. ~~nobody evaluates local/open-weight models~~ — SWR-Bench evaluates
   Qwen2.5 7/14/32B; ContextCRBench evaluates Qwen2.5-Coder and
   Codestral.
4. ~~this lane is unclaimed~~ — Kodus occupies very nearly this exact
   position and is actively developed.
5. ~~nobody uses clean controls~~ — SWR-Bench ships 500 Clean-PRs
   specifically to measure false-positive rate.

What survives scrutiny is a **combination**, stated as emphasis rather
than primacy:

- The same clean-control protocol run across both a frontier API and
  locally-hosted open-weight models on one machine, with cost and
  hardware reported alongside detection.
- False-positive rate on defect-free diffs reported as a headline
  number, co-equal with detection, rather than buried in a precision
  denominator.
- Models rather than products, under one identical prompt contract, so
  results isolate model capability from scaffolding and retrieval.
- Self-authored cases with machine-readable authorship provenance, which
  is what lets the self-authorship limitation be disclosed and sliced
  instead of hidden.

Where others are simply better: scale, language coverage, real-repository
context, and real-PR realism. Martian has real products and real merged
PRs; AACR-Bench and ContextCRBench have 10× to 700× the data and true
repo-level context; Kodus has production PRs, frozen snapshots, and
cost-per-PR. Those are not our axes and pretending otherwise would fail
the first informed reader.

## Related-work paragraph (reusable in README / posts)

> Related and complementary work exists, and predates this project.
> Microsoft's CodeReviewer (2022) and Tufano et al. (2021) established
> the task; SWR-Bench pairs 500 defect-bearing PRs with 500 clean ones
> to measure false-positive rate; AACR-Bench evaluates raw models and
> agent harnesses across 10 languages under several context regimes;
> ContextCRBench studies how much repository context actually helps; and
> Martian's Code Review Bench and Kodus's CodeReviewBench both score real
> reviewer systems on real merged pull requests. This benchmark is
> smaller than all of them and deliberately different in kind: cases are
> self-authored with seeded defects rather than mined from real PRs, so
> there is no upstream-licensing entanglement and the answer key is fully
> known; hard clean controls and detection are reported as co-equal
> headline numbers; every backend — hosted and local open-weight alike —
> receives one identical prompt contract; runs are repeated with variance
> reported; and technical errors are counted separately from quality
> misses. It is a controlled diagnostic instrument, not a leaderboard of
> shipping products, and it is best read alongside the benchmarks above
> rather than instead of them.
