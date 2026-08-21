"""Seeded-defect reviewer evaluation.

The product question this answers: can a local open-source reviewer serve
as a useful independent reviewer, compared with Codex? The harness runs
IDENTICAL review semantics — same prompt, same diff, same output contract —
against any backend, over ~20 small diffs with known ground truth, and
scores what each reviewer caught, missed and invented.

Scoring semantics, stated so they are checkable:

  detected            defect case where the reviewer reported >= 1 finding
  miss                defect case with zero findings
  false positive      CLEAN case where the reviewer reported >= 1 finding
  category correct    detected, and some finding uses the ground-truth category
  severity correct    category-correct finding whose severity is inside the
                      acceptable range
  error               the backend raised (unavailable, malformed output);
                      counted separately, never as a pass

Cost is measured, never fabricated: latency always, tokens where the
provider reports them, dollars never (Codex is "not directly metered";
local models have "no external model API charge").

CI runs this with --backend fake, which replays each case's ground truth
as a perfect scripted reviewer: that proves the harness end to end with no
GPU, no Ollama, no Codex login and no network. Real Codex-vs-local runs
are a maintainer's local execution mode.
"""

import argparse
import json
import os
import sys

from .backends import create_backend
from .backends.fake import FakeReviewer
from .config import load_config
from .errors import ConfigError, ReviewerError
from .result import CATEGORIES, SEVERITIES

DEFAULT_CASES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                 "eval", "cases")

_SEV_INDEX = {s: i for i, s in enumerate(SEVERITIES)}


def load_case(path):
    with open(path, encoding="utf-8") as fh:
        obj = json.load(fh)
    errors = []
    for field in ("id", "title", "diff", "ground_truth"):
        if field not in obj:
            errors.append(f"missing '{field}'")
    if errors:
        raise ConfigError(f"{path}: " + "; ".join(errors))
    if isinstance(obj["diff"], list):
        obj["diff"] = "\n".join(obj["diff"]) + "\n"
    gt = obj["ground_truth"]
    if not isinstance(gt.get("defect"), bool):
        errors.append("ground_truth.defect must be a boolean")
    if gt.get("defect"):
        if gt.get("category") not in CATEGORIES:
            errors.append(f"ground_truth.category {gt.get('category')!r} "
                          "is not in the vocabulary")
        sev = gt.get("severity", [])
        if (not isinstance(sev, list) or len(sev) != 2
                or any(s not in SEVERITIES for s in sev)
                or _SEV_INDEX[sev[0]] > _SEV_INDEX[sev[1]]):
            errors.append("ground_truth.severity must be [min, max] from the scale")
    if not isinstance(gt.get("explanation"), str) or not gt["explanation"].strip():
        errors.append("ground_truth.explanation must be a non-empty string")
    if errors:
        raise ConfigError(f"{path}: " + "; ".join(errors))
    return obj


def load_cases(cases_dir):
    paths = sorted(
        os.path.join(cases_dir, name)
        for name in os.listdir(cases_dir) if name.endswith(".json"))
    if not paths:
        raise ConfigError(f"no cases found in {cases_dir}")
    cases = [load_case(p) for p in paths]
    ids = [c["id"] for c in cases]
    if len(set(ids)) != len(ids):
        raise ConfigError("duplicate case ids")
    return cases


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
    matching = [f for f in findings if f["category"] == gt["category"]]
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


def run_eval(backend, cases):
    """Run every case; return the full machine-readable report."""
    records = []
    for case in cases:
        record = {"case_id": case["id"], "title": case["title"],
                  "defect": case["ground_truth"]["defect"]}
        try:
            result = backend.review_diff(case["diff"])
        except ReviewerError as exc:
            record.update({"status": "error",
                           "error": f"{type(exc).__name__}: {exc}"})
            records.append(record)
            continue
        record.update({
            "status": "ok",
            "verdict": result.verdict,
            "findings": result.findings,
            "metrics": result.metrics.to_dict(),
            "score": score_case(case, result),
        })
        records.append(record)
    return {
        "backend": backend.name,
        "model": backend.model,
        "cases": records,
        "summary": aggregate(records),
    }


def aggregate(records):
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
    lines = [
        f"reviewer eval — backend={report['backend']} model={report['model']}",
        f"  cases:             {s['cases']} "
        f"({s['defect_cases']} defective, {s['clean_cases']} clean, "
        f"{s['errors']} errors)",
        f"  detected:          {s['detected']}/{s['defect_cases']}",
        f"  missed:            {s['missed']}",
        f"  false positives:   {s['false_positives']}/{s['clean_cases']} clean cases",
        f"  category correct:  {s['category_correct']}/{s['defect_cases']}",
        f"  severity correct:  {s['severity_correct']}/{s['defect_cases']}",
        f"  mean latency:      {s['mean_latency_seconds']}s",
        f"  tokens in/out:     {s['total_input_tokens']}/{s['total_output_tokens']}",
        f"  external cost:     {'; '.join(s['external_cost']) or 'unknown'}"
        + (f" — total ${s['total_external_cost_usd']:.6f}"
           if s["total_external_cost_usd"] is not None else ""),
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

    report = run_eval(backend, cases)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"review-eval: report written to {args.out}", file=sys.stderr)
    print(render_summary(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
