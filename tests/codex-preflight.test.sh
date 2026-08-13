#!/usr/bin/env bash
# AI-DEV regression test — the Codex preflight reads the exit status, never the
# wording.
#
# THE FAILURE MODE THIS PREVENTS
#
# An auth guard of this shape:
#
#     codex login status | grep -qi 'chatgpt'
#
# breaks the moment Codex rewords that line. Codex is logged in, the grep
# misses, the preflight reports "Codex is not logged in with ChatGPT. Run: codex
# login", the review gate refuses to run against a perfectly healthy reviewer,
# and a human debugs a login that was never broken.
#
# The defect is not the specific string. It is reading prose as an API: any
# release can reword a status line, and a check built on a substring will keep
# failing open or closed on cosmetic changes. `codex login status` returns 0
# when authenticated and non-zero otherwise; that is the contract.
#
# WHAT THIS TEST PINS
#
#   1. exit 0 means authenticated, whatever the text says — including text that
#      contains none of the old keywords, text on stderr, and no text at all.
#      This is the exact regression: every one of these cases failed before.
#   2. a non-zero status is reported as logged out.
#   3. a non-zero status caused by an unreachable keyring is reported as
#      "cannot determine", NOT as logged out. Inside the Claude sandbox the
#      D-Bus socket is blocked by design, so a logged-in machine looks logged
#      out; telling the human to re-login sends them to fix the wrong thing.
#   4. ~/.codex/auth.json is still refused outright, ahead of everything else.
#   5. no code path suggests creating auth.json as a workaround.
#
# Every case runs the real bin/codex-review against a stub `codex` on PATH.
# Nothing here contacts the real Codex, spends anything, or touches
# ~/.codex — HOME is redirected to a temporary directory for the whole run.
#
# Exit codes: 0 all passed · 1 a contract was violated · 3 prerequisites missing

set -uo pipefail

# Default to the repository this script lives in, so a fresh clone tests
# itself rather than whatever happens to be installed at ~/.ai-dev. An
# explicit AI_DEV_HOME still wins.
AI_DEV_HOME="${AI_DEV_HOME:-$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
REVIEW="$AI_DEV_HOME/bin/codex-review"

if [ -t 1 ]; then G=$'\e[32m'; R=$'\e[31m'; B=$'\e[2m'; N=$'\e[0m'
else G=""; R=""; B=""; N=""; fi
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf '  %sPASS%s  %s\n' "$G" "$N" "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  %sFAIL%s  %s\n        %s\n' "$R" "$N" "$1" "${2:-}"; }

[ -x "$REVIEW" ] || { printf 'skip: %s missing\n' "$REVIEW"; exit 3; }
command -v git >/dev/null 2>&1 || { printf 'skip: git missing\n'; exit 3; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/aidev-preflight.XXXXXX")" || exit 3
trap 'rm -rf "$WORK"' EXIT

# A git repository, because codex-review refuses to run outside one.
REPO="$WORK/repo"; mkdir -p "$REPO"
git -C "$REPO" init -q
printf 'x\n' > "$REPO/f.txt"
git -C "$REPO" add -A >/dev/null 2>&1
git -C "$REPO" -c user.email=t@t -c user.name=t commit -qm init >/dev/null 2>&1

FAKEHOME="$WORK/home"; mkdir -p "$FAKEHOME"
BIN="$WORK/bin"; mkdir -p "$BIN"

# stub_codex <exit> <stdout> <stderr>
stub_codex() {
  { printf '#!/bin/sh\n'
    printf 'if [ "$1" = "login" ]; then\n'
    [ -n "$2" ] && printf '  printf "%%s\\n" %s\n' "$(printf '%q' "$2")"
    [ -n "$3" ] && printf '  printf "%%s\\n" %s >&2\n' "$(printf '%q' "$3")"
    printf '  exit %s\n' "$1"
    printf 'fi\n'
    printf 'exit 0\n'
  } > "$BIN/codex"
  chmod +x "$BIN/codex"
}

# Sets OUT and RC. Deliberately NOT called as `out=$(run_preflight)` — that runs
# the assignment to RC inside a subshell and every rc reads back as 0, which is
# how a green test can be measuring nothing at all.
RC=0; OUT=""
run_preflight() {
  OUT="$(cd "$REPO" && HOME="$FAKEHOME" PATH="$BIN:$PATH" \
         "$REVIEW" --diff --preflight-only 2>&1)"
  RC=$?
}

printf 'AI-DEV Codex preflight regression\n'
printf '%s── the false "not logged in"%s\n\n' "$B" "$N"

# ---------------------------------------------- 1. exit 0 is authenticated
printf '%s1. exit 0 means authenticated, whatever the wording%s\n' "$B" "$N"

# The exact shape that broke it: logged in, but the word "chatgpt" is gone.
stub_codex 0 'Logged in using your OpenAI account (Plus plan)' ''
run_preflight
if [ "$RC" -eq 0 ]; then
  ok "wording with no 'chatgpt' anywhere still passes (the original regression)"
else
  bad "wording with no 'chatgpt' anywhere still passes (the original regression)" \
      "rc=$RC · $OUT"
fi

stub_codex 0 '' ''
run_preflight
if [ "$RC" -eq 0 ]; then ok "silent success passes"
else bad "silent success passes" "rc=$RC · $OUT"; fi

stub_codex 0 '' 'note: refreshed credentials'
run_preflight
if [ "$RC" -eq 0 ]; then ok "success that writes only to stderr passes"
else bad "success that writes only to stderr passes" "rc=$RC · $OUT"; fi

stub_codex 0 'Not logged in' ''
run_preflight
if [ "$RC" -eq 0 ]; then
  ok "exit 0 wins over contradictory stdout (status is the contract, not prose)"
else
  bad "exit 0 wins over contradictory stdout (status is the contract, not prose)" \
      "rc=$RC · $OUT — the guard is reading stdout again"
fi

# ---------------------------------------------- 2. genuine logout
printf '\n%s2. a real logout is reported as a logout%s\n' "$B" "$N"
stub_codex 1 '' 'Not logged in. Run codex login.'
run_preflight
if [ "$RC" -eq 3 ] && printf '%s' "$OUT" | grep -qi 'not logged in'; then
  ok "non-zero status reports logged out, exit 3"
else
  bad "non-zero status reports logged out, exit 3" "rc=$RC · $OUT"
fi

# ---------------------------------------------- 3. cannot determine
printf '\n%s3. an unreachable keyring is NOT reported as a logout%s\n' "$B" "$N"
stub_codex 1 '' 'Error checking login status: failed to load CLI auth from keyring: Platform secure storage failure: zbus error: I/O error: Operation not permitted (os error 1)'
run_preflight
if [ "$RC" -ne 3 ]; then
  bad "keyring failure exits 3 (reviewer unavailable)" "rc=$RC · $OUT"
elif printf '%s' "$OUT" | grep -qi 'cannot determine'; then
  ok "keyring failure is reported as 'cannot determine', not as logged out"
else
  bad "keyring failure is reported as 'cannot determine', not as logged out" \
      "it said: $OUT"
fi
if printf '%s' "$OUT" | grep -qi 'sandbox'; then
  ok "the message names the sandbox as the likely cause"
else
  bad "the message names the sandbox as the likely cause" "it said: $OUT"
fi
if printf '%s' "$OUT" | grep -qi 'do not create'; then
  ok "the message explicitly warns against creating auth.json as a workaround"
else
  bad "the message explicitly warns against creating auth.json as a workaround" \
      "it said: $OUT"
fi

# ---------------------------------------------- 4. timeout
printf '\n%s4. a hung check is not a logout either%s\n' "$B" "$N"
printf '#!/bin/sh\nif [ "$1" = "login" ]; then exit 124; fi\nexit 0\n' > "$BIN/codex"
chmod +x "$BIN/codex"
run_preflight
if [ "$RC" -eq 3 ] && printf '%s' "$OUT" | grep -qi 'timed out\|cannot determine'; then
  ok "a timeout is reported as a timeout"
else
  bad "a timeout is reported as a timeout" "rc=$RC · $OUT"
fi

# ---------------------------------------------- 5. auth.json still refused
printf '\n%s5. ~/.codex/auth.json is refused ahead of everything else%s\n' "$B" "$N"
mkdir -p "$FAKEHOME/.codex"
printf '{"OPENAI_API_KEY":"redacted-not-a-real-key"}\n' > "$FAKEHOME/.codex/auth.json"
stub_codex 0 'Logged in' ''
run_preflight
if [ "$RC" -eq 3 ] && printf '%s' "$OUT" | grep -q 'auth.json'; then
  ok "auth.json is refused even when the login check would have succeeded"
else
  bad "auth.json is refused even when the login check would have succeeded" "rc=$RC · $OUT"
fi
rm -f "$FAKEHOME/.codex/auth.json"

# ---------------------------------------------- 6. source-level guarantee
printf '\n%s6. the source does not grep the status output%s\n' "$B" "$N"
# Comment lines are excluded: the file documents the broken shape on
# purpose, and a test that cannot tell an explanation from an implementation
# would forbid writing the explanation down.
offenders="$(grep -n 'codex login status' "$REVIEW" | grep -v '^[0-9]*:[[:space:]]*#' | grep 'grep')"
if [ -n "$offenders" ]; then
  bad "no executable line pipes 'codex login status' into grep" "$offenders"
else
  ok "no executable line pipes 'codex login status' into grep"
fi

# bin/host-check asks the same question from outside the sandbox, so it is held
# to the same rule. A reporting tool that decides on wording raises a false
# alarm on the next release note, which is how a verification tool teaches
# people to ignore it.
HOSTCHECK="$AI_DEV_HOME/bin/host-check"
if [ ! -r "$HOSTCHECK" ]; then
  bad "bin/host-check decides login state by exit status too" "$HOSTCHECK missing"
else
  hc_offenders="$(grep -n 'codex login status' "$HOSTCHECK" | grep -v '^[0-9]*:[[:space:]]*#' | grep 'grep')"
  if [ -n "$hc_offenders" ]; then
    bad "bin/host-check decides login state by exit status too" "$hc_offenders"
  elif ! grep -q 'rc=\$?' "$HOSTCHECK"; then
    bad "bin/host-check decides login state by exit status too" \
        "it never captures an exit status after codex login status"
  else
    ok "bin/host-check decides login state by exit status too"
  fi
fi

printf '\n'
if [ "$FAIL" -eq 0 ]; then printf '%s%d passed%s\n' "$G" "$PASS" "$N"; exit 0; fi
printf '%s%d passed, %d failed%s\n' "$R" "$PASS" "$FAIL" "$N"; exit 1
