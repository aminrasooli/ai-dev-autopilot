# Per-project integration guidance

This kit is generic and vendor-neutral by design (no JP-specific values are
hardcoded). The notes below are how each target project *would* adopt it —
written as guidance, not applied as code in those repos, for two reasons:

1. **Write-scope collision.** Several of these repos currently have their
   own long-lived sessions attached (per `~/ops/PROJECTS.md`'s write-scope
   table) — at the time this was written, live sessions were attached to
   `personal-trading-lab` (x2), `photo-macro-pregnancy-stage`,
   `photo-macro-tracker-beta`, `bergamasco-site`, and `jp-manager`, some
   actively busy. Writing into those trees from an unrelated session risks
   exactly the kind of collision `SYSTEM.md` rule 8 exists to prevent.
2. **Sandbox read-only mount.** This session's `~/code` and `~/projects`
   are mounted read-only; the only repo this session could actually write
   to and push was `ai-dev-autopilot` (it has a remote reachable by `git
   push`, and no other live session attached).

## JP Manager (`~/ops/jp-manager`)

Already runs **Claude Code CLI** (subscription-billed, not API-billed)
under root-brokered, nologin service accounts (`pc-manager`/`pc-engineer`/
`pc-reviewer`) — see its `DESIGN.md`. That is a sealed, reviewed deployment
("No Paperclip fork, no second scheduler, no custom dashboard"); nothing in
this kit should be wired into it without going through its own owner-gated
change process. If JP wants an *API-billed* (not subscription) role inside
Paperclip later, that is a privileged, root-level change (new service
account, new launch-chain entry) outside this kit's and this session's
scope entirely.

## AI Dev Autopilot (this repo)

Done — see `demos/jp_autopilot_demo.py`. A vendor-neutral, read-only,
budget-gated Agent SDK demo lives alongside the existing Claude Code/Codex/
Qwen adapters. It is additive: nothing about the existing subscription-based
CLI flows changes.

## CAL / PAL (`photo-macro-tracker`, `photo-macro-tracker-beta`)

Has a live attached session. Suggested integration *for that session to
apply*, not this one:
```python
from anthropic_api_kit import load_config, ApiAdapter, BudgetExhausted
config = load_config("cal", ledger_dir="./var")
```
Routine model for macro-photo analysis descriptions; hard model reserved for
ambiguous/low-confidence photos only. **Do not** add this to any pregnancy-
or health-labeled code path without JP's explicit sign-off per data-handling
rule 10 — route only non-sensitive, already-anonymized image features to the
API, never raw identifiable imagery or pregnancy-stage records, unless JP
has separately authorized and reviewed that specific data flow.

## Trading Lab (`personal-trading-lab`)

Has two live attached sessions. Suggested integration: structured research/
critique only — e.g., "critique this trade thesis" or "summarize this
week's risk-limit breaches" — never an execution path. `ApiAdapter.complete`
has no tool-use/execution capability by itself, so this is naturally
satisfied as long as nothing wires its output into an order-placement path.
Use `difficulty="hard"` sparingly (it's the expensive tier) — reserve it for
genuinely hard critique, not routine formatting.

## CSI

No project by that name was found under `~/projects` or `~/code` in this
machine's registry (`~/ops/PROJECTS.md`). If CSI exists under a different
name, or hasn't been created yet, this integration is **not applicable**
until JP identifies the actual project path — don't guess at one.

## Bergamasco site (`bergamasco-site`)

Has a live attached session, and **no git remote** (local-only — can't be
reached by this session's clone-and-push workaround even if it were idle).
Suggested integration for that session: content/breed-research drafting and
optional grounded Q&A using the `web_search` server tool (see the
`claude-api` skill's Server Tools reference) rather than this kit's plain
`complete()` — grounded Q&A benefits from Claude's own web search tool,
which this kit intentionally does not wrap (keeping the kit to the simple
single-call case; a research pipeline should call the Anthropic SDK's tool
surface directly for that one feature).
