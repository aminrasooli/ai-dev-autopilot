"""Reviewer configuration.

No file means codex — the existing default, unchanged. A file selects a
backend and carries its settings. A malformed file or an unknown backend is
an error that stops the run; it never silently falls back to codex, because
a user who configured a local reviewer must not have their diff sent to an
external service by a typo.

Search order:
  1. explicit path argument
  2. $AI_DEV_REVIEWER_CONFIG
  3. $AI_DEV_HOME/config/reviewer.json   (gitignored; user-owned)
  4. absent -> {"backend": "codex"}

Example file:

    {"backend": "ollama", "model": "qwen3.6:27b",
     "endpoint": "http://127.0.0.1:11434", "timeout": 300}
"""

import json
import os

from .errors import ConfigError

DEFAULT_CONFIG = {"backend": "codex"}

KNOWN_KEYS = {"backend", "model", "endpoint", "timeout"}


def config_path(explicit=None):
    if explicit:
        return explicit
    env = os.environ.get("AI_DEV_REVIEWER_CONFIG")
    if env:
        return env
    home = os.environ.get("AI_DEV_HOME")
    if home:
        return os.path.join(home, "config", "reviewer.json")
    return None


def load_config(explicit=None):
    path = config_path(explicit)
    if not path or not os.path.exists(path):
        if explicit:
            raise ConfigError(f"reviewer config not found: {explicit}")
        return dict(DEFAULT_CONFIG)
    try:
        with open(path, encoding="utf-8") as fh:
            obj = json.load(fh)
    except ValueError as exc:
        raise ConfigError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise ConfigError(f"{path} must contain a JSON object")
    unknown = set(obj) - KNOWN_KEYS
    if unknown:
        raise ConfigError(f"{path}: unknown keys {sorted(unknown)}")
    if "backend" not in obj:
        raise ConfigError(f"{path}: missing 'backend'")
    if "timeout" in obj:
        if not isinstance(obj["timeout"], (int, float)) or obj["timeout"] <= 0:
            raise ConfigError(f"{path}: timeout must be a positive number")
    return obj
