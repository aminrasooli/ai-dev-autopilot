#!/usr/bin/env bash
# AI-DEV regression test — the pluggable reviewer (reviewer/).
#
# A thin wrapper: the reviewer package's own logic is exercised by a
# deterministic Python unittest suite (reviewer/tests/test_reviewer.py), not
# reimplemented in bash. This script just runs it and translates the result
# into the same 0/1/3 contract every other suite here uses.
#
# Every case in that suite stubs the network (Ollama's HTTP door) and the
# subprocess (Codex's exec door) — no GPU, no Ollama daemon, no Codex login,
# no network access, no paid API.
#
# Exit codes: 0 all passed · 1 a contract was violated · 3 python3 missing

set -uo pipefail

AI_DEV_HOME="${AI_DEV_HOME:-$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"

command -v python3 >/dev/null 2>&1 \
  || { printf 'skip: python3 is required\n'; exit 3; }

cd "$AI_DEV_HOME" || exit 1
PYTHONPATH="$AI_DEV_HOME${PYTHONPATH:+:$PYTHONPATH}" \
  python3 -m unittest discover -s reviewer/tests -t "$AI_DEV_HOME" -v
exit $?
