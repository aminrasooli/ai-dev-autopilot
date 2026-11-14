class AdapterError(Exception):
    """Base class for this kit's own errors (never raised for SDK errors)."""


class BudgetExhaustedError(AdapterError):
    """Raised instead of making a call that would exceed the monthly budget.

    Callers must catch this and fall back to deterministic behavior — never
    retry it, never widen the budget from inside request code.
    """

    def __init__(self, project_name: str, spent_usd: float, budget_usd: float):
        self.project_name = project_name
        self.spent_usd = spent_usd
        self.budget_usd = budget_usd
        super().__init__(
            f"{project_name}: monthly budget exhausted "
            f"(${spent_usd:.4f} spent of ${budget_usd:.2f} cap)"
        )


class RateLimitedError(AdapterError):
    """Raised by the local rate limiter before a call is even attempted."""
