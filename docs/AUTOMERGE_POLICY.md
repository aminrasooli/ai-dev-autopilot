# Limited automatic-merge authorization

**Authorized by JP, 2026-09-20.** This narrows a previously absolute rule
("merge to `main` is permanently a human gate"). It does not remove it: every
merge outside the scope below is still human-only.

Staged copy. The landed copy belongs at `docs/AUTOMERGE_POLICY.md` in the
product repository, and that file is itself **outside** automatic scope, so
this policy can never be widened by an automatic merge.

## What may merge automatically

Only a pull request that satisfies **all** of the following, each re-checked
against live GitHub at merge time rather than trusted from the cycle that
built the branch:

1. **Ours and routine** — opened by this controller, head branch `auto/*`,
   open, not a draft. Ownership is re-asserted locally, never left to a
   server-side filter.
2. **In scope** — every changed path is outside the exclusion list below.
3. **Independently reviewed at that exact commit** — a separate model, in a
   fresh session, returned `VERDICT: APPROVE` with a `COMMIT:` line echoing
   the head SHA. The verdict is read from the controller's own queue, which
   lives outside the repository and which workers are denied access to.
4. **Required checks green** — every context branch protection *actually
   requires* is a successful check run. The required list is read from the
   protection API, so tightening protection automatically tightens this.
5. **Window and switch** — the host mutation window (07:00–15:00 PT freeze)
   is open and the publication kill switch is clear.
6. **Head pinned** — the head SHA is re-read immediately before merging and
   the merge is pinned with `--match-head-commit`. A push landing
   mid-decision aborts the merge rather than riding in on it.

Branch protection is never bypassed: no `--admin`, no `--auto-merge`, no
edits to protection settings.

## Permanently outside automatic scope (human merge only)

| Path | Why |
|---|---|
| `.github/**` | CI definitions *are* the trusted checks |
| `hooks/**` | security controls |
| `tests/**`, `bin/doctor`, `Makefile` | the trusted merge checks themselves |
| `eval/cases/**`, `eval/cases-v3/**`, `eval/cases-provenance/**` | frozen corpora |
| `docs/ROADMAP.md`, `CURRENT-MILESTONE.md` | milestone decisions |
| `SECURITY.md`, `LICENSE` | security and licensing |
| `docs/AUTOMERGE_POLICY.md` | this policy |

Also outside scope by construction, because the controller cannot do them at
all: spending, provisioning, and any external post, comment or review.

## Separation of duties

A worker cannot approve its own change. The implementer (Sonnet) and the
reviewer (Fable) are separate invocations; the reviewer is read-only and has
no publication path. The approval record is written by the controller into
state the worker is denied (`Read`/`Edit`/`Write` on the controller state
directory, plus `gh` entirely). The merge decision is made by the controller
from that state, never from anything inside the worktree.

## Turning it off

```sh
# permanently: set AIDEV_AUTOMERGE=0 in the service environment
# immediately, for everything including publication:
touch ~/.repo-guardian/state/publication.lock
```

Every merge and every refusal, with its reason, appears in the existing daily
email.
