"""Thin, budget-aware wrapper around the official Anthropic SDK.

Design choices:
- Model selection is explicit (routine vs. hard), never silently escalated.
- Retries/timeouts delegate to the SDK's own `max_retries`/`timeout`
  (see Anthropic SDK client config) rather than reimplementing backoff.
- The budget check runs BEFORE every call using a conservative worst-case
  estimate, and the ledger is updated with the ACTUAL usage the API
  reports afterward — so the running total is always real, not estimated,
  while the gate that prevents overspend is pessimistic on purpose.
- Credit exhaustion (whether from this local budget cap or a real 429/
  insufficient-credits response from Anthropic) always raises a typed
  exception the caller is expected to catch and fall back on — this
  adapter never retries past either kind of exhaustion.
"""

from __future__ import annotations

import logging
from typing import Literal

import anthropic

from .budget import Budget
from .config import AdapterConfig
from .exceptions import AdapterError, BudgetExhaustedError
from .pricing import CostEstimate, estimate_cost_usd
from .ratelimit import SlidingWindowLimiter

logger = logging.getLogger("anthropic_api_kit")

Difficulty = Literal["routine", "hard"]

# Rough, deliberately pessimistic chars-per-token ratio for the pre-call
# worst-case budget estimate (English prose/code is usually denser than
# this). Real spend is always taken from response.usage, never from this
# heuristic.
_CHARS_PER_TOKEN_WORST_CASE = 3.2

# Pinned so an inherited ANTHROPIC_BASE_URL can never route this project's key to another host.
API_BASE_URL = "https://api.anthropic.com"


class CreditsExhaustedError(AdapterError):
    """Anthropic itself reported the account/org is out of credits.

    Distinct from BudgetExhaustedError (our own local per-project cap) —
    this means the Console org's actual balance is gone, which this library
    cannot see directly (see REPORT.md: Admin API billing visibility).
    """


class InvalidCredentialError(AdapterError):
    """Anthropic rejected the key itself (401) — not a credits problem.

    Distinct from CreditsExhaustedError: a 401 means the configured key is
    missing, malformed, revoked, or scoped to the wrong organization/
    workspace. Retrying or escalating model tier will not fix this —
    only a corrected credential will. Never billed: a 401 is rejected
    before the request reaches a model, so it costs nothing.
    """


class ApiAdapter:
    def __init__(self, config: AdapterConfig):
        self.config = config
        self.budget = Budget(
            project_name=config.project_name,
            monthly_budget_usd=config.monthly_budget_usd,
            ledger_path=config.ledger_path,
        )
        self._limiter = SlidingWindowLimiter(config.rate_limit_per_minute)
        self._client: anthropic.Anthropic | None = None

    def _get_client(self) -> anthropic.Anthropic:
        api_key = self.config.api_key()
        if not api_key:
            raise AdapterError(
                f"{self.config.api_key_env_var} is not set — this project has no "
                "Anthropic API credential configured. See the onboarding doc; "
                "this is an owner action, not something this library can fix."
            )
        if self._client is None:
            self._client = anthropic.Anthropic(
                api_key=api_key,
                base_url=API_BASE_URL,
                timeout=self.config.request_timeout_s,
                max_retries=self.config.max_retries,
            )
        return self._client

    def select_model(self, difficulty: Difficulty) -> str:
        return self.config.hard_model if difficulty == "hard" else self.config.routine_model

    def _worst_case_estimate(self, model: str, prompt_text: str) -> CostEstimate:
        worst_case_input_tokens = max(1, int(len(prompt_text) / _CHARS_PER_TOKEN_WORST_CASE))
        return estimate_cost_usd(
            model,
            input_tokens=worst_case_input_tokens,
            output_tokens=self.config.max_output_tokens,
        )

    def complete(
        self,
        prompt: str,
        *,
        difficulty: Difficulty = "routine",
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> anthropic.types.Message:
        """Send one Messages API request, budget-gated and logged.

        Raises BudgetExhaustedError before ever calling the network if the
        worst-case cost would exceed this project's remaining monthly
        budget. Raises CreditsExhaustedError if Anthropic itself reports
        the account out of credits (HTTP 429 with an insufficient-credits
        style body, surfaced by the SDK as a RateLimitError/PermissionDeniedError
        — both are mapped here rather than left for the caller to
        string-match).
        """
        model = self.select_model(difficulty)
        worst_case = self._worst_case_estimate(model, prompt)
        self.budget.check_before_call(worst_case)

        self._limiter.acquire()
        client = self._get_client()

        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens or self.config.max_output_tokens,
                system=system or anthropic.NOT_GIVEN,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.AuthenticationError as exc:
            raise InvalidCredentialError(
                f"{self.config.project_name}: Anthropic rejected the "
                f"{self.config.api_key_env_var} credential itself (401) — "
                f"check it was copied correctly and belongs to this org's "
                f"workspace ({exc})"
            ) from exc
        except anthropic.RateLimitError as exc:
            raise CreditsExhaustedError(
                f"{self.config.project_name}: Anthropic rate-limited or "
                f"credit-exhausted this request ({exc})"
            ) from exc
        except anthropic.PermissionDeniedError as exc:
            raise CreditsExhaustedError(
                f"{self.config.project_name}: Anthropic denied this request "
                f"— check Console org credit balance and workspace scoping "
                f"({exc})"
            ) from exc
        except anthropic.APIStatusError as exc:
            # Catch-all for any other non-2xx response so a raw SDK
            # exception never escapes this adapter uncaught.
            raise AdapterError(
                f"{self.config.project_name}: Anthropic API call failed "
                f"({exc})"
            ) from exc

        actual = estimate_cost_usd(
            model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        self.budget.record(actual, model=model, request_id=response.id)
        logger.info(
            "%s: %s call cost $%.6f (in=%d out=%d), cycle spend now $%.4f/%.2f",
            self.config.project_name,
            model,
            actual.total_usd,
            response.usage.input_tokens,
            response.usage.output_tokens,
            self.budget.spent_this_cycle(),
            self.config.monthly_budget_usd,
        )
        return response
