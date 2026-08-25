"""Private holdout contamination check (M4-D, docs/M4_DESIGN_BRIEF.md §D).

The holdout itself never lives in this repository
(docs/BENCHMARK_METHODOLOGY.md §11) — this module contains no holdout
content and does not know where one lives on any machine. What it does:
given a directory path supplied at the command line (never hardcoded,
never defaulted to anything inside this repo), compute its corpus
fingerprint the same way `reviewer.corpus` does, and check that
fingerprint against two cheap, real contamination signals:

1. **Collision with a public corpus.** If a "private" directory's
   fingerprint matches `eval/cases/` or `eval/cases-v3/cases/` exactly,
   it isn't holding anything the public corpus doesn't already have.
2. **Already referenced publicly.** If that exact fingerprint string
   already appears anywhere in `eval/EXPERIMENTS.md` (or any other
   tracked file, optionally), it may have already been run and recorded
   as if it were a public corpus — the one thing a holdout must never be.

This is a real but partial check (docs/BENCHMARK_METHODOLOGY.md §11's own
"Residual leakage" caveat still applies) — it catches accidental reuse,
it does not prove a holdout was never seen by any model provider.

CLI:
    python3 -m reviewer.holdout check --cases DIR [--repo-root .]
Exit codes: 0 no contamination signal found · 2 a signal was found ·
1 usage/IO error (e.g. DIR doesn't exist).
"""

import argparse
import os
import re
import sys

from .corpus import corpus_fingerprint, load_corpus

_FINGERPRINT_RE = re.compile(r"\b[0-9a-f]{64}\b")


def _public_corpus_fingerprints(repo_root):
    """Fingerprints of every public corpus this repo currently ships,
    computed live (never hardcoded) so this never silently goes stale
    if a corpus changes."""
    out = {}
    for name, rel in (("v2", os.path.join("eval", "cases")),
                      ("v3", os.path.join("eval", "cases-v3", "cases"))):
        path = os.path.join(repo_root, rel)
        if os.path.isdir(path) and any(f.endswith(".json")
                                       for f in os.listdir(path)):
            cases = load_corpus(path)
            out[name] = corpus_fingerprint(cases)
    return out


def _fingerprints_referenced_in_tree(repo_root, extra_paths=()):
    """Every 64-hex-char string appearing in eval/EXPERIMENTS.md and any
    extra tracked files given — a crude but real "has this exact corpus
    already been named in a public record" signal."""
    found = set()
    paths = [os.path.join(repo_root, "eval", "EXPERIMENTS.md"), *extra_paths]
    for path in paths:
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as fh:
            found.update(_FINGERPRINT_RE.findall(fh.read()))
    return found


def check_holdout(cases_dir, repo_root):
    """Return a report dict. Never raises for a contamination finding —
    only for a bad path (caller decides how to present that)."""
    cases = load_corpus(cases_dir)
    fingerprint = corpus_fingerprint(cases)

    public = _public_corpus_fingerprints(repo_root)
    referenced = _fingerprints_referenced_in_tree(repo_root)

    collisions = [name for name, fp in public.items() if fp == fingerprint]
    already_referenced = fingerprint in referenced

    return {
        "cases_dir": cases_dir,
        "case_count": len(cases),
        "fingerprint": fingerprint,
        "collides_with_public_corpus": collisions,
        "already_referenced_publicly": already_referenced,
        "ok": not collisions and not already_referenced,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="reviewer-holdout",
        description="Check a private holdout directory for contamination "
                    "signals. Never reads holdout content into this "
                    "repository; only compares fingerprints.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("check", help="check a holdout directory")
    p1.add_argument("--cases", required=True,
                    help="path to the private holdout directory "
                        "(never a path under this repository)")
    p1.add_argument("--repo-root", default=".",
                    help="this repository's root (default: cwd)")
    args = parser.parse_args(argv)

    repo_root = os.path.abspath(args.repo_root)
    cases_dir = os.path.abspath(args.cases)
    if os.path.commonpath([repo_root, cases_dir]) == repo_root:
        print("error: --cases must not be a path inside this repository "
              "— a holdout committed here is not a holdout", file=sys.stderr)
        return 1
    try:
        report = check_holdout(cases_dir, repo_root)
    except Exception as exc:  # noqa: BLE001 - CLI boundary, report and exit
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"holdout: {report['case_count']} cases, "
          f"fingerprint {report['fingerprint']}")
    if report["ok"]:
        print("no contamination signal found")
        return 0
    if report["collides_with_public_corpus"]:
        print("CONTAMINATION: fingerprint matches public corpus "
              f"{report['collides_with_public_corpus']}", file=sys.stderr)
    if report["already_referenced_publicly"]:
        print("CONTAMINATION: this fingerprint already appears in "
              "eval/EXPERIMENTS.md — it may already be public", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
