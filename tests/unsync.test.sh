#!/usr/bin/env bash
# Contract test for `ai-dev unsync`, run with a disposable scratch HOME.
#
# Evidence: the stranger test (2026-10-17) found `make sync` has no documented
# reverse — only `make unmanage` exists, which undoes `make manage`, not
# `make sync`. This asserts the smallest fix: a file sync overwrote comes back
# exactly as it was, and a file sync created fresh is removed again, leaving a
# scratch home indistinguishable from one that was never synced.

set -uo pipefail
AI_DEV_HOME="${AI_DEV_HOME:-$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"

FAIL=0
ok()  { printf '  PASS  %s\n' "$1"; }
bad() { FAIL=1; printf '  FAIL  %s\n        %s\n' "$1" "$2"; }

T="$(mktemp -d "${TMPDIR:-/tmp}/aidev-unsync.XXXXXX")"
trap 'rm -rf "$T"' EXIT
export HOME="$T"
mkdir -p "$T/bin"
export PATH="$T/bin:$PATH"

echo "unsync contract"
echo "  scratch home: $T"

# A file that pre-exists before the first sync, so sync must back it up and
# unsync must put this exact content back.
mkdir -p "$T/.claude"
printf '{"preexisting": true}\n' >"$T/.claude/settings.json"

"$AI_DEV_HOME/bin/ai-dev" sync >"$T/sync.out" 2>&1
rc=$?
[ "$rc" -eq 0 ] || { bad "sync succeeds in the scratch home" "exit $rc:"; cat "$T/sync.out"; exit 1; }
ok "sync succeeds in the scratch home"

[ -f "$T/.claude/CLAUDE.md" ] && ok "sync wrote CLAUDE.md (created fresh)" || bad "sync wrote CLAUDE.md" "missing"
jq -e '.hooks' "$T/.claude/settings.json" >/dev/null 2>&1 \
  && ok "sync merged hub keys into the preexisting settings.json" \
  || bad "sync merged hub keys into the preexisting settings.json" "no .hooks key after sync"
grep -q preexisting "$T/.claude/settings.json" >/dev/null 2>&1 \
  && ok "the merge kept the preexisting key (user preferences preserved)" \
  || bad "the merge kept the preexisting key" "marker lost"
[ -L "$T/bin/aidev" ] && ok "sync linked the launcher (created fresh)" || bad "sync linked the launcher" "missing"
backup_dir="$(ls -1dt "$T"/.ai-dev-backups/*/ 2>/dev/null | head -1)"
[ -n "$backup_dir" ] && ok "sync left a backup directory" || bad "sync left a backup directory" "none found"
[ -n "$backup_dir" ] && [ -f "${backup_dir%/}/.claude_settings.json" ] \
  && ok "the preexisting settings.json was backed up" \
  || bad "the preexisting settings.json was backed up" "backup file missing"

"$AI_DEV_HOME/bin/ai-dev" unsync >"$T/unsync.out" 2>&1
rc=$?
[ "$rc" -eq 0 ] || { bad "unsync succeeds" "exit $rc:"; cat "$T/unsync.out"; exit 1; }
ok "unsync succeeds"

[ ! -e "$T/.claude/CLAUDE.md" ] && ok "unsync removed CLAUDE.md (sync had created it)" \
  || bad "unsync removed CLAUDE.md" "still present"
[ ! -e "$T/bin/aidev" ] && ok "unsync removed the launcher symlink" \
  || bad "unsync removed the launcher symlink" "still present"
[ -f "$T/.claude/settings.json" ] && diff -q <(printf '{"preexisting": true}\n') "$T/.claude/settings.json" >/dev/null 2>&1 \
  && ok "unsync restored the preexisting settings.json verbatim (merged .hooks key gone)" \
  || bad "unsync restored the preexisting settings.json verbatim" "file differs from its pre-sync content"
[ -d "$backup_dir" ] && ok "unsync left the backup directory in place" \
  || bad "unsync left the backup directory in place" "backup directory was removed"

for d in "$T/.claude/skills" "$T/.codex/skills"; do
  [ -d "$d" ] || continue
  for s in "$d"/*; do
    [ -e "$s" ] || continue
    case "$(readlink -f "$s" 2>/dev/null)" in
      "$AI_DEV_HOME"/skills/*) bad "unsync removed skill symlink $s" "still points into the hub" ;;
    esac
  done
done
ok "no hub skill symlink survives unsync"

[ "$FAIL" -ne 0 ] && exit 1
exit 0
