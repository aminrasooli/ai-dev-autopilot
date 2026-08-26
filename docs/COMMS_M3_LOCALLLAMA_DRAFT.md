# r/LocalLLaMA post draft — M3 hard benchmark finding

Status: **DRAFT ONLY. NOT PUBLISHED.** Publishing is a human gate
(`docs/ROADMAP.md` §3, §6) and remains JP's decision — see the M4
decision packet for the explicit yes/no. This file exists so that
decision can be made by reading finished text, not by re-deriving it
from raw reports. Saved at `docs/` root because no drafts location
existed anywhere in this repository before this session (checked: no
`docs/drafts/`, `docs/communications/`, or similarly named directory) —
one file was the minimum needed rather than inventing a directory
structure for a single post.

**Source of every number below:** `eval/results/M3-HARD-SCORECARD.md`,
X17-X19, preregistered before execution, frozen corpus fingerprint
`81daa0b7a48259184a91c48ab1dcf17c9d3ed4902fa891b5895db0f29fd79790`. No
number here was rounded beyond what the scorecard itself reports.

**Compliance with task constraints, checked against the draft below:**
no novelty claim, M2->M3 is stated as a harder corpus not a model
regression, no industry-wide claim (every claim is scoped to "this
37-case corpus, these three models"), no invented composite metric (the
post reports detection and clean-FP separately, exactly as measured, and
says explicitly why it doesn't combine them), local compute is never
called free.

---

## Post title (draft)

Qwen3.6:27b matched Claude Sonnet on defect detection in my code-review
benchmark. Then both of them flagged ~80-90% of my clean control diffs
as buggy.

(Earlier draft title framed the clean-control twist as something "local
models" did. The measurement doesn't support that framing: on clean
controls Qwen was marginally *better* than the hosted model, 19/24
versus 21/24. The finding is that both leading reviewers cry wolf, which
is the more interesting result anyway — a title should not quietly pick
a side the data didn't.)

## Post body (draft)

I've been building an open, self-hosted benchmark for LLMs acting as
independent code reviewers: given a diff, does the model catch a seeded
bug, and does it stay quiet on clean code. Not a claim of novelty, this
kind of benchmark exists elsewhere too, but I wanted one I could run
myself, on my own hardware, with the raw data public.

The thesis I keep coming back to: never let the same vendor grade its
own homework. Every model in this benchmark, including Claude, is
evaluated the same way, with the same prompt, and I disclose that most
of the current corpus is Claude-authored (a real limitation, not
hand-waved away, more below).

**What I measured.** 37 cases, 29 with a seeded defect and 8 "hard
clean controls" designed to look suspicious while actually being
correct. Diffs are bigger and messier than my first pass at this
benchmark, 80 to 219 lines, deliberately harder to skim. 3 models,
3 runs each, same prompt, same scoring code, no LLM judge anywhere in
the loop: claude-sonnet-5 (hosted), qwen3.6:27b and deepseek-r1:14b
(both local, via Ollama, on one RTX 6000).

**Detection looked saturated for the top two.** Sonnet caught 85 of 87
defective observations it completed (the 2 it didn't complete were
malformed responses, not misses). Qwen caught 82 of 82 it completed.
DeepSeek collapsed to 12 of 87, mostly by returning an empty "approve"
with no findings at all. (All three had a few calls fail outright — 2, 6 and 2 of 111
respectively — which I count as errors rather than misses, the same way
for every model. DeepSeek's 12 is out of all 87; out of the 85 it
actually completed it's 12 of 85. Neither framing rescues it.)

**Then I looked at the clean controls, and the story flipped.** Sonnet
flagged 21 of 24 clean observations as if they had a defect. Qwen
flagged 19 of 24. These are diffs with no bug in them, deliberately
written to look suspicious. A reviewer that just flags everything also
gets 100% detection, for free, so a detection number on its own doesn't
tell you whether a model is actually reasoning about the diff or just
being paranoid. I'm not reporting a single blended score for this,
on purpose: detection and clean-precision measure different failure
modes, and folding them into one number would hide exactly the tension
this post is about.

DeepSeek's shape was the opposite: low false-positive rate (4 of 24),
but only because it barely said anything at all.

**Cost, honestly.** Sonnet: $5.34 for the full 111-call run, measured,
not estimated. Qwen and DeepSeek: no external API charge, because they
ran locally, but that is not the same as free. Qwen's calls used about
41.5 minutes of GPU time; DeepSeek's about 3.5 minutes, though its
speed came from producing near-empty responses, not from doing the same
work faster.

**What I'm not claiming.** This is one self-authored 37-case corpus, not
an industry benchmark, and I'm not claiming these numbers generalize
past this corpus and this prompt contract. I'm also not calling this a
"Qwen beats Claude" or "these models got worse" result: the corpus
changed between my last post and this one specifically to stop rewarding
flag-everything behavior, so a lower number here means the test got
harder, not that a model regressed. Full methodology, every raw report,
and the scoring code are public in the repo if you want to point out
where I'm wrong.

**What's next.** I already know the biggest weakness in this benchmark:
it's currently 100% authored with Claude's help, and Claude is one of
the models I'm scoring. My next milestone is specifically about fixing
that: real historical bugs pulled from permissively-licensed repos with
their provenance preserved, cases authored by non-Claude local models,
a small human-written tranche, and a private holdout so nothing gets
memorized into a future training run. Posting about that separately once
there's something real to show, not vaporware-teasing it here.

---

## Numbers used in the draft (verification table)

| claim in post | source | exact figure |
|---|---|---|
| Sonnet detection | M3-HARD-SCORECARD.md headline table | 85/87 (97.7%), 0 misses among completed |
| Qwen detection | same | 82/87 (94.3%), 0 misses among completed |
| DeepSeek detection | same | 12/87 (13.8%) |
| Sonnet clean FP | same | 21/24 (87.5%) |
| Qwen clean FP | same | 19/24 (79.2%; 19/23 of completed) |
| DeepSeek clean FP | same | 4/24 (16.7%) |
| Sonnet cost | same, "Cost, latency, execution environments" | $5.335879, 111 calls |
| Qwen local time | same | 2491.6s (~41.5 min) measured model execution |
| DeepSeek local time | same | 208.9s (~3.5 min) measured model execution |
| Corpus size | eval/cases-v3/README.md | 37 cases, 29 defective / 8 clean |
| Diff size range | same | 80-219 lines, median 102 |
| Corpus fingerprint | same | `81daa0b7a48259184a91c48ab1dcf17c9d3ed4902fa891b5895db0f29fd79790` |
| Error counts (2 / 6 / 2 of 111) | M3-HARD-SCORECARD.md headline table | Sonnet 2 (both defective); Qwen 5 defective + 1 clean = 6; DeepSeek 2 |
| DeepSeek 12 of 85 completed | same | 12/87 raw, 2 errors -> 85 completed |
| Hardware | M3-HARD-SCORECARD.md names the RTX 6000; the 24GB figure is from docs/BENCHMARK_METHODOLOGY.md §"local execution" and eval/SUBMIT.md | one RTX 6000, 24GB |

## Open decision for JP

Publish as-is, edit, or hold — see the M4 session decision packet,
question 4. If edited, re-check the verification table above still
matches the edited text before publishing; do not let a copy edit
quietly drift a number away from its source.
