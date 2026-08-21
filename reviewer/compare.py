"""Deterministic comparison across N result reports.

Comparability is checked, not assumed. Two reports are directly
comparable only if they share a corpus fingerprint, a benchmark version
and a prompt-contract fingerprint; differing run counts are comparable
but worth flagging, since a 3-run and a 10-run rate carry very different
uncertainty. Anything incompatible is refused or loudly labelled rather
than quietly tabulated — a table that silently mixes corpora is worse
than no table.

No composite score and no ranking: see reviewer/leaderboard.py for why.
This prints the dimensions side by side and lets a reader weigh them.

CLI:
    python3 -m reviewer.compare A.json B.json [C.json ...]
Exit codes: 0 compared · 2 refused (incompatible or inconsistent input).
"""

import argparse
import json
import sys

from .analyze import analyze
from .corpus import DEFAULT_CASES_DIR, load_corpus
from .verify import verify_report


def compatibility(reports):
    """Return (errors, warnings) about comparing these reports together."""
    errors, warnings = [], []
    corpora = {r["corpus"]["sha256"] for _, r in reports}
    versions = {r["corpus"].get("benchmark_version") for _, r in reports}
    prompts = {(r.get("prompt_contract") or {}).get("fingerprint") for _, r in reports}
    runs = {r["runs_per_case"] for _, r in reports}
    if len(corpora) > 1:
        errors.append(f"reports span {len(corpora)} different corpora "
                      f"({', '.join(sorted(c[:12] for c in corpora))}) — "
                      "they did not answer the same questions")
    if len(versions) > 1:
        errors.append(f"reports span benchmark versions {sorted(versions)} — "
                      "scoring semantics differ between versions")
    known_prompts = {p for p in prompts if p}
    if len(known_prompts) > 1:
        errors.append(f"reports span {len(known_prompts)} prompt contracts — "
                      "the models were not asked the same thing")
    if None in prompts:
        warnings.append("at least one report predates prompt-contract "
                        "fingerprinting; assuming the contract was unchanged")
    if len(runs) > 1:
        warnings.append(f"run counts differ ({sorted(runs)}); rates are "
                        "comparable but their uncertainty is not")
    return errors, warnings


_ROWS = [
    ("defect recall", lambda a: _rate(a["overall"]["recall"], a["overall"]["recall_ci95"])),
    ("clean FP rate", lambda a: _rate(a["overall"]["fp_rate"], a["overall"]["fp_rate_ci95"])),
    ("category correct", lambda a: _frac(a["overall"]["category_correct_runs"],
                                         a["overall"]["defect_runs"])),
    ("severity correct", lambda a: _frac(a["overall"]["severity_correct_runs"],
                                         a["overall"]["defect_runs"])),
    ("always detected", lambda a: f"{a['stability']['defect_always_detected']} cases"),
    ("sometimes detected", lambda a: f"{a['stability']['defect_sometimes_detected']} cases"),
    ("never detected", lambda a: f"{a['stability']['defect_never_detected']} cases"),
    ("clean never FP", lambda a: f"{a['stability']['clean_never_fp']} cases"),
    ("clean persistent FP", lambda a: f"{a['stability']['clean_persistent_fp']} cases"),
    ("findings/run", lambda a: str(a["finding_load"]["findings_per_run_mean"])),
    ("silent runs", lambda a: str(a["finding_load"]["runs_with_zero_findings"])),
    ("unmatched on defects", lambda a: _frac(a["finding_load"]["defect_runs_with_unmatched"],
                                             a["finding_load"]["defect_runs"])),
    ("severity below/in/above", lambda a: "{}/{}/{}".format(
        a["confusion"]["severity"].get("below", 0),
        a["confusion"]["severity"].get("within", 0),
        a["confusion"]["severity"].get("above", 0))),
    ("errored runs", lambda a: str(a["overall"]["error_runs"])),
]

_TIERS = ("obvious-local", "moderate", "contextual", "subtle", "cross-file")


def _rate(value, ci):
    if value is None:
        return "—"
    return f"{value:.2f} [{ci[0]:.2f}–{ci[1]:.2f}]"


def _frac(num, den):
    return f"{num}/{den}" + (f" ({num / den:.2f})" if den else "")


def render(reports, cases):
    analyses = [(path, analyze(report, cases)) for path, report in reports]
    names = [f"{a['model']}" for _, a in analyses]
    width = max([len(n) for n in names] + [22])
    out = []
    head = f"{'metric':<24}" + "".join(f"{n:<{width + 2}}" for n in names)
    out += [head, "-" * len(head)]
    for label, fn in _ROWS:
        out.append(f"{label:<24}" + "".join(f"{fn(a):<{width + 2}}" for _, a in analyses))
    out.append("")
    out.append("recall by difficulty tier (N = defective runs in tier)")
    for tier in _TIERS:
        cells = []
        for _, a in analyses:
            g = a["by_difficulty"].get(tier, {})
            cells.append(f"{g['recall']:.2f} (N={g['defect_runs']})"
                         if "recall" in g else "—")
        out.append(f"  {tier:<22}" + "".join(f"{c:<{width + 2}}" for c in cells))
    cells = []
    for _, a in analyses:
        g = a["by_file_span"].get("cross-file", {})
        cells.append(f"{g['recall']:.2f} (N={g['defect_runs']})" if "recall" in g else "—")
    out.append(f"  {'multi-file span':<22}" + "".join(f"{c:<{width + 2}}" for c in cells))
    out.append("")
    out.append("cost and latency (different hardware — not a like-for-like benchmark)")
    for label, key in (("mean latency (s)", "mean_latency_seconds"),
                       ("min latency (s)", "min_latency_seconds"),
                       ("max latency (s)", "max_latency_seconds")):
        cells = [str(r["summary"].get(key, "—")) for _, r in reports]
        out.append(f"  {label:<22}" + "".join(f"{c:<{width + 2}}" for c in cells))
    cells = []
    for _, r in reports:
        usd = r["summary"].get("total_external_cost_usd")
        cells.append(f"${usd:.4f}" if usd is not None
                     else "no external API charge")
    out.append(f"  {'external cost':<22}" + "".join(f"{c:<{width + 2}}" for c in cells))
    out += ["",
            "Local runs incur no external model API charge; that is not the "
            "same as free — they occupy hardware for the stated latency.",
            "No composite score is offered: weighing recall against precision "
            "against cost is the reader's judgement, not the harness's."]
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="reviewer-compare",
        description="Compare N result reports on identical corpus and prompt.")
    parser.add_argument("reports", nargs="+", metavar="REPORT.json")
    parser.add_argument("--cases", default=DEFAULT_CASES_DIR)
    parser.add_argument("--force", action="store_true",
                        help="compare anyway despite incompatibility (labelled)")
    args = parser.parse_args(argv)

    loaded = []
    for path in args.reports:
        with open(path, encoding="utf-8") as fh:
            report = json.load(fh)
        errors, _ = verify_report(report, origin=path)
        if errors:
            for e in errors[:5]:
                print(f"error: {e}", file=sys.stderr)
            print(f"error: {path} is not internally consistent — refusing to "
                  "compare it", file=sys.stderr)
            return 2
        loaded.append((path, report))

    errors, warnings = compatibility(loaded)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        if not args.force:
            print("error: refusing to compare incompatible reports "
                  "(pass --force to print an explicitly-labelled table)",
                  file=sys.stderr)
            return 2
        print("WARNING: reports below are NOT directly comparable.\n")

    print(render(loaded, load_corpus(args.cases)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
