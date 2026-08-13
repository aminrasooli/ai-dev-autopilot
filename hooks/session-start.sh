#!/usr/bin/env bash
# AI-DEV SessionStart hook.
#
# Emits a short, factual status line as additionalContext: which project this
# is, whether it has been bootstrapped, and whether the security posture is
# actually active. Fast and read-only. Never prints file contents.

set -uo pipefail

AI_DEV_HOME="${AI_DEV_HOME:-$HOME/.ai-dev}"
input="$(cat)"
cwd="$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null)"
[ -n "$cwd" ] || cwd="$PWD"

lines=()
add() { lines+=("$1"); }

root="$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null || true)"
project="${root:-$cwd}"

if [ "$project" = "$AI_DEV_HOME" ]; then
  add "AI-DEV: you are in the framework hub. Framework edits are allowed here."
  add "After changing adapters/, hooks/ or skills/, run: make sync && make doctor"
else
  add "AI-DEV active. Hub: $AI_DEV_HOME (read-only from this session)."
  if [ -n "$root" ]; then
    if [ -f "$project/.ai/project.yaml" ]; then
      add "Project: $(basename "$project") — bootstrapped (.ai/project.yaml present)."
      [ -f "$project/.ai/decisions.md" ] || add "No .ai/decisions.md yet; create it when a decision is worth keeping."
    else
      add "Project: $(basename "$project") — NOT bootstrapped. Inspect it first, then run the project-bootstrap skill if this is real work rather than a one-off."
    fi
  else
    add "Not inside a git repository."
  fi
fi

# Posture: report, never repair.
posture=()
[ -e "$HOME/.claude/CLAUDE.md" ] || posture+=("global policy not linked")
[ -e "$HOME/.claude/skills/project-bootstrap" ] || posture+=("skills not linked")
[ -e "$HOME/.codex/auth.json" ] && posture+=("WARNING: ~/.codex/auth.json exists and must not")
if [ ${#posture[@]} -gt 0 ]; then
  add "AI-DEV posture problems: ${posture[*]}. Run: $AI_DEV_HOME/bin/doctor"
fi

ctx="$(printf '%s\n' "${lines[@]}")"
jq -n --arg c "$ctx" \
  '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$c}}'
