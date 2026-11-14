"""Pricing table and cost estimation for Anthropic API usage.

Prices are USD per million tokens, first-party API rates (cached 2026-11-13
from the Claude API reference). Update PRICING_LAST_VERIFIED when refreshed —
this module never calls the network; it is a static table plus arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass

PRICING_LAST_VERIFIED = "2026-11-13"

# model_id -> (input $/MTok, output $/MTok)
MODEL_PRICING_USD_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
    "claude-opus-5-5": (4.00, 20.00),
    "claude-fable-5": (10.00, 50.00),
    "claude-fable-5-1": (10.00, 50.00),
}

# Routine-vs-hard default tiers used by ApiAdapter.select_model().
DEFAULT_ROUTINE_MODEL = "claude-haiku-4-5"
DEFAULT_HARD_MODEL = "claude-sonnet-5"


@dataclass(frozen=True)
class CostEstimate:
    model: str
    input_tokens: int
    output_tokens: int
    input_cost_usd: float
    output_cost_usd: float

    @property
    def total_usd(self) -> float:
        return self.input_cost_usd + self.output_cost_usd


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> CostEstimate:
    """Estimate USD cost for a completed or planned request.

    Raises KeyError for an unlisted model — callers must add new models to
    MODEL_PRICING_USD_PER_MTOK explicitly rather than guessing a price.
    """
    if model not in MODEL_PRICING_USD_PER_MTOK:
        raise KeyError(
            f"no pricing entry for model '{model}' — add it to "
            "MODEL_PRICING_USD_PER_MTOK before using it for cost estimation"
        )
    in_rate, out_rate = MODEL_PRICING_USD_PER_MTOK[model]
    input_cost = (input_tokens / 1_000_000) * in_rate
    output_cost = (output_tokens / 1_000_000) * out_rate
    return CostEstimate(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
    )
