"""Regression tests for the deploy helper script."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


def run_deploy_script(tmp_path, *args):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls_file = tmp_path / "docker-calls.log"
    docker = fake_bin / "docker"
    docker.write_text(
        "#!/usr/bin/env bash\n"
        'printf "%s\\n" "$*" >> "$DOCKER_CALLS_FILE"\n'
        "exit 0\n",
        encoding="utf-8",
    )
    docker.chmod(docker.stat().st_mode | stat.S_IXUSR)

    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["DOCKER_CALLS_FILE"] = str(calls_file)

    result = subprocess.run(
        ["bash", str(repo_root / "deploy.sh"), *args],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    calls = calls_file.read_text(encoding="utf-8").splitlines() if calls_file.exists() else []
    return result, calls


def test_deploy_script_supports_default_mode_without_profiles(tmp_path):
    result, _calls = run_deploy_script(tmp_path)

    assert result.returncode == 0, result.stderr
    assert ">> Deploying default tradingagents service" in result.stdout


def test_default_deploy_builds_with_cache_and_prunes_dangling_images(tmp_path):
    result, calls = run_deploy_script(tmp_path)

    assert result.returncode == 0, result.stderr
    assert "compose up -d --build --remove-orphans" in calls
    assert "image prune -f" in calls
    assert "builder prune -f --max-used-space 5GB" in calls
    assert all("--rmi local" not in call for call in calls)
    assert all("builder prune -af" not in call for call in calls)


def test_deep_clean_prunes_build_cache_after_deploy(tmp_path):
    result, calls = run_deploy_script(tmp_path, "--deep-clean")

    assert result.returncode == 0, result.stderr
    assert "compose up -d --build --remove-orphans" in calls
    assert "image prune -f" in calls
    assert "builder prune -af" in calls
