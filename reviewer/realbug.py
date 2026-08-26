"""Real-bug candidate queue: intake for `mined-real-fix` candidates.

M4 (docs/ROADMAP.md §4, docs/M4_DESIGN_BRIEF.md §A). A **queue, not an
admission path** — nothing here writes to `eval/cases*` or
`eval/proposals/`. A candidate becomes a proposal (`eval/proposals/`,
`reviewer.propose`) only after a human reads it, and a proposal becomes a
case only after a second human decision. This module's only job is to
make each candidate's licensing and treatment reasoning explicit and
machine-checkable before that conversation happens.

Deliberately does NOT fetch anything from the network, does NOT search
GitHub, and does NOT admit a candidate merely because a `.json` file
exists here — every field below is a claim a human entered, not a fact
this module verified. No mass import mode exists and none should be
added (docs/M4_DESIGN_BRIEF.md §A rule 5).

CLI:
    python3 -m reviewer.realbug validate DIR
    python3 -m reviewer.realbug summary  DIR
Exit codes: 0 valid · 2 validation errors.
"""

import argparse
import json
import os
import re
import sys

# Licenses that permit redistribution of excerpts without triggering
# copyleft or all-rights-reserved exposure — anything outside the list
# needs `reject` or `synthetic-reconstruction`, never
# `verbatim`/`transformed` (docs/M4_DESIGN_BRIEF.md §A rule 1). Imported
# from the schema module rather than redefined, so this advisory queue
# and the corpus admission gate can never disagree about what
# "permissive" means.
from .corpus import PERMISSIVE_LICENSES

CANDIDATE_STATUSES = ("candidate", "queued", "rejected", "promoted")

TREATMENTS = ("verbatim", "transformed", "synthetic-reconstruction", "reject")

# Known-incompatible-with-verbatim-incorporation licenses, named so the
# validator's error message is specific instead of "not in a list".
COPYLEFT_OR_RESTRICTIVE_LICENSES = (
    "GPL-2.0", "GPL-2.0-only", "GPL-2.0-or-later",
    "GPL-3.0", "GPL-3.0-only", "GPL-3.0-or-later",
    "AGPL-3.0", "AGPL-3.0-only", "AGPL-3.0-or-later",
    "LGPL-2.1", "LGPL-3.0", "MPL-2.0", "NOASSERTION", "proprietary", "none",
)

_REQUIRED_FIELDS = (
    "candidate_id", "repository", "repository_url", "commit",
    "parent_commit", "language", "changed_files", "diff_size_lines",
    "license", "bugfix_confidence", "incorporation_safe",
    "recommended_treatment", "status", "notes",
)
_KNOWN_FIELDS = set(_REQUIRED_FIELDS) | {"issue_or_pr_reference", "found_by"}

_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
_REPO_RE = re.compile(r"^[\w.-]+/[\w.-]+$")


def validate_candidate(obj, origin="candidate"):
    """Return (errors, warnings) for one real-bug candidate. Never raises."""
    errors, warnings = [], []
    if not isinstance(obj, dict):
        return [f"{origin}: candidate must be a JSON object"], warnings
    for field in _REQUIRED_FIELDS:
        if field not in obj:
            errors.append(f"{origin}: missing '{field}'")
    unknown = set(obj) - _KNOWN_FIELDS
    if unknown:
        errors.append(f"{origin}: unknown fields {sorted(unknown)}")
    if errors:
        return errors, warnings

    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(obj["candidate_id"])):
        errors.append(f"{origin}: candidate_id must be kebab-case, "
                      f"got {obj['candidate_id']!r}")
    if not (isinstance(obj["repository"], str)
            and _REPO_RE.match(obj["repository"])):
        errors.append(f"{origin}: repository must look like 'owner/repo'")
    if not (isinstance(obj["repository_url"], str)
            and obj["repository_url"].startswith("https://")):
        errors.append(f"{origin}: repository_url must be an https:// URL")
    for field in ("commit", "parent_commit"):
        if not (isinstance(obj[field], str) and _SHA_RE.match(obj[field])):
            errors.append(f"{origin}: {field} must be a 7-40 char hex commit sha")
    if obj["commit"] == obj.get("parent_commit"):
        errors.append(f"{origin}: commit and parent_commit must differ")
    if not (isinstance(obj["language"], str) and obj["language"].strip()):
        errors.append(f"{origin}: language must be a non-empty string")
    files = obj["changed_files"]
    if (not isinstance(files, list) or not files
            or not all(isinstance(f, str) and f.strip() for f in files)):
        errors.append(f"{origin}: changed_files must be a non-empty list of paths")
    size = obj["diff_size_lines"]
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        errors.append(f"{origin}: diff_size_lines must be a positive integer")

    license_ = obj["license"]
    if not (isinstance(license_, str) and license_.strip()):
        errors.append(f"{origin}: license must be a non-empty string "
                      "(the repository's actual license, checked, not assumed)")
        license_ = None
    elif license_ not in PERMISSIVE_LICENSES \
            and license_ not in COPYLEFT_OR_RESTRICTIVE_LICENSES:
        warnings.append(f"{origin}: license {license_!r} is not in the known "
                        "permissive or known-restrictive lists — needs a "
                        "human license read before any treatment but 'reject'")

    conf = obj["bugfix_confidence"]
    if not isinstance(conf, (int, float)) or isinstance(conf, bool) \
            or not 0.0 <= conf <= 1.0:
        errors.append(f"{origin}: bugfix_confidence must be a number in 0.0-1.0")

    safe = obj["incorporation_safe"]
    if not isinstance(safe, bool):
        errors.append(f"{origin}: incorporation_safe must be a boolean")

    treatment = obj["recommended_treatment"]
    if treatment not in TREATMENTS:
        errors.append(f"{origin}: recommended_treatment {treatment!r} "
                      f"not in {TREATMENTS}")

    if obj["status"] not in CANDIDATE_STATUSES:
        errors.append(f"{origin}: status {obj['status']!r} "
                      f"not in {CANDIDATE_STATUSES}")

    if not (isinstance(obj["notes"], str) and obj["notes"].strip()):
        errors.append(f"{origin}: notes must explain the confidence/treatment "
                      "reasoning, not be empty")

    ref = obj.get("issue_or_pr_reference")
    if ref is not None and not (isinstance(ref, str) and ref.strip()):
        errors.append(f"{origin}: issue_or_pr_reference must be a non-empty "
                      "string if present")
    found_by = obj.get("found_by")
    if found_by is not None and not (isinstance(found_by, str) and found_by.strip()):
        errors.append(f"{origin}: found_by must be a non-empty string if present")

    # Cross-field rules — these are the actual license/safety gate, not
    # the field-shape checks above.
    if treatment in TREATMENTS and license_ is not None:
        if safe is False and treatment != "reject":
            errors.append(f"{origin}: incorporation_safe=false requires "
                          "recommended_treatment 'reject'")
        if license_ in COPYLEFT_OR_RESTRICTIVE_LICENSES \
                and treatment not in ("reject", "synthetic-reconstruction"):
            errors.append(f"{origin}: license {license_!r} is not permissive; "
                          "recommended_treatment must be 'reject' or "
                          "'synthetic-reconstruction', got "
                          f"{treatment!r}")
        if treatment == "verbatim" and license_ not in PERMISSIVE_LICENSES:
            errors.append(f"{origin}: recommended_treatment 'verbatim' requires "
                          "a known-permissive license, got "
                          f"{license_!r}")

    return errors, warnings


def load_queue(directory, collect=False):
    """Load and validate every candidate in a queue directory."""
    try:
        names = sorted(n for n in os.listdir(directory) if n.endswith(".json"))
    except OSError as exc:
        errors = [f"cannot read {directory}: {exc}"]
        return ([], errors, []) if collect else _raise(errors)
    out, errors, warnings = [], [], []
    seen_ids = {}
    for name in names:
        path = os.path.join(directory, name)
        try:
            with open(path, encoding="utf-8") as fh:
                obj = json.load(fh)
        except ValueError as exc:
            errors.append(f"{name}: invalid JSON: {exc}")
            continue
        e, w = validate_candidate(obj, origin=name)
        errors.extend(e)
        warnings.extend(w)
        if e:
            continue
        stem = name[:-len(".json")]
        if obj["candidate_id"] != stem:
            errors.append(f"{name}: candidate_id {obj['candidate_id']!r} "
                          "does not match filename")
        if obj["candidate_id"] in seen_ids:
            errors.append(f"{name}: duplicate candidate_id "
                          f"(also in {seen_ids[obj['candidate_id']]})")
        seen_ids[obj["candidate_id"]] = name
        out.append(obj)
    if collect:
        return out, errors, warnings
    if errors:
        _raise(errors)
    return out


def _raise(errors):
    raise ValueError("real-bug queue validation failed:\n  " + "\n  ".join(errors))


def summarize(candidates):
    def count_by(key_fn):
        out = {}
        for c in candidates:
            k = key_fn(c)
            out[k] = out.get(k, 0) + 1
        return dict(sorted(out.items()))

    return {
        "candidates": len(candidates),
        "statuses": count_by(lambda c: c["status"]),
        "recommended_treatments": count_by(lambda c: c["recommended_treatment"]),
        "licenses": count_by(lambda c: c["license"]),
        "languages": count_by(lambda c: c["language"]),
        "reject_count": sum(1 for c in candidates
                            if c["recommended_treatment"] == "reject"),
        "verbatim_count": sum(1 for c in candidates
                              if c["recommended_treatment"] == "verbatim"),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="reviewer-realbug",
        description="Validate the real-bug candidate queue. Never admits "
                    "anything into the scored corpus.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("validate", help="validate a queue directory")
    p1.add_argument("directory")
    p2 = sub.add_parser("summary", help="print a distribution summary")
    p2.add_argument("directory")
    p2.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    candidates, errors, warnings = load_queue(args.directory, collect=True)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        print(f"queue INVALID: {len(errors)} error(s)", file=sys.stderr)
        return 2

    if args.cmd == "validate":
        print(f"{len(candidates)} candidate(s) valid ({len(warnings)} warning(s))")
    else:
        summary = summarize(candidates)
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(f"queue: {summary['candidates']} candidates")
            for label, key in (("status", "statuses"),
                               ("treatment", "recommended_treatments"),
                               ("license", "licenses"),
                               ("language", "languages")):
                dist = ", ".join(f"{k}={v}" for k, v in summary[key].items())
                print(f"  {label:<10} {dist}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
