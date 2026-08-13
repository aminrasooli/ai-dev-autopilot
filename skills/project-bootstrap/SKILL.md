---
name: project-bootstrap
description: Inspect an existing project and bring it up to the AI-DEV baseline — .ai/ decision records, dependency locking, tests, lint, config separation, structured logging, health endpoint for services, README run instructions. Use when entering a repository for the first time, when a session reports "NOT bootstrapped", or when starting a new project from scratch.
---

# Project bootstrap

Adopt the project as it is. Bootstrapping adds what is missing; it never
migrates a working project to different tooling.

## 1. Inspect before touching anything

Read before you write:

```bash
ls -a; git -C . log --oneline -10; git status --porcelain
cat README* 2>/dev/null | head -60
ls .ai 2>/dev/null; cat .ai/project.yaml 2>/dev/null
```

Detect and write down: language(s), package manager (by lockfile), test runner,
linter/formatter, type checker, CI config, containerisation, entrypoints, and
whether this is a library, a CLI, a service or a one-off script.

Lockfile → package manager, without exception:

| Lockfile | Manager | Lockfile | Manager |
|---|---|---|---|
| `uv.lock` | uv | `package-lock.json` | npm |
| `poetry.lock` | Poetry | `pnpm-lock.yaml` | pnpm |
| `Pipfile.lock` | Pipenv | `yarn.lock` | yarn |
| `environment.yml` | Conda | `bun.lockb` | bun |
| `requirements*.txt` only | pip + `.venv` | | |

If two lockfiles disagree, ask which one is authoritative — do not pick.

## 2. Environment

**Python** — project-local `.venv` (`python3 -m venv .venv` or `uv venv`) unless
uv/Poetry/Pipenv/Conda already manages it; then use that. Never install a
project dependency into a global or system interpreter. Pin: `uv lock`,
`poetry lock`, or `pip-compile`/`pip freeze` into a requirements lockfile.

**Node** — install with the detected manager, respecting the existing lockfile.
Never switch managers. Dependencies stay project-local; no `-g`.

## 3. Add only what is missing

Create a file only if it is absent and it earns its place in this project.

**`.ai/project.yaml`** — the machine-readable summary:

```yaml
name: <repo name>
kind: service | cli | library | app | research
language: <primary>
package_manager: <detected>
run: <command that starts it>
test: <command that runs tests>
lint: <command>
entrypoints: [<paths>]
services: []            # databases, queues, caches this needs
notes: <anything non-obvious a fresh session must know>
```

**`.ai/decisions.md`** — append-only. One entry per meaningful decision:

```markdown
## YYYY-MM-DD — <decision>
**Context:** what forced a choice.
**Options:** A / B / C.
**Chosen:** X, because …
**Evidence:** research/<file>.md, benchmark output, source links.
**Confidence:** high | medium | low. **Uncertain:** what could invalidate this.
**Reversal cost:** cheap | moderate | expensive.
```

**`.ai/architecture.md`** — components, data flow, state ownership, external
dependencies, and the boundaries that must not be crossed.

**`.gitignore`** — must cover `.env`, `.env.*` (except `.env.example`), `.venv`,
`node_modules`, `__pycache__`, build output, coverage, `*.log`, `.ai/reviews/`.

**`.env.example`** — variable **names** and one-line comments only. Never a real
value, never a placeholder that looks like a real key. Never copy `.env`.

**Tests** — a runnable test command and at least one meaningful test of the
project's actual behaviour. A smoke test that imports the package is a start,
not a finish.

**Lint / static analysis** — adopt what is configured. Otherwise: ruff for
Python, eslint + prettier for JS/TS, plus a type checker (mypy/pyright/tsc).
Wire them into one command.

**Config separation** — configuration comes from the environment with a typed,
validated loader (pydantic-settings, zod, envalid) and sane defaults for local
development. No secrets, hostnames or ports literal in code.

**Structured logging** — one logger, JSON in production, level from
configuration, request/correlation ID propagated. No `print`/`console.log` in
library or service code.

**Health endpoint** — services only: `GET /health` (liveness, no dependencies)
and `GET /ready` (checks the dependencies it actually needs). Wire graceful
shutdown on SIGTERM at the same time.

**README** — how to install, how to run, how to test, what configuration exists.
Commands must be copy-pasteable and must actually work.

Do **not** create Docker, Kubernetes, CI pipelines, or a microservice split
merely because a project exists. Add them when the project needs them.

## 4. Verify, then record

Run the install, the tests, the linter, and the run command. Fix what you broke.
Report exactly which commands you ran and what they printed. If a command fails
for a pre-existing reason, say so and leave it failing rather than papering over
it.

Then write `.ai/decisions.md` with the bootstrap decisions you actually made
(package manager, test runner, config approach) and stop. Do not start feature
work in the same breath unless that was the request.

## 5. Refuse to do this badly

- Do not run `git init` in a directory that is already inside a repository.
- Do not rewrite existing config to your preferred style.
- Do not add dependencies the project does not need.
- Do not commit. Bootstrapping leaves a reviewable working tree.
