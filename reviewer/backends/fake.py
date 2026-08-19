"""Deterministic fake backend.

What CI runs against: no GPU, no Ollama, no Codex login, no network, no
paid API. Scripted replies are keyed by a substring of the diff under
review and pass through the SAME parse-and-validate pipeline as real model
output, so a test that scripts prose proves the malformed-output path and a
test that scripts JSON proves the happy path — the fake cannot skip the
contract it exists to test.
"""

import json
import time

from ..errors import MalformedResponse, ReviewerUnavailable
from ..result import ReviewMetrics, ReviewResult, parse_json_output, validate_review_output
from . import ReviewerBackend


class FakeReviewer(ReviewerBackend):
    name = "fake"
    external_service_required = False

    def __init__(self, script=None, model="fake-model", healthy=True,
                 latency_seconds=0.0):
        # script: {diff-substring: reply}. A reply may be a dict (encoded
        # to JSON, the normal case) or a raw string (fed to the parser
        # as-is, for malformed-output tests).
        self.script = script or {}
        self.model = model
        self.healthy = healthy
        self.latency_seconds = latency_seconds
        self.reviewed = []  # diffs seen, for assertions

    @classmethod
    def from_config(cls, config):
        return cls(
            script=config.get("script"),
            model=config.get("model", "fake-model"),
            healthy=config.get("healthy", True),
            latency_seconds=config.get("latency_seconds", 0.0),
        )

    def preflight(self):
        if not self.healthy:
            return {"ok": False, "detail": "fake reviewer configured unhealthy"}
        return {"ok": True, "detail": "fake reviewer ready"}

    def _reply_for(self, diff_text):
        for marker, reply in self.script.items():
            if marker != "default" and marker in diff_text:
                return reply
        if "default" in self.script:
            return self.script["default"]
        raise MalformedResponse("fake reviewer has no scripted reply for this diff")

    def review_diff(self, diff_text, context=None):
        self.reviewed.append(diff_text)
        if not self.healthy:
            raise ReviewerUnavailable("fake reviewer configured unhealthy")
        if self.latency_seconds:
            time.sleep(self.latency_seconds)
        reply = self._reply_for(diff_text)
        text = reply if isinstance(reply, str) else json.dumps(reply)
        verdict, findings = validate_review_output(parse_json_output(text))
        metrics = ReviewMetrics(
            backend=self.name, model=self.model,
            latency_seconds=self.latency_seconds, calls=1,
            input_tokens=len(diff_text.split()), output_tokens=len(text.split()),
            external_service_required=False,
            external_cost="none (deterministic fake)",
        )
        return ReviewResult(verdict, findings, metrics)
