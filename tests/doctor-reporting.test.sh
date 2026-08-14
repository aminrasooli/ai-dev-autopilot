#!/usr/bin/env bash
# AI-DEV contract test — doctor tells "not installed here" apart from "broken".
#
# Most of what bin/doctor inspects lives OUTSIDE this repository — ~/.claude,
# ~/.codex, /etc, $PATH — and none of it exists until `make sync` has run. Every
# one of those checks therefore fails on a fresh clone, a CI runner, and anyone's
# first five minutes, and `make test` used to end in CONTRACT TESTS FAILED with a
# dozen failures that all said the same thing: you have not installed this yet.
#
# The fix is a third answer, PENDING, and a third exit code, 3. A third answer is
# also exactly the shape of a way to make findings disappear, so this test exists
# to pin BOTH directions:
#
#   not deployed  -> PENDING, exit 3, and zero failures
#   deployed and drifted -> FAIL, exit 1, and zero pendings
#
# The second is the load-bearing one. Without it, "AI-DEV is not installed here"
# would be a sentence any machine could be made to say by deleting one file, and
# a real drift would report as a clean run.
#
# Model-free and free of charge. Nothing is installed, nothing is deployed, and
# nothing outside a temporary directory is written: each case runs doctor against
# a synthetic $HOME.
#
# Exit codes: 0 all passed · 1 a contract was violated · 3 prerequisites missing

set -uo pipefail

AI_DEV_HOME="${AI_DEV_HOME:-$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
export AI_DEV_HOME
DOCTOR="$AI_DEV_HOME/bin/doctor"
RUNALL="$AI_DEV_HOME/tests/run-all.sh"

if [ -t 1 ]; then G=$'\e[32m'; R=$'\e[31m'; B=$'\e[2m'; N=$'\e[0m'
else G=""; R=""; B=""; N=""; fi
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf '  %sPASS%s  %s\n' "$G" "$N" "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  %sFAIL%s  %s\n        %s\n' "$R" "$N" "$1" "${2:-}"; }

[ -x "$DOCTOR" ] || { printf 'skip: %s missing\n' "$DOCTOR"; exit 3; }
command -v jq >/dev/null 2>&1 || { printf 'skip: jq missing\n'; exit 3; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/aidev-doctor-reporting.XXXXXX")" || exit 3
trap 'rm -rf "$WORK"' EXIT

# The subset of checks that compare the deployed adapters against the hub. Small
# and fast, and every one of them is deployment-dependent, which is the property
# under test.
SCOPE="drift:"

# run_case <home-dir> -> sets RC, OUT
run_case() {
  OUT="$(env HOME="$1" bash "$DOCTOR" --quick --only "$SCOPE" 2>&1)"
  RC=$?
}

count_of() { printf '%s' "$OUT" | grep -cE "^  $1 " ; }

# --- 1. a machine that never ran `make sync` ----------------------------------
printf '\n%s1. not deployed: pending, never failed%s\n' "$B" "$N"

FRESH="$WORK/fresh-home"
mkdir -p "$FRESH"
run_case "$FRESH"

fresh_fail="$(count_of FAIL)"; fresh_pend="$(count_of PEND)"

if [ "$fresh_pend" -gt 0 ]; then
  ok "an undeployed machine reports $fresh_pend pending check(s)"
else
  bad "an undeployed machine reports pending checks" \
      "no PEND lines at all — either the category is gone or --only $SCOPE selected nothing:
$OUT"
fi

if [ "$fresh_fail" -eq 0 ]; then
  ok "an undeployed machine reports no failures"
else
  bad "an undeployed machine reports no failures" \
      "$fresh_fail FAIL line(s) — a fresh clone still reads as a violated contract:
$(printf '%s' "$OUT" | grep -E '^  FAIL ')"
fi

if [ "$RC" -eq 3 ]; then
  ok "an undeployed machine exits 3, which is neither pass nor failure"
elif [ "$RC" -eq 0 ]; then
  bad "an undeployed machine exits 3" \
      "exit 0 would let a CI run or a first \`make test\` claim a posture nobody has deployed"
else
  bad "an undeployed machine exits 3" "exit $RC"
fi

# --- 2. a machine that IS deployed, and has drifted ---------------------------
# The load-bearing direction. DEPLOYED is decided by one narrow fact: the live
# user settings register a hook that lives in this hub. Nothing else here is
# correct, so every drift check must fail — if any of them said "not deployed"
# instead, the category would be a way to hide drift by deleting a file.
printf '\n%s2. deployed and drifted: still a failure, never pending%s\n' "$B" "$N"

DRIFTED="$WORK/drifted-home"
mkdir -p "$DRIFTED/.claude"
jq -n --arg c "bash $AI_DEV_HOME/hooks/security-guard.sh" \
  '{hooks:{PreToolUse:[{matcher:"Bash",hooks:[{type:"command",command:$c}]}]}}' \
  > "$DRIFTED/.claude/settings.json"
run_case "$DRIFTED"

drift_fail="$(count_of FAIL)"; drift_pend="$(count_of PEND)"

if [ "$drift_fail" -gt 0 ]; then
  ok "a deployed machine with drifted adapters reports $drift_fail failure(s)"
else
  bad "a deployed machine with drifted adapters reports failures" \
      "no FAIL lines — drift is being reported as 'not installed':
$OUT"
fi

if [ "$drift_pend" -eq 0 ]; then
  ok "a deployed machine reports nothing as pending"
else
  bad "a deployed machine reports nothing as pending" \
      "$drift_pend PEND line(s) on a machine that HAS been synced:
$(printf '%s' "$OUT" | grep -E '^  PEND ')"
fi

if [ "$RC" -eq 1 ]; then
  ok "a deployed machine with drifted adapters exits 1"
else
  bad "a deployed machine with drifted adapters exits 1" "exit $RC"
fi

# --- 3. the two runs really are classified differently ------------------------
# Counts alone could both be satisfied by a check that simply disappeared. Name
# one check and require it to appear as PEND in the first run and FAIL in the
# second: same check, same scope, opposite classification, decided only by
# whether this hub has ever been synced onto the machine.
printf '\n%s3. the same check, classified by deployment and nothing else%s\n' "$B" "$N"

PROBE="~/.codex/AGENTS.md points at the hub"
run_case "$FRESH";   fresh_line="$(printf '%s' "$OUT" | grep -F "$PROBE" | head -1)"
run_case "$DRIFTED"; drift_line="$(printf '%s' "$OUT" | grep -F "$PROBE" | head -1)"

case "$fresh_line" in
  *PEND*) ok "undeployed: '$PROBE' is pending" ;;
  *) bad "undeployed: '$PROBE' is pending" "got: ${fresh_line:-<the check did not run at all>}" ;;
esac
case "$drift_line" in
  *FAIL*) ok "deployed: the same check is a failure" ;;
  *) bad "deployed: the same check is a failure" "got: ${drift_line:-<the check did not run at all>}" ;;
esac

# --- 4. the runner honours the third exit code --------------------------------
# A distinction doctor draws and the runner discards is not a distinction. The
# suites already use exit 2 for the same idea; doctor uses 3 because 2 is taken.
printf '\n%s4. tests/run-all.sh maps exit 3 to "awaiting make sync"%s\n' "$B" "$N"
if [ ! -r "$RUNALL" ]; then
  bad "run-all.sh handles doctor's exit 3" "$RUNALL missing"
elif grep -q 'bin/doctor --quick; s=\$?' "$RUNALL" \
  && printf '%s' "$(sed -n '/bin\/doctor --quick; s=\$?/,/esac/p' "$RUNALL")" | grep -qE '^\s*3\)'; then
  ok "run-all.sh routes doctor's exit 3 to the sync-pending path, not to failure"
else
  bad "run-all.sh handles doctor's exit 3" \
      "no '3)' arm after the doctor invocation — an undeployed machine would report CONTRACT TESTS FAILED again"
fi

printf '\n'
if [ "$FAIL" -eq 0 ]; then printf '%s%d passed%s\n' "$G" "$PASS" "$N"; exit 0; fi
printf '%s%d passed · %d FAILED%s\n' "$R" "$PASS" "$FAIL" "$N"; exit 1
