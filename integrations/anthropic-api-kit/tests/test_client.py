from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from anthropic_api_kit.client import ApiAdapter
from anthropic_api_kit.config import load_config
from anthropic_api_kit.exceptions import AdapterError, BudgetExhaustedError


def _config(tmp_path, **kw):
    return load_config("testproj", ledger_dir=tmp_path, **kw)


def test_missing_api_key_raises_adapter_error(tmp_path, monkeypatch):
    monkeypatch.delenv("TESTPROJ_ANTHROPIC_API_KEY", raising=False)
    adapter = ApiAdapter(_config(tmp_path))
    with pytest.raises(AdapterError):
        adapter.complete("hello", difficulty="routine")


def test_select_model_routine_vs_hard(tmp_path, monkeypatch):
    monkeypatch.setenv("TESTPROJ_ANTHROPIC_API_KEY", "sk-ant-fake-for-test")
    adapter = ApiAdapter(_config(tmp_path))
    assert adapter.select_model("routine") == "claude-haiku-4-5"
    assert adapter.select_model("hard") == "claude-sonnet-5"


def test_budget_gate_blocks_before_any_network_call(tmp_path, monkeypatch):
    monkeypatch.setenv("TESTPROJ_ANTHROPIC_API_KEY", "sk-ant-fake-for-test")
    adapter = ApiAdapter(_config(tmp_path, monthly_budget_usd=0.0000001))
    adapter._get_client = MagicMock(side_effect=AssertionError("network should never be reached"))
    with pytest.raises(BudgetExhaustedError):
        adapter.complete("x" * 10_000, difficulty="hard")


def test_successful_call_records_actual_usage(tmp_path, monkeypatch):
    monkeypatch.setenv("TESTPROJ_ANTHROPIC_API_KEY", "sk-ant-fake-for-test")
    adapter = ApiAdapter(_config(tmp_path, monthly_budget_usd=10.0))

    fake_response = SimpleNamespace(
        id="msg_fake",
        usage=SimpleNamespace(input_tokens=100, output_tokens=50),
    )
    fake_messages = MagicMock()
    fake_messages.create.return_value = fake_response
    fake_client = SimpleNamespace(messages=fake_messages)
    adapter._get_client = MagicMock(return_value=fake_client)

    result = adapter.complete("hello world", difficulty="routine")
    assert result is fake_response
    assert adapter.budget.spent_this_cycle() > 0
