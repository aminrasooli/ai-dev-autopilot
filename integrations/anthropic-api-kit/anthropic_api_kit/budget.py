"""Local, per-project usage ledger and monthly budget enforcement.

The ledger is a JSONL file living next to the caller's own project (never
centralized), one line per completed request. Budget checks are local and
conservative: they run BEFORE a request is sent, using a worst-case estimate,
so a call that would blow the budget is never attempted — there is no
server-side guarantee this code relies on, because Anthropic Console org
spend caps and credit expiration are owner-configured, not something this
library can read or set (see the Console API Drift note in REPORT.md).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .exceptions import BudgetExhaustedError
from .pricing import CostEstimate


def _cycle_start(now: datetime, anchor_day: int) -> datetime:
    """Start of the current monthly credit cycle, given the anchor day-of-month.

    Anthropic's monthly credit grant lands on a fixed calendar day (per this
    project: the 21st). The ledger resets its spend window on that day, not
    on the 1st of the month, so local tracking lines up with when fresh
    credits actually land.
    """
    if now.day >= anchor_day:
        return now.replace(day=anchor_day, hour=0, minute=0, second=0, microsecond=0)
    # Before the anchor day this month: cycle started on the anchor day of
    # the previous month.
    prev_month = now.month - 1 or 12
    prev_year = now.year - 1 if now.month == 1 else now.year
    return now.replace(
        year=prev_year, month=prev_month, day=anchor_day,
        hour=0, minute=0, second=0, microsecond=0,
    )


@dataclass
class Budget:
    project_name: str
    monthly_budget_usd: float
    ledger_path: Path
    anchor_day: int = 21

    def _read_cycle_spend(self) -> float:
        if not self.ledger_path.exists():
            return 0.0
        start = _cycle_start(datetime.now(timezone.utc), self.anchor_day)
        total = 0.0
        with self.ledger_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    ts = datetime.fromisoformat(row["ts"])
                    if ts >= start:
                        total += float(row["cost_usd"])
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue  # never let a malformed line crash budget checks
        return total

    def spent_this_cycle(self) -> float:
        return self._read_cycle_spend()

    def remaining_this_cycle(self) -> float:
        return max(0.0, self.monthly_budget_usd - self.spent_this_cycle())

    def check_before_call(self, worst_case_estimate: CostEstimate) -> None:
        """Raise BudgetExhaustedError if this call would exceed the cap."""
        spent = self.spent_this_cycle()
        if spent + worst_case_estimate.total_usd > self.monthly_budget_usd:
            raise BudgetExhaustedError(self.project_name, spent, self.monthly_budget_usd)

    def record(self, estimate: CostEstimate, *, model: str, request_id: str | None = None) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "project": self.project_name,
            "model": model,
            "request_id": request_id,
            "input_tokens": estimate.input_tokens,
            "output_tokens": estimate.output_tokens,
            "cost_usd": round(estimate.total_usd, 6),
        }
        with self.ledger_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")


# Re-exported for callers that only need the exception type.
BudgetExhausted = BudgetExhaustedError
