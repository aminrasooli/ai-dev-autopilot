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


def test_locked_down_env_blanks_every_other_credential_source(monkeypatch):
    from demos.jp_autopilot_demo import _OTHER_CREDENTIAL_ENV_VARS, _locked_down_env

    env = _locked_down_env("sk-ant-real-project-key")
    assert env["ANTHROPIC_API_KEY"] == "sk-ant-real-project-key"
    for var in _OTHER_CREDENTIAL_ENV_VARS:
        assert env[var] == "", f"{var} must be blanked, not left for the CLI to fall back to"
