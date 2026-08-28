# v3 corpus errata

Corrections to the **answer key** of the frozen v3 corpus. Found by an
AI-assisted pre-review and **accepted by JP on 2026-08-28** — see the
human review record at the end of this file, which is the M5 launch
gate's ground-truth review.

**v3 is human-reviewed *with documented errata*. It is not error-free,
and must never be described as 37/37 ground-truth-correct.** One case
(`t1-12`) has invalid ground truth and deliberately remains in the
frozen corpus.

**Nothing in `cases/` is modified by this file, and nothing may be.** v3
is frozen at
`81daa0b7a48259184a91c48ab1dcf17c9d3ed4902fa891b5895db0f29fd79790`;
every authoritative M3 result names that fingerprint, and `explanation`
text is inside the hashed content, so *editing a single word of an
explanation would change the fingerprint and invalidate X17–X19*. Errata
are therefore recorded here and folded into a future corpus version, not
patched into this one.

**No published M3 number changes as a result of this file.**

## What the reviewer actually receives

Several findings below turn on this, so it is established from the code
rather than assumed: `reviewer/evaluate.py` calls
`backend.review_diff(case["diff"])`. The optional `context` parameter of
`build_review_prompt` is **never passed by the harness**, and no v3 case
carries a `context` field. **The reviewer sees the unified diff and
nothing else** — no file contents, no helper implementations, no
unchanged code outside the diff's own context lines.

---

## E1 — `t1-12-py-concurrency-inventory-oversell`

**Verdict: INVALID (the asserted race cannot occur in the shown code).**

**Reproduction.** The post-diff code was extracted verbatim and run with
no added sleeps or yields, 6 concurrent reservations against 6 concurrent
restocks, starting stock set high enough that `OutOfStock` cannot fire so
the expected total is order-independent:

| code | divergences |
|---|---|
| exact case code | **0/200** |
| same code with `await asyncio.sleep(0)` inserted *between* the read and the write | **200/200** |

An explicit interleaving trace confirms the mechanism:
`res-read(100) → res-write(99) → rst-read(99) → rst-write(100)` — fully
serialized.

**Static reason.** `get_available()` is `async def` but its body is a
plain dict lookup with no `await`. Awaiting a coroutine that never
suspends does not yield to the event loop, so
`available = await get_available(sku)` and
`_stock_cache[sku] = available - qty` execute with no scheduling point
between them. The read-modify-write is atomic in **both** functions, so
`reserve_stock` and `restock_and_release_holds` cannot interleave, and
the different locks never matter.

**On the recorded 182/200.** That rate is unreachable from this code — a
lost update requires a suspension between the read and the write, which
must have been present in whatever was executed. The
`execution_validated` note therefore does not describe the case as
shipped.

**What is still defensible:** two different locks guarding the same
mutable state is a real latent hazard — the day `get_available` performs
genuine I/O, the race becomes real. That is a *design* criticism, not the
reproducible 91%-of-trials defect the key asserts.

**M3 impact.** Sonnet 3/3 detected, Qwen 3/3, DeepSeek 0/3. Excluding the
case: Sonnet 97.7% → 97.6%, Qwen 94.3% → 94.0%, DeepSeek 13.8% → 14.3%.
No conclusion changes.

## E2 — `t2-13-py-negative-cache-uninvalidated-create`

**Verdict: WORDING-FIX (defect real; stated trigger unreachable).**

**Static reason.** The key ids are generated server-side
(`generate_key_material()` in the sibling `rotate_api_key`;
`create_api_key(account, "ci")` takes no id). Poisoning the negative
cache for a *specific future* key id therefore requires probing a random
id before it is generated. The two triggers the key names do not hold:
"client creates a key and immediately uses it" is create-then-resolve,
which has no prior probe and which `test_created_key_resolves` shows
succeeding; "a deploy probes with the key before provisioning finishes"
presupposes knowing the id in advance.

**What is still valid:** negative caching was added with **no
invalidation on the write path** while `revoke_api_key` does invalidate —
a genuine asymmetry, and the defect a reviewer should flag. The
`100/100` validation measures a probe-then-create sequence whose
precondition the shipped code cannot produce.

**M3 impact.** None proposed — the defect label stands; only the causal
story needs qualifying.

## E3 — `t2-06-xfile-partial-unique-email-lookup`

**Verdict: INSUFFICIENT-EVIDENCE (key evidence is invisible to the reviewer).**

**Static reason.** The explanation rests on three properties of
`get_by_email()`: that it has no `deleted_at` filter, that it calls
`.one_or_none()`, and that its docstring asserts emails are unique.
**None of the three is in the diff.** The `repo.py` hunk shows `create`,
then the *added* `soft_delete` and `find_live_by_email`; `get_by_email`
appears only as call sites in `password_reset.py`, `signup.py` and
`login.py`.

The defect is *inferable* — a newly added "live only" helper beside
continued use of the old one is a strong hint — but it requires assuming
unseen code. A reviewer who correctly declines to assert a bug in code
they cannot see is scored as a **miss**. This is the mirror image of the
trap the holdout audit already named: there, caution became a false
positive; here, caution becomes a missed detection.

**M3 impact.** Sonnet 3/3, Qwen 2/2 completed (1 error), DeepSeek 0/3.
Excluding it together with E1: Sonnet 97.7% → 97.5%, Qwen 94.3% → 95.1%,
DeepSeek 13.8% → 14.8%. Still no conclusion change.

## E4 — `t2-08-xfile-cursor-sort-field-divergence`

**Verdict: WORDING-FIX (core defect visible; one cited fact is not).**

**Static reason.** The core mismatch is fully visible **inside a single
hunk**: `.orderBy("updated_at", "desc")` beside the unchanged
`q.where("created_at", "<", before)`. Ordering by one column while
filtering by another breaks cursor pagination regardless of which value
the cursor carries, so the defect is establishable from the diff alone.

However the key states "the handler still encodes `last.created_at` as
nextCursor", and `encodeCursor` appears in the diff **only at its
definition** — never applied to a row. The closing sentence goes further,
saying the bug is "only establishable by combining … and the handler's
cursor encoding", which understates what the visible code already proves
and cites evidence the reviewer never receives.

**M3 impact.** None. Detection is achievable from visible code; no
exclusion warranted.

## E5 — `t2-17-py-nested-executor-submit-deadlock`

**Verdict: WORDING-FIX (core deadlock valid; `render_cover` is not safe).**

**Reproduction.** Exact post-diff structure, 4-worker pool, stubs only
for leaf helpers the case does not show:

| calls | result |
|---|---|
| 1 concurrent `render_cover` | completes |
| 8 concurrent `render_cover` | **2/8 completed, 6 permanently blocked** |

**Static reason.** `render_cover` does not itself occupy a worker, but it
submits `render_photo`, which occupies one and then blocks on a nested
submit to the *same* pool. At ≥4 concurrent covers every worker holds a
blocked `render_photo`, and the watermark tasks can never be scheduled.
The docstring's rule — "waiting on the pool is fine because the caller is
never itself a pool worker" — is true only when the submitted work does
not itself block on that pool, which here it does. `render_cover` is safe
only below saturation, exactly like `render_album`.

**M3 impact.** None — `defect: true`, category and severity all stand.
Only the "shows the pattern being SAFE" sentence is wrong.

## E6 — `t2-14-py-replica-read-after-write`

**Verdict: WORDING-FIX (core defect valid; one clause unsupported).**

**Static reason.** The diff contains no payment, capture or charge path.
The only monetary token is `payload.total_cents` on the INSERT, which
establishes an order total, not that money was taken. The phrase "an
order that WAS created and **WAS charged**" is therefore not supported by
the reviewer's input and should be dropped or qualified to "an order that
was created".

**M3 impact.** None. The read-after-write defect — `create_order()`
INSERTs on the primary then calls `get_order()`, which now routes to a
replica — is fully visible and valid.

---

## Safe remediation

1. **Do not touch `cases/`.** Explanations are inside the fingerprint;
   editing one invalidates X17–X19 and every citation of `81daa0b7…`.
2. **This file is the correction of record** for the v3 answer key.
   Link it from `eval/cases-v3/README.md` and
   `eval/results/M3-HARD-SCORECARD.md` so no one reads the key without
   it.
3. **Fold the corrections into the next corpus version**, where a
   fingerprint change is expected and priced in. E1 should be rewritten
   or dropped rather than carried forward; E3 needs `get_by_email`'s body
   included in the diff to be answerable from the input.
4. **Published M3 results stand unchanged.** The largest exclusion
   scenario moves any headline by **≤1.0 pp** and changes no ranking or
   conclusion. Recomputed figures are recorded above so a reader can
   adjust without anyone rewriting a result file.
5. **Review status: see the attestation below.**

---

## Human review record — JP, 2026-08-28

The M5 launch gate (`docs/ROADMAP.md` §5) requires that ground truth was
human-reviewed. It has been. What was decided, stated exactly:

**JP does NOT attest that all 37 frozen v3 cases are correct.** He
reviewed the pre-review findings above and accepted all six:

| case | accepted finding |
|---|---|
| `t1-12-py-concurrency-inventory-oversell` | **invalid ground truth** |
| `t2-06-xfile-partial-unique-email-lookup` | **insufficient evidence** in reviewer-visible input |
| `t2-13-py-negative-cache-uninvalidated-create` | wording correction |
| `t2-08-xfile-cursor-sort-field-divergence` | wording correction |
| `t2-17-py-nested-executor-submit-deadlock` | wording correction |
| `t2-14-py-replica-read-after-write` | wording correction |

Standing instructions issued with that decision: do not modify frozen v3
case bytes or historical M3 results; keep the frozen fingerprint
unchanged; record findings additively here; carry the substantive
corrections into the next corpus version.

### How v3 may and may not be described

- **Permitted:** "human-reviewed, with documented errata."
- **Not permitted:** "error-free", "37/37 ground-truth-correct", or any
  phrasing implying the answer key is fully validated. One case
  (`t1-12`) has **invalid** ground truth and remains in the frozen
  corpus and in the published M3 scoring, by deliberate choice, because
  correcting it would break the fingerprint that every M3 result cites.

This is a real limitation, disclosed rather than resolved. Anyone citing
an M3 number should read this file alongside it.

### Carried forward

The substantive corrections (E1 rewritten or dropped; E3 given a diff
that actually contains `get_by_email`'s body) are owed to the **next
corpus version**, where a fingerprint change is expected and priced in.
They are not owed to v3, which is immutable.
