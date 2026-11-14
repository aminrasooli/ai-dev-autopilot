"""Per-project configuration loading.

Deliberately NOT a central credential store: each caller passes its own
env_prefix (e.g. "JPAUTOPILOT", "CAL", "TRADINGLAB") and this module reads
only that project's own environment / .env file. No code path here can read
or hold more than one project's credential at a time, and nothing is cached
to disk except the project's own usage ledger (see budget.py).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AdapterConfig:
    project_name: str
    api_key_env_var: str
    monthly_budget_usd: float
    routine_model: str
    hard_model: str
    max_output_tokens: int
    request_timeout_s: float
    max_retries: int
    ledger_path: Path
    rate_limit_per_minute: int

    def api_key(self) -> str | None:
        """Read the key fresh on every call — never store it on the object."""
        return os.environ.get(self.api_key_env_var)


def load_config(
    project_name: str,
    *,
    env_prefix: str | None = None,
    ledger_dir: str | Path = ".",
    monthly_budget_usd: float = 10.0,
    routine_model: str = "claude-haiku-4-5",
    hard_model: str = "claude-sonnet-5",
    max_output_tokens: int = 4096,
    request_timeout_s: float = 60.0,
    max_retries: int = 2,
    rate_limit_per_minute: int = 20,
) -> AdapterConfig:
    """Build a project-scoped config.

    env_prefix defaults to the uppercased project_name. The API key env var
    is always "<PREFIX>_ANTHROPIC_API_KEY" — never the bare
    "ANTHROPIC_API_KEY" — so one project's key can never be read by another
    project's code that merely forgot to scope its lookup, and so no
    project accidentally falls back to a Claude Code subscription credential
    that might be sitting in the parent process's environment.
    """
    prefix = (env_prefix or project_name).upper().replace("-", "_")
    api_key_env_var = f"{prefix}_ANTHROPIC_API_KEY"

    budget_override = os.environ.get(f"{prefix}_MONTHLY_BUDGET_USD")
    effective_budget = float(budget_override) if budget_override else monthly_budget_usd

    return AdapterConfig(
        project_name=project_name,
        api_key_env_var=api_key_env_var,
        monthly_budget_usd=effective_budget,
        routine_model=os.environ.get(f"{prefix}_ROUTINE_MODEL", routine_model),
        hard_model=os.environ.get(f"{prefix}_HARD_MODEL", hard_model),
        max_output_tokens=max_output_tokens,
        request_timeout_s=request_timeout_s,
        max_retries=max_retries,
        ledger_path=Path(ledger_dir) / f".{prefix.lower()}_usage_ledger.jsonl",
        rate_limit_per_minute=rate_limit_per_minute,
    )
