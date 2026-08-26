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
shape `eval/proposals/` expects. A malformed attempt, a schema-invalid
attempt, or one authored in a different language than was asked for is
recorded as REJECTED, never silently repaired or relabeled: fixing a
model's output and still labeling it that model's authorship is exactly
the failure mode this pipeline exists to prevent
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
import ast
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

from . import net
from .corpus import AUTHOR_FAMILIES, LANGUAGES, validate_case
from .errors import MalformedResponse, ReviewerUnavailable
from .propose import validate_proposal

DEFAULT_ENDPOINT = "http://127.0.0.1:11434"
DEFAULT_TIMEOUT = 300

AUTHORING_PROMPT_TEMPLATE = """You are authoring ONE new test case for an \
independent code-review benchmark. Invent a small, realistic, self-contained \
piece of {language} code, then give it to us twice: BEFORE and AFTER a change. \
Either the change introduces exactly one defect, or it is a clean change with \
no defect at all. If you author a defective case, prefer a defect in the \
"{category}" category if you can do so naturally; do not force it if it \
doesn't fit your scenario.

Do NOT write a diff. Write the two complete versions of the file and we will \
compute the diff for you.

Reply with ONLY a single JSON object, no prose before or after, matching \
exactly this shape:
{{
  "title": "one short human-readable line",
  "language": "{language}",
  "file_path": "path/to/file.ext",
  "before": ["complete file contents BEFORE the change,", "one array element per line,", "no line numbers, no +/- markers"],
  "after": ["complete file contents AFTER the change,", "same file, one array element per line"],
  "defect": true or false,
  "category": "one of: {categories}" ,
  "severity": ["low", "high"],
  "explanation": "one sentence: what the defect is and why it matters, or why the change is clean"
}}

Rules that will cause your case to be REJECTED if broken:
- "before" and "after" must each be COMPLETE, syntactically valid {language} \
that would parse on its own. Not a fragment, not a hunk.
- "before" and "after" must actually differ. Identical versions are rejected.
- "severity" must be exactly two values [minimum, maximum] in that order, \
lowest first, each one of: low, medium, high, critical.
- If defect is false, omit "category" and "severity" entirely.
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


class NoOpChange(ValueError):
    """The model's BEFORE and AFTER are the same source.

    Its own outcome because it is a specific, recurring failure — the
    first pilot produced two attempts whose only `-`/`+` pair was
    byte-identical. A case with no behavioural change cannot carry a
    defect label either way, and no amount of downstream review would
    recover one.
    """


class SourceSyntaxError(ValueError):
    """Model-authored source does not parse.

    Rejected, never repaired. A benchmark case whose code does not parse
    measures whether a reviewer notices a syntax error, not whether it
    notices the seeded defect the ground truth claims.
    """


def normalize_source(value):
    """Accept the model's source as either a list of lines or one string.

    Purely mechanical: the case schema itself already accepts `diff` as
    "string or list, list-of-lines joins with \\n"
    (docs/BENCHMARK_METHODOLOGY.md §4), so accepting both shapes here
    follows an existing convention rather than inventing one. Returns
    text with a trailing newline, or None if the value is neither shape.
    """
    if isinstance(value, list):
        text = "\n".join(str(line) for line in value)
    elif isinstance(value, str):
        text = value
    else:
        return None
    if text and not text.endswith("\n"):
        text += "\n"
    return text


def check_python_syntax(source):
    """Return None if `source` parses, else a one-line reason."""
    try:
        ast.parse(source)
        return None
    except SyntaxError as exc:
        return f"{exc.msg} (line {exc.lineno})"


def check_javascript_syntax(source):
    """Return None if `source` parses under `node --check`, a reason if it
    does not, and None if node is unavailable (an absent checker must not
    read as a passing check — the caller records which languages were
    actually checked)."""
    node = shutil.which("node")
    if node is None:
        return None
    tmp = tempfile.NamedTemporaryFile(
        "w", suffix=".js", delete=False, encoding="utf-8")
    try:
        tmp.write(source)
        tmp.close()
        proc = subprocess.run([node, "--check", tmp.name],
                              capture_output=True, text=True, timeout=30)
        if proc.returncode == 0:
            return None
        for line in proc.stderr.splitlines():
            if "Error" in line:
                return line.strip()
        return "node --check rejected the source"
    except (OSError, subprocess.SubprocessError) as exc:
        return None if isinstance(exc, FileNotFoundError) else f"node --check failed: {exc}"
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


# Only languages with a deterministic checker available locally. A
# language absent here is authored unchecked and says so in the record;
# it is deliberately not treated as having passed.
SYNTAX_CHECKERS = {
    "python": check_python_syntax,
    "javascript": check_javascript_syntax,
}


def syntax_checker_available(language):
    if language == "javascript":
        return shutil.which("node") is not None
    return language in SYNTAX_CHECKERS


def build_unified_diff(before_text, after_text, file_path):
    """Deterministically serialize BEFORE/AFTER into unified-diff lines.

    This is the whole of what the harness took over from the model in
    pilot 2, and it is mechanical serialization, not authorship: every
    output line is a function of source the model wrote. It cannot
    introduce, remove or alter a line of code — difflib only re-expresses
    the two texts it is given.
    """
    lines = list(difflib.unified_diff(
        before_text.splitlines(), after_text.splitlines(),
        fromfile=f"a/{file_path}", tofile=f"b/{file_path}", lineterm=""))
    return lines


class LanguageMismatch(ValueError):
    """The model authored in a language other than the one requested.

    Its own outcome rather than a generic malformed-output error: the
    reply parsed fine and may be a perfectly good case, it just isn't a
    case in the language this attempt asked for. A human decides whether
    to keep it under the language the model actually used or re-ask.
    """


def _case_from_pilot_json(obj, case_id, language):
    """Map the pilot's authoring-prompt JSON shape onto the real case
    schema. Structural translation only (wrapping fields into the
    required envelope) — never invents or corrects content the model
    didn't provide."""
    if not isinstance(obj, dict):
        raise ValueError("model output is not a JSON object")

    # The authoring prompt states the language and the reply echoes it
    # back. Stamping the *requested* language onto the case regardless
    # would be exactly the "correcting content the model didn't provide"
    # this function promises not to do — and it is not cosmetic: a case
    # recorded as `go` whose diff is Python is a wrong label in a scored
    # corpus, and it would skew any per-language slice computed from it.
    stated = obj.get("language")
    if isinstance(stated, str) and stated.strip() \
            and stated.strip().lower() != language:
        raise LanguageMismatch(
            f"model authored in {stated.strip()!r} but {language!r} was "
            "requested — not relabeling it, since which one is right "
            "depends on the diff a human has to read")

    defect = obj.get("defect")
    if not isinstance(defect, bool):
        raise ValueError("model output missing boolean 'defect'")

    file_path = obj.get("file_path")
    if not isinstance(file_path, str) or not file_path.strip():
        raise ValueError("model output missing non-empty 'file_path'")
    file_path = file_path.strip()

    before_text = normalize_source(obj.get("before"))
    after_text = normalize_source(obj.get("after"))
    if before_text is None or after_text is None:
        raise ValueError(
            "model output missing 'before'/'after' source (each must be a "
            "list of lines or a string)")

    # Rejected before the syntax check: a no-op is not a syntax problem
    # and reporting it as one would misclassify the failure.
    if before_text == after_text:
        raise NoOpChange(
            "'before' and 'after' are identical — the attempt authored no "
            "change, so there is nothing for a reviewer to judge")

    checker = SYNTAX_CHECKERS.get(language)
    if checker is not None:
        for label, text in (("before", before_text), ("after", after_text)):
            reason = checker(text)
            if reason:
                raise SourceSyntaxError(
                    f"model-authored {label!r} source is not valid "
                    f"{language}: {reason}")

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
        # Harness-generated from the model's own before/after. See
        # build_unified_diff: serialization, not authorship.
        "diff": build_unified_diff(before_text, after_text, file_path),
        "affected_files": [file_path],
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
        # Exactly which fields of a resulting case the harness produced
        # rather than the model. Recorded on every attempt, so a reader
        # never has to infer it from the code (M4-B interface change,
        # eval/authorship-pilot/PREREGISTRATION-PILOT-2.md).
        "harness_generated_fields": [
            "diff", "affected_files", "benchmark_version", "id", "status",
            "difficulty", "provenance",
        ],
        "model_authored_fields": [
            "title", "language", "file_path", "before", "after", "defect",
            "category", "severity", "explanation",
        ],
        "syntax_checked": syntax_checker_available(language),
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
                f"Authored by {model} via reviewer.authorpilot. The model "
                "wrote the complete before/after source, the defect (or "
                "its absence), the category, the severity and the "
                "explanation; all are its own and unmodified. The unified "
                "diff was generated deterministically by the harness from "
                "that before/after pair (difflib), and `affected_files` "
                "restates the model's own `file_path` — serialization "
                "only, incapable of adding or altering a line of code. "
                "`difficulty` was not requested in the authoring prompt "
                "and was defaulted by the pilot harness, not judged by "
                "the model; a human must set it before this case is ever "
                "admitted."
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
    except LanguageMismatch as exc:
        # Before ValueError, which this subclasses.
        record["status"] = "rejected-language-mismatch"
        record["validation_errors"] = [f"{type(exc).__name__}: {exc}"]
    except NoOpChange as exc:
        record["status"] = "rejected-noop"
        record["validation_errors"] = [f"{type(exc).__name__}: {exc}"]
    except SourceSyntaxError as exc:
        record["status"] = "rejected-syntax"
        record["validation_errors"] = [f"{type(exc).__name__}: {exc}"]
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
