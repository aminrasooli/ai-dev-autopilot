"""Reusable, project-scoped Claude API adapter kit.

Separate from the Claude Code subscription: this talks to the Anthropic
Messages API / Claude Agent SDK directly, billed against a project's own
Anthropic API credits. Never shares credentials across projects — each
caller supplies its own project-scoped key via its own environment.
"""

from .budget import Budget, BudgetExhausted
from .client import ApiAdapter
from .pricing import estimate_cost_usd
from .config import AdapterConfig, load_config

__all__ = [
    "ApiAdapter",
    "AdapterConfig",
    "load_config",
    "Budget",
    "BudgetExhausted",
    "estimate_cost_usd",
]
