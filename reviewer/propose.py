"""Case proposals and independent answer-key audits.

Two intake formats, both built on the same principle: **a model may
propose, but never write into the scored corpus.** Nothing in this
module can create or modify a file in `eval/cases/`. Proposals and
audits land in a separate area, are schema-validated here, and enter the
benchmark only through human adjudication.

Why this exists: the corpus is currently 100% Claude-authored while
Claude models are among those evaluated (docs/BENCHMARK_METHODOLOGY.md
§10). The credible fix is other authors — humans, and other model
families — and that needs an intake path that is safe to point a model
at.

  CASE PROPOSAL — "here is a case you might add"
  AUDIT OPINION — "here is what I think your existing answer key says"

An audit opinion is advisory evidence for a human adjudicator. It is
never applied automatically, and disagreement by a model is not proof of
anything: the model may simply be wrong.

CLI:
    python3 -m reviewer.propose validate-cases  DIR
    python3 -m reviewer.propose validate-audits FILE.json
Exit codes: 0 valid · 2 validation errors.
"""

import argparse
import json
import os
import sys

from .corpus import (AUTHOR_FAMILIES, DIFFICULTIES, LANGUAGES, validate_case)
from .result import CATEGORIES, SEVERITIES

PROPOSAL_STATUSES = ("proposed", "under-review", "accepted", "rejected")

_PROPOSAL_REQUIRED = ("proposal_id", "author_family", "generator",
                      "status", "case", "rationale")
_PROPOSAL_KNOWN = set(_PROPOSAL_REQUIRED) | {"notes", "reviewer_notes"}

_AUDIT_REQUIRED = ("case_id", "defect_opinion", "confidence", "rationale")
_AUDIT_KNOWN = set(_AUDIT_REQUIRED) | {
    "category_opinion", "severity_opinion", "disagrees_with_ground_truth",
    "suspected_fixture_flaw", "notes"}


def validate_proposal(obj, origin="proposal"):
    """A proposal wraps a candidate case in provenance and review state."""
    errors, warnings = [], []
    if not isinstance(obj, dict):
        return [f"{origin}: proposal must be a JSON object"], warnings
    for field in _PROPOSAL_REQUIRED:
        if field not in obj:
            errors.append(f"{origin}: missing '{field}'")
    unknown = set(obj) - _PROPOSAL_KNOWN
    if unknown:
        errors.append(f"{origin}: unknown fields {sorted(unknown)}")
    if errors:
        return errors, warnings

    if obj["author_family"] not in AUTHOR_FAMILIES:
        errors.append(f"{origin}: author_family {obj['author_family']!r} "
                      f"not in {AUTHOR_FAMILIES}")
    if obj["status"] not in PROPOSAL_STATUSES:
        errors.append(f"{origin}: status {obj['status']!r} "
                      f"not in {PROPOSAL_STATUSES}")
    if not isinstance(obj["generator"], str) or not obj["generator"].strip():
        errors.append(f"{origin}: generator must name the model or person "
                      "that produced this (e.g. 'qwen3.6:27b' or 'human:alice')")
    if not isinstance(obj["rationale"], str) or not obj["rationale"].strip():
        errors.append(f"{origin}: rationale must explain why the case is "
                      "worth adding")

    # The embedded case must satisfy the real corpus schema — a proposal
    # that could not become a case is not a useful proposal.
    case = obj["case"]
    case_errors, case_warnings = validate_case(case, origin=f"{origin}.case")
    errors.extend(case_errors)
    warnings.extend(case_warnings)

    if isinstance(case, dict) and isinstance(case.get("provenance"), dict):
        if case["provenance"].get("author_family") != obj["author_family"]:
            errors.append(f"{origin}: case provenance.author_family disagrees "
                          "with the proposal's author_family")
    if obj["status"] == "accepted":
        warnings.append(f"{origin}: status 'accepted' in a proposal file is "
                        "advisory only — admission happens by a human moving "
                        "the case into eval/cases, not by this field")
    return errors, warnings


def validate_audit(obj, origin="audit"):
    """An independent opinion about one existing case's answer key."""
    errors, warnings = [], []
    if not isinstance(obj, dict):
        return [f"{origin}: audit entry must be a JSON object"], warnings
    for field in _AUDIT_REQUIRED:
        if field not in obj:
            errors.append(f"{origin}: missing '{field}'")
    unknown = set(obj) - _AUDIT_KNOWN
    if unknown:
        errors.append(f"{origin}: unknown fields {sorted(unknown)}")
    if errors:
        return errors, warnings

    if obj["defect_opinion"] not in ("defect", "clean", "unsure"):
        errors.append(f"{origin}: defect_opinion must be defect/clean/unsure")
    conf = obj["confidence"]
    if not isinstance(conf, (int, float)) or not 0.0 <= conf <= 1.0:
        errors.append(f"{origin}: confidence must be a number in 0.0–1.0")
    if not isinstance(obj["rationale"], str) or not obj["rationale"].strip():
        errors.append(f"{origin}: rationale must be a non-empty string")
    cat = obj.get("category_opinion")
    if cat is not None and cat not in CATEGORIES:
        errors.append(f"{origin}: category_opinion {cat!r} not in the vocabulary")
    sev = obj.get("severity_opinion")
    if sev is not None and sev not in SEVERITIES:
        errors.append(f"{origin}: severity_opinion {sev!r} not in {SEVERITIES}")
    for flag in ("disagrees_with_ground_truth", "suspected_fixture_flaw"):
        if flag in obj and not isinstance(obj[flag], bool):
            errors.append(f"{origin}: {flag} must be a boolean")
    if obj["defect_opinion"] == "clean" and cat is not None:
        errors.append(f"{origin}: a 'clean' opinion must not carry a category")
    return errors, warnings


def load_proposals(directory):
    out, errors, warnings = [], [], []
    try:
        names = sorted(n for n in os.listdir(directory) if n.endswith(".json"))
    except OSError as exc:
        return [], [f"cannot read {directory}: {exc}"], []
    for name in names:
        path = os.path.join(directory, name)
        try:
            with open(path, encoding="utf-8") as fh:
                obj = json.load(fh)
        except ValueError as exc:
            errors.append(f"{name}: invalid JSON: {exc}")
            continue
        e, w = validate_proposal(obj, origin=name)
        errors.extend(e)
        warnings.extend(w)
        if not e:
            out.append(obj)
    ids = [p["proposal_id"] for p in out]
    if len(set(ids)) != len(ids):
        errors.append("duplicate proposal_id values")
    return out, errors, warnings


def load_audits(path, known_case_ids=None):
    try:
        with open(path, encoding="utf-8") as fh:
            obj = json.load(fh)
    except (OSError, ValueError) as exc:
        return [], [f"cannot read {path}: {exc}"], []
    entries = obj.get("audits") if isinstance(obj, dict) else obj
    if not isinstance(entries, list):
        return [], [f"{path}: expected a list of audits (or an object with "
                    "an 'audits' list)"], []
    out, errors, warnings = [], [], []
    for i, entry in enumerate(entries):
        e, w = validate_audit(entry, origin=f"{path}[{i}]")
        errors.extend(e)
        warnings.extend(w)
        if not e:
            out.append(entry)
    if known_case_ids is not None:
        for entry in out:
            if entry["case_id"] not in known_case_ids:
                warnings.append(f"{path}: audit references unknown case "
                                f"{entry['case_id']!r}")
    return out, errors, warnings


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="reviewer-propose",
        description="Validate case proposals and independent audit opinions.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("validate-cases", help="validate a proposals directory")
    p1.add_argument("directory")
    p2 = sub.add_parser("validate-audits", help="validate an audit file")
    p2.add_argument("path")
    args = parser.parse_args(argv)

    if args.cmd == "validate-cases":
        items, errors, warnings = load_proposals(args.directory)
        label = "proposal"
    else:
        from .corpus import DEFAULT_CASES_DIR, load_corpus
        try:
            known = {c["id"] for c in load_corpus(DEFAULT_CASES_DIR)}
        except Exception:
            known = None
        items, errors, warnings = load_audits(args.path, known)
        label = "audit"
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    if errors:
        print(f"{label}s INVALID: {len(errors)} error(s)", file=sys.stderr)
        return 2
    print(f"{len(items)} {label}(s) valid ({len(warnings)} warning(s))")
    if label == "audit":
        flagged = [a for a in items if a.get("disagrees_with_ground_truth")]
        print(f"{len(flagged)} disagree with current ground truth "
              "— advisory only, for human adjudication")
    return 0


if __name__ == "__main__":
    sys.exit(main())
