"""Ollama backend — the generic local reviewer door.

Not Qwen-specific: the model is configuration, and nothing here knows one
model family from another. Defaults to the loopback endpoint Ollama binds
to out of the box. This adapter never binds any socket, never exposes
Ollama, and refuses a non-loopback endpoint at construction — before any
request — because "local review stays local" is the whole point.

Failure modes are distinct and typed: daemon unreachable is
ReviewerUnavailable, a missing model is ModelUnavailable, prose where JSON
was required is MalformedResponse. None of them fall back to Codex or any
cloud service — there is no such code path.
"""

import time

from .. import net
from ..errors import ConfigError, MalformedResponse, ModelUnavailable
from ..prompt import build_review_prompt
from ..result import ReviewMetrics, ReviewResult, parse_json_output, validate_review_output
from . import ReviewerBackend

DEFAULT_ENDPOINT = "http://127.0.0.1:11434"
DEFAULT_TIMEOUT = 300

LOCAL_COST_STATEMENT = "no external model API charge (local compute time is not free)"


class OllamaReviewer(ReviewerBackend):
    name = "ollama"
    external_service_required = False

    def __init__(self, model, endpoint=DEFAULT_ENDPOINT, timeout=DEFAULT_TIMEOUT,
                 opener=None):
        if not model:
            raise ConfigError("ollama reviewer needs a configured model")
        net.require_local(endpoint)
        self.model = model
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.opener = opener  # tests only

    @classmethod
    def from_config(cls, config):
        return cls(
            model=config.get("model"),
            endpoint=config.get("endpoint", DEFAULT_ENDPOINT),
            timeout=config.get("timeout", DEFAULT_TIMEOUT),
            opener=config.get("_opener"),
        )

    def _post(self, path, payload):
        return net.post_json(self.endpoint + path, payload, self.timeout,
                             opener=self.opener)

    def preflight(self):
        try:
            status, body = self._post("/api/show", {"model": self.model})
        except Exception as exc:  # preflight never raises
            return {"ok": False, "detail": f"{type(exc).__name__}: {exc}"}
        if status == 200:
            return {"ok": True, "detail": f"model '{self.model}' installed"}
        error = body.get("error", "") if isinstance(body, dict) else ""
        if status == 404 or "not found" in str(error):
            return {"ok": False,
                    "detail": f"model '{self.model}' is not installed "
                              "(pull it explicitly; this reviewer never downloads models)"}
        return {"ok": False, "detail": f"unexpected status {status}: {str(error)[:200]}"}

    def review_diff(self, diff_text, context=None):
        prompt = build_review_prompt(diff_text, context)
        payload = {"model": self.model, "prompt": prompt,
                   "stream": False, "format": "json"}
        started = time.monotonic()
        status, body = self._post("/api/generate", payload)
        latency = round(time.monotonic() - started, 3)
        if not isinstance(body, dict):
            raise MalformedResponse(f"ollama returned non-object: {str(body)[:200]!r}")
        if status != 200 or "error" in body:
            error = str(body.get("error", f"status {status}"))
            if "not found" in error:
                raise ModelUnavailable(
                    f"model '{self.model}' is not installed in Ollama "
                    "(pull it explicitly; this reviewer never downloads models)")
            raise MalformedResponse(f"ollama error: {error[:300]}")
        text = body.get("response")
        if not isinstance(text, str):
            raise MalformedResponse("ollama response missing 'response' field")
        verdict, findings = validate_review_output(parse_json_output(text))
        total_duration = body.get("total_duration")
        metrics = ReviewMetrics(
            backend=self.name, model=self.model, latency_seconds=latency,
            calls=1,
            input_tokens=body.get("prompt_eval_count"),
            output_tokens=body.get("eval_count"),
            # total_duration is nanoseconds of end-to-end model work — the
            # closest honest stand-in for on-device execution time.
            local_execution_seconds=round(total_duration / 1e9, 3)
            if isinstance(total_duration, (int, float)) else None,
            external_service_required=False,
            external_cost=LOCAL_COST_STATEMENT,
        )
        return ReviewResult(verdict, findings, metrics)
