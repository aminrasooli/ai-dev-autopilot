"""Descriptive corpus diagnostics.

Deliberately descriptive: there is no composite "case quality score"
here, because any such number would encode weights nobody agreed on and
would then get optimised against. These are measurements a human uses to
decide what the corpus needs next.

Three questions this answers:

  1. How big is the context models actually receive? (A benchmark whose
     median prompt is a dozen lines is testing something much narrower
     than "code review", and that bears directly on why detection
     saturated.)
  2. Which cases resemble each other? (Near-duplicates inflate a case
     count without adding information.)
  3. How is difficulty, language, category and provenance distributed
     against changed-line volume?

Similarity uses token shingles plus a normalised-diff hash: no
embeddings, no network, deterministic. It FLAGS, it never rejects — two
cases can legitimately share a shape while testing different defects.

CLI:
    python3 -m reviewer.diagnose [--cases DIR] [--json]
"""

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict

from .corpus import DEFAULT_CASES_DIR, load_corpus
from .prompt import build_review_prompt

_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _changed_lines(diff):
    add = sum(1 for l in diff.splitlines()
              if l.startswith("+") and not l.startswith("+++"))
    rem = sum(1 for l in diff.splitlines()
              if l.startswith("-") and not l.startswith("---"))
    return add, rem


def shingles(text, n=5):
    """Token n-gram set over identifiers and words in the changed lines."""
    toks = _WORD.findall(text.lower())
    return {tuple(toks[i:i + n]) for i in range(max(0, len(toks) - n + 1))}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def similarity_report(cases, threshold=0.35):
    """Flag case pairs sharing a lot of token structure."""
    bodies = {}
    for case in cases:
        changed = "\n".join(
            l[1:] for l in case["diff"].splitlines()
            if l[:1] in "+-" and not l.startswith(("+++", "---")))
        bodies[case["id"]] = shingles(changed)
    flagged = []
    ids = [c["id"] for c in cases]
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            score = jaccard(bodies[a], bodies[b])
            if score >= threshold:
                flagged.append({"a": a, "b": b, "jaccard": round(score, 3)})
    return sorted(flagged, key=lambda f: -f["jaccard"])


def context_budget(cases):
    """Prompt sizes models actually receive, in characters and lines."""
    sizes, lines = [], []
    per_case = []
    for case in cases:
        prompt = build_review_prompt(case["diff"])
        sizes.append(len(prompt))
        lines.append(len(case["diff"].splitlines()))
        per_case.append({"case_id": case["id"], "prompt_chars": len(prompt),
                         "diff_lines": len(case["diff"].splitlines())})
    def pct(values, p):
        ordered = sorted(values)
        return ordered[min(len(ordered) - 1, int(len(ordered) * p))]
    return {
        "prompt_chars": {
            "min": min(sizes), "median": int(statistics.median(sizes)),
            "p90": pct(sizes, 0.9), "max": max(sizes),
            "approx_tokens_median": int(statistics.median(sizes) / 4),
        },
        "diff_lines": {
            "min": min(lines), "median": int(statistics.median(lines)),
            "p90": pct(lines, 0.9), "max": max(lines),
        },
        "largest": sorted(per_case, key=lambda c: -c["prompt_chars"])[:5],
        "smallest": sorted(per_case, key=lambda c: c["prompt_chars"])[:5],
    }


def complexity(cases):
    rows = []
    for case in cases:
        add, rem = _changed_lines(case["diff"])
        rows.append({
            "case_id": case["id"],
            "files": len(case["affected_files"]),
            "added": add, "removed": rem, "changed": add + rem,
            "language": case["language"],
            "difficulty": case.get("difficulty"),
        })
    changed = [r["changed"] for r in rows]
    return {
        "changed_lines": {"min": min(changed),
                          "median": int(statistics.median(changed)),
                          "max": max(changed),
                          "mean": round(statistics.mean(changed), 1)},
        "files_per_case": dict(sorted(Counter(r["files"] for r in rows).items())),
        "changed_by_difficulty": {
            k: {"cases": len(v), "median_changed": int(statistics.median(v))}
            for k, v in sorted(_group(rows, "difficulty").items())},
        "rows": rows,
    }


def _group(rows, key):
    out = defaultdict(list)
    for r in rows:
        out[r[key] or "(clean)"].append(r["changed"])
    return out


def information_density(cases):
    """How much of the corpus is structurally unique.

    Descriptive only: a repeated (language, category) pair is not
    automatically waste — two auth-bypass cases in Python can test very
    different mistakes — but a corpus where most combinations repeat is
    one where extra cases are buying less than the count suggests.
    """
    combos = Counter((c["language"], c["ground_truth"].get("category", "(clean)"))
                     for c in cases)
    cats = Counter(c["ground_truth"].get("category", "(clean)") for c in cases)
    return {
        "unique_language_category_pairs": len(combos),
        "cases": len(cases),
        "pairs_appearing_once": sum(1 for v in combos.values() if v == 1),
        "most_repeated_pairs": [
            {"language": k[0], "category": k[1], "cases": v}
            for k, v in combos.most_common(5) if v > 1],
        "categories_with_one_case": sorted(k for k, v in cats.items() if v == 1),
        "singleton_category_share": round(
            sum(1 for v in cats.values() if v == 1) / max(1, len(cats)), 3),
    }


def diagnose(cases):
    return {
        "cases": len(cases),
        "context_budget": context_budget(cases),
        "complexity": complexity(cases),
        "similarity_flags": similarity_report(cases),
        "information_density": information_density(cases),
    }


def render(d):
    cb, cx, dens = d["context_budget"], d["complexity"], d["information_density"]
    L = [f"corpus diagnostics — {d['cases']} cases", "",
         "context the model receives (this bounds what the benchmark can test)",
         f"  prompt chars    min {cb['prompt_chars']['min']} · "
         f"median {cb['prompt_chars']['median']} · p90 {cb['prompt_chars']['p90']} "
         f"· max {cb['prompt_chars']['max']}",
         f"  ~tokens median  {cb['prompt_chars']['approx_tokens_median']} "
         "(rough: chars/4)",
         f"  diff lines      min {cb['diff_lines']['min']} · "
         f"median {cb['diff_lines']['median']} · p90 {cb['diff_lines']['p90']} "
         f"· max {cb['diff_lines']['max']}", "",
         "change volume",
         f"  changed lines   min {cx['changed_lines']['min']} · "
         f"median {cx['changed_lines']['median']} · "
         f"mean {cx['changed_lines']['mean']} · max {cx['changed_lines']['max']}",
         f"  files per case  {cx['files_per_case']}", ""]
    L.append("median changed lines by difficulty")
    for k, v in cx["changed_by_difficulty"].items():
        L.append(f"  {k:<16} {v['median_changed']:>3} lines over {v['cases']} cases")
    L += ["",
          "information density (descriptive, not a quality score)",
          f"  unique (language, category) pairs: "
          f"{dens['unique_language_category_pairs']} across {dens['cases']} cases",
          f"  pairs appearing exactly once:      {dens['pairs_appearing_once']}",
          f"  categories with a single case:     "
          f"{len(dens['categories_with_one_case'])} "
          f"({dens['singleton_category_share']:.0%} of categories)"]
    if dens["most_repeated_pairs"]:
        L.append("  most repeated:")
        for p in dens["most_repeated_pairs"]:
            L.append(f"    {p['language']}/{p['category']}: {p['cases']} cases")
    L.append("")
    if d["similarity_flags"]:
        L.append(f"structural similarity flags ({len(d['similarity_flags'])}) "
                 "— flagged for review, not rejected")
        for f in d["similarity_flags"][:10]:
            L.append(f"  {f['jaccard']:.2f}  {f['a']}  ~  {f['b']}")
    else:
        L.append("structural similarity: no pairs above threshold")
    return "\n".join(L)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="reviewer-diagnose",
        description="Descriptive corpus diagnostics (no quality score).")
    parser.add_argument("--cases", default=DEFAULT_CASES_DIR)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    d = diagnose(load_corpus(args.cases))
    print(json.dumps(d, indent=2) if args.json else render(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
