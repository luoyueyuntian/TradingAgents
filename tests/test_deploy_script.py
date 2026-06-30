"""Regression tests for the deploy helper script."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


def test_deploy_script_supports_default_mode_without_profiles(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    docker = fake_bin / "docker"
    docker.write_text(
        "#!/usr/bin/env bash\n"
        "exit 0\n",
        encoding="utf-8",
    )
    docker.chmod(docker.stat().st_mode | stat.S_IXUSR)

    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"

    result = subprocess.run(
        ["bash", str(repo_root / "deploy.sh")],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert ">> Deploying default tradingagents service" in result.stdout
