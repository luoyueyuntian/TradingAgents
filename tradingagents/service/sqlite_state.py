"""SQLite-backed shared state helpers for the Web runtime."""

from __future__ import annotations

import datetime
import json
import sqlite3
from pathlib import Path
from typing import Any


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            created_at TEXT,
            queue_sequence INTEGER
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            event TEXT NOT NULL,
            data TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS worker_status (
            slot INTEGER PRIMARY KEY CHECK (slot = 1),
            worker_mode TEXT,
            last_seen TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS claims (
            run_id TEXT PRIMARY KEY,
            claimed_at TEXT NOT NULL
        )
        """
    )
    return conn


def upsert_run(db_path: Path, payload: dict[str, Any]) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO runs (run_id, payload, created_at, queue_sequence)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                payload=excluded.payload,
                created_at=excluded.created_at,
                queue_sequence=excluded.queue_sequence
            """,
            (
                payload["run_id"],
                json.dumps(payload, ensure_ascii=False),
                payload.get("created_at"),
                payload.get("queue_sequence"),
            ),
        )


def delete_run(db_path: Path, run_id: str) -> None:
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))


def delete_events(db_path: Path, run_id: str) -> None:
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM events WHERE run_id = ?", (run_id,))


def load_runs(db_path: Path) -> list[dict[str, Any]]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT payload FROM runs ORDER BY created_at DESC"
        ).fetchall()
    return [json.loads(row["payload"]) for row in rows]


def append_event(
    db_path: Path,
    run_id: str,
    event: dict[str, Any],
) -> dict[str, Any]:
    record = {
        "timestamp": datetime.datetime.now().isoformat(),
        "event": event.get("event", "message"),
        "data": event.get("data", {}),
    }
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO events (run_id, timestamp, event, data) VALUES (?, ?, ?, ?)",
            (
                run_id,
                record["timestamp"],
                record["event"],
                json.dumps(record["data"], ensure_ascii=False),
            ),
        )
    return record


def load_events(db_path: Path, run_id: str) -> list[dict[str, Any]]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT timestamp, event, data FROM events WHERE run_id = ? ORDER BY id ASC",
            (run_id,),
        ).fetchall()
    return [
        {
            "timestamp": row["timestamp"],
            "event": row["event"],
            "data": json.loads(row["data"]),
        }
        for row in rows
    ]


def write_worker_heartbeat(db_path: Path, worker_mode: str) -> None:
    now = datetime.datetime.now().isoformat()
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO worker_status (slot, worker_mode, last_seen)
            VALUES (1, ?, ?)
            ON CONFLICT(slot) DO UPDATE SET
                worker_mode=excluded.worker_mode,
                last_seen=excluded.last_seen
            """,
            (worker_mode, now),
        )


def read_worker_heartbeat(db_path: Path) -> dict[str, object]:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT worker_mode, last_seen FROM worker_status WHERE slot = 1"
        ).fetchone()
    if row is None:
        return {"worker_mode": None, "last_seen": None}
    return {"worker_mode": row["worker_mode"], "last_seen": row["last_seen"]}


def acquire_claim(db_path: Path, run_id: str) -> bool:
    now = datetime.datetime.now().isoformat()
    try:
        with _connect(db_path) as conn:
            conn.execute(
                "INSERT INTO claims (run_id, claimed_at) VALUES (?, ?)",
                (run_id, now),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def release_claim(db_path: Path, run_id: str) -> None:
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM claims WHERE run_id = ?", (run_id,))
