"""Seeded-defect reviewer evaluation.

The product question this answers: can a local open-source reviewer serve
as a useful independent reviewer, compared with a cloud one? The harness
runs IDENTICAL review semantics — same prompt, same diff, same output
contract — against any backend, over a versioned corpus with known ground
truth, and scores what each reviewer caught, missed and invented.

Scoring semantics, stated so they are checkable (and defined normatively
in docs/BENCHMARK_METHODOLOGY.md):

  detected            defect case where the reviewer reported >= 1 finding
  miss                defect case with zero findings
  false positive      CLEAN case where the reviewer reported >= 1 finding
  category correct    detected, and some finding uses the ground-truth category
  severity correct    category-correct finding whose severity is inside the
                      acceptable range
  error               the backend raised (unavailable, malformed output,
                      timeout); counted separately, never as a pass or a miss

Sampling models are nondeterministic, so --runs N evaluates every case N
independent times: every raw run is preserved, run-level counters keep the
single-run semantics, and per-case consistency (a clean case that alarms
in 1 of 3 runs says exactly that) is reported instead of flattened away.

Cost is measured, never fabricated: latency always, tokens where the
provider reports them, dollars only where a tool reports a real figure.
There are no automatic retries — a failed paid call is a recorded error,
not a silent re-spend — and every model call is bounded by a finite
timeout, so a run can be slow but never silently hung.

CI runs this with --backend fake, which replays each case's ground truth
as a perfect scripted reviewer: that proves the harness end to end with no
GPU, no Ollama, no login and no network. Real model runs are a
maintainer's local execution mode.
"""

import argparse
import json
import sys
import time

from .backends import create_backend
from .backends.fake import FakeReviewer
from .config import load_config
from .corpus import DEFAULT_CASES_DIR, corpus_fingerprint, load_corpus
from .errors import ConfigError, ReviewerError
from .result import SEVERITIES

_SEV_INDEX = {s: i for i, s in enumerate(SEVERITIES)}

REPORT_FORMAT = 2


def load_cases(cases_dir):
    """Load a validated corpus. Delegates to reviewer.corpus so the eval,
    the validator and any externally supplied (holdout) corpus all pass
    the same door."""
    return load_corpus(cases_dir)


def score_case(case, result):
    """Score one backend result against one case's ground truth."""
    gt = case["ground_truth"]
    findings = result.findings
    if not gt["defect"]:
        return {
            "detected": None,
            "false_positive": len(findings) > 0,
            "category_correct": None,
            "severity_correct": None,
        }
    detected = len(findings) > 0
    # Category correctness accepts the primary label or any pre-declared
    # alternative. Alternatives are part of the answer key, fixed before
    # any model comparison (docs/BENCHMARK_METHODOLOGY.md §5) — never
    # added afterwards because a model happened to use another word.
    acceptable = {gt["category"], *gt.get("accepted_categories", [])}
    matching = [f for f in findings if f["category"] in acceptable]
    lo, hi = (_SEV_INDEX[gt["severity"][0]], _SEV_INDEX[gt["severity"][1]])
    severity_correct = any(lo <= _SEV_INDEX[f["severity"]] <= hi for f in matching)
    return {
        "detected": detected,
        "false_positive": False,
        "category_correct": bool(matching),
        "severity_correct": severity_correct,
    }


def oracle_backend(cases):
    """A perfect scripted reviewer built from the ground truth itself.

    Proves the harness (prompting, parsing, scoring, aggregation) without
    any model: a correct harness must score the oracle at 100%.
    """
    script = {}
    for case in cases:
        gt = case["ground_truth"]
        if gt["defect"]:
            reply = {"findings": [{"category": gt["category"],
                                   "severity": gt["severity"][0],
                                   "file": None,
                                   "note": gt["explanation"]}],
                     "verdict": "changes_required"}
        else:
            reply = {"findings": [], "verdict": "approve"}
        script[case["diff"]] = reply
    return FakeReviewer(script=script, model="oracle")


def _one_run(backend, case, run_index):
    record = {"run": run_index}
    try:
        result = backend.review_diff(case["diff"])
    except ReviewerError as exc:
        record.update({"status": "error",
                       "error": f"{type(exc).__name__}: {exc}"})
        return record
    record.update({
        "status": "ok",
        "verdict": result.verdict,
        "findings": result.findings,
        "metrics": result.metrics.to_dict(),
        "score": score_case(case, result),
    })
    return record


def _case_consistency(case, runs):
    ok = [r for r in runs if r["status"] == "ok"]
    out = {"runs": len(runs), "ok_runs": len(ok),
           "error_runs": len(runs) - len(ok)}
    if case["ground_truth"]["defect"]:
        out["detected_runs"] = sum(1 for r in ok if r["score"]["detected"])
        out["category_correct_runs"] = sum(
            1 for r in ok if r["score"]["category_correct"])
        out["severity_correct_runs"] = sum(
            1 for r in ok if r["score"]["severity_correct"])
    else:
        out["false_positive_runs"] = sum(
            1 for r in ok if r["score"]["false_positive"])
    return out


def run_eval(backend, cases, runs=1, progress=None):
    """Run every case `runs` independent times; return the full report.

    `progress` is an optional callable taking one line of text; the CLI
    wires it to stderr so a long real-model run is never confusable with
    a hang. A run that errors is recorded and the eval continues — an
    external-service failure must be visible as an error, never disguised
    as model quality or allowed to abort the benchmark.
    """
    started = time.monotonic()
    case_records = []
    flat_runs = []
    for ci, case in enumerate(cases, 1):
        record = {"case_id": case["id"], "title": case["title"],
                  "defect": case["ground_truth"]["defect"],
                  "language": case.get("language"),
                  "runs": []}
        for ri in range(1, runs + 1):
            run_record = _one_run(backend, case, ri)
            record["runs"].append(run_record)
            flat_runs.append({"defect": record["defect"], **run_record})
            if progress:
                elapsed = time.monotonic() - started
                if run_record["status"] == "ok":
                    outcome = (f"ok · {len(run_record['findings'])} finding(s) "
                               f"· {run_record['metrics']['latency_seconds']}s")
                else:
                    outcome = run_record["error"].split(":")[0]
                progress(f"[{elapsed:8.1f}s] case {ci}/{len(cases)} "
                         f"run {ri}/{runs} {case['id']}: {outcome}")
        record["consistency"] = _case_consistency(case, record["runs"])
        case_records.append(record)
    return {
        "report_format": REPORT_FORMAT,
        "backend": backend.name,
        "model": backend.model,
        "runs_per_case": runs,
        # What this report actually ran against — counts and a content
        # fingerprint, never a filesystem path (a submitted report must
        # not leak local paths, and a private holdout's contents stay
        # private while still being precisely identifiable).
        "corpus": {
            "case_count": len(cases),
            "benchmark_version": cases[0].get("benchmark_version")
            if cases else None,
            "sha256": corpus_fingerprint(cases),
        },
        "cases": case_records,
        "summary": {**aggregate(flat_runs),
                    **_corpus_consistency(case_records),
                    "runs_per_case": runs},
    }


def _corpus_consistency(case_records):
    """Case-level consistency rollup: which cases were stable, which noisy."""
    defect = [c for c in case_records if c["defect"]]
    clean = [c for c in case_records if not c["defect"]]
    scored = [c for c in defect if c["consistency"]["ok_runs"] > 0]
    always = sum(1 for c in scored
                 if c["consistency"]["detected_runs"] == c["consistency"]["ok_runs"])
    never = sum(1 for c in scored if c["consistency"]["detected_runs"] == 0)
    clean_scored = [c for c in clean if c["consistency"]["ok_runs"] > 0]
    ever_fp = sum(1 for c in clean_scored
                  if c["consistency"]["false_positive_runs"] > 0)
    return {"consistency": {
        "defect_cases_always_detected": always,
        "defect_cases_sometimes_detected": len(scored) - always - never,
        "defect_cases_never_detected": never,
        "clean_cases_ever_false_positive": ever_fp,
        "cases_with_errors": sum(1 for c in case_records
                                 if c["consistency"]["error_runs"] > 0),
    }}


def aggregate(records):
    """Run-level aggregation over flat run records. With one run per case
    this is exactly the single-run summary; with N runs the counters count
    runs, and the per-case view lives in the consistency block."""
    ok = [r for r in records if r["status"] == "ok"]
    defect = [r for r in ok if r["defect"]]
    clean = [r for r in ok if not r["defect"]]
    detected = [r for r in defect if r["score"]["detected"]]
    latencies = [r["metrics"]["latency_seconds"] for r in ok]
    tokens_in = [r["metrics"]["input_tokens"] for r in ok]
    tokens_out = [r["metrics"]["output_tokens"] for r in ok]
    costs = {r["metrics"]["external_cost"] for r in ok}
    costs_usd = [r["metrics"].get("external_cost_usd") for r in ok]
    return {
        "cases": len(records),
        "errors": len(records) - len(ok),
        "defect_cases": len(defect),
        "clean_cases": len(clean),
        "detected": len(detected),
        "missed": len(defect) - len(detected),
        "false_positives": sum(1 for r in clean if r["score"]["false_positive"]),
        "category_correct": sum(1 for r in defect if r["score"]["category_correct"]),
        "severity_correct": sum(1 for r in defect if r["score"]["severity_correct"]),
        "mean_latency_seconds": round(sum(latencies) / len(latencies), 3)
        if latencies else None,
        "min_latency_seconds": round(min(latencies), 3) if latencies else None,
        "max_latency_seconds": round(max(latencies), 3) if latencies else None,
        "total_input_tokens": sum(t for t in tokens_in if t is not None)
        if any(t is not None for t in tokens_in) else None,
        "total_output_tokens": sum(t for t in tokens_out if t is not None)
        if any(t is not None for t in tokens_out) else None,
        "external_cost": sorted(costs),
        # Distinct from 'external_cost': that field holds a stable
        # per-backend label (deduped across calls), this is the honest sum
        # of whatever real dollar figures were reported — None if no call
        # reported one, never 0.
        "total_external_cost_usd": round(sum(c for c in costs_usd if c is not None), 6)
        if any(c is not None for c in costs_usd) else None,
    }


def render_summary(report):
    s = report["summary"]
    runs = report.get("runs_per_case", 1)
    unit = "runs" if runs > 1 else "cases"
    lines = [
        f"reviewer eval — backend={report['backend']} model={report['model']}"
        + (f" · {runs} runs/case" if runs > 1 else ""),
        f"  {unit}:{' ' * (18 - len(unit))}{s['cases']} "
        f"({s['defect_cases']} defective, {s['clean_cases']} clean, "
        f"{s['errors']} errors)",
        f"  detected:          {s['detected']}/{s['defect_cases']}",
        f"  missed:            {s['missed']}",
        f"  false positives:   {s['false_positives']}/{s['clean_cases']} clean {unit}",
        f"  category correct:  {s['category_correct']}/{s['defect_cases']}",
        f"  severity correct:  {s['severity_correct']}/{s['defect_cases']}",
        f"  latency:           mean {s['mean_latency_seconds']}s "
        f"(min {s['min_latency_seconds']}s, max {s['max_latency_seconds']}s)",
        f"  tokens in/out:     {s['total_input_tokens']}/{s['total_output_tokens']}",
        f"  external cost:     {'; '.join(s['external_cost']) or 'unknown'}"
        + (f" — total ${s['total_external_cost_usd']:.6f}"
           if s["total_external_cost_usd"] is not None else ""),
    ]
    c = s.get("consistency")
    if c and runs > 1:
        lines += [
            "  consistency across runs:",
            f"    defect cases always/sometimes/never detected: "
            f"{c['defect_cases_always_detected']}/"
            f"{c['defect_cases_sometimes_detected']}/"
            f"{c['defect_cases_never_detected']}",
            f"    clean cases that ever false-positived:        "
            f"{c['clean_cases_ever_false_positive']}",
            f"    cases with errored runs:                      "
            f"{c['cases_with_errors']}",
        ]
    return "\n".join(lines)


def render_comparison(report_a, report_b):
    a, b = report_a["summary"], report_b["summary"]
    name_a = f"{report_a['backend']}/{report_a['model']}"
    name_b = f"{report_b['backend']}/{report_b['model']}"
    rows = [
        ("detected", f"{a['detected']}/{a['defect_cases']}",
         f"{b['detected']}/{b['defect_cases']}"),
        ("missed", a["missed"], b["missed"]),
        ("false positives", a["false_positives"], b["false_positives"]),
        ("category correct", a["category_correct"], b["category_correct"]),
        ("severity correct", a["severity_correct"], b["severity_correct"]),
        ("errors", a["errors"], b["errors"]),
        ("mean latency (s)", a["mean_latency_seconds"], b["mean_latency_seconds"]),
        ("external cost", "; ".join(a["external_cost"]), "; ".join(b["external_cost"])),
        ("total cost (USD)",
         f"${a['total_external_cost_usd']:.6f}" if a["total_external_cost_usd"] is not None else "n/a",
         f"${b['total_external_cost_usd']:.6f}" if b["total_external_cost_usd"] is not None else "n/a"),
    ]
    # Sized from the actual cell contents, not just the header — a column
    # narrower than its longest value runs straight into the next column
    # with no separating space.
    width = max(len(name_a), *(len(str(va)) for _, va, _ in rows), 24)
    lines = [f"{'metric':<20} {name_a:<{width}} {name_b}"]
    for label, va, vb in rows:
        lines.append(f"{label:<20} {str(va):<{width}} {vb}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="review-eval",
        description="Run the seeded-defect eval against a reviewer backend.")
    parser.add_argument("--backend", choices=["codex", "ollama", "claude", "fake"],
                        help="backend to evaluate (default: from reviewer config)")
    parser.add_argument("--model", help="model override for the ollama/claude backend")
    parser.add_argument("--cases", default=DEFAULT_CASES_DIR,
                        help="directory of case JSON files")
    parser.add_argument("--runs", type=int, default=1, metavar="N",
                        help="independent runs per case (default 1)")
    parser.add_argument("--out", help="write the machine-readable report here")
    parser.add_argument("--compare", nargs=2, metavar="REPORT.json",
                        help="render a comparison of two saved reports and exit")
    args = parser.parse_args(argv)

    if args.compare:
        with open(args.compare[0], encoding="utf-8") as fh:
            report_a = json.load(fh)
        with open(args.compare[1], encoding="utf-8") as fh:
            report_b = json.load(fh)
        print(render_comparison(report_a, report_b))
        return 0

    if args.runs < 1:
        print("review-eval: --runs must be >= 1", file=sys.stderr)
        return 2

    try:
        cases = load_cases(args.cases)
        if args.backend == "fake":
            backend = oracle_backend(cases)
        else:
            config = load_config()
            if args.backend:
                config["backend"] = args.backend
            if args.model:
                config["model"] = args.model
            backend = create_backend(config)
    except ConfigError as exc:
        print(f"review-eval: {exc}", file=sys.stderr)
        return 2

    if backend.name != "fake":
        check = backend.preflight()
        if not check["ok"]:
            print(f"review-eval: backend '{backend.name}' unavailable: "
                  f"{check['detail']}", file=sys.stderr)
            return 3

    total_calls = len(cases) * args.runs
    print(f"review-eval: backend={backend.name} model={backend.model} · "
          f"{len(cases)} cases × {args.runs} run(s) = {total_calls} calls",
          file=sys.stderr)
    report = run_eval(backend, cases, runs=args.runs,
                      progress=lambda line: print(line, file=sys.stderr))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"review-eval: report written to {args.out}", file=sys.stderr)
    print(render_summary(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
