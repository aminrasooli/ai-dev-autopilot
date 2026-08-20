"""Claude Code (Sonnet 5) backend — an isolated non-interactive judge.

Exists solely so the seeded-defect eval harness can compare Claude Code
against Codex and local models as an independent reviewer, under the exact
same prompt and output contract. It is not wired into bin/review: this is
an evaluation backend, not a new interactive review product surface.

`claude -p` is run in a disposable empty directory (no CLAUDE.md, no .git)
with a custom --system-prompt that REPLACES Claude Code's default one.
That matters: even with --tools "" disabling tool access, Claude Code's
default system prompt bakes in cwd, environment info and git status, which
would leak this repository and this machine into a call that is supposed
to see only the review prompt. --setting-sources "" additionally excludes
this machine's user-level CLAUDE.md and settings. None of this call uses
the current session's conversation — it is a fresh, stateless invocation.
"""

import json
import os
import shutil
import subprocess
import tempfile
import time

from ..errors import MalformedResponse, ReviewerUnavailable
from ..prompt import build_review_prompt
from ..result import ReviewMetrics, ReviewResult, parse_json_output, validate_review_output
from . import ReviewerBackend

DEFAULT_TIMEOUT = 600

# Replaces Claude Code's default system prompt entirely, not appended to
# it — that is what strips the cwd/env/git-status sections the default one
# otherwise injects regardless of tool access.
ISOLATION_SYSTEM_PROMPT = (
    "You are an independent code reviewer. Follow only the instructions in "
    "the user message; you have no other context, tools or history."
)

# Unlike Codex, this backend legitimately needs its own Anthropic
# credentials to authenticate — those are not stripped. Everything else
# unrelated to this call is, on the same principle as the Codex backend.
CREDENTIAL_ENV_VARS = (
    "OPENAI_API_KEY", "CODEX_API_KEY",
    "GITHUB_TOKEN", "GH_TOKEN", "NPM_TOKEN",
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
)


def _default_runner(model, prompt, timeout):
    """Run `claude -p` isolated from this repository and this session.

    Returns (returncode, stdout_text) — stdout is the --output-format json
    envelope, parsed by the caller.
    """
    cmd = [
        "claude", "-p", prompt,
        "--model", model,
        "--output-format", "json",
        "--tools", "",
        "--system-prompt", ISOLATION_SYSTEM_PROMPT,
        "--setting-sources", "",
    ]
    env = {k: v for k, v in os.environ.items() if k not in CREDENTIAL_ENV_VARS}
    with tempfile.TemporaryDirectory(prefix="aidev-reviewer-claude.") as work:
        try:
            proc = subprocess.run(cmd, cwd=work, capture_output=True, text=True,
                                  timeout=timeout, env=env)
        except subprocess.TimeoutExpired:
            return 124, ""
        return proc.returncode, proc.stdout


class ClaudeCodeReviewer(ReviewerBackend):
    name = "claude"
    external_service_required = True

    def __init__(self, model="claude-sonnet-5", timeout=DEFAULT_TIMEOUT, runner=None):
        self.model = model
        self.timeout = timeout
        self.runner = runner or _default_runner

    @classmethod
    def from_config(cls, config):
        return cls(
            model=config.get("model", "claude-sonnet-5"),
            timeout=config.get("timeout", DEFAULT_TIMEOUT),
            runner=config.get("_runner"),
        )

    def preflight(self):
        if shutil.which("claude") is None:
            return {"ok": False, "detail": "claude CLI is not installed"}
        return {"ok": True, "detail": "claude CLI present"}

    def review_diff(self, diff_text, context=None):
        prompt = build_review_prompt(diff_text, context)
        started = time.monotonic()
        returncode, stdout = self.runner(self.model, prompt, self.timeout)
        latency = round(time.monotonic() - started, 3)
        if returncode in (124, 137):
            raise ReviewerUnavailable(f"claude reviewer timed out after {self.timeout}s")
        if returncode != 0 or not stdout.strip():
            raise MalformedResponse(f"claude produced no output (exit {returncode})")
        try:
            envelope = json.loads(stdout)
        except ValueError as exc:
            raise MalformedResponse(
                f"claude --output-format json did not return JSON: {stdout[:200]!r}") from exc
        if envelope.get("is_error"):
            raise ReviewerUnavailable(
                f"claude reviewer error: {str(envelope.get('result', envelope))[:300]}")
        text = envelope.get("result")
        if not isinstance(text, str):
            raise MalformedResponse("claude output envelope missing 'result' text")
        verdict, findings = validate_review_output(parse_json_output(text))
        usage = envelope.get("usage") or {}
        cost_usd = envelope.get("total_cost_usd")
        metrics = ReviewMetrics(
            backend=self.name, model=self.model, latency_seconds=latency,
            calls=1,
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
            external_service_required=True,
            # Directly measured by the tool itself, not estimated — the one
            # backend where a dollar figure is honest rather than invented.
            external_cost=(f"${cost_usd:.6f} (measured, claude --output-format json)"
                           if isinstance(cost_usd, (int, float)) else None),
        )
        return ReviewResult(verdict, findings, metrics)
