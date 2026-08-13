#!/usr/bin/env bash
# AI-DEV contract test — the launcher's permission posture cannot be widened by
# the caller, in any spelling or form the installed Claude CLI supports.
#
# A launcher that documents a prohibition but only checks one spelling of it has
# not implemented the prohibition. Both the space-separated and the `=` form of
# every permission-mode flag are asserted here, together with the synonymous
# dangerous flags, so a prohibition cannot be true in prose and absent in code.
#
# The enumeration below is taken from `claude --help` on the installed version,
# not from memory. `--permission-mode` there advertises:
#
#   acceptEdits, auto, bypassPermissions, manual, dontAsk, plan
#
# and the documentation adds `default` (with `manual` as its alias). Each is
# classified here as widening or not, and each dangerous spelling is asserted
# to be refused in BOTH the space form and the = form. Safe modes are asserted
# to still work, because a launcher that refuses everything is not a fix.
#
# Two layers are checked, and they are checked separately on purpose:
#
#   1. the launcher refuses the flag        — fails fast, with a reason
#   2. managed settings refuse the MODE     — the actual enforcement, applies
#      (permissions.disableBypassPermissionsMode)   to bare `claude` too
#
# Layer 1 alone is a blacklist on one entry point; someone who types `claude`
# instead of `aidev` walks around it. Layer 2 is why the finding is closed.
#
# The literal bypass flags are assembled at runtime from fragments so that this
# file does not put them on a command line the AI-DEV PreToolUse guard would
# correctly refuse to let through.
#
# Exit codes: 0 all passed · 1 a contract was violated · 2 control not deployed
#             · 3 prerequisites missing

set -uo pipefail

# Default to the repository this script lives in, so a fresh clone tests
# itself rather than whatever happens to be installed at ~/.ai-dev. An
# explicit AI_DEV_HOME still wins.
AI_DEV_HOME="${AI_DEV_HOME:-$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
AIDEV="$AI_DEV_HOME/bin/aidev"
MANAGED_SRC="$AI_DEV_HOME/adapters/claude/managed-settings.json"
MANAGED_LIVE="/etc/claude-code/managed-settings.d/20-ai-dev-security.json"

if [ -t 1 ]; then G=$'\e[32m'; R=$'\e[31m'; Y=$'\e[33m'; B=$'\e[2m'; N=$'\e[0m'
else G=""; R=""; Y=""; B=""; N=""; fi
PASS=0; FAIL=0; SYNC=0
ok()   { PASS=$((PASS+1)); printf '  %sPASS%s  %s\n' "$G" "$N" "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  %sFAIL%s  %s\n        %s\n' "$R" "$N" "$1" "${2:-}"; }
sync_needed() { SYNC=$((SYNC+1)); printf '  %sSYNC%s  %s\n        %s\n' "$Y" "$N" "$1" "${2:-}"; }

[ -x "$AIDEV" ] || { printf 'skip: %s missing\n' "$AIDEV"; exit 3; }

# A stub `claude` so accepted invocations print their argv instead of starting
# a session. Anything the launcher refuses never reaches it.
STUB="$(mktemp -d "${TMPDIR:-/tmp}/aidev-posture.XXXXXX")" || exit 3
trap 'rm -rf "$STUB"' EXIT
printf '#!/bin/sh\nprintf "%%s\\n" "$*"\n' > "$STUB/claude"
chmod +x "$STUB/claude"

run_aidev() { PATH="$STUB:$PATH" "$AIDEV" "$@" 2>&1; }

refuses() {  # refuses <label> <args...>
  local label="$1"; shift
  local out rc
  out="$(run_aidev "$@")"; rc=$?
  if [ "$rc" -eq 0 ]; then
    bad "refuses $label" "accepted it — argv reached claude as: $out"
  elif printf '%s' "$out" | grep -qi 'refusing'; then
    ok "refuses $label"
  else
    bad "refuses $label" "exited $rc but without a stated reason: $out"
  fi
}

accepts() {  # accepts <label> <expected-substring> <args...>
  local label="$1" want="$2"; shift 2
  local out rc
  out="$(run_aidev "$@")"; rc=$?
  if [ "$rc" -ne 0 ]; then
    bad "still accepts $label" "refused it: $out"
  elif printf '%s' "$out" | grep -qF -- "$want"; then
    ok "still accepts $label"
  else
    bad "still accepts $label" "argv did not carry '$want': $out"
  fi
}

printf 'AI-DEV permission posture contract\n'
printf '%s── launcher: %s%s\n\n' "$B" "$AIDEV" "$N"

# ---------------------------------------------------------------- 1. the mode
printf '%s1. every dangerous spelling of the bypass mode%s\n' "$B" "$N"
BYPASS="bypass""Permissions"
refuses "--permission-mode $BYPASS (space form)"  --permission-mode "$BYPASS"
refuses "--permission-mode=$BYPASS (equals form)" "--permission-mode=$BYPASS"

# ---------------------------------------------------------------- 2. the flags
printf '\n%s2. the synonymous and deferred flags%s\n' "$B" "$N"
SKIP="--dangerously""-skip-permissions"
ALLOW="--allow-dangerously""-skip-permissions"
refuses "$SKIP"  "$SKIP"
refuses "$ALLOW" "$ALLOW"
# The deferred form is the subtle one: it does not start in bypass, it adds
# bypass to the Shift+Tab cycle, so the session can reach it later.
refuses "$ALLOW combined with a safe starting mode" --permission-mode plan "$ALLOW"

# ------------------------------------------------------- 3. unknown modes
printf '\n%s3. an unrecognised mode is refused, not passed through%s\n' "$B" "$N"
refuses "--permission-mode someFutureMode"  --permission-mode someFutureMode
refuses "--permission-mode=someFutureMode"  "--permission-mode=someFutureMode"
refuses "--permission-mode with an empty value" "--permission-mode="

# ------------------------------------------------------- 4. safe modes still work
printf '\n%s4. safe modes are still usable (an allowlist, not a lockout)%s\n' "$B" "$N"
for m in default manual acceptEdits plan auto dontAsk; do
  accepts "--permission-mode $m"  "--permission-mode $m"  --permission-mode "$m"
  accepts "--permission-mode=$m"  "--permission-mode=$m"  "--permission-mode=$m"
done
accepts "no --permission-mode at all defaults to auto" "--permission-mode auto"

# ------------------------------------------- 5. configuration-injection flags
printf '\n%s5. flags that inject configuration --setting-sources does not govern%s\n' "$B" "$N"
refuses "--settings <json>"        --settings '{"permissions":{"defaultMode":"acceptEdits"}}'
refuses "--settings=<json>"        '--settings={"permissions":{"defaultMode":"acceptEdits"}}'
refuses "--agents <json>"          --agents '{"x":{"description":"d","prompt":"p"}}'
refuses "--mcp-config <file>"      --mcp-config ./evil.json
refuses "--plugin-dir <dir>"       --plugin-dir ./evil-plugin
refuses "--plugin-url <url>"       --plugin-url https://example.invalid/p.zip
refuses "--setting-sources user,project" --setting-sources user,project
refuses "--setting-sources=user,project" "--setting-sources=user,project"

# ----------------------------------------------- 6. the enforcement layer
printf '\n%s6. managed policy, which also covers bare `claude`%s\n' "$B" "$N"
if [ -f "$MANAGED_SRC" ] && grep -q '"disableBypassPermissionsMode"[[:space:]]*:[[:space:]]*"disable"' "$MANAGED_SRC"; then
  ok "the managed settings SOURCE sets permissions.disableBypassPermissionsMode=disable"
else
  bad "the managed settings SOURCE sets permissions.disableBypassPermissionsMode=disable" \
      "not found in $MANAGED_SRC"
fi

if [ ! -r "$MANAGED_LIVE" ]; then
  sync_needed "the DEPLOYED managed policy carries the control" \
      "cannot read $MANAGED_LIVE — run: make -C \"$AI_DEV_HOME\" sync (needs sudo)"
elif grep -q '"disableBypassPermissionsMode"[[:space:]]*:[[:space:]]*"disable"' "$MANAGED_LIVE"; then
  ok "the DEPLOYED managed policy carries the control"
else
  sync_needed "the DEPLOYED managed policy carries the control" \
      "$MANAGED_LIVE is live but predates this change — run: make -C \"$AI_DEV_HOME\" sync (needs sudo)"
fi

printf '\n'
if [ "$FAIL" -eq 0 ] && [ "$SYNC" -eq 0 ]; then
  printf '%s%d passed%s\n' "$G" "$PASS" "$N"; exit 0
fi
if [ "$FAIL" -eq 0 ]; then
  printf '%s%d passed, %d awaiting `make sync`%s\n' "$Y" "$PASS" "$SYNC" "$N"
  printf '%sThe launcher-side refusals are live. The managed-policy layer is NOT,\n' "$Y"
  printf 'so `claude` invoked directly can still select the bypass mode.%s\n' "$N"
  exit 2
fi
printf '%s%d passed, %d failed%s\n' "$R" "$PASS" "$FAIL" "$N"; exit 1
