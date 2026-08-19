"""The structured review result, and the deterministic parsing that
produces it.

Every backend returns the same shape, so the eval harness and the humans
reading a review compare like with like. Malformed model output raises
MalformedResponse and the run fails safely — nothing here guesses at what a
model probably meant.
"""

import json
import re

from .errors import MalformedResponse

SEVERITIES = ("low", "medium", "high", "critical")

# The fixed finding vocabulary. Both backends receive it verbatim in the
# prompt, which is what makes category correctness measurable rather than a
# judgment call about synonyms.
CATEGORIES = (
    "logic-error",
    "missing-validation",
    "shell-quoting",
    "command-injection",
    "path-traversal",
    "sensitive-logging",
    "insecure-network",
    "dependency-risk",
    "test-gap",
    "misleading-test",
    "destructive-operation",
    "permission-widening",
    "secret-exposure",
    "other",
)

VERDICTS = ("approve", "changes_required")


def parse_json_output(text):
    """Extract one JSON object from model output, deterministically.

    Accepts the object bare or inside a ```json fence — nothing looser.
    Prose, several objects, or truncated JSON raise MalformedResponse.
    """
    candidate = text.strip()
    fence = re.match(r"^```(?:json)?\s*\n(.*?)\n?\s*```\s*$", candidate, re.DOTALL)
    if fence:
        candidate = fence.group(1).strip()
    try:
        obj = json.loads(candidate)
    except ValueError as exc:
        raise MalformedResponse(
            f"reviewer output is not a single JSON value: {candidate[:200]!r}") from exc
    if not isinstance(obj, dict):
        raise MalformedResponse(
            f"reviewer output is JSON but not an object: {candidate[:200]!r}")
    return obj


def validate_review_output(obj):
    """Validate the model's {"verdict", "findings"} object strictly.

    Returns (verdict, findings) with findings normalized to
    {"category", "severity", "file", "note"}. Any deviation from the
    documented shape — wrong types, off-vocabulary category or severity —
    is MalformedResponse, because a reviewer that cannot follow its output
    contract is not producing results the scoring can honestly use.
    """
    errors = []
    verdict = obj.get("verdict")
    if verdict not in VERDICTS:
        errors.append(f"verdict must be one of {VERDICTS}, got {verdict!r}")
    raw_findings = obj.get("findings")
    findings = []
    if not isinstance(raw_findings, list):
        errors.append(f"findings must be a list, got {type(raw_findings).__name__}")
        raw_findings = []
    for i, f in enumerate(raw_findings):
        if not isinstance(f, dict):
            errors.append(f"findings[{i}]: expected object")
            continue
        category = f.get("category")
        severity = f.get("severity")
        note = f.get("note")
        file_ = f.get("file")
        if category not in CATEGORIES:
            errors.append(f"findings[{i}].category {category!r} is not in the vocabulary")
        if severity not in SEVERITIES:
            errors.append(f"findings[{i}].severity {severity!r} is not in {SEVERITIES}")
        if not isinstance(note, str) or not note.strip():
            errors.append(f"findings[{i}].note must be a non-empty string")
        if file_ is not None and not isinstance(file_, str):
            errors.append(f"findings[{i}].file must be a string or null")
        findings.append({"category": category, "severity": severity,
                         "file": file_, "note": note})
    unknown = set(obj) - {"verdict", "findings"}
    if unknown:
        errors.append(f"unknown fields: {sorted(unknown)}")
    if errors:
        raise MalformedResponse("review output failed validation: " + "; ".join(errors))
    return verdict, findings


class ReviewMetrics:
    """What one review run honestly cost. Unknown stays None — never zero,
    never invented."""

    def __init__(self, backend, model, latency_seconds, calls=1,
                 input_tokens=None, output_tokens=None,
                 local_execution_seconds=None,
                 external_service_required=False, external_cost=None):
        self.backend = backend
        self.model = model
        self.latency_seconds = latency_seconds
        self.calls = calls
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.local_execution_seconds = local_execution_seconds
        self.external_service_required = external_service_required
        # A human-readable statement of the money question, e.g.
        # "not directly metered (subscription authentication)" for Codex or
        # "no external model API charge (local compute time is not free)"
        # for a local model. A dollar figure appears only when reliable
        # pricing and usage both exist — which today is never.
        self.external_cost = external_cost or "unknown"

    def to_dict(self):
        return {
            "backend": self.backend,
            "model": self.model,
            "latency_seconds": self.latency_seconds,
            "calls": self.calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "local_execution_seconds": self.local_execution_seconds,
            "external_service_required": self.external_service_required,
            "external_cost": self.external_cost,
        }


class ReviewResult:
    def __init__(self, verdict, findings, metrics):
        self.verdict = verdict
        self.findings = findings
        self.metrics = metrics

    def to_dict(self):
        return {
            "verdict": self.verdict,
            "findings": self.findings,
            "metrics": self.metrics.to_dict(),
        }

    def render_markdown(self):
        """The human-facing review, mirroring the existing Codex review
        shape: findings first, one VERDICT line last."""
        lines = ["# Independent review", ""]
        if not self.findings:
            lines.append("No findings. The change looks sound to this reviewer.")
        for f in self.findings:
            where = f" `{f['file']}`" if f.get("file") else ""
            lines.append(f"- **{f['severity']}** [{f['category']}]{where}: {f['note']}")
        lines += ["",
                  "VERDICT: " + ("APPROVE" if self.verdict == "approve"
                                 else "CHANGES REQUIRED")]
        return "\n".join(lines) + "\n"
