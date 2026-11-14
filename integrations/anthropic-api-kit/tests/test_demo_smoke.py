"""Smoke test for the JP Autopilot demo: no credentials configured must be a
graceful no-op (exit 0, no network call), never a crash or a hang.
"""

import subprocess
import sys
from pathlib import Path

DEMO = Path(__file__).resolve().parent.parent / "demos" / "jp_autopilot_demo.py"
VENV_PY = Path(__file__).resolve().parent.parent / ".venv" / "bin" / "python"


def test_demo_exits_cleanly_without_api_key(monkeypatch, tmp_path):
    env = {"PATH": "/usr/bin:/bin"}
    result = subprocess.run(
        [str(VENV_PY), str(DEMO)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "blocked" in result.stdout
    assert "not set" in result.stdout
