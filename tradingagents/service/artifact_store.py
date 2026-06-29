"""Helpers for discovering and resolving run artifacts."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ArtifactDescriptor:
    """Descriptor for a downloadable run artifact."""

    key: str
    label: str
    path: Path


def _existing_file(path: str | None) -> Path | None:
    if not path:
        return None
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return None
    return file_path


def build_run_artifacts(
    *,
    report_path: str | None,
    state_log_path: str | None,
) -> list[ArtifactDescriptor]:
    """Return downloadable artifacts for a run."""
    artifacts: list[ArtifactDescriptor] = []

    report_file = _existing_file(report_path)
    if report_file is not None:
        artifacts.append(ArtifactDescriptor(
            key="complete-report",
            label="Complete report",
            path=report_file,
        ))
        report_root = report_file.parent
        for child in sorted(report_root.rglob("*.md")):
            if child == report_file:
                continue
            relative = child.relative_to(report_root).as_posix()
            artifacts.append(ArtifactDescriptor(
                key=f"report-tree/{relative}",
                label=relative,
                path=child,
            ))

    state_file = _existing_file(state_log_path)
    if state_file is not None:
        insert_at = 1 if artifacts else 0
        artifacts.insert(insert_at, ArtifactDescriptor(
            key="full-state",
            label="Full state JSON",
            path=state_file,
        ))

    return artifacts


def resolve_run_artifact(
    *,
    report_path: str | None,
    state_log_path: str | None,
    key: str,
) -> ArtifactDescriptor | None:
    """Resolve one artifact key to a concrete file."""
    for artifact in build_run_artifacts(
        report_path=report_path,
        state_log_path=state_log_path,
    ):
        if artifact.key == key:
            return artifact
    return None


def delete_run_artifacts(
    *,
    run_root: Path | None,
    event_log_path: str | None,
) -> None:
    """Delete a run's on-disk artifacts."""
    if run_root and run_root.exists():
        shutil.rmtree(run_root, ignore_errors=True)

    event_file = _existing_file(event_log_path)
    if event_file is not None:
        try:
            event_file.unlink()
        except OSError:
            pass
