#!/usr/bin/env bash
# repair-session.sh — launch ONE bounded repair session after a controller
# fault. Part B (trigger) and Part C (escalation / anti-loop).
#
# PROTECTED PATH. This file and the limits in it are exactly what a repair
# session may never modify. Changes here are human-merged, always.
#
# Reuses, and never duplicates: the controller's state dir, queue, digest,
# single-writer lock, time guard and kill switch. It is not a second
# controller — it runs no cycles, selects no work, and publishes nothing.
#
#   repair-session.sh            trigger if the last cycle warrants it
#   repair-session.sh --check    decide and explain; launch nothing
set -uo pipefail

TRAVEL_HOME="${AIDEV_TRAVEL_HOME:-$HOME/.local/state/ai-dev-autopilot-travel}"
STATE="$TRAVEL_HOME/state"; LOGROOT="$TRAVEL_HOME/logs"
LASTRUN="$STATE/last-run.json"
ATTEMPTS="$STATE/repair-attempts.json"
DAY="$(date +%F)"
DIGEST="$STATE/digest-$DAY.jsonl"
TIME_GUARD="${AIDEV_TIME_GUARD:-$HOME/ops/scripts/ai-dev-time-guard.sh}"
KILL_SWITCH="${REPO_GUARDIAN_HOME:-$HOME/.repo-guardian}/state/publication.lock"
CHARTER="${AIDEV_REPAIR_CHARTER:-$HOME/projects/ai-team-runtime-v0/automation/REPAIR-CHARTER.md}"
CLAUDE_BIN="${AIDEV_TRAVEL_CLAUDE_BIN:-$HOME/.local/bin/claude}"
CFG="${AIDEV_TRAVEL_CFG:-$HOME/.config/ai-dev-autopilot-travel}"

# ---- LIMITS. A repair session may never change these. ----------------
CEILING="${AIDEV_REPAIR_CEILING:-45m}"   # hard wall-clock ceiling
MAX_PER_DAY=1                            # per distinct signature, per day
MAX_EVER=2                               # per signature, without a human decision

CHECK_ONLY=0; [ "${1:-}" = "--check" ] && CHECK_ONLY=1
say() { printf '%s\n' "$*"; }
digest_event() {
  printf '{"at":"%s","kind":"%s","task":"repair","msg":"%s"}\n' \
    "$(date -Is)" "$1" "$(printf '%s' "$2" | tr -d '"\\' | cut -c1-240)" >> "$DIGEST" 2>/dev/null || true
}
decline() { say "no repair: $1"; [ "$CHECK_ONLY" -eq 1 ] && exit 0; exit 0; }

[ -s "$LASTRUN" ] || decline "no last-run.json"
RESULT="$(jq -r '.result // ""' "$LASTRUN" 2>/dev/null)"
TASK="$(jq -r '.task // "none"' "$LASTRUN" 2>/dev/null)"

# ---- Which results are faults? ---------------------------------------
# Capacity, idle and deliberate holds are NOT faults. Repairing a quota
# pause is how a loop starts: the fix is to wait, and a repair session
# cannot make capacity appear.
case "$RESULT" in
  fault-*|tests-failed*|acceptance-failed*|guardian-blocked|semantic-audit-blocked) ;;
  quota-unavailable|held-transient|auth-unavailable|waiting-backoff) decline "capacity/auth hold ($RESULT), not a defect" ;;
  no-work-needed|queue-complete|queue-blocked|analysis-complete|no-change-required) decline "idle or clean ($RESULT)" ;;
  published|review-only|review-pending|held-*|skipped-already-done|dry-run-pass) decline "clean or deliberate hold ($RESULT)" ;;
  *) decline "unrecognised result '$RESULT' — not auto-repairing something undiagnosed" ;;
esac

# ---- Fault signature: stable across runs, distinct across causes -----
ERRLINE="$(jq -r --arg t "$TASK" 'first(.tasks[]? | select(.id == $t) | .last_error // "")' \
  "$STATE/queue.json" 2>/dev/null || echo "")"
SIG="$(printf '%s|%s|%s' "$RESULT" "$TASK" "$ERRLINE" \
  | sed -e 's/[0-9a-f]\{7,40\}/HEX/g' -e 's/[0-9]\{2,\}/N/g' \
  | sha256sum | cut -c1-16)"
say "result=$RESULT task=$TASK signature=$SIG"

# ---- Gates. Same gates as everything else; never bypassed. -----------
[ -e "$KILL_SWITCH" ] && decline "kill switch is active"
if [ -r "$TIME_GUARD" ] && ! bash "$TIME_GUARD" >/dev/null 2>&1; then
  decline "inside the host mutation freeze; a repair cannot commit now"
fi
# Single writer: never run while a controller cycle holds the lock.
if command -v flock >/dev/null 2>&1; then
  exec 8>"$STATE/travel.lock" 2>/dev/null || true
  if ! flock -n 8 2>/dev/null; then decline "a controller cycle is running; not competing for the writer"; fi
  flock -u 8 2>/dev/null || true
fi

# ---- Anti-loop ledger -------------------------------------------------
[ -s "$ATTEMPTS" ] || printf '{}\n' > "$ATTEMPTS"
N_EVER="$(jq -r --arg s "$SIG" '.[$s].count // 0' "$ATTEMPTS" 2>/dev/null || echo 0)"
LAST_DAY="$(jq -r --arg s "$SIG" '.[$s].last_day // ""' "$ATTEMPTS" 2>/dev/null || echo "")"
DECIDED="$(jq -r --arg s "$SIG" '.[$s].owner_decision // ""' "$ATTEMPTS" 2>/dev/null || echo "")"

if [ "$LAST_DAY" = "$DAY" ]; then
  decline "already attempted signature $SIG today (limit $MAX_PER_DAY/day)"
fi
if [ "${N_EVER:-0}" -ge "$MAX_EVER" ] && [ -z "$DECIDED" ]; then
  # PART C: exactly one decision line, once, then silence on this signature.
  if ! grep -q "\"escalated\".*$SIG" "$DIGEST" 2>/dev/null; then
    digest_event "escalated" "signature $SIG recurred after $N_EVER repairs — owner decision required before any further attempt"
  fi
  decline "signature $SIG reached $N_EVER attempts; awaiting an owner decision"
fi

if [ "$CHECK_ONLY" -eq 1 ]; then
  say "WOULD LAUNCH a repair session (attempt $((N_EVER + 1))/$MAX_EVER, ceiling $CEILING)"
  exit 0
fi

# ---- Record the attempt BEFORE launching ------------------------------
# Crash-safe: a session that dies still consumed its attempt, so a crash
# loop cannot spin.
jq --arg s "$SIG" --arg d "$DAY" --arg t "$(date -Is)" --arg r "$RESULT" \
   '.[$s] = {count: ((.[$s].count // 0) + 1), last_day: $d, last_at: $t,
             result: $r, owner_decision: (.[$s].owner_decision // "")}' \
   "$ATTEMPTS" > "$ATTEMPTS.tmp" && mv "$ATTEMPTS.tmp" "$ATTEMPTS"

# The repair session is told, in-band, exactly what it may not touch. The
# list lives in a protected file so a session cannot widen its own reach.
PROTECTED="$(cat "$(dirname "$0")/PROTECTED-PATHS.txt" 2>/dev/null | grep -v '^#' | grep -v '^$' | tr '\n' ' ')"

RLOG="$LOGROOT/repair-$(date +%Y%m%d-%H%M%S)-$SIG.log"
digest_event "repair-started" "signature $SIG after $RESULT on task $TASK"
say "launching bounded repair session -> $RLOG"
START=$(date +%s)

# Same containment as the worker, and explicitly NOT the merger: no GitHub
# credentials, no publish path. It can diagnose, fix, test and commit; it
# cannot merge or push through a credential it does not have.
timeout --kill-after=60s "$CEILING" \
  env -u GH_TOKEN -u GITHUB_TOKEN -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN \
      GH_CONFIG_DIR="$STATE/no-gh-config" \
      GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=/bin/false \
      CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1 \
      AIDEV_REPAIR_SIGNATURE="$SIG" \
  "$CLAUDE_BIN" -p --safe-mode --permission-mode auto \
      --model fable --effort high \
      --setting-sources user --settings "$CFG/worker-settings.json" \
      "$(cat "$CHARTER" 2>/dev/null)
---
LIVE STATE FOR THIS REPAIR (your only input besides the repository itself):
  last-run.json: $(cat "$LASTRUN" 2>/dev/null)
  fault signature: $SIG
  run log: $(ls -t "$LOGROOT"/run-*.log 2>/dev/null | head -1)
Work on branch repair/$SIG-$DAY. Open a PR and stop. Never merge.
PROTECTED PATHS — if your fix touches any of these, open the PR and STOP;
never install, never merge, never edit this list:
$PROTECTED" \
  >"$RLOG" 2>&1
RC=$?
ELAPSED=$(( $(date +%s) - START ))

case "$RC" in
  0)   digest_event "repair-finished" "signature $SIG: session completed in ${ELAPSED}s" ;;
  124|137) digest_event "repair-timeout" "signature $SIG: hit the ${CEILING} ceiling after ${ELAPSED}s" ;;
  *)   digest_event "repair-failed" "signature $SIG: session exited $RC after ${ELAPSED}s" ;;
esac
jq --arg s "$SIG" --argjson e "$ELAPSED" --arg o "rc=$RC" \
   '.[$s] += {last_runtime_s: $e, last_outcome: $o}' \
   "$ATTEMPTS" > "$ATTEMPTS.tmp" && mv "$ATTEMPTS.tmp" "$ATTEMPTS"
say "repair session ended rc=$RC in ${ELAPSED}s"
exit 0
