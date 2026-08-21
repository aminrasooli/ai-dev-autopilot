"""Deterministic leaderboard generation from verified result reports.

A scorecard, not a ranking. There is no composite score and no default
sort by "best", because any single number would need weights — 50%
recall plus 20% cost plus… — that we would be inventing rather than
deriving. A reviewer that catches everything and cries wolf constantly
is not obviously better or worse than a quieter one that misses a
subtle bug; which you want depends on whether your team ignores noisy
tools, and that is the reader's judgement, not ours.

So rows are ordered by model identifier, and precision, recall,
classification, consistency, latency and cost are shown side by side.
If a composite is ever justified, it needs a documented rationale in the
methodology first.

Every input must pass reviewer.verify (internal consistency) before it
appears, and each row states its verification level, corpus fingerprint
and prompt contract — comparisons are only valid within matching
fingerprints, and the generator refuses to silently mix them.

CLI:
    python3 -m reviewer.leaderboard REPORT.json [...] [--level L0=...]
"""

import argparse
import json
import sys

from .analyze import analyze
from .corpus import DEFAULT_CASES_DIR, load_corpus
from .verify import verify_report

TRUST_LEVELS = ("L0-self-reported", "L1-reproducible", "L2-reproduced",
                "L3-holdout-confirmed")


def _cost_cell(summary):
    """Cost is two dimensions, never collapsed: money leaving your
    account, and compute you already own. 'Free' is never printed."""
    usd = summary.get("total_external_cost_usd")
    if usd is not None:
        return f"${usd:.4f}"
    labels = summary.get("external_cost") or []
    if any("no external model API charge" in str(x) for x in labels):
        return "no external API charge"
    return "not metered"


def build_rows(reports, cases, levels=None):
    levels = levels or {}
    rows = []
    for path, report in reports:
        a = analyze(report, cases)
        o, s = a["overall"], a["stability"]
        defect_runs = o["defect_runs"] or 1
        clean_runs = o["clean_runs"] or 1
        xfile = a["by_file_span"].get("cross-file", {})
        rows.append({
            "model": a["model"],
            "runtime": a["backend"],
            "benchmark_version": a["corpus"].get("benchmark_version"),
            "corpus": a["corpus"]["sha256"][:12],
            "prompt": (a.get("prompt_contract") or {}).get("fingerprint", "—"),
            "runs": a["runs_per_case"],
            "recall": f"{o['recall']:.2f}" if o["recall"] is not None else "—",
            "recall_ci": f"{o['recall_ci95'][0]:.2f}–{o['recall_ci95'][1]:.2f}",
            "fp_rate": f"{o['fp_rate']:.2f}" if o["fp_rate"] is not None else "—",
            "fp_ci": f"{o['fp_rate_ci95'][0]:.2f}–{o['fp_rate_ci95'][1]:.2f}",
            "category": f"{o['category_correct_runs'] / defect_runs:.2f}",
            "severity": f"{o['severity_correct_runs'] / defect_runs:.2f}",
            "consistency": f"{s['defect_always_detected']}A/"
                           f"{s['defect_sometimes_detected']}S/"
                           f"{s['defect_never_detected']}N",
            "cross_file": f"{xfile['recall']:.2f}" if "recall" in xfile else "—",
            "latency": _latency(report),
            "errors": o["error_runs"],
            "cost": _cost_cell(report["summary"]),
            "level": levels.get(path, TRUST_LEVELS[0]),
        })
    return sorted(rows, key=lambda r: (r["model"], r["runtime"]))


def _latency(report):
    mean = report["summary"].get("mean_latency_seconds")
    lo = report["summary"].get("min_latency_seconds")
    hi = report["summary"].get("max_latency_seconds")
    if mean is None:
        return "—"
    return f"{mean:.1f}s ({lo:.1f}–{hi:.1f})" if lo is not None else f"{mean:.1f}s"

_COLUMNS = [
    ("model", "model"), ("runtime", "runtime"), ("runs", "runs"),
    ("recall", "defect recall"), ("recall_ci", "recall 95% CI"),
    ("fp_rate", "clean FP rate"), ("fp_ci", "FP 95% CI"),
    ("category", "category"), ("severity", "severity"),
    ("consistency", "always/sometimes/never"), ("cross_file", "cross-file recall"),
    ("latency", "latency"), ("errors", "errors"), ("cost", "external cost"),
    ("level", "verification"),
]


def render_markdown(rows, note=None):
    if not rows:
        return "_No verified results yet._"
    corpora = {r["corpus"] for r in rows}
    prompts = {r["prompt"] for r in rows}
    out = ["# Local Reviewer Benchmark — scorecard", ""]
    if note:
        out += [note, ""]
    out.append(
        "Ordered by model identifier, **not** by score: there is no composite "
        "ranking, because any single number would need invented weights. Read "
        "the columns together — a reviewer that catches everything and cries "
        "wolf is not strictly better than a quieter one that misses a subtle "
        "bug, and which you want is your call.")
    out.append("")
    out.append("| " + " | ".join(label for _, label in _COLUMNS) + " |")
    out.append("|" + "|".join("---" for _ in _COLUMNS) + "|")
    for r in rows:
        out.append("| " + " | ".join(str(r[key]) for key, _ in _COLUMNS) + " |")
    out += ["",
            f"Corpus fingerprint(s): {', '.join(sorted(corpora))} · "
            f"prompt contract(s): {', '.join(sorted(prompts))}."]
    if len(corpora) > 1 or len(prompts) > 1:
        out.append("**Rows above do not share a corpus or prompt contract and "
                   "are NOT directly comparable.**")
    out += ["",
            "Local runs show *no external API charge* — which is not the same "
            "as free: they occupy hardware for the stated latency and draw "
            "power that is not metered here.",
            "",
            "Verification levels: L0 self-reported · L1 reproducible metadata "
            "· L2 independently reproduced · L3 holdout-confirmed. Only L2 "
            "costs an outside party real work."]
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="reviewer-leaderboard",
        description="Render a scorecard from verified result reports.")
    parser.add_argument("reports", nargs="+", metavar="REPORT.json")
    parser.add_argument("--cases", default=DEFAULT_CASES_DIR)
    parser.add_argument("--level", action="append", default=[],
                        metavar="PATH=LEVEL",
                        help="verification level for a report path")
    parser.add_argument("--note", help="a line printed above the table")
    args = parser.parse_args(argv)

    levels = {}
    for item in args.level:
        path, _, level = item.partition("=")
        if level not in TRUST_LEVELS:
            print(f"error: level must be one of {TRUST_LEVELS}", file=sys.stderr)
            return 2
        levels[path] = level

    loaded = []
    for path in args.reports:
        with open(path, encoding="utf-8") as fh:
            report = json.load(fh)
        errors, _ = verify_report(report, origin=path)
        if errors:
            for e in errors:
                print(f"error: {e}", file=sys.stderr)
            print(f"error: {path} failed integrity verification — refusing to "
                  "put an inconsistent report on a scorecard", file=sys.stderr)
            return 2
        loaded.append((path, report))

    cases = load_corpus(args.cases)
    print(render_markdown(build_rows(loaded, cases, levels), note=args.note))
    return 0


if __name__ == "__main__":
    sys.exit(main())
