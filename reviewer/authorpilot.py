"""Non-Claude authorship pilot (M4-B, docs/M4_DESIGN_BRIEF.md §B).

Prompts a local Ollama model to AUTHOR a candidate benchmark case (invent
a scenario, a diff, and a defect/clean judgment) — the inverse of the
existing `reviewer.backends.ollama` adapter, which asks a model to
REVIEW a diff someone else wrote. Reuses the same loopback-only
transport (`reviewer.net`) and the same "local stays local" guarantee.

Every attempt is recorded, whether or not it produces something usable:
exact model, exact prompt, a timestamp, the raw output, and — only when
the raw output parses as JSON and validates against the real case
schema without modification — a ready-to-review case proposal in the
shape `eval/proposals/` expects. A malformed or schema-invalid attempt
is recorded as REJECTED, never silently repaired: fixing a model's
output and still labeling it that model's authorship is exactly the
failure mode this pipeline exists to prevent
(docs/ROADMAP.md §9 failure mode 3).

Nothing here writes into `eval/proposals/` or `eval/cases*` — it writes
attempt records to a pilot output directory, for a human to read and, if
they choose, hand-copy the `proposal` field of a READY attempt into
`eval/proposals/cases/`. See docs/M4_DESIGN_BRIEF.md §B.

CLI:
    python3 -m reviewer.authorpilot run \
        --model qwen3.6:27b --author-family qwen \
        --language python --category resource-leak \
        --out-dir eval/authorship-pilot/attempts
Exit codes: 0 attempt recorded (ready or rejected — both are a
successful pilot run) · 1 could not reach the model at all.
"""

import argparse
import json
import os
import re
import sys
import time

from . import net
from .corpus import AUTHOR_FAMILIES, LANGUAGES, validate_case
from .errors import MalformedResponse, ReviewerUnavailable
from .propose import validate_proposal

DEFAULT_ENDPOINT = "http://127.0.0.1:11434"
DEFAULT_TIMEOUT = 300

AUTHORING_PROMPT_TEMPLATE = """You are authoring ONE new test case for an \
independent code-review benchmark. Invent a small, realistic, self-contained \
diff in {language} — either one with exactly one seeded defect, or a clean \
diff with no defect at all. If you author a defective case, prefer a defect \
in the "{category}" category if you can do so naturally; do not force it if \
it doesn't fit your scenario.

Reply with ONLY a single JSON object, no prose before or after, matching \
exactly this shape:
{{
  "title": "one short human-readable line",
  "language": "{language}",
  "affected_files": ["path/to/file.ext"],
  "diff": ["--- a/path/to/file.ext", "+++ b/path/to/file.ext", "@@ ... @@", "-old line", "+new line"],
  "defect": true or false,
  "category": "one of: {categories}" ,
  "severity": ["low"|"medium"|"high"|"critical", "low"|"medium"|"high"|"critical"],
  "explanation": "one sentence: what the defect is and why it matters, or why the diff is clean"
}}

If defect is false, omit "category" and "severity" entirely. The diff array \
must be actual unified-diff lines (paths, hunk header, +/- lines) — not a \
prose description of a diff.
"""


def build_authoring_prompt(language, category_hint, categories):
    if language not in LANGUAGES:
        raise ValueError(f"language {language!r} not in {LANGUAGES}")
    return AUTHORING_PROMPT_TEMPLATE.format(
        language=language, category=category_hint,
        categories=", ".join(categories))


def call_model(model, prompt, endpoint=DEFAULT_ENDPOINT, timeout=DEFAULT_TIMEOUT,
                opener=None):
    """POST the authoring prompt to Ollama. Returns the raw response text.
    Raises ReviewerUnavailable/MalformedResponse — never falls back to any
    other backend or endpoint (same discipline as reviewer.backends.ollama)."""
    net.require_local(endpoint)
    payload = {"model": model, "prompt": prompt, "stream": False,
              "format": "json", "think": False}
    status, body = net.post_json(endpoint.rstrip("/") + "/api/generate",
                                 payload, timeout, opener=opener)
    if not isinstance(body, dict):
        raise MalformedResponse(f"ollama returned non-object: {str(body)[:200]!r}")
    if status != 200 or "error" in body:
        raise MalformedResponse(f"ollama error: {str(body.get('error', status))[:300]}")
    text = body.get("response")
    if not isinstance(text, str) or not text.strip():
        raise MalformedResponse("ollama response missing non-empty 'response' field")
    return text


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_pilot_output(raw_text):
    """Best-effort extraction of a JSON object from a model's raw reply.
    Tries the whole text first, then the largest {...} span — never
    modifies field values, only locates the JSON."""
    try:
        return json.loads(raw_text)
    except ValueError:
        pass
    match = _JSON_OBJECT_RE.search(raw_text)
    if not match:
        raise ValueError("no JSON object found in model output")
    return json.loads(match.group(0))


def _case_from_pilot_json(obj, case_id, language):
    """Map the pilot's authoring-prompt JSON shape onto the real case
    schema. Structural translation only (wrapping fields into the
    required envelope) — never invents or corrects content the model
    didn't provide."""
    if not isinstance(obj, dict):
        raise ValueError("model output is not a JSON object")
    defect = obj.get("defect")
    if not isinstance(defect, bool):
        raise ValueError("model output missing boolean 'defect'")
    ground_truth = {"defect": defect,
                    "explanation": obj.get("explanation", "")}
    if defect:
        ground_truth["category"] = obj.get("category")
        ground_truth["severity"] = obj.get("severity")
    return {
        "benchmark_version": 2,
        "id": case_id,
        "title": obj.get("title", ""),
        "language": language,
        "status": "pilot",
        "diff": obj.get("diff"),
        "affected_files": obj.get("affected_files"),
        "ground_truth": ground_truth,
        "difficulty": "moderate" if defect else None,
    }


def run_pilot(model, author_family, language, category_hint, case_id,
             endpoint=DEFAULT_ENDPOINT, timeout=DEFAULT_TIMEOUT, opener=None,
             now=None, rationale=None):
    """Run one full pilot attempt and return an attempt record — always,
    whether the attempt succeeds or fails. Never raises for a bad model
    output (that's a REJECTED record); only raises if the model can't be
    reached at all (ReviewerUnavailable) or returns garbage HTTP
    (MalformedResponse) — those are infrastructure failures, not pilot
    outcomes, and the caller decides what to do with them."""
    if author_family not in AUTHOR_FAMILIES:
        raise ValueError(f"author_family {author_family!r} not in {AUTHOR_FAMILIES}")
    from .result import CATEGORIES
    prompt = build_authoring_prompt(language, category_hint, CATEGORIES)
    generated_at = now() if now else time.time()
    raw_text = call_model(model, prompt, endpoint=endpoint, timeout=timeout,
                          opener=opener)

    record = {
        "attempt_id": case_id,
        "model": model,
        "author_family": author_family,
        "language": language,
        "category_hint": category_hint,
        "prompt": prompt,
        "generated_at": generated_at,
        "raw_output": raw_text,
        "claude_touched": False,
        "status": None,
        "validation_errors": [],
        "proposal": None,
    }

    try:
        parsed = parse_pilot_output(raw_text)
        case = _case_from_pilot_json(parsed, case_id, language)
        case["provenance"] = {
            "type": "seeded-synthetic",
            "author_family": author_family,
            "author_model": model,
            # The authoring prompt never asks for `difficulty`, but the
            # schema requires one on defective cases, so the harness
            # supplies a neutral default. That is a judgment the model
            # did not make, inside a case attributed to it — say so in
            # the record rather than let it pass as the model's
            # (docs/M4_DESIGN_BRIEF.md §B).
            "provenance_notes": (
                f"Authored by {model} via reviewer.authorpilot. Defect "
                "content, category, severity and explanation are the "
                "model's own, unmodified. `difficulty` was not requested "
                "in the authoring prompt and was defaulted by the pilot "
                "harness, not judged by the model; a human must set it "
                "before this case is ever admitted."
            ),
        }
        if isinstance(case.get("diff"), list):
            case["diff"] = [str(line) for line in case["diff"]]
        if case.get("difficulty") is None:
            case.pop("difficulty", None)
        proposal = {
            "proposal_id": case_id,
            "author_family": author_family,
            "generator": model,
            "status": "proposed",
            "case": case,
            "rationale": rationale or (
                f"M4 non-Claude authorship pilot: {model} authoring a "
                f"{language} case, category hint {category_hint!r}"),
        }
        errors, warnings = validate_proposal(proposal)
        if errors:
            record["status"] = "rejected-invalid-schema"
            record["validation_errors"] = errors
        else:
            record["status"] = "ready"
            record["proposal"] = proposal
    except (ValueError, KeyError) as exc:
        record["status"] = "rejected-malformed"
        record["validation_errors"] = [f"{type(exc).__name__}: {exc}"]
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="reviewer-authorpilot",
        description="Non-Claude authorship pilot: prompt a local Ollama "
                    "model to author one candidate benchmark case.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("run", help="run one pilot attempt")
    p1.add_argument("--model", required=True)
    p1.add_argument("--author-family", required=True, choices=AUTHOR_FAMILIES)
    p1.add_argument("--language", required=True, choices=LANGUAGES)
    p1.add_argument("--category", required=True,
                    help="category hint, e.g. resource-leak")
    p1.add_argument("--out-dir", required=True)
    p1.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    p1.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = parser.parse_args(argv)

    os.makedirs(args.out_dir, exist_ok=True)
    case_id = f"{args.author_family}-pilot-{args.language}-{int(time.time())}"
    try:
        record = run_pilot(args.model, args.author_family, args.language,
                           args.category, case_id, endpoint=args.endpoint,
                           timeout=args.timeout)
    except (ReviewerUnavailable, MalformedResponse) as exc:
        print(f"error: could not reach model {args.model!r} at "
              f"{args.endpoint}: {exc}", file=sys.stderr)
        return 1

    out_path = os.path.join(args.out_dir, case_id + ".json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
    print(f"{record['status']}: {out_path}")
    if record["validation_errors"]:
        for e in record["validation_errors"]:
            print(f"  {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
