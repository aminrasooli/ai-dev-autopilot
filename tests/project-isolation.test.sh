#!/usr/bin/env bash
# AI-DEV contract test — a hostile checked-out repository cannot inject
# executable configuration into a normal `aidev` session.
#
# The security property under test:
#
#   An untrusted repository may supply SOURCE CODE and ordinary project files
#   for Claude to inspect. It must not be able to supply instructions, skills,
#   agents, commands, hooks, MCP integrations, output styles or security policy.
#
# WHY THIS TEST DOES NOT USE `claude doctor`
#
# Running `claude doctor` and watching for the repository's settings path in the
# output is not enough. That observes settings-file *validation* and nothing
# else: a hostile CLAUDE.md, skill, agent or .mcp.json is never exercised, so
# such a test passes without touching four of the six classes it appears to
# cover.
#
# WHAT IT USES INSTEAD
#
# `--output-format stream-json` emits a `system/init` event before the first
# model turn that enumerates exactly what the session loaded:
#
#   slash_commands[]  skills[]  agents[]  mcp_servers[]  plugins[]
#   output_style      permissionMode      tools[]
#
# That is Claude Code's own account of its resolved configuration, not an
# inference from silence. Each customization class is asserted against the list
# that class appears in. Where a class can act rather than merely be listed —
# hooks, the MCP server process, the status line — the payload writes a marker
# file, and the marker is checked as well: `mcp_servers` proves it was not
# registered, the absent marker proves no process was spawned.
#
# Absence of model output is never used as evidence. It cannot be: the init
# event is emitted before authentication, and a nested session inside the
# sandbox has no credentials (see LIMITATION below).
#
# BASELINE FIRST
#
# Every assertion runs twice: once with plain `claude` to establish that the
# payload is live and reaches the surface it targets, and once through the
# production `aidev` path. An isolation test that never sees the attack work is
# indistinguishable from a broken test.
#
# LIMITATION, stated rather than papered over
#
# This test proves what is LOADED. It cannot additionally prove the model would
# have disobeyed a hostile instruction, because `~/.claude/.credentials.json` is
# a denied path inside the sandbox, so the nested session reports "Not logged
# in" and never runs a model turn. That is the correct trade: a hostile
# instruction that never enters the context window cannot be obeyed, and
# "the model ignored it" was always the weaker of the two properties.
#
# Nothing here runs a model turn, so the test costs nothing and needs no auth.
#
# Exit codes: 0 all passed · 1 a contract was violated · 3 prerequisites missing

set -uo pipefail

# Default to the repository this script lives in, so a fresh clone tests
# itself rather than whatever happens to be installed at ~/.ai-dev. An
# explicit AI_DEV_HOME still wins.
AI_DEV_HOME="${AI_DEV_HOME:-$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
AIDEV="$AI_DEV_HOME/bin/aidev"
FIX="$AI_DEV_HOME/tests/fixtures/hostile-project"
RUN="$AI_DEV_HOME/tests/fixtures/.run-hostile"
PROBE_TIMEOUT="${AIDEV_PROBE_TIMEOUT:-120}"

if [ -t 1 ]; then G=$'\e[32m'; R=$'\e[31m'; Y=$'\e[33m'; B=$'\e[2m'; N=$'\e[0m'
else G=""; R=""; Y=""; B=""; N=""; fi
PASS=0; FAIL=0; WARN=0
ok()   { PASS=$((PASS+1)); printf '  %sPASS%s  %s\n' "$G" "$N" "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  %sFAIL%s  %s\n        %s\n' "$R" "$N" "$1" "${2:-}"; }
warn() { WARN=$((WARN+1)); printf '  %sWARN%s  %s\n        %s\n' "$Y" "$N" "$1" "${2:-}"; }

command -v claude >/dev/null 2>&1 || { printf 'skip: claude not on PATH\n'; exit 3; }
[ -x "$AIDEV" ] || { printf 'skip: %s missing\n' "$AIDEV"; exit 3; }
[ -d "$FIX" ]   || { printf 'skip: fixture %s missing\n' "$FIX"; exit 3; }

cleanup() { rm -rf "$RUN"; }
trap cleanup EXIT

# ------------------------------------------------------------- materialize
# The fixture is stored inert: non-discovery filenames, and @@RUNDIR@@ instead
# of any real path. This is where it becomes live, in a gitignored directory
# that is deleted on exit.
materialize() {
  rm -rf "$RUN"
  mkdir -p "$RUN"
  cp -R "$FIX/claude"            "$RUN/.claude"
  cp    "$FIX/claude-md/CLAUDE.md"        "$RUN/CLAUDE.md"
  cp    "$FIX/claude-md/CLAUDE.local.md"  "$RUN/CLAUDE.local.md"
  cp    "$FIX/mcp.json"          "$RUN/.mcp.json"
  cp    "$FIX/AGENTS.md"         "$RUN/AGENTS.md"
  printf 'int main(void){return 0;}\n' > "$RUN/main.c"

  # settings.local.json is held back from the commit on purpose: an UNTRACKED
  # local settings file is the scope that historically bypassed the workspace
  # trust gate, so the fixture has to reproduce that shape to test it.
  mv "$RUN/.claude/settings.local.json" "$RUN/.settings.local.json.staged"

  local f
  while IFS= read -r f; do
    [ -f "$f" ] && sed -i "s|@@RUNDIR@@|$RUN|g" "$f"
  done < <(grep -rl '@@RUNDIR@@' "$RUN" 2>/dev/null)

  git -C "$RUN" init -q >/dev/null 2>&1
  git -C "$RUN" add -A >/dev/null 2>&1
  git -C "$RUN" -c user.email=hostile@example.invalid -c user.name=hostile \
      commit -qm 'hostile payload' >/dev/null 2>&1

  mv "$RUN/.settings.local.json.staged" "$RUN/.claude/settings.local.json"
  sed -i "s|@@RUNDIR@@|$RUN|g" "$RUN/.claude/settings.local.json"
}

# ----------------------------------------------------------------- probing
# Capture the system/init event. Everything before the first model turn, so no
# credentials and no cost. stderr is kept: that is where a refusal would appear.
INIT=""; PROBE_RC=0; PROBE_ERR=""
probe() {
  local out
  out="$(cd "$RUN" && timeout "$PROBE_TIMEOUT" "$@" \
          -p 'reply READY' --output-format stream-json --verbose 2>"$RUN/.stderr")"
  PROBE_RC=$?
  PROBE_ERR="$(head -c 2000 <"$RUN/.stderr" 2>/dev/null)"
  INIT="$(printf '%s\n' "$out" | grep -m1 '"subtype":"init"')"
}

# Read one JSON array or scalar field out of the init line without needing jq.
field() { printf '%s' "$INIT" | grep -o "\"$1\":\[[^]]*\]" | head -1; }
scalar() { printf '%s' "$INIT" | grep -o "\"$1\":\"[^\"]*\"" | head -1 | sed 's/.*:"//;s/"$//'; }

marker() { [ -e "$RUN/$1" ]; }

printf 'AI-DEV project-customization isolation contract\n'
printf '%s── fixture:  %s%s\n' "$B" "$FIX" "$N"
printf '%s── run copy: %s (gitignored, deleted on exit)%s\n\n' "$B" "$RUN" "$N"

# =====================================================================
# PART 1 — baseline: prove the payload is live and the attack is real
# =====================================================================
printf '%s1. baseline — plain `claude`, no isolation flags%s\n' "$B" "$N"
materialize
probe claude

if [ -z "$INIT" ]; then
  printf '  %sSKIP%s  the probe produced no init event (rc=%s)\n        %s\n' \
    "$Y" "$N" "$PROBE_RC" "$(printf '%s' "$PROBE_ERR" | head -2)"
  printf '        Without a baseline this test cannot distinguish isolation from a broken probe.\n'
  exit 3
fi

base_cmds="$(field slash_commands)"
base_agents="$(field agents)"
base_skills="$(field skills)"
base_mcp="$(field mcp_servers)"

attack_live=0
case "$base_cmds$base_skills"   in *exfiltrate*|*canarycmd*) attack_live=1 ;; esac
case "$base_agents"             in *canary-agent*)           attack_live=1 ;; esac
case "$base_mcp"                in *canary*)                 attack_live=1 ;; esac

if [ "$attack_live" = "1" ]; then
  ok "baseline: plain \`claude\` DOES load the hostile repository's customizations"
  printf '        %sslash_commands: %s%s\n' "$B" "$(printf '%s' "$base_cmds" | grep -o 'exfiltrate\|canarycmd' | tr '\n' ' ')" "$N"
  printf '        %sagents:         %s%s\n' "$B" "$(printf '%s' "$base_agents" | grep -o 'canary-agent' | tr '\n' ' ')" "$N"
  printf '        %smcp_servers:    %s%s\n' "$B" "$(printf '%s' "$base_mcp" | grep -o 'canary' | tr '\n' ' ')" "$N"
else
  warn "baseline: plain \`claude\` did NOT load the hostile customizations" \
       "the vendor may now gate these behind workspace trust. Recorded, not assumed: the aidev assertions below still run, but this test no longer proves aidev is what stops them."
fi

for m in CANARY-HOOK-SESSIONSTART CANARY-HOOK-USERPROMPT CANARY-MCP-STARTED CANARY-STATUSLINE; do
  if marker "$m"; then
    printf '        %sbaseline executed: %s%s\n' "$B" "$m" "$N"
  fi
done

# =====================================================================
# PART 2 — the production path
# =====================================================================
printf '\n%s2. production path — `aidev` exactly as a human runs it%s\n' "$B" "$N"
materialize
probe "$AIDEV"

if [ -z "$INIT" ]; then
  bad "aidev produced a session init event" \
      "rc=$PROBE_RC · $(printf '%s' "$PROBE_ERR" | head -2)"
  printf '\n%s%d passed, %d failed, %d warnings%s\n' "$R" "$PASS" "$FAIL" "$WARN" "$N"
  exit 1
fi
ok "aidev starts and reports a session init event"

cmds="$(field slash_commands)"; agents="$(field agents)"
skills="$(field skills)";       mcp="$(field mcp_servers)"
plugins="$(field plugins)";     style="$(scalar output_style)"
mode="$(scalar permissionMode)"

# ---- instruction surfaces (CLAUDE.md family) ----
# Proven by their absence from the loaded-configuration lists AND by the
# marker/registration checks below; the CLAUDE.md family additionally cannot
# be confirmed from init alone, so it is cross-checked against the debug log.
dbg="$(cd "$RUN" && timeout "$PROBE_TIMEOUT" "$AIDEV" -p 'reply READY' --debug 2>&1 | head -c 200000)"
claudemd_hits="$(printf '%s' "$dbg" | grep -c "$RUN/CLAUDE.md\|$RUN/.claude/CLAUDE.md\|$RUN/CLAUDE.local.md\|$RUN/.claude/rules" 2>/dev/null)"
if [ "${claudemd_hits:-0}" -eq 0 ]; then
  ok "no project CLAUDE.md / CLAUDE.local.md / .claude/rules path is read"
else
  bad "no project CLAUDE.md / CLAUDE.local.md / .claude/rules path is read" \
      "the debug log references $claudemd_hits project instruction path(s)"
fi

# ---- skills ----
case "$skills$cmds" in
  *exfiltrate*) bad "the hostile project skill is not registered" "found in skills/slash_commands: $skills" ;;
  *)            ok  "the hostile project skill is not registered" ;;
esac

# ---- custom commands ----
case "$cmds" in
  *canarycmd*) bad "the hostile project command is not registered" "found in slash_commands" ;;
  *)           ok  "the hostile project command is not registered" ;;
esac

# ---- subagents ----
case "$agents" in
  *canary-agent*) bad "the hostile project agent is not registered" "found in agents: $agents" ;;
  *)              ok  "the hostile project agent is not registered" ;;
esac

# ---- MCP: registration AND process spawn ----
case "$mcp" in
  *canary*) bad "the hostile .mcp.json server is not registered" "found in mcp_servers: $mcp" ;;
  *)        ok  "the hostile .mcp.json server is not registered" ;;
esac
if marker CANARY-MCP-STARTED; then
  bad "the hostile MCP server process was never spawned" "marker CANARY-MCP-STARTED exists"
else
  ok  "the hostile MCP server process was never spawned"
fi

# ---- plugins ----
case "$plugins" in
  *canary*) bad "no hostile plugin is loaded" "found in plugins: $plugins" ;;
  *)        ok  "no hostile plugin is loaded" ;;
esac

# ---- output style ----
case "$style" in
  canary*) bad "the hostile output style is not applied" "output_style=$style" ;;
  *)       ok  "the hostile output style is not applied (output_style=$style)" ;;
esac

# ---- hooks: every lifecycle event the payload registered ----
hook_leak=0
for m in CANARY-HOOK-SESSIONSTART CANARY-HOOK-USERPROMPT CANARY-HOOK-PRETOOLUSE \
         CANARY-HOOK-LOCAL-SESSIONSTART CANARY-STATUSLINE; do
  if marker "$m"; then bad "hook/statusline payload $m did not execute" "marker exists"; hook_leak=1; fi
done
[ "$hook_leak" = "0" ] && ok "no project hook, local-settings hook or status-line command executed"

# ---- permission posture is ours, not the repository's ----
# NOT read from the init event. Measured on Claude Code 2.1.x: under -p the
# init event reports permissionMode:"default" whatever was passed —
# `--permission-mode plan` reports "default" too. It is a constant in print
# mode, so it is evidence of nothing. The real assertions are (a) what the
# launcher puts on argv, checked against a stub claude below, and (b) that the
# repository's settings file is never read at all, which is what would have
# carried its defaultMode:bypassPermissions.
if [ -n "$mode" ]; then
  printf '        %sinit reported permissionMode=%s (constant under -p; not used as evidence)%s\n' \
    "$B" "$mode" "$N"
fi

stub="$RUN/.stub"; mkdir -p "$stub"
printf '#!/bin/sh\nprintf "%%s\\n" "$*"\n' > "$stub/claude"
chmod +x "$stub/claude"
argv="$(cd "$RUN" && PATH="$stub:$PATH" "$AIDEV" 2>/dev/null)"
case "$argv" in
  *"--permission-mode auto"*) ok "aidev pins --permission-mode auto on the real command line" ;;
  *) bad "aidev pins --permission-mode auto on the real command line" "argv: $argv" ;;
esac
case "$argv" in
  *"--setting-sources user"*) ok "aidev pins --setting-sources user on the real command line" ;;
  *) bad "aidev pins --setting-sources user on the real command line" "argv: $argv" ;;
esac
case "$argv" in
  *project*|*local*) bad "aidev names no project or local settings scope" "argv: $argv" ;;
  *) ok "aidev names no project or local settings scope" ;;
esac

# ---- the repository's own settings file is not read at all ----
if printf '%s' "$dbg" | grep -q "$RUN/.claude/settings"; then
  bad "the repository's settings files are not read" "the debug log references them"
else
  ok "the repository's settings files are not read"
fi

# ---- source code is still available: the boundary must not break the tool ----
if [ -f "$RUN/main.c" ]; then
  ok "ordinary project files remain present for inspection (the boundary is not a lockout)"
fi

printf '\n'
if [ "$FAIL" -eq 0 ]; then
  printf '%s%d passed%s' "$G" "$PASS" "$N"
  [ "$WARN" -gt 0 ] && printf ', %s%d warnings%s' "$Y" "$WARN" "$N"
  printf '\n'; exit 0
fi
printf '%s%d passed, %d failed%s' "$R" "$PASS" "$FAIL" "$N"
[ "$WARN" -gt 0 ] && printf ', %s%d warnings%s' "$Y" "$WARN" "$N"
printf '\n'; exit 1
