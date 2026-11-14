import os

from anthropic_api_kit.config import load_config


def test_env_var_name_is_project_scoped():
    cfg = load_config("cal-photo", ledger_dir="/tmp")
    assert cfg.api_key_env_var == "CAL_PHOTO_ANTHROPIC_API_KEY"


def test_bare_anthropic_api_key_never_used(monkeypatch):
    # Even if a bare ANTHROPIC_API_KEY (e.g. from a Claude Code subscription
    # session) is sitting in the environment, a project-scoped config must
    # never read it.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-should-not-be-used")
    monkeypatch.delenv("JPAUTOPILOT_ANTHROPIC_API_KEY", raising=False)
    cfg = load_config("jpautopilot", ledger_dir="/tmp")
    assert cfg.api_key() is None


def test_budget_override_from_env(monkeypatch):
    monkeypatch.setenv("TRADINGLAB_MONTHLY_BUDGET_USD", "25.50")
    cfg = load_config("tradinglab", ledger_dir="/tmp", monthly_budget_usd=10.0)
    assert cfg.monthly_budget_usd == 25.50
