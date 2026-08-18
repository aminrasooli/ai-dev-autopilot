#!/usr/bin/env bash
# AI-DEV contract test — nothing machine-specific survives the publication
# filter.
#
# The daily contributor publishes a PR body assembled from material written
# on a private machine: the brief, the worktree path, the tail of a local
# test log. bin/sanitize-pr-body is the last thing that text passes through
# before it reaches a public forge, and this suite pins both directions of
# its contract:
#
#   1. what must be redacted: the invoking user's home directory (under any
#      spelling the XDG variables give it), other users' home directories,
#      private/CGNAT IPv4 addresses, and the machine's hostname;
#   2. what must survive: repo-relative paths, test counts, public
#      addresses, loopback, and prose that merely resembles a hostname —
#      the diagnostics a reviewer actually uses.
#
# The suite drives the filter with a fabricated HOME/XDG/hostname
# environment, so it neither depends on nor reveals anything about the
# machine it runs on.
#
# Exit codes: 0 all passed · 1 a contract was violated

set -uo pipefail

AI_DEV_HOME="${AI_DEV_HOME:-$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
SAN="$AI_DEV_HOME/bin/sanitize-pr-body"

if [ -t 1 ]; then G=$'\e[32m'; R=$'\e[31m'; N=$'\e[0m'
else G=""; R=""; N=""; fi
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf '  %sPASS%s  %s\n' "$G" "$N" "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  %sFAIL%s  %s\n        %s\n' "$R" "$N" "$1" "${2:-}"; }

[ -x "$SAN" ] || { printf 'FAIL: %s missing or not executable\n' "$SAN"; exit 1; }

# A fabricated machine. Nothing below touches the real one.
FAKE_HOME="/home/fakeuser"
run() { # $1 input → sanitized stdout under the fabricated environment
  printf '%s\n' "$1" |
    env -i PATH="$PATH" \
      HOME="$FAKE_HOME" \
      SANITIZE_HOSTNAME="buildbox-03" \
      bash "$SAN"
}

gone() { # $1 label  $2 input  $3 forbidden  $4 expected replacement
  local out; out="$(run "$2")"
  case "$out" in
    *"$3"*) bad "$1" "output still contains: $3"; return ;;
  esac
  case "$out" in
    *"$4"*) ok "$1" ;;
    *) bad "$1" "expected replacement missing: $4 (got: $out)" ;;
  esac
}

kept() { # $1 label  $2 input  $3 text that must survive verbatim
  local out; out="$(run "$2")"
  case "$out" in
    *"$3"*) ok "$1" ;;
    *) bad "$1" "text did not survive: $3 (got: $out)" ;;
  esac
}

printf 'AI-DEV publication sanitizer contract\n'

# ------------------------------------------------------------- must redact

gone "XDG state path becomes <local-state>" \
  "worktree at $FAKE_HOME/.local/state/daily/worktrees/2026-08-16 ready" \
  "$FAKE_HOME/.local/state" "<local-state>/daily/worktrees/2026-08-16"

gone "XDG config path becomes <local-config>" \
  "settings read from $FAKE_HOME/.config/tool/worker.json" \
  "$FAKE_HOME/.config" "<local-config>/tool/worker.json"

gone "XDG cache path becomes <local-cache>" \
  "cache at $FAKE_HOME/.cache/tool/x" \
  "$FAKE_HOME/.cache" "<local-cache>/tool/x"

gone "home directory becomes <HOME>" \
  "cloned into $FAKE_HOME/code/project" \
  "$FAKE_HOME" "<HOME>/code/project"

gone "install hint carries no home path" \
  "run make -C $FAKE_HOME/.local/state/w/2026-08-16 sync" \
  "$FAKE_HOME" "make -C <local-state>/w/2026-08-16 sync"

# XDG variables pointing outside $HOME are still redacted by their label.
out="$(printf 'state under /var/lib/mystate/job\n' |
  env -i PATH="$PATH" HOME="$FAKE_HOME" XDG_STATE_HOME=/var/lib/mystate \
    SANITIZE_HOSTNAME= bash "$SAN")"
case "$out" in
  *"/var/lib/mystate"*) bad "explicit XDG_STATE_HOME is redacted" "path survived" ;;
  *"<local-state>/job"*) ok "explicit XDG_STATE_HOME is redacted" ;;
  *) bad "explicit XDG_STATE_HOME is redacted" "replacement missing: $out" ;;
esac

gone "another Linux user home is redacted" \
  "copied from /home/otherperson/secrets.txt" \
  "/home/otherperson" "<HOME>/secrets.txt"

gone "a macOS user home is redacted" \
  "built on /Users/someone/work" \
  "/Users/someone" "<HOME>/work"

gone "RFC1918 192.168/16 is redacted" \
  "listening on 192.168.1.44:8080" \
  "192.168.1.44" "<private-ip>:8080"

gone "RFC1918 10/8 is redacted" \
  "peer 10.20.30.40 answered" \
  "10.20.30.40" "peer <private-ip> answered"

gone "RFC1918 172.16/12 is redacted" \
  "gateway 172.16.9.9 up" \
  "172.16.9.9" "gateway <private-ip> up"

gone "CGNAT 100.64/10 is redacted" \
  "mesh address 100.101.102.103 reachable" \
  "100.101.102.103" "mesh address <private-ip> reachable"

gone "the machine hostname is redacted" \
  "ssh to buildbox-03 worked" \
  "buildbox-03" "ssh to <host> worked"

# --------------------------------------------------------- must survive

kept "repo-relative diagnostics survive" \
  "tests/approval.test.sh 943 passed" \
  "tests/approval.test.sh 943 passed"

kept "public addresses survive" \
  "fetched https://api.github.com/repos/x/y at 140.82.112.3" \
  "140.82.112.3"

kept "loopback survives" \
  "bound to 127.0.0.1:8080 for the probe" \
  "127.0.0.1:8080"

kept "172.x outside 172.16/12 survives" \
  "the linux 172.15.0.1 and 172.32.0.1 hosts are public" \
  "172.15.0.1 and 172.32.0.1"

# A word that merely contains the hostname is not the hostname.
kept "hostname matches whole words only" \
  "the buildbox-030 machine and pre-buildbox-03 alias stay" \
  "buildbox-030 machine and pre-buildbox-03 alias"

# A short or empty hostname must not shred ordinary prose.
out="$(printf 'test the code\n' |
  env -i PATH="$PATH" HOME="$FAKE_HOME" SANITIZE_HOSTNAME="the" bash "$SAN")"
if [ "$out" = "test the code" ]; then
  ok "hostnames under 4 characters are ignored"
else
  bad "hostnames under 4 characters are ignored" "got: $out"
fi

out="$(printf 'nothing here\n' |
  env -i PATH="$PATH" HOME="$FAKE_HOME" SANITIZE_HOSTNAME= bash "$SAN")"
if [ "$out" = "nothing here" ]; then
  ok "empty SANITIZE_HOSTNAME disables hostname redaction"
else
  bad "empty SANITIZE_HOSTNAME disables hostname redaction" "got: $out"
fi

# The filter is a pass-through for text with nothing to hide.
IN='## Daily brief

- Branch: `auto/2026-08-16`
- 943 assertions passed'
out="$(run "$IN")"
if [ "$out" = "$IN" ]; then
  ok "clean text passes through byte-identical"
else
  bad "clean text passes through byte-identical" "output drifted"
fi

# ------------------------------------------------------------------ report

printf '\n  %d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
