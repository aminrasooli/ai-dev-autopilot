#!/usr/bin/env bash
# Regression tests for the self-repair trigger (automation/repair-session.sh).
#
# Every scenario drives the REAL script against an isolated fake state dir.
# The Claude binary is stubbed, so no model is ever invoked and no session
# cost is incurred; what is under test is the TRIGGER's decision logic,
# limits and gates — not the repair session's judgement.
set -u

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$SRC/repair-session.sh"
T="${TMPDIR:-/tmp}/repair-loop-tests-$$"
DAY="$(date +%F)"
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf '  ok: %s\n' "$*"; }
bad() { FAIL=$((FAIL+1)); printf '  FAIL: %s\n' "$*"; }
chk() { local d="$1"; shift; if "$@" >/dev/null 2>&1; then ok "$d"; else bad "$d"; fi; }

mk() { # $1 scenario, $2 result, $3 task
  H="$T/$1"; ST="$H/state"; LG="$H/logs"
  mkdir -p "$ST/no-gh-config" "$LG" "$H/bin" "$H/guard/state"
  printf '{"result":"%s","task":"%s","completed":"%s"}\n' "$2" "$3" "$(date -Is)" > "$ST/last-run.json"
  printf '{"tasks":[{"id":"%s","last_error":"boom at 0xdeadbeef after 1234 ms"}]}\n' "$3" > "$ST/queue.json"
  : > "$LG/run-x.log"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$H/bin/timeguard"; chmod +x "$H/bin/timeguard"
  # stub claude: records that it was launched, never calls a model
  printf '#!/usr/bin/env bash\necho launched >> "%s/launched"\nexit "${STUB_RC:-0}"\n' "$ST" > "$H/bin/claude"
  chmod +x "$H/bin/claude"
  mkdir -p "$H/cfg"; printf '{}\n' > "$H/cfg/worker-settings.json"
  printf 'charter\n' > "$H/charter.md"
}
run() { # extra env via prefix
  env AIDEV_TRAVEL_HOME="$H" AIDEV_TIME_GUARD="$H/bin/timeguard" \
      REPO_GUARDIAN_HOME="$H/guard" AIDEV_REPAIR_CHARTER="$H/charter.md" \
      AIDEV_TRAVEL_CLAUDE_BIN="$H/bin/claude" AIDEV_TRAVEL_CFG="$H/cfg" \
      "$@" bash "$SCRIPT" 2>&1
}
launched() { [ -s "$H/state/launched" ]; }

echo "== a genuine fault triggers exactly one repair session =="
mk fault fault-sonnet-run taskA
export OUT; OUT="$(run)"
chk "session launched"              launched
chk "attempt recorded"              test -s "$H/state/repair-attempts.json"
chk "digest records the start"      grep -q 'repair-started' "$H/state/digest-$DAY.jsonl"
chk "digest records the finish"     grep -q 'repair-finished' "$H/state/digest-$DAY.jsonl"
chk "runtime recorded for the ledger" bash -c "jq -e '.[].last_runtime_s != null' '$H/state/repair-attempts.json'"
N1="$(jq -r '[.[]][0].count' "$H/state/repair-attempts.json")"
: > "$H/state/launched"
run >/dev/null 2>&1
chk "second run the same day does NOT relaunch" bash -c '! [ -s "'"$H"'/state/launched" ]'
chk "attempt count unchanged"       bash -c "[ \"\$(jq -r '[.[]][0].count' '$H/state/repair-attempts.json')\" = '$N1' ]"

echo "== capacity and idle results never trigger a repair =="
for r in quota-unavailable held-transient auth-unavailable waiting-backoff \
         no-work-needed queue-complete queue-blocked published review-pending; do
  mk "no-$r" "$r" taskA
  run >/dev/null 2>&1
  chk "no repair for $r"            bash -c '! [ -s "'"$H"'/state/launched" ]'
done

echo "== the kill switch halts everything =="
mk killed fault-sonnet-run taskA
: > "$H/guard/state/publication.lock"
export OUT; OUT="$(run)"
chk "no session launched"           bash -c '! [ -s "'"$H"'/state/launched" ]'
chk "reason is the kill switch"     bash -c "printf '%s' \"\$OUT\" | grep -q 'kill switch'"

echo "== the host mutation freeze halts everything =="
mk frozen fault-sonnet-run taskA
printf '#!/usr/bin/env bash\nexit 1\n' > "$H/bin/timeguard"; chmod +x "$H/bin/timeguard"
export OUT; OUT="$(run)"
chk "no session launched"           bash -c '! [ -s "'"$H"'/state/launched" ]'
chk "reason is the freeze"          bash -c "printf '%s' \"\$OUT\" | grep -q 'freeze'"

echo "== a running controller cycle keeps the single writer =="
mk busy fault-sonnet-run taskA
( exec 9>"$H/state/travel.lock"; flock 9; sleep 4 ) &
HOLD=$!; sleep 1
export OUT; OUT="$(run)"
chk "no session launched while a cycle runs" bash -c '! [ -s "'"$H"'/state/launched" ]'
chk "reason names the writer"       bash -c "printf '%s' \"\$OUT\" | grep -q 'controller cycle is running'"
wait $HOLD 2>/dev/null

echo "== a recurring signature escalates once, then stops =="
mk loop fault-sonnet-run taskA
run >/dev/null 2>&1                                   # attempt 1
jq '.[] |= (.last_day = "1970-01-01")' "$H/state/repair-attempts.json" > "$H/t" && mv "$H/t" "$H/state/repair-attempts.json"
: > "$H/state/launched"
run >/dev/null 2>&1                                   # attempt 2
chk "second attempt allowed"        launched
jq '.[] |= (.last_day = "1970-01-01")' "$H/state/repair-attempts.json" > "$H/t" && mv "$H/t" "$H/state/repair-attempts.json"
: > "$H/state/launched"
export OUT; OUT="$(run)"                                          # attempt 3 -> escalate
chk "third attempt refused"         bash -c '! [ -s "'"$H"'/state/launched" ]'
chk "escalated to the owner once"   bash -c "[ \"\$(grep -c escalated '$H/state/digest-$DAY.jsonl')\" = 1 ]"
jq '.[] |= (.last_day = "1970-01-01")' "$H/state/repair-attempts.json" > "$H/t" && mv "$H/t" "$H/state/repair-attempts.json"
run >/dev/null 2>&1
chk "escalation is not repeated"    bash -c "[ \"\$(grep -c escalated '$H/state/digest-$DAY.jsonl')\" = 1 ]"
chk "still refused without a decision" bash -c '! [ -s "'"$H"'/state/launched" ]'
jq '.[] |= (.owner_decision = "retry")' "$H/state/repair-attempts.json" > "$H/t" && mv "$H/t" "$H/state/repair-attempts.json"
run >/dev/null 2>&1
chk "an owner decision unblocks it" launched

echo "== distinct signatures are tracked separately =="
mk twosig fault-sonnet-run taskA
run >/dev/null 2>&1
printf '{"result":"fault-uncommitted-only","task":"taskB","completed":"%s"}\n' "$(date -Is)" > "$H/state/last-run.json"
: > "$H/state/launched"
run >/dev/null 2>&1
chk "a different signature still gets its attempt" launched
chk "two signatures tracked"        bash -c "[ \"\$(jq -r 'length' '$H/state/repair-attempts.json')\" = 2 ]"

echo "== a crashed session still consumes its attempt (no crash loop) =="
mk crash fault-sonnet-run taskA
STUB_RC=1 run >/dev/null 2>&1
chk "attempt recorded despite failure" bash -c "[ \"\$(jq -r '[.[]][0].count' '$H/state/repair-attempts.json')\" = 1 ]"
chk "failure recorded in the digest"   grep -q 'repair-failed' "$H/state/digest-$DAY.jsonl"

echo "== the trigger itself never merges or publishes =="
chk "no merge command"              bash -c "! grep -qE 'gh pr merge|git push|--admin' '$SCRIPT'"
chk "credentials stripped"          bash -c "grep -q 'GH_CONFIG_DIR' '$SCRIPT' && grep -q 'u GH_TOKEN' '$SCRIPT'"
chk "limits are literal, not env-overridable" \
  bash -c "grep -q '^MAX_PER_DAY=1' '$SCRIPT' && grep -q '^MAX_EVER=2' '$SCRIPT'"
chk "charter is the only instruction" bash -c "grep -q 'cat \"\$CHARTER\"' '$SCRIPT'"
chk "runs fable, fresh session"     bash -c "grep -q 'model fable' '$SCRIPT'"
chk "protected paths are passed to the session" \
  bash -c "grep -q 'PROTECTED PATHS' '$SCRIPT' && grep -q 'PROTECTED-PATHS.txt' '$SCRIPT'"
chk "the loop protects its own trigger and limits" \
  bash -c "grep -q '^automation/repair-session.sh' '$SRC/PROTECTED-PATHS.txt' && grep -q '^automation/PROTECTED-PATHS.txt' '$SRC/PROTECTED-PATHS.txt'"
chk "guards, protection and corpora are protected" \
  bash -c "grep -q '^hooks/' '$SRC/PROTECTED-PATHS.txt' && grep -q '^.github/workflows/' '$SRC/PROTECTED-PATHS.txt' && grep -q '^eval/cases/' '$SRC/PROTECTED-PATHS.txt'"

printf '\nPASS=%d FAIL=%d\n' "$PASS" "$FAIL"
rm -rf "$T"
[ "$FAIL" -eq 0 ]
