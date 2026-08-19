"""Pluggable independent reviewer — experimental.

The autonomous Claude Code loop is the product; the independent reviewer is
a second opinion that can now be swapped by configuration:

    reviewer:  codex (default)  |  ollama (local model)

One concept lives here: a REVIEWER BACKEND takes a unified diff, returns a
structured ReviewResult, and reports what its run honestly cost. Codex
remains the default and its existing containment (`bin/codex-review`) is
unchanged. The Ollama backend is the generic local-model door — Qwen may be
the first model tested through it, but model identity is configuration.

Privacy claim, stated precisely: local review stays local. The review stage
with the ollama backend speaks only to a loopback endpoint and has no
fallback to any remote service. This does NOT make the whole workflow
local — Claude Code still communicates with Anthropic when it does the
building.

The larger team-of-seats architecture is recorded in docs/NORTH_STAR.md and
deliberately NOT implemented.
"""

__version__ = "0.1.0"
