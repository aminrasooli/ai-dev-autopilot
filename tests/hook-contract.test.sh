#!/usr/bin/env bash
# AI-DEV contract test — the hooks speak the shape Claude Code parses.
#
# WHAT NOBODY WAS CHECKING
#
# Every other suite drives a hook directly and asserts what the hook DECIDED.
# Not one of them asserts that Claude Code would act on the decision. Those are
# different claims, and only the second one is the product: the entire value of
# this framework is that a routine command is approved without a dialog and a
# consequential one is not, and that happens only if the JSON the hook prints is
# a shape Claude Code recognises.
#
# The failure mode is silent in both directions, which is why it needs its own
# suite. If the decision shape drifts:
#
#   - an `allow` Claude Code cannot parse is not a deny, it is NO decision —
#     so every routine command starts prompting again, and the framework
#     degrades into the approval-fatigue problem it exists to solve, with 813
#     assertions still passing;
#   - a key outside the schema is dropped with one line in a debug log. It does
#     not error. This file used to emit `addPermissionRule` inside an allow, a
#     key the installed build does not define, and nothing anywhere said so.
#
# WHAT THIS PROVES, AND WHAT IT DOES NOT
#
# Section 1 pins the shapes the hooks emit, exactly, including that a decision
# object carries no key outside the documented set — the check that would have
# caught `addPermissionRule`.
#
# Section 2 asserts the installed Claude Code build still contains every name
# those shapes are built from, and carries a negative control proving the search
# can tell present from absent. That is a canary for a renamed or removed field
# on upgrade. It is NOT proof that the CLI honours the decision: only a live
# session proves behaviour, and `project-isolation.test.sh` is the suite that
# starts real sessions. Read this one as "the vocabulary still exists".
#
# Model-free and free of charge.
#
# Exit codes: 0 all passed · 1 a contract was violated · 3 prerequisites missing

set -uo pipefail

AI_DEV_HOME="${AI_DEV_HOME:-$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
export AI_DEV_HOME
GUARD="$AI_DEV_HOME/hooks/security-guard.sh"
BROKER="$AI_DEV_HOME/hooks/permission-broker.sh"
SESSION="$AI_DEV_HOME/hooks/session-start.sh"

if [ -t 1 ]; then G=$'\e[32m'; R=$'\e[31m'; B=$'\e[2m'; N=$'\e[0m'
else G=""; R=""; B=""; N=""; fi
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf '  %sPASS%s  %s\n' "$G" "$N" "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  %sFAIL%s  %s\n        %s\n' "$R" "$N" "$1" "${2:-}"; }
defer() { printf '  %sDEFER%s %s (%s)\n' "$B" "$N" "$1" "${2:-}"; }

for f in "$GUARD" "$BROKER" "$SESSION"; do
  [ -r "$f" ] || { printf 'skip: %s missing\n' "$f"; exit 3; }
done
command -v jq >/dev/null 2>&1 || { printf 'skip: jq missing\n'; exit 3; }

printf 'AI-DEV hook output contract\n'

# hookrun <script> <payload-json> [env...] -> stdout
hookrun() {
  local script="$1" payload="$2"; shift 2
  printf '%s' "$payload" | env AI_DEV_UNATTENDED=0 AI_DEV_OVERNIGHT=0 "$@" bash "$script" 2>/dev/null
}
bashp() { jq -nc --arg c "$1" --arg d "${2:-$AI_DEV_HOME}" \
  '{hook_event_name:"PreToolUse",tool_name:"Bash",cwd:$d,tool_input:{command:$c}}'; }

# jqok <json> <filter> -> 0 when the filter is true
jqok() { printf '%s' "$1" | jq -e "$2" >/dev/null 2>&1; }

# --- 1. the shapes the hooks emit ---------------------------------------------
printf '\n%s1. every decision is exactly the shape Claude Code parses%s\n' "$B" "$N"

# PreToolUse: { hookSpecificOutput: { hookEventName, permissionDecision,
#               permissionDecisionReason } }
for pair in "rm -rf / --no-preserve-root:deny" "git push origin main:ask"; do
  cmd="${pair%:*}"; want="${pair##*:}"
  out="$(hookrun "$GUARD" "$(bashp "$cmd")")"
  if ! jqok "$out" '.hookSpecificOutput.hookEventName == "PreToolUse"'; then
    bad "guard '$cmd' names its hook event" "got: ${out:-<empty>}"
  elif ! printf '%s' "$out" | jq -e --arg w "$want" \
        '.hookSpecificOutput.permissionDecision == $w' >/dev/null 2>&1; then
    bad "guard '$cmd' decides $want" "got: $out"
  elif ! jqok "$out" '.hookSpecificOutput.permissionDecisionReason | type == "string"'; then
    bad "guard '$cmd' carries a reason string" "got: $out"
  else
    ok "guard emits PreToolUse/$want with a reason string ($cmd)"
  fi

  # No key outside the documented three. An unknown key is dropped silently by
  # Claude Code, so this is the only place it can be noticed.
  extra="$(printf '%s' "$out" | jq -r '.hookSpecificOutput
      | keys - ["hookEventName","permissionDecision","permissionDecisionReason"]
      | join(",")' 2>/dev/null)"
  [ -z "$extra" ] && ok "...and carries no key outside the PreToolUse schema" \
    || bad "guard carries no key outside the PreToolUse schema" "unknown: $extra"
done

# The guard's silent path really is silent: an empty stdout, not an "allow".
out="$(hookrun "$GUARD" "$(bashp 'ls -la')")"
[ -z "$out" ] && ok "guard stays silent for a command it has no opinion on" \
  || bad "guard stays silent for a command it has no opinion on" "got: $out"

# PermissionRequest: decision is one of two objects and nothing else.
#   { behavior: "allow", updatedInput?, updatedPermissions? }
#   { behavior: "deny",  message?, interrupt? }
bp() { jq -nc --arg c "$1" --arg d "$AI_DEV_HOME" \
  '{hook_event_name:"PermissionRequest",tool_name:"Bash",cwd:$d,tool_input:{command:$c}}'; }

out="$(hookrun "$BROKER" "$(bp 'git status')")"
if jqok "$out" '.hookSpecificOutput.hookEventName == "PermissionRequest"' \
  && jqok "$out" '.hookSpecificOutput.decision.behavior == "allow"'; then
  ok "broker emits PermissionRequest/allow for a routine command"
else
  bad "broker emits PermissionRequest/allow for a routine command" "got: ${out:-<empty>}"
fi
extra="$(printf '%s' "$out" | jq -r '.hookSpecificOutput.decision
    | keys - ["behavior","updatedInput","updatedPermissions"] | join(",")' 2>/dev/null)"
[ -z "$extra" ] && ok "...and the allow decision carries no key outside its schema" \
  || bad "the allow decision carries no key outside its schema" \
         "unknown: $extra — Claude Code drops it with one debug line and no error"

out="$(hookrun "$BROKER" "$(bp 'sudo apt-get install nginx')" AI_DEV_OVERNIGHT=1)"
if jqok "$out" '.hookSpecificOutput.decision.behavior == "deny"'; then
  ok "broker emits PermissionRequest/deny when unattended"
else
  bad "broker emits PermissionRequest/deny when unattended" "got: ${out:-<empty>}"
fi
extra="$(printf '%s' "$out" | jq -r '.hookSpecificOutput.decision
    | keys - ["behavior","message","interrupt"] | join(",")' 2>/dev/null)"
[ -z "$extra" ] && ok "...and the deny decision carries no key outside its schema" \
  || bad "the deny decision carries no key outside its schema" "unknown: $extra"

# A denial the model cannot read is a denial it will retry.
if jqok "$out" '.hookSpecificOutput.decision.message | type == "string" and (length > 20)'; then
  ok "...and the deny explains itself, so the model stops rather than retrying"
else
  bad "the deny explains itself" "no usable message: $out"
fi

# Escalate is the absence of a decision, not a decision to escalate. If this
# ever emitted an object, Claude Code would act on it instead of asking.
out="$(hookrun "$BROKER" "$(bp 'sudo apt-get install nginx')")"
[ -z "$out" ] && ok "broker escalates by emitting nothing, so the human sees the original dialog" \
  || bad "broker escalates by emitting nothing" "got: $out"

# SessionStart contributes context, and must not contribute a decision.
out="$(printf '%s' "$(jq -nc --arg c "$AI_DEV_HOME" \
        '{hook_event_name:"SessionStart",cwd:$c,source:"startup"}')" \
      | bash "$SESSION" 2>/dev/null)"
if jqok "$out" '.hookSpecificOutput.hookEventName == "SessionStart"' \
  && jqok "$out" '.hookSpecificOutput.additionalContext | type == "string"'; then
  ok "session-start emits SessionStart/additionalContext"
else
  bad "session-start emits SessionStart/additionalContext" "got: ${out:-<empty>}"
fi

# --- 2. the installed build still knows these names ---------------------------
# A canary for the upgrade that renames or removes a field. It reads the
# installed Claude Code executable and asks whether each name the hooks are
# built from still appears in it. That is a weaker claim than "the CLI honours
# the decision" — only a live session proves behaviour — but it is the strongest
# one available without spending a model call, and it fails loudly on the change
# that would otherwise degrade this framework in silence.
printf '\n%s2. the installed Claude Code still contains every name the hooks emit%s\n' "$B" "$N"

CLAUDE_BIN=""
if command -v claude >/dev/null 2>&1; then
  CLAUDE_BIN="$(readlink -f "$(command -v claude)" 2>/dev/null)"
fi

# A name no hook emits and no CLI defines. Without it, "every name was found"
# could equally mean the search matches everything.
CANARY="aidevAbsentHookKeyDoNotDefine"
NAMES="hookSpecificOutput|hookEventName|PreToolUse|PermissionRequest|SessionStart|permissionDecision|permissionDecisionReason|additionalContext|behavior|updatedInput|updatedPermissions|interrupt"

if [ -z "$CLAUDE_BIN" ] || [ ! -r "$CLAUDE_BIN" ]; then
  defer "the installed Claude Code contains the hook vocabulary" \
        "no readable \`claude\` on PATH — this check reads the shipped executable, and there is none here"
  defer "control: an absent name is reported absent" "same reason"
else
  found="$(grep -aoE "$NAMES|$CANARY" "$CLAUDE_BIN" 2>/dev/null | sort -u)"
  missing=""
  # shellcheck disable=SC2086
  for n in $(printf '%s' "$NAMES" | tr '|' ' '); do
    printf '%s\n' "$found" | grep -qx "$n" || missing="$missing $n"
  done
  if [ -z "$missing" ]; then
    ok "all $(printf '%s' "$NAMES" | tr '|' '\n' | grep -c .) hook field names are present in $(basename "$CLAUDE_BIN")"
  else
    bad "the installed Claude Code contains the hook vocabulary" \
        "absent from the shipped executable:$missing — a renamed or removed field means the hooks' output is parsed as something else, or not at all. Re-read the hooks reference before trusting any other suite in this repository."
  fi

  if printf '%s\n' "$found" | grep -qx "$CANARY"; then
    bad "control: an absent name is reported absent" \
        "the canary '$CANARY' was 'found', so this search cannot tell present from absent and the assertion above proves nothing"
  else
    ok "control: an invented name is not found, so the search distinguishes present from absent"
  fi
fi

printf '\n'
if [ "$FAIL" -eq 0 ]; then printf '%s%d passed%s\n' "$G" "$PASS" "$N"; exit 0; fi
printf '%s%d passed · %d FAILED%s\n' "$R" "$PASS" "$FAIL" "$N"; exit 1
