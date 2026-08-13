#!/usr/bin/env bash
# Contract test for project bootstrap, run in a disposable git repository.
#
# It does not invoke a model. It asserts the things the skill promises are
# mechanically achievable here: the skill is discoverable, its detection rules
# identify the right package manager, a project-local Python venv can be created
# without touching any global interpreter, and the bootstrap artefacts are valid.

set -uo pipefail
# Default to the repository this script lives in, so a fresh clone tests
# itself rather than whatever happens to be installed at ~/.ai-dev. An
# explicit AI_DEV_HOME still wins.
AI_DEV_HOME="${AI_DEV_HOME:-$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
SKILL="$AI_DEV_HOME/skills/project-bootstrap/SKILL.md"

FAIL=0
SYNC_PENDING=0
ok()  { printf '  PASS  %s\n' "$1"; }
bad() { FAIL=1; printf '  FAIL  %s\n        %s\n' "$1" "$2"; }
# A control that is correct in the hub but undeployed on the running machine is
# a real gap and must not read as a pass — but it is not a violated contract
# either, and the fix is `make sync`, not a code change. run-all.sh reserves
# exit 2 for exactly this, so it stays visible without masking a regression.
pending() { SYNC_PENDING=1; printf '  SYNC  %s\n        %s\n' "$1" "$2"; }

T="$(mktemp -d "${TMPDIR:-/tmp}/aidev-bootstrap.XXXXXX")"
trap 'rm -rf "$T"' EXIT
cd "$T" || exit 1

echo "project bootstrap contract"
echo "  disposable repo: $T"

git init -q . && ok "disposable git repository created" || bad "git init" "failed"

# --- the skill is real and discoverable ---------------------------------------
[ -f "$SKILL" ] && ok "skill source exists in the hub" || bad "skill source exists" "$SKILL missing"
head -1 "$SKILL" | grep -q '^---$' && grep -q '^description:' "$SKILL" \
  && ok "skill frontmatter is valid" || bad "skill frontmatter is valid" "missing --- or description:"
[ "$(readlink -f "$HOME/.claude/skills/project-bootstrap" 2>/dev/null)" = "$(readlink -f "$AI_DEV_HOME/skills/project-bootstrap")" ] \
  && ok "skill is exposed to Claude Code via ~/.claude/skills" \
  || pending "skill is exposed to Claude Code via ~/.claude/skills" \
             "symlink missing — this hub is not deployed. Run: make -C $AI_DEV_HOME sync"

# --- package-manager detection matches the skill's table ----------------------
detect() { # detect <lockfile> -> manager
  case "$1" in
    uv.lock) echo uv ;; poetry.lock) echo poetry ;; Pipfile.lock) echo pipenv ;;
    package-lock.json) echo npm ;; pnpm-lock.yaml) echo pnpm ;;
    yarn.lock) echo yarn ;; bun.lockb) echo bun ;; *) echo unknown ;;
  esac
}
for pair in "uv.lock:uv" "poetry.lock:poetry" "Pipfile.lock:pipenv" \
            "package-lock.json:npm" "pnpm-lock.yaml:pnpm" "yarn.lock:yarn" "bun.lockb:bun"; do
  f="${pair%%:*}"; want="${pair##*:}"
  got="$(detect "$f")"
  [ "$got" = "$want" ] || { bad "lockfile $f maps to $want" "got $got"; continue; }
  grep -q "\`$f\`" "$SKILL" || { bad "lockfile $f documented in the skill" "not in the table"; continue; }
  ok "lockfile $f -> $want (documented)"
done

# --- python: project-local venv, nothing global -------------------------------
GLOBAL_SITE_BEFORE="$(python3 -c 'import site,sys;print(sorted(site.getsitepackages()))' 2>/dev/null | md5sum)"
if python3 -m venv .venv >/dev/null 2>&1; then
  ok "project-local .venv created"
  [ -x .venv/bin/python ] && ok ".venv has its own interpreter" || bad ".venv interpreter" "missing"
  vp="$(.venv/bin/python -c 'import sys;print(sys.prefix)')"
  [ "$vp" = "$T/.venv" ] && ok "venv prefix is project-local ($vp)" || bad "venv prefix is project-local" "$vp"
else
  bad "project-local .venv created" "python3 -m venv failed (install python3-venv)"
fi
GLOBAL_SITE_AFTER="$(python3 -c 'import site,sys;print(sorted(site.getsitepackages()))' 2>/dev/null | md5sum)"
[ "$GLOBAL_SITE_BEFORE" = "$GLOBAL_SITE_AFTER" ] \
  && ok "global site-packages untouched" || bad "global site-packages untouched" "global interpreter changed"

# --- the artefacts the skill prescribes ---------------------------------------
mkdir -p .ai
cat >.ai/project.yaml <<'EOF'
name: bootstrap-selftest
kind: cli
language: python
package_manager: pip
run: python -m selftest
test: pytest -q
lint: ruff check .
entrypoints: [src/selftest/__main__.py]
services: []
notes: disposable fixture created by tests/bootstrap.test.sh
EOF
python3 -c 'import sys,yaml' 2>/dev/null \
  && { python3 -c 'import yaml,sys; d=yaml.safe_load(open(".ai/project.yaml")); sys.exit(0 if {"name","kind","run","test"} <= set(d) else 1)' \
       && ok ".ai/project.yaml parses and has the required keys" || bad ".ai/project.yaml" "invalid"; } \
  || ok ".ai/project.yaml written (PyYAML absent, parse check skipped)"

printf '# Decisions\n' >.ai/decisions.md
printf '# Architecture\n' >.ai/architecture.md
[ -s .ai/decisions.md ] && [ -s .ai/architecture.md ] && ok ".ai/decisions.md and .ai/architecture.md created" || bad ".ai records" "missing"

cat >.gitignore <<'EOF'
.env
.env.*
!.env.example
.venv/
node_modules/
__pycache__/
*.log
.ai/reviews/
EOF
printf 'DATABASE_URL=\nAPI_BASE_URL=\n' >.env.example
printf 'SECRET=hunter2\n' >.env
git add -A >/dev/null 2>&1
git status --porcelain | grep -q '^A  .env$' \
  && bad ".env is gitignored" ".env was staged" \
  || ok ".env is gitignored while .env.example is tracked"
git status --porcelain | grep -q '\.env\.example' && ok ".env.example is tracked" || bad ".env.example is tracked" "not staged"
grep -qE '=[^[:space:]]' .env.example && bad ".env.example holds names only" "a value is present" || ok ".env.example holds names only"

# --- the guard must not obstruct ordinary bootstrap commands ------------------
GUARD="$AI_DEV_HOME/hooks/security-guard.sh"
for c in "python3 -m venv .venv" "npm ci" "pnpm install" "pytest -q" "ruff check ." \
         "git add -A" "git commit -m msg" "mkdir -p src/pkg" "rm -rf ./build"; do
  d="$(jq -nc --arg c "$c" --arg cwd "$T" '{hook_event_name:"PreToolUse",tool_name:"Bash",cwd:$cwd,tool_input:{command:$c}}' \
       | env AI_DEV_UNATTENDED=0 AI_DEV_OVERNIGHT=0 "$GUARD" 2>/dev/null \
       | jq -r '.hookSpecificOutput.permissionDecision // "allow"' 2>/dev/null)"
  [ -z "$d" ] && d=allow
  [ "$d" = "allow" ] && ok "guard allows: $c" || bad "guard allows: $c" "returned $d"
done

[ "$FAIL" -ne 0 ] && exit 1
[ "$SYNC_PENDING" -ne 0 ] && exit 2
exit 0
