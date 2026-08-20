"""Reviewer backends.

A backend answers one question — "review this diff" — and returns a
ReviewResult. Selecting one is configuration; codex is the default and an
unknown name is an error, never a silent fallback to something else.
"""

from ..errors import ConfigError


class ReviewerBackend:
    """The whole contract. Two methods."""

    name = "abstract"
    #: True when the review itself needs an external service (Codex).
    external_service_required = True

    def preflight(self):
        """{"ok": bool, "detail": str} — can this backend run here, now?
        Never raises."""
        raise NotImplementedError

    def review_diff(self, diff_text, context=None):
        """Return a ReviewResult. Raises the typed errors in
        reviewer.errors; never falls back to another backend."""
        raise NotImplementedError


def create_backend(config):
    """Instantiate the configured backend. config is the validated dict
    from reviewer.config.load_config()."""
    from . import claude_code, codex, fake, ollama

    backends = {
        "codex": codex.CodexReviewer,
        "ollama": ollama.OllamaReviewer,
        # Eval-only: benchmarks Claude Code/Sonnet against the other
        # backends. Not wired into bin/review's interactive path.
        "claude": claude_code.ClaudeCodeReviewer,
        # Deterministic scripted backend for tests and CI eval runs.
        "fake": fake.FakeReviewer,
    }
    name = config.get("backend")
    if name not in backends:
        raise ConfigError(
            f"unknown reviewer backend {name!r} (known: {', '.join(sorted(backends))})")
    return backends[name].from_config(config)
