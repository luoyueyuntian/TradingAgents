"""Backend selection and operations for shared Web runtime state."""

from __future__ import annotations

import datetime
import json
import logging
import os
import shutil
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tradingagents.service.run_state_codec import deserialize_run_state, serialize_run_state
from tradingagents.service.sqlite_state import (
    acquire_claim as sqlite_acquire_claim,
    append_event as sqlite_append_event,
    delete_events as sqlite_delete_events,
    delete_run as sqlite_delete_run,
    load_events as sqlite_load_events,
    load_runs as sqlite_load_runs,
    read_worker_heartbeat as sqlite_read_worker_heartbeat,
    release_claim as sqlite_release_claim,
    upsert_run as sqlite_upsert_run,
    write_worker_heartbeat as sqlite_write_worker_heartbeat,
)
from tradingagents.service.web_state import (
    get_web_sqlite_path,
    get_web_state_backend,
    get_web_state_dir,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StateBackendAdapter:
    """Unified backend operations for shared Web runtime state."""

    kind: str
    location: Path

    def _index_path(self, index_path: Path | None) -> Path:
        return index_path or self.location / "runs.json"

    def _events_dir(self, base_dir: Path | None) -> Path:
        return base_dir or self.location / "events"

    def _claims_dir(self, claims_dir: Path | None) -> Path:
        return claims_dir or self.location / "claims"

    def _worker_status_path(self, path: Path | None) -> Path:
        return path or self.location / "worker-status.json"

    def upsert_run(self, run, *, index_path: Path | None = None) -> None:
        if self.kind == "sqlite":
            sqlite_upsert_run(self.location, serialize_run_state(run))
            return

        target = self._index_path(index_path)
        with _acquire_index_lock(target):
            payload = _read_index_payload(target)
            entry = serialize_run_state(run)
            replaced = False
            for idx, item in enumerate(payload):
                if isinstance(item, dict) and item.get("run_id") == run.run_id:
                    payload[idx] = entry
                    replaced = True
                    break
            if not replaced:
                payload.append(entry)
            payload.sort(key=lambda item: item.get("created_at", ""), reverse=True)
            _write_payload_atomic(target, payload)

    def delete_run(self, run_id: str, *, index_path: Path | None = None) -> None:
        if self.kind == "sqlite":
            sqlite_delete_run(self.location, run_id)
            return

        target = self._index_path(index_path)
        with _acquire_index_lock(target):
            payload = _read_index_payload(target)
            payload = [
                item for item in payload
                if not (isinstance(item, dict) and item.get("run_id") == run_id)
            ]
            _write_payload_atomic(target, payload)

    def delete_run_state(
        self,
        run_id: str,
        *,
        run_root: Path | None = None,
        event_log_path: Path | None = None,
        claims_dir: Path | None = None,
        index_path: Path | None = None,
    ) -> None:
        """Delete a run and its associated shared state."""
        if self.kind == "sqlite":
            sqlite_delete_run(self.location, run_id)
            sqlite_delete_events(self.location, run_id)
            sqlite_release_claim(self.location, run_id)
        else:
            self.delete_run(run_id, index_path=index_path)
            if run_root and run_root.exists():
                shutil.rmtree(run_root, ignore_errors=True)
            if event_log_path and event_log_path.exists():
                try:
                    event_log_path.unlink()
                except OSError:
                    pass
            claim = claim_path(run_id, claims_dir=self._claims_dir(claims_dir))
            try:
                claim.unlink()
            except FileNotFoundError:
                pass

    def load_runs(self, *, runs_root_dir: Path, index_path: Path | None = None):
        if self.kind == "sqlite":
            payload = sqlite_load_runs(self.location)
        else:
            target = self._index_path(index_path)
            payload = _read_index_payload(target) if target.exists() else []
        return {
            item["run_id"]: deserialize_run_state(item, runs_root_dir=runs_root_dir)
            for item in payload
            if isinstance(item, dict) and item.get("run_id")
        }

    def save_runs(self, runs: list, *, index_path: Path | None = None) -> None:
        if self.kind == "sqlite":
            for run in sorted(runs, key=lambda item: item.created_at or "", reverse=True):
                sqlite_upsert_run(self.location, serialize_run_state(run))
            return

        target = self._index_path(index_path)
        with _acquire_index_lock(target):
            payload = _read_index_payload(target)
            by_id: dict[str, dict] = {
                item["run_id"]: item
                for item in payload
                if isinstance(item, dict) and item.get("run_id")
            }
            for run in runs:
                by_id[run.run_id] = serialize_run_state(run)
            merged = sorted(
                by_id.values(),
                key=lambda item: item.get("created_at", ""),
                reverse=True,
            )
            _write_payload_atomic(target, merged)

    def append_event(self, run_id: str, event: dict[str, Any], *, event_log_path: Path | None = None, base_dir: Path | None = None):
        if self.kind == "sqlite":
            return self.location, sqlite_append_event(self.location, run_id, event)

        log_path = event_log_path or default_event_log_path(run_id, base_dir=self._events_dir(base_dir))
        record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "event": event.get("event", "message"),
            "data": event.get("data", {}),
        }
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            logger.warning("Failed to persist event log for run %s", run_id)
        return log_path, record

    def load_events(self, run_id: str, *, event_log_path: Path | None = None, base_dir: Path | None = None):
        if self.kind == "sqlite":
            return self.location, sqlite_load_events(self.location, run_id)

        log_path = event_log_path or default_event_log_path(run_id, base_dir=self._events_dir(base_dir))
        history: list[dict[str, Any]] = []
        if not log_path.exists():
            return log_path, history
        try:
            lines = log_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            logger.warning("Failed to read event log for run %s", run_id)
            return log_path, history
        for line in lines:
            if not line.strip():
                continue
            try:
                history.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed event log line for run %s", run_id)
        return log_path, history

    def write_worker_status(self, worker_mode: str, *, path: Path | None = None) -> None:
        if self.kind == "sqlite":
            sqlite_write_worker_heartbeat(self.location, worker_mode)
            return
        target = self._worker_status_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {
                    "worker_mode": worker_mode,
                    "last_seen": datetime.datetime.now().isoformat(),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def read_worker_status(self, *, path: Path | None = None, stale_after_seconds: int = 5) -> dict[str, object]:
        if self.kind == "sqlite":
            payload = sqlite_read_worker_heartbeat(self.location)
            return _normalize_worker_status_payload(payload, stale_after_seconds=stale_after_seconds)
        target = self._worker_status_path(path)
        if not target.exists():
            return {"worker_running": False, "worker_mode": None, "last_seen": None}
        payload = json.loads(target.read_text(encoding="utf-8"))
        return _normalize_worker_status_payload(payload, stale_after_seconds=stale_after_seconds)

    def acquire_claim(self, run_id: str, *, claims_dir: Path | None = None) -> Path | None:
        if self.kind == "sqlite":
            acquired = sqlite_acquire_claim(self.location, run_id)
            return claim_path(run_id, claims_dir=self._claims_dir(claims_dir)) if acquired else None
        path = claim_path(run_id, claims_dir=self._claims_dir(claims_dir))
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return None
        else:
            os.close(fd)
            return path

    def release_claim(self, path: Path | None = None, *, run_id: str | None = None, claims_dir: Path | None = None) -> None:
        if self.kind == "sqlite":
            if run_id is None and path is not None:
                run_id = path.stem
            if run_id is not None:
                sqlite_release_claim(self.location, run_id)
            return
        target = path or claim_path(run_id or "", claims_dir=self._claims_dir(claims_dir))
        try:
            target.unlink()
        except FileNotFoundError:
            return


def get_state_backend_adapter() -> StateBackendAdapter:
    """Return the active backend selection and primary storage location."""
    kind = get_web_state_backend()
    if kind == "sqlite":
        return StateBackendAdapter(kind="sqlite", location=get_web_sqlite_path())
    return StateBackendAdapter(kind="file", location=get_web_state_dir())


def index_lock_path(index_path: Path) -> Path:
    """Return the lockfile path used for index writes."""
    return index_path.with_suffix(index_path.suffix + ".lock")


def claim_path(run_id: str, *, claims_dir: Path) -> Path:
    return claims_dir / f"{run_id}.lock"


def default_event_log_path(run_id: str, *, base_dir: Path) -> Path:
    return base_dir / f"{run_id}.jsonl"


def _normalize_worker_status_payload(payload: dict[str, object], *, stale_after_seconds: int) -> dict[str, object]:
    last_seen_raw = payload.get("last_seen")
    worker_mode = payload.get("worker_mode")
    if not last_seen_raw:
        return {"worker_running": False, "worker_mode": worker_mode, "last_seen": None}
    last_seen = datetime.datetime.fromisoformat(str(last_seen_raw))
    age = (datetime.datetime.now() - last_seen).total_seconds()
    return {
        "worker_running": age <= stale_after_seconds,
        "worker_mode": worker_mode,
        "last_seen": last_seen_raw,
    }


def _read_index_payload(index_path: Path) -> list[dict]:
    if not index_path.exists():
        return []
    try:
        return json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Failed to load persisted run history from %s", index_path)
        return []


@contextmanager
def _acquire_index_lock(
    index_path: Path,
    *,
    timeout_seconds: float = 5.0,
    poll_interval: float = 0.05,
):
    index_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = index_lock_path(index_path)
    deadline = time.monotonic() + timeout_seconds

    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out acquiring run index lock {lock_path}")
            time.sleep(poll_interval)
            continue
        else:
            os.close(fd)
            break

    try:
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _write_payload_atomic(index_path: Path, payload: list[dict]) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(index_path.parent),
        prefix=f"{index_path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(tmp_path, index_path)
    except OSError:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
