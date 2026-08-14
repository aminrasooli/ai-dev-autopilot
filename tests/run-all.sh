#!/usr/bin/env bash
# Run every AI-DEV contract test. Nothing here performs a destructive action.
set -uo pipefail
# Default to the repository this script lives in, so a fresh clone tests
# itself rather than whatever happens to be installed at ~/.ai-dev. An
# explicit AI_DEV_HOME still wins.
AI_DEV_HOME="${AI_DEV_HOME:-$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
# Exported so every child — the suites and bin/doctor — resolves the same hub.
# Without this each one re-derives its own default and a run could silently
# straddle two trees.
export AI_DEV_HOME
cd "$AI_DEV_HOME" || { printf 'run-all: cannot enter %s\n' "$AI_DEV_HOME" >&2; exit 1; }

rc=0
sync_pending=0
for t in tests/*.test.sh; do
  printf '\n=== %s ===\n' "$t"
  bash "$t"; s=$?
  case $s in
    0) ;;
    3) printf '  (skipped: dependency unavailable)\n' ;;
    # 2 = the contract holds where this repository can enforce it, but a control
    # that lives outside the repository is not deployed yet. That is a real gap
    # and must not read as a pass, but it is also not the same thing as a
    # violated contract: the fix is `make sync`, not a code change. Kept
    # separate so a stale deployment cannot hide an actual regression.
    2) sync_pending=1; printf '  (contract holds; a control is awaiting `make sync`)\n' ;;
    *) rc=1 ;;
  esac
done

printf '\n=== bin/doctor ===\n'
# Doctor uses the same three-way answer the suites do, for the same reason: most
# of what it inspects lives outside this repository and does not exist until
# `make sync` has run. 3 = nothing here is violated, some controls are simply
# not installed on this machine — the state of a fresh clone, a CI runner, and
# anyone's first five minutes. Folding that into 1 would make "CONTRACT TESTS
# FAILED" the normal first impression of a project whose whole claim is that its
# contracts are checkable.
bash bin/doctor --quick; s=$?
case $s in
  0) ;;
  3) sync_pending=1 ;;
  *) rc=1 ;;
esac

printf '\n'
if [ $rc != 0 ]; then
  printf 'CONTRACT TESTS FAILED\n'
elif [ $sync_pending = 1 ]; then
  printf 'CONTRACT TESTS PASSED — but run `make -C %s sync`:\n' "$AI_DEV_HOME"
  printf 'a control is defined in the hub but is not deployed on this machine.\n'
else
  printf 'ALL CONTRACT TESTS PASSED\n'
fi
exit $rc
