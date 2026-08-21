"""Result-report integrity checking.

What this proves and what it does not, stated up front because the
distinction is the whole point:

  It PROVES a report is internally consistent — that its headline
  summary is exactly what its own raw per-run observations produce when
  the scoring code is re-run over them, that its counts are possible,
  and that its declared metadata is present and well-formed.

  It does NOT prove honesty. Someone can fabricate a complete, perfectly
  self-consistent report. What this removes is the cheap failure mode:
  a summary that quietly disagrees with the runs beneath it, whether
  through tampering, a harness bug, or hand-editing "just the total".
  Catching an inconsistent submission is worth doing; claiming it makes
  submissions trustworthy would not be.

Trust levels (docs/BENCHMARK_METHODOLOGY.md §11b) do the rest: only an
independent reproduction (L2) costs a faker real work.

CLI:
    python3 -m reviewer.verify REPORT.json [REPORT.json ...]
Exit codes: 0 all reports consistent · 2 a report failed.
"""

import argparse
import json
import sys

from .evaluate import aggregate, _corpus_consistency

REQUIRED_TOP = ("report_format", "backend", "model", "runs_per_case",
                "corpus", "cases", "summary")
REQUIRED_CORPUS = ("case_count", "benchmark_version", "sha256")

# Fields a submission must carry for a reproducible claim (trust level
# L1). Absent metadata is a warning, not a failure: an L0 self-report is
# still a valid report, it is simply labelled as less verifiable.
SUBMISSION_METADATA = ("prompt_contract",)


def _flat_runs(report):
    flat = []
    for case in report.get("cases", []):
        for run in case.get("runs", []):
            flat.append({"defect": case.get("defect"), **run})
    return flat


def verify_report(report, origin="report"):
    """Return (errors, warnings). Never raises on malformed input."""
    errors, warnings = [], []
    if not isinstance(report, dict):
        return [f"{origin}: report must be a JSON object"], warnings

    for field in REQUIRED_TOP:
        if field not in report:
            errors.append(f"{origin}: missing '{field}'")
    if errors:
        return errors, warnings

    corpus = report["corpus"]
    if not isinstance(corpus, dict):
        errors.append(f"{origin}: corpus must be an object")
    else:
        for field in REQUIRED_CORPUS:
            if field not in corpus:
                errors.append(f"{origin}: corpus missing '{field}'")
        if len(str(corpus.get("sha256", ""))) != 64:
            errors.append(f"{origin}: corpus.sha256 is not a sha256 digest")
    for field in SUBMISSION_METADATA:
        if field not in report:
            warnings.append(f"{origin}: no '{field}' — self-reported (L0) "
                            "rather than reproducible (L1)")

    runs_per_case = report["runs_per_case"]
    if not isinstance(runs_per_case, int) or runs_per_case < 1:
        errors.append(f"{origin}: runs_per_case must be a positive integer")
        return errors, warnings

    cases = report["cases"]
    if not isinstance(cases, list) or not cases:
        errors.append(f"{origin}: cases must be a non-empty list")
        return errors, warnings
    if isinstance(corpus, dict) and corpus.get("case_count") != len(cases):
        errors.append(f"{origin}: corpus.case_count {corpus.get('case_count')} "
                      f"disagrees with {len(cases)} case records")

    seen = set()
    for case in cases:
        cid = case.get("case_id", "?")
        if cid in seen:
            errors.append(f"{origin}: duplicate case_id {cid!r}")
        seen.add(cid)
        runs = case.get("runs")
        if not isinstance(runs, list) or len(runs) != runs_per_case:
            errors.append(f"{origin}: {cid} has {len(runs or [])} runs, "
                          f"expected {runs_per_case}")
            continue
        if sorted(r.get("run") for r in runs) != list(range(1, runs_per_case + 1)):
            errors.append(f"{origin}: {cid} run indices are not 1..{runs_per_case}")
        for run in runs:
            status = run.get("status")
            if status not in ("ok", "error"):
                errors.append(f"{origin}: {cid} run {run.get('run')} has "
                              f"status {status!r}")
            elif status == "ok":
                if not isinstance(run.get("findings"), list):
                    errors.append(f"{origin}: {cid} run {run.get('run')} "
                                  "ok without findings list")
                if not isinstance(run.get("metrics"), dict):
                    errors.append(f"{origin}: {cid} run {run.get('run')} "
                                  "ok without metrics")
        # Consistency counters must match the runs they summarise.
        declared = case.get("consistency")
        if isinstance(declared, dict):
            ok_runs = [r for r in runs if r.get("status") == "ok"]
            recomputed = {"runs": len(runs), "ok_runs": len(ok_runs),
                          "error_runs": len(runs) - len(ok_runs)}
            for key, value in recomputed.items():
                if declared.get(key) != value:
                    errors.append(f"{origin}: {cid} consistency.{key} says "
                                  f"{declared.get(key)}, runs show {value}")
    if errors:
        return errors, warnings

    # The load-bearing check: re-derive the summary from the raw runs.
    recomputed = aggregate(_flat_runs(report))
    recomputed.update(_corpus_consistency(cases))
    declared = report["summary"]
    for key, value in recomputed.items():
        if key not in declared:
            errors.append(f"{origin}: summary missing '{key}'")
        elif declared[key] != value:
            errors.append(f"{origin}: summary.{key} says {declared[key]!r}, "
                          f"raw runs give {value!r}")
    return errors, warnings


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="reviewer-verify",
        description="Check that a result report agrees with its own raw runs.")
    parser.add_argument("reports", nargs="+", metavar="REPORT.json")
    args = parser.parse_args(argv)

    failed = False
    for path in args.reports:
        try:
            with open(path, encoding="utf-8") as fh:
                report = json.load(fh)
        except (OSError, ValueError) as exc:
            print(f"error: {path}: cannot read: {exc}", file=sys.stderr)
            failed = True
            continue
        errors, warnings = verify_report(report, origin=path)
        for w in warnings:
            print(f"warning: {w}", file=sys.stderr)
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        if errors:
            failed = True
        else:
            print(f"{path}: internally consistent "
                  f"({report['corpus']['case_count']} cases × "
                  f"{report['runs_per_case']} runs, corpus "
                  f"{report['corpus']['sha256'][:12]}…)")
    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
