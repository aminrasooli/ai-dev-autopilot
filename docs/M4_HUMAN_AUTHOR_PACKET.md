# M4 human-author packet

M4-C (`docs/ROADMAP.md` §4, `docs/M4_DESIGN_BRIEF.md` §C). This is the
whole ask for a human-authored benchmark case — fill in the five fields
below per case, nothing else. No JSON, no schema, no diff formatting
required from you.

## What "human-written" actually means here

`docs/BENCHMARK_METHODOLOGY.md` §4 defines it precisely, restated
plainly: a case can only be labeled `human_authored: true` if **you
supplied the diff/code content yourself** — not just the idea. If you
give the five fields below and someone (Claude or otherwise) writes the
actual diff from your spec, that case is **human-reviewed**
(`human_authored: false`), not human-written. Both are useful and both
are truthfully labeled; they are not the same claim, and the schema
refuses to leave it ambiguous.

**If you want a case to count as genuinely human-written**, field 5
below ("Diff, if you're writing it yourself") is where that happens —
paste real diff-shaped content there, even rough. Anything less, and the
case is human-reviewed once formatted, which is still real and still
worth having.

## Per-case template (copy this block, fill it in, one block per case)

```
### Case: <a short name for yourself, not the final id>

1. Scenario: what's the surrounding code/feature? (1-3 sentences)

2. Intended defect (or "none — this is a clean control"):
   what exactly is wrong, in your own words.

3. Why it matters: what breaks, or what could an attacker/user hit?
   (1-2 sentences — this becomes the ground-truth explanation)

4. Expected correct behavior: what should the code do instead?

5. Diff, if you're writing it yourself (optional — leave blank for
   human-reviewed instead of human-written):
   <paste the actual before/after code or a real unified diff>

6. Language/domain (optional): e.g. python, go, sql, "auth middleware"
```

That's it. Six lines, five of them required, the sixth optional twice
over (optional field, and only required at all if you want the
human-written label rather than human-reviewed).

## What happens after you hand this over

1. Whoever formats it (Claude or otherwise) turns your answers into a
   schema-valid case proposal, `provenance.author_family: human`,
   `provenance.human_authored` set to `true` only if you filled in field
   5 with real content, `false` otherwise.
2. It lands in `eval/proposals/cases/` — a proposal, not yet a scored
   case (`eval/proposals/README.md`).
3. A second human decision (yours or JP's, same discipline as every
   other admission path in M4) moves it into `eval/cases*` or not.

Nothing here is auto-admitted. This packet exists to make it cheap for
you to originate content, not to skip review.

## Minimum useful tranche

Not fixed by this document — a JP decision, batched at the end of the
session this packet was written in. A working floor to react to, not a
target: **3-5 cases** is enough to exercise this packet and the
formatting step end to end. It will not move any aggregate benchmark
number and should never be reported as if it did — the value of a
tiny human tranche at M4 is proving the pipeline and the truthful
label, not statistical weight.
