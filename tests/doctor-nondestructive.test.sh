#!/usr/bin/env bash
# AI-DEV contract test — bin/doctor never damages the machine it inspects.
#
# THE DEFECT THIS PINS
#
# doctor answers "is this path writable?" for a list of real, valuable host
# paths — ~/.bashrc, ~/.zshrc, ~/.profile, ~/.gitconfig — because those are the
# denyWrite entries that carry the load when the sandbox cannot confirm write
# confinement. The obvious way to ask is `: > "$path"`, and it is wrong: the
# redirection opens with O_TRUNC and empties the file, and the `rm -f` that
# tidies the probe away then deletes it.
#
# The blast radius is the opposite of theoretical. That branch runs precisely
# when writes are NOT being confined, which is the state of a machine that has
# not been `make sync`ed yet — so the first `make doctor` a new user runs is the
# one that silently destroys their shell configuration. It also contradicts what
# doctor says about itself in its own header, and what README.md claims about
# the suite as a whole.
#
# So the probe must be able to say "writable" without writing anything and
# without removing anything it did not create. Section 1 proves the destructive
# shape really is destructive, so this file cannot quietly stop testing
# anything; section 2 proves the shipped helper is not that shape; section 3
# reads bin/doctor itself, so a future edit cannot reintroduce the pattern
# somewhere the behavioural test does not reach.
#
# Exit codes: 0 all passed · 1 a contract was violated · 3 prerequisites missing

set -uo pipefail

AI_DEV_HOME="${AI_DEV_HOME:-$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
DOCTOR="$AI_DEV_HOME/bin/doctor"

if [ -t 1 ]; then G=$'\e[32m'; R=$'\e[31m'; B=$'\e[2m'; N=$'\e[0m'
else G=""; R=""; B=""; N=""; fi
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf '  %sPASS%s  %s\n' "$G" "$N" "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  %sFAIL%s  %s\n        %s\n' "$R" "$N" "$1" "${2:-}"; }

[ -r "$DOCTOR" ] || { printf 'skip: %s missing\n' "$DOCTOR"; exit 3; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/aidev-doctor-nondestructive.XXXXXX")" || exit 3
trap 'chmod -R u+w "$WORK" 2>/dev/null; rm -rf "$WORK"' EXIT

printf 'doctor non-destructive probe contract\n'
printf '%s── disposable tree: %s%s\n' "$B" "$WORK" "$N"

# Bind the test to the SHIPPED implementation rather than to a copy of it. A
# reimplementation here would keep passing after bin/doctor regressed, which is
# the failure mode this whole file exists to prevent.
probe_src="$(awk '/^writable_probe\(\) \{/,/^\}/' "$DOCTOR")"
if [ -z "$probe_src" ]; then
  bad "bin/doctor defines writable_probe()" "no such function — the probe helper is gone"
  printf '\n%s%d passed, %d failed%s\n' "$R" "$PASS" "$FAIL" "$N"; exit 1
fi
ok "bin/doctor defines writable_probe()"
eval "$probe_src"

CONTENT='export PATH=/something/the/user/needs:$PATH'

# ------------------------------------- 1. the destructive shape IS destructive
# Without this, section 2 could pass against a filesystem that silently refused
# every write, and would be measuring nothing at all.
printf '\n1. baseline: the truncating probe really does destroy a real file\n'
f="$WORK/baseline.bashrc"; printf '%s\n' "$CONTENT" > "$f"
if ( : > "$f" ) 2>/dev/null; then rm -f "$f" 2>/dev/null; fi
if [ -e "$f" ]; then
  bad "baseline: \`: > file\` followed by rm destroys the file" \
      "the file survived, so this environment cannot demonstrate the defect and section 2 proves nothing"
else
  ok "baseline: \`: > file\` followed by rm destroys the file"
fi

# ------------------------------------------ 2. the shipped helper is not that
printf '\n2. writable_probe answers without destroying anything\n'

f="$WORK/real.bashrc"; printf '%s\n' "$CONTENT" > "$f"
before="$(cat "$f")"
if writable_probe "$f"; then ok "an existing writable file is reported writable"
else bad "an existing writable file is reported writable" "writable_probe said no"; fi
if [ -e "$f" ]; then ok "...and the file still exists"
else bad "...and the file still exists" "writable_probe deleted it"; fi
if [ "$(cat "$f" 2>/dev/null)" = "$before" ]; then ok "...and its contents are byte-for-byte unchanged"
else bad "...and its contents are byte-for-byte unchanged" "content was truncated or appended to"; fi

# A path that does not exist must still be answerable, and must not be left
# behind: doctor probes ~/.zshrc on machines that do not use zsh, and inventing
# one would change the host it is only supposed to be reading.
f="$WORK/absent.zshrc"
if writable_probe "$f"; then ok "an absent path in a writable directory is reported writable"
else bad "an absent path in a writable directory is reported writable" "writable_probe said no"; fi
if [ ! -e "$f" ]; then ok "...and no file is left behind"
else bad "...and no file is left behind" "writable_probe created $f and kept it"; fi

d="$WORK/somedir"; mkdir -p "$d"; printf 'keep me\n' > "$d/existing"
if writable_probe "$d"; then ok "a writable directory is reported writable"
else bad "a writable directory is reported writable" "writable_probe said no"; fi
if [ -e "$d/existing" ] && [ "$(find "$d" -type f | wc -l)" -eq 1 ]; then
  ok "...and the directory is left exactly as it was"
else
  bad "...and the directory is left exactly as it was" "contents changed: $(find "$d" -type f | tr '\n' ' ')"
fi

# The refusal path is the one that decides a security verdict, so it has to be
# a refusal and not an accident.
ro="$WORK/readonly"; mkdir -p "$ro"; printf '%s\n' "$CONTENT" > "$ro/locked"; chmod 0500 "$ro"
if [ "$(id -u)" = "0" ]; then
  printf '  %sSKIP%s  a refused write is reported refused (running as root; mode bits do not apply)\n' "$B" "$N"
else
  f="$ro/absent"
  if writable_probe "$f"; then bad "a refused write is reported refused" "writable_probe claimed a read-only directory was writable"
  else ok "a refused write is reported refused"; fi
  if [ ! -e "$f" ]; then ok "...and nothing was created by the attempt"
  else bad "...and nothing was created by the attempt" "$f exists"; fi
fi
chmod 0700 "$ro"

# A path that is writable but cannot be stat'd reads as "absent" to `[ -e ]`.
# Treating that as "I created this" is how a file nobody could see gets deleted.
unread="$WORK/unreadable"; mkdir -p "$unread"
printf '%s\n' "$CONTENT" > "$unread/hidden.bashrc"
chmod 0300 "$unread"   # write+execute, no read: open works, stat of the name does not
if [ "$(id -u)" = "0" ]; then
  printf '  %sSKIP%s  an unstattable but writable file is not deleted (running as root)\n' "$B" "$N"
else
  writable_probe "$unread/hidden.bashrc" >/dev/null 2>&1
  chmod 0700 "$unread"
  if [ -s "$unread/hidden.bashrc" ]; then
    ok "an unstattable but writable file is neither emptied nor deleted"
  else
    bad "an unstattable but writable file is neither emptied nor deleted" \
        "the probe destroyed a file it could not see"
  fi
fi
chmod 0700 "$unread" 2>/dev/null

# --------------------------------- 3. the pattern cannot come back by accident
# A behavioural test only covers the helper. This reads the source, so a new
# probe written the old way anywhere in the file is caught even though nothing
# in section 2 would exercise it.
printf '\n3. bin/doctor contains no truncating write probe\n'
offenders="$(grep -nE '\(\s*:\s*>[^>]' "$DOCTOR" | grep -v '^\s*#')"
if [ -z "$offenders" ]; then
  ok "no \`( : > path )\` truncating probe remains in bin/doctor"
else
  bad "no \`( : > path )\` truncating probe remains in bin/doctor" \
      "found: $(printf '%s' "$offenders" | tr '\n' ' ') — use writable_probe instead"
fi

# The tidy-up is the second half of the defect: a probe that removes a path it
# found already there is data loss even if it never truncated it. The one
# removal inside writable_probe is the guarded one — it fires only when that
# function created the file — so the check is scoped to everything ELSE, which
# is where an unguarded `rm -f "$t"` would be a bug again.
outside="$(awk '/^writable_probe\(\) \{/,/^\}/ { next } { print }' "$DOCTOR" | grep -nE 'rm -f "\$(t|cp|conf_probe|live_probe)"')"
if [ -z "$outside" ]; then
  ok "no probe outside writable_probe removes a host path"
else
  bad "no probe outside writable_probe removes a host path" \
      "found: $(printf '%s' "$outside" | tr '\n' ' ')"
fi

# ...and the removal that IS inside it must stay guarded by the "did we create
# this" flag. An unconditional rm there would reintroduce the whole defect.
if printf '%s' "$probe_src" | grep -qE 'existed" -eq 0'; then
  ok "writable_probe removes the probe file only when it created it"
else
  bad "writable_probe removes the probe file only when it created it" \
      "the guard on the rm is gone — an existing host file could be deleted again"
fi

# The claim README makes on this file's behalf.
if grep -q 'Nothing in the suite performs a destructive action' "$AI_DEV_HOME/README.md" 2>/dev/null; then
  ok "README still makes the non-destructive claim this suite is the evidence for"
else
  bad "README still makes the non-destructive claim this suite is the evidence for" \
      "the claim moved or was reworded — re-point this assertion rather than deleting it"
fi

printf '\n'
if [ "$FAIL" -gt 0 ]; then printf '%s%d passed, %d failed%s\n' "$R" "$PASS" "$FAIL" "$N"; exit 1; fi
printf '%s%d passed%s\n' "$G" "$PASS" "$N"; exit 0
