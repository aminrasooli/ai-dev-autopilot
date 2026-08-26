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

AUTHOR_FAMILIES = ("claude", "qwen", "deepseek", "human", "mixed", "other")

# M4 (docs/ROADMAP.md §4, docs/M4_DESIGN_BRIEF.md): how source material for
# a mined-real-fix case was incorporated. Required exactly when
# provenance.type == "mined-real-fix" — that is the one class where "how
# much of the original code survives" is a real licensing/credibility
# question, not a stylistic detail.
TRANSFORMATIONS = ("verbatim", "transformed", "synthetic-reconstruction")

# Licenses under which this project is willing to carry code derived from
# someone else's repository (docs/M4_DESIGN_BRIEF.md §A rule 1). Defined
# here, in the schema module, because this is the gate that decides what
# may enter a *scored corpus* — `reviewer.realbug` imports it so the
# advisory queue and the actual admission path cannot drift apart. Not
# legal advice, a practical allowlist for this project's risk tolerance:
# anything outside it may only be reached by
# `transformation: synthetic-reconstruction`, which derives no code.
PERMISSIVE_LICENSES = (
    "MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC", "0BSD",
    "Unlicense",
)

# Author families that name a specific model lineage. For these,
# `author_model` must actually be a model of that family — otherwise a
# case could read `author_family: qwen` while naming a Claude model as
# its author, which is exactly docs/ROADMAP.md §9 failure mode 3 written
# into the schema instead of caught by it.
_MODEL_AUTHOR_FAMILIES = ("claude", "qwen", "deepseek")

_SOURCE_COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")

STATUSES = ("pilot", "stable")

# How much work the defect asks of a reviewer. Recorded so that a high
# detection rate can be read honestly: 41/41 on a corpus that is mostly
# obvious-local says less than the same number on a subtle one.
DIFFICULTIES = ("obvious-local", "moderate", "contextual", "subtle", "cross-file")

_SEV_INDEX = {s: i for i, s in enumerate(SEVERITIES)}

_REQUIRED_FIELDS = (
    "benchmark_version", "id", "title", "language", "status",
    "diff", "affected_files", "provenance", "ground_truth",
)
_KNOWN_FIELDS = set(_REQUIRED_FIELDS) | {"tags", "difficulty"}

# Optional, non-scoring ground-truth provenance fields (M3 methodology
# decision, docs/M3_METHODOLOGY_DECISION.md): a case author may run a
# one-time offline validation script — never part of the harness, never
# seen by a model, never CI — to raise confidence in a state/cache or
# concurrency case's label, and record that here. These fields never
# affect detected/miss/category/severity scoring.
_EXECUTION_PROVENANCE_FIELDS = {
    "execution_validated", "validation_note", "validation_artifact_sha256",
}
_ARTIFACT_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

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
        is_mined = prov.get("type") == "mined-real-fix"
        if is_mined and not (isinstance(ref, str) and ref.strip()):
            errors.append(f"{origin}: mined-real-fix requires provenance.reference")

        # M4 provenance fields (docs/M4_DESIGN_BRIEF.md). All optional,
        # non-scoring, fingerprint-only additions per
        # docs/BENCHMARK_METHODOLOGY.md §11a — existing v2/v3 cases carry
        # none of them and remain valid. mined-real-fix is the one type
        # where they become required: that is the class this project
        # incorporates someone else's code into, so the licensing and
        # transformation record is not optional for it.
        for field in ("source_repository", "source_commit", "source_license",
                      "provenance_notes"):
            if field in prov and not (
                    isinstance(prov[field], str) and prov[field].strip()):
                errors.append(f"{origin}: provenance.{field} must be a "
                              "non-empty string")
        if is_mined:
            for field in ("source_repository", "source_commit", "source_license"):
                if not (isinstance(prov.get(field), str) and prov[field].strip()):
                    errors.append(f"{origin}: mined-real-fix requires "
                                  f"provenance.{field}")
        transformation = prov.get("transformation")
        if transformation is not None and transformation not in TRANSFORMATIONS:
            errors.append(f"{origin}: provenance.transformation "
                          f"{transformation!r} not in {TRANSFORMATIONS}")
        if is_mined and transformation is None:
            errors.append(f"{origin}: mined-real-fix requires "
                          "provenance.transformation")
        if not is_mined and transformation is not None:
            errors.append(f"{origin}: provenance.transformation only applies "
                          "to provenance.type mined-real-fix")

        # A source attribution without a license record is a claim this
        # project cannot stand behind — it reads as "derived from that
        # repository" while recording nothing about whether that was
        # allowed. Either say where it came from *and* under what, or
        # say neither.
        source_license = prov.get("source_license")
        attributes_a_source = any(
            prov.get(f) for f in ("source_repository", "source_commit",
                                  "transformation"))
        if attributes_a_source and not (
                isinstance(source_license, str) and source_license.strip()):
            errors.append(f"{origin}: provenance names a source "
                          "(source_repository/source_commit/transformation) "
                          "without provenance.source_license")

        # The licensing gate itself, mirroring the advisory queue's rule
        # (docs/M4_DESIGN_BRIEF.md §A rules 1 and 4) at the point that
        # actually matters: what may enter a scored corpus.
        # `synthetic-reconstruction` is exempt by construction — it
        # derives no code from the source, only the observed mechanism.
        if transformation in ("verbatim", "transformed") \
                and isinstance(source_license, str) \
                and source_license.strip() not in PERMISSIVE_LICENSES:
            errors.append(
                f"{origin}: provenance.transformation {transformation!r} "
                f"requires a known-permissive source_license "
                f"{PERMISSIVE_LICENSES}, got {source_license!r} — use "
                "'synthetic-reconstruction' (no code derived) or do not "
                "admit the case")

        # A commit that cannot be looked up is not provenance. Same shape
        # the queue already enforces (reviewer.realbug), applied here so a
        # case cannot carry a source_commit the queue would have rejected.
        source_commit = prov.get("source_commit")
        if isinstance(source_commit, str) and source_commit.strip() \
                and not _SOURCE_COMMIT_RE.match(source_commit.strip()):
            errors.append(f"{origin}: provenance.source_commit must be a "
                          f"7-40 char hex commit sha, got {source_commit!r}")

        author_model = prov.get("author_model")
        if author_model is not None and not (
                isinstance(author_model, str) and author_model.strip()):
            errors.append(f"{origin}: provenance.author_model must be a "
                          "non-empty string")
        elif isinstance(author_model, str) and author_model.strip():
            family = prov.get("author_family")
            if family in _MODEL_AUTHOR_FAMILIES \
                    and family not in author_model.lower():
                errors.append(
                    f"{origin}: provenance.author_model {author_model!r} does "
                    f"not name a {family!r} model — author_family and "
                    "author_model must agree, or the family is 'mixed'/'other'")

        human_authored = prov.get("human_authored")
        if "human_authored" in prov and not isinstance(human_authored, bool):
            errors.append(f"{origin}: provenance.human_authored must be a "
                          "boolean")
        elif prov.get("author_family") == "human" and human_authored is None:
            errors.append(f"{origin}: author_family 'human' requires an "
                          "explicit provenance.human_authored (true only "
                          "when a human wrote the case content itself, "
                          "false for human-reviewed/tool-formatted cases)")
        if human_authored is True and prov.get("author_family") != "human":
            errors.append(f"{origin}: provenance.human_authored=true requires "
                          "author_family 'human'")
        # "A human wrote this" and "this model wrote this" cannot both be
        # true of the same case content. A human-*reviewed* case (concept
        # by a person, formatting by tooling) is human_authored=false and
        # may name the model that formatted it.
        if human_authored is True and prov.get("author_model") is not None:
            errors.append(f"{origin}: provenance.human_authored=true cannot "
                          "carry provenance.author_model — a case a model "
                          "authored is human-reviewed at best "
                          "(human_authored=false)")

        unknown_prov = set(prov) - {
            "type", "author_family", "reference", "source_repository",
            "source_commit", "source_license", "transformation",
            "author_model", "human_authored", "provenance_notes",
        }
        if unknown_prov:
            errors.append(f"{origin}: unknown provenance fields {sorted(unknown_prov)}")

    gt = obj["ground_truth"]
    if not isinstance(gt, dict) or not isinstance(gt.get("defect"), bool):
        errors.append(f"{origin}: ground_truth.defect must be a boolean")
    else:
        if not isinstance(gt.get("explanation"), str) or not gt["explanation"].strip():
            errors.append(f"{origin}: ground_truth.explanation must be non-empty")

        if "execution_validated" in gt and not isinstance(
                gt["execution_validated"], bool):
            errors.append(f"{origin}: ground_truth.execution_validated "
                          "must be a boolean")
        if gt.get("execution_validated") is True and (
                not isinstance(gt.get("validation_note"), str)
                or not gt["validation_note"].strip()):
            errors.append(f"{origin}: execution_validated=true requires a "
                          "non-empty ground_truth.validation_note")
        if "validation_note" in gt and not isinstance(gt["validation_note"], str):
            errors.append(f"{origin}: ground_truth.validation_note must be "
                          "a string")
        artifact = gt.get("validation_artifact_sha256")
        if artifact is not None and not _ARTIFACT_SHA256_RE.fullmatch(str(artifact)):
            errors.append(f"{origin}: ground_truth.validation_artifact_sha256 "
                          "must be a lowercase 64-hex-char sha256")

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
            unknown_gt = set(gt) - ({"defect", "category", "severity",
                                     "explanation", "accepted_categories"}
                                    | _EXECUTION_PROVENANCE_FIELDS)
            if unknown_gt:
                errors.append(f"{origin}: unknown ground_truth fields "
                              f"{sorted(unknown_gt)}")
        else:
            contradictions = set(gt) & {"category", "severity"}
            if contradictions:
                errors.append(f"{origin}: clean case must not carry "
                              f"{sorted(contradictions)}")
            unknown_gt = set(gt) - ({"defect", "explanation"}
                                    | _EXECUTION_PROVENANCE_FIELDS)
            if unknown_gt:
                errors.append(f"{origin}: unknown ground_truth fields "
                              f"{sorted(unknown_gt)}")

    tags = obj.get("tags", [])
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        errors.append(f"{origin}: tags must be a list of strings")

    difficulty = obj.get("difficulty")
    if difficulty is not None and difficulty not in DIFFICULTIES:
        errors.append(f"{origin}: difficulty {difficulty!r} not in {DIFFICULTIES}")
    if isinstance(gt, dict) and gt.get("defect") and difficulty is None:
        errors.append(f"{origin}: defective cases must declare a difficulty")
    # Clean cases may optionally declare a difficulty too (M3 methodology
    # decision: "hard clean controls" need a machine-distinguishable tier
    # from v2's undifferentiated clean cases). Here difficulty means how
    # convincingly suspicious a correct diff looks, not how hard a defect
    # is to find — there is no defect. Optional, unlike the defective case.

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


def cross_corpus_conflicts(corpora):
    """Find case ids and diffs that collide ACROSS separate corpora.

    `load_corpus` already refuses duplicate ids and near-duplicate diffs
    *within* one directory, but every corpus this project ships lives in
    its own directory (`eval/cases`, `eval/cases-v3/cases`, and any
    provenance tranche), so nothing stopped a new tranche from
    re-admitting a case that already exists in a frozen corpus. That
    matters for M4 specifically: a "real historical bug" case that is
    secretly a duplicate of a seeded-synthetic v2 case would inflate the
    provenance claim while adding no new evidence.

    `corpora` maps a display name to a list of validated cases. Returns
    a list of conflict dicts, each naming both sides — never raises, and
    never mutates a corpus. Diff comparison reuses the same whitespace-
    and case-insensitive key `load_corpus` uses, so the two checks agree
    about what "the same diff" means.
    """
    conflicts = []
    seen_ids, seen_diffs = {}, {}
    for name in sorted(corpora):
        for case in sorted(corpora[name], key=lambda c: c["id"]):
            case_id = case["id"]
            if case_id in seen_ids:
                other_corpus, _ = seen_ids[case_id]
                conflicts.append({
                    "kind": "duplicate-id", "id": case_id,
                    "corpus": name, "other_corpus": other_corpus,
                    "other_id": case_id})
            else:
                seen_ids[case_id] = (name, case_id)
            diff = case["diff"]
            if isinstance(diff, list):
                diff = "\n".join(diff) + "\n"
            key = _normalized_diff_key(diff)
            if key in seen_diffs:
                other_corpus, other_id = seen_diffs[key]
                conflicts.append({
                    "kind": "duplicate-diff", "id": case_id,
                    "corpus": name, "other_corpus": other_corpus,
                    "other_id": other_id})
            else:
                seen_diffs[key] = (name, case_id)
    return conflicts


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
        "difficulties": count_by(lambda c: c.get("difficulty") or "(clean)"),
        "provenance_types": count_by(lambda c: c["provenance"]["type"]),
        "author_families": count_by(lambda c: c["provenance"]["author_family"]),
        "statuses": count_by(lambda c: c["status"]),
        "cross_file_cases": sum(1 for c in cases if len(c["affected_files"]) > 1),
        # Non-scoring provenance visibility, not a quality signal: how
        # many cases carry an offline execution-validated ground truth
        # (docs/M3_METHODOLOGY_DECISION.md).
        "execution_validated_cases": sum(
            1 for c in cases if c["ground_truth"].get("execution_validated")),
        # M4 provenance visibility (docs/M4_DESIGN_BRIEF.md), same
        # non-scoring spirit as execution_validated_cases above.
        "human_authored_cases": sum(
            1 for c in cases if c["provenance"].get("human_authored") is True),
        "mined_real_fix_cases": sum(
            1 for c in cases if c["provenance"]["type"] == "mined-real-fix"),
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
                       ("difficulty", "difficulties"),
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
    parser.add_argument("--cross-check", action="append", default=[],
                        metavar="DIR",
                        help="also load DIR and report case ids or diffs "
                             "that collide with --cases (repeatable). Use "
                             "when admitting a new tranche alongside a "
                             "frozen corpus.")
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
    conflicts = []
    if args.cross_check:
        corpora = {args.cases: cases}
        for other in args.cross_check:
            try:
                corpora[other] = load_corpus(other)
            except ConfigError as exc:
                print(f"error: cross-check corpus {other}: {exc}",
                      file=sys.stderr)
                return 2
        conflicts = cross_corpus_conflicts(corpora)

    summary = summarize(cases)
    if args.json:
        if args.cross_check:
            summary["cross_corpus_conflicts"] = conflicts
        print(json.dumps(summary, indent=2))
    else:
        print(render_summary(summary))
        print(f"corpus valid ({len(warnings)} warning(s))")
        if args.cross_check:
            print(f"cross-check against {len(args.cross_check)} other "
                  f"corpus/corpora: {len(conflicts)} conflict(s)")
    if conflicts:
        for c in conflicts:
            print(f"error: {c['kind']}: {c['corpus']}:{c['id']} collides "
                  f"with {c['other_corpus']}:{c['other_id']}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
