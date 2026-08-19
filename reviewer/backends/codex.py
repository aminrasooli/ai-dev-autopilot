"""Codex backend.

For interactive product use, `bin/review` execs the existing
`bin/codex-review` unchanged — this class does not replace it, so existing
users see identical behaviour. This class exists so the eval harness can
drive Codex with EXACTLY the same prompt and output contract as every
other backend.

The containment mirrors bin/codex-review line for line, and the two are
kept in step deliberately (the permission broker carries a third copy of
the same inline policy — that is house style here, because an inline
policy is one a project-local .codex/config.toml cannot redefine):

  * whole permission profile inline, read-only, network disabled
  * --ephemeral, --ignore-rules, --strict-config, --skip-git-repo-check
  * ChatGPT keyring auth only; API-key variables removed from the
    environment; ~/.codex/auth.json refused
  * bounded wall-clock timeout

Cost: Codex here authenticates through a subscription, so a per-call
dollar figure is not available and is reported as "not directly metered" —
never invented.
"""

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

NOT_METERED = "not directly metered (subscription authentication)"

CREDENTIAL_ENV_VARS = (
    "OPENAI_API_KEY", "CODEX_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
    "GITHUB_TOKEN", "GH_TOKEN", "NPM_TOKEN", "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
)

# Read-only everywhere it can see, and it can see almost nothing: the
# minimal runtime set, the npm global tree the Codex sandbox helper
# re-execs from, and the empty scratch directory the run is rooted in.
FS_POLICY = '{ ":minimal" = "read", "~/.npm-global" = "read", ":workspace_roots" = { "." = "read" } }'


def _default_runner(cmd, stdin_text, timeout, env):
    """Run codex exec; returns (returncode, last_message_text)."""
    with tempfile.TemporaryDirectory(prefix="aidev-reviewer-codex.") as work:
        answer = os.path.join(work, "answer.md")
        full_cmd = cmd + ["-C", work, "--output-last-message", answer, "-"]
        try:
            proc = subprocess.run(
                full_cmd, input=stdin_text, capture_output=True, text=True,
                timeout=timeout, env=env)
        except subprocess.TimeoutExpired:
            return 124, ""
        text = ""
        if os.path.exists(answer):
            with open(answer, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        return proc.returncode, text


class CodexReviewer(ReviewerBackend):
    name = "codex"
    external_service_required = True

    def __init__(self, model="codex-default", timeout=DEFAULT_TIMEOUT, runner=None):
        # Codex picks its own model from the user's Codex configuration;
        # "codex-default" records that this runtime did not choose it.
        self.model = model
        self.timeout = timeout
        self.runner = runner or _default_runner

    @classmethod
    def from_config(cls, config):
        return cls(
            model=config.get("model", "codex-default"),
            timeout=config.get("timeout", DEFAULT_TIMEOUT),
            runner=config.get("_runner"),
        )

    def preflight(self):
        if shutil.which("codex") is None:
            return {"ok": False, "detail": "codex CLI is not installed"}
        if os.path.exists(os.path.expanduser("~/.codex/auth.json")):
            return {"ok": False,
                    "detail": "~/.codex/auth.json exists; Codex must authenticate "
                              "through the OS keyring (remove it and run: codex login)"}
        try:
            proc = subprocess.run(["codex", "login", "status"],
                                  capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            return {"ok": False, "detail": "codex login status timed out after 30s"}
        if proc.returncode == 0:
            return {"ok": True, "detail": "codex CLI present and logged in"}
        stderr = (proc.stderr or proc.stdout).strip().splitlines()
        first = stderr[0] if stderr else f"exit {proc.returncode}"
        # The keyring being unreachable (normal inside the Claude sandbox)
        # is a different answer from "logged out" — same distinction
        # bin/codex-review draws.
        for marker in ("keyring", "secure storage", "zbus", "D-Bus", "dbus",
                       "Operation not permitted"):
            if marker in first:
                return {"ok": False,
                        "detail": f"cannot determine Codex login state ({first}); "
                                  "run from a normal shell, not the sandbox"}
        return {"ok": False, "detail": f"Codex is not logged in ({first})"}

    def _codex_cmd(self):
        return [
            "codex", "exec",
            "--strict-config", "--ephemeral", "--ignore-rules",
            "--skip-git-repo-check",
            "-c", 'permissions.aidevrun.description="AI-DEV ephemeral read-only reviewer"',
            "-c", f"permissions.aidevrun.filesystem={FS_POLICY}",
            "-c", "permissions.aidevrun.network={ enabled = false }",
            "-c", 'default_permissions="aidevrun"',
            "-c", 'approval_policy="never"',
            "-c", 'history.persistence="none"',
        ]

    def review_diff(self, diff_text, context=None):
        check = self.preflight()
        if not check["ok"]:
            raise ReviewerUnavailable(check["detail"])
        prompt = build_review_prompt(diff_text, context)
        env = {k: v for k, v in os.environ.items() if k not in CREDENTIAL_ENV_VARS}
        started = time.monotonic()
        returncode, text = self.runner(self._codex_cmd(), prompt, self.timeout, env)
        latency = round(time.monotonic() - started, 3)
        if returncode in (124, 137):
            raise ReviewerUnavailable(f"codex reviewer timed out after {self.timeout}s")
        if not text.strip():
            raise MalformedResponse(
                f"codex produced no output (exit {returncode})")
        verdict, findings = validate_review_output(parse_json_output(text))
        metrics = ReviewMetrics(
            backend=self.name, model=self.model, latency_seconds=latency,
            calls=1,
            # Codex exec does not report token usage in this mode; unknown
            # stays unknown.
            input_tokens=None, output_tokens=None,
            external_service_required=True,
            external_cost=NOT_METERED,
        )
        return ReviewResult(verdict, findings, metrics)
