"""SQLite-backed shared state helpers for the Web runtime."""

from __future__ import annotations

import datetime
import json
import sqlite3
from pathlib import Path
from typing import Any

from tradingagents.service.timestamps import coerce_timestamp_ms, current_timestamp_ms


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
            created_at INTEGER,
            queue_sequence INTEGER
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
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
            last_seen INTEGER
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS claims (
            run_id TEXT PRIMARY KEY,
            claimed_at INTEGER NOT NULL
        )
        """
    )
    _migrate_timestamp_columns(conn)
    return conn


def _migrate_timestamp_columns(conn: sqlite3.Connection) -> None:
    _migrate_table(
        conn,
        table_name="runs",
        create_sql="""
        CREATE TABLE runs (
            run_id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            created_at INTEGER,
            queue_sequence INTEGER
        )
        """,
        column_names=["run_id", "payload", "created_at", "queue_sequence"],
        timestamp_columns={"created_at"},
    )
    _migrate_table(
        conn,
        table_name="events",
        create_sql="""
        CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            event TEXT NOT NULL,
            data TEXT NOT NULL
        )
        """,
        column_names=["id", "run_id", "timestamp", "event", "data"],
        timestamp_columns={"timestamp"},
    )
    _migrate_table(
        conn,
        table_name="worker_status",
        create_sql="""
        CREATE TABLE worker_status (
            slot INTEGER PRIMARY KEY CHECK (slot = 1),
            worker_mode TEXT,
            last_seen INTEGER
        )
        """,
        column_names=["slot", "worker_mode", "last_seen"],
        timestamp_columns={"last_seen"},
    )
    _migrate_table(
        conn,
        table_name="claims",
        create_sql="""
        CREATE TABLE claims (
            run_id TEXT PRIMARY KEY,
            claimed_at INTEGER NOT NULL
        )
        """,
        column_names=["run_id", "claimed_at"],
        timestamp_columns={"claimed_at"},
    )


def _migrate_table(
    conn: sqlite3.Connection,
    *,
    table_name: str,
    create_sql: str,
    column_names: list[str],
    timestamp_columns: set[str],
) -> None:
    info = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    column_types = {str(row[1]): str(row[2]).upper() for row in info}
    if column_types and all(column_types.get(column_name) == "INTEGER" for column_name in timestamp_columns):
        return

    legacy_name = f"{table_name}__legacy_timestamps"
    conn.execute(f"DROP TABLE IF EXISTS {legacy_name}")
    rows = conn.execute(f"SELECT * FROM {table_name}").fetchall()
    conn.execute(f"ALTER TABLE {table_name} RENAME TO {legacy_name}")
    conn.execute(create_sql)

    placeholders = ", ".join("?" for _ in column_names)
    insert_sql = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({placeholders})"
    for row in rows:
        values = []
        for index, column_name in enumerate(column_names):
            value = row[index]
            if column_name in timestamp_columns:
                value = coerce_timestamp_ms(value)
            values.append(value)
        conn.execute(insert_sql, tuple(values))

    conn.execute(f"DROP TABLE {legacy_name}")


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
        "timestamp": current_timestamp_ms(datetime.datetime.now()),
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
    now = current_timestamp_ms(datetime.datetime.now())
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
    now = current_timestamp_ms(datetime.datetime.now())
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
