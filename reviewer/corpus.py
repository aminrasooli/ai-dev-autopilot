"""Benchmark corpus: case schema v2, validation, loading, summary.

One JSON file per case. The schema, taxonomies and every rule enforced
here are defined in docs/BENCHMARK_METHODOLOGY.md — when this module and
that document disagree, one of them has a bug.

The validator is what CI runs over the corpus: fully offline, no GPU, no
model, no network. It is also the door every externally-supplied corpus
(including a private holdout directory) passes through, so a holdout runs
under exactly the rules the public corpus does without this repository
ever seeing its contents.

CLI:
    python3 -m reviewer.corpus              # validate eval/cases, print summary
    python3 -m reviewer.corpus --cases DIR  # validate any corpus directory
Exit codes: 0 valid · 2 validation errors found.
"""

import argparse
import hashlib
import json
import os
import re
import sys

from .errors import ConfigError
from .result import CATEGORIES, SEVERITIES

BENCHMARK_VERSION = 2

LANGUAGES = (
    "python", "shell", "sql", "javascript", "typescript",
    "go", "java", "rust", "config", "docs",
)

PROVENANCE_TYPES = (
    "seeded-synthetic", "authored-realistic", "mined-real-fix", "mutation",
)

AUTHOR_FAMILIES = ("claude", "qwen", "human", "mixed", "other")

STATUSES = ("pilot", "stable")

_SEV_INDEX = {s: i for i, s in enumerate(SEVERITIES)}

_REQUIRED_FIELDS = (
    "benchmark_version", "id", "title", "language", "status",
    "diff", "affected_files", "provenance", "ground_truth",
)
_KNOWN_FIELDS = set(_REQUIRED_FIELDS) | {"tags"}

# Shapes that must never appear in a public case file. Deliberately
# vendor-shaped prefixes, not generic entropy heuristics: a case ABOUT a
# committed secret uses an invented prefix instead (e.g. payk_live_...),
# which is the whole point — it must look live to the reviewer under test
# without tripping real secret scanners here or on the forge.
_SECRET_PATTERNS = (
    re.compile(r"sk_live_[0-9A-Za-z]"),
    re.compile(r"sk-[A-Za-z0-9]{20}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[0-9A-Za-z]{20}"),
    re.compile(r"github_pat_[0-9A-Za-z_]{20}"),
    re.compile(r"xox[baprs]-"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"AIza[0-9A-Za-z_-]{30}"),
)

# Machine-specific content that must never leak into a public corpus.
_PRIVATE_PATTERNS = (
    re.compile(r"/home/[a-z]"),
    re.compile(r"\b(?:10|172\.(?:1[6-9]|2\d|3[01])|192\.168)\.\d+\.\d+"),
)

_DIFF_FILE_RE = re.compile(r"^\+\+\+ b/(.+)$", re.MULTILINE)


def validate_case(obj, origin="case"):
    """Return (errors, warnings) for one case object. Never raises."""
    errors, warnings = [], []
    if not isinstance(obj, dict):
        return [f"{origin}: case must be a JSON object"], warnings

    for field in _REQUIRED_FIELDS:
        if field not in obj:
            errors.append(f"{origin}: missing '{field}'")
    unknown = set(obj) - _KNOWN_FIELDS
    if unknown:
        errors.append(f"{origin}: unknown fields {sorted(unknown)}")
    if errors:
        return errors, warnings

    if obj["benchmark_version"] != BENCHMARK_VERSION:
        errors.append(f"{origin}: benchmark_version must be {BENCHMARK_VERSION}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(obj["id"])):
        errors.append(f"{origin}: id must be kebab-case, got {obj['id']!r}")
    if not isinstance(obj["title"], str) or not obj["title"].strip():
        errors.append(f"{origin}: title must be a non-empty string")
    if obj["language"] not in LANGUAGES:
        errors.append(f"{origin}: language {obj['language']!r} not in {LANGUAGES}")
    if obj["status"] not in STATUSES:
        errors.append(f"{origin}: status {obj['status']!r} not in {STATUSES}")

    diff = obj["diff"]
    if isinstance(diff, list):
        if not all(isinstance(line, str) for line in diff) or not diff:
            errors.append(f"{origin}: diff list must be non-empty strings")
            diff = ""
        else:
            diff = "\n".join(diff) + "\n"
    if not isinstance(diff, str) or not diff.strip():
        errors.append(f"{origin}: diff must be a non-empty string or list of lines")
        diff = ""

    files = obj["affected_files"]
    if (not isinstance(files, list) or not files
            or not all(isinstance(f, str) and f.strip() for f in files)):
        errors.append(f"{origin}: affected_files must be a non-empty list of paths")
    elif diff:
        in_diff = set(_DIFF_FILE_RE.findall(diff))
        listed = set(files)
        # /dev/null targets (deletions) never appear in affected_files.
        in_diff.discard("/dev/null")
        for f in sorted(listed - in_diff):
            errors.append(f"{origin}: affected_files lists {f!r} not present in diff")
        for f in sorted(in_diff - listed):
            errors.append(f"{origin}: diff touches {f!r} missing from affected_files")

    prov = obj["provenance"]
    if not isinstance(prov, dict):
        errors.append(f"{origin}: provenance must be an object")
    else:
        if prov.get("type") not in PROVENANCE_TYPES:
            errors.append(f"{origin}: provenance.type {prov.get('type')!r} "
                          f"not in {PROVENANCE_TYPES}")
        if prov.get("author_family") not in AUTHOR_FAMILIES:
            errors.append(f"{origin}: provenance.author_family "
                          f"{prov.get('author_family')!r} not in {AUTHOR_FAMILIES}")
        ref = prov.get("reference")
        if prov.get("type") == "mined-real-fix" and not (
                isinstance(ref, str) and ref.strip()):
            errors.append(f"{origin}: mined-real-fix requires provenance.reference")
        unknown_prov = set(prov) - {"type", "author_family", "reference"}
        if unknown_prov:
            errors.append(f"{origin}: unknown provenance fields {sorted(unknown_prov)}")

    gt = obj["ground_truth"]
    if not isinstance(gt, dict) or not isinstance(gt.get("defect"), bool):
        errors.append(f"{origin}: ground_truth.defect must be a boolean")
    else:
        if not isinstance(gt.get("explanation"), str) or not gt["explanation"].strip():
            errors.append(f"{origin}: ground_truth.explanation must be non-empty")
        if gt["defect"]:
            if gt.get("category") not in CATEGORIES:
                errors.append(f"{origin}: ground_truth.category "
                              f"{gt.get('category')!r} is not in the vocabulary")
            sev = gt.get("severity", [])
            if (not isinstance(sev, list) or len(sev) != 2
                    or any(s not in SEVERITIES for s in sev)
                    or _SEV_INDEX[sev[0]] > _SEV_INDEX[sev[1]]):
                errors.append(f"{origin}: ground_truth.severity must be "
                              "[min, max] from the scale")
            elif sev[0] == SEVERITIES[0] and sev[1] == SEVERITIES[-1]:
                warnings.append(f"{origin}: severity range spans the whole "
                                "scale — vacuous ground truth")
            alts = gt.get("accepted_categories", [])
            if not isinstance(alts, list):
                errors.append(f"{origin}: accepted_categories must be a list")
            else:
                for alt in alts:
                    if alt not in CATEGORIES:
                        errors.append(f"{origin}: accepted_categories entry "
                                      f"{alt!r} is not in the vocabulary")
                if gt.get("category") in alts:
                    errors.append(f"{origin}: accepted_categories repeats the "
                                  "primary category")
                if len(set(alts)) != len(alts):
                    errors.append(f"{origin}: accepted_categories has duplicates")
                if len(alts) > 2:
                    errors.append(f"{origin}: at most 2 accepted_categories "
                                  "(alternatives must stay rare and defensible)")
            unknown_gt = set(gt) - {"defect", "category", "severity",
                                    "explanation", "accepted_categories"}
            if unknown_gt:
                errors.append(f"{origin}: unknown ground_truth fields "
                              f"{sorted(unknown_gt)}")
        else:
            contradictions = set(gt) & {"category", "severity"}
            if contradictions:
                errors.append(f"{origin}: clean case must not carry "
                              f"{sorted(contradictions)}")
            unknown_gt = set(gt) - {"defect", "explanation"}
            if unknown_gt:
                errors.append(f"{origin}: unknown ground_truth fields "
                              f"{sorted(unknown_gt)}")

    tags = obj.get("tags", [])
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        errors.append(f"{origin}: tags must be a list of strings")

    raw = json.dumps(obj)
    for pattern in _SECRET_PATTERNS:
        if pattern.search(raw):
            errors.append(f"{origin}: matches secret pattern {pattern.pattern!r}")
    for pattern in _PRIVATE_PATTERNS:
        if pattern.search(raw):
            errors.append(f"{origin}: matches private-content pattern "
                          f"{pattern.pattern!r}")
    return errors, warnings


def corpus_fingerprint(cases):
    """Deterministic sha256 over the full validated corpus content, keyed
    by case id order — identical corpora hash identically wherever they
    live on disk."""
    canon = json.dumps(sorted(cases, key=lambda c: c["id"]),
                       sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _normalized_diff_key(diff_text):
    canon = re.sub(r"\s+", "", diff_text).lower()
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def load_corpus(cases_dir, collect=False):
    """Load and validate a corpus directory.

    Returns validated cases with diff normalized to a string. By default
    raises ConfigError listing every problem; with collect=True returns
    (cases, errors, warnings) and never raises — the CLI uses that to
    report everything at once.
    """
    try:
        names = sorted(n for n in os.listdir(cases_dir) if n.endswith(".json"))
    except OSError as exc:
        raise ConfigError(f"cannot read corpus directory {cases_dir}: {exc}")
    errors, warnings, cases = [], [], []
    if not names:
        errors.append(f"no cases found in {cases_dir}")
    seen_ids = {}
    seen_diffs = {}
    for name in names:
        path = os.path.join(cases_dir, name)
        try:
            with open(path, encoding="utf-8") as fh:
                obj = json.load(fh)
        except ValueError as exc:
            errors.append(f"{name}: invalid JSON: {exc}")
            continue
        case_errors, case_warnings = validate_case(obj, origin=name)
        errors.extend(case_errors)
        warnings.extend(case_warnings)
        if case_errors:
            continue
        stem = name[:-len(".json")]
        if obj["id"] != stem:
            errors.append(f"{name}: id {obj['id']!r} does not match filename")
        if obj["id"] in seen_ids:
            errors.append(f"{name}: duplicate id (also in {seen_ids[obj['id']]})")
        seen_ids[obj["id"]] = name
        if isinstance(obj["diff"], list):
            obj["diff"] = "\n".join(obj["diff"]) + "\n"
        key = _normalized_diff_key(obj["diff"])
        if key in seen_diffs:
            errors.append(f"{name}: diff is a near-duplicate of {seen_diffs[key]}")
        seen_diffs[key] = name
        cases.append(obj)
    if collect:
        return cases, errors, warnings
    if errors:
        raise ConfigError("corpus validation failed:\n  " + "\n  ".join(errors))
    return cases


def summarize(cases):
    """Distribution summary used by the CLI and by result submissions."""
    def count_by(key_fn):
        out = {}
        for case in cases:
            k = key_fn(case)
            out[k] = out.get(k, 0) + 1
        return dict(sorted(out.items()))

    defective = [c for c in cases if c["ground_truth"]["defect"]]
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "cases": len(cases),
        "defective": len(defective),
        "clean": len(cases) - len(defective),
        "languages": count_by(lambda c: c["language"]),
        "categories": count_by(
            lambda c: c["ground_truth"].get("category", "(clean)")),
        "severities": count_by(
            lambda c: "-".join(c["ground_truth"]["severity"])
            if c["ground_truth"]["defect"] else "(clean)"),
        "provenance_types": count_by(lambda c: c["provenance"]["type"]),
        "author_families": count_by(lambda c: c["provenance"]["author_family"]),
        "statuses": count_by(lambda c: c["status"]),
        "cross_file_cases": sum(1 for c in cases if len(c["affected_files"]) > 1),
        # A stable fingerprint of the exact corpus content, so a result
        # report can name precisely what it ran against without carrying
        # any filesystem path.
        "sha256": corpus_fingerprint(cases),
    }


def render_summary(summary):
    lines = [f"corpus: {summary['cases']} cases "
             f"({summary['defective']} defective, {summary['clean']} clean, "
             f"{summary['cross_file_cases']} cross-file) — "
             f"benchmark v{summary['benchmark_version']}"]
    for label, key in (("languages", "languages"), ("categories", "categories"),
                       ("severities", "severities"),
                       ("provenance", "provenance_types"),
                       ("authored by", "author_families")):
        dist = ", ".join(f"{k}={v}" for k, v in summary[key].items())
        lines.append(f"  {label:<12} {dist}")
    return "\n".join(lines)


DEFAULT_CASES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "eval", "cases")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="reviewer-corpus",
        description="Validate a benchmark corpus and print its distribution.")
    parser.add_argument("--cases", default=DEFAULT_CASES_DIR,
                        help="corpus directory (default: eval/cases)")
    parser.add_argument("--json", action="store_true",
                        help="emit the summary as JSON")
    args = parser.parse_args(argv)

    cases, errors, warnings = load_corpus(args.cases, collect=True)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        print(f"corpus INVALID: {len(errors)} error(s), "
              f"{len(warnings)} warning(s)", file=sys.stderr)
        return 2
    summary = summarize(cases)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(render_summary(summary))
        print(f"corpus valid ({len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
