"""CLI for the local (ollama) review path.

`bin/review` execs this when the configured backend is not codex; the
codex path execs the existing bin/codex-review untouched. The evidence
gathering mirrors codex-review: the diff of uncommitted work against HEAD,
or an explicit revision range, capped at the same byte ceiling.

Exit codes match codex-review: 0 review produced, 3 reviewer unavailable,
2 usage error.
"""

import argparse
import datetime
import json
import os
import subprocess
import sys

from .backends import create_backend
from .config import load_config
from .errors import ConfigError, MalformedResponse, ModelUnavailable, ReviewerUnavailable

MAX_DIFF_BYTES = 400000


def _git(repo_args, *args):
    proc = subprocess.run(["git"] + repo_args + list(args),
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise ConfigError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def gather_diff(range_=None):
    """Return (title, diff_text) for the change under review."""
    try:
        repo = _git([], "rev-parse", "--show-toplevel").strip()
    except ConfigError:
        raise ConfigError(
            "not inside a git repository — reviews cover real repositories, "
            "not loose files")
    repo_args = ["-C", repo]
    if range_:
        title = f"revision range {range_}"
        diff = _git(repo_args, "diff", "--no-color", range_)
    else:
        title = "uncommitted work against HEAD"
        if not _git(repo_args, "status", "--porcelain").strip():
            raise ConfigError(
                "working tree is clean — nothing to review. "
                "Use --range to review commits.")
        diff = _git(repo_args, "diff", "--no-color", "HEAD")
    if len(diff.encode()) > MAX_DIFF_BYTES:
        diff = diff.encode()[:MAX_DIFF_BYTES].decode("utf-8", "replace")
        diff += f"\n... diff truncated at {MAX_DIFF_BYTES} bytes.\n"
    return title, diff


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="review", description="Independent review via the configured backend.")
    parser.add_argument("--range", dest="range_", metavar="REV..REV",
                        help="review a revision range instead of uncommitted work")
    parser.add_argument("--out", help="where to write the review")
    parser.add_argument("--config", help="explicit reviewer config path")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        backend = create_backend(config)
        title, diff = gather_diff(args.range_)
    except ConfigError as exc:
        print(f"review: {exc}", file=sys.stderr)
        return 2

    if not diff.strip():
        print("review: nothing to review", file=sys.stderr)
        return 2

    print(f"review: backend={backend.name} model={backend.model} · {title}",
          file=sys.stderr)
    try:
        result = backend.review_diff(diff)
    except (ReviewerUnavailable, ModelUnavailable, MalformedResponse) as exc:
        print(f"review: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3

    rendered = result.render_markdown()
    out = args.out
    if not out:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        out_dir = os.path.join(_git([], "rev-parse", "--show-toplevel").strip(),
                               ".ai", "reviews")
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, f"{stamp}-{backend.name}.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(rendered)
        fh.write("\n<!-- metrics: " + json.dumps(result.metrics.to_dict()) + " -->\n")

    sys.stdout.write(rendered)
    metrics = result.metrics
    print(f"\n---\nreview: saved to {out}", file=sys.stderr)
    print(f"review: latency {metrics.latency_seconds}s · "
          f"tokens in/out {metrics.input_tokens}/{metrics.output_tokens} · "
          f"cost: {metrics.external_cost}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
