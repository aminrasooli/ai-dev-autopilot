"""Variance and slice analysis over repeat-run reports.

Three runs of a sampling model are not three copies of one answer, and
collapsing them to a mean throws away the only thing repetition bought.
This module keeps the raw observations visible and answers the questions
a skeptical reader actually has:

  - which cases are stable, which are coin flips
  - does a headline recall number survive being split by difficulty,
    language, category and provenance
  - how wide is the uncertainty at this corpus size

Uncertainty method, and why this one: we report the observed run range
and a Wilson score interval on proportions. Wilson is the appropriate
choice for small n with proportions near 0 or 1 — exactly our situation,
where a normal approximation would produce intervals extending past 100%
and imply precision the data cannot support. Nothing here does
significance testing: with 57 cases and 3 runs, an interval is an honest
statement of imprecision, whereas a p-value would be decoration.
"""

import argparse
import json
import math
import sys
from collections import defaultdict

from .corpus import DEFAULT_CASES_DIR, load_corpus


def wilson_interval(successes, total, z=1.96):
    """95% Wilson score interval. Returns (low, high) as proportions."""
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    margin = (z * math.sqrt(p * (1 - p) / total
                            + z * z / (4 * total * total))) / denom
    return (round(max(0.0, centre - margin), 4),
            round(min(1.0, centre + margin), 4))


def case_stability(report):
    """Per-case behaviour across runs, raw counts preserved."""
    out = []
    for case in report["cases"]:
        runs = case["runs"]
        ok = [r for r in runs if r["status"] == "ok"]
        row = {
            "case_id": case["case_id"],
            "defect": case["defect"],
            "runs": len(runs),
            "ok_runs": len(ok),
            "error_runs": len(runs) - len(ok),
            "latencies": [r["metrics"]["latency_seconds"] for r in ok],
        }
        if case["defect"]:
            row["detected_runs"] = sum(1 for r in ok if r["score"]["detected"])
            row["category_correct_runs"] = sum(
                1 for r in ok if r["score"]["category_correct"])
            row["severity_correct_runs"] = sum(
                1 for r in ok if r["score"]["severity_correct"])
            det = row["detected_runs"]
            row["stability"] = ("always" if det and det == len(ok)
                                else "never" if det == 0 else "sometimes")
        else:
            row["false_positive_runs"] = sum(
                1 for r in ok if r["score"]["false_positive"])
            fp = row["false_positive_runs"]
            row["stability"] = ("clean" if fp == 0
                                else "persistent-fp" if fp == len(ok)
                                else "occasional-fp")
        row["latency_mean"] = (round(sum(row["latencies"]) / len(row["latencies"]), 3)
                               if row["latencies"] else None)
        row["latency_min"] = min(row["latencies"], default=None)
        row["latency_max"] = max(row["latencies"], default=None)
        out.append(row)
    return out


def _slice_rows(rows, cases_by_id, key_fn):
    """Group per-case rows by a case attribute; return run-level rates."""
    groups = defaultdict(lambda: {"defect_runs": 0, "detected": 0,
                                  "clean_runs": 0, "false_positives": 0,
                                  "category_correct": 0, "severity_correct": 0,
                                  "cases": 0})
    for row in rows:
        case = cases_by_id.get(row["case_id"])
        if case is None:
            continue
        g = groups[key_fn(case)]
        g["cases"] += 1
        if row["defect"]:
            g["defect_runs"] += row["ok_runs"]
            g["detected"] += row["detected_runs"]
            g["category_correct"] += row["category_correct_runs"]
            g["severity_correct"] += row["severity_correct_runs"]
        else:
            g["clean_runs"] += row["ok_runs"]
            g["false_positives"] += row["false_positive_runs"]
    for key, g in groups.items():
        if g["defect_runs"]:
            g["recall"] = round(g["detected"] / g["defect_runs"], 4)
            g["recall_ci95"] = wilson_interval(g["detected"], g["defect_runs"])
        if g["clean_runs"]:
            g["fp_rate"] = round(g["false_positives"] / g["clean_runs"], 4)
            g["fp_rate_ci95"] = wilson_interval(g["false_positives"], g["clean_runs"])
    return dict(sorted(groups.items()))


def analyze(report, cases):
    cases_by_id = {c["id"]: c for c in cases}
    rows = case_stability(report)
    defect_rows = [r for r in rows if r["defect"]]
    clean_rows = [r for r in rows if not r["defect"]]

    detected = sum(r["detected_runs"] for r in defect_rows)
    defect_runs = sum(r["ok_runs"] for r in defect_rows)
    fps = sum(r["false_positive_runs"] for r in clean_rows)
    clean_runs = sum(r["ok_runs"] for r in clean_rows)

    return {
        "backend": report["backend"],
        "model": report["model"],
        "runs_per_case": report["runs_per_case"],
        "corpus": report["corpus"],
        "prompt_contract": report.get("prompt_contract"),
        "overall": {
            "defect_runs": defect_runs,
            "detected": detected,
            "recall": round(detected / defect_runs, 4) if defect_runs else None,
            "recall_ci95": wilson_interval(detected, defect_runs),
            "clean_runs": clean_runs,
            "false_positives": fps,
            "fp_rate": round(fps / clean_runs, 4) if clean_runs else None,
            "fp_rate_ci95": wilson_interval(fps, clean_runs),
            "category_correct_runs": sum(r["category_correct_runs"] for r in defect_rows),
            "severity_correct_runs": sum(r["severity_correct_runs"] for r in defect_rows),
            "error_runs": sum(r["error_runs"] for r in rows),
        },
        "stability": {
            "defect_always_detected": sum(1 for r in defect_rows if r["stability"] == "always"),
            "defect_sometimes_detected": sum(1 for r in defect_rows if r["stability"] == "sometimes"),
            "defect_never_detected": sum(1 for r in defect_rows if r["stability"] == "never"),
            "clean_never_fp": sum(1 for r in clean_rows if r["stability"] == "clean"),
            "clean_occasional_fp": sum(1 for r in clean_rows if r["stability"] == "occasional-fp"),
            "clean_persistent_fp": sum(1 for r in clean_rows if r["stability"] == "persistent-fp"),
        },
        "by_difficulty": _slice_rows(rows, cases_by_id,
                                     lambda c: c.get("difficulty") or "(clean)"),
        "by_language": _slice_rows(rows, cases_by_id, lambda c: c["language"]),
        "by_category": _slice_rows(
            rows, cases_by_id,
            lambda c: c["ground_truth"].get("category", "(clean)")),
        "by_provenance": _slice_rows(rows, cases_by_id,
                                     lambda c: c["provenance"]["type"]),
        "by_file_span": _slice_rows(
            rows, cases_by_id,
            lambda c: "cross-file" if len(c["affected_files"]) > 1 else "single-file"),
        "unstable_cases": [r for r in rows
                           if r["stability"] in ("sometimes", "occasional-fp")],
        "cases": rows,
    }


def render(analysis):
    o, s = analysis["overall"], analysis["stability"]
    L = [f"variance analysis — {analysis['backend']}/{analysis['model']} "
         f"· {analysis['runs_per_case']} runs/case "
         f"· corpus {analysis['corpus']['sha256'][:12]}…",
         f"  recall            {o['detected']}/{o['defect_runs']} runs "
         f"= {o['recall']} (95% CI {o['recall_ci95'][0]}–{o['recall_ci95'][1]})",
         f"  clean FP rate     {o['false_positives']}/{o['clean_runs']} runs "
         f"= {o['fp_rate']} (95% CI {o['fp_rate_ci95'][0]}–{o['fp_rate_ci95'][1]})",
         f"  category correct  {o['category_correct_runs']}/{o['defect_runs']}",
         f"  severity correct  {o['severity_correct_runs']}/{o['defect_runs']}",
         f"  errored runs      {o['error_runs']}",
         f"  defect cases      {s['defect_always_detected']} always / "
         f"{s['defect_sometimes_detected']} sometimes / "
         f"{s['defect_never_detected']} never detected",
         f"  clean cases       {s['clean_never_fp']} never / "
         f"{s['clean_occasional_fp']} occasionally / "
         f"{s['clean_persistent_fp']} persistently false-positive"]
    for label, key in (("difficulty", "by_difficulty"),
                       ("language", "by_language"),
                       ("file span", "by_file_span")):
        L.append(f"  by {label}:")
        for name, g in analysis[key].items():
            if "recall" in g:
                L.append(f"    {name:<16} recall {g['recall']:.2f} "
                         f"(CI {g['recall_ci95'][0]:.2f}–{g['recall_ci95'][1]:.2f}) "
                         f"over {g['defect_runs']} runs")
            elif "fp_rate" in g:
                L.append(f"    {name:<16} FP rate {g['fp_rate']:.2f} "
                         f"(CI {g['fp_rate_ci95'][0]:.2f}–{g['fp_rate_ci95'][1]:.2f}) "
                         f"over {g['clean_runs']} runs")
    if analysis["unstable_cases"]:
        L.append("  unstable cases (the reason repeat runs exist):")
        for r in analysis["unstable_cases"]:
            detail = (f"detected {r['detected_runs']}/{r['ok_runs']}"
                      if r["defect"] else
                      f"false-positive {r['false_positive_runs']}/{r['ok_runs']}")
            L.append(f"    {r['case_id']:<34} {detail}")
    return "\n".join(L)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="reviewer-analyze",
        description="Variance and slice analysis over a repeat-run report.")
    parser.add_argument("report", metavar="REPORT.json")
    parser.add_argument("--cases", default=DEFAULT_CASES_DIR)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    with open(args.report, encoding="utf-8") as fh:
        report = json.load(fh)
    cases = load_corpus(args.cases)
    analysis = analyze(report, cases)
    print(json.dumps(analysis, indent=2) if args.json else render(analysis))
    return 0


if __name__ == "__main__":
    sys.exit(main())
