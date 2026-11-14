from datetime import datetime, timedelta, timezone

import pytest

from anthropic_api_kit.budget import Budget, _cycle_start
from anthropic_api_kit.exceptions import BudgetExhaustedError
from anthropic_api_kit.pricing import estimate_cost_usd


def test_cycle_start_after_anchor_day():
    now = datetime(2026, 11, 25, tzinfo=timezone.utc)
    start = _cycle_start(now, anchor_day=21)
    assert start == datetime(2026, 11, 21, tzinfo=timezone.utc)


def test_cycle_start_before_anchor_day_rolls_back_a_month():
    now = datetime(2026, 11, 5, tzinfo=timezone.utc)
    start = _cycle_start(now, anchor_day=21)
    assert start == datetime(2026, 10, 21, tzinfo=timezone.utc)


def test_cycle_start_handles_january():
    now = datetime(2026, 1, 5, tzinfo=timezone.utc)
    start = _cycle_start(now, anchor_day=21)
    assert start == datetime(2025, 12, 21, tzinfo=timezone.utc)


def test_budget_allows_call_under_cap(tmp_path):
    budget = Budget(project_name="t", monthly_budget_usd=10.0, ledger_path=tmp_path / "ledger.jsonl")
    est = estimate_cost_usd("claude-haiku-4-5", input_tokens=1000, output_tokens=1000)
    budget.check_before_call(est)  # should not raise


def test_budget_blocks_call_over_cap(tmp_path):
    budget = Budget(project_name="t", monthly_budget_usd=0.000001, ledger_path=tmp_path / "ledger.jsonl")
    est = estimate_cost_usd("claude-opus-5", input_tokens=1_000_000, output_tokens=1_000_000)
    with pytest.raises(BudgetExhaustedError):
        budget.check_before_call(est)


def test_budget_tracks_cumulative_spend(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    budget = Budget(project_name="t", monthly_budget_usd=1.0, ledger_path=ledger)
    est = estimate_cost_usd("claude-haiku-4-5", input_tokens=10_000, output_tokens=10_000)
    budget.record(est, model="claude-haiku-4-5")
    budget.record(est, model="claude-haiku-4-5")
    spent = budget.spent_this_cycle()
    assert spent == pytest.approx(2 * est.total_usd)


def test_budget_ignores_spend_from_prior_cycle(tmp_path, monkeypatch):
    ledger = tmp_path / "ledger.jsonl"
    old_row = {
        "ts": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat(),
        "project": "t",
        "model": "claude-haiku-4-5",
        "request_id": None,
        "input_tokens": 1000,
        "output_tokens": 1000,
        "cost_usd": 5.0,
    }
    import json
    ledger.write_text(json.dumps(old_row) + "\n")
    budget = Budget(project_name="t", monthly_budget_usd=1.0, ledger_path=ledger)
    assert budget.spent_this_cycle() == pytest.approx(0.0)


def test_budget_survives_malformed_ledger_line(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("not json at all\n")
    budget = Budget(project_name="t", monthly_budget_usd=1.0, ledger_path=ledger)
    assert budget.spent_this_cycle() == pytest.approx(0.0)
