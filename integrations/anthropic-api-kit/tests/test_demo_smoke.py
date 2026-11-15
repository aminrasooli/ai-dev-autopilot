"""Smoke tests for the JP Autopilot demo:
- No credentials configured must be a graceful no-op (exit 0, no network
  call, no hang) in BOTH run modes.
- The Agent SDK subprocess env builder must never leak a usable fallback
  credential alongside the explicit project-scoped API key.
"""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEMO = Path(__file__).resolve().parent.parent / "demos" / "jp_autopilot_demo.py"
VENV_PY = Path(__file__).resolve().parent.parent / ".venv" / "bin" / "python"


@pytest.mark.parametrize("extra_args", [[], ["--smoke-test"]])
def test_demo_exits_cleanly_without_api_key(tmp_path, extra_args):
    env = {"PATH": "/usr/bin:/bin"}
    result = subprocess.run(
        [str(VENV_PY), str(DEMO), *extra_args],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "blocked" in result.stdout
    assert "not set" in result.stdout


def test_locked_down_env_blanks_every_other_credential_source(tmp_path):
    from demos.jp_autopilot_demo import _OTHER_CREDENTIAL_ENV_VARS, _locked_down_env

    env = _locked_down_env("sk-ant-real-project-key", tmp_path)
    assert env["ANTHROPIC_API_KEY"] == "sk-ant-real-project-key"
    for var in _OTHER_CREDENTIAL_ENV_VARS:
        assert env[var] == "", f"{var} must be blanked, not left for the CLI to fall back to"
    for var in ("CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY"):
        assert var in _OTHER_CREDENTIAL_ENV_VARS


def test_locked_down_env_isolates_cli_from_subscription_login(tmp_path):
    from demos.jp_autopilot_demo import _locked_down_env

    env = _locked_down_env("sk-ant-real-project-key", tmp_path)
    assert env["CLAUDE_CONFIG_DIR"] == str(tmp_path)
    assert env["ANTHROPIC_BASE_URL"] == "https://api.anthropic.com"


def test_agent_options_load_no_filesystem_settings(tmp_path, monkeypatch):
    from anthropic_api_kit.config import load_config
    from demos.jp_autopilot_demo import _build_options

    monkeypatch.setenv("JPAUTOPILOT_ANTHROPIC_API_KEY", "sk-ant-real-project-key")
    options = _build_options(tmp_path, load_config("jpautopilot", ledger_dir=tmp_path), tmp_path / "cfg")
    assert options.setting_sources == []
    assert options.env["CLAUDE_CONFIG_DIR"] == str(tmp_path / "cfg")
    assert "Bash" in options.disallowed_tools and "Write" in options.disallowed_tools
